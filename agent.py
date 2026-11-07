import pandas as pd, os
from mock_llm import mocked_chat_api
os.makedirs("outputs", exist_ok=True)

orders=pd.read_csv("data/clean/orders.csv")
def refund_decision(o):
    if str(o['status'])!='Completed': return False,0,"Only completed orders can be refunded per refund_policy"
    if o['order_amount']<199: return False,0,"No refund on orders below INR 199 per refund_policy"
    if o['delivery_min']>45: return True,30,"Late delivery >45 mins - delivery fee waived per delivery_policy"
    return True,o['order_amount'],"Approved per refund_policy"

refund=[]
for _,o in orders.sample(200, random_state=42).iterrows():
    ok,amt,reason=refund_decision(o)
    # RAG grounded call
    msg=[{"role":"user","content":reason}]
    grounded=mocked_chat_api(msg).choices[0].message.content
    refund.append([o['order_id'],o['customer_id'],ok,amt,grounded])

pd.DataFrame(refund, columns=["order_id","customer_id","refund_approved","refund_amount","reason"]).to_csv("outputs/refund_decisions.csv", index=False)
print("Part C/D done")