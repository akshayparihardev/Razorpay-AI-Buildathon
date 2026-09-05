import sqlite3
conn = sqlite3.connect('./data/recovery.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Customers ===")
cursor.execute("SELECT COUNT(*) FROM customers")
print(f"Total customers: {cursor.fetchone()[0]}")

print("\n=== Payments ===")
cursor.execute("SELECT COUNT(*) FROM payments")
print(f"Total payments: {cursor.fetchone()[0]}")

print("\n=== Failure Reasons Distribution ===")
cursor.execute("SELECT failure_reason, COUNT(*), SUM(amount) FROM payments GROUP BY failure_reason")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} payments, ${row[2]:.2f}")

print("\n=== Sample Payment ===")
cursor.execute("SELECT * FROM payments LIMIT 1")
row = cursor.fetchone()
print(dict(row))

print("\n=== Sample Customer ===")
cursor.execute("SELECT * FROM customers LIMIT 1")
row = cursor.fetchone()
print(dict(row))