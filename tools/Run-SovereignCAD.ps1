$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path

Set-Location -LiteralPath $Root

python -m sovereign_cad.desktop
