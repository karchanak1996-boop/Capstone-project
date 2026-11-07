import pandas as pd, sqlite3, os
os.makedirs("data/clean", exist_ok=True)

cust = pd.read_csv("data/raw/customers.csv")
cust['city'] = cust['city'].astype(str).str.strip().str.title()
cust['gender'] = cust['gender'].astype(str).str.lower().map({'m':'Male','male':'Male','f':'Female','female':'Female'}).fillna('Male')
cust['age'] = pd.to_numeric(cust['age'], errors='coerce')
med = cust[cust['age'].between(10,90)]['age'].median()
cust.loc[~cust['age'].between(10,90), 'age'] = med
cust = cust.drop_duplicates('customer_id', keep='last')
cust.to_csv("data/clean/customers.csv", index=False)

orders = pd.read_csv("data/raw/orders.csv")
orders['order_date_only'] = pd.to_datetime(orders['order_date']).dt.date
orders = orders.drop_duplicates(['customer_id','order_date_only','status'], keep='last').drop(columns=['order_date_only'])
orders.to_csv("data/clean/orders.csv", index=False)

for f in ["products","support_tickets"]:
    pd.read_csv(f"data/raw/{f}.csv").to_csv(f"data/clean/{f}.csv", index=False)

# SQLite DB - Required Repository Contents
con = sqlite3.connect("data/instamart.db")
for tbl in ["customers","products","orders","support_tickets"]:
    pd.read_csv(f"data/clean/{tbl}.csv").to_sql(tbl, con, if_exists="replace", index=False)
con.close()
print("Part A done - cleaned + instamart.db created")