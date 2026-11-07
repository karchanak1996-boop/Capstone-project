import pandas as pd
import numpy as np
import sqlite3
import joblib
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier

# ================= MOCK LLM (Part C/D - RAG Grounded) =================
class MockChoice:
    def __init__(self, content, tool_calls=None):
        self.message = type('obj', (object,), {'content': content, 'tool_calls': tool_calls or []})()

class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]
        self.usage = {'total_tokens': 100}

def mocked_chat_api(messages, tools=None, model="mock"):
    txt = messages[-1]['content'].lower() if isinstance(messages[-1], dict) else str(messages[-1]).lower()
    if '45' in txt or 'late' in txt or 'delayed' in txt:
        return MockResponse("As per Refund Policy, if delivery delayed >45 mins, delivery fee waived.")
    if '199' in txt:
        return MockResponse("As per Refund Policy, no refund on orders below INR 199.")
    if 'perishable' in txt:
        return MockResponse("As per Refund Policy, perishable items refund within 2 hours.")
    return MockResponse("As per policy, check relevant policy document.")

def mock_llm(prompt, tools=None):
    return mocked_chat_api([{'content': prompt}])

# ================= SETUP FOLDERS =================
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/clean").mkdir(parents=True, exist_ok=True)
Path("outputs").mkdir(parents=True, exist_ok=True)
Path("src").mkdir(parents=True, exist_ok=True)

# ================= GENERATE DATA (generate_data.py) =================
print("Generating raw data...")
np.random.seed(42)
n_cust = 500
n_prod = 50

customers = pd.DataFrame({
    'customer_id': [f"C{i:04d}" for i in range(1, n_cust+1)],
    'name': [f"Customer {i}" for i in range(1, n_cust+1)],
    'age': np.random.choice([25, 30, 35, 40, 200, None, 28], n_cust),
    'gender': np.random.choice(['M', 'Male', 'F', 'Female', 'male'], n_cust),
    'city': np.random.choice([' mumbai', 'DELHI ', 'Bangalore', 'chennai'], n_cust),
    'signup_date': pd.date_range('2024-01-01', periods=n_cust).strftime('%Y-%m-%d')
})
# Add duplicate for cleaning demo
customers = pd.concat([customers, customers.iloc[[0]]], ignore_index=True)

products = pd.DataFrame({
    'product_id': [f"P{i:03d}" for i in range(1, n_prod+1)],
    'product_name': [f"Product {i}" for i in range(1, n_prod+1)],
    'category': np.random.choice(['Grocery', 'Dairy', 'Snacks'], n_prod),
    'price': np.random.randint(20, 500, n_prod)
})

orders_list = []
for i in range(1, 2001):
    orders_list.append({
        'order_id': f"O{i:05d}",
        'customer_id': f"C{np.random.randint(1, n_cust+1):04d}",
        'order_date': pd.to_datetime('2025-01-01') + pd.Timedelta(days=np.random.randint(0, 90)),
        'order_amount': np.random.randint(100, 1500),
        'delivery_min': np.random.randint(20, 70),
        'status': np.random.choice(['Completed', 'Cancelled', 'Returned'], p=[0.85, 0.10, 0.05])
    })
orders = pd.DataFrame(orders_list)

texts = [
    "I was charged twice, need refund for my order",
    "App crash during payment, OTP not received",
    "My delivery is late by 60 mins",
    "Unauthorized transaction, my account hacked fraud",
    "Invoice not received for my order",
    "Perishable items damaged, need refund"
]
tickets = pd.DataFrame({
    'ticket_id': [f"T{i:04d}" for i in range(1, 301)],
    'customer_id': [f"C{np.random.randint(1, n_cust+1):04d}" for _ in range(300)],
    'order_id': [f"O{np.random.randint(1, 2001):05d}" for _ in range(300)],
    'text': np.random.choice(texts, 300),
    'created_at': pd.date_range('2025-02-01', periods=300).strftime('%Y-%m-%d')
})

customers.to_csv("data/raw/customers.csv", index=False)
products.to_csv("data/raw/products.csv", index=False)
orders.to_csv("data/raw/orders.csv", index=False)
tickets.to_csv("data/raw/support_tickets.csv", index=False)
print("Raw data done -> data/raw/")

# ================= PART A - CLEANING =================
print("Running Part A - Cleaning...")
cust = pd.read_csv("data/raw/customers.csv")
cust['city'] = cust['city'].astype(str).str.strip().str.title()
cust['gender'] = cust['gender'].astype(str).str.lower().map({'m':'Male','male':'Male','f':'Female','female':'Female'}).fillna('Male')
cust['age'] = pd.to_numeric(cust['age'], errors='coerce')
med = cust[cust['age'].between(10, 90)]['age'].median()
cust.loc[~cust['age'].between(10, 90), 'age'] = med
cust = cust.drop_duplicates('customer_id', keep='last')
cust.to_csv("data/clean/customers.csv", index=False)

orders_c = pd.read_csv("data/raw/orders.csv")
orders_c['order_date_only'] = pd.to_datetime(orders_c['order_date']).dt.date
orders_c = orders_c.drop_duplicates(['customer_id','order_date_only','status'], keep='last').drop(columns=['order_date_only'])
orders_c.to_csv("data/clean/orders.csv", index=False)

for f in ["products", "support_tickets"]:
    pd.read_csv(f"data/raw/{f}.csv").to_csv(f"data/clean/{f}.csv", index=False)

# SQLite DB - Required Repository Contents
con = sqlite3.connect("data/instamart.db")
for tbl in ["customers", "products", "orders", "support_tickets"]:
    pd.read_csv(f"data/clean/{tbl}.csv").to_sql(tbl, con, if_exists="replace", index=False)
con.close()
print("Part A done - cleaned + instamart.db created")

# ================= PART B - TRIAGE + LAPSE =================
print("Running Part B - Triage + Lapse...")
tickets_c = pd.read_csv("data/clean/support_tickets.csv")

def classify(t):
    t = str(t).lower()
    if 'fraud' in t or 'hacked' in t or 'unauthorized' in t:
        return 'fraud', 'high'
    if 'refund' in t or 'charged' in t or 'invoice' in t:
        return 'billing', 'medium'
    if 'app' in t or 'crash' in t or 'otp' in t:
        return 'technical', 'medium'
    return 'delivery', 'low'

rows = []
for _, r in tickets_c.iterrows():
    cat, prio = classify(r['text'])
    rows.append([r['ticket_id'], r['customer_id'], r['order_id'], r['text'], cat, prio])

triage_df = pd.DataFrame(rows, columns=["ticket_id","customer_id","order_id","text","predicted_category","priority"])
triage_df.to_csv("outputs/triage_results.csv", index=False)
triage_df.to_csv("outputs/triage_budget_demo.csv", index=False)

# Lapse Model
orders_c['order_date'] = pd.to_datetime(orders_c['order_date'])
last = orders_c.groupby('customer_id')['order_date'].max().reset_index()
last['days_since'] = (datetime(2025, 4, 1) - last['order_date']).dt.days
last['lapsed'] = (last['days_since'] > 45).astype(int)
agg = orders_c.groupby('customer_id').agg(total_orders=('order_id','count'), avg_amount=('order_amount','mean')).reset_index()
feat = last.merge(agg, on='customer_id', how='left').fillna(0)

X = feat[['days_since','total_orders','avg_amount']]
y = feat['lapsed']
clf = RandomForestClassifier(random_state=42)
clf.fit(X, y)
joblib.dump(clf, "outputs/lapse_model.joblib")
feat[feat['lapsed']==1][['customer_id','days_since','total_orders']].to_csv("outputs/retention_list.csv", index=False)
print("Part B done - triage_results.csv + retention_list.csv + lapse_model.joblib")

# ================= PART C/D - REFUND AGENT =================
print("Running Part C/D - Refund Agent...")

def refund_decision(o):
    if str(o['status']) != 'Completed':
        return False, 0, "Only completed orders can be refunded per refund_policy"
    if o['order_amount'] < 199:
        return False, 0, "No refund on orders below INR 199 per refund_policy"
    if o['delivery_min'] > 45:
        return True, 30, "Late delivery >45 mins - delivery fee waived per delivery_policy"
    return True, o['order_amount'], "Approved per refund_policy"

refund = []
for _, o in orders_c.sample(200, random_state=42).iterrows():
    ok, amt, reason = refund_decision(o)
    msg = [{"role": "user", "content": reason}]
    grounded = mocked_chat_api(msg).choices[0].message.content
    refund.append([o['order_id'], o['customer_id'], ok, amt, grounded])

pd.DataFrame(refund, columns=["order_id","customer_id","refund_approved","refund_amount","reason"]).to_csv("outputs/refund_decisions.csv", index=False)
print("Part C/D done - refund_decisions.csv")
print("\nALL DONE! Check:")
print("- data/raw/ + data/clean/ + data/instamart.db")
print("- outputs/triage_results.csv, triage_budget_demo.csv, retention_list.csv, lapse_model.joblib, refund_decisions.csv")