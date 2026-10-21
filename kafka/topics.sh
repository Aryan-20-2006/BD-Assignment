#!/usr/bin/env bash
# Create, describe or delete the pipeline topics.
#   BOOTSTRAP=localhost:9092 ./kafka/topics.sh create|describe|delete
# On the VMs: BOOTSTRAP=VM2_ADDRESS:9092,VM3_ADDRESS:9092 (or the TA's BS variable)
set -euo pipefail

KAFKA_HOME="${KAFKA_HOME:-$HOME/kafka}"
BOOTSTRAP="${BOOTSTRAP:-${BS:-localhost:9092,localhost:9094}}"
TOPICS=(orders order_metrics)
cmd="${1:-describe}"

topics() { "$KAFKA_HOME/bin/kafka-topics.sh" --bootstrap-server "$BOOTSTRAP" "$@"; }

case "$cmd" in
  create)
    for t in "${TOPICS[@]}"; do
      topics --create --if-not-exists --topic "$t" --partitions 2 --replication-factor 2
    done
    topics --describe --topic orders
    topics --describe --topic order_metrics
    ;;
  describe)
    topics --list
    for t in "${TOPICS[@]}"; do topics --describe --topic "$t"; done
    ;;
  delete)
    for t in "${TOPICS[@]}"; do topics --delete --if-exists --topic "$t"; done
    ;;
  *)
    echo "usage: $0 create|describe|delete" >&2
    exit 1
    ;;
esac
