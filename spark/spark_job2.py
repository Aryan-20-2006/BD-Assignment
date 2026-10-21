"""Spark Job 2 - Operations Analytics (VM1).

Reads order_metrics_landed.jsonl, removes exact duplicates and writes
restaurant_summary.csv and city_summary.csv. All calculated numbers are
rounded to 2 decimal places.

Usage:
    python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \
                               --output-dir outputs
"""

import argparse
import csv
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

STRING_COLUMNS = ["order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city",
                  "delivery_status", "delay_category"]

# Enriched schema in the order given by the spec.
INPUT_COLUMNS = [
    "order_id", "customer_id", "restaurant_id", "delivery_partner_id", "city",
    "order_amount", "delivery_fee", "distance_km", "preparation_time_min",
    "delivery_time_min", "fulfillment_time_min", "delivery_speed_kmph",
    "delay_min", "delivery_status", "delay_category",
]

RESTAURANT_COLUMNS = ["restaurant_id", "order_count", "avg_order_amount", "avg_preparation_time_min",
                      "avg_delivery_time_min", "delayed_order_count", "delay_rate_pct"]
CITY_COLUMNS = ["city", "order_count", "avg_order_amount", "avg_delivery_time_min",
                "delayed_order_count", "delay_rate_pct"]


def input_schema():
    return StructType([
        StructField(name, StringType() if name in STRING_COLUMNS else DoubleType(), True)
        for name in INPUT_COLUMNS
    ])


def build_spark():
    return (
        SparkSession.builder.appName("spark_job2_operations_analytics")
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def delayed_count():
    return F.sum(F.when(F.col("delivery_status") == "DELAYED", 1).otherwise(0)).cast("long")


def delay_rate():
    return F.round(100.0 * F.col("delayed_order_count") / F.col("order_count"), 2)


def write_csv(rows, columns, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row[c] for c in columns])
    print(f"[job2] {len(rows)} rows -> {path}")


def run(input_path, output_dir):
    spark = build_spark()
    spark.sparkContext.setLogLevel("ERROR")

    records = spark.read.schema(input_schema()).option("mode", "DROPMALFORMED").json(input_path)
    total = records.count()
    # Exact duplicates: identical on every enriched field.
    orders = records.dropDuplicates(INPUT_COLUMNS).cache()
    print(f"[job2] input records: {total}, exact duplicates removed: {total - orders.count()}")

    restaurant = (
        orders.groupBy("restaurant_id")
        .agg(
            F.count("*").alias("order_count"),
            F.round(F.avg("order_amount"), 2).alias("avg_order_amount"),
            F.round(F.avg("preparation_time_min"), 2).alias("avg_preparation_time_min"),
            F.round(F.avg("delivery_time_min"), 2).alias("avg_delivery_time_min"),
            delayed_count().alias("delayed_order_count"),
        )
        .withColumn("delay_rate_pct", delay_rate())
        .orderBy("restaurant_id")
    )

    city = (
        orders.groupBy("city")
        .agg(
            F.count("*").alias("order_count"),
            F.round(F.avg("order_amount"), 2).alias("avg_order_amount"),
            F.round(F.avg("delivery_time_min"), 2).alias("avg_delivery_time_min"),
            delayed_count().alias("delayed_order_count"),
        )
        .withColumn("delay_rate_pct", delay_rate())
        .orderBy("city")
    )

    os.makedirs(output_dir, exist_ok=True)
    # Written from the driver so each result is one CSV with the required name.
    write_csv(restaurant.select(*RESTAURANT_COLUMNS).collect(), RESTAURANT_COLUMNS,
              os.path.join(output_dir, "restaurant_summary.csv"))
    write_csv(city.select(*CITY_COLUMNS).collect(), CITY_COLUMNS,
              os.path.join(output_dir, "city_summary.csv"))
    spark.stop()


def main():
    parser = argparse.ArgumentParser(description="Spark Job 2 - Operations Analytics")
    parser.add_argument("--input", default="outputs/order_metrics_landed.jsonl")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()
