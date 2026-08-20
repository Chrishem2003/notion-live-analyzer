import sqlite3
import glob

db_files = glob.glob('**/*.db', recursive=True)
if not db_files:
    db_files = ['sovereign_apex_engine.db']

for db_path in db_files:
    print(f"Patching database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure core tables exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_analyses (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, timestamp TEXT, category TEXT, content TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS system_telemetry_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, module_name TEXT, severity TEXT, details TEXT, crypto_hash TEXT, prev_hash TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions (email TEXT PRIMARY KEY, plan TEXT, trial_started TEXT, renews_at TEXT, status TEXT)''')

    # Add missing columns safely
    migrations = [
        ('system_telemetry_logs', 'prev_hash', 'TEXT'),
        ('subscriptions', 'renews_at', 'TEXT')
    ]

    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            print(f"  -> Added missing column '{column}' to '{table}'.")
        except sqlite3.OperationalError:
            print(f"  -> Column '{column}' already exists in '{table}'.")

    conn.commit()
    conn.close()
print("Database schema patch completed successfully.")