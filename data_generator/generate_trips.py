"""
Synthetic Malaysian e-hailing trip generator.

Creates ~100,000 rides across Kuala Lumpur, Selangor and Johor (Jan 2024 - Oct 2026)
and deliberately injects real-world mess so the cleaning job has work to do:
  - ~2% exact duplicate rows
  - ~5% place-name typos (PJ, JB, KL, ...)
  - ~20% of dates in a second format (dd/MM/yyyy HH:mm)
  - ~5% fares stored as text ("RM23.5")
  - ~3% missing fares
  - ~0.5% negative distances
  - ~12% missing ratings

Output: trips_raw.csv
"""
import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)
N = 100000

AREAS = {
    "Kuala Lumpur": ["KLCC", "Bukit Bintang", "Cheras", "Kepong", "Bangsar", "Setapak"],
    "Selangor": ["Petaling Jaya", "Subang Jaya", "Shah Alam", "Puchong", "Klang", "Cyberjaya"],
    "Johor": ["Johor Bahru", "Skudai", "Iskandar Puteri", "Pasir Gudang", "Kulai"],
}
TYPOS = {"Petaling Jaya": ["P. Jaya", "petaling jaya", "PJ"],
         "Johor Bahru": ["JB", "johor bahru", "Johor Baru"],
         "Kuala Lumpur": ["KL", "kuala lumpur"],
         "Shah Alam": ["shah alam", "ShahAlam"]}
SERVICES = {"Economy": (3.0, 0.85), "Premium": (5.0, 1.40), "XL": (6.0, 1.60)}  # (base fare, per km) in RM
PAYMENTS = ["E-Wallet", "Card", "Cash"]
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 4, 8, 9, 6, 4, 4, 5, 4, 4, 5, 7, 9, 9, 7, 5, 4, 3, 2]

start = datetime(2024, 1, 1)
days = (datetime(2026, 10, 31) - start).days


def messy(value):
    return random.choice(TYPOS[value]) if value in TYPOS and random.random() < 0.05 else value


rows = []
for _ in range(N):
    state = random.choices(list(AREAS), weights=[45, 40, 15])[0]
    pickup, dropoff = random.sample(AREAS[state], 2)
    hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    ts = start + timedelta(days=random.randint(0, days), hours=hour, minutes=random.randint(0, 59))
    service = random.choices(list(SERVICES), weights=[75, 15, 10])[0]
    base, per_km = SERVICES[service]
    distance = round(random.uniform(1.5, 30), 2)
    surge = round(random.choice([1.0, 1.0, 1.0, 1.2, 1.5]) if hour in (7, 8, 17, 18, 19) else 1.0, 1)
    fare = round((base + per_km * distance) * surge, 2)

    trip_time = ts.strftime("%d/%m/%Y %H:%M") if random.random() < 0.2 else ts.strftime("%Y-%m-%d %H:%M:%S")
    fare_out = f"RM{fare}" if random.random() < 0.05 else fare
    if random.random() < 0.03:
        fare_out = ""
    if random.random() < 0.005:
        distance = -distance
    rating = random.choices([5, 4, 3, 2, 1, ""], weights=[50, 25, 8, 3, 2, 12])[0]

    rows.append([str(uuid.uuid4())[:8], trip_time, messy(state), messy(pickup), messy(dropoff),
                 service, distance, surge, fare_out, random.choices(PAYMENTS, weights=[50, 25, 25])[0], rating])

rows += random.sample(rows, int(N * 0.02))  # inject duplicates
random.shuffle(rows)

with open("trips_raw.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["trip_id", "trip_datetime", "state", "pickup_area", "dropoff_area",
                "service_type", "distance_km", "surge_multiplier", "fare", "payment_method", "rating"])
    w.writerows(rows)
print(f"Wrote {len(rows)} rows to trips_raw.csv")
