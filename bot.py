import re, os, json, random, threading, time, requests
from uuid import uuid4
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ChatType

# ====== FLASK FOR RENDER ======
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return jsonify({"status": "ok", "bot": "running"}), 200

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ====== CONFIG ======
BOT_TOKEN = "8885172416:AAFRtSo5uGlTSZBBQgU62Xal8XPgu571tjg"
OWNER_ID = 8586849798
CHANNEL = "@KALYUGESCROWSERVICE"
ADMINS = [OWNER_ID]
EXTRA_GROUPS = []
USERS = {}
BANNED = []
DEALS = {}
DICE_PREDS = []
COIN_PREDS = []
PRED_INDEX = 0

# ====== WEBHOOK CLEAR ON START ======
def clear_webhook():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        r = requests.get(url)
        print(f"🌐 Webhook clear response: {r.json()}")
    except Exception as e:
        print(f"⚠️ Webhook clear error: {e}")

clear_webhook()

# ====== DATA LOAD ======
def load_data():
    global ADMINS, EXTRA_GROUPS, USERS, BANNED, DEALS, DICE_PREDS, COIN_PREDS, PRED_INDEX
    try:
        for fname, gvar in [
            ("admins.json", "ADMINS"), ("extra_groups.json", "EXTRA_GROUPS"),
            ("users.json", "USERS"), ("banned.json", "BANNED"),
            ("deals.json", "DEALS"), ("dice_preds.json", "DICE_PREDS"),
            ("coin_preds.json", "COIN_PREDS"), ("pred_index.json", "PRED_INDEX")
        ]:
            if os.path.exists(fname):
                with open(fname) as f:
                    data = json.load(f)
                    if fname == "pred_index.json":
                        PRED_INDEX = data
                    else:
                        globals()[gvar] = data
    except Exception as e:
        print(f"⚠️ Load error (normal if first run): {e}")

load_data()

def save_all():
    try:
        with open("admins.json","w") as f: json.dump(ADMINS, f, indent=2)
        with open("extra_groups.json","w") as f: json.dump(EXTRA_GROUPS, f, indent=2)
        with open("users.json","w") as f: json.dump(USERS, f, indent=2)
        with open("banned.json","w") as f: json.dump(BANNED, f, indent=2)
        with open("deals.json","w") as f: json.dump(DEALS, f, indent=2)
        with open("dice_preds.json","w") as f: json.dump(DICE_PREDS, f, indent=2)
        with open("coin_preds.json","w") as f: json.dump(COIN_PREDS, f, indent=2)
        with open("pred_index.json","w") as f: json.dump(PRED_INDEX, f)
    except Exception as e:
        print(f"⚠️ Save error: {e}")

# ====== STYLISH TEXT ======
BOLD = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
NORM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
FM = {n: b for n, b in zip(NORM, BOLD)}

def F(t):
    return ''.join(FM.get(c, c) for c in t)

# ====== PREMIUM EMOJIS ======
EMOJIS = {
    "verified": ("6246537187614005254", "✅"),
    "fire": ("4956222745814762495", "🔥"),
    "heart": ("5783157259152397008", "❤️"),
    "heart_blue": ("5780496071645991525", "💙"),
    "heart_green": ("5888789252493283486", "💚"),
    "heart_purple": ("5840265018655703965", "💜"),
    "crown": ("5794422335599546668", "👑"),
    "star": ("6244496562752331516", "⭐"),
    "star_glow": ("6010156854955480259", "🌟"),
    "diamond": ("6086778246882399112", "💎"),
    "money": ("6089104607328342288", "💰"),
    "bolt": ("5791970059597386804", "⚡"),
    "like": ("6089313931149448495", "👍"),
    "clap": ("6093744967304352336", "👏"),
    "smile": ("6093864814071780526", "😀"),
    "laugh": ("5782741660936966676", "😂"),
    "cool": ("6032853480782172520", "😎"),
    "devil": ("6035242444671421879", "👿"),
    "sigma": ("6235620067942341623", "🥃"),
    "don": ("6235717714023814969", "🍂"),
    "skills": ("6235593671073339928", "💀"),
    "heart_fire": ("6147617184479711380", "❤️‍🔥"),
    "eye": ("6035338338406242050", "👁️"),
    "sparkle": ("6010338729640596556", "✨"),
    "flex": ("6147464060305676048", "😎"),
    "zap": ("6087079590377820415", "⚡"),
}

def E(name):
    if name in EMOJIS:
        eid, fb = EMOJIS[name]
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return ""

def R():
    return E(random.choice(list(EMOJIS.keys())))

def BORD(text):
    return '\n'.join(f"{R()} {l} {R()}" if l.strip() else l for l in text.split('\n'))

# ====== HELPERS ======
def REG(uid, u, n):
    s = str(uid)
    if s not in USERS:
        USERS[s] = {"u": u, "n": n, "t": str(datetime.now())}
        save_all()

def OWN(uid): return uid == OWNER_ID
def ADM(uid): return uid in ADMINS or uid == OWNER_ID
def BAN(uid): return str(uid) in BANNED

def JOIN_BTN():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ {F('JOIN')} {CHANNEL} ✅", url=f"https://t.me/{CHANNEL.replace('@','')}")
    ]])

async def CHECK_JOIN(uid, ctx):
    try:
        m = await ctx.bot.get_chat_member(CHANNEL, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ====== FORM PARSE ======
def PARSE(t):
    d = {}
    if not re.search(r'deal|escrow|amount|buyer|seller', t, re.I): return None
    for k, p in [
        ("amount", r'(?:amount|𝐀𝐌𝐎𝐔𝐍𝐓)\s*[:：]?\s*([^\n]+)'),
        ("buyer", r'(?:buyer[s]?|𝐁𝐔𝐘𝐄𝐑)\s*[:：]?\s*([^\n]+)'),
        ("seller", r'(?:seller|𝐒𝐄𝐋𝐋𝐄𝐑)\s*[:：]?\s*([^\n]+)'),
        ("detail", r'(?:detail|𝐃𝐄𝐓𝐀𝐈𝐋)\s*[:：]?\s*([^\n]+)'),
        ("condition", r'(?:condition|𝐂𝐎𝐍𝐃𝐈𝐓𝐈𝐎𝐍)\s*[:：]?\s*([^\n]+)'),
        ("till", r'(?:till|𝐓𝐈𝐋𝐋)\s*[:：]?\s*([^\n]+)'),
        ("upi", r'(?:upi|𝐔𝐏𝐈)\s*[:：]?\s*([^\n]+)'),
        ("rg", r'(?:rg|𝐑𝐆)\s*[:：]?\s*([^\n]+)')
    ]:
        m = re.search(p, t, re.I | re.M)
        if m: d[k] = m.group(1).strip()
    if re.search(r'non.*refund', t, re.I): d["fee"] = True
    return d if d else None

# ====== DEAL CARD ======
def CARD(data, did):
    now = datetime.now().strftime("%I:%M %p | %d %b %Y")
    lines = [
        f"👑 {F('KALYUG ESCROW DEAL FORM')} 👑", "",
        F('━━━━━━━━━━━━━━━━━━━━'),
        f"{E('verified')} {F('Deal ID')}: <code>{did}</code>",
        f"{E('heart_green')} {F('Status')}: {F(data.get('status','ACTIVE').upper())}",
        F('━━━━━━━━━━━━━━━━━━━━'), "",
        f"{E('money')} {F('Amount')}: <b>{data.get('amount','N/A')}</b>",
        f"👤 {F('Buyer')}: {data.get('buyer','N/A')}",
        f"👤 {F('Seller')}: {data.get('seller','N/A')}",
        f"📋 {F('Detail')}: {data.get('detail','N/A')}",
        f"✅ {F('Condition')}: {data.get('condition','N/A')}",
        f"⏳ {F('Escrow Till')}: {data.get('till','N/A')}",
    ]
    if data.get('upi'): lines.append(f"💳 {F('RLS UPI')}: ||{data['upi']}||")
    if data.get('fee'): lines.append(f"⚠️ {F('ESCROW FEE NON-REFUNDABLE')}")
    if data.get('rg'): lines.append(f"📞 {F('RG')}: {data['rg']}")
    lines += ["", F('━━━━━━━━━━━━━━━━━━━━'), f"🕐 {now}", f"{E('heart_fire')} {F('Join')}: {CHANNEL} {E('heart_fire')}"]
    return BORD('\n'.join(lines))

def NEW_DEAL(data):
    did = str(uuid4())[:8].upper()
    data["id"] = did
    data["status"] = "active"
    data["created"] = str(datetime.now())
    DEALS[did] = data
    save_all()
    return did

def GET_D(did):
    return DEALS.get(did.upper())

def COMPLETE_D(did):
    did = did.upper()
    if did in DEALS:
        DEALS[did]["status"] = "completed"
        DEALS[did]["completed_at"] = str(datetime.now())
        save_all()
        return True
    return False

# ====== PREDICTIONS ======
def GEN_PREDS():
    global DICE_PREDS, COIN_PREDS, PRED_INDEX
    DICE_PREDS = [random.randint(1,6) for _ in range(10)]
    COIN_PREDS = [random.choice(["HEAD","TAIL"]) for _ in range(10)]
    PRED_INDEX = 0
    save_all()

GEN_PREDS()

# ====== COMMANDS ======
async def start(upd, ctx):
    u = upd.effective_user
    if BAN(u.id): return await upd.message.reply_text(f"❌ {F('Banned')}")
    if not await CHECK_JOIN(u.id, ctx):
        return await upd.message.reply_text(f"⚠️ {F('Please join')} {CHANNEL}", reply_markup=JOIN_BTN())
    REG(u.id, u.username or "-", u.first_name)
    txt = BORD(f"""👑 {F('KALYUG ESCROW BOT')} 👑
{F('━━━━━━━━━━━━━━━━━━━━')}
👋 {F('Hey')} <b>{u.first_name}</b>!
{E('star_glow')} {F('Premium Escrow + Dice + Coin Bot')}
{F('━━━━━━━━━━━━━━━━━━━━')}
🎲 /dice {F('- Roll dice')}
🪙 /flipcoin {F('- Flip coin')}
📋 /deal ID {F('- View deal')}
👑 /owner {F('- Owner panel')}
{F('━━━━━━━━━━━━━━━━━━━━')}
{E('heart_fire')} {CHANNEL} {E('heart_fire')}""")
    await upd.message.reply_text(txt, parse_mode="HTML", reply_markup=JOIN_BTN())

async def dice(upd, ctx):
    uid = upd.effective_user.id
    if BAN(uid): return await upd.message.reply_text(f"❌ {F('Banned')}")
    if not await CHECK_JOIN(uid, ctx):
        return await upd.message.reply_text(f"⚠️ {F('Please join')} {CHANNEL}", reply_markup=JOIN_BTN())
    
    msg = await ctx.bot.send_dice(chat_id=upd.effective_chat.id, emoji="🎲")
    result = msg.dice.value
    
    global DICE_PREDS, PRED_INDEX
    idx = PRED_INDEX
    if idx < len(DICE_PREDS):
        DICE_PREDS[idx] = result
    PRED_INDEX = (idx + 1) % 10
    save_all()
    
    ds = ["⚀","⚁","⚂","⚃","⚄","⚅"]
    txt = BORD(f"""🎲 {F('DICE ROLLED')} 🎲
{F('━━━━━━━━━━━━━━')}
🎯 {F('Result')}: <b>{F(str(result))}</b> {ds[result-1]}
{F('━━━━━━━━━━━━━━')}
╔══════════╗
║   {ds[result-1]}   ║
║  <b>{F(str(result))}</b>  ║
╚══════════╝
{F('Rolled by')}: {upd.effective_user.first_name}
{E('heart_fire')} {CHANNEL} {E('heart_fire')}""")
    await upd.message.reply_text(txt, parse_mode="HTML", reply_markup=JOIN_BTN())

async def coin(upd, ctx):
    uid = upd.effective_user.id
    if BAN(uid): return await upd.message.reply_text(f"❌ {F('Banned')}")
    if not await CHECK_JOIN(uid, ctx):
        return await upd.message.reply_text(f"⚠️ {F('Please join')} {CHANNEL}", reply_markup=JOIN_BTN())
    
    seq = ["HEAD","HEAD","TAIL","HEAD","TAIL","TAIL","HEAD","TAIL","TAIL","HEAD","HEAD","TAIL","TAIL"]
    global PRED_INDEX, COIN_PREDS
    idx = PRED_INDEX
    result = seq[idx % len(seq)]
    
    if idx < len(COIN_PREDS):
        COIN_PREDS[idx] = result
    PRED_INDEX = (idx + 1) % 10
    save_all()
    
    ce = "🦅" if result == "HEAD" else "🪙"
    txt = BORD(f"""🪙 {F('COIN FLIPPED')} 🪙
{F('━━━━━━━━━━━━━━')}
🪙 {F('Result')}: <b>{F(result)}</b> {ce}
{F('━━━━━━━━━━━━━━')}
╔══════════════╗
║   {ce}       ║
║  <b>{F(result)}</b>  ║
╚══════════════╝
{F('Flipped by')}: {upd.effective_user.first_name}
{E('heart_fire')} {CHANNEL} {E('heart_fire')}""")
    await upd.message.reply_text(txt, parse_mode="HTML", reply_markup=JOIN_BTN())

async def showmydice(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    global DICE_PREDS, PRED_INDEX
    idx = PRED_INDEX
    n3 = DICE_PREDS[idx:idx+3]
    while len(n3) < 3: n3.append(random.randint(1,6))
    txt = BORD(f"""🔮 {F('NEXT 3 DICE')} 🔮
{F('━━━━━━━━━━━━━━')}
1️⃣ {F(str(n3[0]))} 🎲
2️⃣ {F(str(n3[1]))} 🎲
3️⃣ {F(str(n3[2]))} 🎲
{F('━━━━━━━━━━━━━━')}""")
    await upd.message.reply_text(txt, parse_mode="HTML")

async def showmycoin(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    global COIN_PREDS, PRED_INDEX
    idx = PRED_INDEX
    n3 = COIN_PREDS[idx:idx+3]
    while len(n3) < 3: n3.append(random.choice(["HEAD","TAIL"]))
    txt = BORD(f"""🔮 {F('NEXT 3 COIN')} 🔮
{F('━━━━━━━━━━━━━━')}
1️⃣ {F(n3[0])} 🪙
2️⃣ {F(n3[1])} 🪙
3️⃣ {F(n3[2])} 🪙
{F('━━━━━━━━━━━━━━')}""")
    await upd.message.reply_text(txt, parse_mode="HTML")

async def view_deal(upd, ctx):
    if not ctx.args: return await upd.message.reply_text(f"📝 {F('Usage')}: /deal DEAL_ID")
    did = ctx.args[0].upper()
    d = GET_D(did)
    if d: await upd.message.reply_text(CARD(d, did), parse_mode="HTML", reply_markup=JOIN_BTN())
    else: await upd.message.reply_text(f"❌ {F('Deal')} <code>{did}</code> {F('not found')}", parse_mode="HTML")

async def complete(upd, ctx):
    if not ADM(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Admins only')}")
    if not ctx.args: return await upd.message.reply_text(f"📝 {F('Usage')}: /completed DEAL_ID")
    did = ctx.args[0].upper()
    if COMPLETE_D(did):
        txt = BORD(f"""✅ {F('DEAL COMPLETED')} ✅
{F('━━━━━━━━━━━━━━')}
🆔 <code>{did}</code>
✅ {F('Status')}: {F('COMPLETED')}
👤 {upd.effective_user.first_name}
🕐 {datetime.now().strftime('%I:%M %p')}""")
        await upd.message.reply_text(txt, parse_mode="HTML")
        for a in ADMINS:
            try: await ctx.bot.send_message(a, f"✅ Deal <code>{did}</code> completed by {upd.effective_user.first_name}", parse_mode="HTML")
            except: pass
    else:
        await upd.message.reply_text(f"❌ {F('Deal not found')}")

async def confirm(upd, ctx):
    if not ctx.args: return await upd.message.reply_text(f"📝 /confirm DEAL_ID")
    did = ctx.args[0].upper()
    d = GET_D(did)
    if not d: return await upd.message.reply_text(f"❌ Deal {did} not found")
    card = CARD(d, did)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 Copy ID", callback_data=f"cp_{did}"),
         InlineKeyboardButton(f"✅ Complete", callback_data=f"cmp_{did}")],
        [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
    ])
    await upd.message.reply_text(f"✅ Deal <code>{did}</code> confirmed!", parse_mode="HTML")
    await upd.effective_chat.send_message(card, parse_mode="HTML", reply_markup=kb)
    for gid in EXTRA_GROUPS:
        try: await ctx.bot.send_message(int(gid), card, parse_mode="HTML", reply_markup=kb)
        except: pass
    for a in ADMINS:
        try: await ctx.bot.send_message(a, f"✅ New deal <code>{did}</code>", parse_mode="HTML")
        except: pass

async def sendalso(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if len(ctx.args) < 2: return await upd.message.reply_text(f"📝 /sendalso GROUP_ID DEAL_ID")
    gid = ctx.args[0]; did = ctx.args[1].upper()
    if gid not in EXTRA_GROUPS: EXTRA_GROUPS.append(gid); save_all()
    d = GET_D(did)
    if not d: return await upd.message.reply_text(f"❌ Deal not found")
    card = CARD(d, did)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 Copy ID", callback_data=f"cp_{did}"),
         InlineKeyboardButton(f"✅ Complete", callback_data=f"cmp_{did}")],
        [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
    ])
    try:
        await ctx.bot.send_message(int(gid), card, parse_mode="HTML", reply_markup=kb)
        await upd.message.reply_text(f"✅ Sent to <code>{gid}</code>", parse_mode="HTML")
    except Exception as e:
        await upd.message.reply_text(f"❌ Error: {str(e)}")

async def owner(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    txt = BORD(f"""👑 {F('OWNER PANEL')} 👑
{F('━━━━━━━━━━━━━━━━━━━━')}
📊 Users: {len(USERS)} | 🚫 Banned: {len(BANNED)}
📦 Deals: {len(DEALS)} | 👥 Admins: {len(ADMINS)}
📋 Extra Groups: {len(EXTRA_GROUPS)}
{F('━━━━━━━━━━━━━━━━━━━━')}
🔮 /showmydice - Next 3 dice
🔮 /showmycoin - Next 3 coin
👥 /users | 🚫 /ban ID | ✅ /unban ID
➕ /addadmin ID | ➖ /removeadmin ID
📋 /sendalso GID DID
{F('━━━━━━━━━━━━━━━━━━━━')}""")
    await upd.message.reply_text(txt, parse_mode="HTML")

async def addadmin(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ Owner only")
    if not ctx.args: return await upd.message.reply_text("📝 /addadmin ID")
    uid = int(ctx.args[0])
    if uid not in ADMINS: ADMINS.append(uid); save_all(); await upd.message.reply_text(f"✅ <code>{uid}</code> added", parse_mode="HTML")
    else: await upd.message.reply_text("⚠️ Already admin")

async def removeadmin(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ Owner only")
    if not ctx.args: return await upd.message.reply_text("📝 /removeadmin ID")
    uid = int(ctx.args[0])
    if uid in ADMINS: ADMINS.remove(uid); save_all(); await upd.message.reply_text(f"✅ <code>{uid}</code> removed", parse_mode="HTML")
    else: await upd.message.reply_text("⚠️ Not admin")

async def list_users(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ Owner only")
    if not USERS: return await upd.message.reply_text("📭 No users")
    pts = [f"🆔 <code>{u}</code> | @{d.get('u','-')} | {'🚫' if u in BANNED else '✅'}" for u,d in USERS.items()]
    for ch in [pts[i:i+20] for i in range(0,len(pts),20)]:
        await upd.message.reply_text(f"👥 Users ({len(USERS)})\n{F('━━━━━━━━━━━━━━━━━━━━')}\n" + '\n'.join(ch), parse_mode="HTML")

async def ban(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ Owner only")
    if not ctx.args: return await upd.message.reply_text("📝 /ban ID")
    uid = ctx.args[0]
    if uid == str(OWNER_ID): return await upd.message.reply_text("❌ Cannot ban owner")
    if uid not in BANNED: BANNED.append(uid); save_all(); await upd.message.reply_text(f"✅ <code>{uid}</code> banned", parse_mode="HTML")
    else: await upd.message.reply_text("⚠️ Already banned")

async def unban(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ Owner only")
    if not ctx.args: return await upd.message.reply_text("📝 /unban ID")
    uid = ctx.args[0]
    if uid in BANNED: BANNED.remove(uid); save_all(); await upd.message.reply_text(f"✅ <code>{uid}</code> unbanned", parse_mode="HTML")
    else: await upd.message.reply_text("⚠️ Not banned")

async def deals(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ Owner only")
    if not DEALS: return await upd.message.reply_text("📭 No deals")
    pts = [f"🆔 <code>{d}</code> | 💰 {v.get('amount','N/A')} | 👤 {v.get('buyer','N/A')} | 📌 {v.get('status','active')}" for d,v in DEALS.items()]
    for ch in [pts[i:i+15] for i in range(0,len(pts),15)]:
        await upd.message.reply_text(f"📋 Deals ({len(DEALS)})\n{F('━━━━━━━━━━━━━━━━━━━━')}\n" + '\n'.join(ch), parse_mode="HTML")

# ====== FORM HANDLER ======
async def form_handler(upd, ctx):
    msg = upd.message
    if not msg or not msg.text: return
    if not await CHECK_JOIN(msg.from_user.id, ctx):
        return await msg.reply_text(f"⚠️ {F('Please join')} {CHANNEL}", reply_markup=JOIN_BTN())
    data = PARSE(msg.text)
    if not data: return
    did = NEW_DEAL(data)
    confirm_txt = BORD(f"""👑 {F('DEAL FORM RECEIVED')} 👑
{F('━━━━━━━━━━━━━━━━━━━━')}
{E('verified')} {F('Deal ID')}: <code>{did}</code>
{E('star_glow')} {F('Confirm this deal')} {E('star_glow')}
{F('━━━━━━━━━━━━━━━━━━━━')}
{E('money')} {F('Amount')}: <b>{data.get('amount','N/A')}</b>
👤 {F('Buyer')}: {data.get('buyer','N/A')}
👤 {F('Seller')}: {data.get('seller','N/A')}
📋 {F('Detail')}: {data.get('detail','N/A')}
{F('━━━━━━━━━━━━━━━━━━━━')}
{E('heart_fire')} /confirm {did} {F('to confirm')} {E('heart_fire')}""")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Confirm {did}", callback_data=f"cnf_{did}"),
         InlineKeyboardButton(f"❌ Cancel", callback_data=f"cncl_{did}")],
        [InlineKeyboardButton(f"📋 Copy ID", callback_data=f"cp_{did}")],
    ])
    await msg.reply_text(confirm_txt, parse_mode="HTML", reply_markup=kb)

# ====== CALLBACK ======
async def cb(upd, ctx):
    q = upd.callback_query
    await q.answer()
    d = q.data
    if d.startswith("cp_"):
        await q.message.reply_text(f"📋 <b>Deal ID</b>: <code>{d[3:]}</code>", parse_mode="HTML")
    elif d.startswith("vw_") or d.startswith("cnf_"):
        did = d[4:] if d.startswith("cnf_") else d[3:]
        dl = GET_D(did)
        if dl:
            card = CARD(dl, dl["id"])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📋 Copy ID", callback_data=f"cp_{did}"),
                 InlineKeyboardButton(f"✅ Complete", callback_data=f"cmp_{did}")],
                [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
            ])
            if d.startswith("cnf_"):
                await q.message.reply_text(f"✅ Deal <code>{did}</code> confirmed!", parse_mode="HTML")
                await q.message.chat.send_message(card, parse_mode="HTML", reply_markup=kb)
                for gid in EXTRA_GROUPS:
                    try: await ctx.bot.send_message(int(gid), card, parse_mode="HTML", reply_markup=kb)
                    except: pass
                for a in ADMINS:
                    try: await ctx.bot.send_message(a, f"✅ New deal <code>{did}</code>", parse_mode="HTML")
                    except: pass
            else:
                await q.message.reply_text(card, parse_mode="HTML")
        else:
            await q.message.reply_text("❌ Deal not found")
    elif d.startswith("cncl_"):
        await q.message.reply_text(f"❌ Deal <code>{d[5:]}</code> cancelled", parse_mode="HTML")
    elif d.startswith("cmp_"):
        if not ADM(q.from_user.id): return await q.message.reply_text("❌ Admins only")
        if COMPLETE_D(d[4:]):
            await q.message.reply_text(BORD(f"✅ {F('DEAL COMPLETED')} ✅\n🆔 <code>{d[4:]}</code>\n✅ {F('COMPLETED')}"), parse_mode="HTML")

# ====== MAIN ======
def main():
    # Wait for Flask to be ready
    time.sleep(2)
    
    # Start Flask in background
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    # Give Flask a moment
    time.sleep(1)
    
    print(f"🚀 Starting bot with polling... Owner: {OWNER_ID}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("flipcoin", coin))
    app.add_handler(CommandHandler("deal", view_deal))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("completed", complete))
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("showmydice", showmydice))
    app.add_handler(CommandHandler("showmycoin", showmycoin))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("deals", deals))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("sendalso", sendalso))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, form_handler))
    app.add_handler(CallbackQueryHandler(cb))
    
    print(f"✅ BOT IS RUNNING! Send /start to @KALYUGESCROWSERVICE_BOT")
    
    # Use polling (not webhook)
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
