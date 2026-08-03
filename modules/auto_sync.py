import security_guard

import subprocess

def auto_commit_and_push(commit_message="auto: routine application sync"):
    try:
        status_check = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if not status_check.stdout.strip():
            return True, "No changes pending to sync."

        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        return True, "Successfully synced changes to remote repo!"
    except Exception as exc:
        return False, f"Auto-sync skipped or failed: {exc}"
