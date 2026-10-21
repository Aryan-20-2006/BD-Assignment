"""Spark Job 1 - Order Enrichment (VM4).

Reads orders_landed.jsonl, applies the cleaning rules and exact-duplicate
removal from the spec, computes the delivery metrics and writes
order_metrics.jsonl (one JSON object per line).

Usage:
    python spark/spark_job1.py --input outputs/orders_landed.jsonl \
                               --output outputs/order_metrics.jsonl
"""

import argparse
import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

STRING_FIELDS = ["order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city", "status"]
TIMESTAMP_FIELDS = [
    "order_timestamp",
    "accepted_timestamp",
    "picked_up_timestamp",
    "expected_delivery_timestamp",
    "delivered_timestamp",
]
NUMERIC_FIELDS = ["distance_km", "order_amount", "delivery_fee"]

# Input schema in the order given by the spec.
INPUT_COLUMNS = [
    "order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city",
    "order_timestamp", "accepted_timestamp", "picked_up_timestamp",
    "expected_delivery_timestamp", "delivered_timestamp",
    "distance_km", "order_amount", "delivery_fee", "status",
]

# Enriched schema in the order given by the spec.
OUTPUT_COLUMNS = [
    "order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city",
    "order_amount", "delivery_fee", "distance_km", "preparation_time_min",
    "delivery_time_min", "fulfillment_time_min", "delivery_speed_kmph",
    "delay_min", "delivery_status", "delay_category",
]

TIMESTAMP_FORMAT = "yyyy-MM-dd HH:mm:ss"
CORRUPT = "_corrupt_record"


def input_schema():
    fields = []
    for name in INPUT_COLUMNS:
        dtype = DoubleType() if name in NUMERIC_FIELDS else StringType()
        fields.append(StructField(name, dtype, True))
    fields.append(StructField(CORRUPT, StringType(), True))
    return StructType(fields)


def minutes_between(start_col, end_col):
    return (F.unix_timestamp(end_col) - F.unix_timestamp(start_col)) / 60.0


def drop_reason():
    """First cleaning rule a record fails, or null if it is valid.

    Used both to filter and to print a per-reason report.
    """
    reason = F.when(F.col(CORRUPT).isNotNull(), F.lit("malformed_json"))
    for name in STRING_FIELDS:
        reason = reason.when(
            F.col(name).isNull() | (F.trim(F.col(name)) == ""),
            F.lit(f"missing_or_invalid:{name}"),
        )
    for name in NUMERIC_FIELDS:
        reason = reason.when(F.col(name).isNull(), F.lit(f"missing_or_invalid:{name}"))
    for name in TIMESTAMP_FIELDS:
        reason = reason.when(F.col(f"{name}_ts").isNull(), F.lit(f"invalid_timestamp:{name}"))
    reason = (
        reason.when(F.col("distance_km") <= 0, F.lit("distance_km<=0"))
        .when(F.col("order_amount") <= 0, F.lit("order_amount<=0"))
        .when(F.col("status") != "DELIVERED", F.lit("status_not_delivered"))
    )
    return reason


def build_spark():
    return (
        SparkSession.builder.appName("spark_job1_order_enrichment")
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        # Timestamps carry no zone; compute all differences in UTC so no DST
        # shift on the host can change a duration.
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def run(input_path, output_path):
    spark = build_spark()
    spark.sparkContext.setLogLevel("ERROR")

    raw = (
        spark.read.schema(input_schema())
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", CORRUPT)
        .json(input_path)
        .cache()  # Spark requires caching before filtering on the corrupt column.
    )
    total = raw.count()

    parsed = raw
    for name in TIMESTAMP_FIELDS:
        parsed = parsed.withColumn(
            f"{name}_ts", F.try_to_timestamp(F.col(name), F.lit(TIMESTAMP_FORMAT))
        )
    parsed = parsed.withColumn("drop_reason", drop_reason()).cache()

    print(f"[job1] input records (non-blank lines): {total}")
    print("[job1] dropped by cleaning rules:")
    for row in (
        parsed.filter(F.col("drop_reason").isNotNull())
        .groupBy("drop_reason").count().orderBy("drop_reason").collect()
    ):
        print(f"         {row['drop_reason']:<40} {row['count']}")

    valid = parsed.filter(F.col("drop_reason").isNull())
    valid_count = valid.count()

    # Exact duplicates: identical on every input field.
    deduped = valid.dropDuplicates(INPUT_COLUMNS)
    deduped_count = deduped.count()
    print(f"[job1] valid records: {valid_count}")
    print(f"[job1] exact duplicates removed: {valid_count - deduped_count}")

    delay_raw = minutes_between(F.col("expected_delivery_timestamp_ts"), F.col("delivered_timestamp_ts"))
    enriched = (
        deduped
        .withColumn("preparation_time_min",
                    minutes_between(F.col("accepted_timestamp_ts"), F.col("picked_up_timestamp_ts")))
        .withColumn("delivery_time_min",
                    minutes_between(F.col("picked_up_timestamp_ts"), F.col("delivered_timestamp_ts")))
        .withColumn("fulfillment_time_min",
                    minutes_between(F.col("order_timestamp_ts"), F.col("delivered_timestamp_ts")))
        # try_divide yields null instead of failing if delivery_time_min is 0.
        .withColumn("delivery_speed_kmph",
                    F.try_divide(F.col("distance_km"), F.col("delivery_time_min") / 60.0))
        .withColumn("delay_min", F.greatest(F.lit(0.0), delay_raw))
        .withColumn("delivery_status",
                    F.when(F.col("delay_min") == 0, "ON_TIME").otherwise("DELAYED"))
        .withColumn(
            "delay_category",
            F.when(F.col("delay_min") == 0, "ON_TIME")
            .when(F.col("delay_min") <= 15, "SLIGHT_DELAY")
            .when(F.col("delay_min") <= 30, "MODERATE_DELAY")
            .otherwise("SEVERE_DELAY"),
        )
    )
    for name in ["preparation_time_min", "delivery_time_min", "fulfillment_time_min",
                 "delivery_speed_kmph", "delay_min"]:
        enriched = enriched.withColumn(name, F.round(F.col(name), 2))

    rows = enriched.select(*OUTPUT_COLUMNS).orderBy("order_id").collect()

    # Written from the driver so the result is exactly one file with the name
    # the spec requires (Spark's writer produces a directory of part files).
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps({c: row[c] for c in OUTPUT_COLUMNS}) + "\n")

    print(f"[job1] enriched records written: {len(rows)} -> {output_path}")
    spark.stop()


def main():
    parser = argparse.ArgumentParser(description="Spark Job 1 - Order Enrichment")
    parser.add_argument("--input", default="outputs/orders_landed.jsonl")
    parser.add_argument("--output", default="outputs/order_metrics.jsonl")
    args = parser.parse_args()
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    run(args.input, args.output)


if __name__ == "__main__":
    main()
