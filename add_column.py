import sqlite3
conn = sqlite3.connect('instance/learning_portal.db')
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE topic ADD COLUMN images TEXT")
    print('✓ Added images column')
except:
    print('✓ Images column already exists')
conn.commit()
conn.close()
