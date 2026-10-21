"""Producer 1 (VM1): publish the raw dataset to topic 'orders'.

Lines are sent exactly as they appear in the file, dirty records included;
Spark Job 1 on VM4 is responsible for cleaning.

    python producer/producer1.py --input order.jsonl --bootstrap-servers localhost:9092,localhost:9094
"""

import argparse

from publish import add_common_args, publish_file


def main():
    parser = argparse.ArgumentParser(description="Publish raw orders to Kafka")
    add_common_args(parser, topic="orders", input_path="order.jsonl")
    args = parser.parse_args()
    # No key: raw lines may be malformed, so they are not parsed here.
    publish_file(args.bootstrap_servers, args.topic, args.input)


if __name__ == "__main__":
    main()
