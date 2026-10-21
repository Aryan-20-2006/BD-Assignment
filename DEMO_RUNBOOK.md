# Demo runbook

Run the steps **in number order**. Each step says **who** runs it. Wait until a
step has finished, and its owner says "done", before starting the next one.

- **Demo day:** each person runs only the steps with their VM's label.
- **Practising alone:** run every step yourself in one WSL terminal. A few
  steps have a different "Alone" command; use that one.

Installation is in `README.md` (Prerequisites). More detail and
troubleshooting are in `demo_commands.md`.

## Who runs which steps

| VM | Steps |
|---|---|
| **VM1** | 0, 5, 6, 7, 11, 12, 13, 17, 21, 22, 23, 26, 30, 31, 32 |
| **VM2** | 0, 1, 3, 4, 14, 16, 25 |
| **VM3** | 0, 2, 15, 24 |
| **VM4** | 0, 5, 6, 8, 9, 10, 18, 19, 20, 27, 28, 29 |

---

## Part A: Get ready

### Step 0 · EVERYONE · Set up the terminal
Do this in every new terminal.

```bash
cd ~/BD-Assignment                      # VM1 alone/WSL: cd /mnt/c/Users/Aryan/Desktop/BD-Assignment
source .venv/bin/activate               # VM1 and VM4 only (VM1 in WSL: .venv-wsl/bin/activate)
export KAFKA_HOME=~/kafka
```

Then set the broker addresses.

**Demo day** (put in the real ZeroTier IPs):
```bash
export B1=<VM2_ZEROTIER_IP>:9092
export B2=<VM3_ZEROTIER_IP>:9092
```
**Alone:**
```bash
export B1=localhost:9092
export B2=localhost:9094
```
Then, in both cases:
```bash
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

### Step 1 · VM2 · Start broker 1 (and the controller)
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker1.properties
```
Alone: `./kafka/local/cluster.sh format && ./kafka/local/cluster.sh start 1`

### Step 2 · VM3 · Start broker 2
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties
```
Alone: `./kafka/local/cluster.sh start 2`

### Step 3 · VM2 · Check that both brokers joined
```bash
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server $B1 | grep "id:"
```
Expect two lines: `id: 1` and `id: 2`.

### Step 4 · VM2 · Create fresh topics
```bash
./kafka/topics.sh delete; sleep 5; ./kafka/topics.sh create
```
Expect both topics with `PartitionCount: 2`, `ReplicationFactor: 2`, and `Isr` listing 1 and 2.

### Step 5 · VM1 and VM4 · Clear old outputs
```bash
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test
mkdir -p outputs/failover_test outputs/recovery_test
```

### Step 6 · VM1 and VM4 · Check that the brokers are reachable
```bash
nc -zv <VM2_ZEROTIER_IP> 9092; nc -zv <VM3_ZEROTIER_IP> 9092
```
Expect `succeeded` twice. Alone: `nc -zv localhost 9092; nc -zv localhost 9094`

---

## Part B: Main pipeline (these outputs get graded)

### Step 7 · VM1 · Producer 1: send the raw orders
```bash
python producer/producer1.py --input order.jsonl
```
Expect: `published 62 records`.

### Step 8 · VM4 · Consumer 1: save the orders to a file
```bash
python consumer/consumer1.py --output outputs/orders_landed.jsonl
```
Expect: `landed 62 records`.

### Step 9 · VM4 · Spark Job 1: clean and enrich
```bash
python spark/spark_job1.py --input outputs/orders_landed.jsonl --output outputs/order_metrics.jsonl
```
Expect: `valid records: 48`, `exact duplicates removed: 4`, `enriched records written: 44`.

### Step 10 · VM4 · Producer 2: send the cleaned orders
```bash
python producer/producer2.py --input outputs/order_metrics.jsonl
```
Expect: `published 44 records`, partition 0: 16, partition 1: 28.

### Step 11 · VM1 · Consumer 2: save the cleaned orders to a file
```bash
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl
```
Expect: `landed 44 records`.

### Step 12 · VM1 · Spark Job 2: build the reports
```bash
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl --output-dir outputs
```
Expect: `6 rows -> restaurant_summary.csv`, `4 rows -> city_summary.csv`.

### Step 13 · VM1 · Check and show the results
```bash
python tests/verify_outputs.py --raw order.jsonl --metrics outputs/order_metrics_landed.jsonl
cat outputs/restaurant_summary.csv outputs/city_summary.csv
```
Expect: `OK: 44 enriched records and both summaries match ...`

---

## Part C: Failure test, VM3 goes down

### Step 14 · VM2 · Show the topics before the failure
```bash
./kafka/topics.sh describe
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $B1 --describe --under-replicated-partitions
```
Expect `Isr` to list 1 and 2 on every partition. The second command should print nothing.

### Step 15 · VM3 · Stop broker 2
```bash
$KAFKA_HOME/bin/kafka-server-stop.sh
```
Alone: `./kafka/local/cluster.sh stop 2`

### Step 16 · VM2 · Show the topics after the failure (wait 15 s first)
```bash
sleep 15
BOOTSTRAP=$B1 ./kafka/topics.sh describe
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $B1 --describe --under-replicated-partitions
```
Expect `Leader: 1` and `Isr: 1` on every partition. The second command lists all 4 partitions.

**From here until step 23, every Kafka command uses `--bootstrap-servers $B1`, which is VM2 only.**

### Step 17 · VM1 · Producer 1 with VM3 down
```bash
python producer/producer1.py --bootstrap-servers $B1 --input order.jsonl
```
Expect: `published 62 records`, so writes still work.

### Step 18 · VM4 · Consumer 1
```bash
python consumer/consumer1.py --bootstrap-servers $B1 --output outputs/failover_test/orders_landed.jsonl
```
Expect: `landed 124 records` (62 old + 62 new).

### Step 19 · VM4 · Spark Job 1
```bash
python spark/spark_job1.py --input outputs/failover_test/orders_landed.jsonl --output outputs/failover_test/order_metrics.jsonl
```
Expect: still `enriched records written: 44`, because the duplicates are removed.

### Step 20 · VM4 · Producer 2
```bash
python producer/producer2.py --bootstrap-servers $B1 --input outputs/failover_test/order_metrics.jsonl
```
Expect: `published 44 records`.

### Step 21 · VM1 · Consumer 2
```bash
python consumer/consumer2.py --bootstrap-servers $B1 --output outputs/failover_test/order_metrics_landed.jsonl
```
Expect: `landed 88 records` (44 old + 44 new).

### Step 22 · VM1 · Spark Job 2
```bash
python spark/spark_job2.py --input outputs/failover_test/order_metrics_landed.jsonl --output-dir outputs/failover_test
```
Expect: `exact duplicates removed: 44`, then 6 + 4 rows.

### Step 23 · VM1 · Show that the results are unchanged
```bash
diff outputs/restaurant_summary.csv outputs/failover_test/restaurant_summary.csv && diff outputs/city_summary.csv outputs/failover_test/city_summary.csv && echo "SAME RESULTS"
```
Expect: `SAME RESULTS`.

---

## Part D: Recovery, VM3 comes back

### Step 24 · VM3 · Restart broker 2
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties
```
Alone: `./kafka/local/cluster.sh start 2`

### Step 25 · VM2 · Show that VM3 rejoined (wait 15 s first)
```bash
sleep 15
./kafka/topics.sh describe
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $B1 --describe --under-replicated-partitions
```
Expect `Isr` to list 1 and 2 again. The second command prints nothing. (`Leader` may stay 1 for a few minutes; that's normal.)

**From here on, no `--bootstrap-servers` flag: the commands use both brokers again.**

### Step 26 · VM1 · Producer 1
```bash
python producer/producer1.py --input order.jsonl
```
Expect: `published 62 records`.

### Step 27 · VM4 · Consumer 1
```bash
python consumer/consumer1.py --output outputs/recovery_test/orders_landed.jsonl
```
Expect: `landed 186 records`.

### Step 28 · VM4 · Spark Job 1
```bash
python spark/spark_job1.py --input outputs/recovery_test/orders_landed.jsonl --output outputs/recovery_test/order_metrics.jsonl
```
Expect: `enriched records written: 44`.

### Step 29 · VM4 · Producer 2
```bash
python producer/producer2.py --input outputs/recovery_test/order_metrics.jsonl
```
Expect: `published 44 records`.

### Step 30 · VM1 · Consumer 2
```bash
python consumer/consumer2.py --output outputs/recovery_test/order_metrics_landed.jsonl
```
Expect: `landed 132 records`.

### Step 31 · VM1 · Spark Job 2
```bash
python spark/spark_job2.py --input outputs/recovery_test/order_metrics_landed.jsonl --output-dir outputs/recovery_test
```
Expect: 6 + 4 rows.

### Step 32 · VM1 · Show that the results are unchanged
```bash
diff outputs/restaurant_summary.csv outputs/recovery_test/restaurant_summary.csv && diff outputs/city_summary.csv outputs/recovery_test/city_summary.csv && echo "SAME RESULTS"
```
Expect: `SAME RESULTS`. **Demo finished.**

Alone, when you're done: `./kafka/local/cluster.sh stop all`

---

## Why the numbers grow

Kafka keeps every message it has received, so each run adds to the topics:

| | Main run | VM3 down | VM3 back |
|---|---|---|---|
| `orders` topic | 62 | 124 | 186 |
| `order_metrics` topic | 44 | 88 | 132 |
| Spark Job 1 output | 44 | 44 | 44 |
| CSVs | original | identical | identical |

The extra copies are exact duplicates, so Spark removes them and the results never change.
