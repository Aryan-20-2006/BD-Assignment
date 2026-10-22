"""Producer 2 (VM4): publish Spark Job 1's output to topic 'order_metrics'.

    python producer/producer2.py --input outputs/order_metrics.jsonl --bootstrap-servers localhost:9092,localhost:9094
"""

import argparse
import json

from publish import add_common_args, publish_file


def main():
    parser = argparse.ArgumentParser(description="Publish enriched order metrics to Kafka")
    add_common_args(parser, topic="order_metrics", input_path="outputs/order_metrics.jsonl")
    args = parser.parse_args()
    # Enriched records are valid JSON, so key them by order_id.
    publish_file(args.bootstrap_servers, args.topic, args.input,
                 key_fn=lambda line: json.loads(line)["order_id"], delay=args.delay)


if __name__ == "__main__":
    main()
