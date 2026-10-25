# Distributed Food Ordering Pipeline

Two-stage batch pipeline: Kafka (KRaft, 2 brokers) moves data between stages,
Spark Batch does the computation on local files. Built to
`Distributed_Food_Ordering_Assignment_Spec.pdf`.

```
VM1 producer1 ──orders──▶ VM4 consumer1 → orders_landed.jsonl → spark_job1 → order_metrics.jsonl
                                                                                   │
VM1 spark_job2 ◀ order_metrics_landed.jsonl ◀ consumer2 ◀──order_metrics── producer2 (VM4)
     │
     └▶ restaurant_summary.csv, city_summary.csv

Kafka cluster: VM2 = controller + broker 1, VM3 = broker 2
Topics: orders, order_metrics (2 partitions, replication factor 2)
```

**Running the demo?** Follow [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md): numbered
steps, each labelled with the VM that runs it.

## Layout

| Path | Contents |
|---|---|
| `producer/` | `producer1.py` (orders), `producer2.py` (order_metrics), shared `publish.py` |
| `consumer/` | `consumer1.py` (orders → orders_landed.jsonl), `consumer2.py` (order_metrics → order_metrics_landed.jsonl), shared `landing.py` |
| `spark/` | `spark_job1.py` (cleaning, dedup, metrics), `spark_job2.py` (restaurant and city analytics) |
| `kafka/local/` | Configs and helper script for running both brokers on one machine |
| `kafka/vm/` | Per-VM config templates (`VM2_ADDRESS` / `VM3_ADDRESS` placeholders) |
| `kafka/topics.sh` | Create, describe or delete both topics |
| `tests/` | `verify_outputs.py` (standard-library recomputation of both jobs), `fixtures/orders_small.jsonl` |
| `outputs/` | Outputs from the local run |

## Configuration

Every script takes command-line flags; nothing is hardcoded to one machine.

| Setting | Flag | Default |
|---|---|---|
| Kafka brokers | `--bootstrap-servers` or env `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092,localhost:9094` |
| Topic | `--topic` | `orders` / `order_metrics` |
| Producer input | `--input` (alias `--file`) | `order.jsonl` / `outputs/order_metrics.jsonl` |
| Producer slow mode | `--delay` seconds per record; prints each confirmed record (broker-failure test) | `0` |
| Consumer output | `--output` | `outputs/orders_landed.jsonl` / `outputs/order_metrics_landed.jsonl` |
| Consumer stop condition | `--idle-timeout`, `--wait-timeout` | 10 s idle after catching up; wait up to 120 s for the first message |
| Spark Job 1 | `--input`, `--output` | `outputs/orders_landed.jsonl`, `outputs/order_metrics.jsonl` |
| Spark Job 2 | `--input`, `--output-dir` | `outputs/order_metrics_landed.jsonl`, `outputs` |

On the VMs, set `KAFKA_BOOTSTRAP_SERVERS=VM2_ADDRESS:9092,VM3_ADDRESS:9092`.
If it isn't set, the scripts fall back to the `BS` variable from the TA's
instructions; `kafka/topics.sh` uses `BOOTSTRAP`, then `BS`.

## Prerequisites (install before demo day)

All commands assume Ubuntu, or WSL Ubuntu on Windows. Do this once on your
VM, before the team session.

### What each VM needs

| Software | VM1 | VM2 | VM3 | VM4 | Why |
|---|:-:|:-:|:-:|:-:|---|
| ZeroTier | ✔ | ✔ | ✔ | ✔ | All four VMs on one private network |
| Git | ✔ | ✔ | ✔ | ✔ | Clone this repo (configs and scripts) |
| netcat (`nc`) | ✔ | ✔ | ✔ | ✔ | Check that brokers are reachable |
| Java 17+ | ✔ | ✔ | ✔ | ✔ | Kafka runs on Java; PySpark needs it too |
| Kafka 4.3.1 | optional | ✔ | ✔ | – | The brokers. On VM1 it's only for the cluster check commands |
| Python 3.10+ and venv | ✔ | – | – | ✔ | Producers, consumers, Spark jobs |
| `pip install -r requirements.txt` | ✔ | – | – | ✔ | PySpark 4.2.0, kafka-python 2.2.15 |

VM1 runs in WSL: install ZeroTier **on Windows** (WSL traffic goes through
Windows) and everything else inside WSL. On a VirtualBox/VMware VM, install
ZeroTier **inside the VM**, not on the host.

### 1. Every VM: system packages and ZeroTier

```bash
sudo apt update
sudo apt install -y git netcat-openbsd openjdk-21-jre-headless curl
java -version                                         # must say 17 or higher

# ZeroTier (Linux VMs; on Windows use the installer from zerotier.com)
curl -s https://install.zerotier.com | sudo bash
sudo zerotier-cli join <NETWORK_ID>                   # then approve the member in ZeroTier Central
ip -4 addr | grep -A2 zt                              # note your ZeroTier IP and share it with the team

# Get the code
git clone https://github.com/Aryan-20-2006/BD-Assignment.git ~/BD-Assignment
cd ~/BD-Assignment
# later, to get updates:  cd ~/BD-Assignment && git pull
```

### 2. VM2 and VM3 (and optionally VM1): Kafka

```bash
curl -LO https://dlcdn.apache.org/kafka/4.3.1/kafka_2.13-4.3.1.tgz
#   if that link 404s: https://archive.apache.org/dist/kafka/4.3.1/kafka_2.13-4.3.1.tgz
tar xzf kafka_2.13-4.3.1.tgz -C ~ && ln -sfn ~/kafka_2.13-4.3.1 ~/kafka
~/kafka/bin/kafka-topics.sh --version                 # prints 4.3.1

# Open the Kafka ports if the firewall is on
sudo ufw status | grep -q "Status: active" && sudo ufw allow 9092/tcp   # VM2 and VM3
sudo ufw status | grep -q "Status: active" && sudo ufw allow 9093/tcp   # VM2 only (controller)
```

Kafka 4.x runs in KRaft mode only (no ZooKeeper). Formatting the storage and
starting the brokers is covered in "Four-VM deployment" below and in
`demo_commands.md`.

### 3. VM1 and VM4: Python environment

```bash
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate                             # needed in every new terminal
pip install -r requirements.txt                       # ~400 MB, takes a few minutes
pip list | grep -iE "pyspark|kafka"                   # pyspark 4.2.0, kafka-python 2.2.15
```

On VM1 (WSL) this repo uses `.venv-wsl` instead of `.venv`, so that it
doesn't clash with a Windows venv in the same folder. Either name works; just
activate the one you made.

If Spark complains about Java, set `JAVA_HOME` to the JDK folder itself, not
its `bin` folder. For example:
`export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`.

### 4. Check everything is installed

```bash
git --version && nc -h 2>&1 | head -1 && java -version 2>&1 | head -1
~/kafka/bin/kafka-topics.sh --version                                 # VM2, VM3
python -c "import pyspark, kafka; print(pyspark.__version__, kafka.__version__)"   # VM1, VM4 (venv active)
sudo zerotier-cli listnetworks                                        # status OK, with your ZeroTier IP
```

Once the ZeroTier IPs are shared, test the network before demo day. From
every VM run `ping <VM2 ZeroTier IP>`. After VM2 has started Kafka, VM1, VM3
and VM4 can also run `nc -zv <VM2 ZeroTier IP> 9092`.

## Single-machine run

Both brokers run on one host. Broker 1 listens on 9092 (controller on 9093),
broker 2 on 9094. On Windows, run the Kafka commands inside WSL; the Python
clients can run on Windows because WSL2 forwards `localhost`.

### 1. Start the Kafka cluster and create the topics

```bash
./kafka/local/cluster.sh format      # once: one cluster id for both brokers
./kafka/local/cluster.sh start all
./kafka/topics.sh create             # orders, order_metrics: 2 partitions, RF 2
./kafka/topics.sh describe
~/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server localhost:9092 describe --status
```

### 2. Stage 1: order enrichment

```bash
python producer/producer1.py --input order.jsonl                        # VM1
python consumer/consumer1.py --output outputs/orders_landed.jsonl       # VM4
python spark/spark_job1.py --input outputs/orders_landed.jsonl \
                           --output outputs/order_metrics.jsonl         # VM4
python producer/producer2.py --input outputs/order_metrics.jsonl        # VM4
```

### 3. Stage 2: operations analytics

```bash
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl    # VM1
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \
                           --output-dir outputs                             # VM1
```

### 4. Check the outputs

This recomputes both jobs in plain Python, with no Spark, and compares the results:

```bash
python tests/verify_outputs.py --raw outputs/orders_landed.jsonl \
    --metrics outputs/order_metrics_landed.jsonl \
    --restaurant outputs/restaurant_summary.csv --city outputs/city_summary.csv
```

The Spark jobs can also run on the dataset or fixture directly, without Kafka:

```bash
python spark/spark_job1.py --input order.jsonl --output outputs/order_metrics.jsonl
python spark/spark_job2.py --input outputs/order_metrics.jsonl --output-dir outputs
```

### 5. Broker-failure test (stop broker 2 / VM3)

```bash
./kafka/topics.sh describe                    # before: Isr 1,2 / 2,1 on every partition
./kafka/local/cluster.sh stop 2               # simulates stopping VM3
sleep 15
BOOTSTRAP=localhost:9092 ./kafka/topics.sh describe   # every Leader is now 1, Isr is 1

# Data is still fully readable through broker 1 only:
python consumer/consumer1.py --bootstrap-servers localhost:9092 \
    --output outputs/failover_test/orders_landed.jsonl
python consumer/consumer2.py --bootstrap-servers localhost:9092 \
    --output outputs/failover_test/order_metrics_landed.jsonl
diff <(sort outputs/failover_test/orders_landed.jsonl) <(sort outputs/orders_landed.jsonl) && echo same

./kafka/local/cluster.sh start 2              # broker 2 rejoins
sleep 15
./kafka/topics.sh describe                    # Isr back to 1,2 on every partition
```

Only use `cluster.sh stop 2` here. `kafka-server-stop.sh` stops every
broker on the host.

### Clean rerun

Producing again appends to the topics. The consumers land the whole topic,
so rerunning a producer without resetting the topics would land duplicates.
Spark removes exact duplicates either way, but reset the topics for a clean run:

```bash
./kafka/topics.sh delete && ./kafka/topics.sh create
# or start from scratch:
./kafka/local/cluster.sh stop all && ./kafka/local/cluster.sh wipe && ./kafka/local/cluster.sh format
```

## Four-VM deployment

Fill in the addresses in `kafka/vm/*.properties` first. Open ports 9092 and
9093 on VM2, and 9092 on VM3, on the ZeroTier network.

**VM2: controller + broker 1**
```bash
sudo mkdir -p /var/lib/kafka/data && sudo chown "$USER" /var/lib/kafka/data
~/kafka/bin/kafka-storage.sh random-uuid > cluster.id          # once, VM2 only
~/kafka/bin/kafka-storage.sh format -t "$(cat cluster.id)" -c kafka/vm/vm2-broker1.properties
~/kafka/bin/kafka-server-start.sh -daemon kafka/vm/vm2-broker1.properties
~/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server VM2_ADDRESS:9092 describe --status
```

**VM3: broker 2.** Use VM2's cluster id. Do not generate a new one.
```bash
sudo mkdir -p /var/lib/kafka/data && sudo chown "$USER" /var/lib/kafka/data
~/kafka/bin/kafka-storage.sh format -t <cluster id from VM2> -c kafka/vm/vm3-broker2.properties
~/kafka/bin/kafka-server-start.sh -daemon kafka/vm/vm3-broker2.properties
```

**Topics (from VM2 or VM3)**
```bash
BOOTSTRAP=VM2_ADDRESS:9092,VM3_ADDRESS:9092 ./kafka/topics.sh create
~/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server VM2_ADDRESS:9092 | grep id:   # both brokers listed
```

**VM1 and VM4:** run the commands from stages 1 and 2 above, after `export KAFKA_BOOTSTRAP_SERVERS=VM2_ADDRESS:9092,VM3_ADDRESS:9092`.

**Failure test:** on VM3 run `~/kafka/bin/kafka-server-stop.sh` (or shut VM3
down). Then run `BOOTSTRAP=VM2_ADDRESS:9092 ./kafka/topics.sh describe` and
rerun the whole pipeline with `--bootstrap-servers VM2_ADDRESS:9092` into
`outputs/failover_test/`. Restart VM3, show the ISR is back to both brokers,
and run the pipeline once more into `outputs/recovery_test/`. The full
step-by-step is in `demo_commands.md`, step 10. Controller handover is out of
scope; VM2 is never stopped.

## Results on order.jsonl

| | Records |
|---|---|
| Lines in order.jsonl (excluding the trailing blank line) | 62 |
| Dropped by cleaning rules | 14 |
| Valid | 48 |
| Exact duplicates removed | 4 (T040006, T040017, T040028, T040039) |
| **Enriched records in order_metrics.jsonl** | **44** |

The 14 dropped records:

| Line | order_id | Reason |
|---|---|---|
| 14 | BROKEN | missing restaurant_id and other required fields |
| 27, 40 | none | `invalid_order_record` lines: no order_id |
| 34 | T040002 | missing city |
| 7 | T040005 | accepted_timestamp = "bad" |
| 37 | T040003 | delivered_timestamp = "not-a-timestamp" |
| 10 | T040001 | distance_km = -2 |
| 11 | T040004 | order_amount = 0 |
| 1, 15, 20, 31, 38, 54 | T04X0001 to T04X0006 | status CANCELLED / FAILED / PENDING / REFUNDED |

T040001 to T040005 each also have a valid copy elsewhere in the file. That
copy is kept.

## How the spec's rules are implemented

- **Malformed:** a line that is not a JSON object, or a field of the wrong
  type (for example a string where a number is expected).
- **Missing or invalid field:** any of the 14 input fields is null or absent;
  string fields must not be empty or blank.
- **Valid timestamp:** must parse as `yyyy-MM-dd HH:mm:ss`. Durations use the
  full timestamps (in UTC, so a DST change can't affect them), so orders that
  cross midnight are handled.
- **Exact duplicate:** identical on every field (input fields in Job 1,
  enriched fields in Job 2). Records that share an order_id but differ in any
  field are not duplicates.
- **delay_category:** 0 → ON_TIME; >0 to 15 → SLIGHT_DELAY; >15 to 30 →
  MODERATE_DELAY; >30 → SEVERE_DELAY. For whole minutes this is the same as
  the spec's 1-15 and 16-30.
- **Rounding:** calculated values in both jobs are rounded to 2 decimals
  (HALF_UP, Spark `round`).
- **delivery_speed_kmph** is null if delivery_time_min is 0. No record in the
  dataset hits this.
- **Output files:** the Spark jobs gather their small results on the driver
  and write one file per output, so the files have exactly the names in the
  spec. Spark's own writer would create directories of part files.
- **Raw records:** Producer 1 sends each raw line unchanged, dirty records
  included. Only Spark Job 1 decides what is invalid.
