import re, os, json, random, threading, asyncio
from uuid import uuid4
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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
BOT_TOKEN = "8725913927:AAF-Q5RuOobmtLfd4hKarV6s6wYAVklmVNo"
OWNER_ID = 7977493987
CHANNEL = "@KALYUGESCROWSERVICE"

# Admins - owner can add/remove
ADMINS = [OWNER_ID]

# Groups where bot forwards forms
EXTRA_GROUPS = []

# USERS, BANNED, DEALS
USERS = {}
BANNED = []
DEALS = {}

# Dice/Coin predictions (next 3)
DICE_PREDS = []
COIN_PREDS = []
PRED_INDEX = 0

for f, d in [("users.json", USERS), ("banned.json", BANNED), ("deals.json", DEALS), ("admins.json", ADMINS), ("extra_groups.json", EXTRA_GROUPS)]:
    if os.path.exists(f):
        try:
            data = json.load(open(f))
            if isinstance(data, dict): d.update(data)
            elif isinstance(data, list): 
                d.clear()
                d.extend(data)
        except: pass

def SV():
    json.dump(USERS, open("users.json","w"), indent=2)
    json.dump(BANNED, open("banned.json","w"), indent=2)
    json.dump(DEALS, open("deals.json","w"), indent=2)
    json.dump(ADMINS, open("admins.json","w"), indent=2)
    json.dump(EXTRA_GROUPS, open("extra_groups.json","w"), indent=2)

# ====== STYLISH TEXT ======
BOLD = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
NORM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
FM = {n: b for n, b in zip(NORM, BOLD)}

def F(t):
    return ''.join(FM.get(c, c) for c in t)

# ====== PREMIUM EMOJIS ======
EMOJIS = {
    "verified": "6246537187614005254✅", "fire": "4956222745814762495🔥",
    "heart": "5783157259152397008❤️", "heart_blue": "5780496071645991525💙",
    "heart_green": "5888789252493283486💚", "heart_purple": "5840265018655703965💜",
    "crown": "5794422335599546668👑", "star": "6244496562752331516⭐",
    "star_glow": "6010156854955480259🌟", "diamond": "6086778246882399112💎",
    "money": "6089104607328342288💰", "bolt": "5791970059597386804⚡",
    "like": "6089313931149448495👍", "clap": "6093744967304352336👏",
    "smile": "6093864814071780526😀", "laugh": "5782741660936966676😂",
    "cool": "6032853480782172520😎", "devil": "6035242444671421879👿",
    "sigma": "6235620067942341623🥃", "don": "6235717714023814969🍂",
    "skills": "6235593671073339928💀", "heart_fire": "6147617184479711380❤️‍🔥",
    "eye": "6035338338406242050👁️", "sparkle": "6010338729640596556✨",
    "money_bag": "6086730718774300509💰", "dollar": "6089140105233044310💵",
    "flex": "6147464060305676048😎", "zap": "6087079590377820415⚡",
}

def E(name):
    if name in EMOJIS:
        d = EMOJIS[name]
        return f'<tg-emoji emoji-id="{d[:-1]}">{d[-1]}</tg-emoji>'
    return ""

def R():
    return E(random.choice(list(EMOJIS.keys())))

def LINE(line):
    """Har line ke aage piche premium emoji"""
    if line.strip():
        return f"{R()} {line} {R()}"
    return line

def BORD(text):
    return '\n'.join(LINE(l) for l in text.split('\n'))

# ====== HELPERS ======
def REG(uid, u, n):
    s = str(uid)
    if s not in USERS:
        USERS[s] = {"u": u, "n": n, "t": str(datetime.now())}
        SV()

def OWN(uid): return uid == OWNER_ID
def ADM(uid): return uid in ADMINS or uid == OWNER_ID
def BAN(uid): return str(uid) in BANNED

# ====== JOIN BUTTON (GREEN COLOR) ======
def JOIN_BTN():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"✅ {F('JOIN')} {CHANNEL} ✅",
            url=f"https://t.me/{CHANNEL.replace('@','')}"
        )
    ]])

async def CHECK_JOIN(uid, ctx):
    """Check if user joined channel"""
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
        ("amount", r'(?:amount|𝐀𝐌𝐎𝐔𝐍𝐓|amount\s*:)\s*[:：]?\s*([^\n]+)'),
        ("buyer", r'(?:buyer[s]?|𝐁𝐔𝐘𝐄𝐑)\s*[:：]?\s*([^\n]+)'),
        ("seller", r'(?:seller|𝐒𝐄𝐋𝐋𝐄𝐑)\s*[:：]?\s*([^\n]+)'),
        ("detail", r'(?:deal detail|detail|𝐃𝐄𝐓𝐀𝐈𝐋)\s*[:：]?\s*([^\n]+)'),
        ("condition", r'(?:condition|𝐂𝐎𝐍𝐃𝐈𝐓𝐈𝐎𝐍)\s*[:：]?\s*([^\n]+)'),
        ("till", r'(?:escrow till|till|𝐓𝐈𝐋𝐋)\s*[:：]?\s*([^\n]+)'),
        ("upi", r'(?:rls upi|upi|𝐔𝐏𝐈)\s*[:：]?\s*([^\n]+)'),
        ("rg", r'(?:rg|𝐑𝐆)\s*[:：]?\s*([^\n]+)')
    ]:
        m = re.search(p, t, re.I | re.M)
        if m: d[k] = m.group(1).strip()
    if re.search(r'non.*refund', t, re.I): d["fee"] = True
    return d if d else None

# ====== DEAL CARD ======
def CARD(data, did):
    now = datetime.now().strftime("%I:%M %p | %d %b %Y")
    
    lines = []
    lines.append(f"👑 {F('KALYUG ESCROW DEAL FORM')} 👑")
    lines.append("")
    lines.append(F('━━━━━━━━━━━━━━━━━━━━'))
    lines.append(f"{E('verified')} {F('Deal ID')}: <code>{did}</code>")
    lines.append(f"{E('heart_green')} {F('Status')}: {F(data.get('status','Active').upper())}")
    lines.append(F('━━━━━━━━━━━━━━━━━━━━'))
    lines.append("")
    lines.append(f"{E('money')} {F('Amount')}: <b>{data.get('amount','N/A')}</b>")
    lines.append(f"👤 {F('Buyer')}: {data.get('buyer','N/A')}")
    lines.append(f"👤 {F('Seller')}: {data.get('seller','N/A')}")
    lines.append(f"📋 {F('Detail')}: {data.get('detail','N/A')}")
    lines.append(f"✅ {F('Condition')}: {data.get('condition','N/A')}")
    lines.append(f"⏳ {F('Escrow Till')}: {data.get('till','N/A')}")
    
    if data.get('upi'):
        lines.append(f"💳 {F('RLS UPI')}: ||{data['upi']}||")
    if data.get('fee'):
        lines.append(f"⚠️ {F('ESCROW FEE NON-REFUNDABLE')}")
    if data.get('rg'):
        lines.append(f"📞 {F('RG')}: {data['rg']}")
    
    lines.append("")
    lines.append(F('━━━━━━━━━━━━━━━━━━━━'))
    lines.append(f"🕐 {now}")
    lines.append(f"{E('heart_fire')} {F('Join')}: {CHANNEL} {E('heart_fire')}")
    
    # Har line ke aage piche premium emoji
    return BORD('\n'.join(lines))

def NEW_DEAL(data):
    did = str(uuid4())[:8].upper()
    data["id"] = did
    data["status"] = "active"
    data["created"] = str(datetime.now())
    DEALS[did] = data
    SV()
    return did

def GET_D(did):
    return DEALS.get(did.upper())

def COMPLETE_D(did):
    did = did.upper()
    if did in DEALS:
        DEALS[did]["status"] = "completed"
        DEALS[did]["completed_at"] = str(datetime.now())
        SV()
        return True
    return False

# ====== GENERATE PREDICTIONS ======
def GEN_PREDS():
    global DICE_PREDS, COIN_PREDS, PRED_INDEX
    DICE_PREDS = [random.randint(1,6) for _ in range(10)]
    COIN_PREDS = [random.choice(["HEAD","TAIL"]) for _ in range(10)]
    PRED_INDEX = 0

GEN_PREDS()  # pehle se generate

# ====== BOT COMMANDS ======
async def start(upd, ctx):
    u = upd.effective_user
    if BAN(u.id): return await upd.message.reply_text(f"❌ {F('Banned')}")
    
    if not await CHECK_JOIN(u.id, ctx):
        return await upd.message.reply_text(
            f"⚠️ {F('Please join')} {CHANNEL} {F('to use this bot')}",
            reply_markup=JOIN_BTN()
        )
    
    REG(u.id, u.username or "-", u.first_name)
    txt = BORD(f"""👑 {F('KALYUG ESCROW BOT')} 👑

{F('━━━━━━━━━━━━━━━━━━━━')}
👋 {F('Hey')} <b>{u.first_name}</b>!
{E('star_glow')} {F('Premium Escrow Deal + Dice + Coin Bot')}

{F('━━━━━━━━━━━━━━━━━━━━')}
🎲 /dice {F('- Roll dice')}
🪙 /flipcoin {F('- Flip coin')}
📋 /deal ID {F('- View deal status')}
👑 /owner {F('- Owner panel')}

{F('━━━━━━━━━━━━━━━━━━━━')}
{E('heart_fire')} {CHANNEL} {E('heart_fire')}""")
    await upd.message.reply_text(txt, parse_mode="HTML", reply_markup=JOIN_BTN())

async def dice(upd, ctx):
    uid = upd.effective_user.id
    if BAN(uid): return await upd.message.reply_text(f"❌ {F('Banned')}")
    if not await CHECK_JOIN(uid, ctx):
        return await upd.message.reply_text(f"⚠️ {F('Please join')} {CHANNEL}", reply_markup=JOIN_BTN())
    
    # Send real dice animation using sendDice
    msg = await ctx.bot.send_dice(chat_id=upd.effective_chat.id, emoji="🎲")
    result = msg.dice.value
    
    # Store prediction
    global PRED_INDEX
    if PRED_INDEX < len(DICE_PREDS):
        DICE_PREDS[PRED_INDEX] = result
    PRED_INDEX = (PRED_INDEX + 1) % 10
    SV()
    
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
    
    # Send coin animation
    msg = await ctx.bot.send_dice(chat_id=upd.effective_chat.id, emoji="🪙")
    val = msg.dice.value
    result = "HEAD" if val <= 3 else "TAIL"
    
    # Sequence maintenance
    seq = ["HEAD","HEAD","TAIL","HEAD","TAIL","TAIL","HEAD","TAIL","TAIL","HEAD","HEAD","TAIL","TAIL"]
    if PRED_INDEX < len(seq):
        result = seq[PRED_INDEX % len(seq)]
    
    global PRED_INDEX
    if PRED_INDEX < len(COIN_PREDS):
        COIN_PREDS[PRED_INDEX] = result
    PRED_INDEX = (PRED_INDEX + 1) % 10
    SV()
    
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
    next_3 = DICE_PREDS[PRED_INDEX:PRED_INDEX+3]
    if len(next_3) < 3:
        next_3 = DICE_PREDS[:3]
    txt = BORD(f"""🔮 {F('NEXT 3 DICE PREDICTIONS')} 🔮
{F('━━━━━━━━━━━━━━')}
1️⃣ {F(str(next_3[0]))} 🎲
2️⃣ {F(str(next_3[1]))} 🎲
3️⃣ {F(str(next_3[2]))} 🎲
{F('━━━━━━━━━━━━━━')}
⚡ {F('These will be the next dice results')} ⚡""")
    await upd.message.reply_text(txt, parse_mode="HTML")

async def showmycoin(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    next_3 = COIN_PREDS[PRED_INDEX:PRED_INDEX+3]
    if len(next_3) < 3:
        next_3 = COIN_PREDS[:3]
    txt = BORD(f"""🔮 {F('NEXT 3 COIN PREDICTIONS')} 🔮
{F('━━━━━━━━━━━━━━')}
1️⃣ {F(next_3[0])} 🪙
2️⃣ {F(next_3[1])} 🪙
3️⃣ {F(next_3[2])} 🪙
{F('━━━━━━━━━━━━━━')}
⚡ {F('These will be the next coin results')} ⚡""")
    await upd.message.reply_text(txt, parse_mode="HTML")

async def view_deal(upd, ctx):
    if not ctx.args: 
        txt = BORD(f"""📋 {F('Usage')}: /deal DEAL_ID
    
{F('Example')}: /deal A1B2C3D4""")
        return await upd.message.reply_text(txt, parse_mode="HTML")
    
    did = ctx.args[0].upper()
    d = GET_D(did)
    if d:
        await upd.message.reply_text(CARD(d, did), parse_mode="HTML", reply_markup=JOIN_BTN())
    else:
        await upd.message.reply_text(f"❌ {F('Deal')} <code>{did}</code> {F('not found')}", parse_mode="HTML")

async def complete(upd, ctx):
    """Group admin se /completed DEAL_ID"""
    if not ADM(upd.effective_user.id):
        return await upd.message.reply_text(f"❌ {F('Admins only')}")
    
    if not ctx.args:
        return await upd.message.reply_text(f"📝 {F('Usage')}: /completed DEAL_ID")
    
    did = ctx.args[0].upper()
    if COMPLETE_D(did):
        d = GET_D(did)
        txt = BORD(f"""✅ {F('DEAL COMPLETED')} ✅
{F('━━━━━━━━━━━━━━')}
🆔 {F('Deal ID')}: <code>{did}</code>
📌 {F('Status')}: {F('COMPLETED')} ✅
👤 {F('Completed by')}: {upd.effective_user.first_name}
🕐 {datetime.now().strftime('%I:%M %p')}
{F('━━━━━━━━━━━━━━')}
{E('crown')} {F('Deal Successfully Completed')} {E('crown')}""")
        await upd.message.reply_text(txt, parse_mode="HTML")
        
        # Update in all places
        await ctx.bot.send_message(
            OWNER_ID,
            f"✅ {F('Deal')} <code>{did}</code> {F('completed by')} {upd.effective_user.first_name}",
            parse_mode="HTML"
        )
    else:
        await upd.message.reply_text(f"❌ {F('Deal')} <code>{did}</code> {F('not found')}", parse_mode="HTML")

# ====== FORM HANDLER ======
async def form_handler(upd, ctx):
    msg = upd.message
    if not msg or not msg.text: return
    
    # Check if user joined
    if not await CHECK_JOIN(msg.from_user.id, ctx):
        return await msg.reply_text(
            f"⚠️ {F('Please join')} {CHANNEL} {F('to post deals')}",
            reply_markup=JOIN_BTN()
        )
    
    data = PARSE(msg.text)
    if not data: return
    
    # Create deal ID
    did = NEW_DEAL(data)
    
    # Confirmation - form dubara deal ID ke saath
    confirm = BORD(f"""👑 {F('DEAL FORM RECEIVED')} 👑

{F('━━━━━━━━━━━━━━━━━━━━')}
{E('verified')} {F('Deal ID')}: <code>{did}</code>
{E('star_glow')} {F('Please confirm this deal')} {E('star_glow')}
{F('━━━━━━━━━━━━━━━━━━━━')}

{E('money')} {F('Amount')}: <b>{data.get('amount','N/A')}</b>
👤 {F('Buyer')}: {data.get('buyer','N/A')}
👤 {F('Seller')}: {data.get('seller','N/A')}
📋 {F('Detail')}: {data.get('detail','N/A')}
✅ {F('Condition')}: {data.get('condition','N/A')}
⏳ {F('Escrow Till')}: {data.get('till','N/A')}

{F('━━━━━━━━━━━━━━━━━━━━')}
{E('heart_fire')} {F('Reply with')} /confirm {did} {F('to confirm')} {E('heart_fire')}""")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ {F('Confirm')} {did}", callback_data=f"cnf_{did}"),
         InlineKeyboardButton(f"❌ {F('Cancel')}", callback_data=f"cncl_{did}")],
        [InlineKeyboardButton(f"📋 {F('Copy ID')}", callback_data=f"cp_{did}")],
        [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
    ])
    
    await msg.reply_text(confirm, parse_mode="HTML", reply_markup=kb)

async def confirm_deal(upd, ctx):
    """/confirm DEAL_ID - user confirms deal"""
    if not ctx.args:
        return await upd.message.reply_text(f"📝 Usage: /confirm DEAL_ID")
    
    did = ctx.args[0].upper()
    d = GET_D(did)
    if not d:
        return await upd.message.reply_text(f"❌ Deal {did} not found")
    
    # Send final deal card to group
    card = CARD(d, did)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 {F('Copy ID')}", callback_data=f"cp_{did}"),
         InlineKeyboardButton(f"✅ {F('Mark Complete')}", callback_data=f"cmp_{did}")],
        [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
    ])
    
    await upd.message.reply_text(
        f"✅ {F('Deal Confirmed')}! {F('Deal ID')}: <code>{did}</code>",
        parse_mode="HTML"
    )
    
    # Send to same group
    await upd.effective_chat.send_message(card, parse_mode="HTML", reply_markup=kb)
    
    # Send to all extra groups
    for gid in EXTRA_GROUPS:
        try:
            await ctx.bot.send_message(int(gid), card, parse_mode="HTML", reply_markup=kb)
        except:
            pass
    
    # Notify owner
    am = f"✅ {F('New Deal Confirmed')} ✅\n🆔 <code>{did}</code>\n👤 {upd.effective_user.first_name}\n💰 {d.get('amount','N/A')}"
    ak = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👁️ {F('View')}", callback_data=f"vw_{did}"),
         InlineKeyboardButton(f"✅ {F('Complete')}", callback_data=f"cmp_{did}")]
    ])
    for a in ADMINS:
        try: await ctx.bot.send_message(a, am, parse_mode="HTML", reply_markup=ak)
        except: pass

# ====== SEND ALSO ======
async def sendalso(upd, ctx):
    """/sendalso GROUP_ID - send form to another group"""
    if not OWN(upd.effective_user.id):
        return await upd.message.reply_text(f"❌ {F('Owner only')}")
    
    if len(ctx.args) < 2:
        return await upd.message.reply_text(f"📝 {F('Usage')}: /sendalso GROUP_ID DEAL_ID")
    
    gid = ctx.args[0]
    did = ctx.args[1].upper()
    
    # Add to extra groups
    if gid not in EXTRA_GROUPS:
        EXTRA_GROUPS.append(gid)
        SV()
    
    d = GET_D(did)
    if not d:
        return await upd.message.reply_text(f"❌ {F('Deal')} {did} {F('not found')}")
    
    card = CARD(d, did)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 {F('Copy ID')}", callback_data=f"cp_{did}"),
         InlineKeyboardButton(f"✅ {F('Complete')}", callback_data=f"cmp_{did}")],
        [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
    ])
    
    try:
        await ctx.bot.send_message(int(gid), card, parse_mode="HTML", reply_markup=kb)
        await upd.message.reply_text(f"✅ {F('Sent to group')} <code>{gid}</code>", parse_mode="HTML")
    except Exception as e:
        await upd.message.reply_text(f"❌ {F('Error')}: {str(e)}")

# ====== OWNER PANEL ======
async def owner(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    
    txt = BORD(f"""👑 {F('OWNER PANEL')} 👑

{F('━━━━━━━━━━━━━━━━━━━━')}
📊 {F('Users')}: {len(USERS)}
🚫 {F('Banned')}: {len(BANNED)}
📦 {F('Deals')}: {len(DEALS)}
👥 {F('Admins')}: {len(ADMINS)}
📋 {F('Extra Groups')}: {len(EXTRA_GROUPS)}

{F('━━━━━━━━━━━━━━━━━━━━')}
🔮 /showmydice {F('- Next 3 dice')}
🔮 /showmycoin {F('- Next 3 coin')}
👥 /users {F('- List users')}
🚫 /ban ID
✅ /unban ID
📦 /deals {F('- List deals')}
📋 /deal ID {F('- View deal')}
➕ /addadmin ID {F('- Add admin')}
➖ /removeadmin ID {F('- Remove admin')}
📋 /sendalso GID DID {F('- Send to group')}

{F('━━━━━━━━━━━━━━━━━━━━')}
👑 @iflexvenom""")
    await upd.message.reply_text(txt, parse_mode="HTML")

async def addadmin(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if not ctx.args: return await upd.message.reply_text(f"📝 /addadmin ID")
    uid = int(ctx.args[0])
    if uid not in ADMINS:
        ADMINS.append(uid)
        SV()
        await upd.message.reply_text(f"✅ <code>{uid}</code> {F('added as admin')}", parse_mode="HTML")
    else:
        await upd.message.reply_text(f"⚠️ {F('Already admin')}")

async def removeadmin(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if not ctx.args: return await upd.message.reply_text(f"📝 /removeadmin ID")
    uid = int(ctx.args[0])
    if uid in ADMINS:
        ADMINS.remove(uid)
        SV()
        await upd.message.reply_text(f"✅ <code>{uid}</code> {F('removed from admins')}", parse_mode="HTML")
    else:
        await upd.message.reply_text(f"⚠️ {F('Not an admin')}")

async def users(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if not USERS: return await upd.message.reply_text(f"📭 {F('No users')}")
    pts = [f"🆔 <code>{u}</code> | @{d.get('u','-')} | {'🚫' if u in BANNED else '✅'}" for u,d in USERS.items()]
    for ch in [pts[i:i+20] for i in range(0, len(pts), 20)]:
        await upd.message.reply_text(f"👥 {F('Users')} ({len(USERS)})\n{F('━━━━━━━━━━━━━━━━━━━━')}\n" + '\n'.join(ch), parse_mode="HTML")

async def ban(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if not ctx.args: return await upd.message.reply_text(f"📝 /ban ID")
    uid = ctx.args[0]
    if uid == str(OWNER_ID): return await upd.message.reply_text(f"❌ Cannot ban owner")
    if uid not in BANNED:
        BANNED.append(uid); SV()
        await upd.message.reply_text(f"✅ <code>{uid}</code> banned", parse_mode="HTML")
    else:
        await upd.message.reply_text(f"⚠️ Already banned")

async def unban(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if not ctx.args: return await upd.message.reply_text(f"📝 /unban ID")
    uid = ctx.args[0]
    if uid in BANNED:
        BANNED.remove(uid); SV()
        await upd.message.reply_text(f"✅ <code>{uid}</code> unbanned", parse_mode="HTML")
    else:
        await upd.message.reply_text(f"⚠️ Not banned")

async def deals(upd, ctx):
    if not OWN(upd.effective_user.id): return await upd.message.reply_text(f"❌ {F('Owner only')}")
    if not DEALS: return await upd.message.reply_text(f"📭 No deals")
    pts = [f"🆔 <code>{d}</code> | 💰 {v.get('amount','N/A')} | 👤 {v.get('buyer','N/A')} | 📌 {v.get('status','active')}" for d,v in DEALS.items()]
    for ch in [pts[i:i+15] for i in range(0, len(pts), 15)]:
        await upd.message.reply_text(f"📋 Deals ({len(DEALS)})\n{F('━━━━━━━━━━━━━━━━━━━━')}\n" + '\n'.join(ch), parse_mode="HTML")

# ====== CALLBACK ======
async def cb(upd, ctx):
    q = upd.callback_query
    await q.answer()
    d = q.data
    
    if d.startswith("cp_"):
        await q.message.reply_text(f"📋 <b>Deal ID</b>: <code>{d[3:]}</code>", parse_mode="HTML")
    
    elif d.startswith("vw_"):
        dl = GET_D(d[3:])
        if dl: await q.message.reply_text(CARD(dl, dl["id"]), parse_mode="HTML")
        else: await q.message.reply_text("❌ Deal not found")
    
    elif d.startswith("cnf_"):
        did = d[4:]
        dl = GET_D(did)
        if dl:
            card = CARD(dl, did)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📋 Copy ID", callback_data=f"cp_{did}"),
                 InlineKeyboardButton(f"✅ Complete", callback_data=f"cmp_{did}")],
                [InlineKeyboardButton(f"📢 {CHANNEL}", url=f"https://t.me/{CHANNEL.replace('@','')}")]
            ])
            await q.message.reply_text(f"✅ Deal <code>{did}</code> confirmed!", parse_mode="HTML")
            await q.message.chat.send_message(card, parse_mode="HTML", reply_markup=kb)
            
            for gid in EXTRA_GROUPS:
                try: await ctx.bot.send_message(int(gid), card, parse_mode="HTML", reply_markup=kb)
                except: pass
            
            am = f"✅ New Deal\n🆔 <code>{did}</code>\n👤 {q.from_user.first_name}"
            for a in ADMINS:
                try: await ctx.bot.send_message(a, am, parse_mode="HTML")
                except: pass
    
    elif d.startswith("cncl_"):
        did = d[5:]
        await q.message.reply_text(f"❌ Deal <code>{did}</code> cancelled", parse_mode="HTML")
    
    elif d.startswith("cmp_"):
        if not ADM(q.from_user.id):
            return await q.message.reply_text("❌ Admins only")
        did = d[4:]
        if COMPLETE_D(did):
            await q.message.reply_text(
                BORD(f"✅ {F('DEAL COMPLETED')} ✅\n🆔 <code>{did}</code>\n✅ {F('Status')}: {F('COMPLETED')}"),
                parse_mode="HTML"
            )

# ====== MAIN ======
def main():
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("flipcoin", coin))
    app.add_handler(CommandHandler("deal", view_deal))
    app.add_handler(CommandHandler("confirm", confirm_deal))
    app.add_handler(CommandHandler("completed", complete))
    
    # Owner commands
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("showmydice", showmydice))
    app.add_handler(CommandHandler("showmycoin", showmycoin))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("deals", deals))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("sendalso", sendalso))
    
    # Form handler
    app.add_handler(MessageHandler(filters.TEXT & filters.GROUP, form_handler))
    
    # Callback
    app.add_handler(CallbackQueryHandler(cb))
    
    print(f"✅ BOT STARTED! Owner: {OWNER_ID}")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()