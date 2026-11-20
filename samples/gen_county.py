"""Generate fake county-records.csv (300 rows) and leases.csv for the sfcre build. All data invented."""
import csv, json, random, re, sys
from datetime import date, timedelta
from pathlib import Path

random.seed(4812)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
TODAY = date(2026, 11, 21)

CITIES = [("Sacramento", "958"), ("Davis", "956"), ("Roseville", "956"), ("Elk Grove", "957"),
          ("Folsom", "956"), ("Rancho Cordova", "956"), ("West Sacramento", "956"), ("Citrus Heights", "956")]
TREES = ["Oak", "Elm", "Pine", "Cedar", "Maple", "Birch", "Willow", "Aspen", "Redwood", "Sycamore", "Juniper", "Laurel"]
SUFFIX = ["Ave", "St", "Blvd", "Rd", "Dr", "Way", "Ct", "Ln"]
TYPES = ["Office"] * 5 + ["Retail"] * 4 + ["Industrial"] * 4 + ["Multifamily"] * 3 + ["Land"] * 2 + ["Other"]
FIRST = ["Maria", "James", "Linh", "Robert", "Aisha", "David", "Elena", "Kenji", "Priya", "Thomas", "Grace", "Omar",
         "Sofia", "Daniel", "Hannah", "Victor", "Nadia", "Paul", "Rosa", "Samuel"]
LAST = ["Testerson", "Fakeley", "Mockwell", "Sampleton", "Demoro", "Placeford", "Nullman", "Stubbs", "Dummond", "Fixture"]
ENT_WORDS = ["Capitol", "River", "Delta", "Sierra", "Valley", "Gold", "Harbor", "Summit", "Granite", "Meadow",
             "Pioneer", "Lakeside", "Northgate", "Oakmont", "Westfield", "Brightline"]
ENT_TAIL = ["Holdings LLC", "Properties LLC", "Partners LP", "Investments Inc", "Realty Inc", "Ventures LLC", "Land Trust"]

# Same rules as the spec's Clean node (owner_key, phone_clean), to verify the planted cases.
def owner_key(n):
    k = (n or "").upper()
    k = re.sub(r"[.,]", "", k)
    k = re.sub(r"\b(LLC|INC|CORP|CO|LP|LLP|LTD|TRUST)\b", "", k)
    k = re.sub(r"[^A-Z0-9 ]", " ", k).strip()
    k = re.sub(r"\s+", "-", k)
    return k or "UNKNOWN-OWNER"

def phone_clean(p):
    d = re.sub(r"\D", "", p or "")
    return "+1" + d if len(d) == 10 else ("+" + d if len(d) == 11 and d[0] == "1" else "")

def phone():
    return f"(916) 555-{random.randint(100, 199):04d}"

used_keys = set()
def new_owner():
    while True:
        if random.random() < 0.55:
            a, b = random.sample(ENT_WORDS, 2); n = f"{a} {b} {random.choice(ENT_TAIL)}"
        else:
            n = f"{random.choice(FIRST)} {random.choice(LAST)}"
        if owner_key(n) not in used_keys:
            used_keys.add(owner_key(n)); return n

def mail(city=None):
    c, z = random.choice(CITIES)
    return (f"PO Box {random.randint(100, 9999)}" if random.random() < 0.3 else f"{random.randint(10, 9999)} {random.choice(TREES)} Test {random.choice(SUFFIX)}",
            c, "CA", f"{z}{random.randint(10, 99)}")

rows, n = [], 0
def add_row(owner, street=None, **over):
    global n
    n += 1
    c, z = random.choice(CITIES)
    m = mail()
    r = {"APN": f"TEST-{random.randint(100, 999)}-{random.randint(100, 999)}-{n:03d}",
         "SITUS_ADDRESS": street or f"{random.randint(10, 9999)} Test {random.choice(TREES)} {random.choice(SUFFIX)}",
         "SITUS_CITY": c, "SITUS_STATE": "CA", "SITUS_ZIP": f"{z}{random.randint(10, 99)}",
         "USE_CODE": random.choice(TYPES), "BLDG_SQFT": random.choice([0, 0]) if False else random.randint(1200, 85000),
         "YR_BUILT": random.randint(1952, 2021), "OWNER_NAME": owner,
         "MAIL_ADDRESS": m[0], "MAIL_CITY": m[1], "MAIL_STATE": m[2], "MAIL_ZIP": m[3],
         "OWNER_PHONE": phone() if random.random() < 0.7 else ""}
    if r["USE_CODE"] == "Land":
        r["BLDG_SQFT"], r["YR_BUILT"] = "", ""
    r.update(over); rows.append(r); return r

# 1) 6 owners written 2-4 ways across 20 properties
VARIANTS = [
    ["Acme Holdings, L.L.C.", "ACME HOLDINGS LLC", "Acme Holdings L.L.C", "acme holdings llc"],
    ["Riverbend Partners, LP", "RIVERBEND PARTNERS LP", "Riverbend Partners L.P."],
    ["Goldfield Investments, Inc.", "GOLDFIELD INVESTMENTS INC", "Goldfield Investments Inc"],
    ["Tess Q. Mockingham", "TESS Q MOCKINGHAM", "Tess Q Mockingham"],
    ["Northstar Realty Corp.", "NORTHSTAR REALTY CORP"],
    ["Harborview Land Trust", "HARBORVIEW LAND TRUST", "Harborview Land, Trust"],
]
counts = [4, 4, 3, 3, 3, 3]  # = 20
for vs, k in zip(VARIANTS, counts):
    keys = {owner_key(v) for v in vs}
    assert len(keys) == 1, (vs, keys)
    used_keys |= keys
    for i in range(k):
        add_row(vs[i % len(vs)])

# 2) 3 lowercase/abbreviation variants of one street (different parcels)
for s in ["210 Test Elm Street", "214 test elm st.", "218 TEST ELM ST"]:
    add_row(new_owner(), street=s)

# 3) the rest, normal rows, up to 290 unique
while len(rows) < 290:
    add_row(new_owner())

body = rows[26:]  # leave the planted variant rows clean
random.shuffle(body)
# 4) planted problems on distinct normal rows
for r in body[0:5]: r["OWNER_NAME"] = ""                                   # 5 blank owners
for r in body[5:10]: r.update(MAIL_ADDRESS="", MAIL_CITY="", MAIL_ZIP="")  # 5 blank mailing
for r, p in zip(body[10:18], ["555-01", "N/A", "916-555-01420", "12345", "(916) 555", "call office", "0000", "916555014"]):
    r["OWNER_PHONE"] = p                                                    # 8 bad phones
for r in body[18:23]: r["SITUS_ZIP"] = r["SITUS_ZIP"] + f"-{random.randint(1000, 9999)}"  # 5 ZIP+4
for r in body[0:2]: r["OWNER_PHONE"] = ""  # blank-owner rows: no phone, so no double flag

# 5) 10 duplicate APN rows (exact copies of normal clean rows)
dups = [dict(r) for r in body[30:40]]
allrows = rows + dups
random.shuffle(allrows)

# Checks against the spec's expectations
assert len(allrows) == 300 and len({r["APN"] for r in allrows}) == 290
assert all(len(phone_clean(p)) == 0 for p in ["555-01", "N/A", "916-555-01420", "12345", "(916) 555", "call office", "0000", "916555014"])
assert all(phone_clean(r["OWNER_PHONE"]) or not r["OWNER_PHONE"] for r in rows if r not in body[10:18])
uniq = {r["APN"]: r for r in allrows}.values()
review = [r for r in uniq if owner_key(r["OWNER_NAME"]) == "UNKNOWN-OWNER" or not r["MAIL_ADDRESS"]
          or (r["OWNER_PHONE"] and not phone_clean(r["OWNER_PHONE"])) or not re.search(r"\d{5}", r["SITUS_ZIP"])]
variant_keys = {owner_key(v[0]) for v in VARIANTS}
assert sum(1 for r in uniq if owner_key(r["OWNER_NAME"]) in variant_keys) == 20

cols = list(rows[0].keys())
with open(OUT / "county-records.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(allrows)

# Leases: 60 on clean, built properties; 15 end within 12 months (5 <=180 days, 10 in 181-365)
built = [r for r in uniq if r["USE_CODE"] != "Land"]
random.shuffle(built)
TENANTS = ["Test Dental Group", "Fakeway Coffee", "Mockup Logistics", "Sample Fitness", "Demo Insurance Agency",
           "Placeholder Pharmacy", "Stub Labs", "Dummy Data Co-op", "Fixture Furniture", "Null Street Bakery"]
leases = []
for i, r in enumerate(built[:60]):
    if i < 5: end = TODAY + timedelta(days=random.randint(30, 175))
    elif i < 15: end = TODAY + timedelta(days=random.randint(190, 355))
    else: end = TODAY + timedelta(days=random.randint(400, 2200))
    start = end - timedelta(days=365 * random.choice([3, 5, 7, 10]))
    leases.append({"Property__r.APN__c": r["APN"], "Tenant_Name__c": f"{random.choice(TENANTS)} #{i+1}",
                   "Lease_Start__c": start.isoformat(), "Lease_End__c": end.isoformat(),
                   "Monthly_Rent__c": random.randint(18, 160) * 100})
with open(OUT / "leases.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(leases[0].keys())); w.writeheader(); w.writerows(leases)

print(json.dumps({"rows": len(allrows), "unique_apn": len(uniq), "needs_review_expected": len(review),
                  "variant_props": 20, "variant_owners": len(variant_keys), "leases": len(leases),
                  "leases_within_365": 15}))
