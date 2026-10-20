"""
Generate a synthetic facilities work-order dataset for a fictional
multi-region grocery retailer.

All data is randomly generated. No real company, store, or vendor data is used.

Outputs (written to ../data/):
    stores.csv        - one row per store
    vendors.csv       - one row per service vendor
    work_orders.csv   - one row per work order (~45k rows, Oct 2024 - Sep 2026)

Usage:
    python src/generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
START = pd.Timestamp("2024-10-01")
END = pd.Timestamp("2026-09-30 23:59")
AS_OF = END  # snapshot date: anything not finished by now is still open

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

REGIONS = {
    # region: (store count, relative climate heat factor)
    "Central TX": (24, 1.10),
    "Houston": (26, 1.20),
    "San Antonio": (20, 1.10),
    "DFW": (22, 1.00),
    "Rio Grande Valley": (14, 1.30),
    "West TX": (14, 0.90),
}

FORMATS = {
    # format: (share of stores, sq ft range, base monthly WO rate)
    "Large": (0.35, (90_000, 130_000), 22),
    "Standard": (0.45, (55_000, 90_000), 15),
    "Express": (0.20, (20_000, 55_000), 8),
}

TRADES = {
    # trade: (share of WOs, summer seasonality boost, typical cost $, problem codes)
    "HVAC": (0.20, 0.80, 1_400, ["No Cooling", "Thermostat Fault", "RTU Alarm", "Airflow Low"]),
    "Refrigeration": (0.22, 0.60, 1_800, ["Case Warm", "Walk-in Cooler Alarm", "Compressor Fault", "Ice Buildup"]),
    "Electrical": (0.12, 0.10, 650, ["Lighting Out", "Breaker Trip", "Outlet Dead", "Generator Test Fail"]),
    "Plumbing": (0.13, 0.00, 550, ["Leak", "Clogged Drain", "Water Heater", "Restroom Fixture"]),
    "Doors & Entrances": (0.11, 0.00, 480, ["Auto Door Stuck", "Dock Door Damage", "Lock Failure"]),
    "Roofing": (0.05, 0.30, 2_200, ["Roof Leak", "Storm Damage", "Drain Blocked"]),
    "Fire & Life Safety": (0.06, 0.00, 900, ["Sprinkler Inspection", "Alarm Panel Fault", "Extinguisher Service"]),
    "General Maintenance": (0.11, 0.00, 300, ["Ceiling Tile", "Floor Damage", "Signage", "Paint/Patch"]),
}

PRIORITIES = {
    # priority: (share, SLA hours, cost multiplier)
    "P1 - Emergency": (0.10, 4, 1.8),
    "P2 - Urgent": (0.25, 24, 1.3),
    "P3 - Routine": (0.45, 120, 1.0),
    "P4 - Planned": (0.20, 336, 0.9),
}


def make_stores(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    store_num = 1
    fmt_names = list(FORMATS)
    fmt_probs = [FORMATS[f][0] for f in fmt_names]
    for region, (count, _) in REGIONS.items():
        for _ in range(count):
            fmt = rng.choice(fmt_names, p=fmt_probs)
            lo, hi = FORMATS[fmt][1]
            rows.append(
                {
                    "store_id": f"S{store_num:03d}",
                    "store_name": f"Store {store_num:03d}",
                    "region": region,
                    "store_format": fmt,
                    "sq_ft": int(rng.integers(lo, hi) // 500 * 500),
                    "open_year": int(rng.integers(1978, 2025)),
                }
            )
            store_num += 1
    return pd.DataFrame(rows)


def make_vendors(rng: np.random.Generator) -> pd.DataFrame:
    prefixes = ["Lone Star", "Bluebonnet", "Gulf Coast", "Hill Country", "Pecan", "Red River",
                "Brazos", "Trinity", "Frontier", "Alamo", "Big Sky", "Cypress", "Mesquite"]
    suffixes = {
        "HVAC": "Air Systems", "Refrigeration": "Refrigeration", "Electrical": "Electric",
        "Plumbing": "Plumbing", "Doors & Entrances": "Door Co.", "Roofing": "Roofing",
        "Fire & Life Safety": "Fire Protection", "General Maintenance": "Facility Services",
    }
    vendors_per_trade = {"HVAC": 4, "Refrigeration": 4, "Electrical": 3, "Plumbing": 3,
                         "Doors & Entrances": 3, "Roofing": 2, "Fire & Life Safety": 2,
                         "General Maintenance": 4}
    rows, used, vid = [], set(), 1
    for trade, n in vendors_per_trade.items():
        for _ in range(n):
            while True:
                name = f"{rng.choice(prefixes)} {suffixes[trade]}"
                if name not in used:
                    used.add(name)
                    break
            rows.append(
                {
                    "vendor_id": f"V{vid:02d}",
                    "vendor_name": name,
                    "trade": trade,
                    # hidden performance traits (used only for generation, dropped before saving)
                    "_speed": float(rng.lognormal(0, 0.35)),     # >1 = slower
                    "_quality": float(rng.beta(8, 2)),           # lower = more repeat calls
                    "_price": float(rng.normal(1.0, 0.12)),      # cost multiplier
                }
            )
            vid += 1
    return pd.DataFrame(rows)


def make_work_orders(rng, stores, vendors) -> pd.DataFrame:
    months = pd.date_range(START, END, freq="MS")
    trade_names = list(TRADES)
    trade_probs = np.array([TRADES[t][0] for t in trade_names])
    pri_names = list(PRIORITIES)
    pri_probs = [PRIORITIES[p][0] for p in pri_names]
    vendors_by_trade = {t: g for t, g in vendors.groupby("trade")}

    records = []
    for _, store in stores.iterrows():
        base = FORMATS[store.store_format][2]
        heat = REGIONS[store.region][1]
        age_factor = 1 + max(0, 2026 - store.open_year - 10) * 0.012  # older stores break more
        # each store has a "preferred" vendor per trade (70% of its jobs)
        preferred = {t: rng.choice(g.index) for t, g in vendors_by_trade.items()}

        for m in months:
            summer = 1.0 if m.month in (6, 7, 8, 9) else (0.5 if m.month in (5, 10) else 0.0)
            # seasonal adjustment of the trade mix
            adj = trade_probs * (1 + np.array([TRADES[t][1] for t in trade_names]) * summer * heat)
            adj = adj / adj.sum()
            volume_mult = 1 + 0.25 * summer * heat
            n = rng.poisson(base * age_factor * volume_mult)
            days_in_month = m.days_in_month
            for _ in range(n):
                trade = rng.choice(trade_names, p=adj)
                priority = rng.choice(pri_names, p=pri_probs)
                created = m + pd.Timedelta(minutes=int(rng.integers(0, days_in_month * 24 * 60)))
                if created > END:
                    continue
                g = vendors_by_trade[trade]
                vidx = preferred[trade] if rng.random() < 0.7 else rng.choice(g.index)
                v = vendors.loc[vidx]
                records.append((store, trade, priority, created, v))

    rows = []
    for i, (store, trade, priority, created, v) in enumerate(records, start=1):
        sla_h = PRIORITIES[priority][1]
        # time to dispatch to vendor
        assign_h = rng.exponential(0.5 if priority.startswith("P1") else 4)
        # resolution time centered around ~60% of SLA, scaled by vendor speed, long right tail
        resolve_h = rng.lognormal(np.log(sla_h * 0.6 * v._speed), 0.65)
        if trade == "Roofing":
            resolve_h *= 1.4  # roofs wait on weather and materials
        if rng.random() < 0.03:
            resolve_h *= rng.uniform(6, 20)  # stuck: waiting on parts, quotes, or approvals
        assigned = created + pd.Timedelta(hours=assign_h)
        completed = assigned + pd.Timedelta(hours=resolve_h)

        cancelled = rng.random() < 0.03
        if cancelled:
            status, completed_at = "Cancelled", pd.NaT
        elif completed > AS_OF:
            status = "In Progress" if assigned <= AS_OF else "Open"
            completed_at = pd.NaT
        else:
            status, completed_at = "Completed", completed

        base_cost = TRADES[trade][2] * PRIORITIES[priority][2]
        nte = round(base_cost * 1.5 / 50) * 50  # not-to-exceed approval amount
        invoice = np.nan
        if status == "Completed":
            invoice = round(float(rng.gamma(4, base_cost * v._price / 4)), 2)

        rows.append(
            {
                "work_order_id": f"WO{i:06d}",
                "store_id": store.store_id,
                "vendor_id": v.vendor_id,
                "trade": trade,
                "problem_code": rng.choice(TRADES[trade][3]),
                "priority": priority,
                "sla_hours": sla_h,
                "status": status,
                "created_at": created,
                "assigned_at": assigned if assigned <= AS_OF and not cancelled else pd.NaT,
                "completed_at": completed_at,
                "nte_amount": nte,
                "invoice_amount": invoice,
                "_quality": v._quality,
            }
        )

    wo = pd.DataFrame(rows)
    wo["_uid"] = np.arange(len(wo))
    wo["_recall_of_uid"] = np.nan

    # inject "repeat calls": poor-quality vendors trigger a follow-up WO at the same store/trade
    done = wo[wo.status == "Completed"]
    repeat_mask = rng.random(len(done)) > done["_quality"].to_numpy() + 0.10
    repeats = done[repeat_mask].copy()
    repeats["_recall_of_uid"] = repeats["_uid"]
    repeats["_uid"] = np.arange(len(wo), len(wo) + len(repeats))
    gap = pd.to_timedelta(rng.integers(1, 30 * 24, len(repeats)), unit="h")
    repeats["created_at"] = repeats["completed_at"] + gap
    repeats = repeats[repeats.created_at <= AS_OF]
    repeats["assigned_at"] = repeats["created_at"] + pd.Timedelta(hours=2)
    repeats["completed_at"] = repeats["assigned_at"] + pd.to_timedelta(
        rng.lognormal(np.log(24), 0.6, len(repeats)), unit="h")
    open_mask = repeats["completed_at"] > AS_OF
    repeats.loc[open_mask, ["completed_at", "invoice_amount"]] = [pd.NaT, np.nan]
    repeats["status"] = np.where(open_mask, "In Progress", "Completed")
    wo = pd.concat([wo, repeats], ignore_index=True)

    # data-quality noise a real analyst would have to handle
    noise = rng.random(len(wo))
    wo.loc[noise < 0.004, "problem_code"] = None                       # missing codes
    wo.loc[(noise >= 0.004) & (noise < 0.006), "trade"] = wo["trade"].str.upper()  # inconsistent casing

    wo = wo.sort_values("created_at").reset_index(drop=True)
    wo["work_order_id"] = [f"WO{i:06d}" for i in range(1, len(wo) + 1)]
    uid_to_id = dict(zip(wo["_uid"], wo["work_order_id"]))
    # a recall = vendor called back to the same store/trade because the original fix didn't hold
    wo["recall_of_work_order_id"] = wo["_recall_of_uid"].map(uid_to_id)
    wo = wo.drop(columns=["_quality", "_uid", "_recall_of_uid"])
    for col in ("created_at", "assigned_at", "completed_at"):
        wo[col] = pd.to_datetime(wo[col]).dt.floor("min")
    return wo


def main() -> None:
    rng = np.random.default_rng(SEED)
    DATA_DIR.mkdir(exist_ok=True)

    stores = make_stores(rng)
    vendors = make_vendors(rng)
    work_orders = make_work_orders(rng, stores, vendors)

    stores.to_csv(DATA_DIR / "stores.csv", index=False)
    vendors.drop(columns=[c for c in vendors if c.startswith("_")]).to_csv(
        DATA_DIR / "vendors.csv", index=False)
    work_orders.to_csv(DATA_DIR / "work_orders.csv", index=False)

    print(f"stores:      {len(stores):>7,}")
    print(f"vendors:     {len(vendors):>7,}")
    print(f"work_orders: {len(work_orders):>7,}")
    print(work_orders.status.value_counts().to_string())


if __name__ == "__main__":
    main()
