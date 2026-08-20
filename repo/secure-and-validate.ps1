<#
.SYNOPSIS
    Pre-push guardrail for notion-live-analyzer. Catches, locally, every bug class
    that has actually crashed this app in production so far:
      1. Wrong file encoding (UTF-16/BOM instead of UTF-8) -> "null bytes" SyntaxError
      2. Python syntax errors / SyntaxWarnings (mangled operators, broken strings)
      3. Windows/Linux filename case mismatches (Billing_stripe.py vs billing_stripe.py)
      4. Hardcoded secrets (API keys, passwords) accidentally committed
      5. .env tracked by git (should never be — real secrets would leak)

.USAGE
    Run from the repo root before every push:
        .\validate-before-push.ps1
    Exit code 0 = safe to push. Non-zero = fix the reported issues first.
#>

<#
.SYNOPSIS
    Consolidated repo-safety script for notion-live-analyzer. Run before every push.

    Step 0 fixes the two structural issues found in the repo itself:
      - .gitignore was a corrupted mix of two encodings and never excluded .env
      - .env was tracked by git (real secrets would leak the moment you fill it in)

    Steps 1-5 then scan for every bug class that has actually crashed this app
    in production so far:
      1. Wrong file encoding (UTF-16/BOM instead of UTF-8) -> "null bytes" SyntaxError
      2. Python syntax errors / SyntaxWarnings (mangled operators, broken strings)
      3. Windows/Linux filename case mismatches (Billing_stripe.py vs billing_stripe.py)
      4. Hardcoded secrets (API keys, passwords) accidentally committed
      5. .env tracked by git (re-checked, in case Step 0's untracking didn't apply
         because .env wasn't present or the repo state differs)

    This script does NOT touch application logic, admin roles, or auth — deliberately.
    Admin access is granted only via SOVEREIGN_ADMIN_EMAIL in your untracked .env /
    Streamlit secrets, never hardcoded here.

.USAGE
    Run from the repo root before every push:
        .\secure-and-validate.ps1
    Exit code 0 = safe to push. Non-zero = fix the reported issues first.
#>

$ErrorActionPreference = "Stop"
$repoRoot = (Get-Location).Path

# ---------------------------------------------------------------
# STEP 0: Repair .gitignore and stop tracking .env
# ---------------------------------------------------------------
Write-Host "[0/5] Repairing .gitignore and untracking .env..." -ForegroundColor Cyan

$gitignoreContent = @'
# --- Python ---
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/

# --- Virtual environments (never commit these -- installed fresh from requirements.txt) ---
venv/
.venv/
env/
ENV/

# --- Secrets -- NEVER commit real values ---
.env
.env.*
!.env.example
.streamlit/secrets.toml

# --- Local databases / logs ---
*.db
*.sqlite*
*.log

# --- Backups, archives, scratch copies (use git history instead) ---
_backup_*/
backup_corrupted/
pages_backup/
pages_archive/
.temp/
*_backup.py
*_backup_*.py
notion-live-analyzer/

# --- OS / editor cruft ---
.DS_Store
Thumbs.db
.idea/
.vscode/

# --- Test/coverage artifacts ---
.pytest_cache/
.coverage
htmlcov/
'@
[System.IO.File]::WriteAllText("$repoRoot\.gitignore", $gitignoreContent, [System.Text.Encoding]::UTF8)

$tracked = & git ls-files .env 2>$null
if ($tracked) {
    & git rm --cached .env | Out-Null
    Write-Host "  .env was tracked by git -- now untracked (local file kept, just stopped tracking)." -ForegroundColor Yellow
} else {
    Write-Host "  .env is not tracked -- good." -ForegroundColor Green
}

$issues = @()
$pyFiles = Get-ChildItem -Path . -Recurse -Filter *.py -File |
    Where-Object {
        $_.FullName -notmatch '\\\.git\\' -and
        $_.FullName -notmatch '\\venv\\' -and
        $_.FullName -notmatch '\\\.venv\\' -and
        $_.FullName -notmatch '\\_backup_' -and
        $_.FullName -notmatch '\\backup_corrupted\\' -and
        $_.FullName -notmatch '\\pages_backup\\' -and
        $_.FullName -notmatch '\\pages_archive\\' -and
        $_.FullName -notmatch '\\notion-live-analyzer\\'   # nested duplicate repo, if still present
    }

Write-Host "Scanning $($pyFiles.Count) Python files..." -ForegroundColor Cyan

# ---------------------------------------------------------------
# CHECK 1: File encoding — reject any .py/.gitignore file containing null bytes
# ---------------------------------------------------------------
Write-Host "`n[1/5] Checking file encodings..." -ForegroundColor Cyan
$encodingTargets = $pyFiles + (Get-Item ".gitignore" -ErrorAction SilentlyContinue)
foreach ($f in $encodingTargets) {
    if (-not $f) { continue }
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    if ($bytes -contains 0) {
        $issues += "ENCODING: $($f.FullName.Replace($repoRoot,'.')) contains null bytes — likely saved as UTF-16 instead of UTF-8. Re-save as UTF-8 (no BOM)."
    }
}

# ---------------------------------------------------------------
# CHECK 2: Python syntax errors / warnings (requires python on PATH)
# ---------------------------------------------------------------
Write-Host "[2/5] Checking Python syntax..." -ForegroundColor Cyan
foreach ($f in $pyFiles) {
    $result = & python -W error::SyntaxWarning -c "compile(open(r'$($f.FullName)', 'rb').read(), r'$($f.FullName)', 'exec')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $issues += "SYNTAX: $($f.FullName.Replace($repoRoot,'.')) -- $($result -join ' ')"
    }
}

# ---------------------------------------------------------------
# CHECK 3: Case-sensitive import vs filename mismatches
#   (Windows won't catch these; Streamlit Cloud's Linux runner will)
# ---------------------------------------------------------------
Write-Host "[3/5] Checking for Windows/Linux filename case mismatches..." -ForegroundColor Cyan
$moduleFiles = @{}
Get-ChildItem -Path .\modules -Filter *.py -File -ErrorAction SilentlyContinue | ForEach-Object {
    $moduleFiles[$_.BaseName] = $_.Name   # actual on-disk name, exact case
}
$importPattern = 'from\s+modules\s+import\s+([\w,\s]+)|from\s+\.\s+import\s+([\w,\s]+)|from\s+modules\.(\w+)\s+import|import\s+modules\.(\w+)'
foreach ($f in $pyFiles) {
    $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    $matches = [regex]::Matches($content, $importPattern)
    foreach ($m in $matches) {
        $names = @($m.Groups[1].Value, $m.Groups[2].Value) -split ',' | ForEach-Object { $_.Trim() }
        if ($m.Groups[3].Success) { $names += $m.Groups[3].Value }
        if ($m.Groups[4].Success) { $names += $m.Groups[4].Value }
        foreach ($name in $names) {
            if (-not $name) { continue }
            $lowerName = $name.ToLower()
            if ($moduleFiles.ContainsKey($lowerName) -and $moduleFiles[$lowerName] -cne "$name.py") {
                $issues += "CASE MISMATCH: $($f.FullName.Replace($repoRoot,'.')) imports '$name' but the file on disk is '$($moduleFiles[$lowerName])'. This works on Windows, will crash on Streamlit Cloud (Linux)."
            }
        }
    }
}

# ---------------------------------------------------------------
# CHECK 4: Hardcoded secrets
# ---------------------------------------------------------------
Write-Host "[4/5] Scanning for hardcoded secrets..." -ForegroundColor Cyan
$secretPatterns = @(
    @{ Name = "Stripe live key";    Pattern = 'sk_live_[A-Za-z0-9]{20,}' },
    @{ Name = "Stripe test key";    Pattern = 'sk_test_[A-Za-z0-9]{20,}' },
    @{ Name = "AWS access key";     Pattern = 'AKIA[0-9A-Z]{16}' },
    @{ Name = "Google client secret"; Pattern = 'GOCSPX-[A-Za-z0-9_\-]{20,}' },
    @{ Name = "Generic API key assignment"; Pattern = '(?i)(api_key|apikey|secret_key|access_token)\s*=\s*["\''][A-Za-z0-9_\-]{16,}["\'']' },
    @{ Name = "Hardcoded password assignment"; Pattern = '(?i)password\s*=\s*["\''][^"\'']{4,}["\'']' }
)
foreach ($f in $pyFiles) {
    $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    foreach ($p in $secretPatterns) {
        if ($content -match $p.Pattern) {
            $issues += "SECRET: $($f.FullName.Replace($repoRoot,'.')) matches pattern '$($p.Name)'. Verify this isn't a real credential before pushing."
        }
    }
}

# ---------------------------------------------------------------
# CHECK 5: .env must never be tracked by git
# ---------------------------------------------------------------
Write-Host "[5/5] Checking .env is not tracked by git..." -ForegroundColor Cyan
$tracked = & git ls-files .env 2>$null
if ($tracked) {
    $issues += "SECRETS RISK: '.env' is tracked by git. Run: git rm --cached .env  (keep the local file, just stop tracking it) — otherwise real secrets will leak the moment you fill it in."
}

# ---------------------------------------------------------------
# RESULTS
# ---------------------------------------------------------------
Write-Host ""
if ($issues.Count -eq 0) {
    Write-Host "All checks passed. Safe to push." -ForegroundColor Green
    exit 0
} else {
    Write-Host "$($issues.Count) issue(s) found — fix before pushing:" -ForegroundColor Red
    foreach ($i in $issues) {
        Write-Host "  - $i" -ForegroundColor Yellow
    }
    exit 1
}