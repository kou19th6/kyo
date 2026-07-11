import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 
import math
import os
import anthropic

# =====================================================================
# THIẾT LẬP CƠ BẢN
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')
# =====================================================================
# AI TRẢ LỜI KHI TAG BOT
# =====================================================================
try:
    AI_CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
except Exception as e:
    print(f"[WARN] Không khởi tạo được AI client: {e}")
    AI_CLIENT = None

ai_cooldowns = {}
AI_COOLDOWN_SECONDS = 8

async def get_ai_reply(prompt: str, username: str) -> str:
    if not AI_CLIENT:
        return "⚠️ AI chưa được cấu hình! Báo admin thiết lập ANTHROPIC_API_KEY."
    try:
        response = AI_CLIENT.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=600,
            system=(
                "Bạn là trợ lý AI thân thiện trong một Discord server tên KYO CLUB. "
                "Trả lời ngắn gọn, tự nhiên, dùng tiếng Việt trừ khi được hỏi bằng ngôn ngữ khác. "
                "Không dùng markdown quá phức tạp, phù hợp hiển thị trong Discord."
            ),
            messages=[{"role": "user", "content": f"{username} hỏi: {prompt}"}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"[ERROR] AI error: {e}")
        return "⚠️ AI đang gặp sự cố, thử lại sau nhé!"
# =====================================================================
# KHO ẢNH GIF ĐỘNG
# =====================================================================
GIF_LINKS = {
    "jail": "https://media.giphy.com/media/uG3lKkAuh53wKxY0l9/giphy.gif",
    "bank": "https://media.giphy.com/media/xTiTnqUxyWbsAXq7Ju/giphy.gif",
    "rob_success": "https://media.giphy.com/media/Y2ZUWLrTy63j9T6qrK/giphy.gif",
    "rob_fail": "https://media.giphy.com/media/RYjnzPS8u0jAs/giphy.gif",
    "mine": "https://media.giphy.com/media/26ufj1Xj9Vn6QO6vC/giphy.gif",
    "gacha": "https://media.giphy.com/media/3o7TKoHNJTWWLgljYQ/giphy.gif",
    "casino": "https://media.giphy.com/media/l4hLA4ALhloJt2Tny/giphy.gif",
    "marry": "https://media.giphy.com/media/l41JRsph73VokN6ik/giphy.gif",
    "daily": "https://media.giphy.com/media/67ThRZlYBvibtdF9JH/giphy.gif",
    "rank": "https://media.giphy.com/media/LdOyjZ7io5Msw/giphy.gif",
    "fight": "https://media.giphy.com/media/3o7TKsWbXJMIdURvkk/giphy.gif",
    "rugpull": "https://media.giphy.com/media/3o6DWzmToltqKtvRo/giphy.gif",
    "bankrupt": "https://media.giphy.com/media/3o6UB5RrlQuMfZp82Y/giphy.gif",
    "fishing": "https://media.giphy.com/media/3o7TKFZLmO0nqnO4mA/giphy.gif",
    "work": "https://media.giphy.com/media/LmNwrBhejkK9EFP504/giphy.gif",
    "level_up": "https://media.giphy.com/media/3o7btNhMBytxAM6YBa/giphy.gif",
    "quest": "https://media.giphy.com/media/xT0GqGUyFPeYZsNzO0/giphy.gif",
    "duel": "https://media.giphy.com/media/3o7TKsWbXJMIdURvkk/giphy.gif",
}

# =====================================================================
# QUẢN LÝ TRẠNG THÁI
# =====================================================================
gamble_cooldowns = {}
nhansinh_cooldowns = {}
dang_choi_nhansinh = []
cty_cooldowns = {}
work_cooldowns = {}
mining_cooldowns = {}
rob_cooldowns = {}
stock_cooldowns = {}
gacha_cooldowns = {}
fishing_cooldowns = {}
blackjack_games = {}   # NEW
poker_games = {}       # NEW
duel_invites = {}

_processing_users = set()

def acquire_lock(user_id):
    uid = str(user_id)
    if uid in _processing_users:
        return False
    _processing_users.add(uid)
    return True

def release_lock(user_id):
    _processing_users.discard(str(user_id))

# =====================================================================
# KẾT NỐI MONGODB
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    retryWrites=True,
)
db = mongo_client["DiscordBotDB"]

users_col = db["users"]
config_col = db["config"]
companies_col = db["companies"]
stock_orders_col = db["stock_orders"]   # NEW: lệnh chờ khớp
stock_history_col = db["stock_history"] # NEW: lịch sử giá

DB_CACHE = {}
CONFIG_CACHE = {}
COMPANY_CACHE = {}

def load_user(user_id):
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        try:
            document = users_col.find_one({"_id": user_id})
            if document:
                DB_CACHE[user_id] = document
            else:
                DB_CACHE[user_id] = {}
        except Exception as e:
            print(f"[WARN] load_user DB error for {user_id}: {e}")
            if user_id not in DB_CACHE:
                DB_CACHE[user_id] = {}

    defaults = {
        "xp": 0, "level": 1, "money": 0, "bank": 0, "title": "Dân Đáy Xã Hội 🧱",
        "assets": [], "pets": {}, "company": None, "stocks": {},
        "jail_time": None, "spouse": None, "history": [],
        "farm": {"seed": None, "plant_time": None}, "last_interest": "2000-01-01 00:00:00",
        "quest": None, "quest_progress": 0, "last_quest": "2000-01-01 00:00:00",
        "inventory": {}, "skill_points": 0, "prestige": 0,
        "fishing_rod": False, "fish_count": 0,
        "streak": 0, "last_daily": None, "last_lixi": None,
        "badges": [], "achievements": [],
        "last_work": "2000-01-01 00:00:00",
        "last_stock_trade": "2000-01-01 00:00:00",
        "last_gacha": "2000-01-01 00:00:00",
        "last_mine": "2000-01-01 00:00:00",
        "last_rob": "2000-01-01 00:00:00",
        "stock_buy_prices": {},
        # NEW stock fields
        "stock_orders": [],          # lệnh đặt chờ khớp
        "portfolio_value_history": [], # lịch sử giá trị portfolio
        "margin_used": 0,            # tiền vay để mua ký quỹ
        "margin_interest_date": "2000-01-01 00:00:00",
        "stop_loss": {},             # cắt lỗ tự động {code: price}
        "take_profit": {},           # chốt lời tự động {code: price}
        "short_positions": {},       # bán khống {code: qty}
        "short_buy_prices": {},      # giá bán khống ban đầu
        # NEW general fields
        "lottery_tickets": [],       # vé số đặc biệt
        "last_wheel": "2000-01-01 00:00:00",  # vòng quay may mắn
        "loan_amount": 0,            # tiền đang vay ngân hàng
        "loan_due": None,            # hạn trả nợ
        "crime_record": 0,           # số lần phạm tội
        "bounty": 0,                 # tiền thưởng truy nã
        "gym_level": 0,              # level gym (buff duel)
    }

    for key, value in defaults.items():
        if key not in DB_CACHE[user_id]:
            DB_CACHE[user_id][key] = value

    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE:
        try:
            users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)
        except Exception as e:
            print(f"[ERROR] save_user DB error for {user_id}: {e}")

def load_server_config(server_id):
    server_id = str(server_id)
    if server_id not in CONFIG_CACHE:
        try:
            document = config_col.find_one({"_id": server_id})
            if document:
                CONFIG_CACHE[server_id] = document
            else:
                CONFIG_CACHE[server_id] = {}
        except Exception as e:
            print(f"[WARN] load_server_config DB error: {e}")
            CONFIG_CACHE[server_id] = {}
    return CONFIG_CACHE[server_id]

def load_company(company_id):
    company_id = str(company_id)
    if company_id not in COMPANY_CACHE:
        try:
            document = companies_col.find_one({"_id": company_id})
            if document:
                comp_defaults = {
                    "reputation": 100, "has_scandal": False,
                    "atk_level": 1, "def_level": 1,
                    "debt": 0, "debt_due": None,
                    "security_level": 1,
                    "last_pr": "2000-01-01 00:00:00",
                    "last_smear": "2000-01-01 00:00:00",
                    "last_spy": "2000-01-01 00:00:00",
                    "last_dividend": "2000-01-01 00:00:00",
                }
                for k, v in comp_defaults.items():
                    if k not in document: document[k] = v
                COMPANY_CACHE[company_id] = document
            else:
                return None
        except Exception as e:
            print(f"[WARN] load_company DB error: {e}")
            return None
    return COMPANY_CACHE[company_id]

def save_company(company_id):
    company_id = str(company_id)
    if company_id in COMPANY_CACHE:
        try:
            companies_col.update_one({"_id": company_id}, {"$set": COMPANY_CACHE[company_id]}, upsert=True)
        except Exception as e:
            print(f"[ERROR] save_company DB error for {company_id}: {e}")

# =====================================================================
# THƯƠNG TRƯỜNG: VAY NỢ, PR, GIÁN ĐIỆP, PHÁ SẢN
# =====================================================================
COMPANY_LOAN_INTEREST       = 0.25   # lãi vay công ty 25%
COMPANY_LOAN_DAYS           = 5      # hạn trả nợ
COMPANY_LOAN_MAX_MULT       = 3.0    # vay tối đa 3x quỹ hiện có
PR_COOLDOWN_HOURS           = 12
SMEAR_COOLDOWN_HOURS        = 18
SPY_COOLDOWN_HOURS          = 18
ESPIONAGE_CAUGHT_FINE_MULT  = 0.10
SMEAR_CAUGHT_REP_LOSS       = 25

async def bankrupt_company(comp_id, reason="Không trả được nợ", channel=None):
    """Giải thể công ty, sa thải toàn bộ nhân sự."""
    comp = load_company(comp_id)
    if not comp:
        return
    member_ids = list(comp.get("members", {}).keys())
    for m_id in member_ids:
        m_data = load_user(m_id)
        m_data["company"] = None
        save_user(m_id)

    COMPANY_CACHE.pop(comp_id, None)
    try:
        companies_col.delete_one({"_id": comp_id})
    except Exception as e:
        print(f"[WARN] bankrupt_company delete error: {e}")

    if channel:
        try:
            embed = discord.Embed(
                title="💥 CÔNG TY PHÁ SẢN!",
                description=(
                    f"**{comp['name']}** đã chính thức **PHÁ SẢN** và giải thể!\n"
                    f"Lý do: {reason}\n"
                    f"Toàn bộ **{len(member_ids)}** nhân sự mất việc."
                ),
                color=discord.Color.dark_red()
            )
            embed.set_image(url=GIF_LINKS.get("bankrupt", ""))
            await channel.send(embed=embed)
        except Exception:
            pass


async def process_company_debt():
    """Mỗi giờ kiểm tra nợ quá hạn công ty -> tự trả hoặc phá sản."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now()
            overdue = list(companies_col.find({"debt": {"$gt": 0}}))
            for doc in overdue:
                comp_id = doc["_id"]
                COMPANY_CACHE[comp_id] = doc
                comp = COMPANY_CACHE[comp_id]
                due_str = comp.get("debt_due")
                if not due_str:
                    continue
                try:
                    due = datetime.strptime(due_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if now < due:
                    continue

                debt = comp.get("debt", 0)
                if comp.get("treasury", 0) >= debt:
                    comp["treasury"] -= debt
                    comp["debt"] = 0
                    comp["debt_due"] = None
                    save_company(comp_id)
                else:
                    comp["treasury"] = 0
                    save_company(comp_id)
                    target_channel = None
                    try:
                        for guild in bot.guilds:
                            ch = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                            if ch:
                                target_channel = ch
                                break
                    except Exception:
                        pass
                    await bankrupt_company(
                        comp_id,
                        reason="Nợ quá hạn, ngân hàng siết toàn bộ tài sản",
                        channel=target_channel
                    )
        except Exception as e:
            print(f"[WARN] process_company_debt error: {e}")
        await asyncio.sleep(3600)

def add_history(user_id, entry):
    user_data = load_user(user_id)
    if "history" not in user_data: user_data["history"] = []
    time_str = datetime.now().strftime('%H:%M %d/%m')
    user_data["history"].insert(0, f"[`{time_str}`] {entry}")
    if len(user_data["history"]) > 20: user_data["history"].pop()

def check_achievement(user_id, user_data):
    achievements = user_data.get("achievements", [])
    new_achievements = []

    total_money = user_data.get("money", 0) + user_data.get("bank", 0)
    if total_money >= 1_000_000 and "millionaire" not in achievements:
        achievements.append("millionaire")
        new_achievements.append("💰 Triệu Phú Đầu Tiên")
    if total_money >= 1_000_000_000 and "billionaire" not in achievements:
        achievements.append("billionaire")
        new_achievements.append("👑 Tỷ Phú Đồng")
    if user_data.get("level", 1) >= 10 and "level10" not in achievements:
        achievements.append("level10")
        new_achievements.append("⭐ Đạt Cấp 10")
    if user_data.get("level", 1) >= 50 and "level50" not in achievements:
        achievements.append("level50")
        new_achievements.append("🌟 Huyền Thoại Cấp 50")
    if len(user_data.get("pets", {})) >= 5 and "pet_collector" not in achievements:
        achievements.append("pet_collector")
        new_achievements.append("🐾 Nhà Thú Cưng")
    if user_data.get("fish_count", 0) >= 50 and "fisher" not in achievements:
        achievements.append("fisher")
        new_achievements.append("🎣 Ngư Dân Lão Luyện")
    if user_data.get("streak", 0) >= 7 and "streak7" not in achievements:
        achievements.append("streak7")
        new_achievements.append("🔥 Chuỗi 7 Ngày")
    if user_data.get("streak", 0) >= 30 and "streak30" not in achievements:
        achievements.append("streak30")
        new_achievements.append("🌈 Chuỗi 30 Ngày")

    user_data["achievements"] = achievements
    return new_achievements

# =====================================================================
# GLOBAL CHECK
# =====================================================================
@bot.check
async def global_jail_and_channel_check(ctx):
    if ctx.author.guild_permissions.administrator:
        return True
    if ctx.command and ctx.command.name == "help":
        return True

    user_data = load_user(ctx.author.id)
    jail_time_str = user_data.get("jail_time")

    if jail_time_str:
        try:
            jail_end = datetime.strptime(jail_time_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < jail_end:
                embed = discord.Embed(
                    title="🚨 BÁO ĐỘNG ĐỎ!",
                    description=f"{ctx.author.mention} đang bóc lịch trong trại giam!\n\n"
                                f"⏳ Mãn hạn: <t:{int(jail_end.timestamp())}:R>",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=GIF_LINKS["jail"])
                await ctx.reply(embed=embed, mention_author=False)
                return False
            else:
                user_data["jail_time"] = None
                save_user(ctx.author.id)
        except Exception:
            user_data["jail_time"] = None
            save_user(ctx.author.id)

    if ctx.guild:
        try:
            server_config = load_server_config(ctx.guild.id)
            allowed_channels = server_config.get("allowed_channels", [])
            if allowed_channels and ctx.channel.id not in allowed_channels:
                channel_mentions = [f"<#{cid}>" for cid in allowed_channels]
                embed = discord.Embed(
                    description=f"⚠️ Vui lòng dùng bot tại: {', '.join(channel_mentions)}",
                    color=discord.Color.orange()
                )
                try:
                    await ctx.reply(embed=embed, mention_author=False, delete_after=5)
                except Exception:
                    pass
                return False
        except Exception as e:
            print(f"[WARN] channel check error: {e}")

    return True

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply(embed=discord.Embed(description="❌ Bạn không có quyền dùng lệnh này!", color=discord.Color.red()), mention_author=False)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(embed=discord.Embed(description=f"⚠️ Thiếu thông tin! Gõ `k help` để xem hướng dẫn.", color=discord.Color.orange()), mention_author=False)
        return
    if isinstance(error, commands.MemberNotFound):
        await ctx.reply(embed=discord.Embed(description="⚠️ Không tìm thấy người dùng này! Hãy tag trực tiếp @tên.", color=discord.Color.orange()), mention_author=False)
        return
    if isinstance(error, commands.CommandNotFound):
        return
    release_lock(ctx.author.id)
    print(f"[ERROR] Lệnh '{ctx.command}' của {ctx.author} gặp lỗi: {error}")
    try:
        await ctx.reply(embed=discord.Embed(description="⚙️ Có lỗi xảy ra! Thử lại sau hoặc báo admin.", color=discord.Color.red()), mention_author=False)
    except Exception:
        pass

# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================
def make_progress_bar(current_value, total_value, bar_length=12):
    if total_value == 0: return "⬛" * bar_length
    progress_blocks = int((current_value / total_value) * bar_length)
    empty_blocks = bar_length - progress_blocks
    return "🟩" * progress_blocks + "⬛" * empty_blocks

async def check_gamble_conditions(ctx, amount_str):
    user_id = str(ctx.author.id)
    current_time = datetime.now()

    if user_id in gamble_cooldowns:
        time_diff = (current_time - gamble_cooldowns[user_id]).total_seconds()
        if time_diff < 6:
            embed_cd = discord.Embed(description=f"⏳ Tay mỏi rồi! Đợi {int(6 - time_diff)}s nữa!", color=discord.Color.orange())
            await ctx.reply(embed=embed_cd, mention_author=False)
            return None, None

    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        embed_bankrupt = discord.Embed(description="💸 Ví trống không! Đi cày thêm đi sếp.", color=discord.Color.red())
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
        return None, None

    try:
        if amount_str.lower() == "all": bet_amount = min(user_data["money"], 200000)
        else: bet_amount = int(amount_str)
    except ValueError:
        embed_err = discord.Embed(description="⚠️ Nhập số tiền sai! Nhập số hoặc `all`.", color=discord.Color.red())
        await ctx.reply(embed=embed_err, mention_author=False)
        return None, None

    if bet_amount <= 0 or bet_amount > user_data["money"]:
        embed_poor = discord.Embed(description=f"⚠️ Sếp chỉ có **{user_data['money']:,} 💰** thôi!", color=discord.Color.red())
        await ctx.reply(embed=embed_poor, mention_author=False)
        return None, None

    if bet_amount > 300000:
        embed_max = discord.Embed(description="🛑 Mỗi ván tối đa **300,000 💰** thôi nhé!", color=discord.Color.red())
        await ctx.reply(embed=embed_max, mention_author=False)
        return None, None

    return user_data, bet_amount

# =====================================================================
# DATA HỆ THỐNG
# =====================================================================
FARM_SEEDS = {
    "lua": {"name": "Lúa Mì 🌾", "cost": 8000, "time_hours": 6, "profit_min": 15000, "profit_max": 22000},
    "ngo": {"name": "Ngô Đồng 🌽", "cost": 25000, "time_hours": 12, "profit_min": 40000, "profit_max": 58000},
    "cachua": {"name": "Cà Chua Đỏ 🍅", "cost": 50000, "time_hours": 18, "profit_min": 85000, "profit_max": 125000},
    "nhansam": {"name": "Nhân Sâm Ngàn Năm 🌿", "cost": 150000, "time_hours": 36, "profit_min": 350000, "profit_max": 550000},
    "duahau": {"name": "Dưa Hấu Khổng Lồ 🍉", "cost": 80000, "time_hours": 24, "profit_min": 150000, "profit_max": 230000},
    "socola": {"name": "Cây Socola Thần Kỳ 🍫", "cost": 300000, "time_hours": 48, "profit_min": 700000, "profit_max": 1100000},
}

SHOP_ITEMS = {
    "title_1": {"type": "title", "name": "Kẻ Lưu Đày 🛖", "price": 10000, "emoji": "🏷️"},
    "title_2": {"type": "title", "name": "Tiểu Thương 🏪", "price": 50000, "emoji": "🏷️"},
    "title_3": {"type": "title", "name": "Phú Nông 🌾", "price": 200000, "emoji": "🏷️"},
    "title_4": {"type": "title", "name": "Đại Gia 💸", "price": 1000000, "emoji": "🏷️"},
    "title_5": {"type": "title", "name": "Tỷ Phú 💎", "price": 5000000, "emoji": "🏷️"},
    "title_6": {"type": "title", "name": "Thần Tài 🧧", "price": 20000000, "emoji": "🏷️"},
    "title_7": {"type": "title", "name": "Kẻ Thống Trị Vũ Trụ 🌌", "price": 100000000, "emoji": "👑"},
    "vehicle_1": {"type": "vehicle", "name": "Xe Đạp Địa Hình 🚲", "price": 15000, "emoji": "🚲"},
    "vehicle_2": {"type": "vehicle", "name": "Honda SH 150i 🏍️", "price": 300000, "emoji": "🏍️"},
    "vehicle_3": {"type": "vehicle", "name": "Toyota Camry 🚗", "price": 2000000, "emoji": "🚗"},
    "vehicle_4": {"type": "vehicle", "name": "Mercedes G63 🚙", "price": 8000000, "emoji": "🚙"},
    "vehicle_5": {"type": "vehicle", "name": "Lamborghini Aventador 🏎️", "price": 25000000, "emoji": "🏎️"},
    "vehicle_6": {"type": "vehicle", "name": "Du Thuyền Hạng Sang 🛥️", "price": 150000000, "emoji": "🛥️"},
    "vehicle_7": {"type": "vehicle", "name": "Trạm Không Gian UFO 🛸", "price": 900000000, "emoji": "🛸"},
    "house_1": {"type": "house", "name": "Nhà Trọ Ẩm Thấp ⛺", "price": 50000, "emoji": "⛺"},
    "house_2": {"type": "house", "name": "Chung Cư Mini 🏢", "price": 500000, "emoji": "🏢"},
    "house_3": {"type": "house", "name": "Nhà Phố 3 Tầng 🏘️", "price": 5000000, "emoji": "🏘️"},
    "house_4": {"type": "house", "name": "Biệt Thự Hồ Tây 🏡", "price": 30000000, "emoji": "🏡"},
    "house_5": {"type": "house", "name": "Lâu Đài Cổ Tích 🏰", "price": 150000000, "emoji": "🏰"},
    "house_6": {"type": "house", "name": "Đảo Tư Nhân Maldives 🏝️", "price": 600000000, "emoji": "🏝️"},
    "house_7": {"type": "house", "name": "Hành Tinh Namek 🪐", "price": 2000000000, "emoji": "🪐"},
    "tool_1": {"type": "tool", "name": "Cần Câu Cơ Bản 🎣", "price": 8000, "emoji": "🎣"},
    "tool_2": {"type": "tool", "name": "Cần Câu Carbon 🎣", "price": 80000, "emoji": "🎣"},
    "tool_3": {"type": "tool", "name": "Máy Câu Tự Động ⚙️", "price": 350000, "emoji": "⚙️"},
}

def get_asset_price(asset_name):
    for item_key, item_data in SHOP_ITEMS.items():
        if item_data["name"] == asset_name: return int(item_data["price"] * 0.6)
    return 1000

PET_RATES = {
    "common": {"rate": 70.0, "pool": ["Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", "Lợn Đất 🐖", "Cáo Nhỏ 🦊", "Chuột Đồng 🐁"]},
    "rare": {"rate": 20.0, "pool": ["Sói Tuyết 🐺", "Gấu Xám 🐻", "Đại Bàng 🦅", "Báo Gấm 🐆"]},
    "epic": {"rate": 7.0, "pool": ["Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍", "Bạch Hổ 🐅", "Tê Giác Thiết Giáp 🦏"]},
    "legendary": {"rate": 2.5, "pool": ["Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", "Phượng Hoàng Lửa 🦚", "Thủy Quái Leviathan 🐙"]},
    "mythic": {"rate": 0.5, "pool": ["Thần Long Hoàng Kim 🐲", "Hắc Ám Cự Thú 🦇", "Mèo Thần Tài Siêu Cấp 😻", "Godzilla Vĩ Đại 🦖"]}
}

def get_pet_sell_price(pet_name):
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 3000
            if rarity == "rare": return 15000
            if rarity == "epic": return 100000
            if rarity == "legendary": return 600000
            if rarity == "mythic": return 8000000
    return 1000

# =====================================================================
# HỆ THỐNG CHỨNG KHOÁN THỰC TẾ (HOÀN TOÀN MỚI)
# =====================================================================

STANDARD_STOCKS = {
    "VIN": {"name": "Tập Đoàn VIN", "base": 80000, "sector": "BDS", "volatility": 0.03},
    "FLC": {"name": "Hàng Không FLC", "base": 12000, "sector": "HK", "volatility": 0.05},
    "VNZ": {"name": "Công Nghệ VNZ", "base": 150000, "sector": "TECH", "volatility": 0.04},
    "DOGE": {"name": "Doge Coin", "base": 5000, "sector": "CRYPTO", "volatility": 0.15},
    "BTC": {"name": "Bitcoin", "base": 500000, "sector": "CRYPTO", "volatility": 0.10},
    "AAPL": {"name": "Apple Inc.", "base": 200000, "sector": "TECH", "volatility": 0.025},
    "TSLA": {"name": "Tesla", "base": 180000, "sector": "AUTO", "volatility": 0.07},
    "VCB": {"name": "Vietcombank", "base": 90000, "sector": "BANK", "volatility": 0.02},
    "TCB": {"name": "Techcombank", "base": 55000, "sector": "BANK", "volatility": 0.025},
    "HPG": {"name": "Hòa Phát Group", "base": 40000, "sector": "STEEL", "volatility": 0.035},
}

# Hằng số thị trường
STOCK_TAX_RATE = 0.001      # Thuế bán 0.1% (thực tế VN)
STOCK_SPREAD = 0.001        # Spread 0.1%
MARGIN_INTEREST_RATE = 0.15 # Lãi vay ký quỹ 15%/năm
MAX_MARGIN_RATIO = 2.0      # Tối đa vay gấp 2 lần tài sản
CIRCUIT_BREAKER = 0.07      # Tạm ngừng khi giá thay đổi >7% trong phiên

# Lưu trữ giá phiên trong RAM để tính circuit breaker
_session_open_prices = {}   # {code: giá mở phiên}
_market_events = []         # tin tức thị trường đang active

def get_sector_trend(sector):
    """Tính xu hướng ngành theo giờ"""
    hour = datetime.now().hour
    rng = random.Random(int(datetime.now().strftime("%Y%m%d%H")) + sum(ord(c) for c in sector))
    return rng.uniform(-0.02, 0.02)

def get_stock_price(stock_code, hour_offset=0, use_cache=True):
    """Tính giá cổ phiếu với mô phỏng Geometric Brownian Motion"""
    code = stock_code.upper()

    # Kiểm tra cổ phiếu IPO của công ty
    try:
        ipo_comp = companies_col.find_one({"is_ipo": True, "name": {"$regex": f"^{code}", "$options": "i"}})
    except Exception:
        ipo_comp = None

    if ipo_comp:
        base_price = max(5000, int(ipo_comp.get("treasury", 0) / 1000))
        rep_mult = max(0.1, ipo_comp.get("reputation", 100) / 100.0)
        scandal = 0.5 if ipo_comp.get("has_scandal", False) else 1.0
        target_time = datetime.now() + timedelta(hours=hour_offset)
        rng = random.Random(int(target_time.strftime("%Y%m%d%H%M")) // 15 + sum(ord(c) for c in code))
        fluctuation = rng.uniform(0.85, 1.15)
        return max(1000, int(base_price * rep_mult * scandal * fluctuation))

    stock_info = STANDARD_STOCKS.get(code)
    if not stock_info:
        return 0

    base = stock_info["base"]
    vol = stock_info["volatility"]
    sector = stock_info["sector"]

    # Dùng seed theo ngày + mã để giá ổn định trong ngày, thay đổi từng 15 phút
    target_time = datetime.now() + timedelta(hours=hour_offset)
    seed_15min = int(target_time.strftime("%Y%m%d%H%M")) // 15
    seed = seed_15min * 1000 + sum(ord(c) for c in code)
    rng = random.Random(seed)

    # GBM simulation: log-normal price walk
    dt = 1 / 252  # 1 ngày giao dịch
    periods = seed_15min % 26  # trong 1 ngày có 26 phiên 15 phút
    
    price = base
    for i in range(periods):
        period_seed = seed - i * 100
        r = random.Random(period_seed)
        z = r.gauss(0, 1)
        # drift nhỏ + volatility random
        sector_drift = get_sector_trend(sector) / 26
        price = price * math.exp((sector_drift - 0.5 * vol**2) * dt + vol * math.sqrt(dt) * z)

    price = max(100, int(price))

    # Áp dụng tin tức thị trường nếu có
    for event in _market_events:
        if event.get("sector") in [sector, "ALL"] or event.get("code") == code:
            price = int(price * event.get("multiplier", 1.0))

    return price

def get_session_open_price(code):
    """Lấy giá mở phiên hôm nay"""
    if code not in _session_open_prices:
        # Lấy giá đầu ngày (offset về đầu ngày)
        today_seed = int(datetime.now().strftime("%Y%m%d")) * 1000 + sum(ord(c) for c in code)
        rng = random.Random(today_seed)
        stock_info = STANDARD_STOCKS.get(code)
        if stock_info:
            _session_open_prices[code] = max(100, int(stock_info["base"] * rng.uniform(0.95, 1.05)))
        else:
            _session_open_prices[code] = get_stock_price(code)
    return _session_open_prices[code]

def check_circuit_breaker(code):
    """Kiểm tra có kích hoạt cầu dao tự động không"""
    current = get_stock_price(code)
    open_price = get_session_open_price(code)
    if open_price == 0:
        return False
    change_pct = abs(current - open_price) / open_price
    return change_pct >= CIRCUIT_BREAKER

def get_stock_buy_price(code):
    """Giá mua = giá thị trường + spread"""
    return int(get_stock_price(code) * (1 + STOCK_SPREAD))

def get_stock_sell_price(code):
    """Giá bán = giá thị trường - spread - thuế"""
    market = get_stock_price(code)
    after_spread = int(market * (1 - STOCK_SPREAD))
    tax = int(after_spread * STOCK_TAX_RATE)
    return after_spread - tax

def get_price_change_pct(code):
    """Phần trăm thay đổi giá so với 1 giờ trước"""
    current = get_stock_price(code)
    prev = get_stock_price(code, hour_offset=-1)
    if prev == 0: return 0.0
    return (current - prev) / prev * 100

def get_next_15min_timestamp():
    now = datetime.now()
    next_update = now + timedelta(minutes=15 - (now.minute % 15))
    next_update = next_update.replace(second=0, microsecond=0)
    return int(next_update.timestamp())

def get_all_stocks():
    all_stocks = {}
    for code, info in STANDARD_STOCKS.items():
        all_stocks[code] = info["name"]
    try:
        ipo_companies = companies_col.find({"is_ipo": True})
        for comp in ipo_companies:
            code = comp["name"][:4].upper()
            all_stocks[code] = comp["name"]
    except Exception as e:
        print(f"[WARN] get_all_stocks error: {e}")
    return all_stocks

async def check_stop_loss_take_profit(user_id, channel):
    """Kiểm tra và thực thi lệnh stop-loss / take-profit tự động"""
    user_data = load_user(user_id)
    sold_msg = []

    for code, qty in dict(user_data.get("stocks", {})).items():
        if qty <= 0:
            continue
        current_price = get_stock_sell_price(code)

        # Stop-loss
        sl_price = user_data.get("stop_loss", {}).get(code, 0)
        if sl_price and current_price <= sl_price:
            gain = current_price * qty
            user_data["money"] += gain
            del user_data["stocks"][code]
            user_data["stop_loss"].pop(code, None)
            user_data["stock_buy_prices"].pop(code, None)
            add_history(user_id, f"[SL] Bán {qty} {code} @ {current_price:,} (+{gain:,})")
            sold_msg.append(f"🛑 **STOP-LOSS {code}**: Bán {qty} CP @ {current_price:,} (tổng {gain:,} 💰)")

        # Take-profit
        tp_price = user_data.get("take_profit", {}).get(code, 0)
        if tp_price and current_price >= tp_price:
            gain = current_price * qty
            user_data["money"] += gain
            del user_data["stocks"][code]
            user_data["take_profit"].pop(code, None)
            user_data["stock_buy_prices"].pop(code, None)
            add_history(user_id, f"[TP] Bán {qty} {code} @ {current_price:,} (+{gain:,})")
            sold_msg.append(f"✅ **TAKE-PROFIT {code}**: Bán {qty} CP @ {current_price:,} (tổng {gain:,} 💰)")

    # Kiểm tra margin call
    margin = user_data.get("margin_used", 0)
    if margin > 0:
        total_stock_value = sum(get_stock_sell_price(c) * q for c, q in user_data.get("stocks", {}).items())
        total_assets = user_data.get("money", 0) + user_data.get("bank", 0) + total_stock_value
        # Margin call nếu tài sản < 130% tiền vay
        if total_assets < margin * 1.3 and total_assets > 0:
            # Bán cổ phiếu tự động để trả ký quỹ
            for code in list(user_data.get("stocks", {}).keys()):
                if user_data.get("margin_used", 0) <= 0:
                    break
                qty = user_data["stocks"].get(code, 0)
                sp = get_stock_sell_price(code)
                proceeds = sp * qty
                user_data["money"] += proceeds
                user_data["margin_used"] = max(0, user_data.get("margin_used", 0) - proceeds)
                del user_data["stocks"][code]
                sold_msg.append(f"🚨 **MARGIN CALL {code}**: Tự động bán {qty} CP @ {sp:,}")
                add_history(user_id, f"[MARGIN CALL] Bán {qty} {code}")

    if sold_msg:
        save_user(user_id)
        try:
            embed = discord.Embed(
                title="🤖 TỰ ĐỘNG KHỚP LỆNH",
                description="\n".join(sold_msg),
                color=discord.Color.orange()
            )
            await channel.send(f"<@{user_id}>", embed=embed)
        except Exception:
            pass

# =====================================================================
# CÁC LỆNH CHỨNG KHOÁN MỚI
# =====================================================================

@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    all_stocks = get_all_stocks()
    embed = discord.Embed(
        title="📈 SÀN GIAO DỊCH CHỨNG KHOÁN",
        description=(
            f"⏱️ Cập nhật mỗi **15 phút** | Tiếp theo: <t:{get_next_15min_timestamp()}:R>\n"
            f"💸 Phí: Spread **0.1%** + Thuế bán **0.1%** (thực tế VN)\n"
            f"⚡ Cầu dao: Tạm ngừng nếu giá biến động >7%/phiên\n"
            f"📊 Cooldown: **2 phút** mỗi lệnh\n\n"
            f"**LỆNH:**\n"
            f"🛒 Mua: `k ck buy <MÃ> <SL>`\n"
            f"💸 Bán: `k ck sell <MÃ> <SL/all>`\n"
            f"📋 Lệnh giá: `k ck order <MÃ> buy/sell <SL> <GIÁ>`\n"
            f"🔍 Lịch sử: `k ck chart <MÃ>`\n"
            f"📊 Portfolio: `k ck port`\n"
            f"🛑 Stop-Loss: `k ck sl <MÃ> <GIÁ>`\n"
            f"✅ Take-Profit: `k ck tp <MÃ> <GIÁ>`\n"
            f"💳 Mua ký quỹ: `k ck margin <MÃ> <SL>`\n"
            f"📉 Bán khống: `k ck short <MÃ> <SL>`\n"
            f"🏢 IPO: `k ck ipo`"
        ),
        color=discord.Color.blue()
    )

    for code, name in list(all_stocks.items())[:8]:
        current = get_stock_price(code)
        prev = get_stock_price(code, hour_offset=-1)
        change_pct = (current - prev) / prev * 100 if prev > 0 else 0
        circuit = "🔴DỪNG" if check_circuit_breaker(code) else ""
        trend = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
        buy_p = get_stock_buy_price(code)
        sell_p = get_stock_sell_price(code)
        vol = STANDARD_STOCKS.get(code, {}).get("volatility", 0.05)
        embed.add_field(
            name=f"{trend} {code} {circuit}",
            value=f"Giá: **{current:,}** | Mua: {buy_p:,} | Bán: {sell_p:,}\n"
                  f"Thay đổi: **{change_pct:+.2f}%** | Biến động: {vol*100:.1f}%",
            inline=True
        )

    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    """Mua cổ phiếu theo giá thị trường"""
    user_id = str(ctx.author.id)

    if not acquire_lock(user_id):
        return await ctx.reply(embed=discord.Embed(description="⚠️ Đang xử lý lệnh trước!", color=discord.Color.orange()), mention_author=False)

    try:
        now = datetime.now()
        if user_id in stock_cooldowns:
            diff = (now - stock_cooldowns[user_id]).total_seconds()
            if diff < 600:
                return await ctx.reply(embed=discord.Embed(
                    description=f"⏳ Cooldown: còn **{int((600-diff)//60)}p {int((600-diff)%60)}s**",
                    color=discord.Color.orange()
                ), mention_author=False)

        code = code.upper()
        all_stocks = get_all_stocks()
        if code not in all_stocks:
            return await ctx.reply("⚠️ Mã CK không tồn tại!")

        if qty <= 0 or qty > 10000:
            return await ctx.reply("⚠️ Số lượng từ 1-10,000 CP!")

        # Kiểm tra cầu dao
        if check_circuit_breaker(code):
            return await ctx.reply(embed=discord.Embed(
                description=f"🔴 **CẦU DAO TỰ ĐỘNG!** Mã {code} tạm ngừng giao dịch do biến động >7%!",
                color=discord.Color.red()
            ), mention_author=False)

        buy_price = get_stock_buy_price(code)
        market_price = get_stock_price(code)
        if market_price <= 100:
            return await ctx.reply("⚠️ Mã CP giá quá thấp, không cho mua!")

        total_cost = buy_price * qty
        user_data = load_user(user_id)

        if user_data.get("money", 0) < total_cost:
            return await ctx.reply(embed=discord.Embed(
                description=f"⚠️ Thiếu tiền! Cần **{total_cost:,} 💰** (Giá mua: {buy_price:,}/CP × {qty} CP)",
                color=discord.Color.red()
            ), mention_author=False)

        user_data["money"] -= total_cost

        # Tính giá mua trung bình (average cost)
        old_qty = user_data["stocks"].get(code, 0)
        old_avg = user_data.get("stock_buy_prices", {}).get(code, buy_price)
        new_qty = old_qty + qty
        new_avg = int((old_qty * old_avg + qty * buy_price) / new_qty)

        if "stocks" not in user_data: user_data["stocks"] = {}
        if "stock_buy_prices" not in user_data: user_data["stock_buy_prices"] = {}
        user_data["stocks"][code] = new_qty
        user_data["stock_buy_prices"][code] = new_avg

        stock_cooldowns[user_id] = now
        save_user(user_id)
        add_history(user_id, f"Mua {qty} {code} @ {buy_price:,} (-{total_cost:,})")

        embed = discord.Embed(title="✅ LỆNH MUA KHỚP", color=discord.Color.green())
        embed.add_field(name="Mã CK", value=f"**{code}**", inline=True)
        embed.add_field(name="Số lượng", value=f"**{qty:,} CP**", inline=True)
        embed.add_field(name="Giá mua", value=f"**{buy_price:,} 💰/CP**", inline=True)
        embed.add_field(name="Tổng chi", value=f"**{total_cost:,} 💰**", inline=True)
        embed.add_field(name="Giá TB mới", value=f"**{new_avg:,} 💰/CP**", inline=True)
        embed.add_field(name="Số dư ví", value=f"**{user_data['money']:,} 💰**", inline=True)
        embed.set_footer(text="⏳ Cooldown 2 phút | Dùng 'k ck sl' để đặt cắt lỗ")
        await ctx.reply(embed=embed, mention_author=False)
    finally:
        release_lock(user_id)


@chungkhoan.command()
async def sell(ctx, code: str, qty_str: str):
    """Bán cổ phiếu theo giá thị trường"""
    user_id = str(ctx.author.id)

    if not acquire_lock(user_id):
        return await ctx.reply(embed=discord.Embed(description="⚠️ Đang xử lý!", color=discord.Color.orange()), mention_author=False)

    try:
        now = datetime.now()
        if user_id in stock_cooldowns:
            diff = (now - stock_cooldowns[user_id]).total_seconds()
            if diff < 120:
                return await ctx.reply(embed=discord.Embed(
                    description=f"⏳ Cooldown: còn **{int((120-diff)//60)}p {int((120-diff)%60)}s**",
                    color=discord.Color.orange()
                ), mention_author=False)

        code = code.upper()
        user_data = load_user(user_id)
        owned = user_data.get("stocks", {}).get(code, 0)

        if qty_str.lower() == "all":
            qty = owned
        else:
            try: qty = int(qty_str)
            except ValueError: return await ctx.reply("⚠️ Nhập số lượng hoặc `all`!")

        if qty <= 0:
            return await ctx.reply("⚠️ Số lượng > 0!")

        if owned < qty:
            return await ctx.reply(embed=discord.Embed(
                description=f"⚠️ Bạn chỉ có **{owned:,} CP {code}**! Bán tối đa {owned} CP.",
                color=discord.Color.red()
            ), mention_author=False)

        # Kiểm tra cầu dao
        if check_circuit_breaker(code):
            return await ctx.reply(embed=discord.Embed(
                description=f"🔴 **CẦU DAO TỰ ĐỘNG!** Mã {code} tạm ngừng giao dịch!",
                color=discord.Color.red()
            ), mention_author=False)

        sell_price = get_stock_sell_price(code)
        market_price = get_stock_price(code)
        total_gain = sell_price * qty
        tax = int(market_price * STOCK_TAX_RATE * qty)

        avg_buy = user_data.get("stock_buy_prices", {}).get(code, sell_price)
        profit = (sell_price - avg_buy) * qty
        profit_pct = ((sell_price - avg_buy) / avg_buy * 100) if avg_buy > 0 else 0

        # Cập nhật portfolio
        user_data["stocks"][code] -= qty
        if user_data["stocks"][code] <= 0:
            del user_data["stocks"][code]
            user_data.get("stock_buy_prices", {}).pop(code, None)
            user_data.get("stop_loss", {}).pop(code, None)
            user_data.get("take_profit", {}).pop(code, None)

        user_data["money"] += total_gain
        stock_cooldowns[user_id] = now
        save_user(user_id)
        add_history(user_id, f"Bán {qty} {code} @ {sell_price:,} (+{total_gain:,}, P&L {profit:+,})")

        color = discord.Color.green() if profit >= 0 else discord.Color.red()
        profit_icon = "📈" if profit >= 0 else "📉"

        embed = discord.Embed(title="✅ LỆNH BÁN KHỚP", color=color)
        embed.add_field(name="Mã CK", value=f"**{code}**", inline=True)
        embed.add_field(name="Số lượng", value=f"**{qty:,} CP**", inline=True)
        embed.add_field(name="Giá bán", value=f"**{sell_price:,} 💰/CP**", inline=True)
        embed.add_field(name="Thu về", value=f"**{total_gain:,} 💰**", inline=True)
        embed.add_field(name="Thuế", value=f"**{tax:,} 💰** (0.1%)", inline=True)
        embed.add_field(name=f"{profit_icon} P&L", value=f"**{profit:+,} 💰** ({profit_pct:+.2f}%)", inline=True)
        embed.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰")
        await ctx.reply(embed=embed, mention_author=False)
    finally:
        release_lock(user_id)


@chungkhoan.command()
async def order(ctx, code: str, side: str, qty: int, price: int):
    """Đặt lệnh giá - chờ thị trường về mức giá mong muốn mới khớp"""
    user_id = str(ctx.author.id)
    code = code.upper()
    side = side.lower()

    if side not in ["buy", "sell", "mua", "ban", "bán"]:
        return await ctx.reply("⚠️ Dùng: `k ck order <MÃ> buy/sell <SL> <GIÁ>`")

    if code not in get_all_stocks():
        return await ctx.reply("⚠️ Mã không tồn tại!")
    if qty <= 0 or qty > 10000:
        return await ctx.reply("⚠️ SL 1-10000!")
    if price <= 0:
        return await ctx.reply("⚠️ Giá > 0!")

    is_buy = side in ["buy", "mua"]
    user_data = load_user(user_id)

    if is_buy:
        total = price * qty
        if user_data["money"] < total:
            return await ctx.reply(f"⚠️ Cần **{total:,} 💰** để đặt lệnh mua!")
        # Phong tỏa tiền
        user_data["money"] -= total
    else:
        owned = user_data["stocks"].get(code, 0)
        if owned < qty:
            return await ctx.reply(f"⚠️ Chỉ có {owned} CP, không đủ để đặt bán {qty} CP!")

    # Lưu lệnh chờ
    pending_order = {
        "user_id": user_id,
        "code": code,
        "side": "buy" if is_buy else "sell",
        "qty": qty,
        "price": price,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending"
    }
    if "stock_orders" not in user_data: user_data["stock_orders"] = []
    order_id = len(user_data["stock_orders"])
    pending_order["id"] = order_id
    user_data["stock_orders"].append(pending_order)
    save_user(user_id)

    side_name = "MUA" if is_buy else "BÁN"
    current = get_stock_price(code)
    embed = discord.Embed(
        title=f"📋 ĐẶT LỆNH {side_name} THÀNH CÔNG",
        description=(
            f"Mã: **{code}** | SL: **{qty:,} CP** | Giá đặt: **{price:,}**\n"
            f"Giá thị trường hiện tại: **{current:,}**\n\n"
            f"⏳ Lệnh sẽ tự động khớp khi giá {'≤' if is_buy else '≥'} **{price:,}**\n"
            f"📋 Xem lệnh chờ: `k ck orders` | Hủy: `k ck cancel {order_id}`"
        ),
        color=discord.Color.blue()
    )
    if is_buy:
        embed.set_footer(text=f"Đã phong tỏa {price*qty:,} 💰 từ ví")
    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command(name="orders")
async def list_orders(ctx):
    """Xem danh sách lệnh chờ"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    orders = [o for o in user_data.get("stock_orders", []) if o.get("status") == "pending"]

    if not orders:
        return await ctx.reply(embed=discord.Embed(description="📋 Không có lệnh chờ nào.", color=discord.Color.blue()), mention_author=False)

    embed = discord.Embed(title="📋 LỆNH CHỜ KHỚP", color=discord.Color.blue())
    for o in orders:
        current = get_stock_price(o["code"])
        diff = current - o["price"]
        side_emoji = "🟢" if o["side"] == "buy" else "🔴"
        embed.add_field(
            name=f"#{o['id']} {side_emoji} {o['side'].upper()} {o['code']}",
            value=f"SL: {o['qty']:,} CP | Giá đặt: **{o['price']:,}** | Hiện tại: **{current:,}** (cách {diff:+,})\n"
                  f"Đặt lúc: {o['created']}",
            inline=False
        )
    embed.set_footer(text="Hủy lệnh: k ck cancel <ID>")
    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command()
async def cancel(ctx, order_id: int):
    """Hủy lệnh chờ"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    orders = user_data.get("stock_orders", [])

    target = next((o for o in orders if o.get("id") == order_id and o.get("status") == "pending"), None)
    if not target:
        return await ctx.reply("⚠️ Không tìm thấy lệnh này!")

    target["status"] = "cancelled"
    # Hoàn tiền nếu là lệnh mua
    if target["side"] == "buy":
        refund = target["price"] * target["qty"]
        user_data["money"] += refund
        await ctx.reply(embed=discord.Embed(description=f"✅ Đã hủy lệnh #{order_id}. Hoàn lại **{refund:,} 💰**", color=discord.Color.green()), mention_author=False)
    else:
        await ctx.reply(embed=discord.Embed(description=f"✅ Đã hủy lệnh bán #{order_id}.", color=discord.Color.green()), mention_author=False)

    save_user(user_id)


@chungkhoan.command()
async def sl(ctx, code: str, price: int):
    """Đặt lệnh Stop-Loss (cắt lỗ tự động)"""
    user_id = str(ctx.author.id)
    code = code.upper()
    user_data = load_user(user_id)

    if code not in user_data.get("stocks", {}):
        return await ctx.reply(f"⚠️ Bạn chưa có cổ phiếu {code}!")

    current = get_stock_price(code)
    if price >= current:
        return await ctx.reply(f"⚠️ Giá SL ({price:,}) phải **thấp hơn** giá hiện tại ({current:,})!")

    if "stop_loss" not in user_data: user_data["stop_loss"] = {}
    user_data["stop_loss"][code] = price
    save_user(user_id)

    avg_buy = user_data.get("stock_buy_prices", {}).get(code, current)
    loss_pct = (price - avg_buy) / avg_buy * 100

    embed = discord.Embed(
        title="🛑 ĐẶT STOP-LOSS THÀNH CÔNG",
        description=f"Mã: **{code}** | Giá SL: **{price:,}**\n"
                    f"Nếu giá xuống **≤ {price:,}**, hệ thống tự bán tất cả!\n"
                    f"Giá mua TB: {avg_buy:,} | Lỗ tối đa: **{loss_pct:.1f}%**",
        color=discord.Color.red()
    )
    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command()
async def tp(ctx, code: str, price: int):
    """Đặt lệnh Take-Profit (chốt lời tự động)"""
    user_id = str(ctx.author.id)
    code = code.upper()
    user_data = load_user(user_id)

    if code not in user_data.get("stocks", {}):
        return await ctx.reply(f"⚠️ Bạn chưa có cổ phiếu {code}!")

    current = get_stock_price(code)
    if price <= current:
        return await ctx.reply(f"⚠️ Giá TP ({price:,}) phải **cao hơn** giá hiện tại ({current:,})!")

    if "take_profit" not in user_data: user_data["take_profit"] = {}
    user_data["take_profit"][code] = price
    save_user(user_id)

    avg_buy = user_data.get("stock_buy_prices", {}).get(code, current)
    profit_pct = (price - avg_buy) / avg_buy * 100

    embed = discord.Embed(
        title="✅ ĐẶT TAKE-PROFIT THÀNH CÔNG",
        description=f"Mã: **{code}** | Giá TP: **{price:,}**\n"
                    f"Khi giá lên **≥ {price:,}**, hệ thống tự bán để chốt lời!\n"
                    f"Giá mua TB: {avg_buy:,} | Lợi nhuận mục tiêu: **+{profit_pct:.1f}%**",
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command()
async def margin(ctx, code: str, qty: int):
    """Mua ký quỹ - dùng đòn bẩy tài chính (tối đa 2x vốn tự có)"""
    user_id = str(ctx.author.id)

    if not acquire_lock(user_id):
        return await ctx.reply("⚠️ Đang xử lý!", mention_author=False)

    try:
        code = code.upper()
        if code not in get_all_stocks():
            return await ctx.reply("⚠️ Mã không tồn tại!")
        if qty <= 0:
            return await ctx.reply("⚠️ SL > 0!")

        user_data = load_user(user_id)
        buy_price = get_stock_buy_price(code)
        total_cost = buy_price * qty

        # Tính tài sản hiện tại (không gồm tiền vay)
        own_cash = user_data.get("money", 0)
        current_margin = user_data.get("margin_used", 0)
        stock_value = sum(get_stock_sell_price(c) * q for c, q in user_data.get("stocks", {}).items())
        total_own_assets = own_cash + user_data.get("bank", 0) + stock_value

        # Kiểm tra hạn mức ký quỹ
        max_borrow = total_own_assets * MAX_MARGIN_RATIO - current_margin
        if max_borrow <= 0:
            return await ctx.reply(embed=discord.Embed(
                description=f"⚠️ Bạn đã vay tới hạn mức!\nHạn mức tối đa: {total_own_assets * MAX_MARGIN_RATIO:,.0f} 💰",
                color=discord.Color.red()
            ), mention_author=False)

        # Tính tiền cần vay
        cash_needed = max(0, total_cost - own_cash)
        if cash_needed > max_borrow:
            return await ctx.reply(embed=discord.Embed(
                description=f"⚠️ Vượt hạn mức ký quỹ!\nCó thể vay thêm: {max_borrow:,.0f} 💰\nCần vay: {cash_needed:,.0f} 💰",
                color=discord.Color.red()
            ), mention_author=False)

        # Thực hiện mua
        paid_cash = min(own_cash, total_cost)
        user_data["money"] -= paid_cash
        if cash_needed > 0:
            user_data["margin_used"] = current_margin + cash_needed

        old_qty = user_data["stocks"].get(code, 0)
        old_avg = user_data.get("stock_buy_prices", {}).get(code, buy_price)
        new_qty = old_qty + qty
        new_avg = int((old_qty * old_avg + qty * buy_price) / new_qty)

        if "stocks" not in user_data: user_data["stocks"] = {}
        if "stock_buy_prices" not in user_data: user_data["stock_buy_prices"] = {}
        user_data["stocks"][code] = new_qty
        user_data["stock_buy_prices"][code] = new_avg

        daily_interest = int(cash_needed * MARGIN_INTEREST_RATE / 365)
        save_user(user_id)
        add_history(user_id, f"[MARGIN] Mua {qty} {code} @ {buy_price:,} (vay {cash_needed:,})")

        embed = discord.Embed(title="💳 MUA KÝ QUỸ THÀNH CÔNG", color=discord.Color.gold())
        embed.add_field(name="Mã CK", value=code, inline=True)
        embed.add_field(name="SL mua", value=f"{qty:,} CP", inline=True)
        embed.add_field(name="Giá mua", value=f"{buy_price:,}", inline=True)
        embed.add_field(name="Tự bỏ", value=f"{paid_cash:,} 💰", inline=True)
        embed.add_field(name="Vay ký quỹ", value=f"{cash_needed:,} 💰", inline=True)
        embed.add_field(name="Lãi vay/ngày", value=f"~{daily_interest:,} 💰", inline=True)
        embed.add_field(name="Tổng nợ ký quỹ", value=f"{user_data['margin_used']:,} 💰", inline=False)
        embed.set_footer(text=f"⚠️ MARGIN CALL nếu tài sản < 130% nợ! Lãi suất {MARGIN_INTEREST_RATE*100}%/năm")
        await ctx.reply(embed=embed, mention_author=False)
    finally:
        release_lock(user_id)


@chungkhoan.command()
async def short(ctx, code: str, qty: int):
    """Bán khống - kiếm tiền khi giá xuống"""
    user_id = str(ctx.author.id)

    if not acquire_lock(user_id):
        return await ctx.reply("⚠️ Đang xử lý!", mention_author=False)

    try:
        code = code.upper()
        if code not in STANDARD_STOCKS:
            return await ctx.reply("⚠️ Chỉ bán khống cổ phiếu tiêu chuẩn!")
        if qty <= 0 or qty > 1000:
            return await ctx.reply("⚠️ SL 1-1000 CP!")

        user_data = load_user(user_id)
        market_price = get_stock_price(code)
        total_collateral = market_price * qty  # Ký quỹ bằng 100% giá trị

        if user_data.get("money", 0) < total_collateral:
            return await ctx.reply(embed=discord.Embed(
                description=f"⚠️ Cần **{total_collateral:,} 💰** ký quỹ bán khống!",
                color=discord.Color.red()
            ), mention_author=False)

        user_data["money"] -= total_collateral  # Phong tỏa ký quỹ
        if "short_positions" not in user_data: user_data["short_positions"] = {}
        if "short_buy_prices" not in user_data: user_data["short_buy_prices"] = {}

        existing = user_data["short_positions"].get(code, 0)
        user_data["short_positions"][code] = existing + qty
        user_data["short_buy_prices"][code] = market_price  # Giá bán khống ban đầu

        save_user(user_id)
        add_history(user_id, f"[SHORT] Mở {qty} {code} @ {market_price:,}")

        embed = discord.Embed(
            title="📉 MỞ VỊ THẾ BÁN KHỐNG",
            description=(
                f"Mã: **{code}** | SL: **{qty:,} CP**\n"
                f"Giá bán khống: **{market_price:,}**\n"
                f"Ký quỹ phong tỏa: **{total_collateral:,} 💰**\n\n"
                f"💡 Bạn lãi khi giá **xuống**, lỗ khi giá **lên**!\n"
                f"Đóng short: `k ck covershort {code} {qty}`"
            ),
            color=discord.Color.dark_red()
        )
        await ctx.reply(embed=embed, mention_author=False)
    finally:
        release_lock(user_id)


@chungkhoan.command()
async def covershort(ctx, code: str, qty: int):
    """Đóng vị thế bán khống"""
    user_id = str(ctx.author.id)

    if not acquire_lock(user_id):
        return await ctx.reply("⚠️ Đang xử lý!", mention_author=False)

    try:
        code = code.upper()
        user_data = load_user(user_id)
        short_qty = user_data.get("short_positions", {}).get(code, 0)

        if short_qty <= 0:
            return await ctx.reply(f"⚠️ Không có vị thế bán khống {code}!")
        if qty > short_qty:
            return await ctx.reply(f"⚠️ Chỉ có {short_qty} CP bán khống!")

        short_price = user_data.get("short_buy_prices", {}).get(code, 0)
        current_price = get_stock_price(code)

        # Lãi/lỗ: short lãi khi giá xuống
        profit_per_share = short_price - current_price
        total_profit = profit_per_share * qty
        collateral_return = short_price * qty  # Hoàn ký quỹ gốc

        user_data["money"] += collateral_return + total_profit
        user_data["short_positions"][code] -= qty
        if user_data["short_positions"][code] <= 0:
            del user_data["short_positions"][code]
            user_data.get("short_buy_prices", {}).pop(code, None)

        save_user(user_id)
        add_history(user_id, f"[COVER SHORT] Đóng {qty} {code} P&L {total_profit:+,}")

        color = discord.Color.green() if total_profit >= 0 else discord.Color.red()
        profit_icon = "📈" if total_profit >= 0 else "📉"

        embed = discord.Embed(title="✅ ĐÓNG BÁN KHỐNG", color=color)
        embed.add_field(name="Mã", value=code, inline=True)
        embed.add_field(name="SL đóng", value=f"{qty:,} CP", inline=True)
        embed.add_field(name="Giá bán khống", value=f"{short_price:,}", inline=True)
        embed.add_field(name="Giá mua lại", value=f"{current_price:,}", inline=True)
        embed.add_field(name=f"{profit_icon} P&L", value=f"**{total_profit:+,} 💰**", inline=True)
        embed.add_field(name="Hoàn ký quỹ", value=f"{collateral_return:,} 💰", inline=True)
        await ctx.reply(embed=embed, mention_author=False)
    finally:
        release_lock(user_id)


@chungkhoan.command()
async def port(ctx, member: discord.Member = None):
    """Xem portfolio đầu tư"""
    target = member or ctx.author
    user_data = load_user(target.id)

    stocks = user_data.get("stocks", {})
    shorts = user_data.get("short_positions", {})
    margin = user_data.get("margin_used", 0)
    sl_prices = user_data.get("stop_loss", {})
    tp_prices = user_data.get("take_profit", {})

    embed = discord.Embed(title=f"📊 PORTFOLIO - {target.name}", color=discord.Color.blue())

    total_long_value = 0
    if stocks:
        long_lines = []
        for code, qty in stocks.items():
            if qty <= 0: continue
            curr = get_stock_price(code)
            sell_p = get_stock_sell_price(code)
            avg_buy = user_data.get("stock_buy_prices", {}).get(code, curr)
            val = sell_p * qty
            pnl = (sell_p - avg_buy) * qty
            pnl_pct = (sell_p - avg_buy) / avg_buy * 100 if avg_buy > 0 else 0
            total_long_value += val
            sl_str = f" | SL:{sl_prices[code]:,}" if code in sl_prices else ""
            tp_str = f" | TP:{tp_prices[code]:,}" if code in tp_prices else ""
            icon = "📈" if pnl >= 0 else "📉"
            long_lines.append(
                f"{icon} **{code}** {qty:,}CP @ avg {avg_buy:,}\n"
                f"    Giá hiện tại: {curr:,} | Giá trị: {val:,} | P&L: **{pnl:+,}** ({pnl_pct:+.1f}%){sl_str}{tp_str}"
            )
        embed.add_field(name=f"📦 CỔ PHIẾU NẮNG GIỮ (Tổng: {total_long_value:,} 💰)", value="\n".join(long_lines) or "Trống", inline=False)

    if shorts:
        short_lines = []
        total_short_pnl = 0
        for code, qty in shorts.items():
            curr = get_stock_price(code)
            entry = user_data.get("short_buy_prices", {}).get(code, curr)
            pnl = (entry - curr) * qty
            total_short_pnl += pnl
            icon = "📈" if pnl >= 0 else "📉"
            short_lines.append(f"{icon} **{code}** SHORT {qty:,}CP | Entry: {entry:,} | Hiện: {curr:,} | P&L: **{pnl:+,}**")
        embed.add_field(name=f"📉 VỊ THẾ BÁN KHỐNG", value="\n".join(short_lines), inline=False)

    if margin > 0:
        daily_int = int(margin * MARGIN_INTEREST_RATE / 365)
        embed.add_field(name="💳 KÝ QUỸ", value=f"Nợ: **{margin:,} 💰** | Lãi/ngày: **~{daily_int:,} 💰**", inline=False)

    cash = user_data.get("money", 0)
    bank = user_data.get("bank", 0)
    net_assets = cash + bank + total_long_value - margin
    embed.add_field(name="💰 TỔNG TÀI SẢN RÒNG", value=f"Tiền mặt: {cash:,} | Ngân hàng: {bank:,}\nCổ phiếu: {total_long_value:,} | Nợ ký quỹ: -{margin:,}\n**= {net_assets:,} 💰**", inline=False)

    pending = [o for o in user_data.get("stock_orders", []) if o.get("status") == "pending"]
    if pending:
        embed.add_field(name=f"📋 LỆNH CHỜ ({len(pending)})", value="`k ck orders` để xem chi tiết", inline=False)

    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command()
async def chart(ctx, code: str):
    """Xem biểu đồ giá 6 giờ qua"""
    code = code.upper()
    if code not in get_all_stocks():
        return await ctx.reply("⚠️ Mã không tồn tại!")

    prices = []
    for h in range(-5, 1):
        p = get_stock_price(code, hour_offset=h)
        prices.append(p)

    min_p = min(prices)
    max_p = max(prices)
    price_range = max_p - min_p if max_p != min_p else 1

    chart_height = 6
    chart_lines = []
    for row in range(chart_height, -1, -1):
        threshold = min_p + (price_range * row / chart_height)
        line = ""
        for p in prices:
            if p >= threshold:
                line += "█"
            else:
                line += "░"
        price_label = f"{threshold:,.0f}"
        chart_lines.append(f"`{price_label:>10}` {line}")

    hours_ago = ["6h", "5h", "4h", "3h", "2h", "1h", "Now"]
    price_row = " | ".join([f"{p:,}" for p in prices])

    change = prices[-1] - prices[0]
    change_pct = change / prices[0] * 100 if prices[0] > 0 else 0
    color = discord.Color.green() if change >= 0 else discord.Color.red()

    embed = discord.Embed(title=f"📊 BIỂU ĐỒ GIÁ {code}", color=color)
    embed.add_field(name="Biểu đồ (6h)", value="```\n" + "\n".join(chart_lines) + "\n```", inline=False)
    embed.add_field(name="Giá các mốc", value=f"`{price_row}`", inline=False)
    embed.add_field(name="Thay đổi 6h", value=f"**{change:+,}** ({change_pct:+.2f}%)", inline=True)
    embed.add_field(name="Hiện tại", value=f"**{prices[-1]:,}**", inline=True)
    stock_info = STANDARD_STOCKS.get(code, {})
    embed.add_field(name="Biến động", value=f"**{stock_info.get('volatility', 0)*100:.1f}%**", inline=True)
    await ctx.reply(embed=embed, mention_author=False)


@chungkhoan.command()
async def ipo(ctx):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn chưa có công ty!", color=discord.Color.red()), mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("⚠️ Chỉ Chủ Tịch mới được IPO!", mention_author=False)
    if comp.get("is_ipo"): return await ctx.reply("⚠️ Đã niêm yết rồi!", mention_author=False)
    if comp["treasury"] < 50000000: return await ctx.reply("⚠️ Quỹ tối thiểu **50,000,000 💰** để IPO.", mention_author=False)
    comp["is_ipo"] = True
    save_company(comp_id)
    code = comp["name"][:4].upper()
    await ctx.reply(embed=discord.Embed(title="📈 CHÀO SÀN THÀNH CÔNG", description=f"**{comp['name']}** đã IPO!\nMã: **{code}** | Spread 0.1% | Thuế bán 0.1%", color=discord.Color.green()), mention_author=False)


# =====================================================================
# BACKGROUND TASK: Tự động khớp lệnh giá
# =====================================================================


async def process_pending_orders():
    """Tự động khớp lệnh giá mỗi 2 phút"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            all_users = list(users_col.find({"stock_orders": {"$elemMatch": {"status": "pending"}}}))
            for doc in all_users:
                user_id = doc["_id"]
                if user_id not in DB_CACHE:
                    DB_CACHE[user_id] = doc
                user_data = DB_CACHE[user_id]
                changed = False

                for order in user_data.get("stock_orders", []):
                    if order.get("status") != "pending":
                        continue
                    code = order["code"]
                    current_price = get_stock_price(code)
                    is_buy = order["side"] == "buy"

                    should_fill = (is_buy and current_price <= order["price"]) or \
                                  (not is_buy and current_price >= order["price"])

                    if should_fill:
                        order["status"] = "filled"
                        changed = True
                        qty = order["qty"]

                        if is_buy:
                            # Tiền đã bị phong tỏa, chỉ cần nhận CP
                            old_qty = user_data["stocks"].get(code, 0)
                            old_avg = user_data.get("stock_buy_prices", {}).get(code, order["price"])
                            new_qty = old_qty + qty
                            new_avg = int((old_qty * old_avg + qty * order["price"]) / new_qty)
                            if "stocks" not in user_data: user_data["stocks"] = {}
                            if "stock_buy_prices" not in user_data: user_data["stock_buy_prices"] = {}
                            user_data["stocks"][code] = new_qty
                            user_data["stock_buy_prices"][code] = new_avg
                            add_history(user_id, f"[LỆNH GIÁ] Mua {qty} {code} @ {order['price']:,}")
                        else:
                            owned = user_data.get("stocks", {}).get(code, 0)
                            sell_qty = min(qty, owned)
                            if sell_qty > 0:
                                gain = order["price"] * sell_qty
                                tax = int(gain * STOCK_TAX_RATE)
                                user_data["money"] = user_data.get("money", 0) + gain - tax
                                user_data["stocks"][code] -= sell_qty
                                if user_data["stocks"][code] <= 0:
                                    del user_data["stocks"][code]
                                    user_data.get("stock_buy_prices", {}).pop(code, None)
                                add_history(user_id, f"[LỆNH GIÁ] Bán {sell_qty} {code} @ {order['price']:,}")

                if changed:
                    save_user(user_id)
        except Exception as e:
            print(f"[WARN] process_pending_orders error: {e}")

        await asyncio.sleep(120)  # Mỗi 2 phút


async def process_margin_interest():
    """Tính lãi vay ký quỹ hàng ngày"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now()
            all_users = list(users_col.find({"margin_used": {"$gt": 0}}))
            for doc in all_users:
                user_id = doc["_id"]
                if user_id not in DB_CACHE: DB_CACHE[user_id] = doc
                user_data = DB_CACHE[user_id]
                margin = user_data.get("margin_used", 0)
                if margin <= 0: continue

                last_str = user_data.get("margin_interest_date", "2000-01-01 00:00:00")
                try: last = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
                except Exception: last = datetime(2000, 1, 1)

                if now - last >= timedelta(days=1):
                    daily_interest = int(margin * MARGIN_INTEREST_RATE / 365)
                    # Trừ từ tiền mặt, nếu không đủ thì trừ vào bank
                    if user_data.get("money", 0) >= daily_interest:
                        user_data["money"] -= daily_interest
                    elif user_data.get("bank", 0) >= daily_interest:
                        user_data["bank"] -= daily_interest
                    else:
                        # Bị margin call
                        user_data["margin_used"] += daily_interest
                    user_data["margin_interest_date"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    save_user(user_id)
        except Exception as e:
            print(f"[WARN] margin interest error: {e}")
        await asyncio.sleep(3600)  # Mỗi giờ kiểm tra


async def auto_sl_tp_monitor():
    """Kiểm tra SL/TP mỗi 5 phút"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            # Lấy tất cả user có SL hoặc TP
            all_users = list(users_col.find({"$or": [
                {"stop_loss": {"$exists": True, "$ne": {}}},
                {"take_profit": {"$exists": True, "$ne": {}}}
            ]}))
            for doc in all_users:
                user_id = doc["_id"]
                if user_id not in DB_CACHE: DB_CACHE[user_id] = doc
                # Không có channel cụ thể ở đây, chỉ update data
                user_data = DB_CACHE[user_id]
                changed = False

                for code in list(user_data.get("stocks", {}).keys()):
                    qty = user_data["stocks"].get(code, 0)
                    if qty <= 0: continue
                    current = get_stock_sell_price(code)
                    sl = user_data.get("stop_loss", {}).get(code, 0)
                    tp = user_data.get("take_profit", {}).get(code, 0)

                    if (sl and current <= sl) or (tp and current >= tp):
                        gain = current * qty
                        user_data["money"] = user_data.get("money", 0) + gain
                        del user_data["stocks"][code]
                        user_data.get("stop_loss", {}).pop(code, None)
                        user_data.get("take_profit", {}).pop(code, None)
                        user_data.get("stock_buy_prices", {}).pop(code, None)
                        trigger = "SL" if (sl and current <= sl) else "TP"
                        add_history(user_id, f"[{trigger}] Auto-sell {qty} {code} @ {current:,} (+{gain:,})")
                        changed = True

                if changed:
                    save_user(user_id)
        except Exception as e:
            print(f"[WARN] auto_sl_tp error: {e}")
        await asyncio.sleep(300)  # Mỗi 5 phút


# =====================================================================
# MINI-GAMES MỚI
# =====================================================================

# ===== BLACKJACK =====
def card_value(card):
    if card in ['J', 'Q', 'K']: return 10
    if card == 'A': return 11
    return int(card)

def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces = hand.count('A')
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def draw_card():
    return random.choice(['A','2','3','4','5','6','7','8','9','10','J','Q','K'])

def format_hand(hand):
    return " | ".join(hand)

class BlackjackView(discord.ui.View):
    def __init__(self, player, bet, player_hand, dealer_hand, user_data):
        super().__init__(timeout=60)
        self.player = player
        self.bet = bet
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.user_data = user_data
        self.doubled = False
        self.finished = False

    def make_embed(self, reveal_dealer=False):
        ph = hand_value(self.player_hand)
        dh = hand_value(self.dealer_hand)
        d_display = format_hand(self.dealer_hand) if reveal_dealer else f"{self.dealer_hand[0]} | ?"
        embed = discord.Embed(title="🃏 BLACKJACK", color=discord.Color.dark_green())
        embed.add_field(name=f"Nhà Cái {f'({dh})' if reveal_dealer else ''}", value=d_display, inline=False)
        embed.add_field(name=f"Bạn ({ph})", value=format_hand(self.player_hand), inline=False)
        embed.add_field(name="💰 Cược", value=f"**{self.bet:,}**", inline=True)
        return embed

    async def end_game(self, interaction, result):
        self.finished = True
        self.clear_items()
        ph = hand_value(self.player_hand)
        dh = hand_value(self.dealer_hand)

        if result == "player_bj":
            win = int(self.bet * 1.5)
            self.user_data["money"] += self.bet + win
            desc = f"🃏 **BLACKJACK! Thắng {win:,} 💰!**"
            color = discord.Color.gold()
        elif result == "player_win":
            self.user_data["money"] += self.bet * 2
            desc = f"🎉 **THẮNG! Nhận {self.bet*2:,} 💰!**"
            color = discord.Color.green()
        elif result == "tie":
            self.user_data["money"] += self.bet
            desc = "🤝 **HÒA! Tiền cược hoàn lại.**"
            color = discord.Color.blue()
        else:  # lose
            desc = f"💀 **THUA! Mất {self.bet:,} 💰.**"
            color = discord.Color.red()

        save_user(str(self.player.id))
        add_history(str(self.player.id), f"Blackjack {result} ({'+' if result in ['player_bj','player_win','tie'] else '-'}{self.bet:,})")

        embed = self.make_embed(reveal_dealer=True)
        embed.color = color
        embed.add_field(name="Kết quả", value=desc, inline=False)
        embed.set_footer(text=f"Bạn: {ph} | Nhà cái: {dh} | Ví: {self.user_data['money']:,} 💰")
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🃏 Rút Bài (Hit)", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id: return await interaction.response.send_message("Không phải ván của bạn!", ephemeral=True)
        if self.finished: return

        self.player_hand.append(draw_card())
        ph = hand_value(self.player_hand)

        if ph > 21:
            await self.end_game(interaction, "lose")
        elif ph == 21:
            # Auto stand
            while hand_value(self.dealer_hand) < 17:
                self.dealer_hand.append(draw_card())
            dh = hand_value(self.dealer_hand)
            if dh > 21 or ph > dh: await self.end_game(interaction, "player_win")
            elif ph == dh: await self.end_game(interaction, "tie")
            else: await self.end_game(interaction, "lose")
        else:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="✋ Dừng (Stand)", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id: return await interaction.response.send_message("Không phải ván của bạn!", ephemeral=True)
        if self.finished: return

        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_card())
        ph = hand_value(self.player_hand)
        dh = hand_value(self.dealer_hand)

        if dh > 21 or ph > dh: await self.end_game(interaction, "player_win")
        elif ph == dh: await self.end_game(interaction, "tie")
        else: await self.end_game(interaction, "lose")

    @discord.ui.button(label="💰 Gấp Đôi (Double)", style=discord.ButtonStyle.success)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id: return await interaction.response.send_message("Không phải ván của bạn!", ephemeral=True)
        if self.finished or self.doubled: return
        if len(self.player_hand) != 2: return await interaction.response.send_message("Chỉ Double khi có đúng 2 bài!", ephemeral=True)

        if self.user_data.get("money", 0) < self.bet:
            return await interaction.response.send_message("Không đủ tiền để gấp đôi!", ephemeral=True)

        self.user_data["money"] -= self.bet
        self.bet *= 2
        self.doubled = True
        self.player_hand.append(draw_card())

        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_card())

        ph = hand_value(self.player_hand)
        dh = hand_value(self.dealer_hand)

        if ph > 21: await self.end_game(interaction, "lose")
        elif dh > 21 or ph > dh: await self.end_game(interaction, "player_win")
        elif ph == dh: await self.end_game(interaction, "tie")
        else: await self.end_game(interaction, "lose")

    async def on_timeout(self):
        if not self.finished:
            self.user_data["money"] += self.bet
            save_user(str(self.player.id))


@bot.command(aliases=['bj', '21'])
async def blackjack(ctx, amount: str):
    """Chơi Blackjack"""
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    gamble_cooldowns[user_id] = datetime.now()

    player_hand = [draw_card(), draw_card()]
    dealer_hand = [draw_card(), draw_card()]

    ph = hand_value(player_hand)
    dh = hand_value(dealer_hand)

    view = BlackjackView(ctx.author, bet, player_hand, dealer_hand, user_data)
    embed = view.make_embed()
    embed.set_footer(text="Rút bài | Dừng | Gấp đôi (chỉ khi có 2 bài)")

    msg = await ctx.reply(embed=embed, view=view, mention_author=False)

    # Kiểm tra Blackjack ngay
    if ph == 21 and dh != 21:
        await view.end_game(type('obj', (object,), {'response': type('r', (object,), {'is_done': lambda: True, 'edit_message': None})(), 'message': msg})(), "player_bj")
    elif ph == 21 and dh == 21:
        await view.end_game(type('obj', (object,), {'response': type('r', (object,), {'is_done': lambda: True, 'edit_message': None})(), 'message': msg})(), "tie")


# ===== VÒNG QUAY MAY MẮN =====
WHEEL_PRIZES = [
    {"name": "💀 Mất 20% tiền ví", "mult": -0.2, "color": "red", "weight": 10},
    {"name": "😞 Không có gì", "mult": 0, "color": "grey", "weight": 20},
    {"name": "💰 +5,000 💰", "fixed": 5000, "color": "yellow", "weight": 25},
    {"name": "💰 +15,000 💰", "fixed": 15000, "color": "yellow", "weight": 20},
    {"name": "💰 +50,000 💰", "fixed": 50000, "color": "green", "weight": 12},
    {"name": "🎁 +100,000 💰", "fixed": 100000, "color": "blue", "weight": 7},
    {"name": "⭐ +300,000 💰", "fixed": 300000, "color": "purple", "weight": 4},
    {"name": "👑 +1,000,000 💰", "fixed": 1000000, "color": "gold", "weight": 1},
    {"name": "🐾 Thú cưng ngẫu nhiên", "pet": True, "color": "orange", "weight": 1},
]


@bot.command(aliases=['spin', 'wheel'])
async def vongquay(ctx):
    """Vòng quay may mắn - free 1 lần/ngày"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()

    last_str = user_data.get("last_wheel", "2000-01-01 00:00:00")
    try: last = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)

    if now - last < timedelta(hours=20):
        next_time = int((last + timedelta(hours=20)).timestamp())
        return await ctx.reply(embed=discord.Embed(description=f"🎡 Vòng quay hồi máu vào: <t:{next_time}:R>", color=discord.Color.orange()), mention_author=False)

    user_data["last_wheel"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)

    weights = [p["weight"] for p in WHEEL_PRIZES]
    prize = random.choices(WHEEL_PRIZES, weights=weights, k=1)[0]

    msg = await ctx.reply(embed=discord.Embed(title="🎡 VÒNG QUAY MAY MẮN", description="🎰 Đang quay...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(2)

    result_text = ""
    if "fixed" in prize:
        user_data["money"] += prize["fixed"]
        result_text = f"**{prize['name']}**\nBạn nhận được **{prize['fixed']:,} 💰**!"
        save_user(user_id)
    elif "mult" in prize:
        change = int(user_data.get("money", 0) * prize["mult"])
        user_data["money"] = max(0, user_data["money"] + change)
        result_text = f"**{prize['name']}**\n{'Mất' if change < 0 else 'Nhận'} **{abs(change):,} 💰**."
        save_user(user_id)
    elif prize.get("pet"):
        rarity = random.choices(list(PET_RATES.keys()), weights=[70, 20, 7, 2.5, 0.5], k=1)[0]
        pet_name = random.choice(PET_RATES[rarity]["pool"])
        if "pets" not in user_data: user_data["pets"] = {}
        user_data["pets"][pet_name] = user_data["pets"].get(pet_name, 0) + 1
        result_text = f"**{prize['name']}**\nBạn nhận được: **{pet_name}**!"
        save_user(user_id)
    else:
        result_text = f"**{prize['name']}**\nChúc may mắn lần sau!"

    add_history(user_id, f"Vòng quay: {prize['name']}")
    embed = discord.Embed(title="🎡 KẾT QUẢ VÒNG QUAY", description=result_text, color=discord.Color.gold())
    embed.set_footer(text=f"Quay lại sau 20 giờ | Ví: {user_data.get('money', 0):,} 💰")
    await msg.edit(embed=embed)


# ===== SCRATCH CARD (VÉ CÀO) =====
@bot.command(aliases=['vecat', 'scratch'])
async def vecao(ctx, amount: str):
    """Mua vé cào may mắn"""
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not bet: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    gamble_cooldowns[user_id] = datetime.now()

    # 9 ô, mỗi ô là 1 trong các biểu tượng
    symbols = ["💎", "⭐", "🍀", "🎁", "💰", "🔔", "🌈", "🃏", "💔"]
    grid = [random.choice(symbols) for _ in range(9)]

    # Đếm ký hiệu xuất hiện nhiều nhất
    from collections import Counter
    counts = Counter(grid)
    most_common_sym, most_common_count = counts.most_common(1)[0]

    multipliers = {3: 0, 4: 0.5, 5: 1.0, 6: 2.0, 7: 5.0, 8: 10.0, 9: 50.0}
    mult = multipliers.get(most_common_count, 0)

    win = int(bet * mult)
    user_data["money"] += win
    save_user(user_id)
    add_history(user_id, f"Vé cào: {most_common_count}x{most_common_sym} (+{win:,} - {bet:,} = {win-bet:+,} 💰)")

    # Hiển thị grid
    grid_display = ""
    for i, s in enumerate(grid):
        if s == most_common_sym:
            grid_display += f"**{s}**"
        else:
            grid_display += s
        grid_display += " "
        if (i+1) % 3 == 0: grid_display += "\n"

    if win > bet:
        result = f"🎉 **TRÚNG {most_common_count}x {most_common_sym}!** Nhận **{win:,} 💰** (lãi {win-bet:+,})"
        color = discord.Color.green()
    elif win == bet:
        result = f"🤝 **Hòa vốn!** Được lại **{win:,} 💰**"
        color = discord.Color.blue()
    else:
        result = f"💀 **Mất {bet-win:,} 💰**"
        color = discord.Color.red()

    embed = discord.Embed(title="🎟️ VÉ CÀO", color=color)
    embed.add_field(name="Bảng vé", value=grid_display, inline=False)
    embed.add_field(name="Kết quả", value=result, inline=False)
    embed.set_footer(text=f"Ví: {user_data['money']:,} 💰 | Cần {most_common_count} ô giống nhau để thắng")
    await ctx.reply(embed=embed, mention_author=False)


# ===== TỰ DO TÀI CHÍNH (FIRE CALCULATOR) =====
@bot.command(aliases=['fire', 'tudo'])
async def tuido(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_data = load_user(target.id)

    cash = user_data.get("money", 0)
    bank = user_data.get("bank", 0)
    stock_value = sum(get_stock_sell_price(c) * q for c, q in user_data.get("stocks", {}).items())
    total_wealth = cash + bank + stock_value

    # FIRE số: cần tích lũy = 25x chi tiêu hàng năm (4% rule)
    monthly_expense = max(10000, total_wealth * 0.002)  # giả sử chi 0.2%/tháng
    fire_number = monthly_expense * 12 * 25
    fire_progress = min(100, total_wealth / fire_number * 100) if fire_number > 0 else 0
    years_to_fire = 0
    if total_wealth < fire_number:
        monthly_saving = total_wealth * 0.003  # giả sử tiết kiệm 0.3%/tháng
        if monthly_saving > 0:
            years_to_fire = (fire_number - total_wealth) / (monthly_saving * 12)

    embed = discord.Embed(title=f"🏖️ TỰ DO TÀI CHÍNH - {target.name}", color=discord.Color.teal())
    embed.add_field(name="💵 Tiền mặt", value=f"{cash:,}", inline=True)
    embed.add_field(name="🏦 Ngân hàng", value=f"{bank:,}", inline=True)
    embed.add_field(name="📈 Cổ phiếu", value=f"{stock_value:,}", inline=True)
    embed.add_field(name="💎 Tổng tài sản", value=f"**{total_wealth:,} 💰**", inline=False)
    embed.add_field(name="🎯 FIRE Number (25x)", value=f"**{fire_number:,.0f} 💰**", inline=True)
    embed.add_field(name="📊 Tiến độ FIRE", value=f"`{make_progress_bar(fire_progress, 100)}` **{fire_progress:.1f}%**", inline=False)
    if years_to_fire > 0:
        embed.add_field(name="⏳ Ước tính thời gian", value=f"**{years_to_fire:.1f} năm**", inline=True)
    else:
        embed.add_field(name="🎉 TRẠNG THÁI", value="**ĐÃ ĐẠT TỰ DO TÀI CHÍNH!** 🏖️", inline=True)

    assets = user_data.get("assets", [])
    pets = user_data.get("pets", {})
    embed.add_field(name="🎒 Tài sản vật chất", value=f"{len(assets)} món đồ, {len(pets)} loại thú cưng", inline=True)
    embed.add_field(name="🎣 Cá câu", value=f"{user_data.get('fish_count', 0)} con", inline=True)
    await ctx.reply(embed=embed, mention_author=False)


# ===== VAY TIỀN NGÂN HÀNG =====
@bot.command(aliases=['borrow'])
async def vay(ctx, amount: int):
    """Vay tiền ngân hàng - lãi 20%/ngày, hạn 3 ngày"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)

    if user_data.get("loan_amount", 0) > 0:
        due = user_data.get("loan_due")
        return await ctx.reply(embed=discord.Embed(
            description=f"⚠️ Bạn đang nợ **{user_data['loan_amount']:,} 💰**! Trả nợ trước: `k tranno`",
            color=discord.Color.red()
        ), mention_author=False)

    max_loan = max(50000, (user_data.get("money", 0) + user_data.get("bank", 0)) * 2)
    if amount <= 0 or amount > max_loan:
        return await ctx.reply(embed=discord.Embed(
            description=f"⚠️ Vay từ 1 đến **{max_loan:,} 💰** (2x tài sản hiện tại).",
            color=discord.Color.red()
        ), mention_author=False)

    if amount > 5000000:
        return await ctx.reply("⚠️ Tối đa vay **5,000,000 💰** mỗi lần!")

    due_date = datetime.now() + timedelta(days=3)
    total_owed = int(amount * 1.20)  # Lãi 20%
    user_data["money"] += amount
    user_data["loan_amount"] = total_owed
    user_data["loan_due"] = due_date.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    add_history(user_id, f"Vay ngân hàng {amount:,} 💰 (phải trả {total_owed:,})")

    embed = discord.Embed(title="💳 VAY TIỀN THÀNH CÔNG", color=discord.Color.green())
    embed.add_field(name="Số tiền vay", value=f"**{amount:,} 💰**", inline=True)
    embed.add_field(name="Phải trả", value=f"**{total_owed:,} 💰** (+20%)", inline=True)
    embed.add_field(name="Hạn chót", value=f"<t:{int(due_date.timestamp())}:F>", inline=False)
    embed.add_field(name="⚠️ Quá hạn", value="Giang hồ đến đòi nợ! Mất 30% tài sản!", inline=False)
    embed.set_footer(text="Trả nợ: k tranno")
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(aliases=['repaydeb'])
async def tranno(ctx):
    """Trả nợ ngân hàng"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    loan = user_data.get("loan_amount", 0)

    if loan <= 0:
        return await ctx.reply(embed=discord.Embed(description="✅ Bạn không có khoản nợ nào!", color=discord.Color.green()), mention_author=False)

    if user_data.get("money", 0) < loan:
        return await ctx.reply(embed=discord.Embed(
            description=f"⚠️ Thiếu tiền! Cần **{loan:,} 💰** để trả nợ. Bạn chỉ có {user_data['money']:,} 💰.\nRút từ ngân hàng: `k bank rut all`",
            color=discord.Color.red()
        ), mention_author=False)

    user_data["money"] -= loan
    user_data["loan_amount"] = 0
    user_data["loan_due"] = None
    save_user(user_id)
    add_history(user_id, f"Trả nợ ngân hàng -{loan:,} 💰")

    await ctx.reply(embed=discord.Embed(
        title="✅ TRẢ NỢ THÀNH CÔNG",
        description=f"Đã trả **{loan:,} 💰** cho ngân hàng. Tín dụng sạch!",
        color=discord.Color.green()
    ), mention_author=False)


# ===== GYM (BUFF DUEL) =====
@bot.command()
async def gym(ctx, action: str = ""):
    """Tập gym để tăng sức mạnh trong duel"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    gym_level = user_data.get("gym_level", 0)

    if not action:
        embed = discord.Embed(title="💪 PHÒNG GYM", color=discord.Color.orange())
        embed.add_field(name="Level hiện tại", value=f"**Lv{gym_level}** (+{gym_level*5}% ATK trong Duel)", inline=False)
        upgrade_cost = (gym_level + 1) * 50000
        embed.add_field(name="Nâng cấp", value=f"Lv{gym_level+1}: **{upgrade_cost:,} 💰**\n`k gym nangcap`", inline=False)
        embed.add_field(name="Tập luyện hàng ngày", value="`k gym tap` - nhận XP + giảm CD duel", inline=False)
        return await ctx.reply(embed=embed, mention_author=False)

    action = action.lower()
    if action == "nangcap":
        cost = (gym_level + 1) * 50000
        if gym_level >= 10: return await ctx.reply("⚠️ Gym đã max level!", mention_author=False)
        if user_data.get("money", 0) < cost: return await ctx.reply(f"⚠️ Cần **{cost:,} 💰**!", mention_author=False)
        user_data["money"] -= cost
        user_data["gym_level"] = gym_level + 1
        save_user(user_id)
        await ctx.reply(embed=discord.Embed(description=f"💪 **GYM LV{gym_level+1}!** +{(gym_level+1)*5}% ATK trong mọi trận Duel!", color=discord.Color.orange()), mention_author=False)
    elif action == "tap":
        user_data["xp"] = user_data.get("xp", 0) + 50
        save_user(user_id)
        await ctx.reply(embed=discord.Embed(description="💪 Tập gym 1 giờ, nhận **+50 XP**!", color=discord.Color.green()), mention_author=False)
    else:
        await ctx.reply("⚠️ `k gym` | `k gym nangcap` | `k gym tap`", mention_author=False)


# =====================================================================
# DATA NHÂN SINH, VŨ KHÍ, KỊCH BẢN (giữ nguyên)
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "🪵 Gậy Gỗ Mục", "terrible": 25, "bad": 40, "neutral": 15, "good": 15, "great": 5, "jackpot": 0},
    "kiem_hiep_si": {"price": 500, "name": "⚔️ Kiếm Hiệp Sĩ", "terrible": 10, "bad": 20, "neutral": 15, "good": 30, "great": 20, "jackpot": 5},
    "sung_phong_luu": {"price": 3000, "name": "🚀 Súng Phóng Lựu RPG", "terrible": 5, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 15},
    "gang_tay": {"price": 5000, "name": "🧤 Găng Tay Vô Cực", "terrible": 2, "bad": 5, "neutral": 5, "good": 20, "great": 40, "jackpot": 28}
}

SCENARIOS = {
    "terrible": [{"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!** Bị đấm bay xa, rớt sạch đồ đạc!"}],
    "bad": [{"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!** Một con khỉ giật túi tiền rồi đu cây biến mất."}],
    "neutral": [{"mult": 0, "msg": "🍂 **LÁ KHÔ XÀO XẠC...** Chẳng có gì cả."}],
    "good": [{"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!** Nhặt được một chiếc ví nhỏ."}],
    "great": [{"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!** Tịch thu kho báu của toán cướp rừng!"}],
    "jackpot": [{"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)** Trúng giải ĐẶC BIỆT!"}]
}

EVENTS_P1 = [{"q": "Tuổi 15: Bạn tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", "choices": [{"text": "Đem nộp lên công an phường", "rate": 50, "win": "Chủ ví là giám đốc lớn, khen thưởng tiền mặt.", "lose": "Bị công an nghi là kẻ ăn cắp, phạt lao động công ích.", "tien_w": 5000, "tien_l": -10000}, {"text": "Bỏ túi xài luôn, không nói ai", "rate": 20, "win": "Trót lọt, bao cả lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường và bị đuổi học.", "tien_w": 8000, "tien_l": -25000}, {"text": "Rút tờ 500k rồi vứt lại ví", "rate": 30, "win": "Trót lọt, dùng tiền đó nạp game.", "lose": "Chủ nhân báo mất, bị giang hồ mạng truy lùng đền gấp 10.", "tien_w": 500, "tien_l": -50000}, {"text": "Giả vờ không thấy, đi thẳng", "rate": 80, "win": "Bình yên vô sự.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn.", "tien_w": 0, "tien_l": -15000}]}]
EVENTS_P2 = [{"q": "Tuổi 25: Bạn có 500 triệu tiết kiệm, hãy đưa ra quyết định đầu tư.", "choices": [{"text": "All-in Tiền ảo (Crypto)", "rate": 15, "win": "Giá x100 lần! Mua biệt thự và siêu xe.", "lose": "Bị sập sàn, cháy túi và gánh nợ ngân hàng.", "tien_w": 2500000, "tien_l": -500000}, {"text": "Gửi tiết kiệm ngân hàng", "rate": 70, "win": "Lãi suất ổn định, cuộc sống an nhàn.", "lose": "Ngân hàng bị thanh tra, giám đốc ôm tiền bỏ trốn.", "tien_w": 50000, "tien_l": -500000}, {"text": "Khởi nghiệp kinh doanh nhà hàng", "rate": 30, "win": "Khách đông nườm nượp, mở chuỗi 5 chi nhánh.", "lose": "Bị đối thủ chơi bẩn bóc phốt, phá sản ôm nợ.", "tien_w": 500000, "tien_l": -800000}, {"text": "Mua vàng cất vào két sắt", "rate": 60, "win": "Vàng tăng giá phi mã, chốt lời đậm.", "lose": "Bị trộm cạy cửa khiêng luôn két sắt.", "tien_w": 100000, "tien_l": -500000}]}]
EVENTS_P3 = [{"q": "Tuổi 35: Cò đất rủ chung vốn lướt sóng khu quy hoạch mới.", "choices": [{"text": "Cắm sổ đỏ vay nặng lãi quất liền", "rate": 10, "win": "Giá đất x5, trở thành tỷ phú bất động sản.", "lose": "Dính bẫy dự án ma. Giang hồ siết nợ, ra đê ở.", "tien_w": 5000000, "tien_l": -2000000}, {"text": "Mua 1 lô nhỏ bằng vốn tự có", "rate": 40, "win": "Đất lên nhẹ, chốt lời an toàn.", "lose": "Đất dính quy hoạch làm nghĩa trang, giam vốn không ai mua.", "tien_w": 300000, "tien_l": -200000}, {"text": "Làm Cò đất ăn hoa hồng", "rate": 50, "win": "Chốt được chục lô, hoa hồng nhận mỏi tay.", "lose": "Khách hàng bùng kèo, bị chủ đất giam tiền cọc bắt đền.", "tien_w": 200000, "tien_l": -100000}, {"text": "Không quan tâm nhà đất", "rate": 80, "win": "Cuộc sống trôi qua bình yên.", "lose": "Lạm phát tăng cao, tiền giấy mất giá trầm trọng.", "tien_w": 0, "tien_l": -50000}]}]
EVENTS_P4 = [{"q": "Tuổi 50: Bạn bước vào giai đoạn khủng hoảng tuổi trung niên.", "choices": [{"text": "Bán đất mua siêu xe để tìm lại thanh xuân", "rate": 10, "win": "Tham gia giải đua xe, trở nên nổi tiếng kiếm bộn tiền quảng cáo.", "lose": "Đạp nhầm chân ga tông nát xe.", "tien_w": 800000, "tien_l": -1000000}, {"text": "Cặp Sugar Baby", "rate": 20, "win": "Tâm hồn trẻ lại, sung mãn như thanh niên.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, ra tòa ly hôn mất trắng.", "tien_w": 10000, "tien_l": -2000000}, {"text": "Chơi đồ cổ, lan đột biến", "rate": 30, "win": "Bán được bình gốm cổ cho đại gia nước ngoài.", "lose": "Thị trường sập, ôm đống rác trong nhà.", "tien_w": 600000, "tien_l": -500000}, {"text": "Tập Thiền, đi chùa, ăn chay", "rate": 80, "win": "Tâm hồn thanh tịnh, sức khỏe dồi dào.", "lose": "Bị gian thương bán nấm chay có độc, phải đi rửa ruột.", "tien_w": 50000, "tien_l": -80000}]}]
EVENTS_P5 = [{"q": "Tuổi 70: Có người đến gạ bán Linh Đan Cải Lão Hoàn Đồng giá 1 Tỷ.", "choices": [{"text": "Vung tiền mua ngay không chần chừ", "rate": 5, "win": "Phép màu xảy ra! Bạn trở lại tuổi 20!", "lose": "Thuốc giả chứa chì và thủy ngân. Bạn thăng thiên sớm.", "tien_w": 5000000, "tien_l": -1000000, "die_l": True}, {"text": "Lập di chúc chia tài sản cho con cháu", "rate": 60, "win": "Con cháu hiếu thảo, tổ chức lễ mừng thọ hoành tráng.", "lose": "Con cháu bất hiếu, đánh nhau giành giật gia tài.", "tien_w": 200000, "tien_l": -500000, "die_l": True}, {"text": "Quyên góp 100% tài sản đi làm từ thiện", "rate": 70, "win": "Được nhà nước tạc tượng vinh danh.", "lose": "Tổ chức từ thiện cuỗm tiền chạy mất.", "tien_w": 500000, "tien_l": -1000000, "die_l": True}, {"text": "Lên Las Vegas quất 1 ván Casino All-in cuối đời", "rate": 10, "win": "Trúng Jackpot 50 triệu đô! Lên báo quốc tế!", "lose": "Thua trắng tay, nhồi máu cơ tim gục tại sòng bạc.", "tien_w": 10000000, "tien_l": -1000000, "die_l": True}]}]

FISH_TABLE = {
    "common": {"rate": 50, "pool": [("Cá Rô Đồng 🐟", 300, 1000), ("Cá Trê Béo 🐠", 500, 1500), ("Cá Chép Vàng 🐡", 700, 1800), ("Cá Mương Nhỏ 🐟", 200, 600)]},
    "rare": {"rate": 28, "pool": [("Cá Hồi Nguyên Chất 🍣", 4000, 10000), ("Cá Mú Đỏ 🦈", 5000, 12000), ("Cá Vược Bạc 🐟", 3000, 8000)]},
    "epic": {"rate": 13, "pool": [("Cá Ngừ Đại Dương 🐋", 18000, 45000), ("Cá Kiếm Thần Tốc ⚡", 22000, 55000), ("Bạch Tuộc Khổng Lồ 🐙", 25000, 60000)]},
    "legendary": {"rate": 4, "pool": [("Cá Vàng Thần Kỳ ✨", 90000, 200000), ("Rồng Biển Cổ Đại 🐲", 150000, 400000)]},
    "trash": {"rate": 5, "pool": [("Cái Giày Cũ 👟", -2000, -1000), ("Lon Nước Rỉ Sét 🥫", -1500, -500), ("Cần Câu Gãy 🪤", -3000, -1000)]}
}

def get_fish_bonus(user_data):
    assets = user_data.get("assets", [])
    if "Máy Câu Tự Động ⚙️" in assets: return 1.4
    if "Cần Câu Carbon 🎣" in assets: return 1.15
    if "Cần Câu Cơ Bản 🎣" in assets: return 0.9
    return 0.5

JOBS = [
    {"name": "Phụ Hồ 🧱", "min": 2000, "max": 6000, "time": 45, "desc": "Trộn hồ, vác gạch..."},
    {"name": "Shipper 🛵", "min": 3000, "max": 9000, "time": 45, "desc": "Giao đồ ăn, đội nắng..."},
    {"name": "Lập Trình Viên 💻", "min": 10000, "max": 25000, "time": 45, "desc": "Fix bug, uống cà phê..."},
    {"name": "Giáo Viên 📚", "min": 5000, "max": 15000, "time": 45, "desc": "Giảng bài, chấm bài..."},
    {"name": "Bác Sĩ 🏥", "min": 15000, "max": 40000, "time": 45, "desc": "Khám bệnh, kê đơn..."},
    {"name": "Nghệ Sĩ 🎨", "min": 500, "max": 80000, "time": 45, "desc": "Lúc thì trắng tay, lúc thì hot trend..."},
    {"name": "Streamer 🎮", "min": 500, "max": 60000, "time": 45, "desc": "Livestream, nhận donate..."},
    {"name": "Thám Tử Tư 🔍", "min": 7000, "max": 30000, "time": 45, "desc": "Theo dõi người, chụp ảnh..."},
    {"name": "Môi Giới CK 📈", "min": 5000, "max": 50000, "time": 45, "desc": "Tư vấn cổ phiếu cho khách..."},
    {"name": "Trader Crypto 🪙", "min": -10000, "max": 100000, "time": 45, "desc": "May thì giàu, xui thì bay ..."},
]

DAILY_QUESTS = [
    {"id": "gamble5", "name": "Tay Chơi Cứng", "desc": "Chơi casino 5 lần", "target": 5, "type": "gamble", "reward": 15000},
    {"id": "mine3", "name": "Thợ Mỏ Chăm Chỉ", "desc": "Đào vàng 3 lần", "target": 3, "type": "mine", "reward": 12000},
    {"id": "fish10", "name": "Ngư Dân Đạo Nghĩa", "desc": "Câu cá 10 lần", "target": 10, "type": "fish", "reward": 25000},
    {"id": "give1", "name": "Bố Thí Hào Phóng", "desc": "Chuyển tiền cho 1 người", "target": 1, "type": "give", "reward": 8000},
    {"id": "farm1", "name": "Lão Nông Tri Điền", "desc": "Thu hoạch nông trại 1 lần", "target": 1, "type": "farm", "reward": 20000},
    {"id": "gacha3", "name": "Nghiện Gacha", "desc": "Quay gacha 3 lần", "target": 3, "type": "gacha", "reward": 40000},
    {"id": "work3", "name": "Nhân Viên Mẫn Cán", "desc": "Đi làm thêm 3 lần", "target": 3, "type": "work", "reward": 30000},
    {"id": "ck_trade1", "name": "Nhà Đầu Tư", "desc": "Giao dịch CK 1 lần", "target": 1, "type": "ck_trade", "reward": 50000},
    {"id": "spin1", "name": "Quay Số", "desc": "Quay vòng quay 1 lần", "target": 1, "type": "spin", "reward": 10000},
]

def get_or_assign_quest(user_data):
    now = datetime.now()
    last_quest_str = user_data.get("last_quest", "2000-01-01 00:00:00")
    try: last_quest = datetime.strptime(last_quest_str, "%Y-%m-%d %H:%M:%S")
    except Exception: last_quest = datetime(2000, 1, 1)

    if now - last_quest >= timedelta(days=1) or user_data.get("quest") is None:
        quest = random.choice(DAILY_QUESTS)
        user_data["quest"] = quest["id"]
        user_data["quest_progress"] = 0
        user_data["last_quest"] = now.strftime("%Y-%m-%d %H:%M:%S")
        return quest, True

    quest_id = user_data.get("quest")
    quest = next((q for q in DAILY_QUESTS if q["id"] == quest_id), None)
    return quest, False

def update_quest_progress(user_id, quest_type):
    user_data = load_user(user_id)
    quest, is_new = get_or_assign_quest(user_data)
    if not quest or quest["type"] != quest_type: return None

    progress = user_data.get("quest_progress", 0)
    if progress >= quest["target"]: return None

    progress += 1
    user_data["quest_progress"] = progress

    if progress >= quest["target"]:
        reward = quest["reward"]
        user_data["money"] += reward
        add_history(user_id, f"Hoàn thành Quest '{quest['name']}' (+{reward:,} 💰)")
        save_user(user_id)
        return f"✅ **HOÀN THÀNH NHIỆM VỤ: {quest['name']}!**\nPhần thưởng: **+{reward:,} 💰**"

    save_user(user_id)
    return None

# =====================================================================
# UI CLASSES (giữ phần gốc quan trọng)
# =====================================================================
class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        options = []
        for key, item_data in SHOP_ITEMS.items():
            if item_data["type"] == category_type:
                options.append(discord.SelectOption(label=item_data['name'], description=f"Giá: {item_data['price']:,} 💰", value=key, emoji=item_data['emoji']))
        super().__init__(placeholder="Nhấn vào đây để chọn món đồ...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_info = SHOP_ITEMS[self.values[0]]
        if user_data.get("money", 0) < item_info["price"]:
            return await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ Cần **{item_info['price']:,} 💰**.", color=discord.Color.red()), ephemeral=True)
        user_data["money"] -= item_info["price"]
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            success_message = f"🎉 Trang bị danh hiệu: **{item_info['name']}**."
        elif item_info["type"] == "tool":
            if item_info["name"] in user_data.get("assets", []):
                user_data["money"] += item_info["price"]
                return await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ Đã có rồi!", color=discord.Color.orange()), ephemeral=True)
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Đã mua **{item_info['name']}**!"
        else:
            if item_info["name"] in user_data.get("assets", []):
                user_data["money"] += item_info["price"]
                return await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ Đã sở hữu rồi!", color=discord.Color.orange()), ephemeral=True)
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Đập hộp **{item_info['name']}**!"
        save_user(user_id)
        add_history(user_id, f"Mua {item_info['name']} (-{item_info['price']:,} 💰)")
        new_achievements = check_achievement(user_id, user_data)
        ach_text = ""
        if new_achievements: save_user(user_id); ach_text = "\n\n🏅 **THÀNH TÍCH MỚI:** " + ", ".join(new_achievements)
        embed_success = discord.Embed(title="🛍️ GIAO DỊCH HOÀN TẤT!", description=success_message + ach_text, color=discord.Color.green())
        embed_success.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("title"))
        await interaction.response.edit_message(embed=discord.Embed(title="🛍️ QUẦY BÁN DANH HIỆU", color=discord.Color.blue()), view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("vehicle"))
        await interaction.response.edit_message(embed=discord.Embed(title="🛍️ SHOWROOM", color=discord.Color.green()), view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("house"))
        await interaction.response.edit_message(embed=discord.Embed(title="🛍️ BẤT ĐỘNG SẢN", color=discord.Color.red()), view=view)

    @discord.ui.button(label="Dụng Cụ Câu Cá", style=discord.ButtonStyle.secondary, emoji="🎣")
    async def btn_tool(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("tool"))
        await interaction.response.edit_message(embed=discord.Embed(title="🎣 THIẾT BỊ CÂU CÁ", color=discord.Color.blue()), view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Ai gọi lệnh người đó mua!", ephemeral=True); return False
        return True

class SellItemSelect(discord.ui.Select):
    def __init__(self, items, is_pet=False):
        self.is_pet = is_pet
        options = []
        if is_pet:
            count = 0
            for pet, quantity in list(items.items()):
                if count >= 25: break
                if quantity > 0:
                    options.append(discord.SelectOption(label=pet, description=f"Đang có: {quantity} | Giá: {get_pet_sell_price(pet):,} 💰", value=pet))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(label=asset, description=f"Giá cầm: {get_asset_price(asset):,} 💰", value=asset))
        super().__init__(placeholder="Chọn món đồ muốn bán...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); item_value = self.values[0]
        if self.is_pet:
            if user_data.get("pets", {}).get(item_value, 0) <= 0: return await interaction.response.send_message("Lỗi!", ephemeral=True)
            sell_price = get_pet_sell_price(item_value)
            user_data["pets"][item_value] -= 1
            if user_data["pets"][item_value] == 0: del user_data["pets"][item_value]
            success_message = f"✅ Bán **{item_value}**. Nhận **{sell_price:,} 💰**!"
        else:
            if item_value not in user_data.get("assets", []): return await interaction.response.send_message("Lỗi!", ephemeral=True)
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            success_message = f"✅ Cầm **{item_value}**. Nhận **{sell_price:,} 💰**!"
        user_data["money"] += sell_price; save_user(user_id); add_history(user_id, f"Bán {item_value} (+{sell_price:,} 💰)")
        await interaction.response.edit_message(embed=discord.Embed(title="🤝 GIAO DỊCH HOÀN TẤT", description=success_message, color=discord.Color.dark_orange()), view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60); self.author = author

    @discord.ui.button(label="Cắm Sổ Đỏ / Cầm Xe", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: return await interaction.response.send_message("Không có tài sản!", ephemeral=True)
        view = discord.ui.View(timeout=60); view.add_item(SellItemSelect(assets, False))
        await interaction.response.edit_message(embed=discord.Embed(title="🏷️ CẦM ĐỒ", color=discord.Color.orange()), view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets: return await interaction.response.send_message("Không có thú cưng!", ephemeral=True)
        view = discord.ui.View(timeout=60); view.add_item(SellItemSelect(pets, True))
        await interaction.response.edit_message(embed=discord.Embed(title="🏷️ THU MUA THÚ CƯNG", color=discord.Color.green()), view=view)

    async def interaction_check(self, interaction: discord.Interaction): return interaction.user.id == self.author.id

class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author; self.stats = stats; self.phase = 1; self.tien_an = 0; self.logs = []; self.ev = random.choice(EVENTS_P1)
        if self.stats["may_man"] >= 8: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng.")
        elif self.stats["may_man"] >= 4: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức bình dân.")
        else: self.logs.append("👶 **Tuổi 0:** Bạn bị vứt ra ngoài bãi rác từ nhỏ.")
        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text'][:70]}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text'][:70]}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text'][:70]}", style=discord.ButtonStyle.success, custom_id="btn_c")
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text'][:70]}", style=discord.ButtonStyle.danger, custom_id="btn_d")
        self.btn_a.callback = self.choice_a; self.btn_b.callback = self.choice_b; self.btn_c.callback = self.choice_c; self.btn_d.callback = self.choice_d
        self.add_item(self.btn_a); self.add_item(self.btn_b); self.add_item(self.btn_c); self.add_item(self.btn_d)

    async def on_timeout(self):
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh!", ephemeral=True); return False
        return True

    async def choice_a(self, interaction): await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction): await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction): await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction): await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction, choice_idx, letter):
        choice_data = self.ev["choices"][choice_idx]
        final_rate = min(85.0, choice_data["rate"] + self.stats["may_man"] * 1.5)
        roll = random.uniform(0, 100)
        is_win = roll <= final_rate
        result_msg = choice_data["win"] if is_win else choice_data["lose"]
        money_change = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        is_dead = (is_win and choice_data.get("die_w")) or (not is_win and choice_data.get("die_l"))
        self.tien_an += money_change
        ages = {1: 15, 2: 25, 3: 35, 4: 50, 5: 70}
        tuoi = ages.get(self.phase, 15)
        status = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log = f"🗓️ **Tuổi {tuoi}:** Chọn {letter}.\n🎲 Tỉ lệ: {final_rate:.1f}% | {status}: {result_msg} ({money_change:,} 💰)"
        if is_dead: log += "\n\n💀 **BẠN ĐÃ ĐỘT TỬ!**"; self.phase = 99
        else:
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)
        self.logs.append(log)
        await self.update_ui(interaction)

    async def update_ui(self, interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH", description=f"Ký chủ: {self.author.mention}", color=discord.Color.teal())
        embed.add_field(name="🍀 Chỉ số may mắn", value=f"**{self.stats['may_man']}/10**", inline=False)
        story = "\n\n".join(self.logs[-4:]) if len(self.logs) > 4 else "\n\n".join(self.logs)
        embed.add_field(name="📜 Hành trình", value=story, inline=False)
        if self.phase <= 5:
            ages = {1: 15, 2: 25, 3: 35, 4: 50, 5: 70}
            embed.add_field(name=f"❓ Ngã rẽ tuổi {ages.get(self.phase, 70)}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.clear_items()
            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)
            user_data = load_user(user_id)
            user_data["money"] = max(0, user_data["money"] + self.tien_an); save_user(user_id)
            add_history(user_id, f"Kết thúc Nhân Sinh ({'+' if self.tien_an >= 0 else ''}{self.tien_an:,} 💰)")
            if self.tien_an < 0: embed.color = discord.Color.red(); embed.add_field(name="🪦 Kết cục", value=f"❌ Để lại khoản nợ: **{self.tien_an:,} 💰**", inline=False)
            elif self.tien_an >= 500000: embed.color = discord.Color.gold(); embed.add_field(name="🪦 Kết cục", value=f"👑 Hưởng thọ trong nhung lụa! Di sản: **+{self.tien_an:,} 💰**", inline=False)
            else: embed.color = discord.Color.blue(); embed.add_field(name="🪦 Kết cục", value=f"💼 Cuộc đời êm ấm. Di sản: **+{self.tien_an:,} 💰**", inline=False)
        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

class SoloOTTGame(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60)
        self.player_1 = p1; self.player_2 = p2; self.bet_amount = bet; self.msg = None
        self.choices = {str(p1.id): None, str(p2.id): None}; self.finished = False

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, i, b): await self.handle_choice(i, "🪨")
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, i, b): await self.handle_choice(i, "📄")
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, i, b): await self.handle_choice(i, "✂️")

    async def handle_choice(self, interaction, choice):
        user_id = str(interaction.user.id)
        if user_id not in self.choices: return await interaction.response.send_message("Không phải ván của bạn!", ephemeral=True)
        if self.choices[user_id] is not None: return await interaction.response.send_message("Đã ra chiêu rồi!", ephemeral=True)
        self.choices[user_id] = choice
        await interaction.response.send_message(f"🤫 Bạn chọn **{choice}**. Chờ đối thủ...", ephemeral=True)
        if all(v is not None for v in self.choices.values()):
            if self.finished: return
            self.finished = True
            for child in self.children: child.disabled = True
            c1 = self.choices[str(self.player_1.id)]; c2 = self.choices[str(self.player_2.id)]
            p1d = load_user(self.player_1.id); p2d = load_user(self.player_2.id); total = self.bet_amount * 2
            if c1 == c2: ket_qua = "🤝 **HÒA!** Tiền hoàn lại."; p1d["money"] += self.bet_amount; p2d["money"] += self.bet_amount
            elif (c1=="🪨" and c2=="✂️") or (c1=="📄" and c2=="🪨") or (c1=="✂️" and c2=="📄"):
                ket_qua = f"🎉 **{self.player_1.name} THẮNG!** +{total:,} 💰"; p1d["money"] += total; add_history(self.player_1.id, f"Thắng OTT +{total:,}")
            else:
                ket_qua = f"🎉 **{self.player_2.name} THẮNG!** +{total:,} 💰"; p2d["money"] += total; add_history(self.player_2.id, f"Thắng OTT +{total:,}")
            save_user(self.player_1.id); save_user(self.player_2.id)
            embed = discord.Embed(title="⚔️ KẾT QUẢ", color=discord.Color.gold())
            embed.add_field(name=self.player_1.name, value=c1, inline=True); embed.add_field(name="VS", value="⚡", inline=True); embed.add_field(name=self.player_2.name, value=c2, inline=True)
            embed.add_field(name="KẾT QUẢ", value=ket_qua, inline=False)
            await self.msg.edit(embed=embed, view=self); self.stop()

    async def on_timeout(self):
        if self.finished: return
        p1d = load_user(self.player_1.id); p2d = load_user(self.player_2.id)
        p1d["money"] += self.bet_amount; p2d["money"] += self.bet_amount; save_user(self.player_1.id); save_user(self.player_2.id)
        try: await self.msg.edit(embed=discord.Embed(description="⏳ Hết giờ, tiền hoàn.", color=discord.Color.dark_gray()), view=None)
        except Exception: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60); self.player_1 = p1; self.player_2 = p2; self.bet_amount = bet

    @discord.ui.button(label="Nhận Kèo!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction, button):
        if interaction.user.id != self.player_2.id: return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        p1d = load_user(self.player_1.id); p2d = load_user(self.player_2.id)
        if p1d.get("money", 0) < self.bet_amount or p2d.get("money", 0) < self.bet_amount: return await interaction.response.send_message("Không đủ tiền!", ephemeral=True)
        p1d["money"] -= self.bet_amount; p2d["money"] -= self.bet_amount; save_user(self.player_1.id); save_user(self.player_2.id)
        game = SoloOTTGame(self.player_1, self.player_2, self.bet_amount)
        embed = discord.Embed(title="⚔️ OẲN TÙ TÌ", description=f"{self.player_1.mention} 🆚 {self.player_2.mention}\nCược: **{self.bet_amount:,} 💰**\n\n👇 **BẤM ĐỂ CHỌN CHIÊU**", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=game); game.msg = interaction.message; self.stop()

class MarryAccept(discord.ui.View):
    def __init__(self, sender, receiver):
        super().__init__(timeout=60); self.sender = sender; self.receiver = receiver

    @discord.ui.button(label="Em Đồng Ý 💍", style=discord.ButtonStyle.success)
    async def btn_accept(self, interaction, button):
        if interaction.user.id != self.receiver.id: return await interaction.response.send_message("Người ta cầu hôn người khác!", ephemeral=True)
        sd = load_user(self.sender.id); rd = load_user(self.receiver.id)
        if sd.get("money", 0) < 1000000: return await interaction.response.send_message("Thiếu 1M lễ cưới!", ephemeral=True)
        sd["money"] -= 1000000; sd["spouse"] = str(self.receiver.id); rd["spouse"] = str(self.sender.id)
        save_user(self.sender.id); save_user(self.receiver.id)
        for c in self.children: c.disabled = True
        embed = discord.Embed(title="💒 KẾT HÔN!", description=f"🎉 {self.sender.mention} và {self.receiver.mention} trăm năm hạnh phúc!", color=discord.Color.magenta())
        embed.set_image(url=GIF_LINKS["marry"])
        await interaction.response.edit_message(embed=embed, view=self); self.stop()

    @discord.ui.button(label="Em Từ Chối 💔", style=discord.ButtonStyle.danger)
    async def btn_decline(self, interaction, button):
        if interaction.user.id != self.receiver.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(description=f"💔 {self.receiver.name} từ chối...", color=discord.Color.dark_grey()), view=self); self.stop()

class DuelAccept(discord.ui.View):
    def __init__(self, challenger, target, bet):
        super().__init__(timeout=60); self.challenger = challenger; self.target = target; self.bet = bet; self.finished = False

    @discord.ui.button(label="Chấp Nhận!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction, button):
        if interaction.user.id != self.target.id: return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        if self.finished: return
        self.finished = True
        cd = load_user(self.challenger.id); td = load_user(self.target.id)
        if cd.get("money",0) < self.bet or td.get("money",0) < self.bet: return await interaction.response.send_message("Thiếu tiền!", ephemeral=True)
        cd["money"] -= self.bet; td["money"] -= self.bet; save_user(self.challenger.id); save_user(self.target.id)

        # Gym buff
        c_gym = load_user(self.challenger.id).get("gym_level", 0)
        t_gym = load_user(self.target.id).get("gym_level", 0)
        c_hp = 100 + c_gym * 10; t_hp = 100 + t_gym * 10
        c_atk_bonus = 1 + c_gym * 0.05; t_atk_bonus = 1 + t_gym * 0.05

        battle_log = []
        rounds = 0
        while c_hp > 0 and t_hp > 0 and rounds < 10:
            rounds += 1
            c_atk = int(random.randint(8, 28) * c_atk_bonus)
            t_atk = int(random.randint(8, 28) * t_atk_bonus)
            t_hp -= c_atk; c_hp -= t_atk
            battle_log.append(f"**Vòng {rounds}:** {self.challenger.name} gây {c_atk} ST | {self.target.name} gây {t_atk} ST")

        winner = self.challenger if c_hp > t_hp else (self.target if t_hp > c_hp else random.choice([self.challenger, self.target]))
        loser = self.target if winner == self.challenger else self.challenger
        prize = self.bet * 2
        wd = load_user(winner.id); wd["money"] += prize; save_user(winner.id)
        add_history(winner.id, f"Thắng Duel vs {loser.name} (+{prize:,})")

        embed = discord.Embed(title="⚔️ KẾT QUẢ QUYẾT ĐẤU", color=discord.Color.gold())
        embed.add_field(name="Diễn biến", value="\n".join(battle_log[-5:]), inline=False)
        embed.add_field(name="🏆 KẾT QUẢ", value=f"**{winner.mention}** thắng! Nhận **{prize:,} 💰**!", inline=False)
        if c_gym or t_gym:
            embed.add_field(name="💪 Gym Buff", value=f"{self.challenger.name}: Gym Lv{c_gym} | {self.target.name}: Gym Lv{t_gym}", inline=False)
        await interaction.response.edit_message(embed=embed, view=None); self.stop()

    @discord.ui.button(label="Bỏ Chạy 🏳️", style=discord.ButtonStyle.secondary)
    async def btn_decline(self, interaction, button):
        if interaction.user.id != self.target.id: return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        await interaction.response.edit_message(embed=discord.Embed(description=f"🏳️ {self.target.name} nhút nhát bỏ chạy!", color=discord.Color.dark_grey()), view=None); self.stop()

class SapNhapAcceptView(discord.ui.View):
    def __init__(self, buyer_comp_id, target_comp_id, target_boss_id, price):
        super().__init__(timeout=120)
        self.buyer_comp_id = buyer_comp_id
        self.target_comp_id = target_comp_id
        self.target_boss_id = target_boss_id
        self.price = price

    @discord.ui.button(label="✅ Đồng ý bán công ty", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_boss_id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)

        buyer_comp = load_company(self.buyer_comp_id)
        target_comp = load_company(self.target_comp_id)
        if not buyer_comp or not target_comp:
            return await interaction.response.send_message("⚠️ Một công ty không còn tồn tại!", ephemeral=True)
        if buyer_comp.get("treasury", 0) < self.price:
            return await interaction.response.send_message("⚠️ Bên mua không còn đủ tiền!", ephemeral=True)

        buyer_comp["treasury"] -= self.price
        target_boss_data = load_user(self.target_boss_id)
        target_boss_data["money"] += self.price
        save_user(self.target_boss_id)

        absorbed = int(target_comp.get("treasury", 0) * 0.5)
        buyer_comp["treasury"] += absorbed
        buyer_comp["reputation"] = min(100, buyer_comp.get("reputation", 100) + 10)
        save_company(self.buyer_comp_id)

        for m_id in list(target_comp.get("members", {}).keys()):
            m_data = load_user(m_id)
            m_data["company"] = None
            save_user(m_id)

        COMPANY_CACHE.pop(self.target_comp_id, None)
        try:
            companies_col.delete_one({"_id": self.target_comp_id})
        except Exception:
            pass

        for c in self.children: c.disabled = True
        embed = discord.Embed(
            title="🤝 SÁP NHẬP THÀNH CÔNG!",
            description=(
                f"**{buyer_comp['name']}** đã thâu tóm **{target_comp['name']}**!\n"
                f"💰 Giá mua: **{self.price:,} 💰** (trả cho cựu Chủ Tịch)\n"
                f"📦 Hấp thụ thêm **{absorbed:,} 💰** từ quỹ cũ\n"
                f"📈 Danh tiếng bên mua +10"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="❌ Từ chối", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_boss_id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(description="❌ Lời mời sáp nhập bị từ chối.", color=discord.Color.dark_grey()),
            view=self
        )
        self.stop()

class CompanyInviteView(discord.ui.View):
    def __init__(self, comp_id, comp_name, target_user):
        super().__init__(timeout=60); self.comp_id = comp_id; self.comp_name = comp_name; self.target_user = target_user

    @discord.ui.button(label="Gia nhập", style=discord.ButtonStyle.success, emoji="🤝")
    async def btn_accept(self, interaction, button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        tid = str(self.target_user.id); td = load_user(tid)
        if td.get("company"): return await interaction.response.send_message("Đã trong công ty khác!", ephemeral=True)
        comp = load_company(self.comp_id)
        if not comp: return await interaction.response.send_message("Công ty không còn tồn tại!", ephemeral=True)
        comp["members"][tid] = "nhanvien"; td["company"] = self.comp_id
        save_company(self.comp_id); save_user(tid)
        await interaction.response.edit_message(embed=discord.Embed(description=f"🎉 {self.target_user.mention} gia nhập **{self.comp_name}**!", color=discord.Color.green()), view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def btn_decline(self, interaction, button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        await interaction.response.edit_message(embed=discord.Embed(description=f"❌ {self.target_user.name} từ chối.", color=discord.Color.red()), view=None)

class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="4 Giờ (Bãi Cỏ)", description="~350 💰", emoji="🌿", value="4"), discord.SelectOption(label="8 Giờ (Hang Động)", description="~800 💰", emoji="🦇", value="8"), discord.SelectOption(label="12 Giờ (Di Tích)", description="~1500 💰", emoji="🏛️", value="12")]
        super().__init__(placeholder="Chọn địa điểm cắm trại...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id)
        hours = int(self.values[0])
        if hours == 4: reward = random.randint(200, 500)
        elif hours == 8: reward = random.randint(500, 1000)
        else: reward = random.randint(1000, 2000)
        end_time = datetime.now() + timedelta(hours=hours)
        user_data["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S"); user_data["exp_reward"] = reward; save_user(user_id)
        await interaction.response.edit_message(embed=discord.Embed(title="⛺ LÊN ĐƯỜNG!", description=f"Cắm trại **{hours} giờ**.\n⏳ Gõ `k phai` để thu hoạch!", color=discord.Color.green()), view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60); self.author = author; self.add_item(ExpSelect())
    async def interaction_check(self, interaction): return interaction.user.id == self.author.id

# =====================================================================
# LỆNH CÔNG TY (giữ nguyên từ gốc)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.send(embed=discord.Embed(title="🏢 SÀN GIAO DỊCH DOANH NGHIỆP", description="Bạn chưa có công ty.\n`k cty tao <tên công ty>` (Phí: 500,000 💰)", color=discord.Color.red()))
    
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None; save_user(user_id)
        return await ctx.send("Công ty của bạn đã phá sản rồi!")
        
    my_role = comp["members"].get(user_id, "nhanvien")
    role_name = comp["roles"].get(my_role, my_role)
    atk, df = comp.get("atk_level", 1), comp.get("def_level", 1)
    
    embed_db = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed_db.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed_db.add_field(name="Sức Mạnh", value=f"⚔️ Công: Lv{atk} | 🛡️ Thủ: Lv{df}", inline=True)
    
    rep = comp.get("reputation", 100)
    rep_status = "Tốt" if rep > 80 else "Trung Bình" if rep > 50 else "⚠️ Cảnh báo Đỏ"
    scandal_str = "\n🚨 **ĐANG DÍNH PHỐT!**" if comp.get("has_scandal") else ""
    embed_db.add_field(name="Danh Tiếng", value=f"**{rep}/100** ({rep_status}){scandal_str}", inline=True)
    embed_db.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed_db.add_field(name="Chức vụ của bạn", value=f"**{role_name}**", inline=False)
    cmds = (
        "`k cty gop <tiền>` | `k cty thulai` | `k cty dinhchinh` | `k cty nangcap <cong/thu>` | `k cty roi`\n"
        "**Thương trường:** `k cty vaycty <tiền>` | `k cty tranocty` | `k cty quangcao <tiền>`\n"
        "`k cty boicong <tên cty>` | `k cty giandiep <tên cty>` | `k cty anninh` | `k cty sapnhap <giá> <tên cty>` | `k cty cotuc <%>`"
    )
   
    if my_role in ["boss", "quanly"]: cmds += "\n**Quản Lý:** `k cty tuyen @user` | `k cty duoi @user`"
    if my_role == "boss": cmds += "\n**Chủ Tịch:** `k cty luong <tiền>` | `k ck ipo` | `k cty chucvu @user <role>` | `k cty doitenchuc <role> <tên>`"
        
    embed_db.add_field(name="📋 Bảng Lệnh", value=cmds, inline=False)
    await ctx.send(embed=embed_db)

@cty.command()
async def tao(ctx, *, name: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    if user_data.get("company"): return await ctx.reply("Bạn đã có công ty rồi!", mention_author=False)
    if user_data.get("money", 0) < 500000: return await ctx.reply("⚠️ Phí đăng ký **500,000 💰**. Cày thêm đi sếp!", mention_author=False)
    
    user_data["money"] -= 500000; user_data["company"] = user_id
    new_comp = {
        "_id": user_id, "name": name, "treasury": 0, "members": {user_id: "boss"}, 
        "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, 
        "reputation": 100, "has_scandal": False, "atk_level": 1, "def_level": 1,
        "last_interest": "2000-01-01 00:00:00", "is_ipo": False
    }
    COMPANY_CACHE[user_id] = new_comp; save_company(user_id); save_user(user_id)
    await ctx.send(embed=discord.Embed(title="🏢 KHAI TRƯƠNG HỒNG PHÁT", description=f"Chúc mừng {ctx.author.mention} đã thành lập **{name}**!\nGõ `k cty` để mở bảng điều khiển.", color=discord.Color.green()))

@cty.command()
async def dinhchinh(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn chưa có công ty!")
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Chỉ Ban Giám Đốc mới được đính chính!")
    if not comp.get("has_scandal") and comp.get("reputation", 100) >= 100: return await ctx.reply("Công ty đang trong sạch!")
    cost = max(100000, int(comp["treasury"] * 0.05))
    if comp["treasury"] < cost: return await ctx.reply(f"⚠️ Quỹ không đủ **{cost:,} 💰** để thuê báo chí!")
    comp["treasury"] -= cost; comp["has_scandal"] = False
    recovered_rep = random.randint(15, 30)
    comp["reputation"] = min(100, comp.get("reputation", 50) + recovered_rep)
    save_company(comp_id)
    embed = discord.Embed(title="📰 XỬ LÝ KHỦNG HOẢNG THÀNH CÔNG", description=f"Chi **{cost:,} 💰** dập tắt dư luận xấu!\n✅ **Đã gỡ bỏ Scandal!**\n📈 Danh tiếng hồi phục: **+{recovered_rep}**", color=discord.Color.green())
    await ctx.reply(embed=embed, mention_author=False)

@cty.command()
async def nangcap(ctx, stat: str, levels: int = 1):
    stat = stat.lower(); user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn chưa có công ty!")
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Chỉ Sếp mới được nâng cấp!")
    if levels < 1 or levels > 100: return await ctx.reply("⚠️ Nâng tối đa 100 cấp 1 lần!")

    if stat == "cong":
        current_lvl = comp.get("atk_level", 1)
        # Tính tổng chi phí: lv1→2 + lv2→3 + ...
        total_cost = sum((current_lvl + i) * 500000 for i in range(levels))
        if comp["treasury"] < total_cost: return await ctx.reply(f"⚠️ Quỹ không đủ **{total_cost:,} 💰**!")
        comp["treasury"] -= total_cost
        comp["atk_level"] = current_lvl + levels
        msg = f"⚔️ Nâng CÔNG **Lv{current_lvl} → Lv{current_lvl+levels}**! (Trừ {total_cost:,} 💰 từ quỹ)"

    elif stat == "thu":
        current_lvl = comp.get("def_level", 1)
        total_cost = sum((current_lvl + i) * 300000 for i in range(levels))
        if comp["treasury"] < total_cost: return await ctx.reply(f"⚠️ Quỹ không đủ **{total_cost:,} 💰**!")
        comp["treasury"] -= total_cost
        comp["def_level"] = current_lvl + levels
        msg = f"🛡️ Nâng THỦ **Lv{current_lvl} → Lv{current_lvl+levels}**! (Trừ {total_cost:,} 💰 từ quỹ)"

    else: return await ctx.reply("⚠️ Dùng `k cty nangcap cong <số lv>` hoặc `k cty nangcap thu <số lv>`.")
    save_company(comp_id)
    await ctx.reply(embed=discord.Embed(description=msg, color=discord.Color.green()), mention_author=False)

@cty.command()
async def tuyen(ctx, member: discord.Member):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn có công ty đâu mà đòi tuyển người!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Chỉ Giám đốc và Chủ tịch mới được tuyển người!", mention_author=False)
    if load_user(member.id).get("company"): return await ctx.reply("Người này đang làm việc cho công ty khác rồi.", mention_author=False)
    view = CompanyInviteView(comp_id, comp["name"], member)
    await ctx.send(f"🏢 {member.mention}, bạn có lá thư mời nhận việc tại **{comp['name']}**!", view=view)

@cty.command()
async def duoi(ctx, member: discord.Member):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Bạn không có quyền sa thải!", mention_author=False)
    target_id = str(member.id)
    if target_id not in comp["members"]: return await ctx.reply("Người này không có trong công ty!", mention_author=False)
    if comp["members"][target_id] == "boss": return await ctx.reply("Không ai đuổi được sếp tổng đâu!", mention_author=False)
    del comp["members"][target_id]
    target_data = load_user(target_id); target_data["company"] = None
    save_company(comp_id); save_user(target_id)
    await ctx.reply(f"👢 Sa thải {member.mention} khỏi công ty!", mention_author=False)

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.reply("Bạn chưa gia nhập công ty nào.", mention_author=False)
    if user_data.get("money", 0) < amount: return await ctx.reply("Ví không đủ tiền!", mention_author=False)
    comp = load_company(comp_id)
    user_data["money"] -= amount; comp["treasury"] += amount
    save_user(user_id); save_company(comp_id)
    await ctx.reply(f"💰 Bạn đã cống hiến **{amount:,} 💰** vào quỹ công ty.\nTổng quỹ: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def thulai(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ Chủ tịch mới được thu lãi!", mention_author=False)
    now = datetime.now()
    try:
        last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception:
        last = datetime(2000, 1, 1)

    if now - last < timedelta(days=1): return await ctx.reply("⏳ Mỗi ngày chỉ được thu lãi 1 lần.", mention_author=False)
    lai_nhan_duoc = min(int(comp["treasury"] * 0.03), 80000)
    comp["treasury"] += lai_nhan_duoc; comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    await ctx.reply(f"📈 Công ty nhận **{lai_nhan_duoc:,} 💰** lãi hôm nay!\nTổng quỹ: **{comp['treasury']:,} 💰**.", mention_author=False)

# ── VAY VỐN / TRẢ NỢ CÔNG TY ──────────────────────────────────────────
@cty.command(name="vaycty")
async def vaycty(ctx, amount: int):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss":
        return await ctx.reply("⚠️ Chỉ Chủ Tịch mới được vay vốn cho công ty!", mention_author=False)
    if comp.get("debt", 0) > 0:
        return await ctx.reply(f"⚠️ Công ty đang nợ **{comp['debt']:,} 💰**! `k cty tranocty` trước.", mention_author=False)

    max_loan = max(1000000, int(comp.get("treasury", 0) * COMPANY_LOAN_MAX_MULT))
    if amount <= 0 or amount > max_loan:
        return await ctx.reply(f"⚠️ Vay từ 1 đến **{max_loan:,} 💰** (tối đa {COMPANY_LOAN_MAX_MULT}x quỹ hiện có).", mention_author=False)

    total_owed = int(amount * (1 + COMPANY_LOAN_INTEREST))
    due = datetime.now() + timedelta(days=COMPANY_LOAN_DAYS)
    comp["treasury"] += amount
    comp["debt"] = total_owed
    comp["debt_due"] = due.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)

    embed = discord.Embed(title="🏦 VAY VỐN NGÂN HÀNG DOANH NGHIỆP", color=discord.Color.green())
    embed.add_field(name="Số tiền vay", value=f"**{amount:,} 💰**", inline=True)
    embed.add_field(name="Phải trả", value=f"**{total_owed:,} 💰** (+{int(COMPANY_LOAN_INTEREST*100)}%)", inline=True)
    embed.add_field(name="Hạn chót", value=f"<t:{int(due.timestamp())}:F>", inline=False)
    embed.add_field(name="⚠️ Cảnh báo", value="Quá hạn = ngân hàng siết quỹ, công ty có thể **PHÁ SẢN**!", inline=False)
    await ctx.reply(embed=embed, mention_author=False)


@cty.command(name="tranocty")
async def tranocty(ctx):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]:
        return await ctx.reply("⚠️ Chỉ Ban Giám Đốc mới trả được nợ!", mention_author=False)
    debt = comp.get("debt", 0)
    if debt <= 0:
        return await ctx.reply("✅ Công ty không có nợ!", mention_author=False)
    if comp.get("treasury", 0) < debt:
        return await ctx.reply(f"⚠️ Cần **{debt:,} 💰**, quỹ chỉ có **{comp['treasury']:,} 💰**.", mention_author=False)
    comp["treasury"] -= debt
    comp["debt"] = 0
    comp["debt_due"] = None
    save_company(comp_id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Đã trả hết nợ **{debt:,} 💰**!", color=discord.Color.green()), mention_author=False)


# ── QUẢNG CÁO / PR ────────────────────────────────────────────────────
@cty.command(name="quangcao")
async def quangcao(ctx, amount: int):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]:
        return await ctx.reply("⚠️ Chỉ Ban Giám Đốc mới chạy quảng cáo!", mention_author=False)

    now = datetime.now()
    try: last = datetime.strptime(comp.get("last_pr", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)
    if now - last < timedelta(hours=PR_COOLDOWN_HOURS):
        return await ctx.reply(f"⏳ Chiến dịch PR hồi: <t:{int((last+timedelta(hours=PR_COOLDOWN_HOURS)).timestamp())}:R>", mention_author=False)

    if amount < 50000:
        return await ctx.reply("⚠️ Tối thiểu **50,000 💰** cho 1 chiến dịch!", mention_author=False)
    if comp.get("treasury", 0) < amount:
        return await ctx.reply("⚠️ Quỹ không đủ!", mention_author=False)

    comp["treasury"] -= amount
    comp["last_pr"] = now.strftime("%Y-%m-%d %H:%M:%S")

    if random.uniform(0, 100) <= 12:
        rep_change = -random.randint(5, 15)
        comp["reputation"] = max(0, comp.get("reputation", 100) + rep_change)
        result = f"💀 **QUẢNG CÁO PHẢN CẢM!** Dư luận chỉ trích, danh tiếng **{rep_change}**!"
        color = discord.Color.red()
    else:
        rep_gain = min(20, max(3, int(amount / 50000) * 3))
        comp["reputation"] = min(100, comp.get("reputation", 100) + rep_gain)
        bonus = int(amount * random.uniform(0.3, 0.8))
        comp["treasury"] += bonus
        result = f"📢 **THÀNH CÔNG!** +{rep_gain} danh tiếng, doanh thu về **+{bonus:,} 💰**!"
        color = discord.Color.green()

    save_company(comp_id)
    embed = discord.Embed(title="📢 CHIẾN DỊCH MARKETING", description=result, color=color)
    embed.set_footer(text=f"Chi: {amount:,} 💰 | Quỹ còn: {comp['treasury']:,} 💰 | Hồi sau {PR_COOLDOWN_HOURS}h")
    await ctx.reply(embed=embed, mention_author=False)


# ── BÓC PHỐT ĐỐI THỦ (SMEAR CAMPAIGN) ─────────────────────────────────
@cty.command(name="boicong", aliases=["choixau"])
async def boicong(ctx, *, target_name: str):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss":
        return await ctx.reply("⚠️ Chỉ Chủ Tịch mới ra quyết định này!", mention_author=False)

    now = datetime.now()
    try: last = datetime.strptime(comp.get("last_smear", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)
    if now - last < timedelta(hours=SMEAR_COOLDOWN_HOURS):
        return await ctx.reply(f"⏳ Đội PR đen hồi: <t:{int((last+timedelta(hours=SMEAR_COOLDOWN_HOURS)).timestamp())}:R>", mention_author=False)

    cost = 80000
    if comp.get("treasury", 0) < cost:
        return await ctx.reply(f"⚠️ Cần **{cost:,} 💰**!", mention_author=False)

    try: all_comps = list(companies_col.find())
    except Exception: all_comps = []
    target = next((c for c in all_comps if target_name.lower() in c["name"].lower()), None)
    if not target or target["_id"] == comp_id:
        return await ctx.reply("⚠️ Không tìm thấy công ty đối thủ hợp lệ!", mention_author=False)
    COMPANY_CACHE[target["_id"]] = target

    comp["treasury"] -= cost
    comp["last_smear"] = now.strftime("%Y-%m-%d %H:%M:%S")

    target_security = target.get("security_level", 1)
    success_chance = max(20, 65 - target_security * 5)

    if random.uniform(0, 100) <= success_chance:
        rep_loss = random.randint(10, 25)
        target["reputation"] = max(0, target.get("reputation", 100) - rep_loss)
        if target["reputation"] <= 30 and not target.get("has_scandal"):
            target["has_scandal"] = True
        save_company(target["_id"])
        save_company(comp_id)
        result = f"🕵️ **THÀNH CÔNG!** **{target['name']}** mất **{rep_loss}** danh tiếng!"
        color = discord.Color.dark_red()
    else:
        comp["reputation"] = max(0, comp.get("reputation", 100) - SMEAR_CAUGHT_REP_LOSS)
        comp["has_scandal"] = True
        save_company(comp_id)
        result = f"🚨 **BỊ PHÁT HIỆN!** Tự dính scandal, mất **{SMEAR_CAUGHT_REP_LOSS}** danh tiếng!"
        color = discord.Color.red()

    embed = discord.Embed(title="🕵️ CHIẾN DỊCH BÓC PHỐT", description=result, color=color)
    embed.set_footer(text=f"Chi: {cost:,} 💰 | Tỉ lệ thành công: {success_chance}% | Hồi sau {SMEAR_COOLDOWN_HOURS}h")
    await ctx.reply(embed=embed, mention_author=False)


# ── GIÁN ĐIỆP CÔNG NGHIỆP (ăn cắp quỹ) ────────────────────────────────
@cty.command(name="giandiep")
async def giandiep(ctx, *, target_name: str):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]:
        return await ctx.reply("⚠️ Chỉ Ban Giám Đốc mới cử gián điệp!", mention_author=False)

    now = datetime.now()
    try: last = datetime.strptime(comp.get("last_spy", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)
    if now - last < timedelta(hours=SPY_COOLDOWN_HOURS):
        return await ctx.reply(f"⏳ Gián điệp hồi: <t:{int((last+timedelta(hours=SPY_COOLDOWN_HOURS)).timestamp())}:R>", mention_author=False)

    cost = 60000
    if comp.get("treasury", 0) < cost:
        return await ctx.reply(f"⚠️ Cần **{cost:,} 💰** chi phí!", mention_author=False)

    try: all_comps = list(companies_col.find())
    except Exception: all_comps = []
    target = next((c for c in all_comps if target_name.lower() in c["name"].lower()), None)
    if not target or target["_id"] == comp_id:
        return await ctx.reply("⚠️ Không tìm thấy công ty đối thủ hợp lệ!", mention_author=False)
    COMPANY_CACHE[target["_id"]] = target

    comp["treasury"] -= cost
    comp["last_spy"] = now.strftime("%Y-%m-%d %H:%M:%S")

    target_security = target.get("security_level", 1)
    success_chance = max(15, 55 - target_security * 6)

    if random.uniform(0, 100) <= success_chance:
        loot = int(target.get("treasury", 0) * random.uniform(0.05, 0.15))
        target["treasury"] = max(0, target.get("treasury", 0) - loot)
        comp["treasury"] += loot
        save_company(target["_id"])
        save_company(comp_id)
        result = f"🕵️‍♂️ **THÀNH CÔNG!** Lấy được **{loot:,} 💰** từ quỹ **{target['name']}**!"
        color = discord.Color.dark_green()
    else:
        fine = int(comp.get("treasury", 0) * ESPIONAGE_CAUGHT_FINE_MULT)
        comp["treasury"] = max(0, comp.get("treasury", 0) - fine)
        comp["reputation"] = max(0, comp.get("reputation", 100) - 15)
        comp["has_scandal"] = True
        save_company(comp_id)
        result = f"🚨 **BỊ BẮT!** Phạt **{fine:,} 💰** và dính scandal!"
        color = discord.Color.red()

    embed = discord.Embed(title="🕵️‍♂️ GIÁN ĐIỆP CÔNG NGHIỆP", description=result, color=color)
    embed.set_footer(text=f"Chi: {cost:,} 💰 | Tỉ lệ thành công: {success_chance}% | Hồi sau {SPY_COOLDOWN_HOURS}h")
    await ctx.reply(embed=embed, mention_author=False)


# ── NÂNG AN NINH (chống gián điệp / bóc phốt) ─────────────────────────
@cty.command(name="anninh")
async def anninh(ctx):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]:
        return await ctx.reply("⚠️ Chỉ Ban Giám Đốc mới nâng an ninh!", mention_author=False)
    lvl = comp.get("security_level", 1)
    if lvl >= 10:
        return await ctx.reply("⚠️ An ninh đã max cấp!", mention_author=False)
    cost = (lvl + 1) * 200000
    if comp.get("treasury", 0) < cost:
        return await ctx.reply(f"⚠️ Cần **{cost:,} 💰**!", mention_author=False)
    comp["treasury"] -= cost
    comp["security_level"] = lvl + 1
    save_company(comp_id)
    await ctx.reply(embed=discord.Embed(
        description=f"🛡️ Nâng AN NINH **Lv{lvl} → Lv{lvl+1}**! Giảm tỉ lệ bị hại từ gián điệp/bóc phốt.",
        color=discord.Color.blue()
    ), mention_author=False)


# ── CHIA CỔ TỨC ────────────────────────────────────────────────────────
@cty.command(name="cotuc")
async def cotuc(ctx, percent: int):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss":
        return await ctx.reply("⚠️ Chỉ Chủ Tịch mới chia cổ tức!", mention_author=False)
    if percent <= 0 or percent > 50:
        return await ctx.reply("⚠️ Chia từ 1-50% quỹ!", mention_author=False)

    now = datetime.now()
    try: last = datetime.strptime(comp.get("last_dividend", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)
    if now - last < timedelta(days=1):
        return await ctx.reply(f"⏳ 1 lần/ngày! Tiếp theo: <t:{int((last+timedelta(days=1)).timestamp())}:R>", mention_author=False)

    total_pay = int(comp.get("treasury", 0) * percent / 100)
    if total_pay <= 0:
        return await ctx.reply("⚠️ Quỹ không đủ để chia!", mention_author=False)

    members = comp.get("members", {})
    each = total_pay // max(1, len(members))
    comp["treasury"] -= total_pay
    comp["last_dividend"] = now.strftime("%Y-%m-%d %H:%M:%S")
    for m_id in members:
        m_data = load_user(m_id)
        m_data["money"] += each
        save_user(m_id)
    save_company(comp_id)

    await ctx.send(embed=discord.Embed(
        title="💵 CHIA CỔ TỨC",
        description=f"Chia **{percent}%** quỹ (**{total_pay:,} 💰**) cho **{len(members)}** người!\nMỗi người: **{each:,} 💰**",
        color=discord.Color.green()
    ))

@cty.command()
async def luong(ctx, amount: int):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ Chủ tịch mới được ký quỹ phát lương!", mention_author=False)
    mem_count = len(comp["members"]); total_cost = amount * mem_count
    if total_cost > comp["treasury"]: return await ctx.reply(f"Quỹ không đủ! Cần **{total_cost:,} 💰** cho {mem_count} người.", mention_author=False)
    comp["treasury"] -= total_cost
    for m_id in list(comp["members"].keys()):
        m_data = load_user(m_id); m_data["money"] += amount; save_user(m_id)
    save_company(comp_id)
    await ctx.send(embed=discord.Embed(description=f"💸 Phát **{amount:,} 💰** lương cho mỗi nhân viên!\nTổng trừ quỹ: **{total_cost:,} 💰**", color=discord.Color.green()))

@cty.command()
async def chucvu(ctx, member: discord.Member, role: str):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ Chủ tịch mới được set chức vụ!", mention_author=False)
    target_id = str(member.id)
    if target_id not in comp["members"]: return await ctx.reply("Người này không thuộc công ty.", mention_author=False)
    if target_id == user_id: return await ctx.reply("Không thể tự đổi chức của bản thân!", mention_author=False)
    if role not in ["quanly", "nhanvien"]: return await ctx.reply("Chức vụ phải là `quanly` hoặc `nhanvien`.", mention_author=False)
    comp["members"][target_id] = role; save_company(comp_id)
    await ctx.reply(f"✅ Đã đặt chức vụ {member.mention} thành **{comp['roles'][role]}**.", mention_author=False)

@cty.command()
async def doitenchuc(ctx, role: str, *, name: str):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ Chủ tịch mới được đổi tên chức vụ!", mention_author=False)
    if role not in ["boss", "quanly", "nhanvien"]: return await ctx.reply("Phải là `boss`, `quanly` hoặc `nhanvien`.", mention_author=False)
    comp["roles"][role] = name; save_company(comp_id)
    await ctx.reply(f"✅ Đổi tên `{role}` thành **{name}**.", mention_author=False)

@cty.command()
async def roi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.reply("Bạn chưa gia nhập công ty nào!", mention_author=False)
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None; save_user(user_id)
        return await ctx.reply("Công ty của bạn đã không còn tồn tại.", mention_author=False)
    my_role = comp["members"].get(user_id)
    if my_role == "boss":
        COMPANY_CACHE.pop(comp_id, None); companies_col.delete_one({"_id": comp_id})
        for m_id in list(comp["members"].keys()):
            m_data = load_user(m_id); m_data["company"] = None; save_user(m_id)
        embed_bankrupt = discord.Embed(description="🏢 Chủ tịch bỏ trốn! Công ty **PHÁ SẢN**, toàn bộ nhân sự giải tán!", color=discord.Color.red())
        embed_bankrupt.set_image(url=GIF_LINKS.get("bankrupt", ""))
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
    else:
        if user_id in comp["members"]: del comp["members"][user_id]
        user_data["company"] = None; save_user(user_id); save_company(comp_id)
        await ctx.reply(embed=discord.Embed(description="🎒 Bạn đã từ chức, thu dọn hành lý rời khỏi công ty.", color=discord.Color.dark_grey()), mention_author=False)

# =====================================================================
# HỆ THỐNG NGÂN HÀNG
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    user_data = load_user(ctx.author.id)
    embed = discord.Embed(title="🏦 NGÂN HÀNG TRUNG ƯƠNG", description="📥 `k bank gui <số / all>` | 📤 `k bank rut <số / all>` | 📈 `k bank laisuat`", color=discord.Color.blue())
    embed.add_field(name="💳 Ví", value=f"**{user_data.get('money', 0):,} 💰**", inline=True)
    embed.add_field(name="🏦 Két sắt", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    if user_data.get("loan_amount", 0) > 0:
        embed.add_field(name="⚠️ Đang nợ", value=f"**{user_data['loan_amount']:,} 💰** | `k tranno`", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@bank.command()
async def laisuat(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); bank_bal = user_data.get("bank", 0)
    if bank_bal < 50000: return await ctx.reply("⚠️ Gửi trên 50k mới có lãi suất.", mention_author=False)
    now = datetime.now()
    try: last = datetime.strptime(user_data.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)
    if now - last < timedelta(days=1):
        next_time = int((last + timedelta(days=1)).timestamp())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Quay lại: <t:{next_time}:R>", color=discord.Color.orange()), mention_author=False)
    interest = int(bank_bal * 0.001)
    user_data["bank"] += interest; user_data["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"📈 Nhận **{interest:,} 💰** lãi (0.1%).", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    try: dep = user_data["money"] if amount.lower() == "all" else int(amount)
    except ValueError: return await ctx.reply("⚠️ Nhập số hoặc `all`!")
    if dep <= 0 or dep > user_data["money"]: return await ctx.reply("⚠️ Không đủ tiền!")
    user_data["money"] -= dep; user_data["bank"] = user_data.get("bank", 0) + dep; save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Gửi **{dep:,} 💰** vào két!", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id); bb = user_data.get("bank", 0)
    try: w = bb if amount.lower() == "all" else int(amount)
    except ValueError: return await ctx.reply("⚠️ Nhập số hoặc `all`!")
    if w <= 0 or w > bb: return await ctx.reply("⚠️ Số dư không đủ!")
    user_data["bank"] -= w; user_data["money"] += w; save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Rút **{w:,} 💰** ra ví!", color=discord.Color.green()), mention_author=False)

# =====================================================================
# HỆ THỐNG NÔNG TRẠI
# =====================================================================
@bot.command(aliases=['ls'])
async def lichsu(ctx):
    history = load_user(ctx.author.id).get("history", [])
    if not history: return await ctx.reply(embed=discord.Embed(description="Chưa có lịch sử.", color=discord.Color.light_grey()))
    await ctx.reply(embed=discord.Embed(title=f"📜 LỊCH SỬ {ctx.author.name}", description="\n".join(history), color=discord.Color.blue()))

@bot.group(invoke_without_command=True, aliases=['farm'])
async def nongtrai(ctx):
    user_data = load_user(ctx.author.id)
    farm = user_data.get("farm", {"seed": None, "plant_time": None})
    embed = discord.Embed(title="🏡 NÔNG TRẠI VUI VẺ", color=discord.Color.green())
    seeds_str = "\n".join([f"`{k}`: {v['name']} | {v['cost']:,}💰 | {v['time_hours']}h" for k, v in FARM_SEEDS.items()])
    if not farm.get("seed"):
        embed.description = f"Đất trống.\n\n{seeds_str}\n\n`k farm mua <tên>` | `k farm trong <tên>`"
    else:
        si = FARM_SEEDS.get(farm["seed"])
        if si:
            ht = datetime.strptime(farm["plant_time"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=si["time_hours"])
            if datetime.now() >= ht:
                embed.description = "🌾 Chín rồi! `k farm thuhoach`"
            else:
                embed.description = f"🌱 **{si['name']}** | Thu hoạch: <t:{int(ht.timestamp())}:R>"
    await ctx.reply(embed=embed)

@nongtrai.command()
async def mua(ctx, seed: str):
    seed = seed.lower()
    if seed not in FARM_SEEDS: return await ctx.reply(f"⚠️ Các loại: {', '.join(FARM_SEEDS.keys())}")
    user_id = str(ctx.author.id); user_data = load_user(user_id); cost = FARM_SEEDS[seed]["cost"]
    if user_data.get("money", 0) < cost: return await ctx.reply(f"⚠️ Cần **{cost:,} 💰**.")
    user_data["money"] -= cost; user_data["assets"].append(f"Hạt giống {FARM_SEEDS[seed]['name']}")
    save_user(user_id); await ctx.reply(embed=discord.Embed(description=f"🛒 Mua xong! `k farm trong {seed}`", color=discord.Color.green()))

@nongtrai.command()
async def trong(ctx, seed: str):
    seed = seed.lower(); user_id = str(ctx.author.id); user_data = load_user(user_id)
    asset_name = f"Hạt giống {FARM_SEEDS.get(seed, {}).get('name', '')}"
    if asset_name not in user_data.get("assets", []): return await ctx.reply("⚠️ Không có hạt giống này!")
    if user_data.get("farm", {}).get("seed"): return await ctx.reply("⚠️ Đất đang bận!")
    user_data["assets"].remove(asset_name); user_data["farm"] = {"seed": seed, "plant_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}; save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"🌱 Gieo **{FARM_SEEDS[seed]['name']}** xuống đất.", color=discord.Color.green()))

@nongtrai.command()
async def thuhoach(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); farm = user_data.get("farm", {})
    if not farm.get("seed"): return await ctx.reply("⚠️ Đất trống!")
    si = FARM_SEEDS.get(farm["seed"])
    if not si: user_data["farm"] = {"seed": None, "plant_time": None}; save_user(user_id); return await ctx.reply("⚠️ Hạt lỗi.")
    ht = datetime.strptime(farm["plant_time"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=si["time_hours"])
    if datetime.now() < ht: return await ctx.reply(f"⏳ Chưa chín! <t:{int(ht.timestamp())}:R>")
    profit = random.randint(si["profit_min"], si["profit_max"])
    user_data["money"] += profit; user_data["farm"] = {"seed": None, "plant_time": None}; save_user(user_id)
    add_history(user_id, f"Thu hoạch {si['name']} (+{profit:,})")
    qm = update_quest_progress(user_id, "farm")
    result = f"🌾 Gặt **{si['name']}** được **{profit:,} 💰**!"
    if qm: result += f"\n\n{qm}"
    await ctx.reply(embed=discord.Embed(description=result, color=discord.Color.gold()))

# =====================================================================
# CÂU CÁ
# =====================================================================
@bot.command(aliases=['caudu', 'fish'])
async def cauca(ctx):
    user_id = str(ctx.author.id); now = datetime.now()
    if user_id in fishing_cooldowns and (now - fishing_cooldowns[user_id]).total_seconds() < 25:
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Đợi {int(25-(now-fishing_cooldowns[user_id]).total_seconds())}s!", color=discord.Color.orange()), mention_author=False)
    user_data = load_user(user_id)
    if not any("Cần Câu" in a or "Máy Câu" in a for a in user_data.get("assets", [])):
        return await ctx.reply(embed=discord.Embed(description="🎣 Cần mua **Cần Câu** trước! `k cuahang`", color=discord.Color.red()), mention_author=False)
    fishing_cooldowns[user_id] = now; bonus = get_fish_bonus(user_data)
    msg = await ctx.reply(embed=discord.Embed(description="🎣 Thả mồi...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(2)
    roll = random.uniform(0, 100); cumulative = 0; rarity = "common"
    for r, d in FISH_TABLE.items():
        cumulative += d["rate"]
        if roll <= cumulative: rarity = r; break
    fish_name, min_v, max_v = random.choice(FISH_TABLE[rarity]["pool"])
    fish_value = int(random.randint(min_v, max_v) * bonus)
    user_data["fish_count"] = user_data.get("fish_count", 0) + 1
    labels = {"common": ("🟤 PHỔ THÔNG", discord.Color.light_grey()), "rare": ("🔵 HIẾM", discord.Color.blue()), "epic": ("🟣 SỬ THI", discord.Color.purple()), "legendary": ("🟡 HUYỀN THOẠI", discord.Color.gold()), "trash": ("🗑️ RÁC", discord.Color.dark_grey())}
    label, color = labels.get(rarity, ("🟤", discord.Color.light_grey()))
    user_data["money"] = max(0, user_data.get("money", 0) + fish_value); save_user(user_id)
    add_history(user_id, f"Câu {fish_name} ({'+' if fish_value>=0 else ''}{fish_value:,})")
    qm = update_quest_progress(user_id, "fish"); na = check_achievement(user_id, user_data)
    result = f"🎣 **{fish_name}** [{label}]\n{'Bán' if fish_value>=0 else 'Chi phí'}: **{fish_value:,} 💰**"
    if qm: result += f"\n\n{qm}"
    if na: save_user(user_id); result += "\n🏅 **THÀNH TÍCH:** " + ", ".join(na)
    await msg.edit(embed=discord.Embed(title="🎣 KẾT QUẢ", description=result, color=color))

# =====================================================================
# ĐI LÀM THÊM
# =====================================================================
@bot.command(aliases=['lamviec', 'work'])
async def dilamthem(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    try: last = datetime.strptime(user_data.get("last_work", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000, 1, 1)
    if now - last < timedelta(minutes=45):
        return await ctx.reply(embed=discord.Embed(description=f"😓 Nghỉ đến <t:{int((last+timedelta(minutes=45)).timestamp())}:R>", color=discord.Color.orange()), mention_author=False)
    job = random.choice(JOBS); wage = random.randint(job["min"], job["max"])
    bad_event = None
    if random.randint(1, 100) <= 10:
        acc = random.randint(1000, max(1000, abs(wage) // 2)); wage -= acc; bad_event = f"⚠️ Sự cố! Mất **{acc:,} 💰**."
    wage = max(0, wage)
    user_data["money"] += wage; user_data["last_work"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    add_history(user_id, f"Làm {job['name']} (+{wage:,})")
    qm = update_quest_progress(user_id, "work")
    embed = discord.Embed(title="💼 NHẬN LƯƠNG!", description=f"**{job['name']}** - _{job['desc']}_\n💰 Lương: **{wage:,} 💰**", color=discord.Color.green())
    if bad_event: embed.description += f"\n\n{bad_event}"
    if qm: embed.description += f"\n\n{qm}"
    embed.set_footer(text=f"Ví: {user_data['money']:,} 💰 | CD: 45p")
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# NHIỆM VỤ, THÀNH TÍCH
# =====================================================================
@bot.command(aliases=['nhv', 'mission'])
async def nhiemvu(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    quest, is_new = get_or_assign_quest(user_data); save_user(user_id)
    if not quest: return await ctx.reply("Không có nhiệm vụ.")
    prog = user_data.get("quest_progress", 0); tgt = quest["target"]; done = prog >= tgt
    embed = discord.Embed(title="📋 NHIỆM VỤ HÀNG NGÀY", color=discord.Color.gold() if done else discord.Color.blue())
    embed.add_field(name=f"{'✅' if done else '🔄'} {quest['name']}", value=quest["desc"], inline=False)
    embed.add_field(name="Tiến độ", value=f"`{make_progress_bar(min(prog,tgt), tgt)}` {min(prog,tgt)}/{tgt}", inline=False)
    embed.add_field(name="Thưởng", value=f"**{quest['reward']:,} 💰**", inline=True)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command(aliases=['achievement', 'ach'])
async def thanhtich(ctx, member: discord.Member = None):
    target = member or ctx.author; user_data = load_user(target.id)
    ach_names = {"millionaire": "💰 Triệu Phú", "billionaire": "👑 Tỷ Phú", "level10": "⭐ Cấp 10", "level50": "🌟 Cấp 50", "pet_collector": "🐾 5 Thú Cưng", "fisher": "🎣 50 Cá", "streak7": "🔥 Streak 7", "streak30": "🌈 Streak 30"}
    achievements = user_data.get("achievements", [])
    embed = discord.Embed(title=f"🏅 THÀNH TÍCH {target.name}", color=discord.Color.gold())
    if not achievements: embed.description = "Chưa có thành tích."
    else:
        embed.add_field(name=f"Đạt được ({len(achievements)}/{len(ach_names)})", value="\n".join([f"✅ {ach_names.get(a,a)}" for a in achievements]), inline=False)
        locked = "\n".join([f"🔒 {v}" for k,v in ach_names.items() if k not in achievements])
        if locked: embed.add_field(name="Chưa đạt", value=locked, inline=False)
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# MINIGAMES
# =====================================================================
@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("bank", 0) < 200000: return await ctx.reply(embed=discord.Embed(description="⚠️ Cần gửi ít nhất **200,000 💰** trong ngân hàng!", color=discord.Color.red()), mention_author=False)
    if user_id in rob_cooldowns and (now - rob_cooldowns[user_id]).total_seconds() < 7200:
        r = int(7200 - (now - rob_cooldowns[user_id]).total_seconds())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Đang bị truy nã! {r//60}p {r%60}s nữa.", color=discord.Color.orange()), mention_author=False)
    rob_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Đang lẻn vào két sắt...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2.5)
    if random.randint(1,100) <= 20:
        loot = int(user_data["bank"] * random.uniform(0.03, 0.10)); user_data["money"] += loot; save_user(user_id)
        add_history(user_id, f"Cướp Bank +{loot:,}")
        embed = discord.Embed(title="🎉 TRÓT LỌT!", description=f"Vơ vét **{loot:,} 💰**!\n⏳ CD: 2 giờ", color=discord.Color.green()); embed.set_image(url=GIF_LINKS["rob_success"])
    else:
        fine = int(user_data["bank"] * 0.15); user_data["bank"] -= fine
        jail_time = now + timedelta(minutes=20); user_data["jail_time"] = jail_time.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
        add_history(user_id, f"Cướp Bank xịt -{fine:,}")
        embed = discord.Embed(title="🚨 BỊ TÓM!", description=f"Bị bắt! Phạt **{fine:,} 💰**.\n⛔ Tù đến: <t:{int(jail_time.timestamp())}:R>!", color=discord.Color.red()); embed.set_image(url=GIF_LINKS["rob_fail"])
    await msg.edit(embed=embed)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_id in mining_cooldowns and (now - mining_cooldowns[user_id]).total_seconds() < 60:
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Nghỉ {int(60-(now-mining_cooldowns[user_id]).total_seconds())}s!", color=discord.Color.orange()), mention_author=False)
    if "Cuốc Chim ⛏️" not in user_data.get("assets", []):
        if user_data.get("money",0) < 10000: return await ctx.reply("⚠️ Cần **10,000 💰** mua Cuốc Chim!")
        user_data["money"] -= 10000; user_data["assets"].append("Cuốc Chim ⛏️"); await ctx.send("🛒 Tự động mua **Cuốc Chim ⛏️**!")
    mining_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(description="⛏️ Đang đào...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2)
    roll = random.randint(1,100)
    if roll<=45: name, val = "Cục Đá 🪨", 0
    elif roll<=72: name, val = "Sắt Vụn 🔩", random.randint(500, 2000)
    elif roll<=90: name, val = "Thỏi Vàng 🥇", random.randint(5000, 12000)
    elif roll<=98: name, val = "Kim Cương 💎", random.randint(40000, 80000)
    else:
        pen = int(user_data["money"]*0.15); user_data["money"] -= pen; save_user(user_id)
        return await msg.edit(embed=discord.Embed(description=f"💥 **BÙMMMM!** Đào trúng bom! -{pen:,} 💰!", color=discord.Color.red()))
    user_data["money"] += val; save_user(user_id)
    if val > 0: add_history(user_id, f"Đào {name} +{val:,}")
    qm = update_quest_progress(user_id, "mine")
    result = f"⛏️ Đào được: **{name}** | Bán: **{val:,} 💰**"
    if qm: result += f"\n\n{qm}"
    await msg.edit(embed=discord.Embed(description=result, color=discord.Color.green() if val > 0 else discord.Color.light_grey()))

@bot.command()
async def vietlott(ctx, so: int, amount: str):
    if so < 0 or so > 99: return await ctx.reply("⚠️ Số 00-99!")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    msg = await ctx.reply(embed=discord.Embed(description=f"🎫 Mua vé **{so:02d}** | {bet:,} 💰 | Quay...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(3)
    kq = random.randint(0, 99)
    if so == kq:
        w = bet * 60; user_data["money"] += w; save_user(user_id); add_history(user_id, f"Trúng Vietlott +{w:,}")
        await msg.edit(embed=discord.Embed(description=f"🎉 **TRÚNG ĐỘC ĐẮC!** Kết quả: **{kq:02d}**!\n+**{w:,} 💰** (x60)!", color=discord.Color.green()))
    else:
        add_history(user_id, f"Trượt Vietlott -{bet:,}")
        await msg.edit(embed=discord.Embed(description=f"💀 **TRẬT!** Kết quả: **{kq:02d}**. Mất **{bet:,} 💰**.", color=discord.Color.red()))

@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    msg = await ctx.reply(embed=discord.Embed(description=f"🪙 Tung **{bet:,} 💰**...", color=discord.Color.gold()), mention_author=False)
    await asyncio.sleep(2)
    if random.randint(1,100) <= 48:
        user_data["money"] += bet*2; save_user(user_id); add_history(user_id, f"Tung xu Thắng +{bet:,}")
        qm = update_quest_progress(user_id, "gamble")
        result = f"🪙 **NGỬA!** +**{bet*2:,} 💰**!"
        if qm: result += f"\n\n{qm}"
        await msg.edit(embed=discord.Embed(description=result, color=discord.Color.green()))
    else:
        add_history(user_id, f"Tung xu Thua -{bet:,}")
        qm = update_quest_progress(user_id, "gamble")
        result = f"🪙 **SẤP!** Mất **{bet:,} 💰**."
        if qm: result += f"\n\n{qm}"
        await msg.edit(embed=discord.Embed(description=result, color=discord.Color.red()))

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    cm = {"tai": "tai", "tài": "tai", "xiu": "xiu", "xỉu": "xiu"}
    ch = choice.lower()
    if ch not in cm: return await ctx.reply("⚠️ `k taixiu tai <tiền>` hoặc `xiu`.")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    msg = await ctx.reply(embed=discord.Embed(title="🎲 TÀI XỈU", description=f"Cược **{bet:,}** vào **{cm[ch].upper()}**. Lắc...", color=discord.Color.gold()), mention_author=False)
    await asyncio.sleep(2.5)
    d1,d2,d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6); total = d1+d2+d3
    rt = "xiu" if total <= 10 else "tai"
    embed = discord.Embed(title="🎲 KẾT QUẢ")
    if cm[ch] == rt:
        if d1==d2==d3: w = bet*5; txt = f"🔥 **BÃO x5!** +{w:,} 💰!"
        else: w = bet*2; txt = f"✅ **THẮNG!** +{w:,} 💰!"
        user_data["money"] += w; embed.color = discord.Color.green(); add_history(user_id, f"TaiXiu +{w-bet:,}")
    else: w = 0; txt = f"💀 **THUA!** Mất {bet:,} 💰."; embed.color = discord.Color.red(); add_history(user_id, f"TaiXiu -{bet:,}")
    save_user(user_id); qm = update_quest_progress(user_id, "gamble")
    embed.description = f"**[{d1}|{d2}|{d3}]** Tổng {total} - **{rt.upper()}**\n\n{txt}"
    if qm: embed.description += f"\n\n{qm}"
    await msg.edit(embed=embed)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    vc = {"bau":"🥒","bầu":"🥒","cua":"🦀","tom":"🦐","tôm":"🦐","ca":"🐟","cá":"🐟","ga":"🐓","gà":"🐓","huou":"🦌","hươu":"🦌"}
    ch = choice.lower()
    if ch not in vc: return await ctx.reply("⚠️ Cửa: `bau, cua, tom, ca, ga, huou`.")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    msg = await ctx.reply(embed=discord.Embed(title="🎲 BẦU CUA", description=f"Cược **{bet:,}** vào **{vc[ch]}**.", color=discord.Color.gold()), mention_author=False)
    await asyncio.sleep(2.5)
    faces = ["🥒","🦀","🦐","🐟","🐓","🦌"]; dice = [random.choice(faces) for _ in range(3)]; mc = dice.count(vc[ch])
    embed = discord.Embed(title="🎲 KẾT QUẢ")
    if mc > 0:
        w = bet + bet*mc; user_data["money"] += w; embed.color = discord.Color.green(); txt = f"🎉 **TRÚNG {mc} Ô!** +{w:,} 💰"; add_history(user_id, f"BauCua +{w-bet:,}")
    else: embed.color = discord.Color.red(); txt = f"💀 **TRẬT!** Mất {bet:,} 💰."; add_history(user_id, f"BauCua -{bet:,}")
    save_user(user_id); qm = update_quest_progress(user_id, "gamble")
    embed.description = f"**[{dice[0]}|{dice[1]}|{dice[2]}]**\n\n{txt}"
    if qm: embed.description += f"\n\n{qm}"
    await msg.edit(embed=embed)

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    items = ["🍒","🍋","🍉","🔔","💎","👑"]
    slots = [random.choice(items) for _ in range(3)]
    embed = discord.Embed(title="🎰 MÁY XÈNG", color=discord.Color.gold())
    msg = await ctx.reply(embed=embed, mention_author=False)
    for _ in range(3): embed.description = f"**[{random.choice(items)}|{random.choice(items)}|{random.choice(items)}]**\n🔄 Quay..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    if slots[0]==slots[1]==slots[2]:
        if slots[0]=="👑": w = bet*40
        elif slots[0]=="💎": w = bet*15
        else: w = bet*8
        txt = f"🔥 **JACKPOT!!! 3x{slots[0]}** +{w:,} 💰!"; user_data["money"] += w; add_history(user_id, f"Slot JACKPOT +{w:,}")
    elif len(set(slots)) < 3:
        w = int(bet*1.5); txt = f"🎉 **Thắng nhỏ!** +{w:,} 💰."; user_data["money"] += w; add_history(user_id, f"Slot +{w-bet:,}")
    else: w = 0; txt = f"💀 **TOANG!** Mất {bet:,} 💰."; add_history(user_id, f"Slot -{bet:,}")
    save_user(user_id); qm = update_quest_progress(user_id, "gamble")
    embed.description = f"**[{slots[0]}|{slots[1]}|{slots[2]}]**\n\n{txt}"
    if qm: embed.description += f"\n\n{qm}"
    embed.set_footer(text=f"Ví: {user_data['money']:,} 💰")
    await msg.edit(embed=embed)

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id); now = datetime.now()
    if user_id in gacha_cooldowns and (now - gacha_cooldowns[user_id]).total_seconds() < 300:
        r = int(300-(now-gacha_cooldowns[user_id]).total_seconds())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Ủ trứng thêm **{r//60}p {r%60}s**!", color=discord.Color.orange()), mention_author=False)
    user_data = load_user(user_id); cost = 50000
    if user_data.get("money",0) < cost: return await ctx.reply(f"⚠️ Cần **{cost:,} 💰**.")
    user_data["money"] -= cost; gacha_cooldowns[user_id] = now; save_user(user_id)
    msg = await ctx.reply(embed=discord.Embed(title="🥚 ĐẬP TRỨNG GACHA", description="Đang đập...", color=discord.Color.orange()), mention_author=False)
    await asyncio.sleep(1.5)
    roll = random.uniform(0,100)
    if roll<=0.5: rarity, title, color = "mythic", "🌌 THẦN THOẠI", discord.Color.dark_purple()
    elif roll<=3.0: rarity, title, color = "legendary", "👑 HUYỀN THOẠI", discord.Color.gold()
    elif roll<=10.0: rarity, title, color = "epic", "🔮 SỬ THI", discord.Color.magenta()
    elif roll<=30.0: rarity, title, color = "rare", "💎 HIẾM", discord.Color.blue()
    else: rarity, title, color = "common", "🪵 PHỔ THÔNG", discord.Color.light_grey()
    pet = random.choice(PET_RATES[rarity]["pool"]); user_data["pets"][pet] = user_data["pets"].get(pet,0)+1; save_user(user_id)
    add_history(user_id, f"Gacha {pet} (-{cost:,})")
    qm = update_quest_progress(user_id, "gacha"); na = check_achievement(user_id, user_data)
    result = f"Nhận: **{pet}**!\n⏳ CD: 5 phút"
    if qm: result += f"\n\n{qm}"
    if na: save_user(user_id); result += "\n🏅 **THÀNH TÍCH:** " + ", ".join(na)
    await msg.edit(embed=discord.Embed(title=f"🎉 {title}!", description=result, color=color))

# =====================================================================
# LỆNH INFO & GIAO DỊCH
# =====================================================================
# =====================================================================
# HELP MENU - PHÂN TRANG (Next/Prev)
# =====================================================================
HELP_PAGES = [
    {
        "title": "🏦 KINH TẾ CƠ BẢN",
        "color": discord.Color.green(),
        "desc": (
            "`k rank [@user]` — Xem căn cước, tài sản, level\n"
            "`k bank` — Mở ngân hàng (gửi/rút/lãi suất)\n"
            "`k bank gui <số/all>` — Gửi tiền vào ngân hàng\n"
            "`k bank rut <số/all>` — Rút tiền ra ví\n"
            "`k bank laisuat` — Nhận lãi suất hàng ngày (0.1%)\n"
            "`k give @user <tiền>` — Chuyển khoản cho người khác\n"
            "`k daily` — Điểm danh nhận lương + streak\n"
            "`k lixi` — Lì xì free (CD 12h)\n"
            "`k vay <tiền>` — Vay ngân hàng (lãi 20%, hạn 3 ngày)\n"
            "`k tranno` — Trả nợ ngân hàng\n"
            "`k top [tien/level/ca]` — Bảng xếp hạng\n"
            "`k lichsu` (`ls`) — Lịch sử giao dịch của bạn\n"
            "`k nhiemvu` — Xem nhiệm vụ hàng ngày\n"
            "`k thanhtich [@user]` — Xem thành tích đã đạt\n"
            "`k marry @user` — Cầu hôn (phí 1,000,000 💰)\n"
            "`k lyhon` — Ly hôn (phí 500,000 💰)\n"
            "`k dilamthem` (`work`) — Đi làm thêm (CD 45p)"
        ),
    },
    {
        "title": "📈 CHỨNG KHOÁN (k ck / trade)",
        "color": discord.Color.blue(),
        "desc": (
            "`k ck` — Xem bảng giá thị trường\n"
            "`k ck buy <MÃ> <SL>` — Mua theo giá thị trường\n"
            "`k ck sell <MÃ> <SL/all>` — Bán theo giá thị trường\n"
            "`k ck order <MÃ> buy/sell <SL> <GIÁ>` — Đặt lệnh chờ khớp giá\n"
            "`k ck orders` — Xem lệnh chờ khớp\n"
            "`k ck cancel <ID>` — Hủy lệnh chờ\n"
            "`k ck sl <MÃ> <GIÁ>` — Đặt Stop-Loss (cắt lỗ tự động)\n"
            "`k ck tp <MÃ> <GIÁ>` — Đặt Take-Profit (chốt lời tự động)\n"
            "`k ck margin <MÃ> <SL>` — Mua ký quỹ (đòn bẩy x2)\n"
            "`k ck short <MÃ> <SL>` — Bán khống (lãi khi giá xuống)\n"
            "`k ck covershort <MÃ> <SL>` — Đóng vị thế bán khống\n"
            "`k ck port [@user]` — Xem portfolio đầu tư\n"
            "`k ck chart <MÃ>` — Biểu đồ giá 6 giờ qua\n"
            "`k ck ipo` — Niêm yết công ty lên sàn (Chủ tịch)\n\n"
            "💸 Spread 0.1% + Thuế bán 0.1% | ⏳ Cooldown 10 phút/lệnh\n"
            "⚡ Cầu dao tự động: dừng nếu giá biến động >7%/phiên"
        ),
    },
    {
        "title": "🎮 CASINO (cược tối đa 300,000 💰, CD 6s)",
        "color": discord.Color.gold(),
        "desc": (
            "`k coin <tiền/all>` — Tung xu\n"
            "`k taixiu tai/xiu <tiền>` — Tài xỉu (3 xí ngầu)\n"
            "`k baucua <cửa> <tiền>` — Bầu cua (bau/cua/tom/ca/ga/huou)\n"
            "`k mayxeng <tiền>` (`nohu`/`slot`) — Máy xèng\n"
            "`k vietlott <số 00-99> <tiền>` — Vé số x60\n"
            "`k blackjack <tiền>` (`bj`/`21`) — Blackjack có nút bấm\n"
            "`k vecao <tiền>` (`scratch`) — Vé cào 9 ô"
        ),
    },
    {
        "title": "🎁 PHÚC LỢI & MAY MẮN",
        "color": discord.Color.purple(),
        "desc": (
            "`k vongquay` (`spin`/`wheel`) — Vòng quay free, hồi 20h\n"
            "`k gacha` — Đập trứng thú cưng (CD 5p, phí 50,000 💰)\n"
            "`k cuopnganhang` (`cuop`) — Cướp ngân hàng (CD 2h, rủi ro tù)"
        ),
    },
    {
        "title": "🌾 SINH HOẠT & NÔNG TRẠI",
        "color": discord.Color.dark_green(),
        "desc": (
            "`k cauca` (`fish`) — Câu cá (CD 25s, cần Cần Câu)\n"
            "`k daovang` (`mine`) — Đào vàng (CD 60s)\n"
            "`k farm` — Xem nông trại\n"
            "`k farm mua <hạt>` — Mua hạt giống\n"
            "`k farm trong <hạt>` — Gieo hạt\n"
            "`k farm thuhoach` — Thu hoạch\n"
            "`k gym` — Xem phòng gym\n"
            "`k gym nangcap` — Nâng cấp Gym (+5% ATK Duel)\n"
            "`k gym tap` — Tập gym nhận XP\n"
            "`k phai` — Đi thám hiểm AFK (4h/8h/12h)\n"
            "`k cuahang` (`shop`) — Mua nhà/xe/danh hiệu/cần câu\n"
            "`k choden` (`ban`/`sell`) — Cầm đồ / bán thú cưng"
        ),
    },
    {
        "title": "⚔️ PK & MINIGAME",
        "color": discord.Color.red(),
        "desc": (
            "`k pk @user <tiền/all>` (`ott`) — Gạ kèo Oẳn Tù Tì\n"
            "`k nhansinh` (`mophong`) — Mô phỏng nhân sinh (vé 500 💰)"
        ),
    },
    {
        "title": "🏢 CÔNG TY (k cty / congty)",
        "color": discord.Color.dark_gold(),
        "desc": (
            "`k cty tao <tên>` — Thành lập công ty (phí 500,000 💰)\n"
            "`k cty` — Xem bảng điều khiển công ty\n"
            "`k cty gop <tiền>` — Góp quỹ công ty\n"
            "`k cty thulai` — Thu lãi quỹ (1 lần/ngày)\n"
            "`k cty dinhchinh` — Xử lý scandal, hồi danh tiếng\n"
            "`k cty nangcap cong/thu <số lv>` — Nâng cấp Công/Thủ\n"
            "`k cty tuyen @user` — Tuyển nhân viên (GĐ+)\n"
            "`k cty duoi @user` — Sa thải nhân viên (GĐ+)\n"
            "`k cty luong <tiền>` — Phát lương toàn công ty (Chủ tịch)\n"
            "`k cty chucvu @user <role>` — Đặt chức vụ (Chủ tịch)\n"
            "`k cty doitenchuc <role> <tên>` — Đổi tên chức vụ\n"
            "`k cty roi` — Rời/giải tán công ty"
        ),
    },
    {
        "title": "⚔️ ĐẠI CHIẾN CÔNG TY (k daichien / dc / war)",
        "color": discord.Color.dark_red(),
        "desc": (
            "`k daichien` — Bảng xếp hạng + cách chơi\n"
            "`k daichien tan <tên cty>` — Thách đấu công ty khác\n"
            "`k daichien info` — Thông tin sức mạnh công ty bạn\n"
            "`k daichien lichsu` — Lịch sử trận đánh\n\n"
            "💡 3 vòng, mỗi vòng chọn 1 trong 5 kỹ năng counter nhau.\n"
            "Thắng: cướp 12% quỹ đối phương + 15 danh tiếng.\n"
            "Thua: -20 danh tiếng, có thể dính scandal.\n"
            "⏳ Cooldown 6 giờ / lần tấn công."
        ),
    },
    {
        "title": "🌸 KALLEN FANTASY (k kallen / kf)",
        "color": discord.Color.magenta(),
        "desc": (
            "`k kallen` — Menu chính, xem tiến độ & vé\n"
            "`k kallen choi` — Chọn nhân vật & chapter để chiến đấu\n"
            "`k kallen muave [số lượng]` — Mua vé (30,000 💰/vé)\n"
            "`k kallen nhanvat` — Xem danh sách nhân vật & kỹ năng\n"
            "`k kallen mokuyen <tên>` — Mở khóa nhân vật bằng vật phẩm\n"
            "`k kallen inventory` (`inv`) — Xem túi đồ Kallen Fantasy\n"
            "`k kallen bancuahang` — Bán vật phẩm KF lấy tiền\n"
            "`k kallen story <chương>` — Đọc lại cốt truyện\n\n"
            "📖 6 Chapter (1 ẩn), mỗi Chapter có nhiều Wave + Boss riêng."
        ),
    },
]


class HelpPaginatorView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=120)
        self.author = author
        self.page = 0
        self._update_buttons()

    def _update_buttons(self):
        self.btn_first.disabled = self.page <= 0
        self.btn_prev.disabled = self.page <= 0
        self.btn_next.disabled = self.page >= len(HELP_PAGES) - 1
        self.btn_last.disabled = self.page >= len(HELP_PAGES) - 1
        self.btn_page.label = f"{self.page + 1}/{len(HELP_PAGES)}"

    def make_embed(self):
        data = HELP_PAGES[self.page]
        embed = discord.Embed(
            title=f"📚 {data['title']}",
            description=data["desc"],
            color=data["color"]
        )
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        embed.set_footer(text=f"Trang {self.page + 1}/{len(HELP_PAGES)} | Tiền tố lệnh: k")
        return embed

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.secondary)
    async def btn_first(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="◀ Trước", style=discord.ButtonStyle.primary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def btn_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Sau ▶", style=discord.ButtonStyle.primary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(HELP_PAGES) - 1:
            self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary)
    async def btn_last(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = len(HELP_PAGES) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


@bot.command()
async def help(ctx):
    view = HelpPaginatorView(ctx.author)
    await ctx.reply(embed=view.make_embed(), view=view, mention_author=False)

@bot.command()
async def rank(ctx, member: discord.Member = None):
    target = member or ctx.author; user_data = load_user(target.id)
    lv = user_data.get("level",1); xp = user_data.get("xp",0); money = user_data.get("money",0)
    bank_bal = user_data.get("bank",0); stock_val = sum(get_stock_sell_price(c)*q for c,q in user_data.get("stocks",{}).items())
    total = money + bank_bal + stock_val
    embed = discord.Embed(title=f"💳 CĂN CƯỚC: {target.name}", color=discord.Color.gold() if total > 1000000 else discord.Color.teal())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp", value=f"**LV {lv}**", inline=True)
    embed.add_field(name="💰 Ví", value=f"**{money:,} 💰**", inline=True)
    embed.add_field(name="🏦 NH", value=f"**{bank_bal:,} 💰**", inline=True)
    embed.add_field(name="📈 CK", value=f"**{stock_val:,} 💰**", inline=True)
    embed.add_field(name="💎 Tổng", value=f"**{total:,} 💰**", inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{user_data.get('streak',0)} ngày**", inline=True)
    if user_data.get("loan_amount",0) > 0: embed.add_field(name="⚠️ Đang nợ", value=f"**{user_data['loan_amount']:,} 💰**", inline=True)
    if user_data.get("spouse"):
        try: sname = (await bot.fetch_user(int(user_data["spouse"]))).name
        except Exception: sname = "???"
        embed.add_field(name="💍 Vợ/Chồng", value=f"**{sname}**", inline=True)
    embed.add_field(name="✨ XP", value=f"`{make_progress_bar(xp, lv*100)}`\n{xp}/{lv*100} XP", inline=False)
    embed.add_field(name="💪 Gym", value=f"Lv{user_data.get('gym_level',0)}", inline=True)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx, category: str = "tien"):
    try: all_users = list(users_col.find())
    except Exception: return await ctx.reply("⚠️ DB lỗi!")
    if category.lower() in ["level","cap"]:
        dl = sorted([(d["_id"], d.get("level",1), d.get("xp",0)) for d in all_users], key=lambda x:(x[1],x[2]), reverse=True)
        title = "🌟 TOP CẤP"; fmt = lambda i,u,*a: f"Lv{a[0]} ({a[1]} XP)"
    elif category.lower() in ["ca","fish"]:
        dl = sorted([(d["_id"], d.get("fish_count",0)) for d in all_users], key=lambda x:x[1], reverse=True)
        title = "🎣 TOP NGƯ DÂN"; fmt = lambda i,u,*a: f"{a[0]} cá"
    else:
        dl = sorted([(d["_id"], d.get("money",0)+d.get("bank",0)) for d in all_users], key=lambda x:x[1], reverse=True)
        title = "🏆 BẢNG VÀNG"; fmt = lambda i,u,*a: f"{a[0]:,} 💰"
    desc = ""
    for idx, data in enumerate(dl[:10]):
        uid = data[0]; rest = data[1:]
        user = bot.get_user(int(uid))
        try:
            if not user: user = await bot.fetch_user(int(uid))
        except Exception: pass
        name = user.name if user else f"Ẩn#{uid[-4:]}"
        icon = "🥇" if idx==0 else "🥈" if idx==1 else "🥉" if idx==2 else f"**#{idx+1}**"
        desc += f"{icon} **{name}** ━ {fmt(idx, uid, *rest)}\n\n"
    await ctx.send(embed=discord.Embed(title=title, description=desc, color=discord.Color.gold()))

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_daily"):
        try: ld = datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S")
        except Exception: ld = datetime(2000,1,1)
        if now - ld < timedelta(days=1):
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Lương tiếp: <t:{int((ld+timedelta(days=1)).timestamp())}:R>.", color=discord.Color.orange()), mention_author=False)
        user_data["streak"] = user_data.get("streak",0)+1 if now-ld < timedelta(days=2) else 1
    else: user_data["streak"] = 1
    streak = user_data.get("streak",1); base = 500; bonus = min(streak*50, 2500); total = base+bonus
    # Kiểm tra nợ quá hạn
    if user_data.get("loan_due"):
        try:
            due = datetime.strptime(user_data["loan_due"], "%Y-%m-%d %H:%M:%S")
            if now > due and user_data.get("loan_amount",0) > 0:
                penalty = int((user_data.get("money",0)+user_data.get("bank",0)) * 0.3)
                user_data["money"] = max(0, user_data.get("money",0) - penalty)
                user_data["bank"] = max(0, user_data.get("bank",0) - max(0, penalty - user_data.get("money",0)))
                user_data["loan_amount"] = 0; user_data["loan_due"] = None
                await ctx.send(embed=discord.Embed(description=f"🦹 **GIANG HỒ ĐẾN ĐÒI NỢ!** Mất **{penalty:,} 💰** (30% tài sản)!", color=discord.Color.dark_red()))
        except Exception: pass
    user_data["money"] += total; user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    na = check_achievement(user_id, user_data); save_user(user_id)
    embed = discord.Embed(title="🎁 ĐIỂM DANH", description=f"Nhận **{total:,} 💰**!\n🔥 Streak: **{streak} ngày** (+{bonus:,} bonus)\n💳 Ví: **{user_data['money']:,} 💰**", color=discord.Color.green())
    if na: embed.description += "\n🏅 " + ", ".join(na)
    embed.set_thumbnail(url=GIF_LINKS["daily"])
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def lixi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    try: last = datetime.strptime(user_data.get("last_lixi","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception: last = datetime(2000,1,1)
    if now - last < timedelta(hours=12):
        return await ctx.reply(embed=discord.Embed(description=f"🧧 Lì xì tiếp: <t:{int((last+timedelta(hours=12)).timestamp())}:R>.", color=discord.Color.orange()), mention_author=False)
    tien = random.randint(500, 5000); user_data["money"] += tien; user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"🧧 Lì xì **{tien:,} 💰**! Ví: **{user_data['money']:,} 💰**", color=discord.Color.red()), mention_author=False)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    ng = str(ctx.author.id); nn = str(member.id); gd = load_user(ng); nd = load_user(nn)
    if amount <= 0 or gd.get("money",0) < amount or ng == nn: return await ctx.reply("⚠️ Giao dịch lỗi.", mention_author=False)
    gd["money"] -= amount; nd["money"] += amount; save_user(ng); save_user(nn)
    add_history(ng, f"Chuyển {member.name} -{amount:,}"); add_history(nn, f"Nhận {ctx.author.name} +{amount:,}")
    qm = update_quest_progress(ng, "give")
    embed = discord.Embed(title="💸 CHUYỂN KHOẢN", description=f"{ctx.author.mention} → {member.mention}: **{amount:,} 💰**!", color=discord.Color.green())
    if qm: embed.description += f"\n\n{qm}"
    await ctx.send(embed=embed)

@bot.command(aliases=['shop'])
async def cuahang(ctx):
    await ctx.send(embed=discord.Embed(title="🏪 ĐẠI SIÊU THỊ", color=discord.Color.brand_green()), view=ShopCategoryMenu(ctx.author))

@bot.command(aliases=['ban', 'sell'])
async def choden(ctx):
    await ctx.send(embed=discord.Embed(title="⚖️ CHỢ ĐEN CẦM ĐỒ", color=discord.Color.dark_orange()), view=SellCategoryMenu(ctx.author))

@bot.command()
async def phai(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); exp_end_str = user_data.get("exp_end")
    if exp_end_str:
        try: end = datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S")
        except Exception: end = datetime.now()
        if datetime.now() >= end:
            r = user_data.get("exp_reward",500); user_data["money"] += r
            user_data.pop("exp_end",None); user_data.pop("exp_reward",None); save_user(user_id)
            return await ctx.reply(embed=discord.Embed(title="🎉 TRỞ VỀ!", description=f"Thu hoạch **{r:,} 💰**!", color=discord.Color.gold()), mention_author=False)
        tl = end - datetime.now(); h,r2 = divmod(int(tl.total_seconds()), 3600); m,_ = divmod(r2, 60)
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Đang khám phá! Còn **{h}h {m}m**.", color=discord.Color.orange()), mention_author=False)
    await ctx.send(embed=discord.Embed(title="⛺ THÁM HIỂM AFK", description="Gửi nhân vật đi treo máy!\n\n👇 **CHỌN KHU VỰC**", color=discord.Color.dark_green()), view=ExpView(ctx.author))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id); now = datetime.now()
    if user_id in dang_choi_nhansinh: return await ctx.reply("⏳ Đang trong một kiếp luân hồi!")
    if user_id in nhansinh_cooldowns and (now-nhansinh_cooldowns[user_id]).total_seconds() < 5: return await ctx.reply("⏳ Từ từ đã!")
    user_data = load_user(user_id)
    if user_data.get("money",0) < 500: return await ctx.reply("⚠️ Vé luân hồi **500 💰**.")
    user_data["money"] -= 500; nhansinh_cooldowns[user_id] = now; dang_choi_nhansinh.append(user_id); save_user(user_id)
    stats = {"may_man": random.randint(1,10)}; view = NhanSinhGameView(ctx.author, stats)
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.teal())
    embed.add_field(name="🍀 May mắn", value=f"**{stats['may_man']}/10**", inline=False)
    embed.add_field(name="📜 Khởi đầu", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Ngã rẽ tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    await ctx.reply(embed=embed, view=view, mention_author=False)

@bot.command(aliases=['ott'])
async def pk(ctx, member: discord.Member, amount: str):
    if member.bot or member.id == ctx.author.id: return await ctx.reply("⚠️ Không được!")
    user_data = load_user(ctx.author.id)
    try: bet = min(user_data.get("money",0),300000) if amount.lower()=="all" else int(amount)
    except ValueError: return await ctx.reply("⚠️ Nhập số hoặc `all`!")
    if bet <= 0 or bet > user_data.get("money",0): return await ctx.reply(f"⚠️ Không đủ tiền! Có {user_data.get('money',0):,}")
    if bet > 300000: return await ctx.reply("⚠️ Tối đa 300k!")
    embed = discord.Embed(title="⚔️ GẠ KÈO OẲN TÙ TÌ", description=f"{ctx.author.mention} thách {member.mention}!\nCược: **{bet:,} 💰**.", color=discord.Color.red())
    await ctx.send(f"{member.mention}", embed=embed, view=SoloOTTAccept(ctx.author, member, bet))

@bot.command()
async def marry(ctx, member: discord.Member):
    if member.bot or member.id == ctx.author.id: return await ctx.reply("⚠️ Không được!")
    sd = load_user(ctx.author.id)
    if sd.get("spouse"): return await ctx.reply("⚠️ Đã kết hôn rồi!")
    if load_user(member.id).get("spouse"): return await ctx.reply(f"⚠️ {member.name} đã có người yêu!")
    if sd.get("money",0) < 1000000: return await ctx.reply(f"⚠️ Lễ cưới cần **1,000,000 💰**.")
    embed = discord.Embed(title="💍 LỜI CẦU HÔN", description=f"💕 {ctx.author.mention} cầu hôn {member.mention}!\n\n💒 Lễ cưới trị giá **1,000,000 💰**!", color=discord.Color.pink())
    embed.set_image(url=GIF_LINKS["marry"])
    await ctx.send(f"{member.mention}", embed=embed, view=MarryAccept(ctx.author, member))

@bot.command()
async def lyhon(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    if not user_data.get("spouse"):
        return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn chưa kết hôn với ai!", color=discord.Color.red()), mention_author=False)
    
    cost = 500000
    if user_data.get("money", 0) < cost:
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ Phí ly hôn là **{cost:,} 💰**.", color=discord.Color.red()), mention_author=False)
    
    spouse_id = user_data["spouse"]
    spouse_data = load_user(spouse_id)
    
    user_data["money"] -= cost
    user_data["spouse"] = None
    spouse_data["spouse"] = None
    
    save_user(user_id)
    save_user(spouse_id)
    
    await ctx.reply(embed=discord.Embed(title="💔 LY HÔN", description=f"💔 Bạn đã nộp đơn ly hôn và mất **{cost:,} 💰** phí luật sư.\nMong bạn sẽ tìm được hạnh phúc mới!", color=discord.Color.dark_grey()), mention_author=False)

# =====================================================================
# HỆ THỐNG SỰ KIỆN
# =====================================================================
@bot.event
async def on_message(message):
    if message.author.bot: return

    # ═══════════════════════════════════════════
    # AI TRẢ LỜI KHI BỊ TAG
    # ═══════════════════════════════════════════
    if bot.user in message.mentions and not message.mention_everyone:
        question = message.content
        for mention in message.mentions:
            question = question.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        question = question.strip()

        if question:
            uid_check = str(message.author.id)
            now_check = datetime.now()
            if uid_check in ai_cooldowns:
                diff = (now_check - ai_cooldowns[uid_check]).total_seconds()
                if diff < AI_COOLDOWN_SECONDS:
                    await message.reply(
                        embed=discord.Embed(
                            description=f"⏳ Đợi {int(AI_COOLDOWN_SECONDS - diff)}s nữa rồi hỏi tiếp nhé!",
                            color=discord.Color.orange()
                        ),
                        mention_author=False
                    )
                    return

            ai_cooldowns[uid_check] = now_check
            async with message.channel.typing():
                reply_text = await get_ai_reply(question, message.author.display_name)

            embed = discord.Embed(description=reply_text[:4000], color=discord.Color.blurple())
            embed.set_author(name=f"🤖 Trả lời {message.author.display_name}", icon_url=bot.user.display_avatar.url)
            try:
                await message.reply(embed=embed, mention_author=False)
            except Exception as e:
                print(f"[WARN] Không gửi được AI reply: {e}")
            return

    user_id = str(message.author.id)
    
    # FIX: luôn process commands TRƯỚC, kể cả người ở tù
    # Người ở tù vẫn được check jail trong global_check
    
    user_data = load_user(user_id)
    
    # FIX: wrap XP/level-up trong try-except để không làm crash on_message
    try:
        if not (user_data.get("jail_time") and datetime.now() < datetime.strptime(user_data.get("jail_time", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")):
            user_data["xp"] += random.randint(3, 10)
            max_xp_required = user_data.get("level", 1) * 100
            
            if user_data["xp"] >= max_xp_required:
                user_data["xp"] -= max_xp_required; user_data["level"] += 1
                reward = user_data["level"] * 100
                user_data["money"] += reward
                add_history(user_id, f"Thăng cấp Lv{user_data['level']} (+{reward:,} 💰)")
                
                new_achievements = check_achievement(user_id, user_data)
                save_user(user_id)
                
                try: 
                    level_msg = f"🎉 **{message.author.mention}** đã đột phá lên **Cấp {user_data['level']}**!\nThưởng: **{reward:,} 💰**"
                    if new_achievements: level_msg += f"\n🏅 **THÀNH TÍCH MỚI:** " + ", ".join(new_achievements)
                    await message.channel.send(embed=discord.Embed(description=level_msg, color=discord.Color.gold()))
                except Exception: pass
            else:
                save_user(user_id)
    except Exception as e:
        print(f"[WARN] on_message XP error for {user_id}: {e}")
        try:
            save_user(user_id)
        except Exception:
            pass
            
    await bot.process_commands(message)

@bot.event
async def on_ready(): 
    print('================================================')
    print(f'>>> BOT {bot.user} ĐÃ SẴN SÀNG!')
    print('>>> VERSION 7.1 - PATCHED & BALANCED')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="k help | Bot 7.1 Patched"))

# =====================================================================
# LỆNH ADMIN
# =====================================================================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    server_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]: del CONFIG_CACHE[server_id]["allowed_channels"]
        return await ctx.send(embed=discord.Embed(description="✅ Đã gỡ bỏ giới hạn kênh.", color=discord.Color.green()))
    mentions = ctx.message.channel_mentions
    if not mentions: return await ctx.send(embed=discord.Embed(description="⚠️ VD: `k setup #chat`", color=discord.Color.red()))
    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids
    await ctx.send(embed=discord.Embed(description=f"✅ Bot chỉ nhận lệnh tại: {', '.join(c.mention for c in mentions)}", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount > 0: 
        user_id = str(member.id); user_data = load_user(user_id)
        user_data["money"] += amount; save_user(user_id)
        add_history(user_id, f"Được Admin bơm (+{amount:,} 💰)")
        await ctx.send(embed=discord.Embed(description=f"✅ Bơm **{amount:,} 💰** cho {member.mention}!", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount > 0: 
        user_id = str(member.id); user_data = load_user(user_id)
        user_data["money"] -= amount; save_user(user_id)
        await ctx.send(embed=discord.Embed(description=f"⚖️ Tước đoạt **{amount:,} 💰** từ {member.mention}!", color=discord.Color.red()))

@bot.command()
@commands.has_permissions(administrator=True)
async def resetjail(ctx, member: discord.Member):
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["jail_time"] = None
    save_user(user_id)
    await ctx.send(embed=discord.Embed(description=f"✅ Đã thả {member.mention} ra khỏi tù!", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True)
async def giveall(ctx, amount: int):
    if amount <= 0 or amount > 10000:
        return await ctx.send(embed=discord.Embed(description="⚠️ Giveall tối đa 10,000 💰!", color=discord.Color.red()))
    count = 0
    for member in ctx.guild.members:
        if not member.bot:
            user_data = load_user(member.id)
            user_data["money"] += amount
            save_user(member.id)
            count += 1
    await ctx.send(embed=discord.Embed(description=f"✅ Đã bơm **{amount:,} 💰** cho **{count}** thành viên!", color=discord.Color.green()))
# =====================================================================
# HỆ THỐNG ĐẠI CHIẾN CÔNG TY - v1.0
# Dán đoạn code này vào bot.py, TRƯỚC dòng keep_alive()
# =====================================================================

import asyncio
import random
from datetime import datetime, timedelta
import discord
from discord.ext import commands

# Cooldown đại chiến: mỗi công ty chỉ được tấn công 1 lần / 6 giờ
daichien_cooldowns = {}   # {comp_id: datetime}
daichien_defense_log = {} # {comp_id: [log entries]}

# ── Bảng kỹ năng chiến đấu ──────────────────────────────────────────
# Mỗi vòng 1 bên chọn 1 kỹ năng (ẩn), reveal cùng lúc
SKILLS = {
    "tan_cong":  {"name": "⚔️  Tấn Công",   "emoji": "⚔️",  "beats": "phong_thu",  "bonus_atk": 1.4, "bonus_def": 1.0, "desc": "Dồn lực đánh thẳng"},
    "phong_thu": {"name": "🛡️  Phòng Thủ",  "emoji": "🛡️",  "beats": "phan_cong",  "bonus_atk": 0.7, "bonus_def": 1.6, "desc": "Lập thế thủ chắc"},
    "phan_cong": {"name": "🔄  Phản Công",   "emoji": "🔄",  "beats": "tan_cong",   "bonus_atk": 1.2, "bonus_def": 1.2, "desc": "Chờ đòn rồi trả"},
    "do_bo":     {"name": "🎯  Đổ Bộ",       "emoji": "🎯",  "beats": None,          "bonus_atk": 1.8, "bonus_def": 0.5, "desc": "All-in mạo hiểm"},
    "mai_phuc":  {"name": "🌑  Mai Phục",    "emoji": "🌑",  "beats": "do_bo",       "bonus_atk": 1.5, "bonus_def": 0.9, "desc": "Bẫy đòn đổ bộ"},
}

# ── Sự kiện ngẫu nhiên trong chiến đấu ─────────────────────────────
BATTLE_EVENTS = [
    {"msg": "⚡ **Sét đánh kho vũ khí** của {atk}! ATK giảm 20%.", "atk_mult": 0.8, "def_mult": 1.0},
    {"msg": "🔥 **Lửa bùng** trại của {def}! DEF giảm 20%.", "atk_mult": 1.0, "def_mult": 0.8},
    {"msg": "🌪️ **Bão cát** phủ chiến trường! Cả 2 bị -10%.", "atk_mult": 0.9, "def_mult": 0.9},
    {"msg": "💊 **Viện trợ y tế** tới {def}! DEF +15%.", "atk_mult": 1.0, "def_mult": 1.15},
    {"msg": "🚀 **Tiếp viện bí mật** cho {atk}! ATK +20%.", "atk_mult": 1.2, "def_mult": 1.0},
    {"msg": "🤝 **Không có sự kiện** — trận đấu diễn ra bình thường.", "atk_mult": 1.0, "def_mult": 1.0},
    {"msg": "🤝 **Không có sự kiện** — trận đấu diễn ra bình thường.", "atk_mult": 1.0, "def_mult": 1.0},
]

# ── Phần thưởng / hình phạt ─────────────────────────────────────────
PRIZE_STEAL_RATE  = 0.12   # Thắng: cướp 12% quỹ đối phương
REP_WIN_BONUS     = 15     # +15 danh tiếng khi thắng
REP_LOSE_PENALTY  = 20     # -20 danh tiếng khi thua
REP_SCANDAL_THRES = 30     # Dưới 30 rep → bị scandal
CRIT_CHANCE       = 0.12   # 12% chí mạng x1.8

# ════════════════════════════════════════════════════════════════════
# VIEW: Màn hình chọn kỹ năng (Button)
# ════════════════════════════════════════════════════════════════════
class SkillPickView(discord.ui.View):
    """Mỗi Chủ tịch bấm nút chọn kỹ năng (ẩn, ephemeral)."""

    def __init__(self, battle_ctx, side: str):
        super().__init__(timeout=60)
        self.battle_ctx = battle_ctx  # BattleContext object
        self.side = side              # "atk" hoặc "def"

        for skill_id, skill_data in SKILLS.items():
            btn = discord.ui.Button(
                label=f"{skill_data['emoji']} {skill_data['name'].split()[1]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"{self.side}_{skill_id}",  # thêm side vào để tránh trùng
)
            btn.callback = self._make_callback(skill_id)
            self.add_item(btn)

    def _make_callback(self, skill_id):
        async def callback(interaction: discord.Interaction):
            ctx = self.battle_ctx
            # Chỉ boss mới được chọn
            expected_id = ctx.atk_boss_id if self.side == "atk" else ctx.def_boss_id
            if str(interaction.user.id) != expected_id:
                return await interaction.response.send_message(
                    "❌ Chỉ Chủ Tịch công ty mới được chọn kỹ năng!", ephemeral=True
                )

            if self.side == "atk":
                ctx.atk_skill = skill_id
            else:
                ctx.def_skill = skill_id

            self.stop()
            for btn in self.children:
                btn.disabled = True

            chosen = SKILLS[skill_id]
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"✅ Đã chọn **{chosen['name']}** — {chosen['desc']}\n⏳ Chờ đối phương...",
                    color=discord.Color.green()
                ),
                view=self
            )

        return callback


# ════════════════════════════════════════════════════════════════════
# VIEW: Chấp nhận / từ chối thách đấu
# ════════════════════════════════════════════════════════════════════
class ChallengeAcceptView(discord.ui.View):
    def __init__(self, ctx, atk_comp, def_comp, atk_boss, def_boss_id: str):
        super().__init__(timeout=120)
        self.ctx       = ctx
        self.atk_comp  = atk_comp
        self.def_comp  = def_comp
        self.atk_boss  = atk_boss
        self.def_boss_id = def_boss_id
        self.accepted  = False

    @discord.ui.button(label="⚔️ Nhận Chiến!", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.def_boss_id:
            return await interaction.response.send_message("❌ Chỉ Chủ Tịch bên phòng thủ!", ephemeral=True)

        self.accepted = True
        for btn in self.children:
            btn.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="⚔️ THÁCH CHIẾN ĐƯỢC CHẤP NHẬN!",
                description="🕐 Trận đấu bắt đầu trong **5 giây**...",
                color=discord.Color.red()
            ),
            view=self
        )
        self.stop()
        await asyncio.sleep(2)
        await run_battle(interaction, self.atk_comp, self.def_comp, self.atk_boss)

    @discord.ui.button(label="🏳️ Rút Lui", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.def_boss_id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        for btn in self.children:
            btn.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"🏳️ Công ty **{self.def_comp['name']}** đã rút lui khỏi thách đấu.",
                color=discord.Color.dark_grey()
            ),
            view=self
        )
        self.stop()


# ════════════════════════════════════════════════════════════════════
# CORE: Chạy trận đấu
# ════════════════════════════════════════════════════════════════════
class BattleContext:
    """Lưu trạng thái 1 trận chiến."""
    def __init__(self, atk_comp, def_comp, atk_boss_id, def_boss_id):
        self.atk_comp    = atk_comp
        self.def_comp    = def_comp
        self.atk_boss_id = str(atk_boss_id)
        self.def_boss_id = str(def_boss_id)
        self.atk_skill   = None
        self.def_skill   = None


async def run_battle(interaction_or_ctx, atk_comp, def_comp, atk_boss_member):
    """Điều phối toàn bộ trận chiến: 3 vòng + tổng kết."""
    channel = (
        interaction_or_ctx.channel
        if hasattr(interaction_or_ctx, "channel")
        else interaction_or_ctx.channel
    )

    atk_boss_id = str(atk_boss_member.id)
    def_boss_id = next(
        (uid for uid, role in def_comp["members"].items() if role == "boss"), None
    )
    if not def_boss_id:
        return await channel.send("❌ Không tìm thấy Chủ Tịch phòng thủ!")

    # Lấy Member object
   
    # Lấy channel và guild đúng cách
    if hasattr(interaction_or_ctx, 'channel'):
        channel = interaction_or_ctx.channel
        guild = interaction_or_ctx.guild
    else:
        channel = interaction_or_ctx.channel
        guild = interaction_or_ctx.guild

    atk_boss_id = str(atk_boss_member.id)
    def_boss_id = next(
        (uid for uid, role in def_comp["members"].items() if role == "boss"), None
    )
    if not def_boss_id:
        return await channel.send("❌ Không tìm thấy Chủ Tịch phòng thủ!")

    try:
        def_boss_member = await guild.fetch_member(int(def_boss_id))
    except Exception:
        def_boss_member = None
   
    # Chỉ số cơ bản
    atk_base = (atk_comp.get("atk_level", 1) * 100 +
                 len(atk_comp.get("members", {})) * 20 +
                 atk_comp.get("treasury", 0) // 100000)
    def_base = (def_comp.get("def_level", 1) * 100 +
                 len(def_comp.get("members", {})) * 20 +
                 def_comp.get("treasury", 0) // 100000)

    atk_hp = 300
    def_hp = 300
    round_logs = []

    for round_num in range(1, 4):
        # ── Gửi DM để chọn kỹ năng ──────────────────────────────────
        ctx_obj = BattleContext(atk_comp, def_comp, atk_boss_id, def_boss_id)

        embed_pick = discord.Embed(
            title=f"⚔️ Vòng {round_num}/3 — Chọn Kỹ Năng",
            description=(
                "Cả 2 Chủ Tịch hãy **chọn kỹ năng trong 30 giây**.\n"
                "Kết quả sẽ reveal cùng lúc!\n\n"
                "```\n⚔️ Tấn Công  > 🛡️ Phòng Thủ\n"
                "🛡️ Phòng Thủ > 🔄 Phản Công\n"
                "🔄 Phản Công  > ⚔️ Tấn Công\n"
                "🌑 Mai Phục   > 🎯 Đổ Bộ\n"
                "🎯 Đổ Bộ     (mạo hiểm nhất)\n```"
            ),
            color=discord.Color.gold()
        )
        await channel.send(
            f"{atk_boss_member.mention} | "
            f"{def_boss_member.mention if def_boss_member else f'<@{def_boss_id}>'} "
            f"— Vòng **{round_num}**: Chọn kỹ năng!",
            embed=embed_pick
        )

        # Gửi view chọn kỹ năng ephemeral (dùng message thường vì không dùng slash)
        view_atk = SkillPickView(ctx_obj, "atk")
        view_def = SkillPickView(ctx_obj, "def")

        msg_atk = await channel.send(
            f"🔐 {atk_boss_member.mention} — **{atk_comp['name']}** chọn kỹ năng:",
            view=view_atk
        )
        msg_def = await channel.send(
            f"🔐 {def_boss_member.mention if def_boss_member else f'<@{def_boss_id}>'} — **{def_comp['name']}** chọn kỹ năng:",
            view=view_def
        )

        # Đợi cả 2 chọn hoặc timeout
        start = datetime.now()
        while (ctx_obj.atk_skill is None or ctx_obj.def_skill is None):
            await asyncio.sleep(1)
            if (datetime.now() - start).total_seconds() >= 30:
                break

        # Nếu ai không chọn → random
        if ctx_obj.atk_skill is None:
            ctx_obj.atk_skill = random.choice(list(SKILLS.keys()))
        if ctx_obj.def_skill is None:
            ctx_obj.def_skill = random.choice(list(SKILLS.keys()))

        # Disable cả 2 view
        for btn in view_atk.children:
            btn.disabled = True
        for btn in view_def.children:
            btn.disabled = True
        try:
            await msg_atk.edit(view=view_atk)
            await msg_def.edit(view=view_def)
        except Exception:
            pass

        # ── Tính kết quả vòng ───────────────────────────────────────
        sk_atk = SKILLS[ctx_obj.atk_skill]
        sk_def = SKILLS[ctx_obj.def_skill]

        # Kỹ năng counter bonus (+20%)
        skill_atk_mult = 1.2 if sk_atk.get("beats") == ctx_obj.def_skill else 1.0
        skill_def_mult = 1.2 if sk_def.get("beats") == ctx_obj.atk_skill else 1.0

        # Sự kiện ngẫu nhiên
        event = random.choice(BATTLE_EVENTS)

        # Tính damage
        atk_power = (atk_base * sk_atk["bonus_atk"] * skill_atk_mult
                     * event["atk_mult"] * random.uniform(0.85, 1.15))
        def_power = (def_base * sk_def["bonus_def"] * skill_def_mult
                     * event["def_mult"] * random.uniform(0.85, 1.15))

        # Chí mạng
        atk_crit = random.random() < CRIT_CHANCE
        def_crit = random.random() < CRIT_CHANCE
        if atk_crit:
            atk_power *= 1.8
        if def_crit:
            def_power *= 1.8

        # Damage thực sự
        atk_dmg = max(5, int((atk_power - def_power * 0.4) / 10))
        def_dmg = max(5, int((def_power - atk_power * 0.4) / 10))

        def_hp -= atk_dmg
        atk_hp -= def_dmg

        # Xây log vòng
        crit_atk_str = " 💥**CHÍ MẠNG!**" if atk_crit else ""
        crit_def_str = " 💥**CHÍ MẠNG!**" if def_crit else ""

        counter_str = ""
        if skill_atk_mult > 1.0:
            counter_str = f"\n🎯 **{sk_atk['emoji']} counter {sk_def['emoji']}** → ATK +20%"
        elif skill_def_mult > 1.0:
            counter_str = f"\n🎯 **{sk_def['emoji']} counter {sk_atk['emoji']}** → DEF +20%"

        log = (
            f"**Vòng {round_num}:**\n"
            f"  {atk_comp['name']}: {sk_atk['emoji']} **{sk_atk['name'].split()[1]}**"
            f"{crit_atk_str} → gây **{atk_dmg} ST**\n"
            f"  {def_comp['name']}: {sk_def['emoji']} **{sk_def['name'].split()[1]}**"
            f"{crit_def_str} → giảm **{def_dmg} ST**\n"
            f"  📣 {event['msg'].format(atk=atk_comp['name'], def_=def_comp['name'])}"
            f"{counter_str}\n"
            f"  ❤️ {atk_comp['name']}: **{max(0,atk_hp)}** | "
            f"{def_comp['name']}: **{max(0,def_hp)}**"
        )
        round_logs.append(log)

        bar_atk = make_hp_bar(max(0, atk_hp), 300)
        bar_def = make_hp_bar(max(0, def_hp), 300)

        embed_round = discord.Embed(
            title=f"⚔️ KẾT QUẢ VÒNG {round_num}",
            description=log,
            color=discord.Color.orange()
        )
        embed_round.add_field(
            name=f"❤️ {atk_comp['name']}",
            value=f"{bar_atk} {max(0,atk_hp)}/300",
            inline=False
        )
        embed_round.add_field(
            name=f"❤️ {def_comp['name']}",
            value=f"{bar_def} {max(0,def_hp)}/300",
            inline=False
        )
        await channel.send(embed=embed_round)

        if atk_hp <= 0 or def_hp <= 0:
            break

        await asyncio.sleep(3)

    # ── Tổng kết ────────────────────────────────────────────────────
    atk_wins = atk_hp > def_hp
    if atk_hp == def_hp:
        atk_wins = random.choice([True, False])  # hòa thì random

    winner_comp = atk_comp if atk_wins else def_comp
    loser_comp  = def_comp if atk_wins else atk_comp
    winner_id   = atk_comp["_id"] if atk_wins else def_comp["_id"]
    loser_id    = def_comp["_id"] if atk_wins else atk_comp["_id"]

    # Thưởng: cướp 12% quỹ đối phương
    loot = int(loser_comp.get("treasury", 0) * PRIZE_STEAL_RATE)
    loser_comp["treasury"]  = max(0, loser_comp.get("treasury", 0) - loot)
    winner_comp["treasury"] = winner_comp.get("treasury", 0) + loot

    # Cập nhật danh tiếng
    winner_comp["reputation"] = min(100, winner_comp.get("reputation", 100) + REP_WIN_BONUS)
    loser_comp["reputation"]  = max(0,   loser_comp.get("reputation",  100) - REP_LOSE_PENALTY)

    # Scandal nếu danh tiếng quá thấp
    if loser_comp["reputation"] <= REP_SCANDAL_THRES and not loser_comp.get("has_scandal"):
        loser_comp["has_scandal"] = True
        scandal_note = f"\n🚨 **{loser_comp['name']}** bị PHỐT do danh tiếng quá thấp!"
    else:
        scandal_note = ""

    # Phần thưởng cho toàn bộ thành viên winner
    member_bonus = max(1000, loot // max(1, len(winner_comp.get("members", {}))))
    for m_id in winner_comp.get("members", {}):
        m_data = load_user(m_id)
        m_data["money"] += member_bonus
        save_user(m_id)

    # Cooldown 6h cho bên tấn công
    daichien_cooldowns[atk_comp["_id"]] = datetime.now()

    save_company(winner_id)
    save_company(loser_id)

    # Thêm vào lịch sử sự kiện server
    add_history(atk_boss_id,
                f"Đại chiến {'thắng' if atk_wins else 'thua'} {loser_comp['name'] if atk_wins else winner_comp['name']}")

    # Embed tổng kết
    color_final = discord.Color.gold() if atk_wins else discord.Color.red()
    embed_final = discord.Embed(
        title="🏆 KẾT QUẢ ĐẠI CHIẾN CÔNG TY",
        color=color_final
    )
    embed_final.add_field(
        name="🎖️ Chiến thắng",
        value=f"**{winner_comp['name']}** đánh bại **{loser_comp['name']}**!",
        inline=False
    )
    embed_final.add_field(
        name="💰 Chiến lợi phẩm",
        value=(
            f"Cướp **{loot:,} 💰** từ quỹ đối phương\n"
            f"Mỗi thành viên nhận thêm **+{member_bonus:,} 💰**"
        ),
        inline=False
    )
    embed_final.add_field(
        name="📊 Danh tiếng",
        value=(
            f"🟢 {winner_comp['name']}: +{REP_WIN_BONUS} → **{winner_comp['reputation']}/100**\n"
            f"🔴 {loser_comp['name']}: -{REP_LOSE_PENALTY} → **{loser_comp['reputation']}/100**"
            f"{scandal_note}"
        ),
        inline=False
    )
    embed_final.add_field(
        name="📜 Tóm tắt trận đấu",
        value="\n".join(round_logs),
        inline=False
    )
    embed_final.set_footer(text=f"Quỹ thắng: {winner_comp['treasury']:,} 💰 | Quỹ thua: {loser_comp['treasury']:,} 💰")

    await channel.send(embed=embed_final)


def make_hp_bar(current, total, length=12):
    """Tạo thanh HP màu."""
    if total == 0:
        return "⬛" * length
    filled = int((current / total) * length)
    empty  = length - filled
    if current / total > 0.5:
        bar = "🟩" * filled
    elif current / total > 0.25:
        bar = "🟨" * filled
    else:
        bar = "🟥" * filled
    return bar + "⬛" * empty


# ════════════════════════════════════════════════════════════════════
# LỆNH CHÍNH: k daichien
# ════════════════════════════════════════════════════════════════════
@bot.group(invoke_without_command=True, aliases=['dc', 'war'])
async def daichien(ctx):
    """Bảng thông tin đại chiến + xem bảng xếp hạng công ty."""
    try:
        all_comps = list(companies_col.find())
    except Exception:
        all_comps = []

    # Sắp xếp theo treasury
    ranked = sorted(all_comps, key=lambda c: c.get("treasury", 0), reverse=True)

    embed = discord.Embed(
        title="⚔️ ĐẠI CHIẾN CÔNG TY",
        description=(
            "**Cách chơi:**\n"
            "`k daichien tan <@user hoặc tên cty>` — Thách đấu\n"
            "`k daichien info` — Thống kê công ty bạn\n"
            "`k daichien lichsu` — Lịch sử trận đánh\n\n"
            "**Cơ chế:**\n"
            "• 3 vòng, mỗi vòng 2 bên chọn kỹ năng\n"
            "• Kỹ năng có quan hệ counter (⚔️>🛡️>🔄>⚔️, 🌑>🎯)\n"
            "• Sự kiện ngẫu nhiên xảy ra mỗi vòng\n"
            "• Thắng: cướp 12% quỹ + +15 danh tiếng\n"
            "• Thua: mất tiền + -20 danh tiếng\n"
            "• CD: 6 giờ / lần tấn công\n"
        ),
        color=discord.Color.red()
    )

    if ranked:
        top_str = ""
        for i, comp in enumerate(ranked[:8]):
            medals = ["🥇", "🥈", "🥉"]
            icon = medals[i] if i < 3 else f"**#{i+1}**"
            rep = comp.get("reputation", 100)
            scandal = "🚨" if comp.get("has_scandal") else ""
            atk = comp.get("atk_level", 1)
            df  = comp.get("def_level",  1)
            top_str += (
                f"{icon} **{comp['name']}** {scandal}\n"
                f"   💰 {comp.get('treasury',0):,} | ⚔️Lv{atk} 🛡️Lv{df} | 🌟{rep}/100\n"
            )
        embed.add_field(name="🏆 BXH CÔNG TY", value=top_str or "Chưa có", inline=False)

    await ctx.reply(embed=embed, mention_author=False)


@daichien.command(aliases=['thachdan', 'attack'])
async def tan(ctx, *, target_name: str):
    """Thách đấu một công ty khác. Dùng tên công ty."""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    atk_comp_id = user_data.get("company")

    if not atk_comp_id:
        return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)

    atk_comp = load_company(atk_comp_id)
    if not atk_comp:
        return await ctx.reply("⚠️ Công ty bạn không tồn tại!", mention_author=False)

    if atk_comp["members"].get(user_id) != "boss":
        return await ctx.reply("⚠️ Chỉ **Chủ Tịch** mới được phát động chiến tranh!", mention_author=False)

    # Cooldown 6 giờ
    last_war = daichien_cooldowns.get(atk_comp_id)
    if last_war and (datetime.now() - last_war).total_seconds() < 21600:
        remain = int(21600 - (datetime.now() - last_war).total_seconds())
        h, m = divmod(remain, 3600)
        m //= 60
        return await ctx.reply(
            embed=discord.Embed(
                description=f"⏳ Quân lính cần nghỉ ngơi! Tấn công lại sau **{h}h {m}m**.",
                color=discord.Color.orange()
            ),
            mention_author=False
        )

    # Tìm công ty đích theo tên
    target_name_lower = target_name.lower().strip()
    try:
        all_comps = list(companies_col.find())
    except Exception:
        all_comps = []

    def_comp = None
    for comp in all_comps:
        if comp["name"].lower() == target_name_lower:
            def_comp = comp
            break
    if not def_comp:
        # Tìm tương đối
        for comp in all_comps:
            if target_name_lower in comp["name"].lower():
                def_comp = comp
                break

    if not def_comp:
        return await ctx.reply(f"⚠️ Không tìm thấy công ty **{target_name}**!", mention_author=False)

    if def_comp["_id"] == atk_comp_id:
        return await ctx.reply("⚠️ Không thể tự tấn công mình!", mention_author=False)

    # Cập nhật cache
    COMPANY_CACHE[def_comp["_id"]] = def_comp

    # Tìm Chủ tịch bên phòng thủ
    def_boss_id = next(
        (uid for uid, role in def_comp["members"].items() if role == "boss"), None
    )
    if not def_boss_id:
        return await ctx.reply("⚠️ Công ty kia không có Chủ Tịch!", mention_author=False)

    # Sức mạnh cơ bản để preview
    atk_power = atk_comp.get("atk_level", 1) * 100 + len(atk_comp.get("members", {})) * 20
    def_power = def_comp.get("def_level", 1)  * 100 + len(def_comp.get("members", {})) * 20
    loot_preview = int(def_comp.get("treasury", 0) * PRIZE_STEAL_RATE)

    embed = discord.Embed(
        title="⚔️ TUYÊN CHIẾN!",
        description=(
            f"**{atk_comp['name']}** tuyên chiến với **{def_comp['name']}**!\n\n"
            f"⚔️ Công: **{atk_power}** vs 🛡️ Thủ: **{def_power}**\n"
            f"💰 Tiền thưởng nếu thắng: **~{loot_preview:,} 💰**\n\n"
            f"<@{def_boss_id}> — **Chủ Tịch {def_comp['name']}**, bạn có nhận chiến không?"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Timeout: 2 phút | 3 vòng | Chọn kỹ năng mỗi vòng")

    view = ChallengeAcceptView(ctx, atk_comp, def_comp, ctx.author, def_boss_id)
    await ctx.send(f"<@{def_boss_id}>", embed=embed, view=view)


@daichien.command()
async def info(ctx):
    """Xem thông tin chiến đấu công ty của bạn."""
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id:
        return await ctx.reply("⚠️ Bạn chưa có công ty!", mention_author=False)

    comp = load_company(comp_id)
    if not comp:
        return await ctx.reply("⚠️ Công ty không tồn tại!", mention_author=False)

    atk_lvl = comp.get("atk_level", 1)
    def_lvl = comp.get("def_level", 1)
    members = len(comp.get("members", {}))
    treasury = comp.get("treasury", 0)
    rep = comp.get("reputation", 100)
    scandal = "🚨 ĐANG DÍNH PHỐT" if comp.get("has_scandal") else "✅ Trong sạch"

    # Tính tổng sức mạnh
    atk_power = atk_lvl * 100 + members * 20 + treasury // 100000
    def_power = def_lvl * 100 + members * 20 + treasury // 100000

    last_war = daichien_cooldowns.get(comp_id)
    if last_war:
        remain = max(0, 21600 - int((datetime.now() - last_war).total_seconds()))
        h, m = divmod(remain, 3600)
        cd_str = f"**{h}h {m//60}m** nữa" if remain > 0 else "Sẵn sàng!"
    else:
        cd_str = "Sẵn sàng!"

    embed = discord.Embed(
        title=f"🏢 THÔNG TIN CHIẾN ĐẤU — {comp['name']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="⚔️ Chỉ số tấn công", value=f"**{atk_power}** (ATK Lv{atk_lvl})", inline=True)
    embed.add_field(name="🛡️ Chỉ số phòng thủ", value=f"**{def_power}** (DEF Lv{def_lvl})", inline=True)
    embed.add_field(name="👥 Nhân sự", value=f"**{members}** người", inline=True)
    embed.add_field(name="🌟 Danh tiếng", value=f"**{rep}/100**", inline=True)
    embed.add_field(name="🚨 Trạng thái", value=scandal, inline=True)
    embed.add_field(name="⏳ Cooldown chiến", value=cd_str, inline=True)
    embed.add_field(
        name="📈 Nâng cấp",
        value=(
            f"ATK Lv{atk_lvl} → Lv{atk_lvl+1}: **{atk_lvl*500000:,} 💰** (từ quỹ)\n"
            f"DEF Lv{def_lvl} → Lv{def_lvl+1}: **{def_lvl*300000:,} 💰** (từ quỹ)\n"
            f"`k cty nangcap cong` | `k cty nangcap thu`"
        ),
        inline=False
    )
    embed.add_field(
        name="💡 Kỹ năng trong trận",
        value=(
            "⚔️ Tấn Công | 🛡️ Phòng Thủ | 🔄 Phản Công\n"
            "🎯 Đổ Bộ (all-in) | 🌑 Mai Phục (counter đổ bộ)"
        ),
        inline=False
    )
    await ctx.reply(embed=embed, mention_author=False)


@daichien.command()
async def lichsu(ctx):
    """Xem lịch sử đại chiến của bạn."""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    history = [h for h in user_data.get("history", []) if "chiến" in h.lower() or "Đại chiến" in h]
    if not history:
        return await ctx.reply(
            embed=discord.Embed(description="📜 Chưa có lịch sử đại chiến.", color=discord.Color.light_grey()),
            mention_author=False
        )
    embed = discord.Embed(
        title="📜 LỊCH SỬ ĐẠI CHIẾN",
        description="\n".join(history[:10]),
        color=discord.Color.blue()
    )
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# KALLEN FANTASY v2.0 — FULL UPGRADE MODULE
# Dán toàn bộ file này vào bot.py, thay thế phần Kallen Fantasy cũ
# Yêu cầu: discord.py, pymongo, asyncio, random, datetime đã import
# =====================================================================

# ══════════════════════════════════════════════════════════════════════
# SECTION 1: CONSTANTS & DATA
# ══════════════════════════════════════════════════════════════════════

KF_TICKET_PRICE = 30_000
KF_TICKET_ITEM  = "Vé Kallen Fantasy 🎟️"

# ── TRANG BỊ ──────────────────────────────────────────────────────────
KF_EQUIPMENT = {
    # ─ VŨ KHÍ ─
    "kiem_kaslana": {
        "name": "⚔️ Kiếm Kaslana Thánh",
        "type": "weapon", "slot": "weapon",
        "rarity": "legendary",
        "atk": 40, "def": 0, "hp": 0, "crit": 10,
        "desc": "Thanh kiếm truyền đời của dòng họ Kaslana. ATK +40, CRIT +10%",
        "craft": {"Giọt Máu Herrscher 🩸": 3, "Tinh Thể Honkai 💠": 5},
        "buy": 0, "sell": 80_000,
        "char_bonus": {"kallen": "Chí mạng gây +50% sát thương thêm"},
    },
    "truong_giao_fuhua": {
        "name": "🪃 Trường Giáo Phượng Hoàng",
        "type": "weapon", "slot": "weapon",
        "rarity": "epic",
        "atk": 30, "def": 5, "hp": 20, "crit": 5,
        "desc": "Vũ khí của Fu Hua. ATK +30, DEF +5, HP +20",
        "craft": {"Lông Vũ Fu Hua 🪶": 3, "Tinh Thể Honkai 💠": 3},
        "buy": 0, "sell": 50_000,
        "char_bonus": {"fuhua": "Hồi thêm 20 HP mỗi khi giết kẻ thù"},
    },
    "quat_onmyo": {
        "name": "🪭 Quạt Onmyo Hồ Ly",
        "type": "weapon", "slot": "weapon",
        "rarity": "epic",
        "atk": 35, "def": 0, "hp": 0, "crit": 8,
        "desc": "Quạt phép của Yae Sakura. ATK +35, CRIT +8%",
        "craft": {"Hoa Anh Đào Yae 🌸": 4, "Tinh Thể Honkai 💠": 2},
        "buy": 0, "sell": 45_000,
        "char_bonus": {"sakura": "Kỹ năng hồ ly gây thêm 20% sát thương"},
    },
    "sung_laser_otto": {
        "name": "🔬 Súng Laser Schicksal",
        "type": "weapon", "slot": "weapon",
        "rarity": "epic",
        "atk": 28, "def": 10, "hp": 30, "crit": 3,
        "desc": "Vũ khí khoa học của Otto. ATK +28, DEF +10, HP +30",
        "craft": {"Thiết Phẩm Kallen ⚙️": 4, "Tinh Thể Honkai 💠": 3},
        "buy": 0, "sell": 40_000,
        "char_bonus": {"otto": "Phản đòn thêm 10% sát thương"},
    },
    "kiem_buong_toi": {
        "name": "🌙 Kiếm Bóng Tối Kevin",
        "type": "weapon", "slot": "weapon",
        "rarity": "mythic",
        "atk": 60, "def": 10, "hp": 50, "crit": 15,
        "desc": "Vũ khí của Kevin Kaslana. ATK +60, DEF +10, HP +50, CRIT +15%",
        "craft": {"Cốt Tủy Kevin ❄️": 4, "Giọt Máu Herrscher 🩸": 2, "Tinh Thể Honkai 💠": 5},
        "buy": 0, "sell": 200_000,
        "char_bonus": {"kevin": "Mỗi lần đánh, sát thương tăng thêm 3% tích lũy"},
    },
    "vu_khi_thuong": {
        "name": "🗡️ Kiếm Sắt Thường",
        "type": "weapon", "slot": "weapon",
        "rarity": "common",
        "atk": 10, "def": 0, "hp": 0, "crit": 0,
        "desc": "Vũ khí phổ thông. ATK +10",
        "craft": {}, "buy": 5_000, "sell": 2_000,
        "char_bonus": {},
    },
    # ─ GIÁP ─
    "giap_kaslana": {
        "name": "🛡️ Giáp Hiệp Sĩ Kaslana",
        "type": "armor", "slot": "armor",
        "rarity": "legendary",
        "atk": 0, "def": 50, "hp": 100, "crit": 0,
        "desc": "Giáp của dòng họ Kaslana. DEF +50, HP +100",
        "craft": {"Thiết Phẩm Kallen ⚙️": 5, "Lông Vũ Fu Hua 🪶": 2},
        "buy": 0, "sell": 90_000,
        "char_bonus": {"kallen": "Không chết khi HP xuống 0, hồi 1 HP (1 lần/trận)"},
    },
    "giap_phoenix": {
        "name": "🦅 Giáp Phượng Hoàng",
        "type": "armor", "slot": "armor",
        "rarity": "epic",
        "atk": 5, "def": 35, "hp": 60, "crit": 0,
        "desc": "Giáp của Fu Hua. DEF +35, HP +60, ATK +5",
        "craft": {"Lông Vũ Fu Hua 🪶": 4, "Tinh Thể Honkai 💠": 2},
        "buy": 0, "sell": 55_000,
        "char_bonus": {"fuhua": "30% cơ hội né miễn phí khi bị tấn công"},
    },
    "ao_holo": {
        "name": "🌸 Áo Onmyo Hồ Ly",
        "type": "armor", "slot": "armor",
        "rarity": "epic",
        "atk": 8, "def": 25, "hp": 40, "crit": 3,
        "desc": "Trang phục Yae Sakura. ATK +8, DEF +25, HP +40",
        "craft": {"Hoa Anh Đào Yae 🌸": 3, "Mảnh Nhớ Otto 💌": 2},
        "buy": 0, "sell": 45_000,
        "char_bonus": {"sakura": "Sau khi dùng ULT, hồi 30 HP"},
    },
    "ao_lab_otto": {
        "name": "🧪 Áo Lab Schicksal",
        "type": "armor", "slot": "armor",
        "rarity": "rare",
        "atk": 5, "def": 20, "hp": 50, "crit": 0,
        "desc": "Áo của Otto. ATK +5, DEF +20, HP +50",
        "craft": {"Mảnh Nhớ Otto 💌": 3, "Thiết Phẩm Kallen ⚙️": 2},
        "buy": 0, "sell": 30_000,
        "char_bonus": {"otto": "Phản đòn kích hoạt từ lần DEF đầu tiên mỗi trận"},
    },
    "giap_bong_toi": {
        "name": "❄️ Giáp Băng Kevin",
        "type": "armor", "slot": "armor",
        "rarity": "mythic",
        "atk": 10, "def": 60, "hp": 120, "crit": 5,
        "desc": "Giáp của Kevin. DEF +60, HP +120, ATK +10, CRIT +5%",
        "craft": {"Cốt Tủy Kevin ❄️": 3, "Giọt Máu Herrscher 🩸": 3, "Tinh Thể Honkai 💠": 4},
        "buy": 0, "sell": 180_000,
        "char_bonus": {"kevin": "Mỗi lần bị đánh, tích 1 charge; 5 charge → tự né 1 đòn"},
    },
    "giap_thuong": {
        "name": "🪖 Giáp Sắt Thường",
        "type": "armor", "slot": "armor",
        "rarity": "common",
        "atk": 0, "def": 10, "hp": 20, "crit": 0,
        "desc": "Giáp phổ thông. DEF +10, HP +20",
        "craft": {}, "buy": 5_000, "sell": 2_000,
        "char_bonus": {},
    },
    # ─ PHỤ KIỆN ─
    "vong_co": {
        "name": "💍 Vòng Cổ Honkai",
        "type": "accessory", "slot": "accessory",
        "rarity": "rare",
        "atk": 5, "def": 5, "hp": 30, "crit": 5,
        "desc": "Vòng cổ có tinh thể Honkai. ATK +5, DEF +5, HP +30, CRIT +5%",
        "craft": {"Tinh Thể Honkai 💠": 3},
        "buy": 15_000, "sell": 8_000,
        "char_bonus": {},
    },
    "nhan_herrscher": {
        "name": "💎 Nhẫn Herrscher",
        "type": "accessory", "slot": "accessory",
        "rarity": "legendary",
        "atk": 15, "def": 10, "hp": 50, "crit": 8,
        "desc": "Nhẫn của Herrscher. ATK +15, DEF +10, HP +50, CRIT +8%",
        "craft": {"Giọt Máu Herrscher 🩸": 4, "Tinh Thể Honkai 💠": 3},
        "buy": 0, "sell": 100_000,
        "char_bonus": {},
    },
    "bua_ho_menh": {
        "name": "📿 Bùa Hộ Mệnh Onmyo",
        "type": "accessory", "slot": "accessory",
        "rarity": "epic",
        "atk": 0, "def": 15, "hp": 40, "crit": 3,
        "desc": "Bùa của Yae Sakura. DEF +15, HP +40, CRIT +3%",
        "craft": {"Hoa Anh Đào Yae 🌸": 2, "Mảnh Nhớ Otto 💌": 2},
        "buy": 0, "sell": 35_000,
        "char_bonus": {"sakura": "10% cơ hội hồi 20 HP mỗi lượt"},
    },
    "phu_kien_thuong": {
        "name": "🔮 Đá Ma Lực Nhỏ",
        "type": "accessory", "slot": "accessory",
        "rarity": "common",
        "atk": 3, "def": 3, "hp": 10, "crit": 2,
        "desc": "Đá phổ thông. ATK +3, DEF +3, HP +10, CRIT +2%",
        "craft": {}, "buy": 3_000, "sell": 1_000,
        "char_bonus": {},
    },
}

RARITY_COLOR = {
    "common":    "⚪ Thường",
    "rare":      "🔵 Hiếm",
    "epic":      "🟣 Sử Thi",
    "legendary": "🟡 Huyền Thoại",
    "mythic":    "🌈 Thần Thoại",
}

# ── VẬT PHẨM ĐỘC QUYỀN ───────────────────────────────────────────────
KF_EXCLUSIVE_ITEMS = {
    "Thiết Phẩm Kallen ⚙️":  {"type": "material", "desc": "Mảnh thép từ kiếm Kallen",         "sell": 50_000},
    "Mảnh Nhớ Otto 💌":       {"type": "material", "desc": "Ký ức Otto về Kallen",              "sell": 40_000},
    "Hoa Anh Đào Yae 🌸":     {"type": "material", "desc": "Bông hoa Yae Sakura ban tặng",      "sell": 45_000},
    "Lông Vũ Fu Hua 🪶":      {"type": "material", "desc": "Lông vũ của Phoenix Fu Hua",        "sell": 55_000},
    "Tinh Thể Honkai 💠":     {"type": "material", "desc": "Năng lượng Honkai tinh khiết",      "sell": 80_000},
    "Giọt Máu Herrscher 🩸":  {"type": "material", "desc": "Từ Herrscher bị đánh bại",         "sell": 120_000},
    "Cốt Tủy Kevin ❄️":       {"type": "material", "desc": "Sức mạnh Kevin Kaslana",            "sell": 150_000},
    "Hồn Ngọc Elysia 💗":     {"type": "material", "desc": "Ngọc tình yêu của Elysia",         "sell": 90_000},
    "Chuỗi Hạt Aponia 🙏":    {"type": "material", "desc": "Chuỗi hạt thánh của Aponia",       "sell": 70_000},
    "Mảnh Ký Ức Seele 👻":    {"type": "material", "desc": "Ký ức Seele từ hư không",          "sell": 60_000},
    "Vảy Rồng Vua 🐉":        {"type": "material", "desc": "Vảy rồng từ chương bí ẩn",         "sell": 200_000},
    "Bụi Sao Trời 🌟":        {"type": "material", "desc": "Bụi sao từ thiên hà KF",           "sell": 300_000},
}

KF_EXCLUSIVE_TITLES = {
    "Hiệp Sĩ Hắc Bạch ⚔️":      {"req_chapter": 1},
    "Người Bảo Vệ Nhân Loại 🛡️": {"req_chapter": 2},
    "Kẻ Diệt Honkai 💠":          {"req_chapter": 3},
    "Thợ Săn Herrscher 🩸":       {"req_chapter": 4},
    "Huyền Thoại Xà Hầu 🌌":     {"req_chapter": 5},
    "Người Kế Thừa Kevin 👑":     {"req_chapter": 6},
    "Kẻ Chinh Phục Vũ Trụ 🌠":   {"req_chapter": 7},
    "Chúa Tể Bóng Tối 🌑":       {"req_chapter": 8},
    "Thần Chiến Honkai 🔱":       {"req_chapter": 9},
    "Truyền Nhân Bất Tử 💎":     {"req_raid": True},
}

# ── NHÂN VẬT ─────────────────────────────────────────────────────────
KF_CHARACTERS = {
    "kallen": {
        "name": "Kallen Kaslana ⚔️",
        "title": "Hiệp Sĩ Trắng",
        "hp": 350, "atk": 80, "def": 40, "crit": 15,
        "element": "Vật Lý ⚪",
        "passive": "Hiệp Sĩ Danh Dự: Chí mạng +15%, sát thương Boss +20%",
        "avatar": "https://i.imgur.com/KallenAvatar.png",
        "banner": "https://i.imgur.com/KallenBanner.png",
        "skills": {
            "atk": {"name": "Kiếm Chém Bạo Phong 🌪️",  "mp": 0,  "mult": 1.2,  "desc": "Chém liên hoàn 3 nhát, x1.2 sát thương"},
            "def": {"name": "Khiên Thánh Kaslana 🛡️",   "mp": 20, "mult": 0,    "desc": "Giảm 40% sát thương 1 lượt"},
            "ult": {"name": "Thánh Nữ Phán Quyết ✨",    "mp": 60, "mult": 3.5,  "desc": "Ánh sáng thánh x3.5, Boss +20%"},
        },
        "unlock": 0,
        "lore": "Kallen Kaslana — hiệp sĩ của dòng họ Kaslana. Cô chiến đấu vì tình yêu với loài người, không màng đến cái chết.",
        "upgrade_stat": "atk",
    },
    "fuhua": {
        "name": "Fu Hua 🦅",
        "title": "Phượng Hoàng Bất Tử",
        "hp": 300, "atk": 90, "def": 30, "crit": 12,
        "element": "Gió 🌬️",
        "passive": "Bất Tử Phượng Hoàng: Hồi 30 HP khi giết kẻ thù",
        "avatar": "https://i.imgur.com/FuHuaAvatar.png",
        "banner": "https://i.imgur.com/FuHuaBanner.png",
        "skills": {
            "atk": {"name": "Song Chưởng Phong Vũ 🌬️",  "mp": 0,  "mult": 1.3,  "desc": "Đòn tay tốc độ cao, x1.3 + hồi HP"},
            "def": {"name": "Tâm Linh Tĩnh Lặng 🧘",    "mp": 25, "mult": 0,    "desc": "Né hoàn toàn 1 đòn tiếp theo"},
            "ult": {"name": "Hồi Sinh Phượng Hoàng 🔥",  "mp": 60, "mult": 2.8,  "desc": "Hồi 80 HP + tấn công x2.8"},
        },
        "unlock": 0,
        "lore": "Fu Hua — bất tử suốt 50.000 năm. Từng là cố vấn của Shenzhou và là Phoenix thực sự của nhân loại.",
        "upgrade_stat": "def",
    },
    "sakura": {
        "name": "Yae Sakura 🌸",
        "title": "Hồ Ly Onmyoji",
        "hp": 280, "atk": 100, "def": 20, "crit": 20,
        "element": "Lửa 🔥",
        "passive": "Linh Hồn Bất Diệt: Sát thương kỹ năng +25%",
        "avatar": "https://i.imgur.com/SakuraAvatar.png",
        "banner": "https://i.imgur.com/SakuraBanner.png",
        "skills": {
            "atk": {"name": "Hồ Ly Hỏa Thuật 🦊",       "mp": 0,  "mult": 1.4,  "desc": "Ném lửa hồ ly x1.4"},
            "def": {"name": "Bùa Hộ Mệnh Onmyo 📿",     "mp": 20, "mult": 0,    "desc": "Hút 25% sát thương thành HP"},
            "ult": {"name": "Trăm Hồ Ly Hỏa Vũ 🌺",     "mp": 60, "mult": 4.0,  "desc": "Triệu hồi 100 hồ ly, x4.0"},
        },
        "unlock": 0,
        "lore": "Yae Sakura — Onmyoji hồ ly đến từ Yae Village. Linh hồn cô gắn liền với Higokumaru trong muôn đời.",
        "upgrade_stat": "atk",
    },
    "otto": {
        "name": "Otto Apocalypse 🧪",
        "title": "Giám Đốc Schicksal",
        "hp": 260, "atk": 95, "def": 35, "crit": 8,
        "element": "Băng 🧊",
        "passive": "Thiên Tài Khoa Học: 20% debuff kẻ thù -20% DEF",
        "avatar": "https://i.imgur.com/OttoAvatar.png",
        "banner": "https://i.imgur.com/OttoBanner.png",
        "skills": {
            "atk": {"name": "Thần Kinh Băng Giá 🧊",    "mp": 0,  "mult": 1.35, "desc": "Phóng băng tinh thể, x1.35"},
            "def": {"name": "Lá Chắn Năng Lượng ⚡",    "mp": 30, "mult": 0,    "desc": "Giảm 50% sát thương + phản 20%"},
            "ult": {"name": "Khải Huyền Otto ❄️",        "mp": 70, "mult": 3.8,  "desc": "Kích hoạt Prometheus, x3.8"},
        },
        "unlock": 1,
        "unlock_item": "Thiết Phẩm Kallen ⚙️",
        "unlock_count": 3,
        "lore": "Otto Apocalypse — Giám đốc tổ chức Schicksal. Mọi việc ông làm đều xuất phát từ tình yêu dành cho Kallen.",
        "upgrade_stat": "def",
    },
    "kevin": {
        "name": "Kevin Kaslana ❄️",
        "title": "Người Cuối Cùng",
        "hp": 400, "atk": 110, "def": 50, "crit": 10,
        "element": "Tối 🌑",
        "passive": "Vũ Khí Cuối Cùng: Sát thương tăng 5% mỗi lượt (tích lũy, max 50%)",
        "avatar": "https://i.imgur.com/KevinAvatar.png",
        "banner": "https://i.imgur.com/KevinBanner.png",
        "skills": {
            "atk": {"name": "Trảm Hồn Đao 🗡️",          "mp": 0,  "mult": 1.5,  "desc": "Đòn đơn cực mạnh, x1.5 + tích stack"},
            "def": {"name": "Tịch Diệt Thể Xác 💀",      "mp": 40, "mult": 0,    "desc": "Bất tử 1 lượt, hồi 50 HP"},
            "ult": {"name": "Ánh Trăng Cuối Cùng 🌙",    "mp": 80, "mult": 5.0,  "desc": "Tuyệt chiêu Kevin x5.0, reset stack"},
        },
        "unlock": 2,
        "unlock_item": "Cốt Tủy Kevin ❄️",
        "unlock_count": 2,
        "lore": "Kevin Kaslana — người cuối cùng đứng vững trước làn sóng Honkai. Anh gánh chịu mọi thứ trong cô đơn suốt nghìn năm.",
        "upgrade_stat": "atk",
    },
    "elysia": {
        "name": "Elysia 🌟",
        "title": "Nữ Hoàng HoV",
        "hp": 320, "atk": 88, "def": 32, "crit": 10,
        "element": "Sinh Học 🌿",
        "passive": "Yêu Thương Vô Điều Kiện: Hồi 15 HP đầu mỗi lượt",
        "avatar": "https://i.imgur.com/ElysiaAvatar.png",
        "banner": "https://i.imgur.com/ElysiaBanner.png",
        "skills": {
            "atk": {"name": "Mũi Tên Tình Yêu 💘",       "mp": 0,  "mult": 1.25, "desc": "Mũi tên hồng x1.25"},
            "def": {"name": "Ôm Ấp Che Chở 🤗",          "mp": 20, "mult": 0,    "desc": "Hồi 60 HP + DEF +30%"},
            "ult": {"name": "Lời Tạm Biệt Elysia 🌸",    "mp": 60, "mult": 3.2,  "desc": "x3.2 + hồi 50 HP"},
        },
        "unlock": 1,
        "unlock_item": "Hồn Ngọc Elysia 💗",
        "unlock_count": 2,
        "lore": "Elysia — thành viên HoV và là 'cô gái đẹp nhất'. Tình yêu của cô dành cho loài người là vô điều kiện.",
        "upgrade_stat": "hp",
    },
    "aponia": {
        "name": "Aponia 📿",
        "title": "Nữ Tu Trừng Phạt",
        "hp": 290, "atk": 92, "def": 38, "crit": 12,
        "element": "Thánh ✝️",
        "passive": "Tội Lỗi & Trừng Phạt: 25% gây choáng 1 lượt khi ATK",
        "avatar": "https://i.imgur.com/AponiaAvatar.png",
        "banner": "https://i.imgur.com/AponiaBanner.png",
        "skills": {
            "atk": {"name": "Roi Trừng Phạt ⛓️",         "mp": 0,  "mult": 1.3,  "desc": "Quật roi thánh x1.3, 25% choáng"},
            "def": {"name": "Cầu Nguyện Bảo Hộ 🙏",      "mp": 25, "mult": 0,    "desc": "Giảm 45% sát thương + phản 15%"},
            "ult": {"name": "Phán Xét Cuối Cùng ✝️",      "mp": 65, "mult": 3.6,  "desc": "Mưa thánh quang x3.6"},
        },
        "unlock": 1,
        "unlock_item": "Chuỗi Hạt Aponia 🙏",
        "unlock_count": 2,
        "lore": "Aponia — Nữ Tu của HoV. Cô tin rằng tội lỗi phải được trừng phạt, kể cả tội của chính mình.",
        "upgrade_stat": "def",
    },
    "seele": {
        "name": "Seele 👻",
        "title": "Linh Hồn Từ Hư Không",
        "hp": 270, "atk": 115, "def": 15, "crit": 25,
        "element": "Tâm Linh 🔮",
        "passive": "Bướm Đêm: Khi chí mạng, đánh thêm 1 lần nữa",
        "avatar": "https://i.imgur.com/SeeleAvatar.png",
        "banner": "https://i.imgur.com/SeeleBanner.png",
        "skills": {
            "atk": {"name": "Lưỡi Hái Bóng Tối 🌑",     "mp": 0,  "mult": 1.5,  "desc": "Lưỡi hái linh hồn x1.5, CRIT cao"},
            "def": {"name": "Bóng Ma Biến Mất 👻",       "mp": 30, "mult": 0,    "desc": "Né 1 đòn + phản công x0.5"},
            "ult": {"name": "Vũ Khúc Bướm Đen 🦋",       "mp": 70, "mult": 4.5,  "desc": "Hóa thân bướm đêm x4.5, CRIT gấp đôi"},
        },
        "unlock": 2,
        "unlock_item": "Mảnh Ký Ức Seele 👻",
        "unlock_count": 3,
        "lore": "Seele — linh hồn nhân tạo được Otto tạo ra. Cô tồn tại giữa ranh giới sống và chết, mang ký ức về Kallen.",
        "upgrade_stat": "atk",
    },
    "vill_v": {
        "name": "Vill-V 🎭",
        "title": "Màn Trình Diễn Cuối",
        "hp": 310, "atk": 85, "def": 45, "crit": 15,
        "element": "Điện ⚡",
        "passive": "Nhân Cách Phân Liệt: Mỗi lượt đổi giữa ATK và DEF chế độ ngẫu nhiên",
        "avatar": "https://i.imgur.com/VillVAvatar.png",
        "banner": "https://i.imgur.com/VillVBanner.png",
        "skills": {
            "atk": {"name": "Điện Kịch Trường 🎭",       "mp": 0,  "mult": 1.35, "desc": "Điện giật sân khấu x1.35"},
            "def": {"name": "Màn Ảo Thuật 🎩",           "mp": 25, "mult": 0,    "desc": "Phân thân thoát đòn + phản 25%"},
            "ult": {"name": "Màn Biểu Diễn Cuối ⚡",     "mp": 65, "mult": 3.8,  "desc": "Toàn bộ điện năng x3.8"},
        },
        "unlock": 2,
        "unlock_item": "Bụi Sao Trời 🌟",
        "unlock_count": 2,
        "lore": "Vill-V — thành viên bí ẩn của HoV. Cô luôn đeo mặt nạ và hành động như diễn viên trên sân khấu định mệnh.",
        "upgrade_stat": "def",
    },
    "pardofelis": {
        "name": "Pardofelis 🐱",
        "title": "Mèo Con HoV",
        "hp": 340, "atk": 75, "def": 55, "crit": 8,
        "element": "Đất 🌍",
        "passive": "Trữ Năng Lượng: Mỗi lần bị đánh, tích 10 MP thêm",
        "avatar": "https://i.imgur.com/PardoAvatar.png",
        "banner": "https://i.imgur.com/PardoBanner.png",
        "skills": {
            "atk": {"name": "Móng Vuốt Đất 🐾",          "mp": 0,  "mult": 1.2,  "desc": "Cào đất x1.2, nhanh và chắc"},
            "def": {"name": "Lãnh Thổ Mèo 🐱",           "mp": 20, "mult": 0,    "desc": "Giảm 50% sát thương + hồi 20 HP"},
            "ult": {"name": "Roar Của Chúa Tể Đất 🌋",   "mp": 60, "mult": 3.0,  "desc": "Chấn động đất x3.0, choáng kẻ thù 2 lượt"},
        },
        "unlock": 1,
        "unlock_item": "Tinh Thể Honkai 💠",
        "unlock_count": 4,
        "lore": "Pardofelis — mèo con đáng yêu của HoV. Đừng để vẻ ngoài đánh lừa bạn, cô ấy có thể nghiền nát đá.",
        "upgrade_stat": "def",
    },
}

# ── SKILLS HỆ THỐNG ───────────────────────────────────────────────────
SKILLS = {
    "tan_cong":  {"name": "⚔️ Tấn Công",  "emoji": "⚔️", "beats": "phong_thu", "bonus_atk": 1.4, "bonus_def": 1.0, "desc": "Dồn lực đánh thẳng"},
    "phong_thu": {"name": "🛡️ Phòng Thủ", "emoji": "🛡️", "beats": "phan_cong", "bonus_atk": 0.7, "bonus_def": 1.6, "desc": "Lập thế thủ chắc"},
    "phan_cong": {"name": "🔄 Phản Công",  "emoji": "🔄", "beats": "tan_cong",  "bonus_atk": 1.2, "bonus_def": 1.2, "desc": "Chờ đòn rồi trả"},
    "do_bo":     {"name": "🎯 Đổ Bộ",      "emoji": "🎯", "beats": None,         "bonus_atk": 1.8, "bonus_def": 0.5, "desc": "All-in mạo hiểm"},
    "mai_phuc":  {"name": "🌑 Mai Phục",   "emoji": "🌑", "beats": "do_bo",      "bonus_atk": 1.5, "bonus_def": 0.9, "desc": "Bẫy đòn đổ bộ"},
}

BATTLE_EVENTS = [
    {"msg": "⚡ Sét đánh kho vũ khí ATK! ATK -{atk} giảm 20%.", "atk_mult": 0.8, "def_mult": 1.0},
    {"msg": "🔥 Lửa bùng trại phòng thủ! DEF -{def} giảm 20%.", "atk_mult": 1.0, "def_mult": 0.8},
    {"msg": "🌪️ Bão cát phủ chiến trường! Cả 2 -10%.",           "atk_mult": 0.9, "def_mult": 0.9},
    {"msg": "💊 Viện trợ y tế đến! DEF +15%.",                    "atk_mult": 1.0, "def_mult": 1.15},
    {"msg": "🚀 Tiếp viện bí mật! ATK +20%.",                     "atk_mult": 1.2, "def_mult": 1.0},
    {"msg": "🤝 Không có sự kiện — chiến đấu bình thường.",       "atk_mult": 1.0, "def_mult": 1.0},
    {"msg": "🤝 Không có sự kiện — chiến đấu bình thường.",       "atk_mult": 1.0, "def_mult": 1.0},
]

PRIZE_STEAL_RATE = 0.12
REP_WIN_BONUS    = 15
REP_LOSE_PENALTY = 20
REP_SCANDAL_THRES= 30
CRIT_CHANCE      = 0.12

# ── CHƯƠNG CHÍNH ──────────────────────────────────────────────────────
KF_CHAPTERS = [
    {
        "id": 1, "title": "Chapter 1: Cánh Đồng Quá Khứ",
        "story_intro": (
            "🌸 **Edo, Nhật Bản — Năm 1600**\n\n"
            "Kallen Kaslana đặt chân đến vùng đất Nhật Bản đầy khói lửa. "
            "Làng Yae bị tấn công bởi những xác sống Honkai. "
            "Tiếng la hét vang khắp đêm đen..."
        ),
        "story_mid": (
            "⚔️ **Giữa trận chiến...**\n\n"
            "Một cô bé hồ ly nhỏ đang khóc bên xác mẹ. "
            "Đôi mắt hồng nhìn Kallen với ánh mắt sợ hãi lẫn tin tưởng.\n\n"
            "*\"Đừng sợ... Ta sẽ không để chúng làm hại ngươi.\"*"
        ),
        "story_end": (
            "🌅 **Bình minh ló dạng...**\n\n"
            "Kallen đánh lui đợt tấn công đầu tiên. Cô bé hồ ly — Yae Sakura — "
            "nhìn với đôi mắt ngưỡng mộ. Một tình yêu bắt đầu từ đây."
        ),
        "enemies": [
            {"name": "Zombie Honkai 🧟",     "hp": 120, "atk": 25, "def": 5,  "xp": 30,  "drop": "Thiết Phẩm Kallen ⚙️", "drop_rate": 0.4},
            {"name": "Zombie Chiến Binh 🧟‍♂️", "hp": 160, "atk": 35, "def": 10, "xp": 50,  "drop": "Thiết Phẩm Kallen ⚙️", "drop_rate": 0.5},
            {"name": "Zombie Samurai ⚔️🧟",  "hp": 200, "atk": 45, "def": 15, "xp": 70,  "drop": "Tinh Thể Honkai 💠",    "drop_rate": 0.2},
        ],
        "boss": {
            "name": "Oni Độc — Trùm Zombie 👹",
            "hp": 500, "atk": 65, "def": 20, "xp": 200, "money": 30_000,
            "drop_item": "Thiết Phẩm Kallen ⚙️", "drop_count": 2,
            "title_reward": "Hiệp Sĩ Hắc Bạch ⚔️",
            "skills": ["Tiếng Gầm Oni 😱 (choáng 1 lượt)", "Đấm Sấm Sét 💥 (x1.8)"],
            "lore": "Oni Nhật Bản bị nhiễm Honkai, sức mạnh tăng gấp bội nhưng mất đi lý trí.",
        },
        "waves": 3, "ticket_cost": 1, "reward_money": 15_000,
    },
    {
        "id": 2, "title": "Chapter 2: Bóng Tối Schicksal",
        "story_intro": (
            "🏰 **Lâu đài Schicksal — Châu Âu**\n\n"
            "Kallen nhận lệnh tiêu diệt ổ Honkai tại lâu đài cũ. "
            "Nhưng khi bước vào, cô cảm nhận điều gì đó không ổn...\n\n"
            "Otto Apocalypse âm thầm dõi theo."
        ),
        "story_mid": (
            "🧪 **Phòng thí nghiệm bí mật...**\n\n"
            "Kallen phát hiện Schicksal đang thực hiện thí nghiệm trên người. "
            "Otto xuất hiện, đôi mắt lạnh lùng:\n\n"
            "*\"Đây là vì sự sống còn của nhân loại. Ngươi có hiểu không?\"*"
        ),
        "story_end": (
            "💔 **Vết nứt đầu tiên...**\n\n"
            "Kallen tiêu diệt thí nghiệm thất bại nhưng không thể ngăn Otto. "
            "Lần đầu tiên, cô nghi ngờ tổ chức mình phục vụ."
        ),
        "enemies": [
            {"name": "Lính Phản Bội 🗡️",   "hp": 180, "atk": 40, "def": 15, "xp": 60,  "drop": "Mảnh Nhớ Otto 💌",   "drop_rate": 0.4},
            {"name": "Thực Nghiệm Thể 🧬",  "hp": 220, "atk": 50, "def": 20, "xp": 80,  "drop": "Tinh Thể Honkai 💠",  "drop_rate": 0.3},
            {"name": "Golem Schicksal 🤖",   "hp": 280, "atk": 60, "def": 30, "xp": 100, "drop": "Mảnh Nhớ Otto 💌",   "drop_rate": 0.5},
        ],
        "boss": {
            "name": "Monstrum ☣️ — Thí Nghiệm Thất Bại",
            "hp": 700, "atk": 80, "def": 30, "xp": 300, "money": 50_000,
            "drop_item": "Mảnh Nhớ Otto 💌", "drop_count": 2,
            "title_reward": "Người Bảo Vệ Nhân Loại 🛡️",
            "skills": ["Axit Honkai 🧪 (đốt -20 HP/lượt)", "Tăng Tốc Đột Biến 💉 (x2.0)"],
            "lore": "Người bị biến đổi bởi thí nghiệm Honkai. Không còn nhân tính.",
        },
        "waves": 3, "ticket_cost": 1, "reward_money": 25_000,
    },
    {
        "id": 3, "title": "Chapter 3: Herrscher Xuất Hiện",
        "story_intro": (
            "🌊 **Biển Nhật Bản — Đêm Bão**\n\n"
            "Một Herrscher xuất hiện tại bờ biển. "
            "Làn sóng năng lượng hủy diệt cuộn qua, xóa sạch mọi thứ.\n\n"
            "Fu Hua hạ cánh bên cạnh: *\"Đây là trận chiến của chúng ta.\"*"
        ),
        "story_mid": (
            "💠 **Trong vòng xoáy Honkai...**\n\n"
            "Herrscher cười lạnh: *\"Các ngươi — những con sâu yếu đuối. "
            "Honkai sẽ thanh tẩy thế giới này!\"*\n\n"
            "Ánh sáng kiếm bùng lên trong đêm tối."
        ),
        "story_end": (
            "✨ **Sau cơn bão...**\n\n"
            "Herrscher bị đánh lui. Fu Hua nhìn với ánh mắt đánh giá:\n"
            "*\"Ngươi mạnh hơn ta nghĩ. Nhưng trận chiến thật sự... còn chưa bắt đầu.\"*"
        ),
        "enemies": [
            {"name": "Hầu Vệ Honkai ⚡",    "hp": 250, "atk": 55, "def": 20, "xp": 90,  "drop": "Hồn Ngọc Elysia 💗",   "drop_rate": 0.2},
            {"name": "Cánh Tay Herrscher 🌊","hp": 300, "atk": 65, "def": 25, "xp": 110, "drop": "Hồn Ngọc Elysia 💗","drop_rate": 0.25},
            {"name": "Phân Thân Honkai 👁️",  "hp": 350, "atk": 75, "def": 30, "xp": 130, "drop": "Giọt Máu Herrscher 🩸","drop_rate": 0.3},
        ],
        "boss": {
            "name": "Herrscher of the Void 🌌",
            "hp": 1_000, "atk": 100, "def": 40, "xp": 500, "money": 80_000,
            "drop_item": "Giọt Máu Herrscher 🩸", "drop_count": 3,
            "title_reward": "Kẻ Diệt Honkai 💠",
            "skills": ["Hủy Diệt Hư Không 🌑 (x2.5)", "Biển Honkai 🌊 (30 ST cố định)", "Hấp Thụ 💠 (hồi 100 HP)"],
            "lore": "Herrscher of the Void — ý chí hủy diệt thuần túy của Honkai.",
        },
        "waves": 4, "ticket_cost": 2, "reward_money": 60_000,
    },
    {
        "id": 4, "title": "Chapter 4: Ký Ức Và Phản Bội",
        "story_intro": (
            "🕯️ **Lâu đài Schicksal — Phòng Ký Ức**\n\n"
            "Otto tìm ra cách hồi sinh Kallen bằng Seele. "
            "Nhưng kế hoạch đòi hỏi hi sinh không thể chấp nhận.\n\n"
            "Yae Sakura nhìn Otto với đôi mắt căm hận: *\"Ông sẽ không đụng đến Kallen!\"*"
        ),
        "story_mid": (
            "💔 **Sự thật được hé lộ...**\n\n"
            "Otto đã hi sinh hàng nghìn người để thu thập năng lượng Honkai.\n\n"
            "Kallen — qua Seele — nhìn Otto với đôi mắt buồn:\n"
            "*\"Otto... tại sao ngươi lại làm vậy?\"*\n\n"
            "Lần đầu tiên, Otto Apocalypse khóc."
        ),
        "story_end": (
            "🌙 **Chọn lựa cuối cùng...**\n\n"
            "Kallen chọn ở lại với Seele. Yae Sakura tiếp tục chiến đấu thay Kallen.\n\n"
            "*\"Đây là kết thúc đẹp nhất có thể... phải không, Otto?\"*"
        ),
        "enemies": [
            {"name": "Lính Phản Bội Elite 🗡️","hp": 300, "atk": 70, "def": 30, "xp": 120, "drop": "Mảnh Nhớ Otto 💌",  "drop_rate": 0.5},
            {"name": "Golem Ký Ức 🤖",         "hp": 380, "atk": 80, "def": 35, "xp": 150, "drop": "Lông Vũ Fu Hua 🪶", "drop_rate": 0.3},
            {"name": "Seele Sai Lệch 👻",       "hp": 420, "atk": 90, "def": 25, "xp": 180, "drop": "Mảnh Ký Ức Seele 👻","drop_rate": 0.4},
        ],
        "boss": {
            "name": "Otto — Dạng Bóng Tối 🧪💀",
            "hp": 1_200, "atk": 110, "def": 50, "xp": 700, "money": 100_000,
            "drop_item": "Mảnh Nhớ Otto 💌", "drop_count": 3,
            "title_reward": "Thợ Săn Herrscher 🩸",
            "skills": ["Khải Huyền Đen ☠️ (x3.0)", "Lá Chắn Ký Ức 🛡️ (miễn 1 đòn)", "Triệu Hồi Seele 👻 (hồi 150 HP)"],
            "lore": "Otto khi bị dồn đến cùng cực. Sức mạnh đến từ tình yêu tuyệt vọng.",
        },
        "waves": 4, "ticket_cost": 2, "reward_money": 90_000,
    },
    {
        "id": 5, "title": "Chapter 5: Làn Sóng Cuối Cùng",
        "story_intro": (
            "❄️ **Bắc Cực — Nơi Kevin Chiến Đấu Một Mình**\n\n"
            "Làn sóng Honkai thứ 3 bùng phát. Kevin chiến đấu suốt 1000 năm.\n\n"
            "Elysia đặt tay lên vai: *\"Kevin... đã đến lúc nghỉ ngơi rồi.\"*"
        ),
        "story_mid": (
            "🌌 **Giữa thiên hà Honkai...**\n\n"
            "Aponia, Elysia, Fu Hua — cùng đứng bên Kevin.\n\n"
            "Herrscher cuối cùng xuất hiện — mạnh hơn tất cả:\n"
            "*\"Các ngươi dám chống lại ý chí vũ trụ?\"*\n\n"
            "*\"Ừ.\"* — Kevin mỉm cười lần đầu sau nghìn năm."
        ),
        "story_end": (
            "🌅 **Bình Minh Mới...**\n\n"
            "Honkai bị đánh lui. Kevin cuối cùng có thể nghỉ ngơi.\n\n"
            "Thế giới được cứu bởi tình yêu của tất cả họ dành cho nhau."
        ),
        "enemies": [
            {"name": "Quân Đoàn Honkai 💀",  "hp": 400, "atk": 90,  "def": 40, "xp": 200, "drop": "Giọt Máu Herrscher 🩸","drop_rate": 0.5},
            {"name": "Herrscher Phân Thân 🌑","hp": 500, "atk": 110, "def": 45, "xp": 250, "drop": "Cốt Tủy Kevin ❄️",    "drop_rate": 0.3},
            {"name": "Vệ Binh Vũ Trụ ⭐",    "hp": 600, "atk": 120, "def": 50, "xp": 300, "drop": "Tinh Thể Honkai 💠",   "drop_rate": 0.4},
        ],
        "boss": {
            "name": "Herrscher of Finality — Kẻ Tận Thế 🌌💀",
            "hp": 2_000, "atk": 150, "def": 60, "xp": 1_000, "money": 200_000,
            "drop_item": "Cốt Tủy Kevin ❄️", "drop_count": 3,
            "title_reward": "Huyền Thoại Xà Hầu 🌌",
            "skills": ["Hủy Diệt Toàn Cõi ☄️ (x4.0)", "Honkai Tuyệt Đối 🌌 (80 ST cố định)", "Tái Sinh ♾️ (hồi 300 HP, 1 lần)"],
            "lore": "Herrscher of Finality — hiện thân của sự kết thúc.",
        },
        "waves": 5, "ticket_cost": 3, "reward_money": 180_000,
    },
    {
        "id": 6, "title": "Chapter 6: Lời Hứa Vĩnh Cửu ✨ [SECRET]",
        "story_intro": (
            "🌸 **Vùng Ký Ức — Nơi Không Có Thời Gian**\n\n"
            "Sau tất cả chiến đấu... Kallen thức dậy trong ánh sáng dịu dàng. "
            "Tất cả những người cô yêu thương đều ở đây.\n\n"
            "Otto. Fu Hua. Yae Sakura. Kevin. Elysia. Aponia.\n\n"
            "*\"Đây là... thiên đường sao?\"*\n"
            "*\"Không,\"* Elysia mỉm cười. *\"Đây là ký ức của tất cả chúng ta về ngươi.\"*"
        ),
        "story_mid": (
            "💫 **Thử thách cuối cùng...**\n\n"
            "Ngay cả trong ký ức, Honkai vẫn tìm đến. "
            "Một thực thể bóng tối xuất hiện — tổng hợp của mọi Herrscher.\n\n"
            "*\"Tình yêu của các ngươi chỉ là ảo tưởng!\"*"
        ),
        "story_end": (
            "🌟 **Lời hứa...**\n\n"
            "*\"Tôi không cần tồn tại mãi mãi. Chỉ cần các bạn nhớ đến tôi.\"*\n\n"
            "Otto cúi đầu, giọng vỡ ra: *\"Ta... Ta yêu ngươi.\"*\n\n"
            "**Vì tình yêu — không bao giờ thực sự mất đi.**"
        ),
        "enemies": [
            {"name": "Bóng Tối Ký Ức 👻",    "hp": 500, "atk": 100, "def": 50, "xp": 300, "drop": "Cốt Tủy Kevin ❄️",   "drop_rate": 0.5},
            {"name": "Herrscher Bóng Tối 🌑", "hp": 700, "atk": 130, "def": 55, "xp": 400, "drop": "Giọt Máu Herrscher 🩸","drop_rate": 0.4},
            {"name": "Phantom 👁️",             "hp": 800, "atk": 140, "def": 60, "xp": 500, "drop": "Thiết Phẩm Kallen ⚙️","drop_rate": 0.6},
        ],
        "boss": {
            "name": "Tổng Hợp Herrscher — Bóng Tối Tuyệt Đối 🌑✨",
            "hp": 3_000, "atk": 180, "def": 70, "xp": 2_000, "money": 500_000,
            "drop_item": "Tinh Thể Honkai 💠", "drop_count": 5,
            "title_reward": "Người Kế Thừa Kevin 👑",
            "skills": ["Hư Vô Tuyệt Đối 🌑 (x5.0)", "Xóa Bỏ Ký Ức 👁️ (vô hiệu skill 1 lượt)", "Phục Hồi ♾️ (hồi 500 HP, 2 lần)", "Lời Nguyền ☠️ (đốt 50 HP/lượt x3)"],
            "lore": "Tổng hợp của tất cả Herrscher từng tồn tại.",
        },
        "waves": 6, "ticket_cost": 5, "reward_money": 500_000,
        "secret": True,
    },
    {
        "id": 7, "title": "Chapter 7: Bình Minh Của Vũ Trụ 🌌",
        "story_intro": (
            "🌠 **Không Gian Sâu — Vượt Ra Ngoài Trái Đất**\n\n"
            "Sau khi Honkai bị đánh lui, một nguồn năng lượng mới xuất hiện từ không gian. "
            "Các nhà khoa học phát hiện đây là Honkai thế hệ mới — thông minh hơn, mạnh hơn.\n\n"
            "Seele bay vào vũ trụ đầu tiên, đôi cánh bướm mở rộng trong bóng tối vũ trụ."
        ),
        "story_mid": (
            "🔮 **Trong bóng tối vũ trụ...**\n\n"
            "Seele tìm thấy một hành tinh bị Honkai hóa hoàn toàn. "
            "Trên đó, một thực thể tự xưng là 'Ý Chí Vũ Trụ' nói chuyện với cô:\n\n"
            "*\"Ta không phải kẻ thù. Ta là ký ức của tất cả vũ trụ.\"*\n\n"
            "Seele run nhẹ nhưng không rút lui."
        ),
        "story_end": (
            "🌟 **Bình Minh Vũ Trụ...**\n\n"
            "Seele hiểu ra: Honkai không phải ác — nó chỉ là năng lượng mất kiểm soát. "
            "Cô mở ra cánh cổng để tất cả mọi người cùng chiến đấu.\n\n"
            "*\"Lần này... chúng ta chiến đấu cùng nhau.\"*"
        ),
        "enemies": [
            {"name": "Honkai Vũ Trụ Cấp 1 🛸", "hp": 600,  "atk": 130, "def": 60, "xp": 350, "drop": "Bụi Sao Trời 🌟",   "drop_rate": 0.4},
            {"name": "Honkai Vũ Trụ Cấp 2 ⭐",  "hp": 800,  "atk": 150, "def": 65, "xp": 450, "drop": "Tinh Thể Honkai 💠", "drop_rate": 0.5},
            {"name": "Tinh Linh Vũ Trụ 🌌",      "hp": 1_000,"atk": 160, "def": 70, "xp": 500, "drop": "Bụi Sao Trời 🌟",   "drop_rate": 0.5},
        ],
        "boss": {
            "name": "Ý Chí Vũ Trụ — Primordial 🌠💀",
            "hp": 4_000, "atk": 200, "def": 80, "xp": 3_000, "money": 800_000,
            "drop_item": "Bụi Sao Trời 🌟", "drop_count": 4,
            "title_reward": "Kẻ Chinh Phục Vũ Trụ 🌠",
            "skills": ["Sóng Hủy Diệt Ngân Hà 🌌 (x5.5)", "Hấp Thụ Năng Lượng ♾️ (hồi 400 HP, 2 lần)", "Vụ Nổ Supernova ☄️ (80 ST cố định)"],
            "lore": "Primordial — ý chí đầu tiên của vũ trụ, từ trước khi Honkai tồn tại.",
        },
        "waves": 6, "ticket_cost": 5, "reward_money": 700_000,
    },
    {
        "id": 8, "title": "Chapter 8: Vương Quốc Bóng Tối 🌑",
        "story_intro": (
            "🌑 **Chiều Không Gian Khác — Elysian Realm**\n\n"
            "Một chiều không gian song song bị Honkai xâm chiếm. "
            "Vill-V và Pardofelis được giao nhiệm vụ thám hiểm.\n\n"
            "Nhưng ngay khi bước vào, hai người phát hiện... "
            "những phiên bản tối tăm của chính mình đang chờ đợi."
        ),
        "story_mid": (
            "🎭 **Màn trình diễn nghiêm túc...**\n\n"
            "'Dark Vill-V' cười: *\"Chúng ta giống nhau, Vill. Tại sao không từ bỏ?\"*\n\n"
            "Vill-V cởi mặt nạ lần đầu tiên, đôi mắt thật:\n"
            "*\"Vì tôi đã hứa sẽ bảo vệ họ. Và tôi không phá vỡ lời hứa.\"*"
        ),
        "story_end": (
            "🌸 **Chiến thắng trong bóng tối...**\n\n"
            "Vill-V và Pardofelis đánh bại phiên bản bóng tối của mình. "
            "Chiều không gian được giải phóng.\n\n"
            "*\"Bây giờ...\"* Pardofelis vươn vai, *\"...ta đói rồi.\"*\n"
            "Vill-V cười to lần đầu tiên — tiếng cười thật sự."
        ),
        "enemies": [
            {"name": "Bóng Tối Chiều Khác 🌑",   "hp": 700,  "atk": 140, "def": 65, "xp": 400, "drop": "Mảnh Ký Ức Seele 👻", "drop_rate": 0.5},
            {"name": "Phiên Bản Đen 👁️",          "hp": 900,  "atk": 160, "def": 70, "xp": 500, "drop": "Bụi Sao Trời 🌟",    "drop_rate": 0.4},
            {"name": "Kẻ Chiều Không Gian ⛓️",    "hp": 1100, "atk": 170, "def": 75, "xp": 600, "drop": "Giọt Máu Herrscher 🩸","drop_rate": 0.3},
        ],
        "boss": {
            "name": "Lord of Darkness — Chúa Tể Bóng Tối 🌑👑",
            "hp": 5_000, "atk": 220, "def": 90, "xp": 4_000, "money": 1_000_000,
            "drop_item": "Mảnh Ký Ức Seele 👻", "drop_count": 5,
            "title_reward": "Chúa Tể Bóng Tối 🌑",
            "skills": ["Bóng Tối Tuyệt Đối ☠️ (x6.0)", "Xâm Chiếm Tâm Trí 🌑 (vô hiệu ULT 2 lượt)", "Phục Hồi Bóng Tối ♾️ (hồi 600 HP, 2 lần)", "Cổng Chiều Khác 🌀 (gây 100 ST cố định)"],
            "lore": "Lord of Darkness — thực thể cai trị chiều không gian tối tăm. Mỗi ánh sáng đều trở thành bóng tối trong vương quốc của hắn.",
        },
        "waves": 7, "ticket_cost": 6, "reward_money": 900_000,
    },
    {
        "id": 9, "title": "Chapter 9: Khởi Nguyên 🌅 [FINALE]",
        "story_intro": (
            "🌅 **Khởi Nguyên — Nơi Bắt Đầu Mọi Thứ**\n\n"
            "Tất cả mọi người tập hợp lần cuối. "
            "Một cổng thời gian mở ra, dẫn đến điểm khởi nguyên của Honkai.\n\n"
            "Nếu họ tiêu diệt Honkai tại đây — mọi thứ sẽ thay đổi mãi mãi.\n\n"
            "Kevin nhìn mọi người: *\"Đây là trận cuối. Không có đường trở về.\"*\n"
            "Tất cả đều gật đầu."
        ),
        "story_mid": (
            "⚡ **Tại điểm khởi nguyên...**\n\n"
            "Honkai Nguyên Thủy xuất hiện — không có hình dạng, không có ý chí.\n"
            "Chỉ là năng lượng thuần túy muốn hủy diệt.\n\n"
            "Elysia chạm vào nó: *\"Ngươi... cũng cô đơn phải không?\"*\n\n"
            "Lần đầu tiên, Honkai dừng lại."
        ),
        "story_end": (
            "🌟 **Kết Thúc Và Khởi Đầu...**\n\n"
            "Elysia dùng tình yêu của mình để... không tiêu diệt Honkai, "
            "mà **chữa lành** nó.\n\n"
            "Honkai tan biến không phải vì bị đánh bại — "
            "mà vì cuối cùng nó được **yêu thương**.\n\n"
            "**Thế giới hồi sinh. Không phải vì chiến thắng — vì lòng nhân ái.**\n\n"
            "🌸 *\"Đây là câu chuyện của chúng ta. Và nó sẽ không bao giờ kết thúc.\"*"
        ),
        "enemies": [
            {"name": "Honkai Nguyên Thủy Cấp 1 🌀","hp": 900,   "atk": 160, "def": 75, "xp": 500, "drop": "Vảy Rồng Vua 🐉",  "drop_rate": 0.5},
            {"name": "Honkai Nguyên Thủy Cấp 2 ⚡",  "hp": 1200,  "atk": 180, "def": 80, "xp": 700, "drop": "Bụi Sao Trời 🌟",  "drop_rate": 0.5},
            {"name": "Kẻ Canh Cổng Thời Gian ⏳",     "hp": 1500,  "atk": 200, "def": 85, "xp": 900, "drop": "Vảy Rồng Vua 🐉", "drop_rate": 0.4},
        ],
        "boss": {
            "name": "Honkai Nguyên Thủy — Khởi Nguyên 🌅🔱",
            "hp": 8_000, "atk": 250, "def": 100, "xp": 8_000, "money": 2_000_000,
            "drop_item": "Vảy Rồng Vua 🐉", "drop_count": 6,
            "title_reward": "Thần Chiến Honkai 🔱",
            "skills": [
                "Cơn Thịnh Nộ Khởi Nguyên 🌀 (x7.0)",
                "Xóa Bỏ Lịch Sử ⏳ (reset HP player về 50%)",
                "Phục Hồi Vĩnh Cửu ♾️ (hồi 1000 HP, 3 lần)",
                "Bùng Nổ Honkai ☄️ (120 ST cố định)",
                "Tái Tạo Bản Thân 🔄 (hồi 50% HP khi xuống dưới 30%)",
            ],
            "lore": "Honkai Nguyên Thủy — nguồn gốc của tất cả. Không có ác tâm, chỉ có bản năng hủy diệt. Đây là kẻ thù cuối cùng và cũng là bài học cuối cùng.",
        },
        "waves": 8, "ticket_cost": 8, "reward_money": 2_000_000,
        "finale": True,
    },
]

# ── PHÓ BẢN CHUNG KẾT (RAID) ──────────────────────────────────────────
KF_RAIDS = {
    "raid_dragon": {
        "id": "raid_dragon",
        "name": "⚔️ Thảo Nguyên Rồng Vua 🐉",
        "desc": "Rồng Vua cổ đại trỗi dậy. Cần tối thiểu 2 người, tối đa 4 người.",
        "min_players": 2, "max_players": 4,
        "ticket_cost": 3,
        "boss_hp": 15_000, "boss_atk": 300, "boss_def": 120,
        "boss_skills": [
            "Thở Lửa 🔥 (x4.0 toàn đội)",
            "Vảy Rồng Thiết Giáp 🐉 (giảm 50% sát thương 2 lượt)",
            "Cơn Thịnh Nộ 💢 (x6.0 một người ngẫu nhiên)",
            "Hồi Máu Rồng ♾️ (hồi 800 HP)",
        ],
        "reward_money": 300_000,
        "drop_item": "Vảy Rồng Vua 🐉",
        "drop_count": 3,
        "title_reward": "Truyền Nhân Bất Tử 💎",
        "waves": 3,
    },
    "raid_void": {
        "id": "raid_void",
        "name": "🌌 Hư Không Sâu Thẳm",
        "desc": "Herrscher kép xuất hiện. Cần tối thiểu 3 người, tối đa 4 người.",
        "min_players": 3, "max_players": 4,
        "ticket_cost": 5,
        "boss_hp": 25_000, "boss_atk": 400, "boss_def": 150,
        "boss_skills": [
            "Hư Không Kép 🌌 (x5.0 toàn đội)",
            "Hấp Thụ Năng Lượng 💠 (hồi 2000 HP)",
            "Xóa Bỏ Hiện Thực 👁️ (vô hiệu skill 2 lượt toàn đội)",
            "Sóng Hủy Diệt ☄️ (150 ST cố định toàn đội)",
        ],
        "reward_money": 600_000,
        "drop_item": "Bụi Sao Trời 🌟",
        "drop_count": 5,
        "title_reward": "Truyền Nhân Bất Tử 💎",
        "waves": 5,
    },
}

# ── CỬA HÀNG KF ────────────────────────────────────────────────────────
KF_SHOP_ITEMS = {
    "kf_potion_small": {
        "name": "🧪 Linh Dược Nhỏ",
        "desc": "Hồi 100 HP trong chiến đấu",
        "price": 8_000, "sell": 3_000,
        "type": "consumable", "effect": {"heal": 100},
    },
    "kf_potion_medium": {
        "name": "⚗️ Linh Dược Vừa",
        "desc": "Hồi 200 HP trong chiến đấu",
        "price": 18_000, "sell": 7_000,
        "type": "consumable", "effect": {"heal": 200},
    },
    "kf_potion_large": {
        "name": "🔮 Linh Dược Lớn",
        "desc": "Hồi 400 HP trong chiến đấu",
        "price": 40_000, "sell": 15_000,
        "type": "consumable", "effect": {"heal": 400},
    },
    "kf_mp_drink": {
        "name": "💙 Nước Hồi MP",
        "desc": "Hồi 50 MP trong chiến đấu",
        "price": 12_000, "sell": 5_000,
        "type": "consumable", "effect": {"mp": 50},
    },
    "kf_elixir": {
        "name": "✨ Tiên Dược Honkai",
        "desc": "Hồi 500 HP + 50 MP trong chiến đấu",
        "price": 80_000, "sell": 30_000,
        "type": "consumable", "effect": {"heal": 500, "mp": 50},
    },
    "kf_ticket_bundle": {
        "name": "🎟️ Bộ 5 Vé",
        "desc": "Mua 5 vé cùng lúc tiết kiệm hơn",
        "price": 140_000, "sell": 0,
        "type": "ticket", "effect": {"tickets": 5},
    },
    "vu_khi_thuong": {
        "name": "🗡️ Kiếm Sắt Thường",
        "desc": "Vũ khí phổ thông. ATK +10",
        "price": 5_000, "sell": 2_000,
        "type": "equipment", "equip_id": "vu_khi_thuong",
    },
    "giap_thuong": {
        "name": "🪖 Giáp Sắt Thường",
        "desc": "Giáp phổ thông. DEF +10, HP +20",
        "price": 5_000, "sell": 2_000,
        "type": "equipment", "equip_id": "giap_thuong",
    },
    "phu_kien_thuong": {
        "name": "🔮 Đá Ma Lực Nhỏ",
        "desc": "Phụ kiện thường. ATK +3, DEF +3, HP +10",
        "price": 3_000, "sell": 1_000,
        "type": "equipment", "equip_id": "phu_kien_thuong",
    },
    "vong_co": {
        "name": "💍 Vòng Cổ Honkai",
        "desc": "Phụ kiện Hiếm. ATK +5, DEF +5, HP +30, CRIT +5%",
        "price": 15_000, "sell": 8_000,
        "type": "equipment", "equip_id": "vong_co",
    },
}

# ── COOLDOWN & TRẠNG THÁI ────────────────────────────────────────────
kf_active_games  = {}   # {user_id: KFGameState}
kf_active_raids  = {}   # {raid_id_str: KFRaidState}

# ══════════════════════════════════════════════════════════════════════
# SECTION 2: HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def kf_bar(cur, max_, length=10, fill=None, empty="⬛"):
    if max_ == 0:
        return empty * length
    ratio  = max(0, min(cur, max_)) / max_
    filled = int(ratio * length)
    if fill is None:
        fill = "🟩" if ratio > 0.5 else "🟨" if ratio > 0.25 else "🟥"
    return fill * filled + empty * (length - filled)


def _drop_summary(drops: dict) -> str:
    if not drops:
        return "Không có"
    return " | ".join(f"**{item}** x{cnt}" for item, cnt in drops.items())


def get_kf_user(user_id):
    """Lấy/khởi tạo dữ liệu KF của user."""
    ud = load_user(user_id)
    if "kf" not in ud:
        ud["kf"] = {
            "chars":       ["kallen", "fuhua", "sakura"],
            "progress":    0,
            "char_levels": {c: 1 for c in KF_CHARACTERS},
            "char_exp":    {c: 0 for c in KF_CHARACTERS},
            "equipment":   {c: {"weapon": None, "armor": None, "accessory": None} for c in KF_CHARACTERS},
            "inventory":   {},
            "consumables": {},
            "raid_clears": [],
            "avatar_url":  "",
            "banner_url":  "",
            "bio":         "",
            "total_kills": 0,
            "total_boss_kills": 0,
        }
        save_user(user_id)
    # Patch thiếu key
    kf = ud["kf"]
    for c in KF_CHARACTERS:
        kf.setdefault("char_levels", {})[c] = kf["char_levels"].get(c, 1)
        kf.setdefault("char_exp",    {})[c] = kf["char_exp"].get(c, 0)
        kf.setdefault("equipment",   {})[c] = kf["equipment"].get(c, {"weapon": None, "armor": None, "accessory": None})
    return ud, kf


def save_kf_user(user_id, ud):
    save_user(user_id)


def get_char_stats(char_id, kf_data):
    """Tính chỉ số nhân vật bao gồm level và trang bị."""
    base = KF_CHARACTERS[char_id]
    lv   = kf_data["char_levels"].get(char_id, 1)
    lv_bonus = (lv - 1) * 0.05  # +5% mỗi level

    atk  = int(base["atk"]  * (1 + lv_bonus))
    def_ = int(base["def"]  * (1 + lv_bonus))
    hp   = int(base["hp"]   * (1 + lv_bonus))
    crit = base.get("crit", 10)

    # Trang bị
    equip = kf_data["equipment"].get(char_id, {})
    for slot, eid in equip.items():
        if eid and eid in KF_EQUIPMENT:
            eq = KF_EQUIPMENT[eid]
            atk  += eq.get("atk",  0)
            def_ += eq.get("def",  0)
            hp   += eq.get("hp",   0)
            crit += eq.get("crit", 0)

    return {"atk": atk, "def": def_, "hp": hp, "crit": min(crit, 60), "lv": lv}


def exp_to_level_up(lv):
    return int(100 * (lv ** 1.5))


def get_char_equip_bonus_desc(char_id, kf_data):
    equip = kf_data["equipment"].get(char_id, {})
    lines = []
    for slot, eid in equip.items():
        if eid and eid in KF_EQUIPMENT:
            eq = KF_EQUIPMENT[eid]
            bonus = eq.get("char_bonus", {}).get(char_id, "")
            lines.append(f"  {eq['name']}" + (f" — *{bonus}*" if bonus else ""))
    return "\n".join(lines) if lines else "  Không có trang bị"


def rarity_emoji(r):
    return RARITY_COLOR.get(r, "⚪")


# ══════════════════════════════════════════════════════════════════════
# SECTION 3: GAME STATE CLASSES
# ══════════════════════════════════════════════════════════════════════

class KFGameState:
    def __init__(self, user_id, char_id, chapter_idx, kf_data):
        self.user_id     = str(user_id)
        self.char_id     = char_id
        self.chapter_idx = chapter_idx
        self.chapter     = KF_CHAPTERS[chapter_idx]
        kf_data          = kf_data

        stats            = get_char_stats(char_id, kf_data)
        self.hp          = stats["hp"]
        self.max_hp      = stats["hp"]
        self.atk         = stats["atk"]
        self.def_        = stats["def"]
        self.crit_rate   = stats["crit"] / 100
        self.lv          = stats["lv"]

        self.mp          = 0
        self.max_mp      = 100

        # Kevin stack
        self.kevin_stacks  = 0
        self.kevin_charges = 0  # giáp Kevin

        # Trạng thái
        self.phase         = "wave"
        self.wave          = 0
        self.enemy         = None
        self.enemy_hp      = 0
        self.enemy_max_hp  = 0
        self.turn          = 0

        self.shield        = False
        self.def_boost     = 0
        self.burn_dmg      = 0
        self.burn_turns    = 0
        self.stunned       = False
        self.invincible    = False
        self.ult_blocked   = False
        self.ult_block_turns = 0

        # Phần thưởng
        self.total_xp    = 0
        self.total_money = 0
        self.drops       = {}

        # Trang bị bonus
        self.equip       = kf_data.get("equipment", {}).get(char_id, {})
        self.kallen_last_stand = False  # giáp Kallen

        # Consumables còn lại trong ván
        self.consumables = dict(kf_data.get("consumables", {}))

        # Auto dùng vật phẩm gắn nhân vật
        self._apply_char_equip_passives()

    def _apply_char_equip_passives(self):
        """Áp dụng passive trang bị lúc vào trận."""
        for slot, eid in self.equip.items():
            if not eid or eid not in KF_EQUIPMENT:
                continue
            eq = KF_EQUIPMENT[eid]
            bonus = eq.get("char_bonus", {}).get(self.char_id, "")
            if "không chết" in bonus.lower():
                self.kallen_last_stand = True

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def gain_mp(self, amount):
        self.mp = min(self.max_mp, self.mp + amount)

    def take_damage(self, raw_dmg):
        if self.invincible:
            return 0
        if self.shield:
            self.shield = False
            return 0
        reduction = self.def_ / (self.def_ + 100)
        reduction += self.def_boost / 100
        reduction  = min(0.85, reduction)
        actual     = max(1, int(raw_dmg * (1 - reduction)))
        self.hp   -= actual
        if self.hp <= 0 and self.kallen_last_stand:
            self.hp = 1
            self.kallen_last_stand = False
        return actual

    def is_dead(self):
        return self.hp <= 0

    def next_wave_enemy(self):
        self.wave  += 1
        self.turn   = 0
        self.stunned = False
        self.burn_dmg = 0
        self.burn_turns = 0
        pool = self.chapter["enemies"]
        tmpl = pool[-1] if self.wave == self.chapter["waves"] else random.choice(pool)
        self.enemy      = dict(tmpl)
        self.enemy_hp   = tmpl["hp"]
        self.enemy_max_hp = tmpl["hp"]

    def load_boss(self):
        boss = self.chapter["boss"]
        self.enemy      = dict(boss)
        self.enemy_hp   = boss["hp"]
        self.enemy_max_hp = boss["hp"]
        self.wave       = 99
        self.turn       = 0
        self.stunned    = False
        self.burn_dmg   = 0
        self.burn_turns = 0
        self.ult_blocked = False
        self.ult_block_turns = 0


class KFBattleView(discord.ui.View):
    def __init__(self, user_id, state: KFGameState):
        super().__init__(timeout=180)
        self.user_id  = str(user_id)
        self.state    = state
        self.finished = False          # FLAG chống double-process
        self.update_buttons()
 
    # ── Tự dọn dẹp khi timeout ──────────────────────────────────────
    async def on_timeout(self):
        if self.finished:
            return
        self.finished = True
        uid = self.user_id
 
        # Xóa khỏi active games
        kf_active_games.pop(uid, None)
 
        # Lưu XP + drops đã kiếm được
        try:
            state = self.state
            ud, kf = get_kf_user(uid)
            cid = state.char_id
            kf["char_exp"][cid] = kf["char_exp"].get(cid, 0) + state.total_xp
            while kf["char_exp"][cid] >= exp_to_level_up(kf["char_levels"].get(cid, 1)):
                kf["char_exp"][cid] -= exp_to_level_up(kf["char_levels"][cid])
                kf["char_levels"][cid] = kf["char_levels"].get(cid, 1) + 1
            for item, cnt in state.drops.items():
                kf["inventory"][item] = kf["inventory"].get(item, 0) + cnt
            if state.total_money > 0:
                ud["money"] = ud.get("money", 0) + state.total_money
            kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}
            save_kf_user(uid, ud)
        except Exception as e:
            print(f"[KF] on_timeout save error for {uid}: {e}")
 
        # Disable tất cả nút
        for item in self.children:
            item.disabled = True
 
    def update_buttons(self):
        state = self.state
        for item in self.children:
            if not hasattr(item, "label"):
                continue
            lbl = str(item.label)
            if "ULT" in lbl:
                ready = state.mp >= state.max_mp and not state.ult_blocked
                item.disabled = not ready
                item.label = f"3️⃣ ULT {'✅' if ready else f'({state.mp}/{state.max_mp}MP)'}"
            elif lbl.startswith("4️⃣"):
                cnt = sum(v for k, v in state.consumables.items() if any(
                    kw in k for kw in ["Dược", "Tiên", "Elixir"]
                ))
                item.label = f"4️⃣ 💊({cnt})"
                item.disabled = cnt <= 0
            elif lbl.startswith("5️⃣"):
                cnt = state.consumables.get("💙 Nước Hồi MP", 0)
                item.label = f"5️⃣ 💙({cnt})"
                item.disabled = cnt <= 0
 
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Đây không phải ván của bạn!", ephemeral=True
            )
            return False
        return True
 
    # ── Guard chống double-click ──────────────────────────────────────
    async def _guard(self, interaction) -> bool:
        if self.finished:
            await interaction.response.send_message(
                "⚠️ Trận đã kết thúc. Dùng `k kallen choi` để chơi lại.",
                ephemeral=True
            )
            return False
        return True
 
    # ══════════════════════════════════════════════════════════════════
    # NÚT KỸ NĂNG
    # ══════════════════════════════════════════════════════════════════
    @discord.ui.button(label="1️⃣ ATK", style=discord.ButtonStyle.danger, row=0)
    async def btn_atk(self, interaction, button):
        if not await self._guard(interaction):
            return
        await self.do_skill(interaction, "atk")
 
    @discord.ui.button(label="2️⃣ DEF", style=discord.ButtonStyle.primary, row=0)
    async def btn_def(self, interaction, button):
        if not await self._guard(interaction):
            return
        await self.do_skill(interaction, "def")
 
    @discord.ui.button(label="3️⃣ ULT ✨", style=discord.ButtonStyle.success, row=0)
    async def btn_ult(self, interaction, button):
        if not await self._guard(interaction):
            return
        await self.do_skill(interaction, "ult")
 
    @discord.ui.button(label="4️⃣ 💊(0)", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def btn_potion(self, interaction, button):
        if not await self._guard(interaction):
            return
        state = self.state
        priority = [
            "✨ Tiên Dược Honkai",
            "🔮 Linh Dược Lớn",
            "⚗️ Linh Dược Vừa",
            "🧪 Linh Dược Nhỏ",
        ]
        used = next((p for p in priority if state.consumables.get(p, 0) > 0), None)
        if not used:
            return await interaction.response.send_message("Không còn thuốc!", ephemeral=True)
 
        state.consumables[used] -= 1
        heal_amt = 0
        mp_amt   = 0
        for v in KF_SHOP_ITEMS.values():
            if v["name"] == used:
                heal_amt = v.get("effect", {}).get("heal", 0)
                mp_amt   = v.get("effect", {}).get("mp", 0)
                break
 
        if heal_amt:
            state.heal(heal_amt)
        if mp_amt:
            state.gain_mp(mp_amt)
 
        self.update_buttons()
        log_msg = f"💊 Dùng **{used}** → Hồi **{heal_amt} HP**"
        if mp_amt:
            log_msg += f" + **{mp_amt} MP**"
        await interaction.response.edit_message(
            embed=kf_battle_embed(state, log_msg), view=self
        )
 
    @discord.ui.button(label="5️⃣ 💙(0)", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def btn_mp(self, interaction, button):
        if not await self._guard(interaction):
            return
        state = self.state
        cnt = state.consumables.get("💙 Nước Hồi MP", 0)
        if cnt <= 0:
            return await interaction.response.send_message("Không còn nước MP!", ephemeral=True)
        state.consumables["💙 Nước Hồi MP"] -= 1
        state.gain_mp(50)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=kf_battle_embed(state, f"💙 **Nước Hồi MP** → +50 MP! MP: **{state.mp}/{state.max_mp}**"),
            view=self,
        )
 
    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.secondary, row=1)
    async def btn_flee(self, interaction, button):
        if not await self._guard(interaction):
            return
        self.finished = True
        state = self.state
        kf_active_games.pop(self.user_id, None)
        self.stop()
        for item in self.children:
            item.disabled = True
 
        # Lưu tiến độ
        ud, kf = get_kf_user(self.user_id)
        cid = state.char_id
        kf["char_exp"][cid] = kf["char_exp"].get(cid, 0) + state.total_xp
        while kf["char_exp"][cid] >= exp_to_level_up(kf["char_levels"].get(cid, 1)):
            kf["char_exp"][cid] -= exp_to_level_up(kf["char_levels"][cid])
            kf["char_levels"][cid] = kf["char_levels"].get(cid, 1) + 1
        for item2, cnt in state.drops.items():
            kf["inventory"][item2] = kf["inventory"].get(item2, 0) + cnt
        if state.total_money > 0:
            ud["money"] = ud.get("money", 0) + state.total_money
        kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}
        save_kf_user(self.user_id, ud)
 
        embed = discord.Embed(
            title="🚪 Rút Lui",
            description=(
                f"Đã thoát khỏi **{state.chapter['title']}**\n\n"
                f"⭐ XP lưu: **+{state.total_xp}**\n"
                f"💰 Tiền lưu: **+{state.total_money:,} 💰**\n"
                f"📦 {_drop_summary(state.drops)}"
            ),
            color=discord.Color.dark_grey(),
        )
        await interaction.response.edit_message(embed=embed, view=self)
 
    # ══════════════════════════════════════════════════════════════════
    # LOGIC CHIẾN ĐẤU (giữ nguyên logic, chỉ bọc try/except)
    # ══════════════════════════════════════════════════════════════════
    async def do_skill(self, interaction, skill_key: str):
        try:
            await self._do_skill_inner(interaction, skill_key)
        except Exception as e:
            print(f"[KF] do_skill error for {self.user_id}: {e}")
            self.finished = True
            kf_active_games.pop(self.user_id, None)
            try:
                await interaction.response.send_message(
                    "⚠️ Lỗi chiến đấu! Trận đã kết thúc. Dùng `k kallen thoat` nếu còn kẹt.",
                    ephemeral=True,
                )
            except Exception:
                pass
 
    async def _do_skill_inner(self, interaction, skill_key: str):
        state  = self.state
        char   = KF_CHARACTERS[state.char_id]
        skill  = char["skills"][skill_key]
        log    = []
 
        # Kiểm tra MP và ULT block
        if skill["mp"] > 0 and state.mp < skill["mp"]:
            return await interaction.response.send_message(
                f"⚠️ Thiếu **{skill['mp']} MP**! Hiện có **{state.mp} MP**.", ephemeral=True
            )
        if skill_key == "ult" and state.ult_blocked:
            return await interaction.response.send_message("🚫 ULT đang bị phong ấn!", ephemeral=True)
 
        state.turn += 1
 
        # Giảm ult block timer
        if state.ult_block_turns > 0:
            state.ult_block_turns -= 1
            if state.ult_block_turns == 0:
                state.ult_blocked = False
                log.append("✅ ULT đã được giải phong!")
 
        # Đốt đầu lượt
        if state.burn_turns > 0:
            dmg = state.burn_dmg
            state.hp = max(1, state.hp - dmg)
            state.burn_turns -= 1
            log.append(f"🔥 Bỏng đốt **-{dmg} HP** (còn {state.burn_turns} lượt)")
 
        # Elysia passive heal đầu lượt
        if state.char_id == "elysia":
            state.heal(15)
            log.append("💗 Elysia passive: **+15 HP**")
 
        # Tính CRIT
        kevin_mult   = 1.0
        if state.char_id == "kevin":
            kevin_mult = 1 + min(state.kevin_stacks, 10) * 0.05
 
        crit       = random.random() < state.crit_rate
        crit_mult  = 1.8 if crit else 1.0
        seele_dbl  = state.char_id == "seele" and crit
        if seele_dbl:
            crit_mult = 2.5
 
        # ─────────────────── PLAYER ACTION ──────────────────────────
        if skill_key == "atk":
            state.mp -= skill["mp"]
            mult = skill["mult"] * kevin_mult
            if state.wave == 99 and state.char_id == "kallen":
                mult *= 1.2
            if state.char_id == "sakura":
                mult *= 1.25
            dmg = int(state.atk * mult * crit_mult * random.uniform(0.9, 1.1))
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            state.gain_mp(20)
            if state.char_id == "kevin":
                state.kevin_stacks = min(state.kevin_stacks + 1, 10)
            c_str = " 💥**CRIT!**" if crit else ""
            d_str = " 🦋**+HIT!**" if seele_dbl else ""
            log.append(f"⚔️ **{skill['name']}**{c_str}{d_str} → 🩸 **{dmg} ST**")
            if seele_dbl and state.enemy_hp > 0:
                dmg2 = int(state.atk * skill["mult"] * random.uniform(0.7, 0.9))
                state.enemy_hp = max(0, state.enemy_hp - dmg2)
                log.append(f"  🦋 Bướm Đêm tấn công thêm → **{dmg2} ST**")
            # Aponia stun
            if state.char_id == "aponia" and random.random() < 0.25:
                state.stunned = True
                log.append("  ⛓️ Choáng kẻ thù lượt tiếp!")
 
        elif skill_key == "def":
            state.mp -= skill["mp"]
            self._apply_def_skill(state, char, log)
 
        elif skill_key == "ult":
            state.mp = 0
            mult = skill["mult"] * kevin_mult
            if state.wave == 99 and state.char_id == "kallen":
                mult *= 1.2
            if state.char_id == "sakura":
                mult *= 1.25
            dmg = int(state.atk * mult * crit_mult * random.uniform(0.9, 1.1))
            state.enemy_hp = max(0, state.enemy_hp - dmg)
            c_str = " 💥**CRIT!**" if crit else ""
 
            if state.char_id == "elysia":
                state.heal(50)
                log.append(f"🌸 **{skill['name']}**{c_str} → **{dmg} ST** + 💗 hồi **50 HP**")
            elif state.char_id == "pardofelis":
                state.stunned = True
                log.append(f"🌋 **{skill['name']}**{c_str} → **{dmg} ST** + 😵 choáng 2 lượt")
            elif state.char_id == "seele":
                log.append(f"🦋 **{skill['name']}**{c_str} → **{dmg} ST** ✨ CRIT rate tăng lượt này!")
            else:
                log.append(f"✨ **{skill['name']}**{c_str} → 🩸 **{dmg} ST**!")
            if state.char_id == "kevin":
                state.kevin_stacks = 0
 
        # Fu Hua kill heal
        if state.char_id == "fuhua" and state.enemy_hp <= 0 and state.wave != 99:
            state.heal(30)
 
        # Enemy chết
        if state.enemy_hp <= 0:
            await self.on_enemy_die(interaction, log)
            return
 
        # ─────────────────── ENEMY TURN ─────────────────────────────
        state.invincible = False
        self._do_enemy_turn(state, log, interaction)
 
        # Kevin giáp charge
        if state.char_id == "kevin":
            state.kevin_charges += 1
            if state.kevin_charges >= 5:
                state.shield       = True
                state.kevin_charges = 0
                log.append("❄️ **Kevin Giáp**: Tích 5 charge → 🛡️ Tự né đòn tiếp!")
 
        # Reset def boost
        state.def_boost = 0
        state.gain_mp(10)
 
        if state.is_dead():
            await self.on_player_die(interaction, log)
            return
 
        self.update_buttons()
        await interaction.response.edit_message(
            embed=kf_battle_embed(state, "\n".join(log)), view=self
        )
 
    def _apply_def_skill(self, state, char, log):
        sk = char["skills"]["def"]
        cid = state.char_id
        if cid == "fuhua":
            state.shield = True
            log.append(f"🛡️ **{sk['name']}** → ✨ Sẽ né hoàn toàn đòn tiếp theo!")
        elif cid == "kallen":
            state.def_boost = 40
            log.append(f"🛡️ **{sk['name']}** → 🔰 Giảm **40% ST** lượt này!")
        elif cid == "sakura":
            state.def_boost = 25
            log.append(f"📿 **{sk['name']}** → 🌸 Hút **25% ST** thành HP!")
        elif cid == "otto":
            state.def_boost = 50
            log.append(f"⚡ **{sk['name']}** → 🛡️ Giảm **50% ST** + Phản **20%**!")
        elif cid == "kevin":
            state.invincible = True
            state.heal(50)
            log.append(f"💀 **{sk['name']}** → 🔰 Bất tử lượt này + 💗 Hồi **50 HP**!")
        elif cid == "elysia":
            state.heal(60)
            state.def_boost = 30
            log.append(f"🤗 **{sk['name']}** → 💗 Hồi **60 HP** + 🛡️ Giảm **30% ST**!")
        elif cid == "aponia":
            state.def_boost = 45
            log.append(f"🙏 **{sk['name']}** → 🛡️ Giảm **45% ST** + Phản **15%**!")
        elif cid == "seele":
            state.shield = True
            log.append(f"👻 **{sk['name']}** → ✨ Né đòn + Phản **0.5x**!")
        elif cid == "vill_v":
            state.def_boost = 25
            log.append(f"🎩 **{sk['name']}** → 🛡️ Giảm **25% ST** + Phản **25%**!")
        elif cid == "pardofelis":
            state.def_boost = 50
            state.heal(20)
            log.append(f"🐱 **{sk['name']}** → 🛡️ Giảm **50% ST** + 💗 Hồi **20 HP**!")
        else:
            state.def_boost = 30
            log.append(f"🛡️ **{sk['name']}** → Phòng thủ **30%**!")
 
    def _do_enemy_turn(self, state, log, interaction):
        if state.stunned:
            log.append(f"😵 **{state.enemy['name']}** bị choáng — bỏ lượt!")
            state.stunned = False
            return
 
        enemy   = state.enemy
        is_boss = state.wave == 99
 
        if is_boss and state.turn % 3 == 0 and enemy.get("skills"):
            self._boss_special(state, enemy, log)
        else:
            raw = int(enemy["atk"] * random.uniform(0.85, 1.15))
            self._apply_enemy_hit(state, raw, enemy["name"], log)
 
        # Rare boss burn
        if is_boss and random.random() < 0.08:
            state.burn_dmg   = 20
            state.burn_turns = 2
            log.append("🔥 Boss gây **đốt** → -20 HP/lượt trong 2 lượt!")
 
        # Pardofelis charge khi bị đánh
        if state.char_id == "pardofelis":
            state.gain_mp(10)
 
    def _boss_special(self, state, enemy, log):
        skill_str = random.choice(enemy["skills"])
        s = skill_str.lower()
 
        if "hồi" in s:
            nums = [int(w) for w in skill_str.split() if w.isdigit()]
            heal_a = nums[0] if nums else 200
            state.enemy_hp = min(state.enemy_max_hp, state.enemy_hp + heal_a)
            log.append(f"👿 **{skill_str.split('(')[0].strip()}** → 💚 Boss hồi **{heal_a} HP**!")
            return
 
        if "reset" in s or "50%" in s:
            state.hp = max(1, state.hp // 2)
            log.append(f"👿 **{skill_str.split('(')[0].strip()}** → ⚡ HP bạn bị giảm 50%!")
            return
 
        if "vô hiệu" in s or "phong ấn" in s:
            state.ult_blocked    = True
            state.ult_block_turns = 2
            raw = int(enemy["atk"] * 0.5)
            actual = state.take_damage(raw)
            log.append(f"👿 **{skill_str.split('(')[0].strip()}** → 🚫 ULT bị phong ấn + **{actual} ST**!")
            return
 
        # Damage multiplier
        if "x" in skill_str:
            try:
                mult = float(skill_str.split("x")[1].split(" ")[0].rstrip(")"))
            except Exception:
                mult = 2.0
            raw = int(enemy["atk"] * mult * random.uniform(0.9, 1.1))
        elif "ST" in skill_str:
            nums = [int(w) for w in skill_str.split() if w.isdigit()]
            raw = nums[0] if nums else 80
        else:
            raw = enemy["atk"]
 
        self._apply_enemy_hit(state, raw, f"Boss — {skill_str.split('(')[0].strip()}", log)
 
    def _apply_enemy_hit(self, state, raw, source_name, log):
        actual = state.take_damage(raw)
        # Phản đòn
        reflect = 0
        if state.char_id == "otto" and state.def_boost >= 50:
            reflect = int(actual * 0.2)
        elif state.char_id == "vill_v" and state.def_boost >= 25:
            reflect = int(actual * 0.25)
        elif state.char_id == "aponia" and state.def_boost >= 45:
            reflect = int(actual * 0.15)
        elif state.char_id == "seele" and state.shield:
            reflect = int(raw * 0.5)
            actual  = 0  # shield đã né
            state.shield = False
 
        if reflect:
            state.enemy_hp = max(0, state.enemy_hp - reflect)
 
        # Sakura hút sát thương
        if state.char_id == "sakura" and state.def_boost >= 25 and actual > 0:
            absorb = int(actual * 0.25)
            state.heal(absorb)
            log.append(
                f"👾 **{source_name}** → 🩸 **{actual} ST** | 🌸 Hút **{absorb} HP**"
                + (f" | Phản **{reflect} ST**" if reflect else "")
            )
            return
 
        dmg_str = f"🩸 **{actual} ST**" if actual else "🛡️ **NÉ!**"
        ref_str = f" | ⚡ Phản **{reflect} ST**" if reflect else ""
        log.append(f"👾 **{source_name}** → {dmg_str}{ref_str}")
 
    # ══════════════════════════════════════════════════════════════════
    # ENEMY DIE / PLAYER DIE / FINISH
    # ══════════════════════════════════════════════════════════════════
    async def on_enemy_die(self, interaction, log):
        state   = self.state
        enemy   = state.enemy
        is_boss = state.wave == 99
 
        xp = enemy.get("xp", 50)
        state.total_xp += xp
        log.append(f"💀 **{enemy['name']}** bị tiêu diệt! ✨ **+{xp} XP**")
 
        if state.char_id == "fuhua" and not is_boss:
            state.heal(30)
            log.append("🦅 Fu Hua passive: 💗 Hồi **30 HP**")
 
        # Drop
        if not is_boss and random.random() < enemy.get("drop_rate", 0.3):
            drop = enemy.get("drop", "Tinh Thể Honkai 💠")
            state.drops[drop] = state.drops.get(drop, 0) + 1
            log.append(f"📦 Drop: **{drop}**!")
 
        if is_boss:
            self.finished = True
            await self.finish_chapter(interaction, log)
            return
 
        if state.wave >= state.chapter["waves"]:
            # Load boss
            state.load_boss()
            boss_intro = (
                f"\n{'═'*28}\n"
                f"👿 **BOSS XUẤT HIỆN!**\n"
                f"🔴 **{state.enemy['name']}**\n"
                f"*{state.enemy.get('lore', '')}*\n"
            )
            for bs in state.enemy.get("skills", []):
                boss_intro += f"  ⚠️ {bs}\n"
            self.update_buttons()
            await interaction.response.edit_message(
                embed=kf_battle_embed(state, "\n".join(log) + boss_intro, color=discord.Color.dark_red()),
                view=self,
            )
        else:
            state.next_wave_enemy()
            log.append(
                f"\n{'─'*28}\n"
                f"👾 Wave **{state.wave}/{state.chapter['waves']}**: **{state.enemy['name']}** xuất hiện!"
            )
            self.update_buttons()
            await interaction.response.edit_message(
                embed=kf_battle_embed(state, "\n".join(log)), view=self
            )
 
    async def on_player_die(self, interaction, log):
        self.finished = True
        kf_active_games.pop(self.user_id, None)
        self.stop()
        for item in self.children:
            item.disabled = True
 
        log.append(f"\n💀 **{KF_CHARACTERS[self.state.char_id]['name']}** đã ngã xuống...")
 
        ud, kf = get_kf_user(self.user_id)
        state  = self.state
        cid    = state.char_id
        kf["char_exp"][cid] = kf["char_exp"].get(cid, 0) + state.total_xp
        while kf["char_exp"][cid] >= exp_to_level_up(kf["char_levels"].get(cid, 1)):
            kf["char_exp"][cid] -= exp_to_level_up(kf["char_levels"][cid])
            kf["char_levels"][cid] = kf["char_levels"].get(cid, 1) + 1
        for item2, cnt in state.drops.items():
            kf["inventory"][item2] = kf["inventory"].get(item2, 0) + cnt
        kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}
        save_kf_user(self.user_id, ud)
 
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="💀 THẤT BẠI",
                description="\n".join(log[-6:]) + f"\n\n📦 XP: **+{state.total_xp}** | {_drop_summary(state.drops)}",
                color=discord.Color.dark_red(),
            ),
            view=self,
        )
 
    async def finish_chapter(self, interaction, log):
        state   = self.state
        chapter = state.chapter
        boss    = chapter["boss"]
        uid     = self.user_id
 
        kf_active_games.pop(uid, None)
        self.stop()
        for item in self.children:
            item.disabled = True
 
        money_r = chapter["reward_money"]
        state.total_money += money_r
        di, dc  = boss.get("drop_item"), boss.get("drop_count", 1)
        if di:
            state.drops[di] = state.drops.get(di, 0) + dc
 
        ud, kf = get_kf_user(uid)
        cid    = state.char_id
        kf["char_exp"][cid] = kf["char_exp"].get(cid, 0) + state.total_xp
        lv_ups = []
        while kf["char_exp"][cid] >= exp_to_level_up(kf["char_levels"].get(cid, 1)):
            kf["char_exp"][cid] -= exp_to_level_up(kf["char_levels"][cid])
            kf["char_levels"][cid] = kf["char_levels"].get(cid, 1) + 1
            lv_ups.append(f"⬆️ **{KF_CHARACTERS[cid]['name']}** lên **Lv{kf['char_levels'][cid]}**!")
 
        for item2, cnt in state.drops.items():
            kf["inventory"][item2] = kf["inventory"].get(item2, 0) + cnt
        kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}
        ud["money"] = ud.get("money", 0) + state.total_money
 
        chid = chapter["id"]
        if chid > kf.get("progress", 0):
            kf["progress"] = chid
 
        title_r = boss.get("title_reward", "")
        title_line = ""
        if title_r and title_r not in ud.get("assets", []):
            ud.setdefault("assets", []).append(title_r)
            title_line = f"\n🏷️ **Danh hiệu mới: {title_r}**"
 
        kf["total_boss_kills"] = kf.get("total_boss_kills", 0) + 1
        save_kf_user(uid, ud)
        add_history(uid, f"KF C{chid} ✅ (+{state.total_money:,} 💰)")
 
        unlock_line = ""
        if chid == 5:
            unlock_line = "\n🌟 **Chapter 6 (SECRET) đã mở khóa!**"
        elif chid == 6:
            unlock_line = "\n🌟 **Chapter 7 đã mở khóa!**"
        elif chid == 8:
            unlock_line = "\n🌟 **Chapter 9 FINALE đã mở khóa!**"
 
        desc = (
            chapter["story_end"] +
            f"\n\n{'═'*28}\n"
            f"💰 Tiền: **+{state.total_money:,} 💰**\n"
            f"⭐ XP: **+{state.total_xp}**\n"
            f"📦 {_drop_summary(state.drops)}"
            f"{title_line}{unlock_line}"
        )
        if lv_ups:
            desc += "\n" + "\n".join(lv_ups)
 
        result = discord.Embed(
            title=f"🎉 CHIẾN THẮNG! — {chapter['title']}",
            description=desc,
            color=discord.Color.gold(),
        )
        result.set_footer(text="k kallen choi → chơi tiếp | k kallen char → nâng cấp nhân vật")
        await interaction.response.edit_message(embed=result, view=self)
 
 
# ══════════════════════════════════════════════════════════════════════
# FIX 3: kf_battle_embed MỚI — GIAO DIỆN ĐẸP HƠN
# THAY THẾ function kf_battle_embed cũ
# ══════════════════════════════════════════════════════════════════════
 
def kf_battle_embed(state: KFGameState, msg: str = "", color=None) -> discord.Embed:
    char    = KF_CHARACTERS[state.char_id]
    is_boss = state.wave == 99
 
    if color is None:
        color = discord.Color.dark_red() if is_boss else discord.Color.purple()
 
    # ── Thanh HP/MP ──────────────────────────────────────────────────
    hp_pct = max(0, state.hp) / state.max_hp
    mp_pct = state.mp / state.max_mp
 
    def hp_bar(cur, max_, length=12):
        if max_ == 0:
            return "⬛" * length
        r = max(0, min(cur, max_)) / max_
        f = int(r * length)
        fill = "🟩" if r > 0.5 else "🟨" if r > 0.25 else "🟥"
        return fill * f + "⬛" * (length - f)
 
    def mp_bar_fn(cur, max_, length=8):
        if max_ == 0:
            return "⬛" * length
        f = int(min(cur, max_) / max_ * length)
        return "🟦" * f + "⬜" * (length - f)
 
    def enemy_bar(cur, max_, length=12):
        if max_ == 0:
            return "⬛" * length
        r = max(0, min(cur, max_)) / max_
        f = int(r * length)
        fill = "🟥" if r > 0.5 else "🟧" if r > 0.25 else "💔"
        return fill * f + "⬛" * (length - f)
 
    # ── Trạng thái nhân vật ──────────────────────────────────────────
    status_icons = []
    if state.invincible:   status_icons.append("🔰")
    if state.shield:       status_icons.append("✨NÉ")
    if state.def_boost>0:  status_icons.append(f"🛡️+{int(state.def_boost)}%")
    if state.burn_turns>0: status_icons.append(f"🔥{state.burn_dmg}×{state.burn_turns}")
    if state.ult_blocked:  status_icons.append("🚫ULT")
    if state.kevin_stacks: status_icons.append(f"⚡×{state.kevin_stacks}")
    status_str = "  ".join(status_icons)
 
    # ── Tiêu đề ──────────────────────────────────────────────────────
    wave_str = "BOSS 👿" if is_boss else f"Wave {state.wave}/{state.chapter['waves']}"
    title    = f"{'⚔️' if not is_boss else '💀'} {state.chapter['title'].split(':')[1].strip()} [{wave_str}]"
 
    embed = discord.Embed(title=title, color=color)
 
    # ── Nhân vật ─────────────────────────────────────────────────────
    hp_display = hp_bar(state.hp, state.max_hp)
    mp_display = mp_bar_fn(state.mp, state.max_mp)
    lv = state.lv
 
    player_val = (
        f"❤️ `{hp_display}` **{max(0,state.hp)}/{state.max_hp}**\n"
        f"💙 `{mp_display}` **{state.mp}/{state.max_mp} MP**"
    )
    if status_str:
        player_val += f"\n{status_str}"
 
    embed.add_field(
        name  = f"🗡️ {char['name']}  Lv{lv}  •  {char['element']}",
        value = player_val,
        inline= True,
    )
 
    # ── Kẻ thù ───────────────────────────────────────────────────────
    if state.enemy:
        stun_str = "  😵 CHOÁNG" if state.stunned else ""
        e_hp_bar = enemy_bar(state.enemy_hp, state.enemy_max_hp)
        embed.add_field(
            name  = f"{'👿 BOSS' if is_boss else '👾'} {state.enemy['name']}{stun_str}",
            value = f"❤️ `{e_hp_bar}` **{max(0,state.enemy_hp):,}/{state.enemy_max_hp:,}**",
            inline= True,
        )
 
    embed.add_field(name="\u200b", value="\u200b", inline=False)  # spacer
 
    # ── Kỹ năng ──────────────────────────────────────────────────────
    skills    = char["skills"]
    ult_rdy   = state.mp >= state.max_mp and not state.ult_blocked
    ult_label = "✅ Sẵn sàng!" if ult_rdy else (f"🚫 Phong ấn" if state.ult_blocked else f"⏳ {state.mp}/{state.max_mp} MP")
 
    skill_val = (
        f"**1️⃣ {skills['atk']['name']}**\n"
        f"   ↳ {skills['atk']['desc']}\n"
        f"**2️⃣ {skills['def']['name']}** *(MP: {skills['def']['mp']})*\n"
        f"   ↳ {skills['def']['desc']}\n"
        f"**3️⃣ {skills['ult']['name']}** ─ {ult_label}\n"
        f"   ↳ {skills['ult']['desc']}\n"
        f"**4️⃣** 💊 Linh Dược  •  **5️⃣** 💙 Nước MP  •  **🚪** Thoát"
    )
    embed.add_field(name="🎮 Kỹ Năng", value=skill_val, inline=False)
 
    # ── Diễn biến ────────────────────────────────────────────────────
    if msg:
        # Giới hạn độ dài
        lines = msg.split("\n")
        if len(lines) > 10:
            lines = lines[-10:]
        embed.add_field(
            name  = "📣 Diễn Biến",
            value = "\n".join(lines)[:950],
            inline= False,
        )
 
    # ── Footer ───────────────────────────────────────────────────────
    embed.set_footer(
        text=(
            f"Lượt {state.turn}  •  "
            f"⭐ XP: +{state.total_xp}  •  "
            f"💰 +{state.total_money:,}  •  "
            f"📦 {len(state.drops)} loại drop"
        )
    )
    return embed

    @discord.ui.button(label="1️⃣ ATK", style=discord.ButtonStyle.danger)
    async def btn_atk(self, interaction, button):
        await self.do_skill(interaction, "atk")

    @discord.ui.button(label="2️⃣ DEF", style=discord.ButtonStyle.primary)
    async def btn_def(self, interaction, button):
        await self.do_skill(interaction, "def")

    @discord.ui.button(label="3️⃣ ULT ✨", style=discord.ButtonStyle.success)
    async def btn_ult(self, interaction, button):
        await self.do_skill(interaction, "ult")

    @discord.ui.button(label="4️⃣ 💊(0)", style=discord.ButtonStyle.secondary, disabled=True)
    async def btn_potion(self, interaction, button):
        state = self.state
        # Tìm potion mạnh nhất
        priority = ["✨ Tiên Dược Honkai", "🔮 Linh Dược Lớn", "⚗️ Linh Dược Vừa", "🧪 Linh Dược Nhỏ"]
        used = None
        for p in priority:
            if state.consumables.get(p, 0) > 0:
                used = p
                break
        if not used:
            return await interaction.response.send_message("Không còn thuốc!", ephemeral=True)

        state.consumables[used] -= 1
        for k, v in KF_SHOP_ITEMS.items():
            if v["name"] == used and "heal" in v.get("effect", {}):
                heal_amt = v["effect"]["heal"]
                state.heal(heal_amt)
                mp_amt = v["effect"].get("mp", 0)
                if mp_amt:
                    state.gain_mp(mp_amt)
                break

        self.update_buttons()
        embed = kf_battle_embed(state, f"💊 Dùng **{used}** — Hồi **{heal_amt} HP**! HP: {state.hp}/{state.max_hp}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="5️⃣ 💙(0)", style=discord.ButtonStyle.secondary, disabled=True)
    async def btn_mp(self, interaction, button):
        state = self.state
        cnt = state.consumables.get("💙 Nước Hồi MP", 0)
        if cnt <= 0:
            return await interaction.response.send_message("Không còn nước MP!", ephemeral=True)
        state.consumables["💙 Nước Hồi MP"] -= 1
        state.gain_mp(50)
        self.update_buttons()
        embed = kf_battle_embed(state, f"💙 Dùng **Nước Hồi MP** — +50 MP! MP: {state.mp}/{state.max_mp}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏃 Rút Lui", style=discord.ButtonStyle.secondary, row=1)
    async def btn_flee(self, interaction, button):
        state = self.state
        kf_active_games.pop(self.user_id, None)
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🏃 Rút Lui",
                description=f"Thoát khỏi **{state.chapter['title']}**.\nXP: **+{state.total_xp}** | 💰 +**{state.total_money:,}**",
                color=discord.Color.dark_grey()
            ),
            view=self
        )

    async def do_skill(self, interaction, skill_key: str):
        state  = self.state
        char   = KF_CHARACTERS[state.char_id]
        skill  = char["skills"][skill_key]
        log    = []

        if skill["mp"] > 0 and state.mp < skill["mp"]:
            return await interaction.response.send_message(f"⚠️ Thiếu MP! Cần {skill['mp']} MP.", ephemeral=True)

        if skill_key == "ult" and state.ult_blocked:
            return await interaction.response.send_message("🚫 ULT bị phong ấn!", ephemeral=True)

        state.turn += 1

        # Giảm ult block
        if state.ult_block_turns > 0:
            state.ult_block_turns -= 1
            if state.ult_block_turns == 0:
                state.ult_blocked = False

        # Đốt đầu lượt
        if state.burn_turns > 0:
            state.hp = max(1, state.hp - state.burn_dmg)
            state.burn_turns -= 1
            log.append(f"🔥 Đốt! -{state.burn_dmg} HP")

        # Hồi HP đầu lượt Elysia
        if state.char_id == "elysia":
            state.heal(15)

        # Kevin passive stack
        kevin_mult = 1.0
        if state.char_id == "kevin":
            kevin_mult = 1 + state.kevin_stacks * 0.05

        # Tính CRIT
        crit      = random.random() < state.crit_rate
        crit_mult = 1.8 if crit else 1.0
        # Seele CRIT bonus
        seele_double = False
        if state.char_id == "seele" and crit:
            crit_mult = 2.5
            seele_double = True

        # === PLAYER SKILL ===
        if skill_key == "atk":
            state.mp -= skill["mp"]
            mult = skill["mult"] * kevin_mult
            # Boss bonus Kallen
            if state.wave == 99 and state.char_id == "kallen":
                mult *= 1.2
            # Sakura skill bonus
            if state.char_id == "sakura":
                mult *= 1.25
            dmg = int(state.atk * mult * crit_mult * random.uniform(0.9, 1.1))
            state.enemy_hp -= dmg
            state.gain_mp(20)
            if state.char_id == "kevin":
                state.kevin_stacks = min(state.kevin_stacks + 1, 10)
            crit_str = " 💥CRIT!" if crit else ""
            double_str = " 🦋+HIT!" if seele_double else ""
            log.append(f"⚔️ **{skill['name']}**{crit_str}{double_str} → **{dmg} ST**")
            # Seele: CRIT = đánh thêm
            if seele_double and state.enemy_hp > 0:
                dmg2 = int(state.atk * skill["mult"] * random.uniform(0.7, 0.9))
                state.enemy_hp -= dmg2
                log.append(f"🦋 Bướm Đêm đánh thêm → **{dmg2} ST**!")

            # Aponia choáng
            if state.char_id == "aponia" and random.random() < 0.25:
                state.stunned = True
                log.append("⛓️ Choáng kẻ thù lượt tiếp!")

        elif skill_key == "def":
            state.mp -= skill["mp"]
            if state.char_id == "fuhua":
                state.shield = True
                log.append(f"🛡️ **{skill['name']}** → Sẽ né đòn tiếp theo!")
                # Passive Fu Hua giáp
                if any(KF_EQUIPMENT.get(e, {}).get("char_bonus", {}).get("fuhua", "") for e in state.equip.values() if e):
                    state.shield = True  # luôn active
            elif state.char_id == "kallen":
                state.def_boost = 40
                log.append(f"🛡️ **{skill['name']}** → -40% sát thương lượt này!")
            elif state.char_id == "sakura":
                state.def_boost = 25
                log.append(f"📿 **{skill['name']}** → Hút 25% sát thương!")
            elif state.char_id == "otto":
                state.def_boost = 50
                log.append(f"⚡ **{skill['name']}** → -50% ST + phản 20%!")
            elif state.char_id == "kevin":
                state.invincible = True
                state.heal(50)
                log.append(f"💀 **{skill['name']}** → Bất tử + hồi 50 HP!")
            elif state.char_id == "elysia":
                state.heal(60)
                state.def_boost = 30
                log.append(f"🤗 **{skill['name']}** → Hồi 60 HP + -30% ST!")
            elif state.char_id == "aponia":
                state.def_boost = 45
                log.append(f"🙏 **{skill['name']}** → -45% ST + phản 15%!")
            elif state.char_id == "seele":
                state.shield = True
                # phản 0.5x
                log.append(f"👻 **{skill['name']}** → Né 1 đòn + phản 0.5x!")
            elif state.char_id == "vill_v":
                state.def_boost = 25
                log.append(f"🎩 **{skill['name']}** → -25% ST + phản 25%!")
            elif state.char_id == "pardofelis":
                state.def_boost = 50
                state.heal(20)
                log.append(f"🐱 **{skill['name']}** → -50% ST + hồi 20 HP!")
            else:
                state.def_boost = 30
                log.append(f"🛡️ **{skill['name']}** → Phòng thủ!")

        elif skill_key == "ult":
            state.mp = 0
            mult = skill["mult"] * kevin_mult
            if state.wave == 99 and state.char_id == "kallen":
                mult *= 1.2
            if state.char_id == "sakura":
                mult *= 1.25
            dmg = int(state.atk * mult * crit_mult * random.uniform(0.9, 1.1))
            state.enemy_hp -= dmg
            if state.char_id == "elysia":
                state.heal(50)
                log.append(f"🌸 **{skill['name']}** {'💥CRIT!' if crit else ''} → **{dmg} ST** + hồi 50 HP!")
            elif state.char_id == "seele":
                log.append(f"🦋 **{skill['name']}** {'💥CRIT!' if crit else ''} → **{dmg} ST**! CRIT rate tạm tăng!")
            elif state.char_id == "pardofelis":
                state.stunned = True  # choáng boss 2 lượt
                log.append(f"🌋 **{skill['name']}** {'💥CRIT!' if crit else ''} → **{dmg} ST** + choáng kẻ thù 2 lượt!")
            else:
                log.append(f"✨ **{skill['name']}** {'💥CRIT!' if crit else ''} → **{dmg} ST**!")
            if state.char_id == "kevin":
                state.kevin_stacks = 0

        # Fu Hua passive: hồi HP khi giết thường
        if state.char_id == "fuhua" and state.enemy_hp <= 0 and state.wave != 99:
            state.heal(30)

        # Pardofelis passive: +10 MP khi bị đánh (xử lý ở enemy turn)

        # Kiểm tra kẻ thù chết
        if state.enemy_hp <= 0:
            await self.on_enemy_die(interaction, log)
            return

        # === ENEMY TURN ===
        state.invincible = False  # reset invincible sau lượt

        if not state.stunned:
            enemy   = state.enemy
            is_boss = state.wave == 99
            raw_dmg = 0

            if is_boss and state.turn % 3 == 0 and enemy.get("skills"):
                skill_str = random.choice(enemy["skills"])
                # Parse
                if "x" in skill_str and "%" not in skill_str:
                    try:
                        parts = skill_str.split("x")
                        mult_s = parts[-1].strip().split(" ")[0].rstrip(")")
                        raw_dmg = int(enemy["atk"] * float(mult_s) * random.uniform(0.9, 1.1))
                    except:
                        raw_dmg = enemy["atk"]
                elif "ST" in skill_str:
                    nums = [int(w) for w in skill_str.split() if w.isdigit()]
                    raw_dmg = nums[0] if nums else 80
                elif "hồi" in skill_str.lower():
                    nums = [int(w) for w in skill_str.split() if w.isdigit()]
                    heal_a = nums[0] if nums else 200
                    state.enemy_hp = min(state.enemy_max_hp, state.enemy_hp + heal_a)
                    log.append(f"👿 Boss dùng **{skill_str.split('(')[0].strip()}** → Hồi **{heal_a} HP**!")
                    raw_dmg = 0
                elif "reset" in skill_str.lower():
                    old_hp = state.hp
                    state.hp = max(1, state.hp // 2)
                    log.append(f"👿 Boss **Xóa Bỏ Lịch Sử** → HP bạn còn {state.hp}!")
                    raw_dmg = 0
                elif "vô hiệu" in skill_str.lower() or "phong ấn" in skill_str.lower():
                    state.ult_blocked = True
                    state.ult_block_turns = 2
                    raw_dmg = int(enemy["atk"] * 0.5)
                    log.append(f"👿 Boss **{skill_str.split('(')[0].strip()}** → ULT bị phong ấn 2 lượt! Gây {raw_dmg} ST")
                else:
                    raw_dmg = enemy["atk"]

                if raw_dmg > 0:
                    actual = state.take_damage(raw_dmg)
                    # Seele phản
                    if state.char_id == "seele" and state.shield:
                        reflect = int(actual * 0.5)
                        state.enemy_hp -= reflect
                        log.append(f"👿 Boss → gây **{actual} ST** | 👻 Seele phản **{reflect} ST**!")
                    # Otto phản
                    elif state.char_id == "otto" and state.def_boost >= 50:
                        reflect = int(actual * 0.2)
                        state.enemy_hp -= reflect
                        log.append(f"👿 Boss → gây **{actual} ST** | ⚡ Phản **{reflect} ST**!")
                    # Vill-V phản
                    elif state.char_id == "vill_v" and state.def_boost >= 25:
                        reflect = int(actual * 0.25)
                        state.enemy_hp -= reflect
                        log.append(f"👿 Boss → gây **{actual} ST** | 🎭 Vill-V phản **{reflect} ST**!")
                    else:
                        log.append(f"👿 Boss dùng **{skill_str.split('(')[0].strip()}** → **{actual} ST**!")
                    # Pardofelis +MP khi bị đánh
                    if state.char_id == "pardofelis":
                        state.gain_mp(10)
            else:
                raw_dmg = int(enemy["atk"] * random.uniform(0.85, 1.15))
                actual  = state.take_damage(raw_dmg)
                if state.char_id == "otto" and state.def_boost >= 50:
                    reflect = int(actual * 0.2)
                    state.enemy_hp -= reflect
                    log.append(f"👾 **{enemy['name']}** → **{actual} ST** | Phản **{reflect} ST**!")
                elif state.char_id == "vill_v" and state.def_boost >= 25:
                    reflect = int(actual * 0.25)
                    state.enemy_hp -= reflect
                    log.append(f"👾 **{enemy['name']}** → **{actual} ST** | Phản **{reflect} ST**!")
                elif state.char_id == "sakura" and state.def_boost > 0:
                    absorb = int(actual * 0.25)
                    state.heal(absorb)
                    log.append(f"👾 **{enemy['name']}** → **{actual} ST** | Hút **{absorb} HP**!")
                elif state.char_id == "seele" and state.shield:
                    state.shield = False
                    reflect = int(raw_dmg * 0.5)
                    state.enemy_hp -= reflect
                    log.append(f"👾 **{enemy['name']}** → NÉ! Phản **{reflect} ST**!")
                else:
                    log.append(f"👾 **{enemy['name']}** → **{actual} ST**!")
                if state.char_id == "pardofelis":
                    state.gain_mp(10)

            # Boss Burn — rare
            if is_boss and random.random() < 0.1:
                state.burn_dmg   = 20
                state.burn_turns = 2
                log.append("🔥 Boss gây **đốt**! -20 HP/lượt trong 2 lượt!")

        else:
            log.append(f"😵 **{state.enemy['name']}** bị choáng, bỏ lượt!")
            state.stunned = False

        # Reset def boost
        state.def_boost = 0
        state.gain_mp(10)

        # Kevin giáp: 5 charge → né
        if state.char_id == "kevin":
            state.kevin_charges += 1
            if state.kevin_charges >= 5:
                state.shield = True
                state.kevin_charges = 0
                log.append("❄️ Kevin Giáp: Tích đủ 5 charge → Tự né đòn tiếp theo!")

        if state.is_dead():
            await self.on_player_die(interaction, log)
            return

        self.update_buttons()
        embed = kf_battle_embed(state, "\n".join(log))
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_enemy_die(self, interaction, log):
        state   = self.state
        enemy   = state.enemy
        is_boss = state.wave == 99

        xp_gain = enemy.get("xp", 50)
        state.total_xp += xp_gain
        log.append(f"💀 **{enemy['name']}** tiêu diệt! +**{xp_gain} XP**")

        if state.char_id == "fuhua" and not is_boss:
            state.heal(30)
            log.append("🦅 Fu Hua passive: hồi **30 HP**!")

        # Drop
        if not is_boss and random.random() < enemy.get("drop_rate", 0.3):
            drop = enemy.get("drop", "Tinh Thể Honkai 💠")
            state.drops[drop] = state.drops.get(drop, 0) + 1
            log.append(f"📦 Drop: **{drop}**!")

        embed = kf_battle_embed(state, "\n".join(log), color=discord.Color.green())

        if is_boss:
            await self.finish_chapter(interaction, embed)
        else:
            if state.wave >= state.chapter["waves"]:
                state.load_boss()
                boss_log = f"\n👿 **BOSS: {state.enemy['name']}** xuất hiện!\n"
                boss_log += f"*{state.enemy.get('lore', '')}*\n"
                for bs in state.enemy.get("skills", []):
                    boss_log += f"  ⚠️ {bs}\n"
                self.update_buttons()
                await interaction.response.edit_message(
                    embed=kf_battle_embed(state, "\n".join(log) + boss_log, color=discord.Color.dark_red()),
                    view=self
                )
            else:
                state.next_wave_enemy()
                log.append(f"\n👾 Wave **{state.wave}/{state.chapter['waves']}**: **{state.enemy['name']}**!")
                self.update_buttons()
                await interaction.response.edit_message(embed=kf_battle_embed(state, "\n".join(log)), view=self)

    async def on_player_die(self, interaction, log):
        state = self.state
        kf_active_games.pop(self.user_id, None)
        self.stop()
        self.clear_items()
        log.append(f"\n💀 **{KF_CHARACTERS[state.char_id]['name']}** đã ngã xuống...")

        ud, kf = get_kf_user(self.user_id)
        # Vẫn nhận XP
        char_id = state.char_id
        kf["char_exp"][char_id] = kf["char_exp"].get(char_id, 0) + state.total_xp
        while kf["char_exp"][char_id] >= exp_to_level_up(kf["char_levels"].get(char_id, 1)):
            kf["char_exp"][char_id] -= exp_to_level_up(kf["char_levels"][char_id])
            kf["char_levels"][char_id] = kf["char_levels"].get(char_id, 1) + 1
        # Drops
        for item, cnt in state.drops.items():
            kf["inventory"][item] = kf["inventory"].get(item, 0) + cnt
        # Tiêu hao consumable đã dùng
        kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}
        save_kf_user(self.user_id, ud)

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="💀 THẤT BẠI",
                description="\n".join(log[-6:]) + f"\n\n📦 XP: +**{state.total_xp}** | {_drop_summary(state.drops)}",
                color=discord.Color.dark_red()
            ),
            view=self
        )

    async def finish_chapter(self, interaction, base_embed):
        state   = self.state
        chapter = state.chapter
        boss    = chapter["boss"]
        user_id = self.user_id

        kf_active_games.pop(user_id, None)
        self.stop()
        self.clear_items()

        money_r = chapter["reward_money"]
        state.total_money += money_r
        di = boss.get("drop_item")
        dc = boss.get("drop_count", 1)
        if di:
            state.drops[di] = state.drops.get(di, 0) + dc

        ud, kf = get_kf_user(user_id)

        # XP và level nhân vật
        char_id = state.char_id
        kf["char_exp"][char_id] = kf["char_exp"].get(char_id, 0) + state.total_xp
        lv_up_msgs = []
        while kf["char_exp"][char_id] >= exp_to_level_up(kf["char_levels"].get(char_id, 1)):
            kf["char_exp"][char_id] -= exp_to_level_up(kf["char_levels"][char_id])
            kf["char_levels"][char_id] = kf["char_levels"].get(char_id, 1) + 1
            lv_up_msgs.append(f"⬆️ **{KF_CHARACTERS[char_id]['name']}** lên Lv{kf['char_levels'][char_id]}!")

        # Drops vào inventory
        for item, cnt in state.drops.items():
            kf["inventory"][item] = kf["inventory"].get(item, 0) + cnt

        # Consumables
        kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}

        # Tiền
        ud["money"] = ud.get("money", 0) + state.total_money

        # Tiến độ chapter
        chid = chapter["id"]
        if chid > kf.get("progress", 0):
            kf["progress"] = chid

        # Danh hiệu
        title_r = boss.get("title_reward", "")
        title_line = ""
        if title_r and title_r not in ud.get("assets", []):
            ud.setdefault("assets", []).append(title_r)
            title_line = f"\n🏷️ **Mở khóa danh hiệu: {title_r}**"

        # Thống kê
        kf["total_boss_kills"] = kf.get("total_boss_kills", 0) + 1

        save_kf_user(user_id, ud)
        add_history(user_id, f"KF C{chid} thắng (+{state.total_money:,} 💰)")

        unlock_next = ""
        if chid == 5:
            unlock_next = "\n🌟 **Chapter 6 mở khóa!** (SECRET)"
        if chid == 6:
            unlock_next = "\n🌟 **Chapter 7 mở khóa!**"

        desc = (
            chapter["story_end"] +
            f"\n\n{'═'*28}\n"
            f"💰 **+{state.total_money:,} 💰** | ⭐ XP: +{state.total_xp}\n"
            f"📦 {_drop_summary(state.drops)}"
            f"{title_line}{unlock_next}"
        )
        if lv_up_msgs:
            desc += "\n" + "\n".join(lv_up_msgs)

        result = discord.Embed(
            title=f"🎉 CHIẾN THẮNG — {chapter['title']}",
            description=desc,
            color=discord.Color.gold()
        )
        result.set_footer(text="k kallen → tiếp tục | k kallen char → nâng cấp nhân vật")
        await interaction.response.edit_message(embed=result, view=self)


# ══════════════════════════════════════════════════════════════════════
# SECTION 5: CHARACTER SELECT VIEWS
# ══════════════════════════════════════════════════════════════════════

class KFCharSelectView(discord.ui.View):
    def __init__(self, author, ud, kf):
        super().__init__(timeout=60)
        self.author = author
        self.ud     = ud
        self.kf     = kf
        unlocked    = kf.get("chars", ["kallen", "fuhua", "sakura"])

        for cid, char in KF_CHARACTERS.items():
            is_unlocked = cid in unlocked
            stats = get_char_stats(cid, kf)
            label = f"{char['name'].split()[0]} Lv{stats['lv']}"
            btn   = discord.ui.Button(
                label    = label[:25],
                style    = discord.ButtonStyle.primary if is_unlocked else discord.ButtonStyle.secondary,
                disabled = not is_unlocked,
                emoji    = "🔒" if not is_unlocked else None,
            )
            btn.callback = self._make_cb(cid, is_unlocked, char)
            self.add_item(btn)

    def _make_cb(self, cid, unlocked, char):
        async def cb(interaction):
            if interaction.user.id != self.author.id:
                return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
            if not unlocked:
                ch = KF_CHARACTERS[cid]
                return await interaction.response.send_message(
                    f"🔒 Cần **{ch.get('unlock_count',1)}x {ch.get('unlock_item','???')}**\n`k kallen mokuyen {cid}`",
                    ephemeral=True
                )
            self.stop()
            embed = discord.Embed(
                title=f"📖 CHỌN CHAPTER — {char['name']}",
                description=(
                    f"**{char['passive']}**\n"
                    f"⚔️ ATK | 🛡️ DEF | ❤️ HP | ✨ CRIT\n"
                    f"Tiến độ: Chapter **{self.kf.get('progress',0)}/9**"
                ),
                color=discord.Color.purple()
            )
            await interaction.response.edit_message(embed=embed, view=KFChapterSelectView(self.author, cid, self.ud, self.kf))
        return cb

    async def interaction_check(self, i):
        return i.user.id == self.author.id


class KFChapterSelectView(discord.ui.View):
    def __init__(self, author, char_id, ud, kf):
        super().__init__(timeout=60)
        self.author  = author
        self.char_id = char_id
        self.ud      = ud
        self.kf      = kf
        progress     = kf.get("progress", 0)

        for i, ch in enumerate(KF_CHAPTERS):
            is_secret  = ch.get("secret", False)
            is_finale  = ch.get("finale", False)
            unlocked   = (i == 0) or (progress >= ch["id"] - 1)
            if is_secret:
                unlocked = progress >= 5
            if is_finale:
                unlocked = progress >= 8

            cost  = ch["ticket_cost"]
            label = f"C{ch['id']} [{cost}🎟️]"
            emoji = "🌟" if is_secret else ("🔱" if is_finale else None)

            btn = discord.ui.Button(
                label    = label,
                style    = discord.ButtonStyle.primary if unlocked else discord.ButtonStyle.secondary,
                disabled = not unlocked,
                emoji    = emoji,
                row      = i // 5
            )
            btn.callback = self._make_cb(i, ch, cost, unlocked)
            self.add_item(btn)

    def _make_cb(self, idx, chapter, ticket_cost, unlocked):
        async def cb(interaction):
            if interaction.user.id != self.author.id:
                return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
            if not unlocked:
                return await interaction.response.send_message("🔒 Chưa mở khóa!", ephemeral=True)

            ud, kf = get_kf_user(str(self.author.id))
            tickets = kf["inventory"].get(KF_TICKET_ITEM, 0)
            if tickets < ticket_cost:
                return await interaction.response.send_message(
                    f"⚠️ Cần **{ticket_cost} {KF_TICKET_ITEM}**, có **{tickets}**!\n`k kallen muave`",
                    ephemeral=True
                )

            kf["inventory"][KF_TICKET_ITEM] = tickets - ticket_cost
            save_kf_user(str(self.author.id), ud)

            state = KFGameState(self.author.id, self.char_id, idx, kf)
            kf_active_games[str(self.author.id)] = state
            self.stop()

            intro = discord.Embed(
                title=f"📖 {chapter['title']}",
                description=chapter["story_intro"],
                color=discord.Color.purple()
            )
            char = KF_CHARACTERS[self.char_id]
            stats = get_char_stats(self.char_id, kf)
            intro.add_field(
                name  = f"🗡️ {char['name']} Lv{stats['lv']}",
                value = (
                    f"⚔️ ATK: {stats['atk']} | 🛡️ DEF: {stats['def']} | ❤️ HP: {stats['hp']} | ✨ CRIT: {stats['crit']}%\n"
                    f"🌟 Passive: {char['passive']}"
                ),
                inline=False
            )
            intro.set_footer(text=f"Vé còn: {kf['inventory'].get(KF_TICKET_ITEM,0)} 🎟️")
            await interaction.response.edit_message(embed=intro, view=KFStoryView(self.author, state))
        return cb

    async def interaction_check(self, i):
        return i.user.id == self.author.id


class KFStoryView(discord.ui.View):
    def __init__(self, author, state):
        super().__init__(timeout=120)
        self.author = author
        self.state  = state

    @discord.ui.button(label="⚔️ Bắt Đầu Chiến Đấu!", style=discord.ButtonStyle.danger)
    async def start(self, interaction, button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        self.stop()
        state = self.state
        state.next_wave_enemy()
        view  = KFBattleView(self.author.id, state)
        view.update_buttons()
        embed = kf_battle_embed(state, f"👾 Wave **1/{state.chapter['waves']}**: **{state.enemy['name']}** xuất hiện!")
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, i):
        return i.user.id == self.author.id


# ══════════════════════════════════════════════════════════════════════
# SECTION 6: RAID SYSTEM
# ══════════════════════════════════════════════════════════════════════

kf_raid_lobbies = {}  # {msg_id: {"raid_id": ..., "players": [...], "owner": ...}}


class KFRaidLobbyView(discord.ui.View):
    def __init__(self, owner, raid_id, lobby_key):
        super().__init__(timeout=300)
        self.owner     = owner
        self.raid_id   = raid_id
        self.lobby_key = lobby_key
        self.players   = [str(owner.id)]

    @discord.ui.button(label="🤝 Tham Gia", style=discord.ButtonStyle.success)
    async def join(self, interaction, button):
        uid = str(interaction.user.id)
        raid = KF_RAIDS[self.raid_id]
        if uid in self.players:
            return await interaction.response.send_message("Bạn đã trong lobby rồi!", ephemeral=True)
        if len(self.players) >= raid["max_players"]:
            return await interaction.response.send_message("Lobby đầy!", ephemeral=True)
        self.players.append(uid)
        await self._update_embed(interaction)

    @discord.ui.button(label="🚀 Bắt Đầu Raid", style=discord.ButtonStyle.danger)
    async def start_raid(self, interaction, button):
        if str(interaction.user.id) != str(self.owner.id):
            return await interaction.response.send_message("Chỉ chủ lobby mới bắt đầu được!", ephemeral=True)
        raid = KF_RAIDS[self.raid_id]
        if len(self.players) < raid["min_players"]:
            return await interaction.response.send_message(f"Cần ít nhất {raid['min_players']} người!", ephemeral=True)
        self.stop()
        self.clear_items()
        await self._run_raid(interaction)

    async def _update_embed(self, interaction):
        raid = KF_RAIDS[self.raid_id]
        names = []
        for uid in self.players:
            user = interaction.guild.get_member(int(uid))
            names.append(user.name if user else f"#{uid[-4:]}")
        embed = discord.Embed(
            title=f"⚔️ LOBBY RAID — {raid['name']}",
            description=(
                f"{raid['desc']}\n"
                f"👥 Người chơi ({len(self.players)}/{raid['max_players']}): {', '.join(names)}\n"
                f"💀 Boss HP: {raid['boss_hp']:,} | ATK: {raid['boss_atk']} | DEF: {raid['boss_def']}\n"
                f"💰 Thưởng: {raid['reward_money']:,} 💰 + {raid['drop_count']}x {raid['drop_item']}"
            ),
            color=discord.Color.dark_red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _run_raid(self, interaction):
        raid      = KF_RAIDS[self.raid_id]
        boss_hp   = raid["boss_hp"]
        boss_atk  = raid["boss_atk"]
        boss_def  = raid["boss_def"]
        boss_skills = raid["boss_skills"]
        players   = self.players[:]
        channel   = interaction.channel

        # Tải nhân vật mặc định (kallen) cho mỗi người
        player_states = {}
        for uid in players:
            ud, kf = get_kf_user(uid)
            unlocked = kf.get("chars", ["kallen"])
            char_id  = unlocked[0]
            stats    = get_char_stats(char_id, kf)
            player_states[uid] = {
                "char_id": char_id,
                "hp": stats["hp"], "max_hp": stats["hp"],
                "atk": stats["atk"], "def": stats["def"],
                "name": KF_CHARACTERS[char_id]["name"],
            }

        embed = discord.Embed(
            title=f"⚔️ RAID BẮT ĐẦU — {raid['name']}",
            description="Trận chiến tập thể bắt đầu!",
            color=discord.Color.dark_red()
        )
        msg = await channel.send(embed=embed)

        for wave_num in range(1, raid["waves"] + 1):
            await asyncio.sleep(3)
            log = [f"🌊 **Wave {wave_num}/{raid['waves']}**"]

            # Player lượt
            total_dmg = 0
            for uid, ps in player_states.items():
                if ps["hp"] <= 0:
                    continue
                atk   = ps["atk"]
                crit  = random.random() < 0.15
                dmg   = int(atk * (1.8 if crit else 1.0) * random.uniform(0.9, 1.1))
                reduction = boss_def / (boss_def + 100)
                dmg = max(1, int(dmg * (1 - reduction)))
                boss_hp -= dmg
                total_dmg += dmg
                user = interaction.guild.get_member(int(uid))
                uname = user.name if user else f"#{uid[-4:]}"
                log.append(f"  ⚔️ {uname}: **{dmg} ST**{'💥' if crit else ''}")

            log.append(f"  💢 Tổng sát thương: **{total_dmg}** | Boss HP: **{max(0,boss_hp)}/{raid['boss_hp']}**")

            if boss_hp <= 0:
                log.append(f"💀 **BOSS ĐÃ BỊ TIÊU DIỆT!**")
                boss_hp = 0
                embed = discord.Embed(title=f"🏆 RAID THÀNH CÔNG — {raid['name']}", description="\n".join(log), color=discord.Color.gold())
                await msg.edit(embed=embed)
                await asyncio.sleep(2)
                await self._finish_raid(interaction, players, True, raid)
                return

            # Boss lượt
            if boss_skills and wave_num % 2 == 0:
                bskill = random.choice(boss_skills)
                if "x" in bskill:
                    try:
                        mult = float(bskill.split("x")[1].split(" ")[0].rstrip(")"))
                    except:
                        mult = 2.0
                    for uid in players:
                        if player_states[uid]["hp"] <= 0:
                            continue
                        raw = int(boss_atk * mult * random.uniform(0.9, 1.1))
                        red = player_states[uid]["def"] / (player_states[uid]["def"] + 100)
                        dmg = max(1, int(raw * (1 - red)))
                        player_states[uid]["hp"] = max(0, player_states[uid]["hp"] - dmg)
                    log.append(f"👿 Boss dùng **{bskill.split('(')[0].strip()}** → Tất cả nhận ST!")
                elif "hồi" in bskill.lower():
                    nums = [int(w) for w in bskill.split() if w.isdigit()]
                    heal_a = nums[0] if nums else 500
                    boss_hp = min(raid["boss_hp"], boss_hp + heal_a)
                    log.append(f"👿 Boss hồi **{heal_a} HP**!")
                else:
                    # Single target
                    target = random.choice([u for u in players if player_states[u]["hp"] > 0])
                    raw  = int(boss_atk * 2.0 * random.uniform(0.9, 1.1))
                    red  = player_states[target]["def"] / (player_states[target]["def"] + 100)
                    dmg  = max(1, int(raw * (1 - red)))
                    player_states[target]["hp"] = max(0, player_states[target]["hp"] - dmg)
                    tname = interaction.guild.get_member(int(target))
                    log.append(f"👿 Boss tập trung tấn công **{tname.name if tname else '???'}** → **{dmg} ST**!")
            else:
                for uid in players:
                    if player_states[uid]["hp"] <= 0:
                        continue
                    raw = int(boss_atk * random.uniform(0.85, 1.15))
                    red = player_states[uid]["def"] / (player_states[uid]["def"] + 100)
                    dmg = max(1, int(raw * (1 - red)))
                    player_states[uid]["hp"] = max(0, player_states[uid]["hp"] - dmg)
                log.append(f"👿 Boss tấn công toàn đội!")

            # Hiển thị HP players
            hp_lines = []
            for uid, ps in player_states.items():
                user  = interaction.guild.get_member(int(uid))
                uname = user.name if user else f"#{uid[-4:]}"
                bar   = kf_bar(ps["hp"], ps["max_hp"], length=8)
                hp_lines.append(f"  {bar} **{uname}**: {max(0,ps['hp'])}/{ps['max_hp']}")
            log.append("**HP Đội:**\n" + "\n".join(hp_lines))

            # Kiểm tra toàn đội chết
            if all(p["hp"] <= 0 for p in player_states.values()):
                log.append("💀 **TOÀN ĐỘI ĐÃ NG倒!**")
                embed = discord.Embed(title=f"💀 RAID THẤT BẠI — {raid['name']}", description="\n".join(log), color=discord.Color.dark_red())
                await msg.edit(embed=embed)
                await self._finish_raid(interaction, players, False, raid)
                return

            embed = discord.Embed(
                title=f"⚔️ Wave {wave_num}/{raid['waves']} — {raid['name']}",
                description="\n".join(log),
                color=discord.Color.orange()
            )
            await msg.edit(embed=embed)

        # Qua hết wave mà boss chưa chết
        await self._finish_raid(interaction, players, boss_hp <= 0, raid)

    async def _finish_raid(self, interaction, players, win, raid):
        channel = interaction.channel
        if win:
            total_money = raid["reward_money"]
            each_money  = total_money // len(players)
            for uid in players:
                ud, kf = get_kf_user(uid)
                ud["money"] = ud.get("money", 0) + each_money
                # Drop items
                drop_cnt = raid["drop_count"]
                kf["inventory"][raid["drop_item"]] = kf["inventory"].get(raid["drop_item"], 0) + drop_cnt
                # Title
                tr = raid.get("title_reward", "")
                if tr and tr not in ud.get("assets", []):
                    ud.setdefault("assets", []).append(tr)
                if raid["id"] not in kf.get("raid_clears", []):
                    kf.setdefault("raid_clears", []).append(raid["id"])
                save_kf_user(uid, ud)
                add_history(uid, f"Raid {raid['name']} thắng (+{each_money:,} 💰)")

            mentions = " ".join(f"<@{p}>" for p in players)
            embed = discord.Embed(
                title=f"🏆 RAID HOÀN THÀNH — {raid['name']}",
                description=(
                    f"{mentions}\n\n"
                    f"💰 Mỗi người nhận: **{each_money:,} 💰**\n"
                    f"📦 Drop: **{raid['drop_count']}x {raid['drop_item']}** mỗi người\n"
                    f"🏷️ Danh hiệu: **{raid.get('title_reward','???')}**"
                ),
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title=f"💀 RAID THẤT BẠI — {raid['name']}",
                description="Đội đã bị đánh bại. Thử lại lần sau!",
                color=discord.Color.dark_red()
            )
        await channel.send(embed=embed)


# ══════════════════════════════════════════════════════════════════════
# SECTION 7: SHOP VIEW
# ══════════════════════════════════════════════════════════════════════

class KFShopView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

        options = []
        for key, item in KF_SHOP_ITEMS.items():
            price_str = f"{item['price']:,} 💰" if item["price"] else "FREE"
            options.append(discord.SelectOption(
                label       = item["name"][:25],
                description = f"{price_str} | {item['desc'][:40]}",
                value       = key
            ))
        select = discord.ui.Select(placeholder="Chọn vật phẩm để mua...", options=options[:25])
        select.callback = self._buy_callback
        self.add_item(select)

    async def _buy_callback(self, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        key  = interaction.data["values"][0]
        item = KF_SHOP_ITEMS[key]
        ud, kf = get_kf_user(str(self.author.id))

        price = item["price"]
        if price > 0 and ud.get("money", 0) < price:
            return await interaction.response.send_message(f"⚠️ Thiếu tiền! Cần **{price:,} 💰**", ephemeral=True)

        if price > 0:
            ud["money"] -= price

        itype = item["type"]
        if itype == "consumable":
            kf["consumables"][item["name"]] = kf["consumables"].get(item["name"], 0) + 1
            result = f"✅ Mua **{item['name']}** (vào túi chiến đấu)"
        elif itype == "ticket":
            cnt = item["effect"]["tickets"]
            kf["inventory"][KF_TICKET_ITEM] = kf["inventory"].get(KF_TICKET_ITEM, 0) + cnt
            result = f"✅ Nhận **{cnt}x {KF_TICKET_ITEM}**"
        elif itype == "equipment":
            eid = item["equip_id"]
            kf["inventory"][eid] = kf["inventory"].get(eid, 0) + 1
            result = f"✅ Mua **{item['name']}** (vào kho trang bị)"
        else:
            result = "✅ Mua thành công!"

        save_kf_user(str(self.author.id), ud)
        add_history(str(self.author.id), f"KF Shop: mua {item['name']} (-{price:,} 💰)")
        await interaction.response.send_message(
            embed=discord.Embed(description=f"{result}\nSố dư: **{ud.get('money',0):,} 💰**", color=discord.Color.green()),
            ephemeral=True
        )

    async def interaction_check(self, i):
        return i.user.id == self.author.id


# ══════════════════════════════════════════════════════════════════════
# SECTION 8: EQUIPMENT VIEW
# ══════════════════════════════════════════════════════════════════════

class KFEquipCharSelect(discord.ui.View):
    """Chọn nhân vật để quản lý trang bị."""
    def __init__(self, author, kf):
        super().__init__(timeout=60)
        self.author = author
        self.kf     = kf
        unlocked    = kf.get("chars", ["kallen", "fuhua", "sakura"])
        for cid in unlocked:
            char = KF_CHARACTERS[cid]
            btn  = discord.ui.Button(label=char["name"].split()[0][:15], style=discord.ButtonStyle.primary)
            btn.callback = self._make_cb(cid)
            self.add_item(btn)

    def _make_cb(self, cid):
        async def cb(interaction):
            if interaction.user.id != self.author.id:
                return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
            self.stop()
            await show_equip_for_char(interaction, self.author, cid, self.kf)
        return cb

    async def interaction_check(self, i):
        return i.user.id == self.author.id


async def show_equip_for_char(interaction, author, cid, kf):
    char  = KF_CHARACTERS[cid]
    equip = kf["equipment"].get(cid, {"weapon": None, "armor": None, "accessory": None})
    stats = get_char_stats(cid, kf)

    lines = []
    for slot in ["weapon", "armor", "accessory"]:
        eid = equip.get(slot)
        if eid and eid in KF_EQUIPMENT:
            eq = KF_EQUIPMENT[eid]
            bonus = eq.get("char_bonus", {}).get(cid, "")
            lines.append(f"**{slot.upper()}**: {eq['name']} [{rarity_emoji(eq['rarity'])}]{(' — '+bonus) if bonus else ''}")
        else:
            lines.append(f"**{slot.upper()}**: Trống")

    embed = discord.Embed(
        title=f"🛡️ TRANG BỊ — {char['name']}",
        description="\n".join(lines),
        color=discord.Color.teal()
    )
    embed.add_field(
        name="📊 Chỉ Số Hiện Tại",
        value=f"⚔️ ATK: **{stats['atk']}** | 🛡️ DEF: **{stats['def']}** | ❤️ HP: **{stats['hp']}** | ✨ CRIT: **{stats['crit']}%**",
        inline=False
    )

    # Inventory trang bị
    inv_equips = {k: v for k, v in kf["inventory"].items() if k in KF_EQUIPMENT and v > 0}
    if inv_equips:
        inv_lines = []
        for eid, cnt in list(inv_equips.items())[:8]:
            eq = KF_EQUIPMENT[eid]
            inv_lines.append(f"• {eq['name']} x{cnt} [{rarity_emoji(eq['rarity'])}]")
        embed.add_field(name="📦 Kho Trang Bị", value="\n".join(inv_lines), inline=False)

    view = KFEquipActionView(author, cid, kf)
    await interaction.response.edit_message(embed=embed, view=view)


class KFEquipActionView(discord.ui.View):
    def __init__(self, author, cid, kf):
        super().__init__(timeout=60)
        self.author = author
        self.cid    = cid
        self.kf     = kf

    @discord.ui.button(label="⚔️ Trang Bị Vũ Khí", style=discord.ButtonStyle.danger)
    async def equip_weapon(self, interaction, button):
        await self._equip_slot(interaction, "weapon")

    @discord.ui.button(label="🛡️ Trang Bị Giáp", style=discord.ButtonStyle.primary)
    async def equip_armor(self, interaction, button):
        await self._equip_slot(interaction, "armor")

    @discord.ui.button(label="💍 Trang Bị Phụ Kiện", style=discord.ButtonStyle.success)
    async def equip_accessory(self, interaction, button):
        await self._equip_slot(interaction, "accessory")

    @discord.ui.button(label="🗑️ Tháo Tất Cả", style=discord.ButtonStyle.secondary)
    async def unequip_all(self, interaction, button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        ud, kf = get_kf_user(str(self.author.id))
        for slot in ["weapon", "armor", "accessory"]:
            eid = kf["equipment"].get(self.cid, {}).get(slot)
            if eid:
                kf["inventory"][eid] = kf["inventory"].get(eid, 0) + 1
                kf["equipment"][self.cid][slot] = None
        save_kf_user(str(self.author.id), ud)
        await interaction.response.send_message("✅ Đã tháo toàn bộ trang bị!", ephemeral=True)

    async def _equip_slot(self, interaction, slot):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        ud, kf = get_kf_user(str(self.author.id))
        # Tìm trang bị phù hợp trong kho
        fitting = {k: v for k, v in kf["inventory"].items() if k in KF_EQUIPMENT and KF_EQUIPMENT[k]["slot"] == slot and v > 0}
        if not fitting:
            return await interaction.response.send_message(f"⚠️ Không có trang bị **{slot}** trong kho!", ephemeral=True)

        options = []
        for eid, cnt in list(fitting.items())[:25]:
            eq = KF_EQUIPMENT[eid]
            options.append(discord.SelectOption(
                label       = eq["name"][:25],
                description = f"{rarity_emoji(eq['rarity'])} | {eq['desc'][:40]}",
                value       = eid
            ))

        select = discord.ui.Select(placeholder=f"Chọn {slot} để trang bị...", options=options)
        async def on_select(i):
            if i.user.id != self.author.id:
                return await i.response.send_message("Không phải bạn!", ephemeral=True)
            chosen_eid = i.data["values"][0]
            ud2, kf2  = get_kf_user(str(self.author.id))
            # Tháo cái cũ
            old = kf2["equipment"].get(self.cid, {}).get(slot)
            if old:
                kf2["inventory"][old] = kf2["inventory"].get(old, 0) + 1
            # Gắn cái mới
            kf2["inventory"][chosen_eid] = max(0, kf2["inventory"].get(chosen_eid, 0) - 1)
            if self.cid not in kf2["equipment"]:
                kf2["equipment"][self.cid] = {}
            kf2["equipment"][self.cid][slot] = chosen_eid
            save_kf_user(str(self.author.id), ud2)
            eq = KF_EQUIPMENT[chosen_eid]
            await i.response.send_message(f"✅ Đã trang bị **{eq['name']}** cho **{KF_CHARACTERS[self.cid]['name']}**!", ephemeral=True)
        select.callback = on_select
        v = discord.ui.View(timeout=30)
        v.add_item(select)
        await interaction.response.send_message(embed=discord.Embed(description=f"Chọn {slot} để trang bị:"), view=v, ephemeral=True)

    async def interaction_check(self, i):
        return i.user.id == self.author.id


# ══════════════════════════════════════════════════════════════════════
# SECTION 9: CRAFT VIEW
# ══════════════════════════════════════════════════════════════════════

class KFCraftView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

        craftable = [k for k, v in KF_EQUIPMENT.items() if v.get("craft")]
        options   = []
        for eid in craftable[:25]:
            eq = KF_EQUIPMENT[eid]
            mats = " + ".join(f"{v}x {k}" for k, v in eq["craft"].items())
            options.append(discord.SelectOption(
                label       = eq["name"][:25],
                description = f"[{rarity_emoji(eq['rarity'])}] {mats[:40]}",
                value       = eid
            ))
        if options:
            select = discord.ui.Select(placeholder="Chọn trang bị để chế tạo...", options=options)
            select.callback = self._craft_cb
            self.add_item(select)

    async def _craft_cb(self, interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        eid = interaction.data["values"][0]
        eq  = KF_EQUIPMENT[eid]
        ud, kf = get_kf_user(str(self.author.id))

        # Kiểm tra nguyên liệu
        for mat, cnt in eq["craft"].items():
            have = kf["inventory"].get(mat, 0)
            if have < cnt:
                return await interaction.response.send_message(
                    f"⚠️ Thiếu **{cnt - have}x {mat}**!", ephemeral=True
                )

        # Trừ nguyên liệu
        for mat, cnt in eq["craft"].items():
            kf["inventory"][mat] -= cnt

        kf["inventory"][eid] = kf["inventory"].get(eid, 0) + 1
        save_kf_user(str(self.author.id), ud)
        add_history(str(self.author.id), f"KF Craft: {eq['name']}")
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚒️ CHẾ TẠO THÀNH CÔNG!",
                description=f"✅ Tạo ra **{eq['name']}** [{rarity_emoji(eq['rarity'])}]\n{eq['desc']}",
                color=discord.Color.gold()
            ),
            ephemeral=True
        )

    async def interaction_check(self, i):
        return i.user.id == self.author.id


# ══════════════════════════════════════════════════════════════════════
# SECTION 10: CHARACTER PROFILE
# ══════════════════════════════════════════════════════════════════════

async def show_kf_char_profile(ctx, char_id, author=None):
    target = author or ctx.author
    ud, kf  = get_kf_user(str(target.id))
    char    = KF_CHARACTERS[char_id]
    unlocked = char_id in kf.get("chars", ["kallen", "fuhua", "sakura"])
    stats   = get_char_stats(char_id, kf)
    lv      = stats["lv"]
    exp     = kf["char_exp"].get(char_id, 0)
    exp_max = exp_to_level_up(lv)
    exp_bar = kf_bar(exp, exp_max, fill="🟨", empty="⬜")

    # Custom ảnh
    avatar_url = kf.get("avatar_url", "") or ""
    banner_url = kf.get("banner_url", "") or ""

    color = discord.Color.gold() if unlocked else discord.Color.dark_grey()
    embed = discord.Embed(color=color)

    # Banner bìa
    if banner_url:
        embed.set_image(url=banner_url)

    # Avatar
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    else:
        embed.set_thumbnail(url=target.display_avatar.url)

    lock_str = "" if unlocked else " 🔒"
    embed.title = f"{'✅' if unlocked else '🔒'} {char['name']}{lock_str} — {char['title']}"

    embed.description = (
        f"*{char['lore']}*\n\n"
        f"🌟 **Passive:** {char['passive']}"
    )

    embed.add_field(
        name="📊 Chỉ Số",
        value=(
            f"**Lv {lv}** {f'(MAX)' if lv >= 50 else ''}\n"
            f"⭐ {exp_bar} {exp}/{exp_max} XP\n"
            f"⚔️ ATK: **{stats['atk']}** | 🛡️ DEF: **{stats['def']}**\n"
            f"❤️ HP: **{stats['hp']}** | ✨ CRIT: **{stats['crit']}%**"
        ),
        inline=True
    )

    skills = char["skills"]
    embed.add_field(
        name="🎮 Kỹ Năng",
        value=(
            f"1️⃣ **{skills['atk']['name']}**\n   {skills['atk']['desc']}\n"
            f"2️⃣ **{skills['def']['name']}** (MP:{skills['def']['mp']})\n   {skills['def']['desc']}\n"
            f"3️⃣ **{skills['ult']['name']}** (MP:{skills['ult']['mp']})\n   {skills['ult']['desc']}"
        ),
        inline=True
    )

    equip_desc = get_char_equip_bonus_desc(char_id, kf)
    embed.add_field(name="🛡️ Trang Bị", value=equip_desc, inline=False)

    if not unlocked:
        ci = KF_CHARACTERS[char_id]
        if ci.get("unlock", 0) == 0:
            embed.add_field(name="🔑 Mở Khóa", value="✅ Mở sẵn", inline=False)
        else:
            embed.add_field(
                name="🔑 Mở Khóa",
                value=f"Cần **{ci['unlock_count']}x {ci['unlock_item']}**\n`k kallen mokuyen {char_id}`",
                inline=False
            )

    bio = kf.get("bio", "")
    if bio:
        embed.add_field(name="📝 Bio", value=bio[:200], inline=False)

    embed.set_footer(text=f"Element: {char['element']} | k kallen nangcap {char_id} | k kallen trangbi")
    await ctx.reply(embed=embed, mention_author=False)


# ══════════════════════════════════════════════════════════════════════
# SECTION 11: COMMANDS
# ══════════════════════════════════════════════════════════════════════

# NOTE: Thêm vào bot.py sau keep_alive(), trước bot.run()
# Tất cả lệnh bên dưới phải được đặt TRƯỚC keep_alive()

@bot.group(invoke_without_command=True, aliases=['kf', 'kallenfantasy'])
async def kallen(ctx):
    user_id = str(ctx.author.id)
    ud, kf  = get_kf_user(user_id)
    progress = kf.get("progress", 0)
    tickets  = kf["inventory"].get(KF_TICKET_ITEM, 0)
    chars    = kf.get("chars", ["kallen"])

    embed = discord.Embed(
        title="🌸 KALLEN FANTASY v2",
        description=(
            f"🎟️ Vé: **{tickets}** | 📖 Chapter: **{progress}/9**\n"
            f"👥 Nhân vật: **{len(chars)}/{len(KF_CHARACTERS)}**\n\n"
            "**LỆNH:**\n"
            "`k kallen choi` — Bắt đầu phiêu lưu\n"
            "`k kallen muave [số]` — Mua vé\n"
            "`k kallen char [tên]` — Hồ sơ nhân vật\n"
            "`k kallen nhanvat` — Danh sách nhân vật\n"
            "`k kallen mokuyen <tên>` — Mở khóa nhân vật\n"
            "`k kallen nangcap <tên>` — Nâng cấp nhân vật\n"
            "`k kallen trangbi` — Quản lý trang bị\n"
            "`k kallen cheta` — Chế tạo trang bị\n"
            "`k kallen cuahang` — Cửa hàng KF\n"
            "`k kallen inventory` — Xem kho đồ\n"
            "`k kallen bancuahang` — Bán vật phẩm\n"
            "`k kallen raid [tên]` — Phó bản tập thể\n"
            "`k kallen story <chương>` — Đọc story\n"
            "`k kallen profile` — Hồ sơ của bạn\n"
            "`k kallen setavatar <url>` — Đặt ảnh đại diện KF\n"
            "`k kallen setbanner <url>` — Đặt ảnh bìa KF\n"
            "`k kallen setbio <text>` — Đặt bio KF\n"
        ),
        color=discord.Color.purple()
    )
    bar = kf_bar(progress, 9, fill="🟣", empty="⬜")
    embed.add_field(name="📊 Tiến Độ", value=f"{bar} {progress}/9 Chapters", inline=False)
    total_boss = kf.get("total_boss_kills", 0)
    raid_clears = len(kf.get("raid_clears", []))
    embed.add_field(
        name="🏆 Thống Kê",
        value=f"Boss đã giết: **{total_boss}** | Raid: **{raid_clears}/{len(KF_RAIDS)}**",
        inline=False
    )
    embed.set_footer(text="Kallen Fantasy v2 — Expanded Universe")
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command(aliases=['exit', 'quit', 'leave'])
async def thoat(ctx):
    """Thoát khẩn cấp khỏi trận đấu nếu bị kẹt."""
    uid = str(ctx.author.id)
    if uid in kf_active_games:
        state = kf_active_games.pop(uid)
        embed = discord.Embed(
            title="🚪 THOÁT KHẨN CẤP",
            description=(
                f"Đã thoát khỏi **{state.chapter['title']}**.\n\n"
                f"📊 XP đã tích: **+{state.total_xp}**\n"
                f"💰 Tiền đã nhận: **+{state.total_money:,} 💰**\n"
                f"📦 Drops: {_drop_summary(state.drops)}\n\n"
                f"*Dùng `k kallen choi` để bắt đầu lại.*"
            ),
            color=discord.Color.orange()
        )
        # Vẫn lưu XP và drops
        ud, kf = get_kf_user(uid)
        cid = state.char_id
        kf["char_exp"][cid] = kf["char_exp"].get(cid, 0) + state.total_xp
        while kf["char_exp"][cid] >= exp_to_level_up(kf["char_levels"].get(cid, 1)):
            kf["char_exp"][cid] -= exp_to_level_up(kf["char_levels"][cid])
            kf["char_levels"][cid] = kf["char_levels"].get(cid, 1) + 1
        for item, cnt in state.drops.items():
            kf["inventory"][item] = kf["inventory"].get(item, 0) + cnt
        if state.total_money > 0:
            ud["money"] = ud.get("money", 0) + state.total_money
        kf["consumables"] = {k: v for k, v in state.consumables.items() if v > 0}
        save_kf_user(uid, ud)
        await ctx.reply(embed=embed, mention_author=False)
    else:
        await ctx.reply(
            embed=discord.Embed(
                description="✅ Bạn không đang trong trận nào.",
                color=discord.Color.green()
            ),
            mention_author=False
        )

@kallen.command(aliases=['start', 'play'])
async def choi(ctx):
    uid = str(ctx.author.id)
    if uid in kf_active_games:
        return await ctx.reply("⚠️ Đang trong ván chơi! Hoàn thành hoặc rút lui trước.", mention_author=False)
    ud, kf = get_kf_user(uid)
    if "kf_chars" not in ud:
        # migrate old format
        pass
    if "kf" not in ud:
        ud["kf"] = {}
    # Đảm bảo mở sẵn
    if "chars" not in kf:
        kf["chars"] = ["kallen", "fuhua", "sakura"]
        save_kf_user(uid, ud)

    embed = discord.Embed(
        title="🗡️ CHỌN NHÂN VẬT",
        description="Chọn nhân vật để bắt đầu hành trình!\n\nMỗi nhân vật có chỉ số và passive khác nhau.",
        color=discord.Color.purple()
    )
    for cid, char in KF_CHARACTERS.items():
        unlocked = cid in kf.get("chars", [])
        stats    = get_char_stats(cid, kf)
        lock     = "✅" if unlocked else "🔒"
        embed.add_field(
            name  = f"{lock} {char['name']} Lv{stats['lv']}",
            value = f"{char['element']} | ⚔️{stats['atk']} 🛡️{stats['def']} ❤️{stats['hp']} ✨{stats['crit']}%",
            inline= True
        )
    await ctx.reply(embed=embed, view=KFCharSelectView(ctx.author, ud, kf), mention_author=False)


@kallen.command(aliases=['buy_ticket', 've'])
async def muave(ctx, amount: int = 1):
    if amount < 1 or amount > 50:
        return await ctx.reply("⚠️ Mua từ 1-50 vé!", mention_author=False)
    uid  = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    total = KF_TICKET_PRICE * amount
    if ud.get("money", 0) < total:
        return await ctx.reply(f"⚠️ Cần **{total:,} 💰** để mua **{amount}** vé!", mention_author=False)
    ud["money"] -= total
    kf["inventory"][KF_TICKET_ITEM] = kf["inventory"].get(KF_TICKET_ITEM, 0) + amount
    save_kf_user(uid, ud)
    add_history(uid, f"Mua {amount}x vé KF (-{total:,} 💰)")
    await ctx.reply(
        embed=discord.Embed(
            description=f"🎟️ Mua **{amount} {KF_TICKET_ITEM}**!\nTổng chi: **{total:,} 💰** | Vé còn: **{kf['inventory'][KF_TICKET_ITEM]}**",
            color=discord.Color.green()
        ), mention_author=False
    )


@kallen.command(aliases=['chars', 'characters'])
async def nhanvat(ctx):
    embed = discord.Embed(title="👥 DANH SÁCH NHÂN VẬT KALLEN FANTASY", color=discord.Color.purple())
    for cid, char in KF_CHARACTERS.items():
        ul = char.get("unlock", 0)
        if ul == 0:
            ul_str = "✅ Mở sẵn"
        else:
            ul_str = f"🔒 {char.get('unlock_count',1)}x {char.get('unlock_item','???')}"
        embed.add_field(
            name  = f"{char['name']} — *{char['title']}*",
            value = (
                f"**{char['element']}** | ❤️{char['hp']} ⚔️{char['atk']} 🛡️{char['def']} ✨{char['crit']}%\n"
                f"🌟 {char['passive']}\n"
                f"1️⃣ {char['skills']['atk']['name']} | 2️⃣ {char['skills']['def']['name']} | 3️⃣ {char['skills']['ult']['name']}\n"
                f"🔑 {ul_str}"
            ),
            inline=False
        )
    await ctx.reply(embed=embed, mention_author=False)


@kallen.command(aliases=['hoso'])
async def char(ctx, char_name: str = None, member: discord.Member = None):
    uid = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    target = member or ctx.author

    if char_name is None:
        # Hiện danh sách nhân vật đã mở
        unlocked = kf.get("chars", ["kallen"])
        embed = discord.Embed(title=f"👥 NHÂN VẬT CỦA {target.name}", color=discord.Color.purple())
        for cid in unlocked:
            if cid in KF_CHARACTERS:
                stats = get_char_stats(cid, kf)
                embed.add_field(
                    name  = KF_CHARACTERS[cid]["name"],
                    value = f"Lv{stats['lv']} | ⚔️{stats['atk']} 🛡️{stats['def']} ❤️{stats['hp']}",
                    inline=True
                )
        embed.set_footer(text=f"k kallen char <tên nhân vật> để xem chi tiết")
        return await ctx.reply(embed=embed, mention_author=False)

    cid = char_name.lower()
    if cid not in KF_CHARACTERS:
        # Tìm theo tên
        for k, v in KF_CHARACTERS.items():
            if char_name.lower() in v["name"].lower():
                cid = k
                break
        else:
            return await ctx.reply("⚠️ Nhân vật không tồn tại!", mention_author=False)

    await show_kf_char_profile(ctx, cid, target)


@kallen.command(aliases=['unlock'])
async def mokuyen(ctx, char_name: str):
    cid = char_name.lower()
    if cid not in KF_CHARACTERS:
        for k, v in KF_CHARACTERS.items():
            if char_name.lower() in v["name"].lower():
                cid = k
                break
        else:
            return await ctx.reply(f"⚠️ Nhân vật '{char_name}' không tồn tại!", mention_author=False)

    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    char   = KF_CHARACTERS[cid]

    if char.get("unlock", 0) == 0:
        return await ctx.reply(f"✅ **{char['name']}** đã mở sẵn!", mention_author=False)
    if cid in kf.get("chars", []):
        return await ctx.reply(f"✅ **{char['name']}** đã mở rồi!", mention_author=False)

    item_n = char["unlock_item"]
    item_c = char["unlock_count"]
    have   = kf["inventory"].get(item_n, 0)
    if have < item_c:
        return await ctx.reply(
            f"⚠️ Cần **{item_c}x {item_n}** | Có: **{have}**\nKiếm từ chiến đấu chương trình chính!",
            mention_author=False
        )

    kf["inventory"][item_n] -= item_c
    kf.setdefault("chars", []).append(cid)
    save_kf_user(uid, ud)

    await ctx.reply(
        embed=discord.Embed(
            title=f"🎉 MỞ KHÓA: {char['name']}",
            description=f"Dùng **{item_c}x {item_n}**!\n\n*{char['lore']}*\n\n💡 **Passive:** {char['passive']}",
            color=discord.Color.gold()
        ), mention_author=False
    )


@kallen.command(aliases=['levelup', 'lu'])
async def nangcap(ctx, char_name: str):
    cid = char_name.lower()
    if cid not in KF_CHARACTERS:
        for k, v in KF_CHARACTERS.items():
            if char_name.lower() in v["name"].lower():
                cid = k
                break
        else:
            return await ctx.reply("⚠️ Nhân vật không tồn tại!", mention_author=False)

    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)

    if cid not in kf.get("chars", []):
        return await ctx.reply("⚠️ Nhân vật chưa mở khóa!", mention_author=False)

    lv     = kf["char_levels"].get(cid, 1)
    if lv >= 50:
        return await ctx.reply("✅ Nhân vật đã đạt **Level 50 MAX**!", mention_author=False)

    exp_need = exp_to_level_up(lv)
    exp_have = kf["char_exp"].get(cid, 0)
    cost_money = lv * 5_000  # Tốn tiền để level up manual

    embed = discord.Embed(
        title=f"⬆️ NÂNG CẤP — {KF_CHARACTERS[cid]['name']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Cấp hiện tại", value=f"**Lv {lv}**", inline=True)
    embed.add_field(name="XP",           value=f"**{exp_have}/{exp_need}**", inline=True)
    embed.add_field(name="Chi phí UP",   value=f"**{cost_money:,} 💰**", inline=True)
    embed.add_field(
        name="Cách lên cấp",
        value="• XP từ chiến đấu (tự động)\n• Dùng tiền để up thẳng: nếu có đủ XP\n• Lên cấp tăng **5% mỗi chỉ số**",
        inline=False
    )

    if exp_have >= exp_need:
        # Auto level up
        kf["char_exp"][cid] -= exp_need
        kf["char_levels"][cid] = lv + 1
        new_stats = get_char_stats(cid, kf)
        save_kf_user(uid, ud)
        embed.add_field(
            name="✅ LÊN CẤP!",
            value=f"**Lv {lv} → Lv {lv+1}**\n⚔️ ATK: {new_stats['atk']} | 🛡️ DEF: {new_stats['def']} | ❤️ HP: {new_stats['hp']}",
            inline=False
        )
    elif ud.get("money", 0) >= cost_money:
        # Trả tiền để nạp XP
        add_xp = int(exp_need * 0.3)
        ud["money"] -= cost_money
        kf["char_exp"][cid] = min(exp_have + add_xp, exp_need - 1)
        save_kf_user(uid, ud)
        embed.add_field(
            name="💰 Dùng tiền nạp XP",
            value=f"Trả **{cost_money:,} 💰** → +**{add_xp} XP** (30% thanh XP)",
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️",
            value=f"Thiếu XP ({exp_have}/{exp_need}) và tiền ({ud.get('money',0):,}/{cost_money:,})\nChơi thêm để tích XP!",
            inline=False
        )

    await ctx.reply(embed=embed, mention_author=False)


@kallen.command(aliases=['equip', 'gear'])
async def trangbi(ctx):
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    embed  = discord.Embed(
        title="🛡️ QUẢN LÝ TRANG BỊ",
        description="Chọn nhân vật để trang bị / tháo đồ.\nTrang bị tăng ATK/DEF/HP/CRIT và có bonus đặc biệt theo nhân vật.",
        color=discord.Color.teal()
    )
    await ctx.reply(embed=embed, view=KFEquipCharSelect(ctx.author, kf), mention_author=False)


@kallen.command(aliases=['forge', 'craft'])
async def cheta(ctx):
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    embed  = discord.Embed(
        title="⚒️ XƯỞNG CHẾ TẠO",
        description="Dùng vật phẩm drop từ chiến đấu để tạo trang bị.",
        color=discord.Color.orange()
    )
    # Show materials
    mats = {k: v for k, v in kf["inventory"].items() if k in KF_EXCLUSIVE_ITEMS and v > 0}
    if mats:
        embed.add_field(
            name="🧪 Nguyên Liệu Hiện Có",
            value="\n".join(f"• {k}: **{v}**" for k, v in mats.items()),
            inline=False
        )
    else:
        embed.add_field(name="🧪 Nguyên Liệu", value="Chưa có. Chiến đấu để kiếm!", inline=False)
    await ctx.reply(embed=embed, view=KFCraftView(ctx.author), mention_author=False)


@kallen.command(aliases=['shop', 'store'])
async def cuahang(ctx):
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    embed  = discord.Embed(
        title="🛒 CỬA HÀNG KALLEN FANTASY",
        description=f"Ví của bạn: **{ud.get('money',0):,} 💰**\n\nMua vật phẩm hỗ trợ chiến đấu, vé, và trang bị cơ bản.",
        color=discord.Color.green()
    )
    for key, item in list(KF_SHOP_ITEMS.items())[:8]:
        embed.add_field(
            name  = item["name"],
            value = f"{item['price']:,} 💰 | {item['desc']}",
            inline=True
        )
    await ctx.reply(embed=embed, view=KFShopView(ctx.author), mention_author=False)


@kallen.command(aliases=['inv', 'items'])
async def inventory(ctx, member: discord.Member = None):
    target = member or ctx.author
    ud, kf = get_kf_user(str(target.id))

    embed = discord.Embed(title=f"📦 KHO ĐỒ KF — {target.name}", color=discord.Color.purple())
    embed.set_thumbnail(url=target.display_avatar.url)

    # Vé
    tickets = kf["inventory"].get(KF_TICKET_ITEM, 0)
    embed.add_field(name="🎟️ Vé", value=f"**{tickets}** {KF_TICKET_ITEM}", inline=False)

    # Nguyên liệu
    mats = {k: v for k, v in kf["inventory"].items() if k in KF_EXCLUSIVE_ITEMS and v > 0}
    if mats:
        embed.add_field(
            name  = "🧪 Nguyên Liệu",
            value = "\n".join(f"• **{k}** x{v} — {KF_EXCLUSIVE_ITEMS[k]['sell']:,} 💰/cái" for k, v in list(mats.items())[:10]),
            inline=False
        )

    # Trang bị
    equips = {k: v for k, v in kf["inventory"].items() if k in KF_EQUIPMENT and v > 0}
    if equips:
        embed.add_field(
            name  = "⚔️ Trang Bị",
            value = "\n".join(f"• {KF_EQUIPMENT[k]['name']} x{v} [{rarity_emoji(KF_EQUIPMENT[k]['rarity'])}]" for k, v in list(equips.items())[:8]),
            inline=False
        )

    # Tiêu hao
    cons = {k: v for k, v in kf.get("consumables", {}).items() if v > 0}
    if cons:
        embed.add_field(
            name  = "💊 Tiêu Hao (dùng trong chiến đấu)",
            value = "\n".join(f"• **{k}** x{v}" for k, v in cons.items()),
            inline=False
        )

    embed.set_footer(text=f"Chapter: {kf.get('progress',0)}/9 | Boss: {kf.get('total_boss_kills',0)} | k kallen bancuahang")
    await ctx.reply(embed=embed, mention_author=False)


@kallen.command(aliases=['sell', 'ban'])
async def bancuahang(ctx, item_name: str = None, amount: int = None):
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    inv    = kf["inventory"]

    if not item_name:
        sellable = {k: v for k, v in inv.items() if k in KF_EXCLUSIVE_ITEMS and v > 0}
        if not sellable:
            return await ctx.reply("📦 Không có vật phẩm KF nào để bán!", mention_author=False)
        lines = [f"**{k}** x{v} → {KF_EXCLUSIVE_ITEMS[k]['sell']:,} 💰/cái" for k, v in sellable.items()]
        embed = discord.Embed(title="💰 BÁN VẬT PHẨM KF", description="\n".join(lines) + "\n\n`k kallen bancuahang <tên> <số>`", color=discord.Color.gold())
        return await ctx.reply(embed=embed, mention_author=False)

    matched = None
    for k in KF_EXCLUSIVE_ITEMS:
        if item_name.lower() in k.lower():
            matched = k
            break
    if not matched:
        return await ctx.reply("⚠️ Không tìm thấy vật phẩm!", mention_author=False)

    have = inv.get(matched, 0)
    if amount is None:
        amount = have
    if amount <= 0 or amount > have:
        return await ctx.reply(f"⚠️ Bạn chỉ có **{have}x {matched}**!", mention_author=False)

    total = KF_EXCLUSIVE_ITEMS[matched]["sell"] * amount
    inv[matched] = have - amount
    ud["money"]  = ud.get("money", 0) + total
    save_kf_user(uid, ud)
    add_history(uid, f"Bán {amount}x {matched} KF (+{total:,} 💰)")
    await ctx.reply(
        embed=discord.Embed(description=f"✅ Bán **{amount}x {matched}** → **+{total:,} 💰**!", color=discord.Color.green()),
        mention_author=False
    )


@kallen.command()
async def story(ctx, chapter_num: int = 1):
    if chapter_num < 1 or chapter_num > len(KF_CHAPTERS):
        return await ctx.reply(f"⚠️ Chapter từ 1-{len(KF_CHAPTERS)}!", mention_author=False)
    ch       = KF_CHAPTERS[chapter_num - 1]
    is_sec   = ch.get("secret", False) or ch.get("finale", False)
    if is_sec:
        ud, kf = get_kf_user(str(ctx.author.id))
        if kf.get("progress", 0) < ch["id"] - 1:
            return await ctx.reply("🔒 Chapter này chưa mở khóa!", mention_author=False)
    embed = discord.Embed(title=f"📖 {ch['title']}", color=discord.Color.purple())
    embed.add_field(name="🌅 Mở Đầu",    value=ch["story_intro"],  inline=False)
    embed.add_field(name="⚔️ Giữa Trận", value=ch["story_mid"],    inline=False)
    embed.add_field(name="🌠 Kết Thúc",  value=ch["story_end"],    inline=False)
    embed.add_field(name="👿 Boss",       value=f"**{ch['boss']['name']}**\n*{ch['boss']['lore']}*", inline=False)
    embed.set_footer(text=f"Waves: {ch['waves']} | Vé: {ch['ticket_cost']} | Thưởng: {ch['reward_money']:,} 💰")
    await ctx.reply(embed=embed, mention_author=False)


@kallen.command()
async def profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    uid    = str(target.id)
    ud, kf = get_kf_user(uid)
    chars  = kf.get("chars", [])

    avatar_url = kf.get("avatar_url", "") or target.display_avatar.url
    banner_url = kf.get("banner_url", "")

    embed = discord.Embed(
        title=f"🌸 HỒ SƠ KALLEN FANTASY — {target.name}",
        color=discord.Color.purple()
    )

    if banner_url:
        embed.set_image(url=banner_url)
    embed.set_thumbnail(url=avatar_url)

    bio = kf.get("bio", "")
    if bio:
        embed.description = f"*{bio[:200]}*"

    embed.add_field(
        name="📊 Tổng Quan",
        value=(
            f"📖 Chapter: **{kf.get('progress',0)}/9**\n"
            f"👥 Nhân vật: **{len(chars)}/{len(KF_CHARACTERS)}**\n"
            f"🎟️ Vé: **{kf['inventory'].get(KF_TICKET_ITEM,0)}**\n"
            f"💀 Boss đã giết: **{kf.get('total_boss_kills',0)}**\n"
            f"⚔️ Raid hoàn thành: **{len(kf.get('raid_clears',[]))}/{len(KF_RAIDS)}**"
        ),
        inline=True
    )

    # Nhân vật mạnh nhất
    if chars:
        best_cid  = max(chars, key=lambda c: kf["char_levels"].get(c, 1))
        best_lv   = kf["char_levels"].get(best_cid, 1)
        best_name = KF_CHARACTERS.get(best_cid, {}).get("name", best_cid)
        embed.add_field(
            name="⭐ Nhân Vật Nổi Bật",
            value=f"**{best_name}** Lv{best_lv}",
            inline=True
        )

    # Trang bị đang đeo
    equip_lines = []
    for cid in chars[:3]:
        eq = kf["equipment"].get(cid, {})
        for slot, eid in eq.items():
            if eid and eid in KF_EQUIPMENT:
                equip_lines.append(f"• {KF_CHARACTERS[cid]['name'].split()[0]}: {KF_EQUIPMENT[eid]['name']}")
    if equip_lines:
        embed.add_field(name="🛡️ Trang Bị Nổi Bật", value="\n".join(equip_lines[:5]), inline=False)

    embed.set_footer(text="k kallen setavatar <url> | k kallen setbanner <url> | k kallen setbio <text>")
    await ctx.reply(embed=embed, mention_author=False)


@kallen.command()
async def setavatar(ctx, url: str):
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    kf["avatar_url"] = url
    save_kf_user(uid, ud)
    embed = discord.Embed(description="✅ Đã đặt ảnh đại diện KF!", color=discord.Color.green())
    embed.set_thumbnail(url=url)
    await ctx.reply(embed=embed, mention_author=False)


@kallen.command()
async def setbanner(ctx, url: str):
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    kf["banner_url"] = url
    save_kf_user(uid, ud)
    embed = discord.Embed(description="✅ Đã đặt ảnh bìa KF!", color=discord.Color.green())
    embed.set_image(url=url)
    await ctx.reply(embed=embed, mention_author=False)


@kallen.command()
async def setbio(ctx, *, text: str):
    if len(text) > 200:
        return await ctx.reply("⚠️ Bio tối đa 200 ký tự!", mention_author=False)
    uid    = str(ctx.author.id)
    ud, kf = get_kf_user(uid)
    kf["bio"] = text
    save_kf_user(uid, ud)
    await ctx.reply(embed=discord.Embed(description=f"✅ Bio: *{text}*", color=discord.Color.green()), mention_author=False)


@kallen.command()
async def raid(ctx, *, raid_name: str = None):
    if raid_name is None:
        embed = discord.Embed(title="⚔️ PHÓ BẢN CHUNG KẾT (RAID)", color=discord.Color.dark_red())
        for rid, r in KF_RAIDS.items():
            embed.add_field(
                name  = r["name"],
                value = (
                    f"{r['desc']}\n"
                    f"👥 {r['min_players']}-{r['max_players']} người | 🎟️ {r['ticket_cost']} vé/người\n"
                    f"💀 HP: {r['boss_hp']:,} | 💰 {r['reward_money']:,} 💰\n"
                    f"`k kallen raid {rid}`"
                ),
                inline=False
            )
        return await ctx.reply(embed=embed, mention_author=False)

    # Tìm raid
    raid_id = None
    for rid, r in KF_RAIDS.items():
        if raid_name.lower() in rid.lower() or raid_name.lower() in r["name"].lower():
            raid_id = rid
            break
    if not raid_id:
        return await ctx.reply("⚠️ Không tìm thấy raid!", mention_author=False)

    raid    = KF_RAIDS[raid_id]
    uid     = str(ctx.author.id)
    ud, kf  = get_kf_user(uid)

    # Kiểm tra vé
    tickets = kf["inventory"].get(KF_TICKET_ITEM, 0)
    if tickets < raid["ticket_cost"]:
        return await ctx.reply(f"⚠️ Cần **{raid['ticket_cost']} {KF_TICKET_ITEM}**! Có: {tickets}", mention_author=False)

    kf["inventory"][KF_TICKET_ITEM] -= raid["ticket_cost"]
    save_kf_user(uid, ud)

    view = KFRaidLobbyView(ctx.author, raid_id, f"{raid_id}_{ctx.message.id}")
    embed = discord.Embed(
        title=f"⚔️ LOBBY RAID — {raid['name']}",
        description=(
            f"{raid['desc']}\n"
            f"👥 {len([str(ctx.author.id)])}/{raid['max_players']} người\n"
            f"💀 Boss HP: {raid['boss_hp']:,} | Thưởng: {raid['reward_money']:,} 💰"
        ),
        color=discord.Color.dark_red()
    )
    await ctx.reply(embed=embed, view=view, mention_author=False)

# =====================================================================
# LOG TIN NHẮN BỊ XÓA
# =====================================================================
@bot.command(aliases=['setlogchannel', 'setlog'])
@commands.has_permissions(administrator=True)
async def dathenhkenh(ctx, *, args=""):
    """Đặt kênh lưu log tin nhắn bị xóa. Dùng: k setlog #kênh | k setlog clear"""
    server_id = str(ctx.guild.id)

    if "clear" in args.lower() or "xoa" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"log_channel": ""}})
        if server_id in CONFIG_CACHE and "log_channel" in CONFIG_CACHE[server_id]:
            del CONFIG_CACHE[server_id]["log_channel"]
        return await ctx.send(embed=discord.Embed(description="✅ Đã tắt log tin nhắn xóa.", color=discord.Color.green()))

    mentions = ctx.message.channel_mentions
    if not mentions:
        return await ctx.send(embed=discord.Embed(description="⚠️ VD: `k setlog #log-tin-nhan`", color=discord.Color.red()))

    channel_id = mentions[0].id
    config_col.update_one({"_id": server_id}, {"$set": {"log_channel": channel_id}}, upsert=True)
    if server_id not in CONFIG_CACHE:
        CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["log_channel"] = channel_id

    await ctx.send(embed=discord.Embed(
        description=f"✅ Tin nhắn bị xóa sẽ được lưu tại {mentions[0].mention}",
        color=discord.Color.green()
    ))
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    if not message.guild:
        return

    try:
        server_config = load_server_config(message.guild.id)
        log_channel_id = server_config.get("log_channel")
        if not log_channel_id:
            return

        log_channel = message.guild.get_channel(log_channel_id)
        if not log_channel:
            return

        content = message.content if message.content else "No text content"

        embed = discord.Embed(
            title="🗑️ Tin Nhắn Đã Xóa",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="User", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Nội Dung", value=content[:1000], inline=False)
        embed.add_field(name="Tại Khu Vực", value=message.channel.mention, inline=False)

        files = []
        # Cố gắng tải lại ảnh/tệp đính kèm trước khi CDN xóa hẳn
        for attachment in message.attachments:
            try:
                file = await attachment.to_file()
                files.append(file)
                if attachment.content_type and "image" in attachment.content_type:
                    embed.set_image(url=f"attachment://{file.filename}")
            except Exception as e:
                print(f"[WARN] Không tải được attachment khi log xóa: {e}")

        await log_channel.send(embed=embed, files=files if files else discord.utils.MISSING)

    except Exception as e:
        print(f"[WARN] on_message_delete log lỗi: {e}")
@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if not before.guild:
        return
    # Bỏ qua nếu nội dung không đổi (VD: chỉ embed load thêm, ghim tin nhắn...)
    if before.content == after.content:
        return

    try:
        server_config = load_server_config(before.guild.id)
        log_channel_id = server_config.get("log_channel")
        if not log_channel_id:
            return

        log_channel = before.guild.get_channel(log_channel_id)
        if not log_channel:
            return

        before_content = before.content if before.content else "No text content"
        after_content = after.content if after.content else "No text content"

        embed = discord.Embed(
            title="🖊️ Tin Nhắn Đã Chỉnh Sửa",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.add_field(name="User", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="Tại Khu Vực", value=before.channel.mention, inline=False)
        embed.add_field(name="Trước:", value=before_content[:1000], inline=False)
        embed.add_field(name="Sau:", value=after_content[:1000], inline=False)

        if before.attachments:
            for attachment in before.attachments:
                if attachment.content_type and "image" in attachment.content_type:
                    embed.set_thumbnail(url=attachment.url)
                    break

        embed.add_field(name="\u200b", value=f"[Nhảy đến tin nhắn]({after.jump_url})", inline=False)

        await log_channel.send(embed=embed)

    except Exception as e:
        print(f"[WARN] on_message_edit log lỗi: {e}")
# =====================================================================
# KCHAT - GỬI TIN NHẮN XUYÊN SERVER (CHỈ OWNER)
# =====================================================================
OWNER_IDS = [1377196723998556271]  # Discord ID của bạn
KCHAT_SENT_IDS = set()  # Lưu ID tin nhắn gửi qua kchat để loại khỏi log

@bot.command(aliases=['sendchat', 'chatas'])
async def kchat(ctx, channel_id: int, *, message: str):
    """Bot gửi tin nhắn đến kênh bất kỳ, kể cả server khác. Dùng: k kchat <channel_id> <nội dung>"""
    if ctx.author.id not in OWNER_IDS:
        return await ctx.reply("⛔ Bạn không có quyền dùng lệnh này!", mention_author=False)

    channel = bot.get_channel(channel_id)

    if not channel:
        return await ctx.reply(
            embed=discord.Embed(
                description="⚠️ Không tìm thấy kênh! Kiểm tra lại Channel ID hoặc bot có ở trong server đó không.",
                color=discord.Color.red()
            ),
            mention_author=False
        )

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return await ctx.reply(
            embed=discord.Embed(description="⚠️ ID này không phải kênh chat văn bản!", color=discord.Color.red()),
            mention_author=False
        )

    try:
        sent_msg = await channel.send(message)
        KCHAT_SENT_IDS.add(sent_msg.id)  # Đánh dấu để loại khỏi log xóa/sửa
    except discord.Forbidden:
        return await ctx.reply(
            embed=discord.Embed(description="⚠️ Bot không có quyền gửi tin nhắn tại kênh đó!", color=discord.Color.red()),
            mention_author=False
        )
    except Exception as e:
        return await ctx.reply(
            embed=discord.Embed(description=f"⚠️ Lỗi: {e}", color=discord.Color.red()),
            mention_author=False
        )

    guild_name = channel.guild.name if channel.guild else "DM"

    try:
        await ctx.message.delete()
    except Exception:
        pass

    try:
        await ctx.send(embed=discord.Embed(
            description=f"✅ Đã gửi tin nhắn đến **#{channel.name}** ({guild_name})",
            color=discord.Color.green()
        ), delete_after=5)
    except Exception:
        pass
# =====================================================================
# KHỞI ĐỘNG
# =====================================================================
keep_alive() 

TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
