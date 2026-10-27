# Distributed Food Ordering System — Command Guide

This file contains the setup and demo commands for the updated **Practice Version** of the Distributed Food Ordering System guide.

## Important notes

- Practice setup: both Kafka brokers run on the same machine, using `10.31.88.79:9092` and `10.31.88.79:9094`.
- If practising alone in WSL, use the local WSL section instead of the shared-machine IP configuration.
- Run commands in the correct member's terminal and in the order shown.
- Do **not** rerun storage-formatting commands on an existing Kafka data directory. Formatting is for a fresh setup only.
- The topic deletion step removes existing topics. Run it only when intentionally resetting the practice run.
- Replace `teamXX` with your actual team number in observer commands.

---

# Part 1 — One-time setup

## Step A — Get the repository

Run on the Linux/Ubuntu machine. If `~/BD-Assignment` already exists, skip the clone and use Step A2.

```bash
sudo apt install -y git
cd ~
[ -L ~/BD-Assignment ] && rm ~/BD-Assignment
git clone https://github.com/Aryan-20-2006/BD-Assignment.git ~/BD-Assignment
ls ~/BD-Assignment/kafka
```

## Step A2 — Update the repository

Run before each practice session.

```bash
cd ~/BD-Assignment
git pull
```

## Step B — Member 2: Configure broker 1

One-time setup only. Do not run the formatting commands again if broker 1 storage is already initialized and contains data.

```bash
export KAFKA_HOME=~/kafka
cd ~/BD-Assignment
$KAFKA_HOME/bin/kafka-server-stop.sh
while pgrep -f kafka.Kafka > /dev/null; do sleep 1; done
sed -e "s/VM2_ADDRESS/10.31.88.79/g" -e "s#/var/lib/kafka/data#$HOME/kafka-data#" \
    kafka/vm/vm2-broker1.properties > ~/broker1.properties
grep -E "voters|advertised|log.dirs" ~/broker1.properties
$KAFKA_HOME/bin/kafka-storage.sh random-uuid > ~/cluster.id
cat ~/cluster.id
```

Initialize storage only if this is a fresh setup with an empty, unformatted data directory:

```bash
$KAFKA_HOME/bin/kafka-storage.sh format -t "$(cat ~/cluster.id)" -c ~/broker1.properties
sudo ufw allow in on zt+
```

Keep the cluster ID saved. Broker 2 must use the same cluster ID.

## Step C — Configure broker 2 on the same machine

Initialize storage only for a fresh setup. If broker 2 is already formatted with the current cluster ID, skip the format command.

```bash
cd ~/BD-Assignment
sed -e "s/VM2_ADDRESS/10.31.88.79/g" -e "s/VM3_ADDRESS:9092/10.31.88.79:9094/" \
    -e "s#0.0.0.0:9092#0.0.0.0:9094#" -e "s#/var/lib/kafka/data#$HOME/kafka-data2#" \
    kafka/vm/vm3-broker2.properties > ~/broker2.properties
grep -E "listeners|voters|log.dirs" ~/broker2.properties
```

Fresh storage only:

```bash
$KAFKA_HOME/bin/kafka-storage.sh format -t "$(cat ~/cluster.id)" -c ~/broker2.properties
```

Check that the generated configuration uses port `9094`, advertises `10.31.88.79:9094`, and stores data under `~/kafka-data2`.

## Step D — Member 4: Install Java and Python packages

Run on the machine that executes Consumer 1 and Spark Job 1.

```bash
sudo apt update
sudo apt install -y openjdk-21-jre-headless python3-venv python3-pip
java -version
cd ~/BD-Assignment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import pyspark, kafka; print(pyspark.__version__, kafka.__version__)"
```

Expected package versions in the guide: PySpark `4.2.0`, kafka-python `2.2.15`.

---

# Part 2 — Step 0: Prepare terminals

Run the appropriate block in every new terminal.

## Member 1 — WSL laptop

```bash
cd /mnt/c/Users/Aryan/Desktop/BD-Assignment
source .venv-wsl/bin/activate
export KAFKA_HOME=~/kafka
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON
export B1=10.31.88.79:9092
export B2=10.31.88.79:9094
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

## Members 2 and 3 — Kafka machine

```bash
cd ~/BD-Assignment
git pull
export KAFKA_HOME=~/kafka
export B1=10.31.88.79:9092
export B2=10.31.88.79:9094
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

## Member 4 — Consumer 1 / Spark Job 1 machine

```bash
cd ~/BD-Assignment
git pull
source .venv/bin/activate
export KAFKA_HOME=~/kafka
export B1=10.31.88.79:9092
export B2=10.31.88.79:9094
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

---

# Part 3 — Demo steps 1–5: Start Kafka and create topics

## Step 1 — Start broker 1

Run on the shared Kafka machine.

```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker1.properties
```

## Step 2 — Start broker 2

Run on the same machine, in a separate terminal if needed.

```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties
```

## Step 3 — Create fresh topics

Run on the Kafka machine after both brokers have started.

> **Warning:** The delete command removes existing topics. Use it only when intentionally resetting the practice run.

```bash
bash kafka/topics.sh delete
sleep 10
bash kafka/topics.sh create
```

Expected: `orders` and `order_metrics`, each with 2 partitions and replication factor 2.

## Step 4 — Clear old outputs

Run on Member 1 and Member 4 machines, in their respective project directories.

```bash
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test
mkdir -p outputs/failover_test outputs/recovery_test
```

## Step 5 — Verify the cluster

Run on the Kafka machine.

```bash
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server "$BS" | grep "id:"
$KAFKA_HOME/bin/kafka-metadata-quorum.sh --bootstrap-server "$BS" describe --status
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --list
```

Expected: broker IDs `1` and `2`, `LeaderId: 1`, and both topic names.

---

# Part 4 — Checkpoint 2: Raw orders (62 records)

## Step 6 — Start the `orders` observer

Run on the Kafka machine. Replace `teamXX` with your actual team number. Keep it running and immediately start Step 7.

```bash
$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \
    --topic orders --group ta-observer-teamXX-run1 \
    --consumer-property auto.offset.reset=latest \
    --max-messages 3 --timeout-ms 30000
```

## Step 7 — Producer 1

Run on Member 1.

```bash
python producer/producer1.py --input order.jsonl
```

Expected: 62 records published.

## Step 8 — Consumer 1

Run on Member 4.

```bash
python consumer/consumer1.py --output outputs/orders_landed.jsonl
```

Expected: 62 records landed.

## Step 9 — Verify the raw file

Run on Member 4.

```bash
wc -l outputs/orders_landed.jsonl && head -n 2 outputs/orders_landed.jsonl
```

Expected: 62 lines.

---

# Part 5 — Checkpoint 3: Clean, enrich, and summarize

## Step 10 — Spark Job 1

Run on Member 4.

```bash
python spark/spark_job1.py --input outputs/orders_landed.jsonl \
    --output outputs/order_metrics.jsonl
```

Expected: 44 enriched records.

## Step 11 — Start the `order_metrics` observer

Run on the Kafka machine. Replace `teamXX` with your team number and immediately run Step 12.

```bash
$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \
    --topic order_metrics --group ta-observer-teamXX-run2 \
    --consumer-property auto.offset.reset=latest \
    --max-messages 3 --timeout-ms 30000
```

## Step 12 — Producer 2

Run on Member 4.

```bash
python producer/producer2.py --input outputs/order_metrics.jsonl
```

Expected: 44 records published.

## Step 13 — Consumer 2

Run on Member 1.

```bash
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl
```

Expected: 44 records landed.

## Step 14 — Verify the enriched file

Run on Member 1.

```bash
wc -l outputs/order_metrics_landed.jsonl && head -n 2 outputs/order_metrics_landed.jsonl
```

Expected: 44 lines.

## Step 15 — Spark Job 2

Run on Member 1.

```bash
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \
    --output-dir outputs
```

Display both CSV reports:

```bash
cat outputs/restaurant_summary.csv outputs/city_summary.csv
```

Expected: 6 restaurant rows and 4 city rows.

---

# Part 6 — Checkpoint 4: Broker failure and recovery

Do these steps in order. Do not stop broker 1, because it also runs the controller in this practice setup.

## Step 16 — Check ISR before failure

Run on the Kafka machine.

```bash
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```

Expected: both partitions have ISR containing brokers `1` and `2`.

## Step 17 — Start the slow producer

Run on Member 1 and leave it running.

```bash
python producer/producer1.py --file order.jsonl --delay 0.5
```

## Step 18 — Kill broker 2

Run on the shared Kafka machine while Step 17 is still sending.

```bash
pkill -9 -f broker2.properties
```

This is specifically for the practice setup with both brokers on one machine. Do not use `pkill -9 -f kafka.Kafka` here; that could kill both brokers.

## Step 19 — Verify the cluster during failure

Run on the Kafka machine.

```bash
sleep 10
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```

Expected: leader `1`, ISR containing only `1`.

## Step 20 — Restart broker 2

Run in a new terminal on the Kafka machine. Perform Step 0 in that terminal first, then run the command below.

```bash
KAFKA_HEAP_OPTS='-Xmx512m -Xms512m' $KAFKA_HOME/bin/kafka-server-start.sh \
    ~/broker2.properties
```

Leave this terminal open so logs remain visible.

## Step 21 — Verify recovery

In another terminal on the Kafka machine.

```bash
sleep 15
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```

Expected: ISR contains brokers `1` and `2` again. Wait for this before Step 22.

## Step 22 — Preferred leader election

Run on the Kafka machine.

```bash
$KAFKA_HOME/bin/kafka-leader-election.sh --bootstrap-server "$BS" \
    --election-type preferred --all-topic-partitions
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```

Expected: successful election and leaders restored to their preferred brokers.

---

# Part 7 — Practising alone on one laptop (local WSL cluster)

If practising everything on one laptop instead of connecting to the shared practice machine, use this configuration instead of the `10.31.88.79` addresses.

## Local Step 0

```bash
cd /mnt/c/Users/Aryan/Desktop/BD-Assignment
source .venv-wsl/bin/activate
export KAFKA_HOME=~/kafka
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON
export B1=localhost:9092
export B2=localhost:9094
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

## Start the local cluster

Run from the repository directory.

```bash
bash kafka/local/cluster.sh format
bash kafka/local/cluster.sh start 1
bash kafka/local/cluster.sh start 2
```

Then use the same topic creation, verification, pipeline, and recovery steps above, substituting local broker startup/restart commands as shown below.

Start broker 1:

```bash
bash kafka/local/cluster.sh start 1
```

Start broker 2:

```bash
bash kafka/local/cluster.sh start 2
```

Restart broker 2 after failure:

```bash
bash kafka/local/cluster.sh start 2
```

Stop the local cluster after finishing:

```bash
bash kafka/local/cluster.sh stop all
```

> Use this local-cluster workflow only if you are practising with the repository's local setup. Do not mix its storage and broker configuration with the shared practice brokers.

---

# Final checklist

| Checkpoint | Expected result |
|---|---|
| Kafka cluster | Brokers 1 and 2; both topics have 2 partitions and replication factor 2 |
| Raw orders | 62 records published and landed |
| Spark Job 1 | 62 → 48 valid → 44 after deduplication |
| Enriched orders | 44 records published and landed |
| Spark Job 2 | 6 restaurant rows and 4 city rows |
| Failure test | ISR `1,2` → `1` → `1,2`; preferred leader election succeeds |
