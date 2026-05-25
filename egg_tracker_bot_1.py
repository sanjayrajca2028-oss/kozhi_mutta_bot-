"""
🥚 Egg Tracker Telegram Bot — Final Version
=============================================
Group chat bot. Anyone can log for anyone by name.
All debts tracked in EGGS. Dates & times on everything.

SETUP:
1. pip install python-telegram-bot==20.7
2. Message @BotFather → /newbot → copy token
3. Replace YOUR_BOT_TOKEN_HERE below with your token
4. python egg_tracker_bot.py
5. Add bot to your group chat — done!

ALL COMMANDS:
  /addmember Arjun              - Add a member by name (no Telegram needed)
  /members                      - List all members + registration date
  /bought Arjun 30 180          - Arjun bought 30 eggs for ₹180
  /ate Arjun 6                  - Arjun ate 6 eggs
  /lent Arjun Karthik 5         - Arjun covered 5 eggs for Karthik
  /giveback Ravi Arjun 4        - Ravi physically returned 4 eggs to Arjun
  /stock                        - Current egg stock
  /summary                      - Full group picture
  /mydebt Arjun                 - Arjun's personal debt view (owes / owed)
  /iowe Arjun                   - What Arjun owes others
  /oweme Arjun                  - What others owe Arjun
  /balances                     - Full group balance sheet
  /eggboard                     - Who ate the most 🏆
  /history                      - Last 10 transactions with date & time
  /undo                         - Undo last transaction
  /redo                         - Redo last undone transaction
  /setstock 14                  - Manually set stock (for existing eggs)
  /help                         - All commands
  /reset                        - Wipe all data
"""

import os, json, logging
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ── CONFIG ──────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8997498192:AAES4jRvnYTqS-AIEKO7eOV-HWmTLjQP0fc")
DATA_FILE  = "egg_data.json"
IST        = timezone(timedelta(hours=5, minutes=30))  # India Standard Time

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ── HELPERS ─────────────────────────────────────────────────────────
def now_str():
    """Current IST time as readable string."""
    return datetime.now(IST).strftime("%d %b %Y, %I:%M %p")

def now_iso():
    return datetime.now(IST).isoformat()

def fmt_dt(iso_str):
    """Format stored ISO timestamp to readable IST string."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return iso_str[:16]

def days_ago(iso_str):
    """How many days ago was this timestamp."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        delta = datetime.now(IST) - dt
        d = delta.days
        if d == 0:   return "today"
        if d == 1:   return "1 day ago"
        return f"{d} days ago"
    except:
        return ""

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "stock": 0,
        "total_spent": 0.0,
        "total_eggs_bought": 0,
        "transactions": [],
        "redo_stack": [],
        # members[name_lower] = {
        #   "name": str,
        #   "registered_at": iso,
        #   "eggs_eaten": int,
        #   "egg_balance": int  (>0 = owed to them, <0 = they owe)
        # }
        "members": {}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def price_per_egg(data):
    if data["total_eggs_bought"] == 0: return 0.0
    return data["total_spent"] / data["total_eggs_bought"]

def find(data, name):
    """Find member by name (case-insensitive). Returns member dict or None."""
    return data["members"].get(name.strip().lower())

def all_members(data):
    return list(data["members"].values())

def log_tx(data, tx):
    tx["at"] = now_iso()
    data["redo_stack"] = []  # New action clears redo history
    data["transactions"].append(tx)

def bal_str(eggs):
    if eggs > 0:   return f"🟢 owed {eggs} eggs"
    if eggs < 0:   return f"🔴 owes {abs(eggs)} eggs"
    return "✅ settled"


# ── /start ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥚 *Egg Tracker Bot* is live!\n\n"
        "Anyone in this group can log for anyone by name.\n\n"
        "First, add everyone:\n"
        "`/addmember Arjun`\n"
        "`/addmember Karthik`\n\n"
        "Then start logging:\n"
        "`/bought Arjun 30 180` — Arjun bought eggs\n"
        "`/ate Arjun 6` — Arjun ate 6 eggs\n\n"
        "Use /help for all commands.",
        parse_mode="Markdown"
    )

# ── /help ───────────────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥚 *All Commands*\n\n"
        "👥 *Members*\n"
        "`/addmember Arjun` — add a person\n"
        "`/members` — list everyone\n\n"
        "📦 *Logging*\n"
        "`/bought Arjun 30 180` — Arjun bought 30 eggs ₹180\n"
        "`/ate Arjun 6` — Arjun ate 6 eggs\n"
        "`/lent Arjun Karthik 5` — Arjun covered 5 eggs for Karthik\n"
        "`/giveback Ravi Arjun 4` — Ravi gave 4 eggs back to Arjun\n"
        "`/setstock 14` — set stock manually\n\n"
        "📊 *Reports*\n"
        "`/stock` — eggs remaining\n"
        "`/mydebt Arjun` — Arjun's full debt view\n"
        "`/iowe Arjun` — what Arjun owes others\n"
        "`/oweme Arjun` — what others owe Arjun\n"
        "`/balances` — everyone's egg balance\n"
        "`/summary` — full group picture\n"
        "`/eggboard` — top egg eaters 🏆\n"
        "`/undo` — undo last action\n"
        "`/redo` — redo last action\n"
        "`/history` — last 10 transactions\n\n"
        "⚙️ *Admin*\n"
        "`/reset` — wipe all data",
        parse_mode="Markdown"
    )

# ── /addmember ──────────────────────────────────────────────────────
async def addmember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/addmember Name`\nExample: `/addmember Arjun`", parse_mode="Markdown")
        return
    name = " ".join(context.args).strip().title()
    if len(name) > 30:
        await update.message.reply_text("❌ Name too long (max 30 chars).")
        return
    data = load_data()
    key  = name.lower()
    if key in data["members"]:
        await update.message.reply_text(f"❌ *{name}* is already a member!", parse_mode="Markdown")
        return
    data["members"][key] = {
        "name": name,
        "registered_at": now_iso(),
        "eggs_eaten": 0,
        "egg_balance": 0
    }
    save_data(data)
    await update.message.reply_text(
        f"✅ *{name}* added!\n"
        f"📅 Registered on {now_str()}\n\n"
        f"Total members: {len(data['members'])}",
        parse_mode="Markdown"
    )

# ── /members ────────────────────────────────────────────────────────
async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["members"]:
        await update.message.reply_text("No members yet! Use `/addmember Name`", parse_mode="Markdown")
        return
    msg = "👥 *Members*\n\n"
    for i, m in enumerate(all_members(data), 1):
        msg += (
            f"{i}. *{m['name']}*\n"
            f"   📅 Joined: {fmt_dt(m['registered_at'])}\n"
            f"   🥚 Ate: {m['eggs_eaten']} eggs | {bal_str(m['egg_balance'])}\n\n"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /bought ─────────────────────────────────────────────────────────
async def bought(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /bought Arjun 30 180
    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ Usage: `/bought Name eggs price`\nExample: `/bought Arjun 30 180`",
            parse_mode="Markdown"
        )
        return
    name_arg, eggs_arg, price_arg = context.args
    data = load_data()
    m    = find(data, name_arg)
    if not m:
        await update.message.reply_text(f"❌ *{name_arg.title()}* is not a member. Use /addmember first.", parse_mode="Markdown")
        return
    try:
        num_eggs = int(eggs_arg)
        price    = float(price_arg)
    except ValueError:
        await update.message.reply_text("❌ Invalid numbers. Example: `/bought Arjun 30 180`", parse_mode="Markdown")
        return
    if num_eggs <= 0 or price <= 0:
        await update.message.reply_text("❌ Numbers must be positive!")
        return

    data["stock"]             += num_eggs
    data["total_spent"]       += price
    data["total_eggs_bought"] += num_eggs
    m["egg_balance"]          += num_eggs

    log_tx(data, {"type": "bought", "user": m["name"], "eggs": num_eggs, "price": price})
    save_data(data)

    avg = price_per_egg(data)
    await update.message.reply_text(
        f"✅ *Purchase logged!*\n\n"
        f"👤 Buyer: *{m['name']}*\n"
        f"🥚 Eggs: {num_eggs}\n"
        f"💰 Paid: ₹{price:.0f} (₹{avg:.1f}/egg)\n"
        f"📅 {now_str()}\n"
        f"📦 Stock now: *{data['stock']} eggs*",
        parse_mode="Markdown"
    )

# ── /ate ────────────────────────────────────────────────────────────
async def ate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /ate Arjun 6
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Usage: `/ate Name eggs`\nExample: `/ate Arjun 6`",
            parse_mode="Markdown"
        )
        return
    name_arg, eggs_arg = context.args
    data = load_data()
    m    = find(data, name_arg)
    if not m:
        await update.message.reply_text(f"❌ *{name_arg.title()}* is not a member. Use /addmember first.", parse_mode="Markdown")
        return
    try:
        num_eggs = int(eggs_arg)
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Example: `/ate Arjun 6`", parse_mode="Markdown")
        return
    if num_eggs <= 0:
        await update.message.reply_text("❌ Must be positive!")
        return
    if data["stock"] < num_eggs:
        await update.message.reply_text(f"❌ Only *{data['stock']} eggs* in stock!", parse_mode="Markdown")
        return

    avg  = price_per_egg(data)
    cost = avg * num_eggs
    data["stock"]        -= num_eggs
    m["eggs_eaten"]      += num_eggs
    m["egg_balance"]     -= num_eggs

    log_tx(data, {"type": "ate", "user": m["name"], "eggs": num_eggs, "cost": round(cost, 2)})
    save_data(data)

    await update.message.reply_text(
        f"🍳 *Logged!*\n\n"
        f"👤 *{m['name']}* ate {num_eggs} eggs\n"
        f"💸 Worth ₹{cost:.0f} (@ ₹{avg:.1f}/egg)\n"
        f"📅 {now_str()}\n"
        f"📦 Stock now: *{data['stock']} eggs*\n"
        f"📊 {m['name']}'s balance: {bal_str(m['egg_balance'])}",
        parse_mode="Markdown"
    )

# ── /lent ───────────────────────────────────────────────────────────
async def lent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /lent Arjun Karthik 5  (Arjun covered 5 eggs for Karthik)
    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ Usage: `/lent Lender Borrower eggs`\nExample: `/lent Arjun Karthik 5`\n_(Arjun covered 5 eggs for Karthik)_",
            parse_mode="Markdown"
        )
        return
    lender_arg, borrower_arg, eggs_arg = context.args
    data = load_data()
    lender   = find(data, lender_arg)
    borrower = find(data, borrower_arg)
    if not lender:
        await update.message.reply_text(f"❌ *{lender_arg.title()}* is not a member.", parse_mode="Markdown")
        return
    if not borrower:
        await update.message.reply_text(f"❌ *{borrower_arg.title()}* is not a member.", parse_mode="Markdown")
        return
    if lender_arg.lower() == borrower_arg.lower():
        await update.message.reply_text("❌ Lender and borrower can't be the same person!")
        return
    try:
        eggs = int(eggs_arg)
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Example: `/lent Arjun Karthik 5`", parse_mode="Markdown")
        return
    if eggs <= 0:
        await update.message.reply_text("❌ Must be positive!")
        return

    lender["egg_balance"]   += eggs
    borrower["egg_balance"] -= eggs

    log_tx(data, {"type": "lent", "lender": lender["name"], "borrower": borrower["name"], "eggs": eggs})
    save_data(data)

    avg   = price_per_egg(data)
    worth = avg * eggs
    await update.message.reply_text(
        f"💸 *Lending logged!*\n\n"
        f"*{lender['name']}* covered *{eggs} eggs* for *{borrower['name']}*\n"
        f"_(worth ₹{worth:.0f} at current price)_\n"
        f"📅 {now_str()}\n\n"
        f"*{borrower['name']}* now owes *{lender['name']}* {eggs} eggs",
        parse_mode="Markdown"
    )

# ── /giveback ───────────────────────────────────────────────────────
async def giveback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /giveback Ravi Arjun 4  (Ravi physically gave 4 eggs back to Arjun)
    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ Usage: `/giveback Giver Receiver eggs`\nExample: `/giveback Ravi Arjun 4`\n_(Ravi physically returned 4 eggs to Arjun)_",
            parse_mode="Markdown"
        )
        return
    giver_arg, receiver_arg, eggs_arg = context.args
    data     = load_data()
    giver    = find(data, giver_arg)
    receiver = find(data, receiver_arg)
    if not giver:
        await update.message.reply_text(f"❌ *{giver_arg.title()}* is not a member.", parse_mode="Markdown")
        return
    if not receiver:
        await update.message.reply_text(f"❌ *{receiver_arg.title()}* is not a member.", parse_mode="Markdown")
        return
    if giver_arg.lower() == receiver_arg.lower():
        await update.message.reply_text("❌ Giver and receiver can't be the same!")
        return
    try:
        eggs = int(eggs_arg)
    except ValueError:
        await update.message.reply_text("❌ Invalid number.", parse_mode="Markdown")
        return
    if eggs <= 0:
        await update.message.reply_text("❌ Must be positive!")
        return

    giver["egg_balance"]    += eggs   # giver returns eggs → their debt reduces
    receiver["egg_balance"] -= eggs   # receiver gets eggs back → their credit reduces

    log_tx(data, {"type": "giveback", "giver": giver["name"], "receiver": receiver["name"], "eggs": eggs})
    save_data(data)

    g_bal = giver["egg_balance"]
    if g_bal == 0:
        status = f"🎉 *{giver['name']}* is now fully settled!"
    elif g_bal < 0:
        status = f"*{giver['name']}* still owes *{abs(g_bal)} eggs*"
    else:
        status = f"*{giver['name']}* is now owed *{g_bal} eggs*"

    await update.message.reply_text(
        f"✅ *Eggs returned!*\n\n"
        f"*{giver['name']}* gave *{eggs} eggs* back to *{receiver['name']}*\n"
        f"📅 {now_str()}\n\n"
        f"{status}",
        parse_mode="Markdown"
    )

# ── /setstock ───────────────────────────────────────────────────────
async def setstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /setstock 14  — for when eggs were bought before bot existed
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: `/setstock 14`", parse_mode="Markdown")
        return
    try:
        n = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid number.")
        return
    if n < 0:
        await update.message.reply_text("❌ Stock can't be negative!")
        return
    data = load_data()
    old_stock = data["stock"]
    data["stock"] = n
    log_tx(data, {"type": "setstock", "eggs": n, "old_eggs": old_stock})
    save_data(data)
    await update.message.reply_text(
        f"📦 Stock manually set to *{n} eggs*\n📅 {now_str()}",
        parse_mode="Markdown"
    )

# ── /stock ──────────────────────────────────────────────────────────
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    avg  = price_per_egg(data)
    val  = data["stock"] * avg
    if data["stock"] == 0:      status = "❌ Out of stock! Someone buy eggs."
    elif data["stock"] <= 6:    status = f"⚠️ Low — only {data['stock']} left!"
    else:                       status = "✅ Good stock."
    await update.message.reply_text(
        f"📦 *Egg Stock*\n\n"
        f"🥚 Available: *{data['stock']} eggs*\n"
        f"💰 Avg ₹{avg:.1f}/egg → worth ₹{val:.0f}\n"
        f"🛒 Total ever bought: {data['total_eggs_bought']} eggs\n"
        f"💸 Total ever spent: ₹{data['total_spent']:.0f}\n\n"
        f"{status}",
        parse_mode="Markdown"
    )

# ── /mydebt ─────────────────────────────────────────────────────────
async def mydebt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /mydebt Arjun
    if not context.args:
        await update.message.reply_text("❌ Usage: `/mydebt Name`\nExample: `/mydebt Arjun`", parse_mode="Markdown")
        return
    name_arg = " ".join(context.args).strip()
    data = load_data()
    m    = find(data, name_arg)
    if not m:
        await update.message.reply_text(f"❌ *{name_arg.title()}* is not a member.", parse_mode="Markdown")
        return

    # Find who specifically owes this person and who they owe
    # based on lent/giveback transactions
    owes_to   = {}  # name → eggs (this person owes others)
    owed_from = {}  # name → eggs (others owe this person)

    for tx in data["transactions"]:
        t = tx["type"]
        if t == "lent":
            if tx["lender"].lower() == m["name"].lower():
                owed_from[tx["borrower"]] = owed_from.get(tx["borrower"], 0) + tx["eggs"]
            elif tx["borrower"].lower() == m["name"].lower():
                owes_to[tx["lender"]] = owes_to.get(tx["lender"], 0) + tx["eggs"]
        elif t == "giveback":
            if tx["giver"].lower() == m["name"].lower():
                owes_to[tx["receiver"]] = owes_to.get(tx["receiver"], 0) - tx["eggs"]
            elif tx["receiver"].lower() == m["name"].lower():
                owed_from[tx["giver"]] = owed_from.get(tx["giver"], 0) - tx["eggs"]

    owes_to   = {k: v for k, v in owes_to.items()   if v > 0}
    owed_from = {k: v for k, v in owed_from.items() if v > 0}

    bal  = m["egg_balance"]
    msg  = (
        f"📊 *Egg Debt — {m['name']}*\n"
        f"📅 As of {now_str()}\n"
        f"──────────────────────\n\n"
    )

    if owes_to:
        msg += "🔴 *You owe:*\n"
        for person, eggs in sorted(owes_to.items(), key=lambda x: -x[1]):
            msg += f"  • *{person}* — {eggs} eggs\n"
        msg += "\n"
    else:
        msg += "🔴 *You owe:* nothing\n\n"

    if owed_from:
        msg += "🟢 *Owed to you:*\n"
        for person, eggs in sorted(owed_from.items(), key=lambda x: -x[1]):
            msg += f"  • *{person}* — {eggs} eggs\n"
        msg += "\n"
    else:
        msg += "🟢 *Owed to you:* nothing\n\n"

    net = sum(owed_from.values()) - sum(owes_to.values())
    if net > 0:   msg += f"💡 *Net:* +{net} eggs in your favour\n"
    elif net < 0: msg += f"💡 *Net:* {net} eggs — you owe more\n"
    else:         msg += f"💡 *Net:* fully settled ✅\n"

    msg += f"\n📊 *Overall balance:* {bal_str(bal)}"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /iowe ───────────────────────────────────────────────────────────
async def iowe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /iowe Arjun
    if not context.args:
        await update.message.reply_text("❌ Usage: `/iowe Name`\nExample: `/iowe Arjun`", parse_mode="Markdown")
        return
    name_arg = " ".join(context.args).strip()
    data = load_data()
    m    = find(data, name_arg)
    if not m:
        await update.message.reply_text(f"❌ *{name_arg.title()}* is not a member.", parse_mode="Markdown")
        return

    owes_to = {}
    for tx in data["transactions"]:
        if tx["type"] == "lent" and tx["borrower"].lower() == m["name"].lower():
            owes_to[tx["lender"]] = owes_to.get(tx["lender"], 0) + tx["eggs"]
        elif tx["type"] == "giveback" and tx["giver"].lower() == m["name"].lower():
            owes_to[tx["receiver"]] = owes_to.get(tx["receiver"], 0) - tx["eggs"]
    owes_to = {k: v for k, v in owes_to.items() if v > 0}

    msg = f"🔴 *Eggs {m['name']} owes*\n📅 {now_str()}\n──────────────────────\n\n"
    if owes_to:
        total = 0
        for person, eggs in sorted(owes_to.items(), key=lambda x: -x[1]):
            msg  += f"  • *{person}* — {eggs} eggs\n"
            total += eggs
        msg += f"\nTotal: *{total} eggs* to return"
    else:
        msg += "✅ Nothing to return — all clear!"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /oweme ──────────────────────────────────────────────────────────
async def oweme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /oweme Arjun
    if not context.args:
        await update.message.reply_text("❌ Usage: `/oweme Name`\nExample: `/oweme Arjun`", parse_mode="Markdown")
        return
    name_arg = " ".join(context.args).strip()
    data = load_data()
    m    = find(data, name_arg)
    if not m:
        await update.message.reply_text(f"❌ *{name_arg.title()}* is not a member.", parse_mode="Markdown")
        return

    owed_from = {}
    for tx in data["transactions"]:
        if tx["type"] == "lent" and tx["lender"].lower() == m["name"].lower():
            owed_from[tx["borrower"]] = owed_from.get(tx["borrower"], 0) + tx["eggs"]
        elif tx["type"] == "giveback" and tx["receiver"].lower() == m["name"].lower():
            owed_from[tx["giver"]] = owed_from.get(tx["giver"], 0) - tx["eggs"]
    owed_from = {k: v for k, v in owed_from.items() if v > 0}

    msg = f"🟢 *Eggs owed to {m['name']}*\n📅 {now_str()}\n──────────────────────\n\n"
    if owed_from:
        total = 0
        for person, eggs in sorted(owed_from.items(), key=lambda x: -x[1]):
            msg  += f"  • *{person}* — {eggs} eggs\n"
            total += eggs
        msg += f"\nTotal: *{total} eggs* coming to you"
    else:
        msg += "✅ Nobody owes you anything right now."
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /balances ───────────────────────────────────────────────────────
async def balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["members"]:
        await update.message.reply_text("No members yet!")
        return
    avg       = price_per_egg(data)
    creditors = []
    debtors   = []
    msg       = f"📊 *Egg Balance Sheet*\n📅 {now_str()}\n──────────────────────\n\n"

    for m in all_members(data):
        b = m["egg_balance"]
        if b > 0:   creditors.append([m["name"], b])
        elif b < 0: debtors.append([m["name"], abs(b)])
        else:       msg += f"✅ *{m['name']}* — settled\n"

    if creditors:
        msg += "\n🟢 *Owed eggs:*\n"
        for name, eggs in sorted(creditors, key=lambda x: -x[1]):
            msg += f"  • *{name}* is owed {eggs} eggs\n"

    if debtors:
        msg += "\n🔴 *Owes eggs:*\n"
        for name, eggs in sorted(debtors, key=lambda x: -x[1]):
            msg += f"  • *{name}* owes {eggs} eggs\n"

    if creditors and debtors:
        msg += "\n💡 *Settle up:*\n"
        c = [[n, e] for n, e in sorted(creditors, key=lambda x: -x[1])]
        d = [[n, e] for n, e in sorted(debtors,   key=lambda x: -x[1])]
        ci = di = 0
        while ci < len(c) and di < len(d):
            pay = min(c[ci][1], d[di][1])
            msg += f"  • *{d[di][0]}* gives {pay} eggs → *{c[ci][0]}*\n"
            c[ci][1] -= pay; d[di][1] -= pay
            if c[ci][1] == 0: ci += 1
            if d[di][1] == 0: di += 1

    if not creditors and not debtors:
        msg += "\n🎉 Everyone is settled up!"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /summary ────────────────────────────────────────────────────────
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["members"]:
        await update.message.reply_text("No members yet!")
        return
    avg  = price_per_egg(data)
    txns = data["transactions"]
    msg  = f"📋 *Group Egg Summary*\n📅 {now_str()}\n━━━━━━━━━━━━━━━━━━━━\n\n"

    bought_list = [t for t in txns if t["type"] == "bought"]
    if bought_list:
        msg += "🛒 *Who Bought:*\n"
        for t in bought_list:
            msg += f"  • *{t['user']}* — {t['eggs']} eggs for ₹{t['price']:.0f} ({fmt_dt(t['at'])})\n"
        msg += "\n"

    lent_list = [t for t in txns if t["type"] == "lent"]
    if lent_list:
        msg += "💸 *Who Lent to Whom:*\n"
        for t in lent_list:
            msg += f"  • *{t['lender']}* → *{t['borrower']}* ({t['eggs']} eggs)\n"
        msg += "\n"

    msg += "🍳 *Who Ate How Many:*\n"
    for m in sorted(all_members(data), key=lambda x: x["eggs_eaten"], reverse=True):
        msg += f"  • *{m['name']}* — {m['eggs_eaten']} eggs\n"
    msg += "\n"

    msg += "📊 *Outstanding (eggs):*\n"
    creditors, debtors = [], []
    for m in all_members(data):
        b = m["egg_balance"]
        if b > 0:   creditors.append((m["name"], b))
        elif b < 0: debtors.append((m["name"], abs(b)))
        else:       msg += f"  ✅ *{m['name']}* — settled\n"
    for name, eggs in sorted(creditors, key=lambda x: -x[1]):
        msg += f"  🟢 *{name}* is owed {eggs} eggs\n"
    for name, eggs in sorted(debtors, key=lambda x: -x[1]):
        msg += f"  🔴 *{name}* owes {eggs} eggs\n"

    msg += f"\n📦 *Stock:* {data['stock']} eggs"
    if data["stock"] == 0:   msg += " ❌"
    elif data["stock"] <= 6: msg += " ⚠️ Low!"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /eggboard ───────────────────────────────────────────────────────
async def eggboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data   = load_data()
    ranked = sorted(all_members(data), key=lambda m: m["eggs_eaten"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    msg    = "🏆 *Egg Leaderboard*\n\n"
    for i, m in enumerate(ranked):
        medal = medals[i] if i < 3 else f"{i+1}."
        msg  += f"{medal} *{m['name']}* — {m['eggs_eaten']} eggs\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /history ────────────────────────────────────────────────────────
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    txns = data["transactions"]
    if not txns:
        await update.message.reply_text("No transactions yet!")
        return
    msg = "📜 *Recent Transactions* (last 10)\n\n"
    for tx in reversed(txns[-10:]):
        ts = fmt_dt(tx.get("at", ""))
        t  = tx["type"]
        if t == "bought":
            msg += f"🛒 *{ts}*\n   {tx['user']} bought {tx['eggs']} eggs for ₹{tx['price']:.0f}\n\n"
        elif t == "ate":
            msg += f"🍳 *{ts}*\n   {tx['user']} ate {tx['eggs']} eggs\n\n"
        elif t == "lent":
            msg += f"💸 *{ts}*\n   {tx['lender']} covered {tx['eggs']} eggs for {tx['borrower']}\n\n"
        elif t == "giveback":
            msg += f"🔄 *{ts}*\n   {tx['giver']} returned {tx['eggs']} eggs to {tx['receiver']}\n\n"
        elif t == "setstock":
            msg += f"📦 *{ts}*\n   Stock set to {tx['eggs']} eggs\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /undo ───────────────────────────────────────────────────────────
async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["transactions"]:
        await update.message.reply_text("❌ Nothing to undo.")
        return

    tx = data["transactions"].pop()
    t = tx["type"]

    # Reverse the effects
    if t == "bought":
        m = find(data, tx["user"])
        data["stock"] -= tx["eggs"]
        data["total_spent"] -= tx["price"]
        data["total_eggs_bought"] -= tx["eggs"]
        if m: m["egg_balance"] -= tx["eggs"]
    elif t == "ate":
        m = find(data, tx["user"])
        data["stock"] += tx["eggs"]
        if m:
            m["eggs_eaten"] -= tx["eggs"]
            m["egg_balance"] += tx["eggs"]
    elif t == "lent":
        lender = find(data, tx["lender"])
        borrower = find(data, tx["borrower"])
        if lender: lender["egg_balance"] -= tx["eggs"]
        if borrower: borrower["egg_balance"] += tx["eggs"]
    elif t == "giveback":
        giver = find(data, tx["giver"])
        receiver = find(data, tx["receiver"])
        if giver: giver["egg_balance"] -= tx["eggs"]
        if receiver: receiver["egg_balance"] += tx["eggs"]
    elif t == "setstock":
        data["stock"] = tx.get("old_eggs", data["stock"])

    data["redo_stack"].append(tx)
    save_data(data)
    await update.message.reply_text(f"↩️ Undone: *{t.upper()}*\nUse /redo to reverse this.", parse_mode="Markdown")

# ── /redo ───────────────────────────────────────────────────────────
async def redo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data.get("redo_stack"):
        await update.message.reply_text("❌ Nothing to redo.")
        return

    tx = data["redo_stack"].pop()
    t = tx["type"]

    # Re-apply the effects
    if t == "bought":
        m = find(data, tx["user"])
        data["stock"] += tx["eggs"]
        data["total_spent"] += tx["price"]
        data["total_eggs_bought"] += tx["eggs"]
        if m: m["egg_balance"] += tx["eggs"]
    elif t == "ate":
        m = find(data, tx["user"])
        data["stock"] -= tx["eggs"]
        if m:
            m["eggs_eaten"] += tx["eggs"]
            m["egg_balance"] -= tx["eggs"]
    elif t == "lent":
        lender = find(data, tx["lender"])
        borrower = find(data, tx["borrower"])
        if lender: lender["egg_balance"] += tx["eggs"]
        if borrower: borrower["egg_balance"] -= tx["eggs"]
    elif t == "giveback":
        giver = find(data, tx["giver"])
        receiver = find(data, tx["receiver"])
        if giver: giver["egg_balance"] += tx["eggs"]
        if receiver: receiver["egg_balance"] -= tx["eggs"]
    elif t == "setstock":
        tx["old_eggs"] = data["stock"]
        data["stock"] = tx["eggs"]

    data["transactions"].append(tx)
    save_data(data)
    await update.message.reply_text(f"↪️ Redone: *{t.upper()}*", parse_mode="Markdown")

# ── /reset ──────────────────────────────────────────────────────────
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_data({
        "stock": 0,
        "total_spent": 0.0,
        "total_eggs_bought": 0,
        "transactions": [],
        "redo_stack": [],
        "members": {}
    })
    await update.message.reply_text(
        f"🔄 All data wiped.\n📅 {now_str()}\nStart fresh — use /addmember to add everyone again!",
        parse_mode="Markdown"
    )

# ── MAIN ────────────────────────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Set your token! Edit BOT_TOKEN or run:")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        return
    print("🥚 Egg Tracker Bot — Final Version starting...")
    app = Application.builder().token(BOT_TOKEN).build()
    for cmd, fn in [
        ("start",     start),
        ("help",      help_cmd),
        ("addmember", addmember),
        ("members",   members),
        ("bought",    bought),
        ("ate",       ate),
        ("lent",      lent),
        ("giveback",  giveback),
        ("setstock",  setstock),
        ("stock",     stock),
        ("mydebt",    mydebt),
        ("iowe",      iowe),
        ("oweme",     oweme),
        ("balances",  balances),
        ("summary",   summary),
        ("eggboard",  eggboard),
        ("history",   history),
        ("undo",      undo),
        ("redo",      redo),
        ("reset",     reset),
    ]:
        app.add_handler(CommandHandler(cmd, fn))
    print("✅ Bot running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
