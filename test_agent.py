from backend.database import init_db
from backend.seed_data import seed_database
init_db()
seed_database()
from backend.agent import decide_recovery_action

result1 = decide_recovery_action('PAY_001')
print('Test 1 (regular):', result1)

import sqlite3
conn = sqlite3.connect('./data/recovery.db')
cursor = conn.cursor()
cursor.execute("SELECT id FROM payments WHERE failure_reason='fraud_suspected'")
fraud_ids = [row[0] for row in cursor.fetchall()]
conn.close()

if fraud_ids:
    result2 = decide_recovery_action(fraud_ids[0])
    print('Test 2 (fraud):', result2)