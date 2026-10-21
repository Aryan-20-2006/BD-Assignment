"""Consumer 2 (VM1): land topic 'order_metrics' into order_metrics_landed.jsonl for Spark Job 2.

    python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl --bootstrap-servers localhost:9092,localhost:9094
"""

import argparse

from landing import add_common_args, land_topic


def main():
    parser = argparse.ArgumentParser(description="Land Kafka topic 'order_metrics' to a local file")
    add_common_args(parser, topic="order_metrics", output_path="outputs/order_metrics_landed.jsonl")
    args = parser.parse_args()
    land_topic(args.bootstrap_servers, args.topic, args.output, args.idle_timeout, args.wait_timeout)


if __name__ == "__main__":
    main()
