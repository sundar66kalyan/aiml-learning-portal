from app import app
from models import db
import sqlite3

with app.app_context():
    # Get database path
    db_path = 'instance/learning_portal.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check and add missing columns
    cursor.execute("PRAGMA table_info(topic)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'difficulty' not in columns:
        cursor.execute("ALTER TABLE topic ADD COLUMN difficulty TEXT DEFAULT 'Beginner'")
        print('✓ Added difficulty column')
    
    if 'views' not in columns:
        cursor.execute("ALTER TABLE topic ADD COLUMN views INTEGER DEFAULT 0")
        print('✓ Added views column')
    
    conn.commit()
    conn.close()
    print('✓ Database schema updated successfully')
