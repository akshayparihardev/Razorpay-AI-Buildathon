import sqlite3
conn = sqlite3.connect('./data/recovery.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Audit Log ===")
cursor.execute("SELECT * FROM audit_log ORDER BY id")
for row in cursor.fetchall():
    print(dict(row))