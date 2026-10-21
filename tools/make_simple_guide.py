import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Preformatted, KeepTogether, PageBreak)

OUT = sys.argv[1]
BLUE = colors.HexColor("#1f4e79")
LIGHT = colors.HexColor("#dce6f1")
MINE = colors.HexColor("#fff4d6")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=BLUE, fontSize=16, spaceBefore=10, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=BLUE, fontSize=12.5, spaceBefore=8, spaceAfter=4)
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=10, leading=14)
BUL = ParagraphStyle("BUL", parent=B, leftIndent=12, bulletIndent=2)
CELL = ParagraphStyle("CELL", parent=B, fontSize=9, leading=12)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
Q = ParagraphStyle("Q", parent=B, fontName="Helvetica-Bold", textColor=BLUE, spaceBefore=5)
A = ParagraphStyle("A", parent=B, leftIndent=10)
# Diagrams and sample output (for reading, not copying)
CODE = ParagraphStyle("CODE", fontName="Courier", fontSize=8.3, leading=10.5,
                      backColor=colors.HexColor("#f4f4f4"), borderPadding=5, leftIndent=4)
# Commands to copy: one command per line, nothing else in the box
CMD = ParagraphStyle("CMD", fontName="Courier", fontSize=9, leading=12.5,
                     backColor=colors.HexColor("#eef2f7"), borderColor=colors.HexColor("#b8c4d6"),
                     borderWidth=0.6, borderPadding=6, leftIndent=6, rightIndent=6)
STEP = ParagraphStyle("STEP", parent=B, fontName="Helvetica-Bold", fontSize=10.5, textColor=BLUE,
                      spaceBefore=8, spaceAfter=0)
EXP = ParagraphStyle("EXP", parent=B, fontSize=9.5, leading=13, leftIndent=6)

story = []
p = lambda t, s=B: story.append(Paragraph(t, s))
bullets = lambda items: [story.append(Paragraph(i, BUL, bulletText="â€¢")) for i in items]


def table(rows, widths, highlight=None):
    data = [[Paragraph(c, CELLB if r == 0 else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), LIGHT),
          ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b8c4")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if highlight is not None:
        st.append(("BACKGROUND", (0, highlight), (-1, highlight), MINE))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 6))


def qa(q, a):
    story.append(KeepTogether([Paragraph("Q. " + q, Q), Paragraph(a, A)]))


def step(num, title, after, cmds, expect=None):
    head = "Step %s &middot; %s" % (num, title)
    if after:
        head += " <font name='Helvetica' color='#666666' size='9'>&nbsp;&nbsp;start after: %s</font>" % after
    parts = [Paragraph(head, STEP), Spacer(1, 7), Preformatted(cmds, CMD), Spacer(1, 8)]
    if expect:
        parts.append(Paragraph("<b>Expect:</b> " + expect, EXP))
    story.append(KeepTogether(parts))


# ---------------------------------------------------------------- title
story.append(Paragraph("Simple Guide: Distributed Food Ordering", ParagraphStyle(
    "T", parent=ss["Title"], textColor=BLUE, fontSize=20)))
p("<para alignment='center'>Kafka (KRaft) + Spark Batch &middot; Big Data 2026 (UE24CS343AB2) &middot; "
  "Team of 4: Member 1 = VM1, Member 2 = VM2, Member 3 = VM3, Member 4 = VM4</para>")
story.append(Spacer(1, 8))

# ---------------------------------------------------------------- 1
p("1. The whole assignment in one minute", H1)
p("A food delivery app has a file of <b>62 orders</b> (<font face='Courier'>order.jsonl</font>). Some of them are "
  "junk: broken records, cancelled orders, bad timestamps, duplicates. We have to:")
bullets([
    "<b>Send</b> the raw orders through Kafka (VM1 -> VM4).",
    "<b>Clean</b> them and add delivery numbers with Spark (VM4). 62 raw -> <b>44 good orders</b>.",
    "<b>Send</b> the cleaned orders back through Kafka (VM4 -> VM1).",
    "<b>Summarise</b> them with Spark (VM1) into two reports: one per restaurant, one per city.",
    "<b>Prove</b> that Kafka keeps working when one broker (VM3) is switched off.",
])
p("<b>Analogy.</b> Kafka is a <b>post office</b> that stores letters (messages) in labelled mailboxes "
  "(<i>topics</i>). It keeps two copies of every letter, one in each branch (VM2 and VM3), so if one branch closes "
  "the letters are still there. Spark is the <b>calculator</b> each side uses on its own desk after collecting the mail.")

p("The 4 machines", H2)
table([
    ["Member / VM", "Role", "What it does in plain words"],
    ["Member 1 / VM1", "Producer 1, Consumer 2, Spark Job 2",
     "Posts the raw orders into Kafka. Later collects the cleaned orders and makes the two final CSV reports."],
    ["Member 2 / VM2", "Kafka broker 1 + controller",
     "A Kafka server, and also the <b>boss</b> of the cluster: it knows which servers are alive and who is in charge "
     "of each piece of data."],
    ["Member 3 / VM3", "Kafka broker 2",
     "The second Kafka server. Holds a backup copy of everything. This is the one we switch off in the failure test."],
    ["Member 4 / VM4", "Consumer 1, Spark Job 1, Producer 2",
     "Collects the raw orders, cleans them and adds metrics with Spark, then posts the cleaned orders back into Kafka."],
], [30 * mm, 45 * mm, 95 * mm])

p("The flow, step by step", H2)
story.append(Preformatted(
    "  STAGE 1                                     STAGE 2\n"
    "  VM1  producer1.py                           VM4  producer2.py\n"
    "        |  topic: orders  (62 msgs)                 |  topic: order_metrics (44 msgs)\n"
    "        v                                           v\n"
    "  VM4  consumer1.py -> orders_landed.jsonl    VM1  consumer2.py -> order_metrics_landed.jsonl\n"
    "        v                                           v\n"
    "  VM4  spark_job1.py -> order_metrics.jsonl   VM1  spark_job2.py -> restaurant_summary.csv\n"
    "        (clean + enrich, 62 -> 44)                                -> city_summary.csv\n"
    "\n"
    "  Both topics live on the Kafka cluster = VM2 + VM3 (connected over ZeroTier)\n"
    "  Each topic: 2 partitions, replication factor 2", CODE))
story.append(Spacer(1, 6))

p("Rules from the spec (the things examiners check)", H2)
bullets([
    "Spark never reads Kafka directly. A consumer first saves the data to a local <font face='Courier'>.jsonl</font> file; Spark reads that file.",
    "No HDFS. Everything is on the normal local disk (<font face='Courier'>outputs/</font>).",
    "VM4 must not copy its file to VM1. It must go through Kafka (topic <font face='Courier'>order_metrics</font>).",
    "Both topics: <b>2 partitions, replication factor 2</b>, same cluster.",
    "Failure test: stop <b>VM3</b>, never VM2 (VM2 is the only boss).",
    "Exact duplicates counted once in both Spark jobs. All calculated numbers rounded to 2 decimals. Nothing hardcoded.",
])

# ---------------------------------------------------------------- 2 member 1
p("2. Member 1 (VM1): Producer 1, Consumer 2, Spark Job 2", H1)
p("Member 1 runs three programs: <b>producer1.py</b> at the start, then later <b>consumer2.py</b> and "
  "<b>spark_job2.py</b> at the end. Two shared helper files sit behind them: <font face='Courier'>publish.py</font> "
  "and <font face='Courier'>landing.py</font>.")

p("2.1 producer1.py: post the raw orders", H2)
p("Reads <font face='Courier'>order.jsonl</font> line by line and sends each line to topic <b>orders</b>. All of the "
  "real work is in the shared helper <font face='Courier'>publish.py</font>.")
bullets([
    "<b>Sends every line as-is, junk included.</b> The producer only delivers; cleaning is Spark Job 1's job. "
    "If both did some cleaning, the rules would be split across two places.",
    "<b>No key.</b> To get a key (order_id) it would have to read the JSON, and some lines are broken. Without a key "
    "Kafka spreads messages randomly over the 2 partitions (e.g. 31 / 31, and the split changes each run).",
    "<b>acks=\"all\"</b>: Kafka only says \"received\" once <i>every</i> in-sync copy has the message. This is the safest setting.",
    "<b>retries=10</b>: if something hiccups (e.g. VM3 goes down mid-send), it tries again automatically.",
    "<b>linger_ms=10</b>: waits up to 10 ms to bundle messages together, so fewer network trips.",
    "It waits for confirmation of every message (<font face='Courier'>flush()</font> + <font face='Courier'>f.get()</font>), "
    "so the printed \"62 sent\" means 62 <i>confirmed</i>, along with which partition each one landed in.",
])

p("2.2 consumer2.py + landing.py: collect the cleaned orders", H2)
p("Reads <i>everything</i> from topic <b>order_metrics</b> and saves it to "
  "<font face='Courier'>order_metrics_landed.jsonl</font> (44 lines). Member 4's consumer1.py is the same code with topic <b>orders</b>.")
bullets([
    "<b>Reads all partitions itself</b> (<font face='Courier'>assign()</font>, no consumer group). A consumer group "
    "remembers where it stopped, so a second run would get nothing. We want the <i>whole</i> topic every time.",
    "<b>Always starts from the beginning</b> (<font face='Courier'>seek_to_beginning</font>, offset 0).",
    "<b>Knows when to stop.</b> Normal consumers run forever. Ours stops once it has reached the last message of "
    "every partition <i>and</i> nothing new has arrived for 10 s (<font face='Courier'>--idle-timeout</font>).",
    "<b>Can start early.</b> <font face='Courier'>--wait-timeout</font> (default 120 s) lets it wait for the producer.",
    "<b>Overwrites the file</b> (<font face='Courier'>\"w\"</font> mode), so running it twice doesn't double the data.",
    "Prints how many records came from each partition: <b>16 from partition 0, 28 from partition 1</b>.",
])

p("2.3 spark_job2.py: make the two reports", H2)
p("Reads <font face='Courier'>order_metrics_landed.jsonl</font> and writes <b>restaurant_summary.csv</b> "
  "(6 rows) and <b>city_summary.csv</b> (4 rows).")
table([
    ["Step", "What happens", "Why"],
    ["1. Read", "Read the file with a fixed schema (types given up front)",
     "Types are guaranteed and the file is read only once"],
    ["2. Dedup", "<font face='Courier'>dropDuplicates</font> on all 15 columns",
     "Spec: exact duplicates count once. Removes 0 here because Job 1 already did it, but it protects against a producer being run twice"],
    ["3. Group", "groupBy restaurant_id, then groupBy city",
     "The two analytics the spec asks for"],
    ["4. Compute", "count, averages, delayed count (rows where status = DELAYED), delay_rate_pct = 100 x delayed / count",
     "delay_rate is worked out from the exact counts, and rounded only once at the end"],
    ["5. Round", "<font face='Courier'>F.round(..., 2)</font> on every calculated number", "Spec rule"],
    ["6. Sort + write", "Sort the rows, collect them (just 10 rows) and write with Python's csv module",
     "Spark's own writer makes a <i>folder</i> of part-files, but the spec wants one file with an exact name"],
], [24 * mm, 76 * mm, 70 * mm])
p("<font face='Courier'>.cache()</font> keeps the deduplicated data in memory because it is used by two reports. "
  "Without it Spark would recompute it for each one.")

p("2.4 Final outputs (know these by heart)", H2)
table([
    ["restaurant", "orders", "avg amount", "avg prep", "avg delivery", "delayed", "delay %"],
    ["R01", "8", "548.5", "13.13", "22.0", "4", "50.0"],
    ["R02", "8", "539.25", "13.38", "27.0", "8", "100.0"],
    ["R03", "7", "664.0", "13.86", "32.0", "4", "57.14"],
    ["R04", "7", "639.57", "12.14", "37.0", "7", "100.0"],
    ["R05", "7", "615.14", "12.0", "42.0", "3", "42.86"],
    ["R06", "7", "712.14", "13.43", "47.0", "7", "100.0"],
], [24 * mm, 18 * mm, 24 * mm, 22 * mm, 26 * mm, 20 * mm, 22 * mm])
table([
    ["city", "orders", "avg amount", "avg delivery", "delayed", "delay %"],
    ["Bengaluru (R01+R02)", "16", "543.88", "24.5", "12", "75.0"],
    ["Hyderabad (R06)", "7", "712.14", "47.0", "7", "100.0"],
    ["Mumbai (R03+R04)", "14", "651.79", "34.5", "11", "78.57"],
    ["Pune (R05)", "7", "615.14", "42.0", "3", "42.86"],
], [44 * mm, 18 * mm, 26 * mm, 28 * mm, 20 * mm, 22 * mm])
p("<b>Easy cross-check:</b> each restaurant is in exactly one city, so Pune = R05 and Hyderabad = R06. "
  "Bengaluru = R01 + R02: 8+8 = 16 orders, 4+8 = 12 delayed, 12/16 = 75%. Order counts add up to 44; delayed "
  "orders add up to 33 of 44. Example: R05 delay % = 100 x 3 / 7 = 42.857 -> <b>42.86</b>.")
p("Member 1's demo commands are in section 7.")

# ---------------------------------------------------------------- 3 members 2-4
story.append(PageBreak())
p("3. Members 2, 3 and 4: what they do", H1)

p("Member 2 (VM2): Broker 1 + KRaft controller (the boss)", H2)
bullets([
    "Runs Kafka with <font face='Courier'>process.roles=broker,controller</font>, <font face='Courier'>node.id=1</font>.",
    "<b>KRaft</b> = Kafka manages itself, with no separate ZooKeeper. The controller keeps the cluster's \"register\" "
    "(which brokers are alive, which topics exist, who leads each partition).",
    "Port <b>9092</b> = normal Kafka traffic, port <b>9093</b> = controller traffic (only VM2 has it).",
    "Generates the <b>cluster ID</b> once; VM3 must use the same ID to join.",
    "<font face='Courier'>min.insync.replicas=1</font>: writes still succeed with only one copy alive (needed while VM3 is off).",
    "<font face='Courier'>auto.create.topics.enable=false</font>: topics are only created on purpose, so a typo can't create a wrong topic.",
])

p("Member 3 (VM3): Broker 2 (the backup)", H2)
bullets([
    "Runs Kafka with <font face='Courier'>process.roles=broker</font> only, <font face='Courier'>node.id=2</font>.",
    "Points at VM2:9093 to join and is formatted with <b>VM2's cluster ID</b> (it must not create its own cluster).",
    "Holds the second copy of every partition. In the failure test, <b>this is the machine that gets stopped</b>.",
])

p("Member 4 (VM4): Consumer 1, Spark Job 1, Producer 2 (the cleaning step)", H2)
bullets([
    "<b>consumer1.py</b>: same code as consumer2, but reads topic <b>orders</b> -> <font face='Courier'>orders_landed.jsonl</font> (62 lines).",
    "<b>spark_job1.py</b>: the heart of the project. It <b>throws away bad records</b>, <b>removes duplicates</b>, and "
    "<b>adds 7 new columns</b>. Output: <font face='Courier'>order_metrics.jsonl</font> (44 lines).",
    "<b>producer2.py</b>: posts those 44 lines to topic <b>order_metrics</b>, <b>keyed by order_id</b>. The same key always "
    "goes to the same partition, so the split is always <b>16 / 28</b>.",
])
p("<b>Cleaning funnel: 62 -> 48 -> 44</b>")
table([
    ["Thrown out because...", "Count"],
    ["status is not DELIVERED (T04X0001-6: cancelled, pending, failed, refunded)", "6"],
    ["no order_id (2 \"invalid_order_record\" lines)", "2"],
    ["missing fields ({\"order_id\":\"BROKEN\"} and a T040002 copy without a city)", "2"],
    ["bad timestamp (T040005 \"bad\", T040003 \"not-a-timestamp\")", "2"],
    ["distance_km &lt;= 0 (T040001: -2) and order_amount &lt;= 0 (T040004: 0)", "2"],
    ["<b>Total dropped -> 48 valid</b>", "<b>14</b>"],
    ["Exact duplicates removed (T040006, T040017, T040028, T040039) -> <b>44</b>", "4"],
], [145 * mm, 25 * mm])
p("<b>New columns Spark Job 1 adds</b> (all in minutes, rounded to 2 decimals):")
table([
    ["Column", "Formula"],
    ["preparation_time_min", "picked_up - accepted"],
    ["delivery_time_min", "delivered - picked_up"],
    ["fulfillment_time_min", "delivered - order_timestamp"],
    ["delivery_speed_kmph", "distance_km / (delivery_time_min / 60)"],
    ["delay_min", "max(0, delivered - expected)"],
    ["delivery_status", "ON_TIME if delay = 0, else DELAYED"],
    ["delay_category", "0 ON_TIME | up to 15 SLIGHT | up to 30 MODERATE | over 30 SEVERE"],
], [50 * mm, 120 * mm])
p("<b>Midnight trick:</b> it uses full date+time, not just the time of day. T040023 picked up 23:20 and delivered "
  "00:02 the next day = <b>42 min</b>, not -1398. The time zone is set to UTC so daylight saving can't shift anything.")

p("The failure test (whole team)", H2)
story.append(Preformatted(
    "Before (both up):    orders P0  Leader: 2  Replicas: 2,1  Isr: 2,1\n"
    "                     orders P1  Leader: 1  Replicas: 1,2  Isr: 1,2\n"
    "After stopping VM3:  orders P0  Leader: 1  Replicas: 2,1  Isr: 1     <- leader moved to 1\n"
    "                     orders P1  Leader: 1  Replicas: 1,2  Isr: 1\n"
    "Restart VM3 -> Isr back to 2,1 / 1,2.", CODE))
p("<b>Leader</b> = the broker currently serving that partition. <b>Replicas</b> = where copies are <i>supposed</i> "
  "to live (doesn't change). <b>Isr</b> = copies that are currently up to date (shrinks to just 1 while VM3 is off).")
p("<b>Why the counts grow:</b> Kafka keeps old messages, so each run adds to the topics: orders 62 -> 124 -> 186, "
  "order_metrics 44 -> 88 -> 132. Those extra copies are exact duplicates, so Job 1 still outputs <b>44</b> and the "
  "CSVs are byte-identical (checked with <font face='Courier'>diff</font>).")

# ---------------------------------------------------------------- 4 glossary
p("4. Key words in one line each", H1)
table([
    ["Term", "Simple meaning"],
    ["Broker", "A Kafka server that stores messages (VM2, VM3)."],
    ["Controller", "The boss broker that tracks who is alive and picks leaders (only VM2)."],
    ["KRaft", "Kafka's built-in way of electing and storing the boss's records. It replaced ZooKeeper."],
    ["Topic", "A named mailbox: <i>orders</i>, <i>order_metrics</i>."],
    ["Partition", "A topic is split into pieces (we use 2) so work can be shared. Order is kept only inside one partition."],
    ["Offset", "A message's position number inside a partition (0, 1, 2 ...)."],
    ["Replication factor 2", "Every partition is stored twice, once on each broker."],
    ["Leader / follower", "The leader copy handles reads and writes; the follower copies it."],
    ["ISR", "In-Sync Replicas: the copies that are fully up to date."],
    ["acks=all", "The producer gets \"OK\" only when all in-sync copies have the message."],
    ["Bootstrap servers", "The first broker address(es) a client contacts to discover the whole cluster."],
    ["advertised.listeners", "The address a broker tells clients to use. It must be the ZeroTier IP, not localhost."],
    ["ZeroTier", "A virtual LAN, so the 4 laptops on different home networks can reach each other."],
    ["local[*]", "Spark runs on this one machine, using all CPU cores."],
    ["Lazy evaluation", "Spark only plans the work; it runs when an action (count, collect) is called."],
], [42 * mm, 128 * mm])

# ---------------------------------------------------------------- 5 viva
p("5. Top viva questions, short answers", H1)
qa("Why use Kafka instead of just copying files?",
   "It separates the stages (VM1 and VM4 never talk directly), stores the data reliably in two copies, and lets "
   "any stage re-read the data. The spec also forbids copying the file.")
qa("Why is Producer 1 unkeyed but Producer 2 keyed?",
   "Raw lines may be broken JSON, so Producer 1 doesn't read them to find a key. Cleaned lines are always valid, so "
   "Producer 2 keys by order_id, which gives a fixed partition split (16/28).")
qa("Why doesn't the consumer use a consumer group?",
   "Groups remember where they stopped, so a second run would read nothing. Ours is a batch job that must copy the "
   "whole topic every time, so it reads all partitions from offset 0 and commits nothing.")
qa("How does the consumer know when to stop?",
   "When its position equals the last offset of every partition and nothing new has arrived for 10 s.")
qa("What happens when VM3 stops?",
   "VM3 stops sending heartbeats, the controller on VM2 removes it from the ISR and makes broker 1 the leader "
   "everywhere. Broker 1 already has a full copy (RF 2), so no data is lost.")
qa("Why stop VM3 and not VM2?",
   "VM2 is the only controller. Without it nobody can elect leaders. Real high availability needs 3 controllers.")
qa("Can you still produce while VM3 is down?",
   "Yes. acks=all only waits for the in-sync copies (now just broker 1), and min.insync.replicas=1 allows that.")
qa("What if Producer 1 runs twice?",
   "The topic has 124 messages, but Spark Job 1 still outputs 44 because duplicates are exact and get removed. "
   "Delivery is at-least-once, which is why both jobs dedupe.")
qa("Why collect() and write the CSV with Python?",
   "Spark's writer makes a folder of part-files. The spec wants single files with exact names, and the results are tiny (6 and 4 rows).")
qa("Why is dropDuplicates in Job 2 if it removes 0?",
   "The spec says both jobs must dedupe. It also protects against Kafka redelivery or a producer re-run.")
qa("Why not deduplicate by order_id?",
   "The spec says <i>exact</i> duplicates. Choosing between two different records with the same ID would be "
   "inventing a business rule.")
qa("How do you know the outputs are correct?",
   "tests/verify_outputs.py redoes everything in plain Python (no Spark) and compares every value. It prints "
   "\"OK: 44 enriched records and both summaries match\".")
qa("Why Spark for only 62 records?",
   "The assignment is about the architecture. The same code would work on millions of rows or on a real cluster.")

# ---------------------------------------------------------------- 6 cheat sheet
p("6. Numbers to remember", H1)
table([
    ["Item", "Value"],
    ["Raw lines", "62"],
    ["Dropped by cleaning", "14  ->  48 valid"],
    ["Exact duplicates removed", "4  ->  44 enriched"],
    ["orders partition split", "random, e.g. 31 / 31"],
    ["order_metrics partition split", "always 16 / 28"],
    ["Restaurants / cities", "6 (R01-R06) / 4 (Bengaluru, Hyderabad, Mumbai, Pune)"],
    ["Delayed orders", "33 of 44 (11 on time)"],
    ["Delay categories", "ON_TIME 11, SLIGHT 11, MODERATE 15, SEVERE 7"],
    ["Highest / lowest delay %", "100% (R02, R04, R06, Hyderabad) / 42.86% (R05, Pune)"],
    ["Fastest / slowest delivery", "R01 22.0 min / R06 47.0 min"],
    ["Node IDs / ports", "VM2 = node 1 (9092 + 9093); VM3 = node 2 (9092)"],
    ["Versions", "Kafka 4.3.1 (KRaft), PySpark 4.2.0, kafka-python 2.2.15, Java 17+"],
], [55 * mm, 115 * mm])

# ---------------------------------------------------------------- 7 demo day
story.append(PageBreak())
p("7. Demo day: who does what", H1)
p("Run the steps <b>in number order</b>. Each member runs only their own steps and says <b>\"done\"</b> "
  "when they finish, then the next member starts. The same commands are in "
  "<font face='Courier'>DEMO_RUNBOOK.md</font> in the repo.")
p("<b>Copying commands:</b> copy one grey box at a time and paste it into the terminal. Every line in a box "
  "is a real command. A line ending in <font face='Courier'>\\</font> continues on the next line, so copy both "
  "lines together. Replace <font face='Courier'>VM2_ZEROTIER_IP</font> and "
  "<font face='Courier'>VM3_ZEROTIER_IP</font> with the real IPs.")

p("Order of turns", H2)
table([
    ["Steps", "Member", "What happens"],
    ["1", "Member 2", "Start broker 1 + controller"],
    ["2", "Member 3", "Start broker 2"],
    ["3-4", "Member 2", "Check both brokers, create fresh topics"],
    ["5-6", "Members 1 + 4", "Clear old outputs, check brokers are reachable"],
    ["7", "Member 1", "Producer 1"],
    ["8-10", "Member 4", "Consumer 1, Spark Job 1, Producer 2"],
    ["11-13", "Member 1", "Consumer 2, Spark Job 2, verify  (graded outputs)"],
    ["14", "Member 2", "Show topics before the failure"],
    ["15", "Member 3", "Stop broker 2"],
    ["16", "Member 2", "Show topics after the failure"],
    ["17", "Member 1", "Producer 1 with VM3 down"],
    ["18-20", "Member 4", "Consumer 1, Spark Job 1, Producer 2 with VM3 down"],
    ["21-23", "Member 1", "Consumer 2, Spark Job 2, compare results"],
    ["24", "Member 3", "Restart broker 2"],
    ["25", "Member 2", "Show VM3 rejoined the ISR"],
    ["26", "Member 1", "Producer 1"],
    ["27-29", "Member 4", "Consumer 1, Spark Job 1, Producer 2"],
    ["30-32", "Member 1", "Consumer 2, Spark Job 2, compare results  (demo finished)"],
], [22 * mm, 32 * mm, 116 * mm])

p("What the evaluator checks", H2)
table([
    ["TA checks", "Steps", "Who shows it", "Evidence on screen"],
    ["Cluster is up, 2 brokers", "3", "Member 2", "<font face='Courier'>id: 1</font> and <font face='Courier'>id: 2</font>"],
    ["Topic config", "4, 14", "Member 2", "PartitionCount 2, ReplicationFactor 2, Isr 1,2"],
    ["Pipeline output (accuracy)", "7-13", "Members 1 + 4", "62 -> 44 -> 6 + 4 rows; verify says OK"],
    ["ISR / leaders after VM3 stops", "15-16", "Members 3 + 2", "Leader 1, Isr 1 everywhere; 4 under-replicated"],
    ["Pipeline continues with VM3 down", "17-23", "Members 1 + 4", "124 landed, 44 enriched, 88 landed, SAME RESULTS"],
    ["VM3 rejoins the ISR", "24-25", "Members 3 + 2", "Isr back to 1,2; under-replicated list empty"],
    ["Pipeline after recovery", "26-32", "Members 1 + 4", "186, 44, 132, SAME RESULTS"],
], [52 * mm, 15 * mm, 27 * mm, 76 * mm])

p("Before you start (everyone)", H2)
bullets([
    "<font face='Courier'>git pull</font> so every VM has the same code. ZeroTier connected; you can "
    "<font face='Courier'>ping</font> VM2's ZeroTier IP.",
    "Run your <b>setup</b> box in <b>every</b> terminal you'll use.",
    "Never stop VM2. Don't edit <font face='Courier'>order.jsonl</font>.",
    "Spark's <font face='Courier'>WARN</font> lines are normal. Only a <font face='Courier'>Traceback</font> means a failure.",
    "Keep each command's output on screen until the evaluator has seen it.",
])


def member_header(title, steps, show, explain):
    story.append(PageBreak())
    p(title, H1)
    p("<b>Your steps:</b> " + steps)
    p("<b>Show the evaluator:</b> " + show)
    p("<b>Be ready to explain:</b> " + explain)


SETUP_TAIL = ("export B1=VM2_ZEROTIER_IP:9092\n"
              "export B2=VM3_ZEROTIER_IP:9092\n"
              "export BS=$B1\n"
              "export BOOTSTRAP=$B1,$B2\n"
              "export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2")
CLEAR = ("rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test\n"
         "mkdir -p outputs/failover_test outputs/recovery_test")
NC = "nc -zv VM2_ZEROTIER_IP 9092\nnc -zv VM3_ZEROTIER_IP 9092"
UNDER = ("$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $B1 \\\n"
         "    --describe --under-replicated-partitions")

# ---------------- Member 1
member_header(
    "Member 1 (VM1): Producer 1, Consumer 2, Spark Job 2",
    "0, 5, 6, 7, 11, 12, 13, 17, 21, 22, 23, 26, 30, 31, 32. You start and finish every run.",
    "62 published; 44 landed (16 / 28); 6 + 4 rows; verify OK; both CSVs; "
    "<font face='Courier'>SAME RESULTS</font> after the failure and after recovery.",
    "why Producer 1 has no key; why the consumer reads every partition from offset 0 and stops by itself; "
    "how Job 2 dedupes, groups and rounds; why the counts grow to 88 and 132 while the CSVs stay the same.")
step(0, "Setup (every terminal)", None,
     "cd /mnt/c/Users/Aryan/Desktop/BD-Assignment\n"
     "source .venv-wsl/bin/activate\n"
     "export KAFKA_HOME=~/kafka\n"
     "export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64\n"
     "unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON\n" + SETUP_TAIL,
     "the prompt starts with <font face='Courier'>(.venv-wsl)</font>.")
step(5, "Clear old outputs", "Member 2, step 4", CLEAR)
step(6, "Check the brokers are reachable", "step 5", NC, "<font face='Courier'>succeeded</font> twice.")
step(7, "Producer 1", "step 6", "python producer/producer1.py --input order.jsonl",
     "<font face='Courier'>published 62 records</font>.")
step(11, "Consumer 2", "Member 4, step 10",
     "python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl",
     "<font face='Courier'>landed 44 records</font>, partition 0: 16, partition 1: 28.")
step(12, "Spark Job 2", "step 11",
     "python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \\\n"
     "    --output-dir outputs",
     "<font face='Courier'>6 rows -> restaurant_summary.csv</font> and <font face='Courier'>4 rows -> city_summary.csv</font>.")
step(13, "Verify and show the results", "step 12",
     "python tests/verify_outputs.py --raw order.jsonl \\\n"
     "    --metrics outputs/order_metrics_landed.jsonl\n"
     "cat outputs/restaurant_summary.csv outputs/city_summary.csv",
     "<font face='Courier'>OK: 44 enriched records ...</font> and the two tables from section 2.4.")
step(17, "Producer 1 with VM3 down", "Member 2, step 16",
     "python producer/producer1.py --bootstrap-servers $B1 --input order.jsonl",
     "<font face='Courier'>published 62 records</font>, so writes still work.")
step(21, "Consumer 2 with VM3 down", "Member 4, step 20",
     "python consumer/consumer2.py --bootstrap-servers $B1 \\\n"
     "    --output outputs/failover_test/order_metrics_landed.jsonl",
     "<font face='Courier'>landed 88 records</font> (44 old + 44 new).")
step(22, "Spark Job 2 with VM3 down", "step 21",
     "python spark/spark_job2.py --input outputs/failover_test/order_metrics_landed.jsonl \\\n"
     "    --output-dir outputs/failover_test",
     "<font face='Courier'>exact duplicates removed: 44</font>, then 6 + 4 rows.")
step(23, "Show the results are unchanged", "step 22",
     "diff outputs/restaurant_summary.csv outputs/failover_test/restaurant_summary.csv\n"
     "diff outputs/city_summary.csv outputs/failover_test/city_summary.csv \\\n    && echo \"SAME RESULTS\"",
     "<font face='Courier'>SAME RESULTS</font>. Tell Member 3 to restart the broker.")
step(26, "Producer 1 after recovery", "Member 2, step 25",
     "python producer/producer1.py --input order.jsonl",
     "<font face='Courier'>published 62 records</font>.")
step(30, "Consumer 2 after recovery", "Member 4, step 29",
     "python consumer/consumer2.py --output outputs/recovery_test/order_metrics_landed.jsonl",
     "<font face='Courier'>landed 132 records</font>.")
step(31, "Spark Job 2 after recovery", "step 30",
     "python spark/spark_job2.py --input outputs/recovery_test/order_metrics_landed.jsonl \\\n"
     "    --output-dir outputs/recovery_test",
     "6 + 4 rows.")
step(32, "Show the results are unchanged", "step 31",
     "diff outputs/restaurant_summary.csv outputs/recovery_test/restaurant_summary.csv\n"
     "diff outputs/city_summary.csv outputs/recovery_test/city_summary.csv \\\n    && echo \"SAME RESULTS\"",
     "<font face='Courier'>SAME RESULTS</font>. <b>Demo finished.</b>")

# ---------------- Member 2
member_header(
    "Member 2 (VM2): Broker 1 + KRaft controller",
    "0, 1, 3, 4, 14, 16, 25. You show the cluster state.",
    "both broker ids; topics with 2 partitions and RF 2; Isr 1,2 before, then Leader 1 / Isr 1 after VM3 stops, "
    "then Isr 1,2 again after it restarts.",
    "KRaft and what the controller does; node.id, listeners vs advertised.listeners, ports 9092/9093; "
    "cluster ID; min.insync.replicas=1; Leader vs Replicas vs Isr; why VM2 can't be stopped.")
step(0, "Setup (every terminal)", None,
     "cd ~/BD-Assignment\n"
     "export KAFKA_HOME=~/kafka\n" + SETUP_TAIL)
step(1, "Start broker 1 and the controller", "step 0",
     "$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker1.properties",
     "no output. Tell Member 3 to start.")
step(3, "Check both brokers joined", "Member 3, step 2",
     "$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server $B1 | grep \"id:\"",
     "two lines, <font face='Courier'>id: 1</font> and <font face='Courier'>id: 2</font>.")
step(4, "Create fresh topics", "step 3",
     "./kafka/topics.sh delete\n"
     "sleep 5\n"
     "./kafka/topics.sh create",
     "both topics with <font face='Courier'>PartitionCount: 2</font>, <font face='Courier'>ReplicationFactor: 2</font>, "
     "Isr 1,2. Tell Members 1 and 4 to start.")
step(14, "Show the topics before the failure", "Member 1, step 13",
     "./kafka/topics.sh describe\n" + UNDER,
     "Isr lists 1 and 2 on every partition; the second command prints nothing.")
step(16, "Show the topics after the failure", "Member 3, step 15",
     "sleep 15\n"
     "BOOTSTRAP=$B1 ./kafka/topics.sh describe\n" + UNDER,
     "<font face='Courier'>Leader: 1</font> and <font face='Courier'>Isr: 1</font> on every partition; "
     "the second command lists all 4 partitions. Tell Member 1 to start.")
step(25, "Show VM3 rejoined", "Member 3, step 24",
     "sleep 15\n"
     "./kafka/topics.sh describe\n" + UNDER,
     "Isr lists 1 and 2 again; the second command prints nothing. Leader may stay 1 for a few minutes; "
     "that's normal. Tell Member 1 to start.")

# ---------------- Member 3
member_header(
    "Member 3 (VM3): Broker 2",
    "0, 2, 15, 24. Your broker is the one that fails.",
    "the broker stopping and starting again. Then point to Member 2's describe output, where Isr shrinks to 1 "
    "and grows back to 1,2.",
    "what happens step by step when VM3 stops (heartbeats stop, it's fenced, leadership moves to broker 1); "
    "how it catches up and rejoins the ISR; why VM3 uses VM2's cluster ID; what RF 2 protects against.")
step(0, "Setup (every terminal)", None,
     "cd ~/BD-Assignment\n"
     "export KAFKA_HOME=~/kafka")
step(2, "Start broker 2", "Member 2, step 1",
     "$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties",
     "no output. Tell Member 2.")
step(15, "Stop broker 2 (the failure)", "Member 2, step 14",
     "$KAFKA_HOME/bin/kafka-server-stop.sh",
     "the broker stops. Tell Member 2.")
step(24, "Restart broker 2 (recovery)", "Member 1, step 23",
     "$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties",
     "no output. Tell Member 2.")

# ---------------- Member 4
member_header(
    "Member 4 (VM4): Consumer 1, Spark Job 1, Producer 2",
    "0, 5, 6, 8, 9, 10, 18, 19, 20, 27, 28, 29. You do the middle of every run.",
    "62 landed; the drop report (14 dropped, 48 valid, 4 duplicates, 44 written); 44 published, split 16 / 28; "
    "still 44 enriched with VM3 down.",
    "each cleaning rule and the 62 -> 48 -> 44 funnel; the 7 new columns and the midnight case (T040023 = 42 min); "
    "why Producer 2 is keyed by order_id; why Job 1 still gives 44 from 124 lines.")
step(0, "Setup (every terminal)", None,
     "cd ~/BD-Assignment\n"
     "source .venv/bin/activate\n"
     "export KAFKA_HOME=~/kafka\n" + SETUP_TAIL,
     "the prompt starts with <font face='Courier'>(.venv)</font>. If Spark later fails with "
     "<font face='Courier'>'JavaPackage' object is not callable</font>, run "
     "<font face='Courier'>unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON</font>.")
step(5, "Clear old outputs", "Member 2, step 4", CLEAR)
step(6, "Check the brokers are reachable", "step 5", NC, "<font face='Courier'>succeeded</font> twice.")
step(8, "Consumer 1", "Member 1, step 7",
     "python consumer/consumer1.py --output outputs/orders_landed.jsonl",
     "<font face='Courier'>landed 62 records</font>.")
step(9, "Spark Job 1", "step 8",
     "python spark/spark_job1.py --input outputs/orders_landed.jsonl \\\n"
     "    --output outputs/order_metrics.jsonl",
     "<font face='Courier'>valid records: 48</font>, <font face='Courier'>exact duplicates removed: 4</font>, "
     "<font face='Courier'>enriched records written: 44</font>.")
step(10, "Producer 2", "step 9",
     "python producer/producer2.py --input outputs/order_metrics.jsonl",
     "<font face='Courier'>published 44 records</font>, partition 0: 16, partition 1: 28. Tell Member 1.")
step(18, "Consumer 1 with VM3 down", "Member 1, step 17",
     "python consumer/consumer1.py --bootstrap-servers $B1 \\\n"
     "    --output outputs/failover_test/orders_landed.jsonl",
     "<font face='Courier'>landed 124 records</font> (62 old + 62 new).")
step(19, "Spark Job 1 with VM3 down", "step 18",
     "python spark/spark_job1.py --input outputs/failover_test/orders_landed.jsonl \\\n"
     "    --output outputs/failover_test/order_metrics.jsonl",
     "still <font face='Courier'>enriched records written: 44</font>.")
step(20, "Producer 2 with VM3 down", "step 19",
     "python producer/producer2.py --bootstrap-servers $B1 \\\n"
     "    --input outputs/failover_test/order_metrics.jsonl",
     "<font face='Courier'>published 44 records</font>. Tell Member 1.")
step(27, "Consumer 1 after recovery", "Member 1, step 26",
     "python consumer/consumer1.py --output outputs/recovery_test/orders_landed.jsonl",
     "<font face='Courier'>landed 186 records</font>.")
step(28, "Spark Job 1 after recovery", "step 27",
     "python spark/spark_job1.py --input outputs/recovery_test/orders_landed.jsonl \\\n"
     "    --output outputs/recovery_test/order_metrics.jsonl",
     "<font face='Courier'>enriched records written: 44</font>.")
step(29, "Producer 2 after recovery", "step 28",
     "python producer/producer2.py --input outputs/recovery_test/order_metrics.jsonl",
     "<font face='Courier'>published 44 records</font>. Tell Member 1.")


def footer(c, d):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawString(18 * mm, 10 * mm, "Distributed Food Ordering - Simple Guide")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, "Page %d" % d.page)
    c.restoreState()


SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                  topMargin=16 * mm, bottomMargin=16 * mm,
                  title="Simple Guide - Distributed Food Ordering").build(
    story, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
