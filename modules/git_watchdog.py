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
        self.cooldown = 10  # Wait at least 10 seconds between pushes to avoid rate-limiting

    def on_any_event(self, event):
        # Ignore git directory changes and temp files to avoid infinite loops
        if ".git" in event.src_path or "__pycache__" in event.src_path or event.src_path.endswith((".tmp", ".log")):
            return

        current_time = time.time()
        if current_time - self.last_sync < self.cooldown:
            return

        # Debounce: give file writes a moment to finish
        time.sleep(2)
        self.trigger_sync()

    def trigger_sync(self):
        try:
            # Check for changes
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=self.watch_path)
            if not status.stdout.strip():
                return

            print("🔄 [Git Watchdog] Changes detected! Auto-committing and pushing...")
            subprocess.run(["git", "add", "."], cwd=self.watch_path, check=True)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            subprocess.run(["git", "commit", "-m", f"auto: autonomous watchdog sync - {timestamp}"], cwd=self.watch_path, check=True)
            
            push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, cwd=self.watch_path)
            if push_res.returncode == 0:
                print(f"🚀 [Git Watchdog] Successfully pushed to GitHub at {timestamp}!")
                self.last_sync = time.time()
            else:
                print(f"⚠️ [Git Watchdog] Push deferred or auth required: {push_res.stderr.strip()}")
        except Exception as e:
            print(f"❌ [Git Watchdog Error]: {str(e)}")

def start_watchdog():
    path = "."
    event_handler = GitAutoSyncHandler(path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("🛡️ [Git Watchdog Daemon] Active and monitoring workspace for instant auto-sync...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watchdog()

