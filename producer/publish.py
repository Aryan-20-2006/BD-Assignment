"""Shared helper for producer1.py and producer2.py: publish a JSONL file to a topic."""

import os
import time
from collections import Counter

from kafka import KafkaProducer

DEFAULT_BOOTSTRAP = (os.environ.get("KAFKA_BOOTSTRAP_SERVERS") or os.environ.get("BS")
                     or "localhost:9092,localhost:9094")


def add_common_args(parser, topic, input_path):
    parser.add_argument("--bootstrap-servers", default=DEFAULT_BOOTSTRAP,
                        help="comma-separated host:port list (env KAFKA_BOOTSTRAP_SERVERS)")
    parser.add_argument("--topic", default=topic)
    parser.add_argument("--input", "--file", dest="input", default=input_path)
    parser.add_argument("--delay", type=float, default=0.0,
                        help="seconds to wait after each record (slow mode for the broker-failure test)")


def publish_file(bootstrap_servers, topic, input_path, key_fn=None, delay=0.0):
    """Send every non-blank line of input_path unchanged as one message.

    key_fn(line) -> str or None picks the message key; None lets the
    partitioner spread messages over the partitions.

    With delay > 0 each record is confirmed and printed before the next one is
    sent, so a broker can be stopped mid-run and the output shows sending carry on.
    """
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        acks="all",
        # Retry long enough to outlast a leader failover (~10 s after a broker is killed).
        retries=30,
        retry_backoff_ms=1000,
        linger_ms=10,
    )
    with open(input_path, encoding="utf-8") as fh:
        lines = [line.rstrip("\r\n") for line in fh]
    lines = [line for line in lines if line.strip()]

    futures = []
    for n, line in enumerate(lines, 1):
        key = key_fn(line) if key_fn else None
        future = producer.send(
            topic,
            key=key.encode("utf-8") if key else None,
            value=line.encode("utf-8"),
        )
        futures.append(future)
        if delay > 0:
            meta = future.get(timeout=120)
            print(f"  sent {n}/{len(lines)} -> partition {meta.partition}, offset {meta.offset}", flush=True)
            time.sleep(delay)
    producer.flush()
    per_partition = Counter(f.get(timeout=120).partition for f in futures)
    producer.close()
    print(f"published {len(futures)} records from {input_path} to topic '{topic}'")
    for partition in sorted(per_partition):
        print(f"  partition {partition}: {per_partition[partition]}")
    return len(futures)
