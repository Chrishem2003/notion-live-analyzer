
import time
import subprocess
import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class GitAutoSyncHandler(FileSystemEventHandler):
    def __init__(self, watch_path):
        self.watch_path = Path(watch_path)
        self.last_sync = 0
        self.cooldown = 8  # Cooldown window to prevent spamming

    def on_any_event(self, event):
        if ".git" in event.src_path or "__pycache__" in event.src_path or event.src_path.endswith((".tmp", ".log")):
            return

        current_time = time.time()
        if current_time - self.last_sync < self.cooldown:
            return

        time.sleep(1.5)
        self.trigger_sync()

    def trigger_sync(self):
        try:
            # Check for any changes (staged, unstaged, or untracked)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=self.watch_path)
            if not status.stdout.strip():
                return

            print("Ã°Å¸â€â€ž [Git Watchdog] Workspace modification detected! Auto-staging, committing, and pushing...")
            
            # Stage all changes (handles both modified and staged-only files)
            subprocess.run(["git", "add", "-A"], cwd=self.watch_path, check=True)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_res = subprocess.run(["git", "commit", "-m", f"auto: full workspace autonomous sync - {timestamp}}"], cwd=self.watch_path, capture_output=True, text=True)
            
            if commit_res.returncode != 0 and "nothing to commit" in commit_res.stdout:
                return

            push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, cwd=self.watch_path)
            if push_res.returncode == 0:
                print(f"Ã°Å¸Å¡â‚¬ [Git Watchdog] Successfully auto-pushed to GitHub at {timestamp}}!")
                self.last_sync = time.time()
            else:
                print(f"Ã¢Å¡Â Ã¯Â¸Â [Git Watchdog] Push pending or authentication required: {push_res.stderr.strip()}}")
        except Exception as e:
            print(f"Ã¢ÂÅ’ [Git Watchdog Error]: {str(e)}}")

def start_watchdog():
    path = "."
    event_handler = GitAutoSyncHandler(path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("Ã°Å¸â€ºÂ¡Ã¯Â¸Â [Git Watchdog Daemon] Active and monitoring all staged/unstaged changes for instant auto-sync...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watchdog()


