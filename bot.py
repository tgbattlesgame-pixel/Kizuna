
import asyncio
import os
import random
import sqlite3
import time

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing!")

DB = "kizuna_arena.db"

bot = Bot(
    TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ================= DATABASE =================

def connect():
    return sqlite3.connect(DB)

def setup_database():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        gems INTEGER DEFAULT 300,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        last_daily INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        rarity TEXT NOT NULL,
        attack INTEGER,
        defense INTEGER,
        hp INTEGER,
        obtained INTEGER
    )
    """)

    con.commit()
    con.close()

def register(user):
    con = connect()
    cur = con.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO players
    (user_id, username, name)
    VALUES (?, ?, ?)
    """, (user.id, user.username, user.full_name))

    cur.execute("""
    UPDATE players
    SET username=?, name=?
    WHERE user_id=?
    """, (user.username, user.full_name, user.id))

    con.commit()
    con.close()

def get_player(user_id):
    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM players WHERE user_id=?",
        (user_id,)
    )

    data = cur.fetchone()
    con.close()
    return data

def is_registered(user_id):
    return get_player(user_id) is not None

# ================= GROUP SECURITY =================

def allowed(message):
    return (
        message.chat.type in ("group", "supergroup")
        and (
            GROUP_ID == 0
            or message.chat.id == GROUP_ID
        )
    )

# ================= CHARACTER DATABASE =================

CHARACTERS = [
    ("Rin the Stormblade", "COMMON", 42, 38, 100),
    ("Mika the Ember Fox", "COMMON", 39, 35, 105),
    ("Kael the Iron Guard", "RARE", 58, 62, 130),
    ("Yuna the Moon Archer", "RARE", 64, 44, 110),
    ("Ren the Rift Mage", "EPIC", 82, 48, 120),
    ("Astra the Star Warden", "EPIC", 70, 76, 145),
    ("Kuro the Void King", "LEGENDARY", 105, 78, 165),
    ("Seraphine, Dawn Eternal", "MYTHIC", 118, 102, 185),
]

RARITIES = [
    "COMMON",
    "RARE",
    "EPIC",
    "LEGENDARY",
    "MYTHIC",
    "DIVINE"
]

WEIGHTS = [45, 27, 17, 8, 2.5, 0.5]

ICONS = {
    "COMMON": "⚪",
    "RARE": "🔵",
    "EPIC": "🟣",
    "LEGENDARY": "🟠",
    "MYTHIC": "🔴",
    "DIVINE": "🌟"
}

def summon_character():
    rarity = random.choices(
        RARITIES,
        weights=WEIGHTS,
        k=1
    )[0]

    available = [
        c for c in CHARACTERS
        if c[1] == rarity
    ]

    if not available:
        available = [
            c for c in CHARACTERS
            if c[1] == "COMMON"
        ]

    return random.choice(available)

# ================= XP SYSTEM =================

def add_xp(user_id, amount):
    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT xp, level FROM players WHERE user_id=?",
        (user_id,)
    )

    xp, level = cur.fetchone()
    xp += amount

    while xp >= level * 100:
        xp -= level * 100
        level += 1

    cur.execute("""
    UPDATE players
    SET xp=?, level=?
    WHERE user_id=?
    """, (xp, level, user_id))

    con.commit()
    con.close()

    return level

# ================= START =================

@dp.message(Command("start"))
async def start(message: Message):

    if not allowed(message):
        return

    user = message.from_user
    register(user)

    await message.answer(
        f"""
⚔️ <b>KIZUNA ARENA</b>

Welcome, {user.mention_html()}!

Your journey begins now.

💎 Starting Gems: 300

🃏 Collect legendary fighters.
⚔️ Build your ultimate team.
🏆 Become the strongest trainer.

━━━━━━━━━━━━━━━━

Use /help to explore commands.
"""
    )

# ================= HELP =================

@dp.message(Command("help"))
async def help_command(message: Message):

    if not allowed(message):
        return

    await message.answer(
        """
✦ <b>KIZUNA ARENA COMMANDS</b>

👤 /profile — Trainer profile
🎁 /daily — Daily gems
✨ /summon — Summon character
🃏 /collection — Your cards
🏆 /leaderboard — Top trainers

━━━━━━━━━━━━━━━━

More features coming soon!
"""
    )

# ================= PROFILE =================

@dp.message(Command("profile"))
async def profile(message: Message):

    if not allowed(message):
        return

    user = message.from_user

    if not is_registered(user.id):
        await message.answer("Use /start first!")
        return

    data = get_player(user.id)

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM cards WHERE user_id=?",
        (user.id,)
    )

    total = cur.fetchone()[0]
    con.close()

    await message.answer(
        f"""
👤 <b>TRAINER PROFILE</b>

Name: {user.mention_html()}

🏅 Level: {data[5]}
✨ XP: {data[4]}
💎 Gems: {data[3]}

🃏 Cards: {total}

⚔️ Wins: {data[6]}
💔 Losses: {data[7]}
"""
    )

# ================= DAILY =================

@dp.message(Command("daily"))
async def daily(message: Message):

    if not allowed(message):
        return

    user = message.from_user

    if not is_registered(user.id):
        await message.answer("Use /start first!")
        return

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT last_daily FROM players WHERE user_id=?",
        (user.id,)
    )

    last = cur.fetchone()[0]
    now = int(time.time())

    if now - last < 86400:
        remaining = 86400 - (now - last)

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        await message.answer(
            f"⏳ Already claimed!\n"
            f"Come back in {hours}h {minutes}m."
        )

        con.close()
        return

    cur.execute("""
    UPDATE players
    SET gems=gems+150, last_daily=?
    WHERE user_id=?
    """, (now, user.id))

    con.commit()
    con.close()

    await message.answer(
        """
🎁 <b>DAILY REWARD CLAIMED!</b>

💎 +150 Gems

See you tomorrow, Trainer!
"""
    )

# ================= SUMMON =================

@dp.message(Command("summon"))
async def summon(message: Message):

    if not allowed(message):
        return

    user = message.from_user

    if not is_registered(user.id):
        await message.answer("Use /start first!")
        return

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT gems FROM players WHERE user_id=?",
        (user.id,)
    )

    gems = cur.fetchone()[0]

    if gems < 100:
        con.close()

        await message.answer(
            "❌ Not enough Gems!\n"
            "Use /daily to earn more."
        )
        return

    card = summon_character()

    cur.execute("""
    UPDATE players
    SET gems=gems-100
    WHERE user_id=?
    """, (user.id,))

    cur.execute("""
    INSERT INTO cards
    (user_id, name, rarity, attack, defense, hp, obtained)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user.id,
        card[0],
        card[1],
        card[2],
        card[3],
        card[4],
        int(time.time())
    ))

    con.commit()
    con.close()

    level = add_xp(user.id, 10)

    await message.answer(
        f"""
✨ <b>SUMMON SUCCESSFUL!</b>

{ICONS[card[1]]} <b>{card[0]}</b>

Rarity: <b>{card[1]}</b>

⚔️ Attack: {card[2]}
🛡 Defense: {card[3]}
❤️ HP: {card[4]}

━━━━━━━━━━━━━━━━

💎 Cost: 100 Gems
✨ +10 XP
🏅 Current Level: {level}
"""
    )

# ================= COLLECTION =================

@dp.message(Command("collection"))
async def collection(message: Message):

    if not allowed(message):
        return

    user = message.from_user

    if not is_registered(user.id):
        await message.answer("Use /start first!")
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
    SELECT name, rarity, attack, defense, hp
    FROM cards
    WHERE user_id=?
    ORDER BY obtained DESC
    LIMIT 30
    """, (user.id,))

    cards = cur.fetchall()
    con.close()

    if not cards:
        await message.answer(
            "🃏 Collection empty!\nUse /summon."
        )
        return

    lines = ["🃏 <b>YOUR COLLECTION</b>\n"]

    for card in cards:
        lines.append(
            f"{ICONS[card[1]]} <b>{card[0]}</b>\n"
            f"Rarity: {card[1]}\n"
            f"⚔️ {card[2]} | 🛡 {card[3]} | ❤️ {card[4]}\n"
        )

    await message.answer("\n".join(lines))

# ================= LEADERBOARD =================

@dp.message(Command("leaderboard"))
async def leaderboard(message: Message):

    if not allowed(message):
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
    SELECT name, level, gems
    FROM players
    ORDER BY level DESC, gems DESC
    LIMIT 10
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await message.answer("No trainers yet!")
        return

    lines = ["🏆 <b>KIZUNA ARENA TOP TRAINERS</b>\n"]

    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. <b>{row[0]}</b>\n"
            f"🏅 Level: {row[1]} | 💎 Gems: {row[2]}\n"
        )

    await message.answer("\n".join(lines))

# ================= LAUNCH =================

async def main():

    setup_database()

    print("KIZUNA ARENA V0.1 ONLINE")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
