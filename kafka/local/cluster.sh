#!/usr/bin/env bash
# Single-machine helper for running both brokers on one host.
#   ./kafka/local/cluster.sh format          # once: format both log dirs with one cluster id
#   ./kafka/local/cluster.sh start 1|2|all
#   ./kafka/local/cluster.sh stop 1|2|all    # stop 2 = simulate VM3 failure
#   ./kafka/local/cluster.sh status
#   ./kafka/local/cluster.sh wipe            # delete local data (fresh cluster)
set -euo pipefail

KAFKA_HOME="${KAFKA_HOME:-$HOME/kafka}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA=/tmp/kafka-data
cmd="${1:-status}"
which="${2:-all}"

ids() { if [ "$which" = all ]; then echo 1 2; else echo "$which"; fi; }

case "$cmd" in
  format)
    mkdir -p "$DATA"
    [ -f "$DATA/cluster.id" ] || "$KAFKA_HOME/bin/kafka-storage.sh" random-uuid > "$DATA/cluster.id"
    for i in 1 2; do
      "$KAFKA_HOME/bin/kafka-storage.sh" format --ignore-formatted \
        -t "$(cat "$DATA/cluster.id")" -c "$DIR/broker$i.properties"
    done
    ;;
  start)
    for i in $(ids); do
      port=$([ "$i" = 1 ] && echo 9092 || echo 9094)
      # setsid detaches the broker so it survives the shell (and a WSL session) exiting.
      LOG_DIR="$DATA/logs$i" setsid "$KAFKA_HOME/bin/kafka-server-start.sh" -daemon "$DIR/broker$i.properties"
      for _ in $(seq 60); do
        (exec 3<>"/dev/tcp/localhost/$port") 2>/dev/null && break
        sleep 1
      done
      echo "started broker $i on port $port (server log: $DATA/logs$i/server.log)"
    done
    ;;
  stop)
    # kafka-server-stop.sh would stop every broker on the host, so match the config file.
    for i in $(ids); do
      pkill -f "broker$i.properties" && echo "stopped broker $i" || echo "broker $i not running"
    done
    ;;
  status)
    for i in 1 2; do
      if pgrep -f "broker$i.properties" >/dev/null; then echo "broker $i: running"; else echo "broker $i: stopped"; fi
    done
    ;;
  wipe)
    rm -rf "$DATA"
    ;;
  *)
    echo "usage: $0 format|start|stop|status|wipe [1|2|all]" >&2
    exit 1
    ;;
esac
