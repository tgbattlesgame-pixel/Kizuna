import asyncio

import random

import sqlite3

import time

from aiogram import Bot, Dispatcher

from aiogram.filters import Command

from aiogram.types import Message

from aiogram.client.default import DefaultBotProperties

from aiogram.enums import ParseMode

# =====================================

# KIZUNA ARENA CONFIG

# =====================================

TOKEN = "9289492109:AAGyvuTiQ30VKfdCiAS97lR6j5-XMQ_S5uM"

GROUP_ID = -1003883166615

DB = "kizuna_arena.db"

if TOKEN == "PASTE_YOUR_NEW_TOKEN_HERE":

    raise RuntimeError("Add your new Telegram bot token!")

bot = Bot(

    token=TOKEN,

    default=DefaultBotProperties(parse_mode=ParseMode.HTML)

)

dp = Dispatcher()

# =====================================

# DATABASE

# =====================================

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

        user_id INTEGER,

        name TEXT,

        rarity TEXT,

        attack INTEGER,

        defense INTEGER,

        hp INTEGER,

        obtained INTEGER

    )

    """)

    con.commit()

    con.close()

# =====================================

# CHARACTERS

# =====================================

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

RARITY_WEIGHTS = [45, 27, 17, 8, 2.5, 0.5]

# =====================================

# PLAYER FUNCTIONS

# =====================================

def register(user):

    con = connect()

    cur = con.cursor()

    cur.execute("""

    INSERT OR IGNORE INTO players

    (user_id, username, name)

    VALUES (?, ?, ?)

    """, (user.id, user.username or "", user.full_name))

    con.commit()

    con.close()

def get_player(user_id):

    con = connect()

    cur = con.cursor()

    cur.execute(

        "SELECT * FROM players WHERE user_id = ?",

        (user_id,)

    )

    result = cur.fetchone()

    con.close()

    return result

def is_registered(user_id):

    return get_player(user_id) is not None

def add_xp(user_id, amount):

    con = connect()

    cur = con.cursor()

    cur.execute(

        "SELECT xp, level FROM players WHERE user_id = ?",

        (user_id,)

    )

    data = cur.fetchone()

    if data:

        xp, level = data

        xp += amount

        while xp >= level * 100:

            xp -= level * 100

            level += 1

        cur.execute("""

        UPDATE players

        SET xp = ?, level = ?

        WHERE user_id = ?

        """, (xp, level, user_id))

    con.commit()

    con.close()

def allowed(message):

    return (

        message.chat.type in ("group", "supergroup")

        and message.chat.id == GROUP_ID

    )

# =====================================

# START

# =====================================

@dp.message(Command("start"))

async def start(message: Message):

    if not allowed(message):

        return

    register(message.from_user)

    await message.answer(

        "⚔️ <b>WELCOME TO KIZUNA ARENA</b>\n\n"

        "🌌 COLLECT YOUR DESTINY\n"

        "🎴 Build your collection\n"

        "🏆 Become a legend\n\n"

        "💎 Starting Gems: <b>300</b>\n\n"

        "Use /help to explore."

    )

# =====================================

# HELP

# =====================================

@dp.message(Command("help"))

async def help_command(message: Message):

    if not allowed(message):

        return

    await message.answer(

        "⚔️ <b>KIZUNA ARENA COMMANDS</b>\n\n"

        "👤 /start - Register\n"

        "📊 /profile - Profile\n"

        "💎 /daily - Daily reward\n"

        "🎴 /summon - Summon character\n"

        "📚 /collection - Your cards\n"

        "🏆 /leaderboard - Top players"

    )

# =====================================

# PROFILE

# =====================================

@dp.message(Command("profile"))

async def profile(message: Message):

    if not allowed(message):

        return

    player = get_player(message.from_user.id)

    if not player:

        await message.answer("Register first using /start")

        return

    con = connect()

    cur = con.cursor()

    cur.execute(

        "SELECT COUNT(*) FROM cards WHERE user_id = ?",

        (message.from_user.id,)

    )

    card_count = cur.fetchone()[0]

    con.close()

    await message.answer(

        f"👤 <b>{player[2]}</b>\n\n"

        f"💎 Gems: <b>{player[3]}</b>\n"

        f"⭐ Level: <b>{player[5]}</b>\n"

        f"✨ XP: <b>{player[4]}</b>\n"

        f"🏆 Wins: <b>{player[6]}</b>\n"

        f"💔 Losses: <b>{player[7]}</b>\n"

        f"🎴 Cards: <b>{card_count}</b>"

    )

# =====================================

# DAILY

# =====================================

@dp.message(Command("daily"))

async def daily(message: Message):

    if not allowed(message):

        return

    user_id = message.from_user.id

    if not is_registered(user_id):

        await message.answer("Register first using /start")

        return

    con = connect()

    cur = con.cursor()

    cur.execute(

        "SELECT last_daily FROM players WHERE user_id = ?",

        (user_id,)

    )

    last_daily = cur.fetchone()[0]

    now = int(time.time())

    remaining = 86400 - (now - last_daily)

    if remaining > 0:

        hours = remaining // 3600

        minutes = (remaining % 3600) // 60

        await message.answer(

            f"⏳ Next reward in <b>{hours}h {minutes}m</b>"

        )

        con.close()

        return

    cur.execute("""

    UPDATE players

    SET gems = gems + 150,

        last_daily = ?

    WHERE user_id = ?

    """, (now, user_id))

    con.commit()

    con.close()

    await message.answer(

        "🎁 <b>DAILY CLAIMED!</b>\n\n"

        "💎 +150 Gems"

    )

# =====================================

# SUMMON

# =====================================

@dp.message(Command("summon"))

async def summon(message: Message):

    if not allowed(message):

        return

    user_id = message.from_user.id

    if not is_registered(user_id):

        await message.answer("Register first using /start")

        return

    player = get_player(user_id)

    if player[3] < 100:

        await message.answer("❌ You need 100 Gems!")

        return

    character = random.choices(

        CHARACTERS,

        weights=[45, 27, 17, 8, 2.5, 0.5, 0, 0],

        k=1

    )[0]

    name, rarity, attack, defense, hp = character

    con = connect()

    cur = con.cursor()

    cur.execute(

        "UPDATE players SET gems = gems - 100 WHERE user_id = ?",

        (user_id,)

    )

    cur.execute("""

    INSERT INTO cards

    (user_id, name, rarity, attack, defense, hp, obtained)

    VALUES (?, ?, ?, ?, ?, ?, ?)

    """, (

        user_id, name, rarity, attack,

        defense, hp, int(time.time())

    ))

    con.commit()

    con.close()

    add_xp(user_id, 10)

    await message.answer(

        "✨ <b>SUMMON SUCCESSFUL!</b>\n\n"

        f"🎴 <b>{name}</b>\n"

        f"💠 Rarity: <b>{rarity}</b>\n\n"

        f"⚔️ Attack: {attack}\n"

        f"🛡️ Defense: {defense}\n"

        f"❤️ HP: {hp}\n\n"

        "⭐ +10 XP"

    )

# =====================================

# COLLECTION

# =====================================

@dp.message(Command("collection"))

async def collection(message: Message):

    if not allowed(message):

        return

    user_id = message.from_user.id

    if not is_registered(user_id):

        await message.answer("Register first using /start")

        return

    con = connect()

    cur = con.cursor()

    cur.execute("""

    SELECT name, rarity

    FROM cards

    WHERE user_id = ?

    ORDER BY id DESC

    LIMIT 30

    """, (user_id,))

    cards = cur.fetchall()

    con.close()

    if not cards:

        await message.answer(

            "📚 Collection empty!\nUse /summon to get cards."

        )

        return

    text = "🎴 <b>YOUR COLLECTION</b>\n\n"

    for index, card in enumerate(cards, 1):

        text += f"{index}. <b>{card[0]}</b>\n   💠 {card[1]}\n\n"

    await message.answer(text)

# =====================================

# LEADERBOARD

# =====================================

@dp.message(Command("leaderboard"))

async def leaderboard(message: Message):

    if not allowed(message):

        return

    con = connect()

    cur = con.cursor()

    cur.execute("""

    SELECT name, level, gems, wins

    FROM players

    ORDER BY level DESC, wins DESC

    LIMIT 10

    """)

    players = cur.fetchall()

    con.close()

    if not players:

        await message.answer("No players registered yet!")

        return

    text = "🏆 <b>KIZUNA ARENA TOP PLAYERS</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for index, player in enumerate(players):

        medal = medals[index] if index < 3 else f"{index + 1}."

        text += (

            f"{medal} <b>{player[0]}</b>\n"

            f"⭐ Level {player[1]} | 💎 {player[2]} | "

            f"🏆 {player[3]} wins\n\n"

        )

    await message.answer(text)

# =====================================

# RUN

# =====================================

async def main():

    setup_database()

    print("================================")

    print(" KIZUNA ARENA IS ONLINE")

    print("================================")

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
