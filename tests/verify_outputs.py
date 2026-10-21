"""Independent check of both Spark jobs using only the Python standard library.

Recomputes the cleaning, dedup, metrics and summaries from the raw dataset
and compares them with the files the Spark jobs wrote. Exits non-zero on any
mismatch.

Usage:
    python tests/verify_outputs.py --raw order.jsonl --metrics outputs/order_metrics.jsonl \
                                   --restaurant outputs/restaurant_summary.csv \
                                   --city outputs/city_summary.csv
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

FIELDS = [
    "order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city",
    "order_timestamp", "accepted_timestamp", "picked_up_timestamp",
    "expected_delivery_timestamp", "delivered_timestamp",
    "distance_km", "order_amount", "delivery_fee", "status",
]
STRINGS = ["order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city", "status"]
TIMESTAMPS = FIELDS[5:10]
NUMBERS = ["distance_km", "order_amount", "delivery_fee"]


def r2(x):
    # Spark's round() is HALF_UP; Python's round() is banker's rounding.
    return float(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_ts(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def why_invalid(line):
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        return "malformed_json", None
    if not isinstance(rec, dict):
        return "malformed_json", None
    for f in STRINGS:
        if not isinstance(rec.get(f), str) or not rec[f].strip():
            return f"missing_or_invalid:{f}", rec
    for f in NUMBERS:
        if isinstance(rec.get(f), bool) or not isinstance(rec.get(f), (int, float)):
            return f"missing_or_invalid:{f}", rec
    for f in TIMESTAMPS:
        if parse_ts(rec.get(f)) is None:
            return f"invalid_timestamp:{f}", rec
    if rec["distance_km"] <= 0:
        return "distance_km<=0", rec
    if rec["order_amount"] <= 0:
        return "order_amount<=0", rec
    if rec["status"] != "DELIVERED":
        return "status_not_delivered", rec
    return None, rec


def minutes(a, b):
    return (parse_ts(b) - parse_ts(a)).total_seconds() / 60.0


def enrich(rec):
    prep = minutes(rec["accepted_timestamp"], rec["picked_up_timestamp"])
    deliv = minutes(rec["picked_up_timestamp"], rec["delivered_timestamp"])
    fulfil = minutes(rec["order_timestamp"], rec["delivered_timestamp"])
    delay = max(0.0, minutes(rec["expected_delivery_timestamp"], rec["delivered_timestamp"]))
    if delay == 0:
        cat = "ON_TIME"
    elif delay <= 15:
        cat = "SLIGHT_DELAY"
    elif delay <= 30:
        cat = "MODERATE_DELAY"
    else:
        cat = "SEVERE_DELAY"
    return {
        "order_id": rec["order_id"], "customer_id": rec["customer_id"],
        "restaurant_id": rec["restaurant_id"], "delivery_partner_id": rec["delivery_partner_id"],
        "city": rec["city"], "order_amount": float(rec["order_amount"]),
        "delivery_fee": float(rec["delivery_fee"]), "distance_km": float(rec["distance_km"]),
        "preparation_time_min": r2(prep), "delivery_time_min": r2(deliv),
        "fulfillment_time_min": r2(fulfil),
        "delivery_speed_kmph": r2(rec["distance_km"] / (deliv / 60.0)) if deliv else None,
        "delay_min": r2(delay), "delivery_status": "ON_TIME" if delay == 0 else "DELAYED",
        "delay_category": cat,
    }


def summarise(metrics, key, avg_cols):
    groups = defaultdict(list)
    for m in metrics:
        groups[m[key]].append(m)
    out = {}
    for k, rows in groups.items():
        n = len(rows)
        delayed = sum(1 for m in rows if m["delivery_status"] == "DELAYED")
        row = {"order_count": n}
        for out_col, src in avg_cols:
            row[out_col] = r2(sum(m[src] for m in rows) / n)
        row["delayed_order_count"] = delayed
        row["delay_rate_pct"] = r2(100.0 * delayed / n)
        out[k] = row
    return out


def compare_csv(path, key, expected, failures):
    with open(path, newline="", encoding="utf-8") as fh:
        actual = {row[key]: row for row in csv.DictReader(fh)}
    if set(actual) != set(expected):
        failures.append(f"{path}: groups differ {sorted(actual)} vs {sorted(expected)}")
        return
    for k, exp in expected.items():
        for col, val in exp.items():
            if abs(float(actual[k][col]) - val) > 1e-9:
                failures.append(f"{path}: {k}.{col} spark={actual[k][col]} python={val}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", default="order.jsonl")
    p.add_argument("--metrics", default="outputs/order_metrics.jsonl")
    p.add_argument("--restaurant", default="outputs/restaurant_summary.csv")
    p.add_argument("--city", default="outputs/city_summary.csv")
    args = p.parse_args()

    lines = [l for l in open(args.raw, encoding="utf-8") if l.strip()]
    reasons, valid = Counter(), []
    for i, line in enumerate(lines, 1):
        reason, rec = why_invalid(line)
        if reason:
            reasons[reason] += 1
            print(f"  dropped line {i:>2}: {reason:<38} order_id={rec.get('order_id') if rec else None}")
        else:
            valid.append(rec)

    seen, unique, dupes = set(), [], []
    for rec in valid:
        key = tuple(rec.get(f) for f in FIELDS)
        if key in seen:
            dupes.append(rec["order_id"])
        else:
            seen.add(key)
            unique.append(rec)

    print(f"\nraw records: {len(lines)}")
    print(f"dropped by cleaning: {sum(reasons.values())}  {dict(sorted(reasons.items()))}")
    print(f"valid: {len(valid)}; exact duplicates removed: {len(dupes)} {sorted(dupes)}")
    print(f"expected enriched records: {len(unique)}")

    failures = []
    expected = {m["order_id"]: m for m in map(enrich, unique)}
    if len(expected) != len(unique):
        failures.append("python check assumes unique order_ids after dedup; they are not")
    actual = {}
    for line in open(args.metrics, encoding="utf-8"):
        m = json.loads(line)
        actual[m["order_id"]] = m
    if set(actual) != set(expected):
        failures.append(f"order_ids differ: only spark={sorted(set(actual) - set(expected))} "
                        f"only python={sorted(set(expected) - set(actual))}")
    for oid in set(actual) & set(expected):
        if list(actual[oid]) != list(expected[oid]):
            failures.append(f"{oid}: field order {list(actual[oid])}")
        for col, val in expected[oid].items():
            if actual[oid].get(col) != val:
                failures.append(f"{oid}.{col}: spark={actual[oid].get(col)} python={val}")

    metrics = list(expected.values())
    compare_csv(args.restaurant, "restaurant_id", summarise(metrics, "restaurant_id", [
        ("avg_order_amount", "order_amount"),
        ("avg_preparation_time_min", "preparation_time_min"),
        ("avg_delivery_time_min", "delivery_time_min")]), failures)
    compare_csv(args.city, "city", summarise(metrics, "city", [
        ("avg_order_amount", "order_amount"),
        ("avg_delivery_time_min", "delivery_time_min")]), failures)

    if failures:
        print("\nMISMATCHES:")
        for f in failures:
            print("  " + f)
        sys.exit(1)
    print(f"\nOK: {len(actual)} enriched records and both summaries match the Python recomputation.")


if __name__ == "__main__":
    main()
