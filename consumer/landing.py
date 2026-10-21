"""Shared helper for consumer1.py and consumer2.py: land a topic into a local JSONL file.

The consumer reads every partition of the topic from the beginning and
writes each message value as one line. It stops once it has caught up with
the end of all partitions and no new message has arrived for --idle-timeout
seconds. The output file is overwritten, so a rerun lands the same data.
"""

import os
import time
from collections import Counter

from kafka import KafkaConsumer, TopicPartition

DEFAULT_BOOTSTRAP = (os.environ.get("KAFKA_BOOTSTRAP_SERVERS") or os.environ.get("BS")
                     or "localhost:9092,localhost:9094")


def add_common_args(parser, topic, output_path):
    parser.add_argument("--bootstrap-servers", default=DEFAULT_BOOTSTRAP,
                        help="comma-separated host:port list (env KAFKA_BOOTSTRAP_SERVERS)")
    parser.add_argument("--topic", default=topic)
    parser.add_argument("--output", default=output_path)
    parser.add_argument("--idle-timeout", type=float, default=10.0,
                        help="stop after this many seconds with no new messages once caught up")
    parser.add_argument("--wait-timeout", type=float, default=120.0,
                        help="how long to wait for the first message before giving up")


def topic_partitions(consumer, topic, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        partitions = consumer.partitions_for_topic(topic)
        if partitions:
            return [TopicPartition(topic, p) for p in sorted(partitions)]
        time.sleep(1)
    raise SystemExit(f"topic '{topic}' not found on the cluster")


def land_topic(bootstrap_servers, topic, output_path, idle_timeout, wait_timeout):
    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_servers.split(","),
        group_id=None,
        enable_auto_commit=False,
    )
    tps = topic_partitions(consumer, topic)
    consumer.assign(tps)
    consumer.seek_to_beginning(*tps)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    per_partition = Counter()
    started = last_message = time.time()
    with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
        while True:
            batch = consumer.poll(timeout_ms=1000)
            for tp, messages in batch.items():
                for message in messages:
                    fh.write(message.value.decode("utf-8") + "\n")
                    per_partition[tp.partition] += 1
            if batch:
                last_message = time.time()
                continue
            if not per_partition and time.time() - started < wait_timeout:
                continue
            if time.time() - last_message < idle_timeout:
                continue
            end = consumer.end_offsets(tps)
            if all(consumer.position(tp) >= end[tp] for tp in tps):
                break
    consumer.close()

    total = sum(per_partition.values())
    print(f"landed {total} records from topic '{topic}' into {output_path}")
    for partition in sorted(per_partition):
        print(f"  partition {partition}: {per_partition[partition]}")
    if total == 0:
        print("warning: no records received")
    return total
