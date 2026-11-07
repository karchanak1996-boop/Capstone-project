import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib, os
from datetime import datetime
os.makedirs("outputs", exist_ok=True)

tickets = pd.read_csv("data/clean/support_tickets.csv")
def classify(t):
    t=t.lower()
    if 'fraud' in t or 'hacked' in t or 'unauthorized' in t: return 'fraud','high'
    if 'refund' in t or 'charged' in t or 'invoice' in t: return 'billing','medium'
    if 'app' in t or 'crash' in t or 'otp' in t: return 'technical','medium'
    return 'delivery','low'

rows=[]
for _,r in tickets.iterrows():
    cat,prio=classify(r['text'])
    rows.append([r['ticket_id'],r['customer_id'],r['order_id'],r['text'],cat,prio])
pd.DataFrame(rows, columns=["ticket_id","customer_id","order_id","text","predicted_category","priority"]).to_csv("outputs/triage_results.csv", index=False)
pd.DataFrame(rows).to_csv("outputs/triage_budget_demo.csv", index=False)

# Lapse
orders=pd.read_csv("data/clean/orders.csv")
orders['order_date']=pd.to_datetime(orders['order_date'])
last=orders.groupby('customer_id')['order_date'].max().reset_index()
last['days_since']=(datetime(2025,4,1)-last['order_date']).dt.days
last['lapsed']=(last['days_since']>45).astype(int)
agg=orders.groupby('customer_id').agg(total_orders=('order_id','count'), avg_amount=('order_amount','mean')).reset_index()
feat=last.merge(agg, on='customer_id', how='left').fillna(0)

X=feat[['days_since','total_orders','avg_amount']]; y=feat['lapsed']
clf=RandomForestClassifier(random_state=42); clf.fit(X,y)
joblib.dump(clf, "outputs/lapse_model.joblib")
feat[feat['lapsed']==1][['customer_id','days_since','total_orders']].to_csv("outputs/retention_list.csv", index=False)
print("Part B done")
