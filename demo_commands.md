# Demo commands – all four VMs

My part is **VM1** (Producer 1, Consumer 2, Spark Job 2). Sections 1–3 are
for VM1. Section 4 has the commands for the other three VMs and the order to
run everything in during the team session.

## 1. VM1 one-time setup (WSL Ubuntu)

```bash
cd /mnt/c/Users/Aryan/Desktop/BD-Assignment
java -version                        # needs 17+ (Ubuntu has 21)
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
pip install -r requirements.txt      # PySpark + kafka-python, ~400 MB
pip list | grep -iE "pyspark|kafka"  # must show pyspark 4.2.0 and kafka-python 2.2.15
```

Every new terminal:

```bash
cd /mnt/c/Users/Aryan/Desktop/BD-Assignment
source .venv-wsl/bin/activate        # prompt shows (.venv-wsl)
```

## 2. Solo test (all four roles on this laptop)

The local two-broker cluster stands in for VM2 + VM3, and the VM4 scripts run
here too. **Only the lines marked VM1 are mine.**

```bash
# Stand-in for VM2 + VM3: start the local brokers
./kafka/local/cluster.sh status
./kafka/local/cluster.sh format      # needed after WSL restarts (/tmp is wiped); safe to repeat
./kafka/local/cluster.sh start all
./kafka/topics.sh delete; ./kafka/topics.sh create

export KAFKA_BOOTSTRAP_SERVERS=localhost:9092,localhost:9094

# VM1 – Producer 1: publish the raw dataset to 'orders'
python producer/producer1.py --input order.jsonl

# Stand-in for VM4: land, enrich, republish
python consumer/consumer1.py --output outputs/orders_landed.jsonl
python spark/spark_job1.py --input outputs/orders_landed.jsonl --output outputs/order_metrics.jsonl
python producer/producer2.py --input outputs/order_metrics.jsonl

# VM1 – Consumer 2: land 'order_metrics' to a local file
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl

# VM1 – Spark Job 2: build the two summaries
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl --output-dir outputs

# VM1 – check and show the results
python tests/verify_outputs.py --raw order.jsonl --metrics outputs/order_metrics_landed.jsonl
cat outputs/restaurant_summary.csv
cat outputs/city_summary.csv
```

Broker-failure test on the local cluster (broker 2 plays VM3):

```bash
./kafka/local/cluster.sh stop 2; sleep 15
BOOTSTRAP=localhost:9092 ./kafka/topics.sh describe        # every Leader: 1, Isr: 1
python consumer/consumer1.py --bootstrap-servers localhost:9092 --output outputs/failover_test/orders_landed.jsonl
python consumer/consumer2.py --bootstrap-servers localhost:9092 --output outputs/failover_test/order_metrics_landed.jsonl
./kafka/local/cluster.sh start 2; sleep 15
./kafka/topics.sh describe                                 # Isr back to 1,2 / 2,1

./kafka/local/cluster.sh stop all                          # done testing
```

## 3. What to show (expected output on order.jsonl)

| Step | Expected output |
|---|---|
| Producer 1 | `published 62 records from order.jsonl to topic 'orders'`, 31 on partition 0, 31 on partition 1 |
| Consumer 1 (VM4) | `landed 62 records from topic 'orders'` |
| Spark Job 1 (VM4) | 14 dropped, `valid records: 48`, `exact duplicates removed: 4`, `enriched records written: 44` |
| Producer 2 (VM4) | `published 44 records ... to topic 'order_metrics'` |
| Consumer 2 | `landed 44 records from topic 'order_metrics' into outputs/order_metrics_landed.jsonl` |
| Spark Job 2 | `input records: 44, exact duplicates removed: 0`, then `6 rows -> restaurant_summary.csv` and `4 rows -> city_summary.csv` |
| Verify | last line `OK: 44 enriched records and both summaries match the Python recomputation.` |
| Failure test | Consumer 1 still lands 62 and Consumer 2 still lands 44 with VM3 stopped |

How partitions split differs between runs; the totals don't.

Expected `restaurant_summary.csv`:

```
restaurant_id,order_count,avg_order_amount,avg_preparation_time_min,avg_delivery_time_min,delayed_order_count,delay_rate_pct
R01,8,548.5,13.13,22.0,4,50.0
R02,8,539.25,13.38,27.0,8,100.0
R03,7,664.0,13.86,32.0,4,57.14
R04,7,639.57,12.14,37.0,7,100.0
R05,7,615.14,12.0,42.0,3,42.86
R06,7,712.14,13.43,47.0,7,100.0
```

Expected `city_summary.csv`:

```
city,order_count,avg_order_amount,avg_delivery_time_min,delayed_order_count,delay_rate_pct
Bengaluru,16,543.88,24.5,12,75.0
Hyderabad,7,712.14,47.0,7,100.0
Mumbai,14,651.79,34.5,11,78.57
Pune,7,615.14,42.0,3,42.86
```

### Same results on every machine

Every member runs the pipeline on their own laptop/VM, but the **results
are identical everywhere**: everyone uses the same `order.jsonl`, and the
cleaning, metrics and summaries are deterministic (output rows are sorted, numbers
rounded the same way). What legitimately differs between machines:

| Differs (ignore) | Same everywhere (compare) |
|---|---|
| How `orders` splits over partitions 0/1 (e.g. 31/31, 40/22) — unkeyed messages go to a random partition | Totals: 62 landed, 14 dropped, 4 duplicates, 44 enriched |
| Line order inside `orders_landed.jsonl` and `order_metrics_landed.jsonl` (partitions interleave) | The **set** of lines in those two files |
| Cluster id, topic ids, leader numbers in `describe` | `order_metrics.jsonl`, `restaurant_summary.csv`, `city_summary.csv`, byte for byte |
| Timestamps and paths in logs | `order_metrics` split: always 16 / 28 (keyed by order_id) |

Fingerprint check. Run this on any machine and compare against the table.
Landed files are sorted first so line order doesn't matter, and `\r` is stripped
in case a copy of the dataset got Windows line endings:

```bash
tr -d '\r' < order.jsonl | sha256sum
sha256sum outputs/order_metrics.jsonl outputs/restaurant_summary.csv outputs/city_summary.csv
LC_ALL=C sort outputs/orders_landed.jsonl | sha256sum
LC_ALL=C sort outputs/order_metrics_landed.jsonl | sha256sum
```

| File | Where it exists in the team session | sha256 (first 12 chars) |
|---|---|---|
| `order.jsonl` (input) | everyone | `a7e3af89730d` |
| `orders_landed.jsonl` (sorted) | VM4 | `c5c093713f4a` |
| `order_metrics.jsonl` | VM4 | `d81f97ee2a35` |
| `order_metrics_landed.jsonl` (sorted) | VM1 | `d81f97ee2a35` (same as `order_metrics.jsonl`: Kafka delivered every record unchanged) |
| `restaurant_summary.csv` | VM1 | `51c22d9a7354` |
| `city_summary.csv` | VM1 | `28012cc015e4` |

If `order.jsonl` doesn't match, that person has a different copy of the
dataset; nothing after it will match either. Don't open and re-save the CSVs in
Excel before hashing; that changes the bytes.

In the team session each file only exists on the VM that produced it
(VM4: the first two JSONL files; VM1: the landed metrics and both CSVs). Copying
them together **for submission** afterwards is fine; the spec only forbids moving
`order_metrics.jsonl` from VM4 to VM1 *as part of the pipeline* instead of through Kafka.

**Start from an empty `outputs/` folder.** A copy of this repo already contains
outputs from a solo run. If a step fails silently, a stale file could make it look
like it worked (e.g. Producer 2 would republish an old `order_metrics.jsonl`). Before
the team run, VM1 and VM4 each run:

```bash
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test
```

## 4. Team session (real VM1–VM4)

### Run order

| # | Who | What |
|---|---|---|
| 1 | Everyone | Join ZeroTier, share IPs, copy this repo onto your VM |
| 2 | VM2 | Format + start controller/broker 1, send the cluster id to VM3 |
| 3 | VM3 | Format with VM2's id, start broker 2 |
| 4 | VM2 | Check both brokers are registered, create both topics |
| 5 | VM1, VM4 | Check brokers are reachable |
| 6 | VM4 | Start Consumer 1 (it waits for data) |
| 7 | VM1 | Producer 1 |
| 8 | VM4 | Spark Job 1, Producer 2 |
| 9 | VM1 | Consumer 2, Spark Job 2, verify |
| 10 | VM3 | Stop the broker → VM2, VM1, VM4 show data is still available |

### Every VM: ZeroTier and addresses

Each VM must be **on the ZeroTier network itself**. For a VirtualBox VM,
install ZeroTier inside the VM, not on the host. VM1 is the exception: it
runs in WSL, and WSL's traffic goes out through Windows, so ZeroTier on Windows
is enough.

```bash
curl -s https://install.zerotier.com | sudo bash      # Linux VMs
sudo zerotier-cli join <NETWORK_ID>                   # approve the member in ZeroTier Central
ip -4 addr | grep -A2 zt                              # your ZeroTier IP

# Put the real IPs in every terminal on every VM:
export VM2=<VM2 ZeroTier IP>
export VM3=<VM3 ZeroTier IP>
export KAFKA_HOME=~/kafka                             # TA requirement; topics.sh uses it
export BS="$VM2:9092"                                 # TA requirement; scripts fall back to it
export BOOTSTRAP="$VM2:9092,$VM3:9092"                # used by kafka/topics.sh
export KAFKA_BOOTSTRAP_SERVERS="$VM2:9092,$VM3:9092"  # used by the Python scripts
```

The Python scripts use `KAFKA_BOOTSTRAP_SERVERS` and fall back to `BS`;
`kafka/topics.sh` uses `BOOTSTRAP` and falls back to `BS`. An explicit
`--bootstrap-servers` flag overrides both.

### VM1 – Producer 1, Consumer 2, Spark Job 2 (mine)

Run in WSL after `source .venv-wsl/bin/activate` and the `export` lines above.

```bash
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test   # no stale files from the solo test

# Step 5: both brokers reachable? Both lines must say "succeeded"
nc -zv $VM2 9092
nc -zv $VM3 9092

# Step 7: after VM2 confirms the topics exist
python producer/producer1.py --input order.jsonl

# Step 9: waits up to 10 min for VM4 to publish order_metrics
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl --wait-timeout 600
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl --output-dir outputs
python tests/verify_outputs.py --raw order.jsonl --metrics outputs/order_metrics_landed.jsonl
cat outputs/restaurant_summary.csv outputs/city_summary.csv

# Fingerprints: VM1's landed file must match VM4's order_metrics.jsonl hash
LC_ALL=C sort outputs/order_metrics_landed.jsonl | sha256sum   # d81f97ee2a35...
sha256sum outputs/restaurant_summary.csv outputs/city_summary.csv   # 51c22d9a7354... / 28012cc015e4...
```

**Checking the other VMs from VM1.** Kafka is installed in WSL, so VM1 can
check the whole cluster without logging into VM2 or VM3:

```bash
# VM2 + VM3 up: two lines, id 1 and id 2, both isFenced: false
~/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server $VM2:9092 | grep "id:"

# VM2 is the controller (LeaderId: 1) and VM3 joined (CurrentObservers has id 2)
~/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server $VM2:9092 describe --status | grep -E "LeaderId|Voters|Observers"

# Topics: 2 partitions, RF 2, Isr has both brokers
BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh describe

# All replicas in sync: prints nothing
~/kafka/bin/kafka-topics.sh --bootstrap-server $VM2:9092 --describe --under-replicated-partitions

# After VM1 publishes: orders has 62 records (the two numbers add up to 62)
~/kafka/bin/kafka-get-offsets.sh --bootstrap-server $VM2:9092 --topic orders

# VM4 did its job: order_metrics has 44 records, e.g. order_metrics:0:16 and order_metrics:1:28
~/kafka/bin/kafka-get-offsets.sh --bootstrap-server $VM2:9092 --topic order_metrics
```

### VM2 – KRaft controller + broker 1

```bash
# Install Java and Kafka (once)
sudo apt update && sudo apt install -y openjdk-21-jre-headless netcat-openbsd
curl -LO https://dlcdn.apache.org/kafka/4.3.1/kafka_2.13-4.3.1.tgz
#   if that 404s: https://archive.apache.org/dist/kafka/4.3.1/kafka_2.13-4.3.1.tgz
tar xzf kafka_2.13-4.3.1.tgz -C ~ && ln -sfn ~/kafka_2.13-4.3.1 ~/kafka
sudo ufw status | grep -q "Status: active" && sudo ufw allow 9092/tcp && sudo ufw allow 9093/tcp

# Config with the real address filled in
sed "s/VM2_ADDRESS/$VM2/g" kafka/vm/vm2-broker1.properties > ~/broker1.properties
grep -E "voters|advertised" ~/broker1.properties      # must show VM2's IP, no placeholder

# Format once with a new cluster id, then start
sudo mkdir -p /var/lib/kafka/data && sudo chown "$USER" /var/lib/kafka/data
~/kafka/bin/kafka-storage.sh random-uuid | tee ~/cluster.id     # send this id to VM3
~/kafka/bin/kafka-storage.sh format -t "$(cat ~/cluster.id)" -c ~/broker1.properties
~/kafka/bin/kafka-server-start.sh -daemon ~/broker1.properties
sleep 10
~/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server $VM2:9092 describe --status
#   LeaderId: 1, CurrentVoters: id 1 at $VM2:9093
```

After VM3 has started:

```bash
~/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server $VM2:9092 | grep "id:"
#   two lines: (id: 1 ... isFenced: false) and (id: 2 ... isFenced: false)
~/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server $VM2:9092 describe --status | grep Observers
#   CurrentObservers shows id 2

BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh create
#   orders and order_metrics: PartitionCount: 2, ReplicationFactor: 2, Isr has both 1 and 2
```

### VM3 – broker 2 (joins VM2's cluster)

Use the same Java + Kafka install and `ufw allow 9092/tcp` as VM2. **Do not
run `random-uuid` here.**

```bash
nc -zv $VM2 9093                                      # controller reachable? must say "succeeded"

sed -e "s/VM2_ADDRESS/$VM2/g" -e "s/VM3_ADDRESS/$VM3/g" \
    kafka/vm/vm3-broker2.properties > ~/broker2.properties
grep -E "voters|advertised" ~/broker2.properties      # voters = VM2's IP, advertised = VM3's IP

sudo mkdir -p /var/lib/kafka/data && sudo chown "$USER" /var/lib/kafka/data
~/kafka/bin/kafka-storage.sh format -t <CLUSTER_ID_FROM_VM2> -c ~/broker2.properties
~/kafka/bin/kafka-server-start.sh -daemon ~/broker2.properties
sleep 10
grep -iE "error|started" ~/kafka/logs/server.log | tail -5   # "Kafka Server started"
```

Checks after VM2 has created the topics:

```bash
BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh describe
~/kafka/bin/kafka-topics.sh --bootstrap-server $VM2:9092 --describe --under-replicated-partitions
#   prints nothing = every replica is in sync
```

Broker-failure test (step 10). Stop **VM3 only**, never VM2:

```bash
~/kafka/bin/kafka-server-stop.sh                      # or power off the VM
# ...after the others have shown data is still available:
~/kafka/bin/kafka-server-start.sh -daemon ~/broker2.properties
```

### VM4 – Consumer 1, Spark Job 1, Producer 2

Needs Java and Python, not Kafka.

```bash
sudo apt update && sudo apt install -y openjdk-21-jre-headless python3-venv netcat-openbsd
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test   # no stale files
nc -zv $VM2 9092 && nc -zv $VM3 9092                  # both "succeeded"

# Step 6: start before VM1 publishes; waits up to 10 min for the first record
python consumer/consumer1.py --output outputs/orders_landed.jsonl --wait-timeout 600
# Step 8:
python spark/spark_job1.py --input outputs/orders_landed.jsonl --output outputs/order_metrics.jsonl
python producer/producer2.py --input outputs/order_metrics.jsonl

# Fingerprints to compare with VM1 / the table in section 3
LC_ALL=C sort outputs/orders_landed.jsonl | sha256sum          # c5c093713f4a...
sha256sum outputs/order_metrics.jsonl                          # d81f97ee2a35...
```

### Step 10 – broker-failure test (VM3 stopped, then restarted)

The evaluator checks four things: (A) topic config and ISR before, (B) ISR and
leaders after VM3 stops, (C) the pipeline keeps working with VM3 down,
(D) VM3 rejoins the ISR and the pipeline still works. **Never stop VM2.**

Run each step only after the previous one has finished. A consumer stops
10 s after it catches up, so it must start *after* its producer is done.
The failover and recovery runs write to their own folders, so the main
outputs in `outputs/` (the ones that get evaluated) are left alone.

**A. Before (both brokers up)**

```bash
# VM2
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server $VM2:9092 | grep "id:"  # ids 1 and 2
BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh describe
#   PartitionCount: 2, ReplicationFactor: 2, Isr: 2,1 / 1,2
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $VM2:9092 --describe --under-replicated-partitions
#   prints nothing = all replicas in sync
```

**B. Stop VM3**

```bash
# VM3
$KAFKA_HOME/bin/kafka-server-stop.sh

# VM2, after ~15 s
BOOTSTRAP=$VM2:9092 ./kafka/topics.sh describe
#   every partition: Leader: 1, Isr: 1   (Replicas still lists 2; that's expected)
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $VM2:9092 --describe --under-replicated-partitions
#   now lists all 4 partitions (only one copy each)
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server $VM2:9092 | grep "id:"  # only id 1
```

**C. Pipeline continuity with VM3 down** (everything talks to VM2 only)

```bash
# VM1 + VM4: run once before step C
mkdir -p outputs/failover_test outputs/recovery_test

# 1. VM1: produce new data
python producer/producer1.py --bootstrap-servers $VM2:9092 --input order.jsonl
#   published 62 records (writes still succeed: acks=all + min.insync.replicas=1)

# 2. VM4: land, clean, republish
python consumer/consumer1.py --bootstrap-servers $VM2:9092 \
    --output outputs/failover_test/orders_landed.jsonl                 # 124 (62 old + 62 new)
python spark/spark_job1.py --input outputs/failover_test/orders_landed.jsonl \
    --output outputs/failover_test/order_metrics.jsonl                 # still 44 (duplicates removed)
python producer/producer2.py --bootstrap-servers $VM2:9092 \
    --input outputs/failover_test/order_metrics.jsonl                  # published 44

# 3. VM1: land and summarise
python consumer/consumer2.py --bootstrap-servers $VM2:9092 \
    --output outputs/failover_test/order_metrics_landed.jsonl          # 88 (44 old + 44 new)
python spark/spark_job2.py --input outputs/failover_test/order_metrics_landed.jsonl \
    --output-dir outputs/failover_test                                 # 44 duplicates removed, 6 + 4 rows
diff outputs/restaurant_summary.csv outputs/failover_test/restaurant_summary.csv && \
diff outputs/city_summary.csv outputs/failover_test/city_summary.csv && echo "SAME RESULTS"
```

**D. Restart VM3, show it rejoins, run the pipeline again**

```bash
# VM3
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties

# VM2, after ~15 s
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server $VM2:9092 | grep "id:"  # ids 1 and 2 again
BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh describe
#   Isr back to 2,1 / 1,2. Leader may stay 1 for a few minutes until Kafka's
#   automatic preferred-leader rebalance moves partition 0 back to broker 2.
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $VM2:9092 --describe --under-replicated-partitions
#   prints nothing again: VM3 caught up on everything it missed

# Same pipeline with both brokers (the env vars list VM2 and VM3 again)
# VM1:
python producer/producer1.py --input order.jsonl                                    # 62
# VM4:
python consumer/consumer1.py --output outputs/recovery_test/orders_landed.jsonl     # 186
python spark/spark_job1.py --input outputs/recovery_test/orders_landed.jsonl \
    --output outputs/recovery_test/order_metrics.jsonl                              # 44
python producer/producer2.py --input outputs/recovery_test/order_metrics.jsonl      # 44
# VM1:
python consumer/consumer2.py --output outputs/recovery_test/order_metrics_landed.jsonl   # 132
python spark/spark_job2.py --input outputs/recovery_test/order_metrics_landed.jsonl \
    --output-dir outputs/recovery_test
diff outputs/restaurant_summary.csv outputs/recovery_test/restaurant_summary.csv && \
diff outputs/city_summary.csv outputs/recovery_test/city_summary.csv && echo "SAME RESULTS"
```

**Why the counts grow (be ready to explain this):** Kafka keeps every message,
so each producer run adds to the topic: `orders` goes 62 -> 124 -> 186 and
`order_metrics` goes 44 -> 88 -> 132. The consumers always land the whole
topic. The extra copies are exact duplicates, so Spark Job 1 still outputs 44
and Spark Job 2's CSVs stay byte-identical. That shows the at-least-once
delivery plus exact-duplicate removal working as designed.

Take screenshots of each command's output and keep the two CSVs, the three
JSONL files and the `describe` output from before and after the failure for submission.

## 5. If something looks wrong

- **`ModuleNotFoundError: No module named 'kafka'`:** the venv isn't activated,
  or `pip install -r requirements.txt` was never run in it.
- **`NoBrokersAvailable` or a client hangs:** a broker isn't running or can't be
  reached. Check `./kafka/local/cluster.sh status` (solo) or the `nc -zv` checks.
  On the VMs, also check that `advertised.listeners` has the ZeroTier IP, not
  `VM2_ADDRESS` or `localhost` (`grep advertised ~/broker*.properties`).
- **VM3 won't join / `Invalid cluster.id` in VM3's log:** VM3 was formatted with
  a different id. On VM3: stop the broker, `rm -rf /var/lib/kafka/data/*`, then format
  again with the id from VM2's `~/cluster.id`.
- **Consumer lands 124 / 88 instead of 62 / 44** (outside the failure test, where it's expected): a topic was published to twice.
  Reset with `./kafka/topics.sh delete; ./kafka/topics.sh create` (solo), or on VM2
  `BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh delete; BOOTSTRAP=$VM2:9092,$VM3:9092 ./kafka/topics.sh create`,
  then rerun from Producer 1. The CSVs are still correct either way, because Spark removes exact duplicates.
- **Consumer waits and then lands 0:** the producer for that topic hasn't run yet.
- **Broker logs:** `~/kafka/logs/server.log` on VM2/VM3; `/tmp/kafka-data/logs1|2/server.log` in the solo test.
