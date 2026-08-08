import sqlite3
import os

# Common places where SQLite databases might be stored in a project
possible_paths = [
    "database.db",
    "app.db",
    "data.db",
    "users.db",
    "instance/database.db",
    "instance/app.db"
]

db_path = None
for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    # Ask the user or search current directory for any .db file
    db_files = [f for f in os.listdir('.') if f.endswith('.db')]
    if db_files:
        db_path = db_files[0]

if db_path:
    print(f"Found database at: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        conn.commit()
        print("Successfully added 'created_at' column to the 'users' table!")
    except sqlite3.OperationalError as e:
        print(f"Note: {e} (This usually means the column already exists).")
    finally:
        conn.close()
else:
    print("Could not automatically locate a .db file. Please check your configuration for the database path.")