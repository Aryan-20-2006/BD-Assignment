"""Build Simple_Guide.pdf: python tools/make_simple_guide.py Simple_Guide.pdf"""
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
                      spaceBefore=10, spaceAfter=0)
EXP = ParagraphStyle("EXP", parent=B, fontSize=9.5, leading=13, leftIndent=6)
BOX = ParagraphStyle("BOX", parent=B, backColor=colors.HexColor("#fff4d6"), borderPadding=6,
                     borderColor=colors.HexColor("#e6c983"), borderWidth=0.6, leftIndent=6, rightIndent=6)

# One colour per member, used for the tag on every demo step
MEMBER_COLOUR = {"1": "#1565c0", "2": "#2e7d32", "3": "#c62828", "4": "#6a1b9a", "all": "#444444"}

story = []
p = lambda t, s=B: story.append(Paragraph(t, s))
bullets = lambda items: [story.append(Paragraph(i, BUL, bulletText="\u2022")) for i in items]
C = lambda t: "<font face='Courier'>%s</font>" % t


def tag(who):
    """Coloured member label, e.g. tag('1') or tag('1+4')."""
    if who == "all":
        return "<font color='%s'>EVERYONE</font>" % MEMBER_COLOUR["all"]
    parts = who.split("+")
    label = "MEMBER " + " + ".join(parts) if len(parts) == 1 else "MEMBERS " + " + ".join(parts)
    vms = " / ".join("VM" + x for x in parts)
    return "<font color='%s'>%s (%s)</font>" % (MEMBER_COLOUR[parts[0]], label, vms)


def table(rows, widths):
    data = [[Paragraph(c, CELLB if r == 0 else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0b8c4")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t)
    story.append(Spacer(1, 6))


def qa(q, a):
    story.append(KeepTogether([Paragraph("Q. " + q, Q), Paragraph(a, A)]))


def summary_box(steps, show, explain):
    """Yellow box at the end of a member's explanation."""
    story.append(Spacer(1, 6))
    p("<b>Your steps (section 3):</b> %s<br/><b>Show the evaluator:</b> %s<br/>"
      "<b>Be ready to explain:</b> %s" % (steps, show, explain), BOX)
    story.append(Spacer(1, 6))


def step(num, who, title, cmds, expect=None, alone=None, boxes=None, fix=None):
    """One demo step in flow order.

    cmds  - the demo-day command box
    alone - optional different box for practising on one laptop
    boxes - optional list of (label, cmds) used instead of cmds (step 0)
    """
    parts = [Paragraph("Step %s &middot; %s &middot; %s" % (num, tag(who), title), STEP), Spacer(1, 7)]
    if boxes is None:
        boxes = [(None, cmds)]
        if alone:
            boxes = [("<b>Demo day:</b>", cmds),
                     ("<b>Practising alone</b> (one laptop, local cluster):", alone)]
    for label, text in boxes:
        if label:
            parts += [Paragraph(label, EXP), Spacer(1, 6)]
        parts += [Preformatted(text, CMD), Spacer(1, 8)]
    if expect:
        parts.append(Paragraph("<b>Expect:</b> " + expect, EXP))
    if fix:
        parts += [Spacer(1, 3), Paragraph("<b>If it fails:</b> " + fix, EXP)]
    story.append(KeepTogether(parts))


# Broker addresses (ZeroTier IP:port). Change these two lines when the team changes.
# For now VM2's machine also plays VM3 (second broker on port 9094) until Member 3 joins;
# then set VM3_ADDR = "<VM3's ZeroTier IP>:9092".
VM1_ADDR = "10.31.88.84"   # Member 1's laptop (only connects out; not used in commands)
VM2_ADDR = "10.31.88.79:9092"
# Two versions from one source:
#   python tools/make_simple_guide.py Simple_Guide.pdf                      -> 4 VMs, VM3 = Kruthik
#   python tools/make_simple_guide.py Simple_Guide_Practice.pdf --practice  -> Aniket runs VM2 + VM3 on one
#                                                                              machine (broker 2 on 9094)
PRACTICE = "--practice" in sys.argv
# Practice now: Aryan = VM1 + VM4, Aniket = VM2, Kruthik = VM3 (separate VMs, like the demo).
# For VM2 + VM3 on Aniket's one machine instead, use "10.31.88.79:9094" here.
VM3_ADDR = "10.31.88.161:9092"
REPO_URL = "https://github.com/Aryan-20-2006/BD-Assignment.git"   # everyone clones this to ~/BD-Assignment

SETUP_TAIL = ("export B1=%s\n"
              "export B2=%s\n"
              "export BS=$B1\n"
              "export BOOTSTRAP=$B1,$B2\n"
              "export KAFKA_BOOTSTRAP_SERVERS=$B1,$B2") % (VM2_ADDR, VM3_ADDR)
# Same exports, for the local two-broker cluster (broker 2 on 9094)
SETUP_TAIL_ALONE = SETUP_TAIL.replace(VM2_ADDR, "localhost:9092").replace(VM3_ADDR, "localhost:9094")
M1_SETUP = ("cd /mnt/c/Users/Aryan/Desktop/BD-Assignment\n"
            "source .venv-wsl/bin/activate\n"
            "export KAFKA_HOME=~/kafka\n"
            "export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64\n"
            "unset SPARK_HOME HADOOP_HOME HADOOP_CONF_DIR PYSPARK_PYTHON PYSPARK_DRIVER_PYTHON\n")
# git pull keeps every VM on the latest code and guide (Member 1 is the one who pushes changes)
M23_SETUP = "cd ~/BD-Assignment\ngit pull\nexport KAFKA_HOME=~/kafka\n"
M4_SETUP = "cd ~/BD-Assignment\ngit pull\nsource .venv/bin/activate\nexport KAFKA_HOME=~/kafka\n"
CLEAR = ("rm -rf outputs/*.jsonl outputs/*.csv outputs/failover_test outputs/recovery_test\n"
         "mkdir -p outputs/failover_test outputs/recovery_test")
UNDER = ("$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $B1 \\\n"
         "    --describe --under-replicated-partitions")

# ================================================================ title
story.append(Paragraph("Simple Guide: Distributed Food Ordering", ParagraphStyle(
    "T", parent=ss["Title"], textColor=BLUE, fontSize=20)))
p("<para alignment='center'>Kafka (KRaft) + Spark Batch &middot; Big Data 2026 (UE24CS343AB2) &middot; "
  "Team of 4: Member 1 = VM1, Member 2 = VM2, Member 3 = VM3, Member 4 = VM4</para>")
p("<para alignment='center'><b>%s</b></para>" % (
    "PRACTICE VERSION (3 people): Aryan runs VM1 <u>and</u> VM4's steps (with Member 1's step 0 box), "
    "Aniket = VM2 (10.31.88.79), Kruthik = VM3 (10.31.88.161). For the real 4-person demo use Simple_Guide.pdf."
    if PRACTICE else
    "DEMO VERSION: 4 separate VMs (VM2 = 10.31.88.79, VM3 = 10.31.88.161). "
    "For practice with 3 people (Aryan also doing VM4) use Simple_Guide_Practice.pdf."))
story.append(Spacer(1, 6))
table([
    ["Section", "What's in it"],
    ["1. Big picture", "What the assignment does, the 4 machines, the rules"],
    ["2. Demo day overview", "Order of turns, what the evaluator checks, before you start"],
    ["3. Demo commands", "<b>What to run before the checkpoints, then each checkpoint's commands</b> (steps 0-22), tagged by member"],
    ["4-7. Members 1-4", "What each member's part does, and what they show and explain"],
    ["8-11", "Failure test explained, key words, viva questions, numbers to remember"],
], [45 * mm, 125 * mm])

# ================================================================ 1 big picture
p("1. The whole assignment in one minute", H1)
p("A food delivery app has a file of <b>62 orders</b> (" + C("order.jsonl") + "). Some of them are "
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
    "Spark never reads Kafka directly. A consumer first saves the data to a local " + C(".jsonl") + " file; Spark reads that file.",
    "No HDFS. Everything is on the normal local disk (" + C("outputs/") + ").",
    "VM4 must not copy its file to VM1. It must go through Kafka (topic " + C("order_metrics") + ").",
    "Both topics: <b>2 partitions, replication factor 2</b>, same cluster.",
    "Failure test: stop <b>VM3</b>, never VM2 (VM2 is the only boss).",
    "Exact duplicates counted once in both Spark jobs. All calculated numbers rounded to 2 decimals. Nothing hardcoded.",
])

# ================================================================ 2 demo day overview
story.append(PageBreak())
p("2. Demo day overview", H1)
p("The evaluator checks <b>4 checkpoints</b>. Section 3 has only the commands needed for them: first what to run "
  "<b>before</b> the checkpoints, then each checkpoint's commands in order. Each step says which member runs it; "
  "when you finish, say <b>\"done\"</b> and the member with the next step starts.")

p("What each member runs", H2)
table([
    ["Member", "Before the checkpoints", "Checkpoint 1", "Checkpoint 2", "Checkpoint 3", "Checkpoint 4"],
    ["<b>Member 1</b> (VM1)", "0 setup, 4 clear outputs", "-", "7 Producer 1",
     "13 Consumer 2, 14 wc -l, 15 Spark Job 2", "17 slow producer"],
    ["<b>Member 2</b> (VM2)", "0 setup, 1 start broker 1, 3 fresh topics", "5 cluster checks", "6 observer",
     "11 observer", "16 describe, 19 describe, 21 describe, 22 election"],
    ["<b>Member 3</b> (VM3)", "0 setup, 2 start broker 2", "-", "-", "-", "18 kill broker, 20 restart broker"],
    ["<b>Member 4</b> (VM4)", "0 setup, 4 clear outputs", "-", "8 Consumer 1, 9 wc -l",
     "10 Spark Job 1, 12 Producer 2", "-"],
], [24 * mm, 36 * mm, 22 * mm, 26 * mm, 32 * mm, 30 * mm])

p("What the evaluator checks", H2)
table([
    ["Checkpoint", "Steps", "Evidence on screen"],
    ["<b>1.</b> Brokers reachable, VM2 is the controller, topics exist", "5",
     "ids 1 and 2; " + C("LeaderId: 1") + "; " + C("orders") + " and " + C("order_metrics")],
    ["<b>2.</b> Raw orders flow VM1 -> VM4", "6-9", "observer prints 3 records; " + C("wc -l") + " = 62"],
    ["<b>3.</b> Enriched orders flow VM4 -> VM1", "10-15",
     "observer prints 3 records; " + C("wc -l") + " = 44; the two CSVs (accuracy checked on the portal)"],
    ["<b>4.</b> Broker failure and recovery", "16-22",
     "Isr 1,2 -> kill VM3 -> Leader 1 / Isr 1 while the slow producer keeps sending -> restart -> Isr 1,2 -> "
     "election puts the leaders back"],
], [62 * mm, 16 * mm, 92 * mm])
p("<b>Output accuracy</b> is graded from this live run only, on the portal "
  + C("assignment2eval2026.vercel.app") + ".")

p("Before you start (everyone)", H2)
bullets([
    C("git pull") + " so every VM has the same code. ZeroTier connected; you can " + C("ping")
    + " VM2's ZeroTier IP.",
    "Use a <b>Linux / WSL terminal</b>, not PowerShell. The prompt must look like "
    + C("user@machine:...$") + ", not " + C("PS C:\\...>") + ".",
    "Do step 0 in <b>every</b> terminal you'll use.",
    "Repo scripts are run as " + C("bash kafka/...sh") + ". If you see " + C("Permission denied")
    + " for " + C("./kafka/...") + ", the copy lost its executable flag: run "
    + C("chmod +x kafka/*.sh kafka/local/*.sh practice_alone.sh") + " once, or put " + C("bash")
    + " in front.",
    "Never stop VM2. Don't edit " + C("order.jsonl") + ".",
    "Spark's " + C("WARN") + " lines are normal. Only a " + C("Traceback") + " means a failure.",
])

# ================================================================ 3 demo flow
story.append(PageBreak())
p("3. Demo commands, in order", H1)
p("<b>Demo day:</b> go down the list. Run only the steps tagged with your member number.")
p("<b>Practising alone</b> (one laptop): run <b>every</b> step, whatever its tag, using the \"Practising alone\" "
  "box where there is one. Steps 6, 11 and 17 keep running, so do the next step in a second terminal "
  "(with step 0 done in it too).")
p("<b>Copying:</b> copy one grey box at a time. A line ending in " + C("\\") + " continues on the next line, so "
  "copy both lines together. The broker addresses are already filled in: VM2 = " + C(VM2_ADDR) + ", VM3 = "
  + C(VM3_ADDR) + ". In the observer commands, replace " + C("teamXX") + " with your team number.")
if VM2_ADDR.split(":")[0] == VM3_ADDR.split(":")[0]:
    p("<b>For now VM2's machine also runs VM3's broker</b> (second broker on port 9094), because Member 3 hasn't "
      "joined yet. That machine does the one-time setup box marked \"for now\" below, then runs both Member 2's "
      "and Member 3's steps. Step 18 is " + C("pkill -9 -f broker2.properties")
      + " for now, because the TA's " + C("pkill -9 -f kafka.Kafka") + " would kill both brokers. "
      "Member 4 hasn't joined either, so Member 1's laptop runs Member 4's steps too, with Member 1's step 0 box.",
      BOX)

# ---------------------------------------------------------------- one-time setup (the day before)
VM2_IP = VM2_ADDR.split(":")[0]
VM3_IP = VM3_ADDR.split(":")[0]
SAME_HOST = VM2_IP == VM3_IP
DATA_SED = '-e "s#/var/lib/kafka/data#$HOME/kafka-data#"'

p("One-time setup (the day before, not in front of the TA)", H2)
p("Do this once per machine. It gets the code and creates the broker config files that steps 1, 2 and 20 use, "
  "with the right ZeroTier IPs already in them, so the brokers never announce " + C("localhost") + ".")
p("<b>Git in one minute.</b> Our project lives on GitHub: " + C("github.com/Aryan-20-2006/BD-Assignment")
  + ". " + C("git clone") + " downloads the whole project folder once (box A). " + C("git pull")
  + " downloads only what has changed since (box A2, and the first lines of step 0). You don't need a GitHub "
  "account, and you never need to upload anything: Member 1 does that. Open a terminal on Ubuntu with "
  "<b>Ctrl+Alt+T</b>. When " + C("sudo") + " asks for a password, it's your VM's login password, and nothing "
  "appears on screen while you type it; that's normal.")
step("A", "all", "Get the code with git, into ~/BD-Assignment (Linux VMs)",
     "sudo apt install -y git\n"
     "cd ~\n"
     "[ -L ~/BD-Assignment ] && rm ~/BD-Assignment\n"
     "git clone %s ~/BD-Assignment\n"
     "ls ~/BD-Assignment/kafka" % REPO_URL,
     "the " + C("ls") + " lists " + C("local  topics.sh  vm") + ". Everyone now has the same folder, "
     + C("~/BD-Assignment") + ", so every " + C("cd ~/BD-Assignment") + " in this guide works. The third line only "
     "removes an old shortcut with that name, never a real folder. An old zip copy elsewhere can stay; it's no "
     "longer used. <b>Member 4</b> then does box D (Java and Python). Member 1 (WSL) skips this box.",
     fix=C("already exists and is not empty") + ": a real folder is already called " + C("~/BD-Assignment")
     + ". Rename it with " + C("mv ~/BD-Assignment ~/BD-Assignment-old") + " and run the " + C("git clone")
     + " line again.")
step("A2", "all", "Get updates (before every practice and on demo morning)",
     "cd ~/BD-Assignment\n"
     "git pull",
     C("Already up to date.") + " or a list of changed files. Member 1 publishes changes from GitHub Desktop "
     "(Commit, then Push).",
     fix=C("Your local changes ... would be overwritten") + ": run " + C("git stash") + ", then " + C("git pull")
     + " again.")
step("B", "2", "Broker 1 config, cluster ID, storage, firewall",
     "export KAFKA_HOME=~/kafka\n"
     "cd ~/BD-Assignment\n"
     "$KAFKA_HOME/bin/kafka-server-stop.sh\n"
     "while pgrep -f kafka.Kafka > /dev/null; do sleep 1; done\n"
     'sed -e "s/VM2_ADDRESS/%s/g" %s \\\n'
     "    kafka/vm/vm2-broker1.properties > ~/broker1.properties\n"
     "grep -E \"voters|advertised|log.dirs\" ~/broker1.properties\n"
     "$KAFKA_HOME/bin/kafka-storage.sh random-uuid > ~/cluster.id\n"
     "cat ~/cluster.id\n"
     '$KAFKA_HOME/bin/kafka-storage.sh format -t "$(cat ~/cluster.id)" -c ~/broker1.properties\n'
     "sudo ufw allow in on zt+" % (VM2_IP, DATA_SED),
     "the " + C("grep") + " shows " + C(VM2_IP) + " (not " + C("VM2_ADDRESS") + " or " + C("localhost")
     + ") and " + C("log.dirs=/home/...") + "; " + C("cat") + " prints the cluster ID: <b>send it to Member 3</b>; "
     + C("format") + " ends with " + C("Formatting ...") + ". The " + C("ufw") + " line lets ZeroTier traffic "
     "through the firewall. If " + C("format") + " says the directory is already formatted, run "
     + C("rm -rf ~/kafka-data") + " and repeat that line. Box B makes a <b>new</b> cluster ID each time, so if "
     "you run it again, redo box C too.")
if SAME_HOST:
    step("C", "2", "For now: broker 2 on the same machine (port 9094)",
         "cd ~/BD-Assignment\n"
         'sed -e "s/VM2_ADDRESS/%s/g" -e "s/VM3_ADDRESS:9092/%s/" \\\n'
         '    -e "s#0.0.0.0:9092#0.0.0.0:9094#" -e "s#/var/lib/kafka/data#$HOME/kafka-data2#" \\\n'
         "    kafka/vm/vm3-broker2.properties > ~/broker2.properties\n"
         "grep -E \"listeners|voters|log.dirs\" ~/broker2.properties\n"
         '$KAFKA_HOME/bin/kafka-storage.sh format -t "$(cat ~/cluster.id)" -c ~/broker2.properties'
         % (VM2_IP, VM3_ADDR),
         "the " + C("grep") + " shows " + C("0.0.0.0:9094") + ", " + C(VM3_ADDR) + " and "
         + C("log.dirs=/home/.../kafka-data2") + ". Then run steps 1 and 2 below on this machine. "
         "If " + C("format") + " says it's already formatted, or box B was run again (new cluster ID), run "
         + C("rm -rf ~/kafka-data2") + " and repeat the " + C("format") + " line. "
         "When Member 3 joins, they get their own setup box here and broker 2 moves to their VM.")
# Member 3's own box only appears once VM3 is a separate machine (VM3_ADDR has its own IP).
if not SAME_HOST:
  step("C", "3", "Broker 2 config and storage (on VM3)",
     "export KAFKA_HOME=~/kafka\n"
     "cd ~/BD-Assignment\n"
     "$KAFKA_HOME/bin/kafka-server-stop.sh\n"
     "while pgrep -f kafka.Kafka > /dev/null; do sleep 1; done\n"
     'sed -e "s/VM2_ADDRESS/%s/g" -e "s/VM3_ADDRESS/%s/g" \\\n'
     "    %s \\\n"
     "    kafka/vm/vm3-broker2.properties > ~/broker2.properties\n"
     "grep -E \"voters|advertised|log.dirs\" ~/broker2.properties\n"
     "$KAFKA_HOME/bin/kafka-storage.sh format -t CLUSTER_ID_FROM_MEMBER_2 \\\n"
     "    -c ~/broker2.properties\n"
     "sudo ufw allow in on zt+" % (VM2_IP, VM3_IP if not SAME_HOST else "VM3_ZEROTIER_IP", DATA_SED),
     "the " + C("grep") + " shows VM2's IP in " + C("voters") + " and VM3's IP in " + C("advertised")
     + ". Replace " + C("CLUSTER_ID_FROM_MEMBER_2") + " with the ID Member 2 sent. Never run "
     + C("random-uuid") + " on VM3. The first two lines stop any Kafka already running on this VM (e.g. a "
     "test setup); it's not part of our cluster.",
     fix=C("already formatted") + " on the " + C("format") + " line: old storage from an earlier test is in "
     + C("~/kafka-data") + ". Run " + C("rm -rf ~/kafka-data") + " and repeat the " + C("format") + " line.")

step("D", "4", "Java, Python and the project's packages (after box A)",
     "sudo apt update\n"
     "sudo apt install -y openjdk-21-jre-headless python3-venv python3-pip\n"
     "java -version\n"
     "cd ~/BD-Assignment\n"
     "python3 -m venv .venv\n"
     "source .venv/bin/activate\n"
     "pip install -r requirements.txt\n"
     'python -c "import pyspark, kafka; print(pyspark.__version__, kafka.__version__)"',
     C("java -version") + " shows 21 (17 or higher is fine). " + C("pip install") + " takes a few minutes "
     "(about 400 MB). The last line prints " + C("4.2.0 2.2.15") + ". Member 4 needs no Kafka install: Java is "
     "for Spark Job 1, Python for the consumer, Spark and producer.",
     fix=C("No module named venv") + " or " + C("ensurepip is not available") + ": the " + C("apt install")
     + " line didn't finish; run it again. " + C("No module named 'pyspark'") + " on the last line: "
     + C("pip install") + " failed or ran without " + C("(.venv)") + " in the prompt; run the "
     + C("source") + " and " + C("pip") + " lines again.")

p("Before the checkpoints", H2)
step(0, "all", "Set up the terminal (every terminal you use)", None,
     "the prompt starts with " + C("(.venv-wsl)") + " (Member 1) or " + C("(.venv)") + " (Member 4).",
     fix=C("No such file or directory") + " on the " + C("cd") + " line: the repo is in another folder, so do "
     "one-time box A. " + C("python: command not found") + " later: this box wasn't run in that terminal, so run "
     "it again. A " + C(">") + " prompt where nothing happens: part of a line (often a quote) was missed when "
     "copying, so press Ctrl+C and copy the whole box again.",
     boxes=[("<b>Member 1 (VM1):</b>", M1_SETUP + SETUP_TAIL),
            ("<b>Members 2 and 3 (VM2, VM3):</b>", M23_SETUP + SETUP_TAIL),
            ("<b>Member 4 (VM4):</b>", M4_SETUP + SETUP_TAIL),
            ("<b>Practising alone</b> (one laptop, local cluster):", M1_SETUP + SETUP_TAIL_ALONE)])
step(1, "2", "Start broker 1 and the controller",
     "$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker1.properties",
     "no output. (Alone: " + C("format") + " is needed after every WSL restart and is safe to repeat.)",
     fix="if the broker doesn't come up and " + C("$KAFKA_HOME/logs/kafkaServer.out") + " says "
     + C("class file versions up to 55.0") + ", Java is too old: run "
     + C("export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64") + " and start it again.",
     alone="bash kafka/local/cluster.sh format\nbash kafka/local/cluster.sh start 1")
step(2, "3", "Start broker 2",
     "$KAFKA_HOME/bin/kafka-server-start.sh -daemon ~/broker2.properties",
     "no output.",
     alone="bash kafka/local/cluster.sh start 2")
step(3, "2", "Create fresh topics",
     "bash kafka/topics.sh delete\nsleep 10\nbash kafka/topics.sh create",
     "both topics with " + C("PartitionCount: 2") + ", " + C("ReplicationFactor: 2") + ", Isr 1,2.",
     fix=C("replication factor of 2 cannot be reached because only 1 broker(s) are registered")
     + ": broker 2 isn't in this cluster yet. " + (
         "Do one-time box C (with the cluster ID from box B) and step 2 on this machine; "
         if SAME_HOST else "Member 3 does one-time box C and step 2; ")
     + "check with step 5 that both " + C("id: 1") + " and " + C("id: 2") + " appear, then run this again."
     + ("" if SAME_HOST else " Never start " + C("broker2.properties") + " on VM2 to get around it.")
     + " " + C("Topic 'orders' does not exist as expected")
     + ": the old topic was still being deleted; run " + C("bash kafka/topics.sh create") + " again. "
     + C("Permission denied") + ": type it with " + C("bash") + " in front, as here (or run "
     + C("chmod +x kafka/*.sh kafka/local/*.sh") + " once). " + C("Connection to node ... could not be "
     "established") + ": a broker isn't running, so redo steps 1 and 2.")
step(4, "1+4", "Clear old outputs", CLEAR,
     "no output. The TA only accepts outputs made during the live run.")

p("Checkpoint 1: cluster", H2)
step(5, "2", "Brokers reachable, VM2 is the controller, topics exist",
     '$KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server "$BS" | grep "id:"\n'
     '$KAFKA_HOME/bin/kafka-metadata-quorum.sh --bootstrap-server "$BS" describe --status\n'
     '$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --list',
     "two brokers, " + C("id: 1") + " and " + C("id: 2") + "; " + C("LeaderId: 1") + " (VM2 is the controller); "
     + C("orders") + " and " + C("order_metrics") + ".",
     fix="the brokers are shown as " + C("localhost") + ": the configs from one-time boxes B and C aren't being "
     "used, so redo them, then steps 1 and 2. " + C("Connection to node -1 ... could not be established")
     + " or " + C("Connection refused") + ": broker 1 isn't running, so run step 1, wait 10 s, then step 2. "
     + C("timed out") + ": the broker machine's firewall is blocking, so run " + C("sudo ufw allow in on zt+")
     + " there.")

p("Checkpoint 2: raw orders, VM1 -> Kafka -> VM4", H2)
step(6, "2", "Observer on orders (leave it running)",
     '$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \\\n'
     '    --topic orders --group ta-observer-teamXX-run1 \\\n'
     '    --consumer-property auto.offset.reset=latest \\\n'
     '    --max-messages 3 --timeout-ms 30000',
     "it waits, and gives up after 30 s, so step 7 must start right away. The " + C("deprecated")
     + " warning is harmless.",
     fix="it ends with " + C("Processed a total of 0 messages") + ": step 7 started too late. Run this again, "
     "then step 7 straight away.")
step(7, "1", "Producer 1",
     "python producer/producer1.py --input order.jsonl",
     C("published 62 records") + "; the observer prints 3 records and " + C("Processed a total of 3 messages") + ".",
     fix=C("python: command not found") + ": run your step 0 box in this terminal. " + C("NoBrokersAvailable")
     + " or " + C("KafkaTimeoutError") + ": this laptop can't use the brokers; step 5 must show "
     + C(VM2_ADDR.split(":")[0]) + " for both brokers (not " + C("localhost") + "), and step 0 must have been run "
     "here.")
step(8, "4", "Consumer 1",
     "python consumer/consumer1.py --output outputs/orders_landed.jsonl",
     C("landed 62 records") + ".")
step(9, "4", "Show the landed file",
     "wc -l outputs/orders_landed.jsonl && head -n 2 outputs/orders_landed.jsonl",
     C("62 outputs/orders_landed.jsonl") + " and two order lines.")

p("Checkpoint 3: enriched orders, VM4 -> Kafka -> VM1", H2)
step(10, "4", "Spark Job 1",
     "python spark/spark_job1.py --input outputs/orders_landed.jsonl \\\n"
     "    --output outputs/order_metrics.jsonl",
     C("enriched records written: 44") + ".",
     fix=C("'JavaPackage' object is not callable") + ": an old Spark install is being picked up; run the "
     + C("unset ...") + " line from Member 1's step 0 box, then run this again.")
step(11, "2", "Observer on order_metrics (leave it running)",
     '$KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server "$BS" \\\n'
     '    --topic order_metrics --group ta-observer-teamXX-run2 \\\n'
     '    --consumer-property auto.offset.reset=latest \\\n'
     '    --max-messages 3 --timeout-ms 30000',
     "it waits; step 12 must start within 30 s.",
     fix="it ends with " + C("Processed a total of 0 messages") + ": step 12 started too late. Run this again, "
     "then step 12 straight away.")
step(12, "4", "Producer 2",
     "python producer/producer2.py --input outputs/order_metrics.jsonl",
     C("published 44 records") + "; the observer prints 3 records.")
step(13, "1", "Consumer 2",
     "python consumer/consumer2.py --output outputs/order_metrics_landed.jsonl",
     C("landed 44 records") + ".")
step(14, "1", "Show the landed file",
     "wc -l outputs/order_metrics_landed.jsonl && head -n 2 outputs/order_metrics_landed.jsonl",
     C("44 outputs/order_metrics_landed.jsonl") + " and two enriched lines.")
step(15, "1", "Spark Job 2 (the final CSVs)",
     "python spark/spark_job2.py --input outputs/order_metrics_landed.jsonl \\\n"
     "    --output-dir outputs",
     C("6 rows -> restaurant_summary.csv") + " and " + C("4 rows -> city_summary.csv")
     + ". If the TA wants to see them: " + C("cat outputs/restaurant_summary.csv outputs/city_summary.csv") + ".",
     fix=C("'JavaPackage' object is not callable") + ": an old Spark install is being picked up; run the "
     + C("unset ...") + " line from Member 1's step 0 box, then run this again.")

p("Checkpoint 4: broker failure and recovery", H2)
step(16, "2", "Leaders and ISR before the failure",
     '$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders',
     C("Isr: 1,2") + " / " + C("2,1") + " on both partitions.")
step(17, "1", "Slow producer (leave it running)",
     "python producer/producer1.py --file order.jsonl --delay 0.5",
     "one line per record, " + C("sent 1/62 -> partition ...") + ", every half second. Keep it on screen: after "
     "the kill in step 18 it pauses briefly, then carries on to " + C("sent 62/62") + " and "
     + C("published 62 records") + " with no error. That is the pipeline continuity the TA checks.")
if VM2_ADDR.split(":")[0] == VM3_ADDR.split(":")[0]:
    # Both brokers share one machine for now: the TA's `pkill -9 -f kafka.Kafka` would kill broker 1 and the
    # controller too, so kill only broker 2's process.
    step(18, "3", "Kill broker 2 (while step 17 is still sending)",
         "pkill -9 -f broker2.properties",
         "no output; only broker 2 dies. <b>Not</b> the TA's " + C("pkill -9 -f kafka.Kafka")
         + " here: on this shared machine it would kill broker 1 and the controller as well. Once VM3 is its own "
         "machine, the TA's command is the one to use there.")
else:
    step(18, "3", "Kill the broker (while step 17 is still sending)",
         "pkill -9 -f kafka.Kafka",
         "no output. <b>Never run this on VM2.</b>",
         alone="pkill -9 -f broker2.properties")
step(19, "2", "Leaders and ISR after the failure",
     "sleep 10\n"
     '$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders',
     C("Leader: 1") + " and " + C("Isr: 1") + " on both partitions. A " + C("WARN ... Connection to node 2 ... "
     "could not be established") + " line is normal here: broker 2 is the one that's down.",
     fix="the describe never finishes and every node fails: both brokers died (the TA's "
     + C("pkill -9 -f kafka.Kafka") + " on a machine that runs both). Run steps 1 and 2, then redo from step 16.")
step(20, "3", "Restart the broker in a second terminal (leave it open)",
     "KAFKA_HEAP_OPTS='-Xmx512m -Xms512m' $KAFKA_HOME/bin/kafka-server-start.sh \\\n"
     "    ~/broker2.properties",
     "it keeps printing log lines (some " + C("WARN") + " ones are normal), including "
     + C("Kafka Server started") + ", and doesn't return to the prompt. Run it in a <b>separate terminal</b> "
     "(with step 0 done) and don't close it or press Ctrl+C: that stops broker 2 again.",
     fix="it returns to the prompt by itself: broker 2 didn't start; the last lines it printed say why.",
     alone="bash kafka/local/cluster.sh start 2")
step(21, "2", "Leaders and ISR after the restart",
     "sleep 15\n"
     '$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders',
     C("Isr: 1,2") + " again; leaders are still all 1. Don't go on to step 22 until it says so.",
     fix="still " + C("Isr: 1") + ": broker 2 isn't running. Check the step 20 terminal is still open and "
     "printing; if not, run step 20 again, wait 15 s, and repeat this step.")
step(22, "2", "Leader election, then check again",
     '$KAFKA_HOME/bin/kafka-leader-election.sh --bootstrap-server "$BS" \\\n'
     '    --election-type preferred --all-topic-partitions\n'
     '$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BS" --describe --topic orders',
     C("Successfully completed leader election") + "; the leaders are back to how they were in step 16. "
     "<b>Demo finished.</b> (Alone: " + C("bash kafka/local/cluster.sh stop all") + ".)",
     fix="many " + C("PreferredLeaderNotAvailableException") + " lines and " + C("Isr: 1") + " in the "
     "describe: broker 2 isn't back yet (the preferred leader of partition 0 is broker 2). Do step 20 again in "
     "its own terminal, wait until step 21 shows " + C("Isr: 1,2") + ", then run this again. "
     + C("Connection to node ... could not be established") + " and it never finishes: broker 1 is down too, so "
     "run step 1, wait 10 s, run step 2, then steps 21 and 22 again.")

# ================================================================ 4 member 1
story.append(PageBreak())
p("4. Member 1 (VM1): Producer 1, Consumer 2, Spark Job 2", H1)
p("Member 1 runs three programs: <b>producer1.py</b> at the start, then later <b>consumer2.py</b> and "
  "<b>spark_job2.py</b> at the end. Two shared helper files sit behind them: " + C("publish.py")
  + " and " + C("landing.py") + ".")

p("4.1 producer1.py: post the raw orders", H2)
p("Reads " + C("order.jsonl") + " line by line and sends each line to topic <b>orders</b>. All of the "
  "real work is in the shared helper " + C("publish.py") + ".")
bullets([
    "<b>Sends every line as-is, junk included.</b> The producer only delivers; cleaning is Spark Job 1's job. "
    "If both did some cleaning, the rules would be split across two places.",
    "<b>No key.</b> To get a key (order_id) it would have to read the JSON, and some lines are broken. Without a key "
    "Kafka spreads messages randomly over the 2 partitions (e.g. 31 / 31, and the split changes each run).",
    "<b>acks=\"all\"</b>: Kafka only says \"received\" once <i>every</i> in-sync copy has the message. This is the safest setting.",
    "<b>retries=10</b>: if something hiccups (e.g. VM3 goes down mid-send), it tries again automatically.",
    "<b>linger_ms=10</b>: waits up to 10 ms to bundle messages together, so fewer network trips.",
    "It waits for confirmation of every message (" + C("flush()") + " + " + C("f.get()") + "), "
    "so the printed \"62 sent\" means 62 <i>confirmed</i>, along with which partition each one landed in.",
])

p("4.2 consumer2.py + landing.py: collect the cleaned orders", H2)
p("Reads <i>everything</i> from topic <b>order_metrics</b> and saves it to " + C("order_metrics_landed.jsonl")
  + " (44 lines). Member 4's consumer1.py is the same code with topic <b>orders</b>.")
bullets([
    "<b>Reads all partitions itself</b> (" + C("assign()") + ", no consumer group). A consumer group "
    "remembers where it stopped, so a second run would get nothing. We want the <i>whole</i> topic every time.",
    "<b>Always starts from the beginning</b> (" + C("seek_to_beginning") + ", offset 0).",
    "<b>Knows when to stop.</b> Normal consumers run forever. Ours stops once it has reached the last message of "
    "every partition <i>and</i> nothing new has arrived for 10 s (" + C("--idle-timeout") + ").",
    "<b>Can start early.</b> " + C("--wait-timeout") + " (default 120 s) lets it wait for the producer.",
    "<b>Overwrites the file</b> (" + C("\"w\"") + " mode), so running it twice doesn't double the data.",
    "Prints how many records came from each partition: <b>16 from partition 0, 28 from partition 1</b>.",
])

p("4.3 spark_job2.py: make the two reports", H2)
p("Reads " + C("order_metrics_landed.jsonl") + " and writes <b>restaurant_summary.csv</b> "
  "(6 rows) and <b>city_summary.csv</b> (4 rows).")
table([
    ["Step", "What happens", "Why"],
    ["1. Read", "Read the file with a fixed schema (types given up front)",
     "Types are guaranteed and the file is read only once"],
    ["2. Dedup", C("dropDuplicates") + " on all 15 columns",
     "Spec: exact duplicates count once. Removes 0 here because Job 1 already did it, but it protects against a producer being run twice"],
    ["3. Group", "groupBy restaurant_id, then groupBy city",
     "The two analytics the spec asks for"],
    ["4. Compute", "count, averages, delayed count (rows where status = DELAYED), delay_rate_pct = 100 x delayed / count",
     "delay_rate is worked out from the exact counts, and rounded only once at the end"],
    ["5. Round", C("F.round(..., 2)") + " on every calculated number", "Spec rule"],
    ["6. Sort + write", "Sort the rows, collect them (just 10 rows) and write with Python's csv module",
     "Spark's own writer makes a <i>folder</i> of part-files, but the spec wants one file with an exact name"],
], [24 * mm, 76 * mm, 70 * mm])
p(C(".cache()") + " keeps the deduplicated data in memory because it is used by two reports. "
  "Without it Spark would recompute it for each one.")

p("4.4 Final outputs (know these by heart)", H2)
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
summary_box(
    "0, 4 before; 7; 13, 14, 15; 17.",
    "62 published (TA observer sees 3); 44 landed and " + C("wc -l") + " = 44; 6 + 4 rows, verify OK; the slow "
    "producer reaching 62/62 while VM3 is killed.",
    "why Producer 1 has no key; why the consumer reads every partition from offset 0 and stops by itself; "
    "how Job 2 dedupes, groups and rounds; why the producer survives the failure (acks=all, retries, "
    "min.insync.replicas=1).")

# ================================================================ 5 member 2
story.append(PageBreak())
p("5. Member 2 (VM2): Broker 1 + KRaft controller (the boss)", H1)
bullets([
    "Runs Kafka with " + C("process.roles=broker,controller") + ", " + C("node.id=1") + ".",
    "<b>KRaft</b> = Kafka manages itself, with no separate ZooKeeper. The controller keeps the cluster's \"register\" "
    "(which brokers are alive, which topics exist, who leads each partition).",
    "Port <b>9092</b> = normal Kafka traffic, port <b>9093</b> = controller traffic (only VM2 has it).",
    "Generates the <b>cluster ID</b> once; VM3 must use the same ID to join.",
    C("min.insync.replicas=1") + ": writes still succeed with only one copy alive (needed while VM3 is off).",
    C("auto.create.topics.enable=false") + ": topics are only created on purpose, so a typo can't create a wrong topic.",
    "In the demo, Member 2 shows the cluster state: both brokers, the topic config, and the ISR before, during "
    "and after the failure (section 8 explains how to read it).",
])
summary_box(
    "0, 1, 3 before; 5; 6; 11; 16, 19, 21, 22. You run the TA's cluster commands and both observers.",
    "both broker ids; " + C("LeaderId: 1") + " (VM2 is the controller); the two topics; the observers printing 3 "
    "records each; Isr 1,2 -> Leader 1 / Isr 1 -> Isr 1,2 -> leaders restored by the election.",
    "KRaft and what the controller does; node.id, listeners vs advertised.listeners, ports 9092/9093; "
    "cluster ID; min.insync.replicas=1; Leader vs Replicas vs Isr; preferred leader election; "
    "why VM2 can't be stopped.")

# ================================================================ 6 member 3
p("6. Member 3 (VM3): Broker 2 (the backup)", H1)
bullets([
    "Runs Kafka with " + C("process.roles=broker") + " only, " + C("node.id=2") + ".",
    "Points at VM2:9093 to join and is formatted with <b>VM2's cluster ID</b> (it must not create its own cluster).",
    "Holds the second copy of every partition. In the failure test, <b>this is the machine that gets stopped</b>.",
    "When it stops, VM2's controller notices the missing heartbeats, removes it from the ISR and makes broker 1 "
    "the leader everywhere. When it restarts, it copies what it missed and rejoins the ISR.",
])
summary_box(
    "0, 2 before; 18, 20. Your broker is the one that fails.",
    "the broker being killed with " + C("pkill -9") + " while the slow producer runs, then restarted in the "
    "foreground. Then point to Member 2's describe output, where Isr shrinks to 1 and grows back to 1,2.",
    "what happens step by step when VM3 stops (heartbeats stop, it's fenced, leadership moves to broker 1); "
    "how it catches up and rejoins the ISR; why VM3 uses VM2's cluster ID; what RF 2 protects against.")

# ================================================================ 7 member 4
story.append(PageBreak())
p("7. Member 4 (VM4): Consumer 1, Spark Job 1, Producer 2 (the cleaning step)", H1)
bullets([
    "<b>consumer1.py</b>: same code as consumer2, but reads topic <b>orders</b> -> " + C("orders_landed.jsonl") + " (62 lines).",
    "<b>spark_job1.py</b>: the heart of the project. It <b>throws away bad records</b>, <b>removes duplicates</b>, and "
    "<b>adds 7 new columns</b>. Output: " + C("order_metrics.jsonl") + " (44 lines).",
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
summary_box(
    "0, 4 before; 8, 9; 10, 12.",
    "62 landed and " + C("wc -l") + " = 62; the drop report (14 dropped, 48 valid, 4 duplicates, 44 written); "
    "44 published, split 16 / 28 (TA observer sees 3).",
    "each cleaning rule and the 62 -> 48 -> 44 funnel; the 7 new columns and the midnight case (T040023 = 42 min); "
    "why Producer 2 is keyed by order_id.")

# ================================================================ 8 failure test explained
story.append(PageBreak())
p("8. The failure test explained (whole team)", H1)
story.append(Preformatted(
    "Before (both up):    orders P0  Leader: 2  Replicas: 2,1  Isr: 2,1\n"
    "                     orders P1  Leader: 1  Replicas: 1,2  Isr: 1,2\n"
    "After stopping VM3:  orders P0  Leader: 1  Replicas: 2,1  Isr: 1     <- leader moved to 1\n"
    "                     orders P1  Leader: 1  Replicas: 1,2  Isr: 1\n"
    "Restart VM3 -> Isr back to 2,1 / 1,2.", CODE))
story.append(Spacer(1, 4))
p("<b>Leader</b> = the broker currently serving that partition. <b>Replicas</b> = where copies are <i>supposed</i> "
  "to live (doesn't change). <b>Isr</b> = copies that are currently up to date (shrinks to just 1 while VM3 is off).")
p("Producing still works with VM3 down because the producer uses " + C("acks=all") + " (wait for every <i>in-sync</i> "
  "copy, now just broker 1) and the brokers allow " + C("min.insync.replicas=1") + ". While the leader moves "
  "(about 10 s after the kill) sends to that partition fail briefly; the producer retries every second for up to "
  "30 tries, so no record is lost.")
p("<b>Preferred leader election</b> (step 22): each partition's <i>preferred</i> leader is the first broker in its "
  + C("Replicas") + " list. After VM3 comes back, broker 1 is still leading everything, so the load is uneven. "
  + C("kafka-leader-election.sh --election-type preferred") + " moves leadership back to the preferred brokers "
  "straight away (Kafka would also do it by itself after a few minutes).")
p("<b>kill -9 vs a normal stop:</b> " + C("pkill -9") + " kills the broker instantly, like a crash or power cut, so "
  "it can't hand over its partitions politely. The controller only notices when the broker's heartbeats stop.")

# ================================================================ 9 glossary
p("9. Key words in one line each", H1)
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

# ================================================================ 10 viva
p("10. Top viva questions, short answers", H1)
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

# ================================================================ 11 cheat sheet
p("11. Numbers to remember", H1)
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
