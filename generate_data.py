import os, csv, math, random
from datetime import datetime, timedelta
rng = random.Random(42)
CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Pune"]
PRODUCTS = [
    ("Amul Gold Milk 500ml", "Dairy", 31),
    ("Lays Classic Salted 48g", "Snacks", 20),
    ("Fortune Sunflower Oil 1L", "Grocery", 145),
    ("Colgate Strong Teeth 100g", "Personal Care", 58),
    ("Dove Shampoo 80ml", "Personal Care", 95),
    ("Britannia Bread 400g", "Bakery", 35),
    ("Red Bull 250ml", "Beverages", 110),
    ("iPhone Charger Cable", "Electronics", 299),
    ("Wireless Earbuds", "Electronics", 1299),
    ("Power Bank 10000mAh", "Electronics", 999),
]
IMPOSSIBLE_AGE = [160,200,250,416,999,510,200]

def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

def poisson(lam):
    L = math.exp(-lam); k=0; p=1.0
    while True:
        k+=1; p*=rng.random()
        if p <= L: return k-1

def mangle_city(c):
    r=rng.random()
    return c.lower() if r<0.20 else c.upper() if r<0.32 else f" {c} " if r<0.42 else c

def mangle_gender(g):
    return rng.choice(["male","Male","MALE","m","M","female","Female","FEMALE","f","F","FEMALE"])

product_rows=[[f"P{i:03d}",n,c,p] for i,(n,c,p) in enumerate(PRODUCTS,1)]
write_csv("data/raw/products.csv",["product_id","product_name","category","price_inr"],product_rows)
write_csv("products.csv",["product_id","product_name","category","price_inr"],product_rows)

cust_rows=[]
for i in range(1,501):
    city=mangle_city(rng.choice(CITIES))
    gender=mangle_gender(rng.choice(["Male","Female"]))
    age=rng.choice(IMPOSSIBLE_AGE) if rng.random()<0.05 else rng.randint(18,65)
    signup=datetime(2024,1,1)+timedelta(days=rng.randint(0,400))
    cust_rows.append([f"C{i:04d}",f"User_{i}",gender,city,age,signup.strftime("%Y-%m-%d")])
for _ in range(20): cust_rows.append(rng.choice(cust_rows))
rng.shuffle(cust_rows)
write_csv("data/raw/customers.csv",["customer_id","name","gender","city","age","signup_date"],cust_rows)
write_csv("customers.csv",["customer_id","name","gender","city","age","signup_date"],cust_rows)

order_rows=[]; order_by_cust={f"C{i:04d}":[] for i in range(1,501)}; oid=1
start=datetime(2024,1,1)
for _ in range(1500):
    cid=f"C{rng.randint(1,500):04d}"; prod=PRODUCTS[rng.randint(0,len(PRODUCTS)-1)]
    pid=f"P{PRODUCTS.index(prod)+1:03d}"; qty=poisson(1.2)+1
    order_date=start+timedelta(days=rng.randint(0,450),minutes=rng.randint(0,1440))
    status="Completed" if rng.random()<0.75 else "Cancelled" if rng.random()<0.5 else "Pending"
    amount=prod[2]*qty*(1-rng.choice([0,0,0,5,10,15])/100)
    order_rows.append([f"O{oid:05d}",cid,pid,qty,order_date.strftime("%Y-%m-%d %H:%M"),status,round(amount,2),0,rng.randint(10,70)])
    order_by_cust[cid].append(oid); oid+=1
for row in order_rows[:100]:
    if rng.random()<0.15: order_rows.append([row[0]+"_dup",row[1],row[2],row[3],row[4],"Pending",row[6],row[7],row[8]])
rng.shuffle(order_rows)
write_csv("data/raw/orders.csv",["order_id","customer_id","product_id","quantity","order_date","status","order_amount","discount_pct","delivery_min"],order_rows)
write_csv("orders.csv",["order_id","customer_id","product_id","quantity","order_date","status","order_amount","discount_pct","delivery_min"],order_rows)

TEMPLATES={
 "billing":["I was charged twice for order {o}. Please refund.","The invoice for {o} shows a wrong amount. Call me to correct the bill."],
 "delivery":["My order {o} has not arrived and the rider is not reachable.","Delivery for {o} is very late, it was promised in 30 mins.","The rider marked {o} as delivered but I never received it."],
 "technical":["The app crashes every time I open the cart. I cannot place {o}.","I cannot login, the OTP never arrives on {o}."],
 "fraud":["There is an unauthorized transaction on my card for order {o} that I never made, it looks like fraud.","Someone hacked my account and used my wallet balance for {o}."]
}
ticket_rows=[]; tid=1
cust_with_orders=[c for c,v in order_by_cust.items() if v]
for _ in range(400):
    cid=rng.choice(cust_with_orders); oid_c=f"O{rng.choice(order_by_cust[cid]):05d}"
    cat=rng.choice(list(TEMPLATES.keys())); txt=rng.choice(TEMPLATES[cat]).format(o=oid_c)
    ticket_rows.append([f"T{tid:04d}",cid,oid_c,txt,cat]); tid+=1
write_csv("data/raw/support_tickets.csv",["ticket_id","customer_id","order_id","text","category"],ticket_rows)
write_csv("support_tickets.csv",["ticket_id","customer_id","order_id","text","category"],ticket_rows)

open("data/raw/refund_policy.txt","w").write("Refund Policy: A refund can be requested only for completed orders. Perishable: 2 hours. Non-perishable: 7 days. Wrong item: 24h. Orders below 199: no refund. Refund must be raised within 7 days of delivery. If delivery delayed >45 mins, delivery fee waived.")
open("refund_policy.txt","w").write("Refund Policy: A refund can be requested only for completed orders. Perishable: 2 hours. Non-perishable: 7 days. Wrong item: 24h. Orders below 199: no refund. Refund must be raised within 7 days of delivery. If delivery delayed >45 mins, delivery fee waived.")