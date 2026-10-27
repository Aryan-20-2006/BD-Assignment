# Demo commands

Every command for the demo, in the order you run them. **Each step says which
member runs it.** When you finish your step, say "done", and the member with
the next step starts.

These are the same commands as in `Simple_Guide.pdf` (section 3), which also
explains the Kafka and Spark concepts for the viva.

## Who is who

| Member | Machine | Name | ZeroTier IP | Used in commands as |
|---|---|---|---|---|
| Member 1 | VM1 | Aryan | `10.31.88.84` | (not needed) |
| Member 2 | VM2 | Aniket | `10.31.88.79` | `B1=10.31.88.79:9092` (broker 1 + controller) |
| Member 3 | VM3 | Kruthik | `10.31.88.161` | `B2=10.31.88.161:9092` (broker 2) |
| Member 4 | VM4 | Khush | `10.31.88.123` | (not needed) |

**Practising with 3 people:** Member 1 also runs every Member 4 step, using
Member 1's step 0 box.

## Rules for everyone

- Use a **Linux / WSL terminal**, never PowerShell. The prompt looks like
  `user@machine:...$`, not `PS C:\...>`.
- Run **step 0 in every new terminal** you open.
- Copy one whole code block at a time. A line ending in `\` continues on the
  next line.
- **Never stop VM2.** Don't edit `order.jsonl`.
- Spark's `WARN` lines are normal. Only a `Traceback` is an error.

---

## One-time setup (the day before)

### Step A · Members 2, 3 and 4 (VM2, VM3, VM4) · Get the code
Member 1 skips this (the code is already on Aryan's laptop).
```bash
sudo apt install -y git
cd ~
[ -L ~/BD-Assignment ] && rm ~/BD-Assignment
git clone https://github.com/Aryan-20-2006/BD-Assignment.git ~/BD-Assignment
ls ~/BD-Assignment/kafka
```
**Expect:** `local  topics.sh  vm`. If `sudo` asks for a password, it's your VM's
login password; nothing shows while you type it.
**If it fails:** `already exists and is not empty` → run
`mv ~/BD-Assignment ~/BD-Assignment-old`, then the `git clone` line again.

### Step A2 · Members 2, 3 and 4 · Get updates (before every practice and on demo morning)
```bash
cd ~/BD-Assignment
git pull
```
**Expect:** `Already up to date.` or a list of changed files.
**If it fails:** `Your local changes ... would be overwritten` → `git stash`, then `git pull` again.

### Step A3 · Member 2 (VM2, Aniket) and Member 3 (VM3, Kruthik) · Install Kafka 3.9.2
The TA's required version. **Both broker machines must run the same version**, or
broker 2 can't join the cluster.
```bash
pkill -9 -f kafka.Kafka
cd ~
curl -LO https://mirrors.huaweicloud.com/apache/kafka/3.9.2/kafka_2.13-3.9.2.tgz
tar xzf kafka_2.13-3.9.2.tgz -C ~
[ -d ~/kafka ] && [ ! -L ~/kafka ] && mv ~/kafka ~/kafka-old
ln -sfn ~/kafka_2.13-3.9.2 ~/kafka
~/kafka/bin/kafka-topics.sh --version
```
**Expect:** the last line prints `3.9.2`. Then redo step B (Member 2) and step C
(Member 3), because storage made by another Kafka version has to be made again.
**If it fails:** `No such file or directory` for `kafka_2.13-3.9.2` → the download
didn't finish; run the `curl` line again. If the mirror doesn't work, use Apache's
own (much slower) link: `https://archive.apache.org/dist/kafka/3.9.2/kafka_2.13-3.9.2.tgz`.

### Step B · Member 2 (VM2, Aniket) · Broker 1 config, cluster ID, storage, firewall
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
$KAFKA_HOME/bin/kafka-storage.sh format -t "$(cat ~/cluster.id)" -c ~/broker1.properties
sudo ufw allow in on zt+
```
**Expect:** the `grep` shows `10.31.88.79` (not `localhost`). `cat` prints the
cluster ID: **send it to Member 3.**
**If it fails:** `already formatted` → `rm -rf ~/kafka-data`, then repeat the
`format` line. Running box B again makes a **new** cluster ID, so Member 3 must
then redo step C.

### Step C · Member 3 (VM3, Kruthik) · Broker 2 config and storage
Replace `CLUSTER_ID_FROM_MEMBER_2` with the ID Member 2 sent.
```bash
export KAFKA_HOME=~/kafka
cd ~/BD-Assignment
$KAFKA_HOME/bin/kafka-server-stop.sh
while pgrep -f kafka.Kafka > /dev/null; do sleep 1; done
sed -e "s/VM2_ADDRESS/10.31.88.79/g" -e "s/VM3_ADDRESS/10.31.88.161/g" \
    -e "s#/var/lib/kafka/data#$HOME/kafka-data#" \
    kafka/vm/vm3-broker2.properties > ~/broker2.properties
echo "initial.broker.registration.timeout.ms=300000" >> ~/broker2.properties
grep -E "voters|advertised|log.dirs|initial" ~/broker2.properties
$KAFKA_HOME/bin/kafka-storage.sh format -t CLUSTER_ID_FROM_MEMBER_2 \
    -c ~/broker2.properties
sudo ufw allow in on zt+
```
**Expect:** `voters` shows `10.31.88.79:9093`, `advertised` shows `10.31.88.161:9092`.
The `initial...` line gives broker 2 five minutes to join over a slow ZeroTier link.
**Never run `random-uuid` on VM3.**
**If it fails:**
- `Expected CLUSTER_ID_FROM_MEMBER_2, but read <Member 2's ID>` → the storage
  is already fine; skip the `format` line.
- `already formatted`, or a *different* ID after `but read` → `rm -rf ~/kafka-data`,
  then repeat `format` with Member 2's ID.
- `advertised` shows an IP other than `10.31.88.161` → your copy is old: `git pull`,
  then run the `sed` line again.

### Step D · Member 4 (VM4, Khush) · Java, Python and packages
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
**Expect:** Java 21 (17+ is fine); the last line prints `4.2.0 2.2.15`. Member 4
doesn't need Kafka installed.

---

## Before the checkpoints

### Step 0 · Everyone · Set up the terminal (every terminal you use)

**Member 1 (VM1, Aryan, WSL):**
```bash
cd /mnt/c/Users/Aryan/Desktop/BD-Assignment
source .venv-wsl/bin/activate
export KAFKA_HOME=~/kafka
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON
export B1=10.31.88.79:9092
export B2=10.31.88.161:9092
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

**Member 2 (VM2, Aniket) and Member 3 (VM3, Kruthik):**
```bash
cd ~/BD-Assignment
git pull
export KAFKA_HOME=~/kafka
export B1=10.31.88.79:9092
export B2=10.31.88.161:9092
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```

**Member 4 (VM4, Khush):**
```bash
cd ~/BD-Assignment
git pull
source .venv/bin/activate
export KAFKA_HOME=~/kafka
export B1=10.31.88.79:9092
export B2=10.31.88.161:9092
export BS=$B1
export BOOTSTRAP=$B1,$B2
export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2
```
**Expect:** Members 1 and 4 see `(.venv-wsl)` / `(.venv)` at the start of the prompt.
**If it fails:** `No such file or directory` on `cd` → do step A. `python: command not found`
later → you're in a terminal without step 0.

### Step 1 · Member 2 (VM2, Aniket) · Start broker 1 and the controller
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker1.properties
```
**Expect:** no output.
**If it fails:** `class file versions up to 55.0` in `$KAFKA_HOME/logs/kafkaServer.out`
→ `export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64` and start again.

### Step 2 · Member 3 (VM3, Kruthik) · Start broker 2
```bash
$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties
```
**Expect:** no output. Give it up to a few minutes to join before step 3.
**If it fails:** see step 20's notes (same broker).

### Step 3 · Member 2 (VM2, Aniket) · Create fresh topics
```bash
bash kafka/topics.sh delete
sleep 10
bash kafka/topics.sh create
```
**Expect:** both topics with `PartitionCount: 2`, `ReplicationFactor: 2`, `Isr: 1,2`.
**If it fails:**
- `only 1 broker(s) are registered` → broker 2 hasn't joined yet. Member 3 checks step 2;
  wait until step 5 shows `id: 1` **and** `id: 2`, then run this again.
- `Topic 'orders' does not exist as expected` → the old topic was still being deleted:
  run `bash kafka/topics.sh create` again.
- `Permission denied` → keep `bash` in front, as shown.

### Step 4 · Member 1 (VM1, Aryan) and Member 4 (VM4, Khush) · Clear old outputs
```bash
rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test
mkdir -p outputs/failover_test outputs/recovery_test
```
**Expect:** no output. The TA only accepts outputs from the live run.

---

## Checkpoint 1: the cluster

### Step 5 · Member 2 (VM2, Aniket) · Brokers reachable, VM2 is the controller, topics exist
```bash
$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server "$BS" | grep "id:"
$KAFKA_HOME/bin/kafka-metadata-quorum.sh --bootstrap-server "$BS" describe --status
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --list
```
**Expect:** `10.31.88.79:9092 (id: 1` and `10.31.88.161:9092 (id: 2`; `LeaderId: 1`;
`orders` and `order_metrics`.
**If it fails:** brokers shown as `localhost` → redo step B / C, then steps 1-2.
`Connection refused` → broker 1 isn't running (step 1). `timed out` → a firewall:
`sudo ufw allow in on zt+` on that VM.

---

## Checkpoint 2: raw orders, VM1 → Kafka → VM4

### Step 6 · Member 2 (VM2, Aniket) · Observer on `orders` (leave it running)
Replace `teamXX` with your team number.
```bash
$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \
    --topic orders --group ta-observer-teamXX-run1 \
    --consumer-property auto.offset.reset=latest \
    --max-messages 3 --timeout-ms 30000
```
**Expect:** it waits. It gives up after 30 s, so **Member 1 starts step 7 straight away.**
**If it fails:** `Processed a total of 0 messages` → step 7 was too late; run this again,
then step 7 immediately.

### Step 7 · Member 1 (VM1, Aryan) · Producer 1
Tip: type it in advance, and press Enter when Member 2 says "go".
```bash
python producer/producer1.py --input order.jsonl
```
**Expect:** `published 62 records`; Member 2's observer prints 3 records and
`Processed a total of 3 messages`.
**If it fails:** `NoBrokersAvailable` / `KafkaTimeoutError` → this laptop can't reach the
brokers: check step 0 was run here (`echo $KAFKA_BOOTSTRAP_SERVERS`) and that
`nc -zv -w 5 10.31.88.79 9092` succeeds.

### Step 8 · Member 4 (VM4, Khush) · Consumer 1
```bash
python consumer/consumer1.py --output outputs/orders_landed.jsonl
```
**Expect:** `landed 62 records`.

### Step 9 · Member 4 (VM4, Khush) · Show the landed file
```bash
wc -l outputs/orders_landed.jsonl && head -n 2 outputs/orders_landed.jsonl
```
**Expect:** `62 outputs/orders_landed.jsonl` and two order lines.

---

## Checkpoint 3: enriched orders, VM4 → Kafka → VM1

### Step 10 · Member 4 (VM4, Khush) · Spark Job 1
```bash
python spark/spark_job1.py --input outputs/orders_landed.jsonl \
    --output outputs/order_metrics.jsonl
```
**Expect:** `valid records: 48`, `exact duplicates removed: 4`, `enriched records written: 44`.
**If it fails:** `'JavaPackage' object is not callable` → run
`unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON`, then again.

### Step 11 · Member 2 (VM2, Aniket) · Observer on `order_metrics` (leave it running)
```bash
$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \
    --topic order_metrics --group ta-observer-teamXX-run2 \
    --consumer-property auto.offset.reset=latest \
    --max-messages 3 --timeout-ms 30000
```
**Expect:** it waits; **Member 4 starts step 12 within 30 s.**

### Step 12 · Member 4 (VM4, Khush) · Producer 2
```bash
python producer/producer2.py --input outputs/order_metrics.jsonl
```
**Expect:** `published 44 records` (partition 0: 16, partition 1: 28); the observer prints 3 records.

### Step 13 · Member 1 (VM1, Aryan) · Consumer 2
```bash
python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl
```
**Expect:** `landed 44 records` (16 / 28).

### Step 14 · Member 1 (VM1, Aryan) · Show the landed file
```bash
wc -l outputs/order_metrics_landed.jsonl && head -n 2 outputs/order_metrics_landed.jsonl
```
**Expect:** `44 outputs/order_metrics_landed.jsonl` and two enriched lines.

### Step 15 · Member 1 (VM1, Aryan) · Spark Job 2 (the final CSVs)
```bash
python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \
    --output-dir outputs
```
**Expect:** `6 rows -> restaurant_summary.csv`, `4 rows -> city_summary.csv`. To show them:
`cat outputs/restaurant_summary.csv outputs/city_summary.csv`.

---

## Checkpoint 4: broker failure and recovery

**Before starting:** step 16 must show `Isr: 1,2` (both brokers up). If it shows
`Isr: 1`, broker 2 isn't running; Member 3 does step 2 first.

### Step 16 · Member 2 (VM2, Aniket) · Leaders and ISR before the failure
```bash
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Isr: 1,2` / `2,1` on both partitions.

### Step 17 · Member 1 (VM1, Aryan) · Slow producer (leave it running)
```bash
python producer/producer1.py --file order.jsonl --delay 0.5
```
**Expect:** `sent 1/62 -> partition ...`, one line every half second. After step 18 it
pauses briefly, then carries on to `sent 62/62` and `published 62 records`. **That's the
pipeline continuity the TA checks.**
**If it fails:** `NoBrokersAvailable` → VM2 isn't reachable from this laptop
(`ping 10.31.88.79`). Member 2 checks `sudo zerotier-cli listnetworks` shows `OK`.

### Step 18 · Member 3 (VM3, Kruthik) · Kill the broker (while step 17 is still sending)
```bash
pkill -9 -f kafka.Kafka
```
**Expect:** no output. **Never run this on VM2.**

### Step 19 · Member 2 (VM2, Aniket) · Leaders and ISR after the failure
```bash
sleep 10
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Leader: 1` and `Isr: 1` on both partitions. A `WARN ... node 2 ... could not
be established` line is normal here.

### Step 20 · Member 3 (VM3, Kruthik) · Restart the broker (in its own terminal, leave it open)
```bash
KAFKA_HEAP_OPTS='-Xmx512m -Xms512m' $KAFKA_HOME/bin/kafka-server-start.sh \
    ~/broker2.properties
```
**Expect:** it keeps printing log lines and doesn't return to the prompt. **Wait for
`Kafka Server started`**: on a slow link this can take a few minutes. Don't press
Ctrl+C or close the terminal.
**If it fails:**
- `fatal error while waiting for the controller to acknowledge that we are caught up` →
  it gave up before joining. Check `~/broker2.properties` has
  `initial.broker.registration.timeout.ms=300000` (step C), and that
  `nc -zv -w 5 10.31.88.79 9093` and `... 9092` both succeed from VM3. Then run this again.
- `Address already in use` → an old broker 2 is still running:
  `pkill -9 -f broker2.properties`, wait 5 s, run this again.

### Step 21 · Member 2 (VM2, Aniket) · Leaders and ISR after the restart
```bash
sleep 15
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Isr: 1,2` again. **Don't go on until it says so.**
**If it fails:** still `Isr: 1` → broker 2 isn't up yet; look at step 20's terminal.

### Step 22 · Member 2 (VM2, Aniket) · Leader election, then check again
```bash
$KAFKA_HOME/bin/kafka-leader-election.sh --bootstrap-server "$BS" \
    --election-type preferred --all-topic-partitions
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders
```
**Expect:** `Successfully completed leader election`; the leaders are back to how they
were in step 16. **Demo finished.**
**If it fails:** many `PreferredLeaderNotAvailableException` lines and `Isr: 1` → broker 2
isn't back (step 20/21). Get `Isr: 1,2` first, then run this again.

---

## Who runs what, at a glance

| Member | One-time | Before the checkpoints | CP1 | CP2 | CP3 | CP4 |
|---|---|---|---|---|---|---|
| **Member 1** (VM1, Aryan) | – | 0, 4 | – | 7 | 13, 14, 15 | 17 |
| **Member 2** (VM2, Aniket) | A, A3, B | 0, 1, 3 | 5 | 6 | 11 | 16, 19, 21, 22 |
| **Member 3** (VM3, Kruthik) | A, A3, C | 0, 2 | – | – | – | 18, 20 |
| **Member 4** (VM4, Khush) | A, D | 0, 4 | – | 8, 9 | 10, 12 | – |
