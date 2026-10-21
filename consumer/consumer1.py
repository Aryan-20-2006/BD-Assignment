"""Consumer 1 (VM4): land topic 'orders' into orders_landed.jsonl for Spark Job 1.

    python consumer/consumer1.py --output outputs/orders_landed.jsonl --bootstrap-servers localhost:9092,localhost:9094
"""

import argparse

from landing import add_common_args, land_topic


def main():
    parser = argparse.ArgumentParser(description="Land Kafka topic 'orders' to a local file")
    add_common_args(parser, topic="orders", output_path="outputs/orders_landed.jsonl")
    args = parser.parse_args()
    land_topic(args.bootstrap_servers, args.topic, args.output, args.idle_timeout, args.wait_timeout)


if __name__ == "__main__":
    main()
