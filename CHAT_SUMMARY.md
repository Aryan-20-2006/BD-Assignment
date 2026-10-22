# Chat summary (2026-10-21)

Where we left off with the demo prep for the Distributed Food Ordering
assignment (Kafka KRaft + Spark). To pick up next time, open this file and
say "continue from CHAT_SUMMARY.md".

## Status

- **Code is finished.** On 2026-10-21 a full solo rehearsal passed: the main
  run, the run with VM3 stopped, and the recovery run, all with identical CSVs.
- **Team:** Member 1 = VM1 (Aryan), Member 2 = VM2, Member 3 = VM3,
  Member 4 = VM4.

## Files made or changed in this chat

| File | What it is |
|---|---|
| `DEMO_RUNBOOK.md` | **The demo script.** Steps 0-32, each labelled with the VM that runs it, plus "Alone" commands for solo practice |
| `practice_alone.sh` | Runs all 33 steps on one laptop: `bash practice_alone.sh` in WSL (~10 min) |
| `Simple_Guide.pdf` | Plain-English guide for the team. Section 2 = demo-day overview; section 3 = the demo flow, steps 0-32 in order, each tagged with its member (colour-coded), with "Practising alone" boxes; sections 4-7 = what each member's part does |
| `tools/make_simple_guide.py` | Rebuilds the PDF: `python tools/make_simple_guide.py Simple_Guide.pdf` (edit this, don't edit the PDF) |
| `README.md` | Added per-VM install prerequisites and a link to the runbook |
| `demo_commands.md` | Detailed reference and troubleshooting; step 10 now has the full failure and recovery test |
| `producer/publish.py`, `consumer/landing.py`, `kafka/topics.sh` | Also accept the TA's `BS` variable |

## TA evaluation page (2026-10-22): 4 checkpoints

Source: https://bd-2026-eval-a2.notion.site/ (TA's "A2 Evaluation" page).
Simple_Guide.pdf section 3 now holds only the commands these need: steps 0-4
before the checkpoints, then steps 5-22 for the checkpoints, each tagged by member.
Section 2 has a "What each member runs" table:
1. Cluster: `kafka-broker-api-versions`, `kafka-metadata-quorum describe --status`
   (VM2 = LeaderId 1), `kafka-topics --list`.
2. TA console-consumer observer on `orders` (started before Producer 1, gives up
   after 30 s), then `wc -l` / `head -n 2` on `orders_landed.jsonl` (62).
3. The same for `order_metrics` before Producer 2; `order_metrics_landed.jsonl` (44).
4. Slow producer `producer1.py --file order.jsonl --delay 0.5`; VM3 runs
   `pkill -9 -f kafka.Kafka`; describe; restart in the foreground with
   `KAFKA_HEAP_OPTS=...`; describe; `kafka-leader-election --election-type
   preferred`; describe.

Code change for this: producers now take `--delay` (and `--file` as an alias of
`--input`), and retry 30 times, 1 s apart, so they survive a leader failover.
Tested locally with the TA's commands: broker 2 was killed with kill -9 after 2
records; the producer still published all 62 with no error, and the election
restored the leaders.

`DEMO_RUNBOOK.md`, `practice_alone.sh` and `demo_commands.md` still describe the
**older** 0-32 flow; the PDF is the up-to-date one.

## Older failure-test plan (superseded by the checkpoints above)

1. Before: topic config, and Isr has both brokers (step 14).
2. VM3 stopped: Leader 1, Isr 1 everywhere (steps 15-16).
3. The pipeline still runs with VM3 down, into `outputs/failover_test/`
   (steps 17-23).
4. VM3 restarted: Isr back to 1,2, and the pipeline runs again into
   `outputs/recovery_test/` (steps 24-32).

The topic counts grow 62 → 124 → 186 and 44 → 88 → 132, because Kafka keeps
the old messages. Spark removes the exact duplicates, so the output is always
44 records and the same CSVs. VM2 is never stopped.

## Fixes on Aryan's laptop (WSL)

- `~/.bashrc` sets Java 11 and an old Spark 3.3.4 (`/opt/spark`), which
  breaks Kafka and PySpark. Every terminal needs:
  ```bash
  export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
  unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON
  ```
  This is already in the runbook's VM1 setup and in `practice_alone.sh`. The
  `.bashrc` file itself was left unchanged.
- ZeroTier inside WSL was turned off because it clashed with the Windows app.
  Use ZeroTier on Windows only.
- `C:\Users\Aryan` is itself a git repo. Don't commit from it; the project
  gets its own repo.
- The `WARN` lines from Spark are normal. Only a `Traceback` is an error.

## ZeroTier

- Network ID: `a581878f7d2d3958`.
- VM1 (Aryan, Windows) = `10.31.88.84`. **VM2 = `10.31.88.79`** (Linux, device
  `461e94c580`; ping from WSL works), already filled in to Simple_Guide.pdf.
  VM3 and VM4 haven't joined yet. **For now VM2's machine also runs VM3's
  broker on port 9094**, so the PDF uses `B2=10.31.88.79:9094`. When Member 3
  joins, change `VM3_ADDR` near the top of `tools/make_simple_guide.py` to
  `"<VM3 IP>:9092"` and rebuild the PDF (the temporary note disappears by itself).
- Approve new devices at my.zerotier.com → network → Members → tick Auth.

## Still to do

- [ ] Publish the repo with GitHub Desktop: **File → New repository**, name
      `BD-Assignment`, path `C:\Users\Aryan\Desktop`, private. Then add the
      teammates as collaborators.
- [ ] Replace `<REPO_URL>` in README.md with the real link.
- [ ] Teammates install the prerequisites (README) and join ZeroTier; VM2 and
      VM3 share their ZeroTier IPs.
- [ ] VM2/VM3 format Kafka once (VM3 uses VM2's cluster ID), as described in
      demo_commands.md section 4.
- [ ] At least one full team rehearsal over ZeroTier with DEMO_RUNBOOK.md.
- [ ] Demo day: everyone runs `git pull` and clears old outputs (step 5).
- [ ] Viva prep for everyone: Simple_Guide.pdf sections 8-11, and the
      "be ready to explain" box in each member's section (4-7).
