#!/usr/bin/env bash
# Is the team cluster ready? Run from Member 1's laptop (WSL), with step 0 done:
#   bash tools/team_check.sh
# Uses B1 / B2 from step 0 (defaults: VM2 10.31.88.79:9092, VM3 10.31.88.161:9092).
B1=${B1:-10.31.88.79:9092}
B2=${B2:-10.31.88.161:9092}
KAFKA_HOME=${KAFKA_HOME:-$HOME/kafka}
[ -d /usr/lib/jvm/java-21-openjdk-amd64 ] && export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
K=$KAFKA_HOME/bin
fails=0
pass() { echo "  PASS  $*"; }
fail() { echo "  FAIL  $*"; fails=$((fails + 1)); }

echo "== 1. Network (ZeroTier)"
for hp in "$B1" "$B2"; do
  h=${hp%:*}; p=${hp#*:}
  if ping -c 2 -W 2 "$h" > /dev/null 2>&1; then pass "ping $h"; else fail "ping $h (machine off, asleep, or ZeroTier down)"; fi
  r=$(timeout 6 nc -zv -w 5 "$h" "$p" 2>&1 | tail -1)
  case "$r" in
    *succeeded*) pass "Kafka port $hp open" ;;
    *refused*)   fail "Kafka port $hp refused (broker not running)" ;;
    *)           fail "Kafka port $hp timed out (firewall: sudo ufw allow in on zt+)" ;;
  esac
done

echo "== 2. Cluster"
brokers=$(timeout 30 "$K/kafka-broker-api-versions.sh" --bootstrap-server "$B1" 2>/dev/null | grep -oE "^[^ ]+ \(id: [0-9]+" )
echo "$brokers" | sed 's/^/        /'
echo "$brokers" | grep -q "^$B1 (id: 1" && pass "broker 1 registered at $B1" || fail "broker 1 not registered at $B1 (localhost? redo box B)"
echo "$brokers" | grep -q "^$B2 (id: 2" && pass "broker 2 registered at $B2" || fail "broker 2 not in the cluster (step 2; same Kafka version on both?)"
leader=$(timeout 30 "$K/kafka-metadata-quorum.sh" --bootstrap-server "$B1" describe --status 2>/dev/null | awk '/LeaderId/{print $2}')
[ "$leader" = "1" ] && pass "controller is node 1 (VM2)" || fail "controller check failed (LeaderId: ${leader:-none})"

echo "== 3. Topics"
desc=$(timeout 30 "$K/kafka-topics.sh" --bootstrap-server "$B1" --describe --topic orders,order_metrics 2>/dev/null | grep "Partition:")
if [ -z "$desc" ]; then
  fail "orders / order_metrics missing (step 3)"
else
  echo "$desc" | awk '{print "        " $2, $4, "Leader", $6, "Isr", $10}'
  echo "$desc" | grep -qE "Isr: (1,2|2,1)" && ! echo "$desc" | grep -qE "Isr: [12]([^,]|$)" \
    && pass "every partition has Isr 1,2" || fail "some partition has only one in-sync copy (broker 2 down or catching up)"
fi

echo
if [ "$fails" -eq 0 ]; then echo "READY: everything is good to go."; else echo "NOT READY: $fails check(s) failed; fix the FAIL lines first."; fi
