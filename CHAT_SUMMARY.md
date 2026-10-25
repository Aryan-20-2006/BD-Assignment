# Chat summary (updated 2026-10-22)

Where we left off with the demo prep for the Distributed Food Ordering
assignment (Kafka KRaft + Spark). To pick up next time, open this file and
say "continue from CHAT_SUMMARY.md".

## Status

- **Code is finished and tested.** The full pipeline gives 62 → 44 → 6 + 4
  rows, and the fingerprints match (`51c22d9a7354`, `28012cc015e4`,
  `d81f97ee2a35`).
- **The TA's 4 checkpoints were all tested on Aryan's laptop** (local cluster)
  using the TA's own commands. All passed, including `kill -9` of broker 2
  mid-run, with the producer still finishing 62/62.
- **`outputs/` currently holds a good main run** (rebuilt 2026-10-22). Step 4
  of the demo deletes it on purpose; any run of the pipeline rebuilds it.
- **Team:** Member 1 = VM1 (Aryan), Member 2 = VM2, Member 3 = VM3,
  Member 4 = VM4.

## What the TA evaluates (from https://bd-2026-eval-a2.notion.site/)

1. **Cluster:** `kafka-broker-api-versions`, `kafka-metadata-quorum describe
   --status` (VM2 = `LeaderId: 1`), `kafka-topics --list`.
2. **Raw orders:** a TA console-consumer observer on `orders`, started before
   Producer 1 (it gives up after 30 s), then `wc -l` / `head -n 2` on
   `orders_landed.jsonl` (62).
3. **Enriched orders:** the same for `order_metrics` before Producer 2, then
   `order_metrics_landed.jsonl` (44). The CSVs are checked on the portal
   `assignment2eval2026.vercel.app` (live-run outputs only).
4. **Broker failure:** a slow producer (`--delay 0.5`); VM3 runs
   `pkill -9 -f kafka.Kafka`; describe; restart in the foreground; describe;
   `kafka-leader-election --election-type preferred`; describe.

Plus: `KAFKA_HOME` and `BS` set in every terminal, old outputs cleared, VM2
never stopped, and an individual viva for every member.

## The main document: `Simple_Guide.pdf` (16 pages)

Built by `tools/make_simple_guide.py`: `python tools/make_simple_guide.py Simple_Guide.pdf`.
Edit the script, not the PDF.

| Pages | Content |
|---|---|
| 1-2 | Big picture, the 4 machines, the spec's rules |
| 3 | Demo day overview: **"What each member runs"** table, what the evaluator checks |
| 4-9 | **Demo commands:** steps 0-4 before the checkpoints, then steps 5-22 for checkpoints 1-4. Each step is tagged with its member (colour-coded), has copyable command boxes and an "Expect" line, plus "Practising alone" boxes |
| 10-13 | Each member's part explained, with a box: your steps / show the evaluator / be ready to explain |
| 14-16 | Failure test explained, key words, viva Q&A, numbers to remember (viva prep) |

**Steps per member:**
- Member 1: 0, 4 | 7 Producer 1 | 13 Consumer 2, 14 wc -l, 15 Spark Job 2 | 17 slow producer
- Member 2: 0, 1, 3 | 5 cluster checks | 6, 11 observers | 16, 19, 21 describe, 22 election
- Member 3: 0, 2 | 18 kill broker, 20 restart broker
- Member 4: 0, 4 | 8 Consumer 1, 9 wc -l | 10 Spark Job 1, 12 Producer 2

## Code changes in this chat

| File | Change |
|---|---|
| `producer/publish.py`, `producer1.py`, `producer2.py` | `--delay` (slow mode: prints each confirmed record), `--file` as an alias of `--input`, retries=30 with a 1 s backoff so the producer survives a leader failover |
| `producer/publish.py`, `consumer/landing.py`, `kafka/topics.sh` | Fall back to the TA's `BS` variable |
| `README.md` | Per-VM install prerequisites, link to the runbook, the `--delay` flag |

## Other files

| File | State |
|---|---|
| `DEMO_RUNBOOK.md`, `practice_alone.sh`, `demo_commands.md` | **Older 0-32 flow** (from before the TA's page); still work, but the step numbers differ from the PDF. The PDF is the one to follow |
| `CHAT_SUMMARY.md` | This file |

## Network (ZeroTier)

- Network ID: `a581878f7d2d3958`. Approve new devices at my.zerotier.com →
  network → Members → tick Auth.
- VM1 (Aryan, Windows) = `10.31.88.84`.
- **VM2 = `10.31.88.79`**: teammate's VMware Ubuntu VM, device `461e94c580`.
- **VM3: waiting for Member 3's new ZeroTier IP.** Member 3 (Luminous) is
  re-joining ZeroTier, so their old entries (`7c69f8d88b` / `10.31.88.36` and
  the duplicate `d84e08aa9d`) are to be removed. The PDF currently shows the
  placeholder `VM3_ZEROTIER_IP` (`VM3_ADDR = "VM3_ZEROTIER_IP:9092"` in
  `tools/make_simple_guide.py`). VM3 is still treated as its own machine:
  Member 3's setup box C, the TA's `pkill -9 -f kafka.Kafka` in step 18, and
  no "VM2 also runs broker 2" workaround. When the new IP arrives, set
  `VM3_ADDR = "<ip>:9092"` and rebuild.
- **Member 4 hasn't joined yet**; until then Aryan's laptop runs Member 4's steps.
- Only VM2's and VM3's IPs go into commands (they're the brokers).

## PDF fix: one-time setup section (added 2026-10-22)

Root cause of the rehearsal problems: the PDF never told VM2/VM3 how to create
`~/broker1.properties` / `~/broker2.properties`, so the teammate used the
localhost practice configs. Section 3 now starts with **"One-time setup (the
day before)"**:
- **A (everyone on a Linux VM):** `ln -sfn "$PWD" ~/BD-Assignment` from the
  repo folder, so `cd ~/BD-Assignment` always works (this was the "No such
  file or directory").
- **B (Member 2):** generate `~/broker1.properties` from `kafka/vm/` with VM2's
  IP, data in `~/kafka-data` (no sudo needed), make the cluster ID, format,
  and run `sudo ufw allow in on zt+`.
- **C (for now, Member 2's machine):** `~/broker2.properties` on port 9094, data
  in `~/kafka-data2`, formatted with the same cluster ID.
- **Member 3's own box** (VM3's IP and Member 2's cluster ID) is hidden while
  VM2 and VM3 share 10.31.88.79; it appears automatically once `VM3_ADDR` in
  `tools/make_simple_guide.py` gets Member 3's own IP. The PDF currently has
  **no placeholders**: box A uses VM2's real repo path
  (`~/distributed-food-ordering/BD-Assignment`, constant `VM2_REPO`).
Tested on Aryan's laptop with 127.0.0.1: both brokers start and advertise the
given IP. Also: all repo scripts are run as `bash kafka/...` (the copy lost its
executable flag → "Permission denied"), and `$KAFKA_HOME/bin/...` commands are
no longer wrapped in quotes (a missed first `"` left bash waiting).

## Two-person rehearsal (2026-10-22): unfinished

The teammate's VM (10.31.88.79) runs both brokers; Aryan runs the VM1 + VM4
steps over ZeroTier.
- Ping works. TCP first **timed out** because `ufw` (the firewall) was on → the
  teammate ran `sudo ufw disable`.
- Their brokers advertised `localhost` → they restarted them with
  `--override listeners=PLAINTEXT://0.0.0.0:9092,...` and
  `--override advertised.listeners=PLAINTEXT://10.31.88.79:9092` (and `:9094`).
- **Last check: "Connection refused"** = the brokers weren't running after the
  restart. Next: the teammate runs `pgrep -af kafka.Kafka`,
  `ss -ltn | grep -E '9092|9093|9094'` and `tail -20 $KAFKA_HOME/logs/kafkaServer.out`,
  then starts broker 1, waits 10 s, and starts broker 2. Success test from
  Aryan's WSL: `nc -zv -w 5 10.31.88.79 9092` says `succeeded`.
- In this setup, step 18 must be `pkill -9 -f broker2.properties` (the TA's
  `pkill -9 -f kafka.Kafka` would kill both brokers). This happened once: all
  ports refused, and the election/describe said "node could not be established".
  Recovery: start broker 1, wait 10 s, start broker 2, then redo from step 16.
  The PDF's step 18 now shows the broker2 command while both brokers share
  10.31.88.79, and switches back to the TA's command once VM3 has its own IP.

## Fixes on Aryan's laptop (WSL)

- `~/.bashrc` sets Java 11 and an old Spark 3.3.4 (`/opt/spark`), which breaks
  Kafka and PySpark. Every terminal needs the Member 1 step 0 box, which has:
  ```bash
  export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
  unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON
  ```
  The `.bashrc` file itself was left unchanged.
- Run everything in a **WSL** terminal (`aryan@Aryan:...$`), not PowerShell
  (`PS C:\...>`). The prompt should show `(.venv-wsl)`.
- `/tmp` is wiped when WSL restarts, so the local cluster needs
  `./kafka/local/cluster.sh format` before `start all`.
- ZeroTier inside WSL was turned off (it clashed with the Windows app). Use
  ZeroTier on Windows only.
- `C:\Users\Aryan` is itself a git repo. Don't commit from it; the project gets
  its own repo.
- Spark's `WARN` lines are normal. Only a `Traceback` is an error.

## Still to do

- [ ] Finish the two-person rehearsal: get the teammate's brokers running and
      reachable (see above), then run PDF steps 5-22 together.
- [ ] Publish the repo with GitHub Desktop (**File → New repository**, name
      `BD-Assignment`, path `C:\Users\Aryan\Desktop`, private), add the
      teammates, and replace `<REPO_URL>` in README.md.
- [ ] Members 3 and 4 install the prerequisites (README) and join ZeroTier;
      update `VM3_ADDR` when Member 3's IP is known.
- [ ] Real VM2/VM3 setup: VM3 is formatted with VM2's cluster ID; both brokers
      advertise their ZeroTier IPs; firewalls allow 9092 (and 9093 on VM2).
- [ ] A full 4-person rehearsal with the PDF.
- [ ] Demo day: everyone runs `git pull` (Member 4 needs the new producer
      code), replace `teamXX` with the team number, and do step 0 in every
      terminal.
- [ ] Viva prep: each member reads their own section (pages 10-13) plus pages 14-16.
- [ ] Optional: split the PDF into `Demo_Commands.pdf` (pages 1-9) and
      `Viva_Guide.pdf` (pages 10-16); bring the runbook and practice script
      in line with the PDF's step numbers.
