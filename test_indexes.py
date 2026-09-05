import sqlite3
conn = sqlite3.connect('./data/recovery.db')
cursor = conn.cursor()
cursor.execute('SELECT sql FROM sqlite_master WHERE type="index"')
for row in cursor.fetchall():
    print(row[0])
    print()