#!/usr/bin/env bash
# Practice the whole demo on one machine (WSL), steps 0-32 of DEMO_RUNBOOK.md.
# The local two-broker cluster stands in for VM2 + VM3; every VM's commands run here.
#   bash practice_alone.sh
# Stops at the first failing step.
set -e
cd "$(dirname "$0")"

step() { echo; echo "================ Step $1 · $2"; }

step 0 "EVERYONE · terminal setup"
if [ -f .venv-wsl/bin/activate ]; then source .venv-wsl/bin/activate; else source .venv/bin/activate; fi
export KAFKA_HOME="${KAFKA_HOME:-$HOME/kafka}"
# Kafka 4.x needs Java 17+; ~/.bashrc may point JAVA_HOME at an older JDK.
[ -d /usr/lib/jvm/java-21-openjdk-amd64 ] && export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
# Use the venv's PySpark, not a system Spark/Hadoop install that ~/.bashrc may point at.
unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON
export B1=localhost:9092 B2=localhost:9094
export BS=$B1 BOOTSTRAP=$B1,$B2 KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
under_replicated() { "$KAFKA_HOME/bin/kafka-topics.sh" --bootstrap-server $B1 --describe --under-replicated-partitions; }

step "1-2" "VM2 + VM3 · start both brokers"
./kafka/local/cluster.sh format > /dev/null
./kafka/local/cluster.sh start all

step 3 "VM2 · both brokers joined (expect id 1 and id 2)"
"$KAFKA_HOME/bin/kafka-broker-api-versions.sh" --bootstrap-server $B1 | grep "id:"

step 4 "VM2 · fresh topics"
./kafka/topics.sh delete; sleep 5; ./kafka/topics.sh create

step 5 "VM1 + VM4 · clear old outputs"
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test
mkdir -p outputs/failover_test outputs/recovery_test

step 6 "VM1 + VM4 · brokers reachable"
nc -zv localhost 9092; nc -zv localhost 9094

step 7 "VM1 · Producer 1 (expect 62)"
python producer/producer1.py --input order.jsonl
step 8 "VM4 · Consumer 1 (expect 62)"
python consumer/consumer1.py --output outputs/orders_landed.jsonl
step 9 "VM4 · Spark Job 1 (expect 44)"
python spark/spark_job1.py --input outputs/orders_landed.jsonl --output outputs/order_metrics.jsonl
step 10 "VM4 · Producer 2 (expect 44)"
python producer/producer2.py --input outputs/order_metrics.jsonl
step 11 "VM1 · Consumer 2 (expect 44)"
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl
step 12 "VM1 · Spark Job 2 (expect 6 + 4 rows)"
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl --output-dir outputs
step 13 "VM1 · verify and show results (expect OK)"
python tests/verify_outputs.py --raw order.jsonl --metrics outputs/order_metrics_landed.jsonl
cat outputs/restaurant_summary.csv outputs/city_summary.csv

step 14 "VM2 · before failure (Isr 1,2; under-replicated list empty)"
./kafka/topics.sh describe
under_replicated
step 15 "VM3 · stop broker 2"
./kafka/local/cluster.sh stop 2
step 16 "VM2 · after failure (Leader 1, Isr 1; 4 under-replicated)"
sleep 15
BOOTSTRAP=$B1 ./kafka/topics.sh describe
under_replicated

step 17 "VM1 · Producer 1 with VM3 down (expect 62)"
python producer/producer1.py --bootstrap-servers $B1 --input order.jsonl
step 18 "VM4 · Consumer 1 (expect 124)"
python consumer/consumer1.py --bootstrap-servers $B1 --output outputs/failover_test/orders_landed.jsonl
step 19 "VM4 · Spark Job 1 (expect 44)"
python spark/spark_job1.py --input outputs/failover_test/orders_landed.jsonl --output outputs/failover_test/order_metrics.jsonl
step 20 "VM4 · Producer 2 (expect 44)"
python producer/producer2.py --bootstrap-servers $B1 --input outputs/failover_test/order_metrics.jsonl
step 21 "VM1 · Consumer 2 (expect 88)"
python consumer/consumer2.py --bootstrap-servers $B1 --output outputs/failover_test/order_metrics_landed.jsonl
step 22 "VM1 · Spark Job 2"
python spark/spark_job2.py --input outputs/failover_test/order_metrics_landed.jsonl --output-dir outputs/failover_test
step 23 "VM1 · results unchanged"
diff outputs/restaurant_summary.csv outputs/failover_test/restaurant_summary.csv
diff outputs/city_summary.csv outputs/failover_test/city_summary.csv && echo "SAME RESULTS"

step 24 "VM3 · restart broker 2"
./kafka/local/cluster.sh start 2
step 25 "VM2 · VM3 rejoined (Isr 1,2; under-replicated list empty)"
sleep 15
./kafka/topics.sh describe
under_replicated

step 26 "VM1 · Producer 1 (expect 62)"
python producer/producer1.py --input order.jsonl
step 27 "VM4 · Consumer 1 (expect 186)"
python consumer/consumer1.py --output outputs/recovery_test/orders_landed.jsonl
step 28 "VM4 · Spark Job 1 (expect 44)"
python spark/spark_job1.py --input outputs/recovery_test/orders_landed.jsonl --output outputs/recovery_test/order_metrics.jsonl
step 29 "VM4 · Producer 2 (expect 44)"
python producer/producer2.py --input outputs/recovery_test/order_metrics.jsonl
step 30 "VM1 · Consumer 2 (expect 132)"
python consumer/consumer2.py --output outputs/recovery_test/order_metrics_landed.jsonl
step 31 "VM1 · Spark Job 2"
python spark/spark_job2.py --input outputs/recovery_test/order_metrics_landed.jsonl --output-dir outputs/recovery_test
step 32 "VM1 · results unchanged"
diff outputs/restaurant_summary.csv outputs/recovery_test/restaurant_summary.csv
diff outputs/city_summary.csv outputs/recovery_test/city_summary.csv && echo "SAME RESULTS"

echo; echo "================ Done: all steps passed. Stopping the local brokers."
./kafka/local/cluster.sh stop all
