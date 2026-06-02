import sqlite3
import os

db_path = 'instance/learning_portal.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE topic ADD COLUMN images TEXT")
        print("✓ Added 'images' column to topic table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("✓ 'images' column already exists")
        else:
            print(f"Note: {e}")
    conn.commit()
    conn.close()
else:
    print("Database will be created on first run")
