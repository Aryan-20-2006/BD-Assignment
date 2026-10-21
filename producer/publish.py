"""Shared helper for producer1.py and producer2.py: publish a JSONL file to a topic."""

import os
from collections import Counter

from kafka import KafkaProducer

DEFAULT_BOOTSTRAP = (os.environ.get("KAFKA_BOOTSTRAP_SERVERS") or os.environ.get("BS")
                     or "localhost:9092,localhost:9094")


def add_common_args(parser, topic, input_path):
    parser.add_argument("--bootstrap-servers", default=DEFAULT_BOOTSTRAP,
                        help="comma-separated host:port list (env KAFKA_BOOTSTRAP_SERVERS)")
    parser.add_argument("--topic", default=topic)
    parser.add_argument("--input", default=input_path)


def publish_file(bootstrap_servers, topic, input_path, key_fn=None):
    """Send every non-blank line of input_path unchanged as one message.

    key_fn(line) -> str or None picks the message key; None lets the
    partitioner spread messages over the partitions.
    """
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        acks="all",
        retries=10,
        linger_ms=10,
    )
    futures = []
    with open(input_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            key = key_fn(line) if key_fn else None
            futures.append(producer.send(
                topic,
                key=key.encode("utf-8") if key else None,
                value=line.encode("utf-8"),
            ))
    producer.flush()
    per_partition = Counter(f.get(timeout=60).partition for f in futures)
    producer.close()
    print(f"published {len(futures)} records from {input_path} to topic '{topic}'")
    for partition in sorted(per_partition):
        print(f"  partition {partition}: {per_partition[partition]}")
    return len(futures)
