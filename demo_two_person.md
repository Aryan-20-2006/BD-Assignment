# Demo commands: backup version (both brokers on Aniket's VM)

Today's setup:

| Person | Plays | Machine | Address |
|---|---|---|---|
| **Aryan** | VM1 (Producer 1, Consumer 2, Spark Job 2) | laptop, WSL | (connects out only) |
| **Aniket** | VM2 **and** VM3 (both brokers + controller) | his Ubuntu VM | broker 1 `10.31.88.79:9092`, broker 2 `10.31.88.79:9094` |
| **Khush** | VM4 (Consumer 1, Spark Job 1, Producer 2) | his Ubuntu VM | (connects out only) |

**If Khush's VM isn't ready** (setup below not done, or a test fails), Aryan runs the
VM4 steps from his laptop instead, using Aryan's step 0 terminal; the commands are the same.

Kruthik's VM couldn't reach the ZeroTier network from his Wi-Fi, so broker 2
runs on Aniket's VM (port 9094) instead. Every step below names who runs it.
When you finish your step, say "done", and the other person goes.

**Rules:** WSL / Linux terminal only (never PowerShell). Step 0 in **every** new
terminal. Copy one whole block at a time. Step 18 is **never** `pkill -9 -f kafka.Kafka`
here: on Aniket's VM that would kill both brokers and the controller.

---

## One-time setup for Khush (VM4), about 15 minutes

In his Ubuntu VM (Ctrl+Alt+T). The `sudo` password is his VM login password.
```bash
sudo apt update
sudo apt install -y git openjdk-21-jre-headless python3-venv python3-pip
cd ~
[ -L ~/BD-Assignment ] && rm ~/BD-Assignment
git clone https://github.com/Aryan-20-2006/BD-Assignment.git ~/BD-Assignment
cd ~/BD-Assignment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import pyspark, kafka; print(pyspark.__version__, kafka.__version__)"
```
**Expect:** the last line prints `4.2.0 2.2.15`.

**Test that VM4 reaches the brokers** (harmless: it only reads the topic into a test file):
```bash
python consumer/consumer1.py --bootstrap-servers 10.31.88.79:9092 --output /tmp/test.jsonl
```
**Expect:** `landed ... records`. If it fails or hangs, Aryan runs the VM4 steps instead.

---

## Before the TA arrives

### Step 0 · Aryan · Terminal setup (every terminal)
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
**Expect:** the prompt starts with `(.venv-wsl)`.

### Step 0 · Aniket · Terminal setup (every terminal)
```bash
cd ~/BD-Assignment
export KAFKA_HOME=~/kafka
export B1=10.31.88.79:9092
export B2=10.31.88.79:9094
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

### Step 0 · Khush (VM4) · Terminal setup (every terminal)
```bash
cd ~/BD-Assignment
git pull
source .venv/bin/activate
export B1=10.31.88.79:9092
export B2=10.31.88.79:9094
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```
**Expect:** the prompt starts with `(.venv)`. If Spark later says
`'JavaPackage' object is not callable`, run
`unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON`.

### Step 1 · Aniket · Broker 1 running?
```bash
pgrep -af broker1.properties
```
If it prints nothing, start it:
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker1.properties
sleep 15
pgrep -af broker1.properties
```

### Step 2 · Aniket · Broker 2 running? (port 9094, on the same VM)
```bash
pgrep -af broker2.properties
```
If it prints nothing, start it:
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties
sleep 30
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server "$BS" | grep "id:"
```
**Expect:** `10.31.88.79:9092 (id: 1` **and** `10.31.88.79:9094 (id: 2`.

### Step 3 · Aniket · Fresh topics
```bash
bash kafka/topics.sh delete
sleep 10
bash kafka/topics.sh create
```
**Expect:** both topics with `PartitionCount: 2`, `ReplicationFactor: 2`, `Isr: 1,2`.
**If it fails:** `only 1 broker(s) are registered` → broker 2 isn't up: step 2.
`Topic 'orders' does not exist as expected` → run `bash kafka/topics.sh create` again.

### Step 4 · Aryan and Khush (VM4) · Clear old outputs (each on their own machine)
```bash
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test
mkdir -p outputs/failover_test outputs/recovery_test
```

### Readiness check · Aryan
```bash
bash tools/team_check.sh
```
**Start with the TA only on `READY`.**

---

## Checkpoint 1: the cluster

### Step 5 · Aniket · Brokers, controller, topics
```bash
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server "$BS" | grep "id:"
$KAFKA_HOME/bin/kafka-metadata-quorum.sh --bootstrap-server "$BS" describe --status
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --list
```
**Expect:** `10.31.88.79:9092 (id: 1` and `10.31.88.79:9094 (id: 2`; `LeaderId: 1`;
`orders` and `order_metrics`.

---

## Checkpoint 2: raw orders

### Step 6 · Aniket · Observer on `orders` (leave it running)
Replace `teamXX` with the team number.
```bash
$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \
    --topic orders --group ta-observer-teamXX-run1 \
    --consumer-property auto.offset.reset=latest \
    --max-messages 3 --timeout-ms 30000
```
**Expect:** it waits; it gives up after 30 s. Say "go" straight away.

### Step 7 · Aryan · Producer 1 (within 30 s of step 6)
```bash
python producer/producer1.py --input order.jsonl
```
**Expect:** `published 62 records`; Aniket's observer prints 3 records and
`Processed a total of 3 messages`.

### Step 8 · Khush (VM4) · Consumer 1
```bash
python consumer/consumer1.py --output outputs/orders_landed.jsonl
```
**Expect:** `landed 62 records`.

### Step 9 · Khush (VM4) · Show the landed file
```bash
wc -l outputs/orders_landed.jsonl && head -n 2 outputs/orders_landed.jsonl
```
**Expect:** `62 outputs/orders_landed.jsonl` and two order lines.

---

## Checkpoint 3: enriched orders

### Step 10 · Khush (VM4) · Spark Job 1
```bash
python spark/spark_job1.py --input outputs/orders_landed.jsonl \
    --output outputs/order_metrics.jsonl
```
**Expect:** `valid records: 48`, `exact duplicates removed: 4`, `enriched records written: 44`.

### Step 11 · Aniket · Observer on `order_metrics` (leave it running)
```bash
$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \
    --topic order_metrics --group ta-observer-teamXX-run2 \
    --consumer-property auto.offset.reset=latest \
    --max-messages 3 --timeout-ms 30000
```
**Expect:** it waits. Say "go".

### Step 12 · Khush (VM4) · Producer 2 (within 30 s, run it ONCE)
```bash
python producer/producer2.py --input outputs/order_metrics.jsonl
```
**Expect:** `published 44 records` (16 / 28); the observer prints 3 records.
**Don't run it twice**: the topic would hold 88 and step 14 would show 88.

### Step 13 · Aryan · Consumer 2
```bash
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl
```
**Expect:** `landed 44 records`.

### Step 14 · Aryan · Show the landed file
```bash
wc -l outputs/order_metrics_landed.jsonl && head -n 2 outputs/order_metrics_landed.jsonl
```
**Expect:** `44 outputs/order_metrics_landed.jsonl`.

### Step 15 · Aryan · Spark Job 2 (the final CSVs)
```bash
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \
    --output-dir outputs
cat outputs/restaurant_summary.csv outputs/city_summary.csv
```
**Expect:** 6 + 4 rows (R01-R06; Bengaluru, Hyderabad, Mumbai, Pune).

### Readiness check · Aryan (before the failure test)
```bash
bash tools/team_check.sh
```
Must be `READY` (every partition `Isr: 1,2`).

---

## Checkpoint 4: broker failure and recovery

### Step 16 · Aniket · Leaders and ISR before
```bash
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Isr: 1,2` / `2,1` on both partitions.

### Step 17 · Aryan · Slow producer (leave it running)
```bash
python producer/producer1.py --file order.jsonl --delay 0.5
```
**Expect:** `sent 1/62 -> partition ...` every half second. Say "kill" once a few lines are printed.

### Step 18 · Aniket (as VM3) · Kill broker 2 only
```bash
pkill -9 -f broker2.properties
```
**Never `pkill -9 -f kafka.Kafka` here**: it would kill broker 1 and the controller too.

### Step 19 · Aniket · Leaders and ISR after the failure
```bash
sleep 10
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Leader: 1`, `Isr: 1` on both partitions. Meanwhile Aryan's step 17 pauses
briefly, then reaches `sent 62/62` and `published 62 records`: the pipeline continued.

### Step 20 · Aniket (as VM3) · Restart broker 2 (in a second terminal, leave it open)
Do step 0 in that new terminal first.
```bash
KAFKA_HEAP_OPTS='-Xmx512m -Xms512m' $KAFKA_HOME/bin/kafka-server-start.sh \
    ~/broker2.properties
```
**Expect:** log lines, then `Kafka Server started`. Don't press Ctrl+C or close it.

### Step 21 · Aniket · Leaders and ISR after the restart (first terminal)
```bash
sleep 15
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Isr: 1,2` again (leaders still 1). Don't go on until it says so.

### Readiness check · Aryan (before the election)
```bash
bash tools/team_check.sh
```

### Step 22 · Aniket · Leader election, then check again
```bash
$KAFKA_HOME/bin/kafka-leader-election.sh --bootstrap-server "$BS" \
    --election-type preferred --all-topic-partitions
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Successfully completed leader election`; leaders back to how they were in
step 16. **Demo finished.**

---

## At a glance

| Person | Before the TA | CP1 | CP2 | CP3 | CP4 |
|---|---|---|---|---|---|
| **Aryan** (VM1) | 0, 4, check | – | 7 | 13, 14, 15, check | 17, checks |
| **Aniket** (VM2 + VM3) | 0, 1, 2, 3 | 5 | 6 | 11 | 16, 18, 19, 20, 21, 22 |
| **Khush** (VM4) | one-time setup, 0, 4 | – | 8, 9 | 10, 12 | – |

**Kruthik (Member 3)** explains VM3's role and the failure test (steps 18 and 20) to the
TA while Aniket types them, and answers the viva questions on broker 2.

**If the TA asks** why broker 2 is on VM2's machine: Kruthik's VM couldn't reach the
ZeroTier network from his Wi-Fi today ("Destination Host Unreachable"), so broker 2
runs as a second process on port 9094 with its own storage and node ID 2. The
replication and failover behaviour is identical: two brokers, two copies, and
killing broker 2 still moves leadership to broker 1.
