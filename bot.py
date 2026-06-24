import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 
import math

# =====================================================================
# THIẾT LẬP CƠ BẢN
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

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
                if "reputation" not in document: document["reputation"] = 100
                if "has_scandal" not in document: document["has_scandal"] = False
                if "atk_level" not in document: document["atk_level"] = 1
                if "def_level" not in document: document["def_level"] = 1
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
            print(f"[ERROR] save_company DB error: {e}")

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
            f"📊 Cooldown: **10 phút** mỗi lệnh\n\n"
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
        embed.set_footer(text="⏳ Cooldown 10 phút | Dùng 'k ck sl' để đặt cắt lỗ")
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
            if diff < 600:
                return await ctx.reply(embed=discord.Embed(
                    description=f"⏳ Cooldown: còn **{int((600-diff)//60)}p {int((600-diff)%60)}s**",
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
@bot.event
async def on_ready():
    print('================================================')
    print(f'>>> BOT {bot.user} ĐÃ SẴN SÀNG!')
    print('>>> VERSION 8.0 - REAL STOCK MARKET')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="k help | v8.0 Real Markets"))
    bot.loop.create_task(process_pending_orders())
    bot.loop.create_task(process_margin_interest())
    bot.loop.create_task(auto_sl_tp_monitor())


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
    
    cmds = "`k cty gop <tiền>` | `k cty thulai` | `k cty dinhchinh` | `k cty nangcap <cong/thu>` | `k cty roi`"
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
    last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    if now - last < timedelta(days=1): return await ctx.reply("⏳ Mỗi ngày chỉ được thu lãi 1 lần.", mention_author=False)
    lai_nhan_duoc = min(int(comp["treasury"] * 0.03), 80000)
    comp["treasury"] += lai_nhan_duoc; comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    await ctx.reply(f"📈 Công ty nhận **{lai_nhan_duoc:,} 💰** lãi hôm nay!\nTổng quỹ: **{comp['treasury']:,} 💰**.", mention_author=False)

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
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 BOT ECONOMY v8.0 - REAL MARKETS", description="Tiền tố: `k` (Ví dụ: `k rank`)", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.add_field(name="🏦 KINH TẾ CƠ BẢN", value="`k rank` `k bank` `k give @user <tiền>`\n`k daily` `k lixi` `k top` `k ls`\n`k dilamthem` (CD:45p) `k nhiemvu`\n`k vay <tiền>` `k tranno`", inline=False)
    embed.add_field(name="📈 CHỨNG KHOÁN v2 (THỰC TẾ)", value="`k ck` - Xem thị trường\n`k ck buy/sell <MÃ> <SL>` - Mua/Bán\n`k ck order <MÃ> buy/sell <SL> <GIÁ>` - Lệnh giá\n`k ck sl/tp <MÃ> <GIÁ>` - Stop-Loss/Take-Profit\n`k ck margin <MÃ> <SL>` - Mua ký quỹ (đòn bẩy)\n`k ck short <MÃ> <SL>` - Bán khống\n`k ck port` `k ck chart <MÃ>`", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 300K, CD 6s)", value="`k coin` `k taixiu` `k baucua`\n`k nohu` `k vietlott <số>` `k blackjack`\n`k vecao <tiền>` - Vé cào 9 ô", inline=False)
    embed.add_field(name="🎁 PHÚC LỢI", value="`k vongquay` - Vòng quay free/20h\n`k gacha` (CD:5p, 50k)\n`k cuopnganhang` (CD:2h)", inline=False)
    embed.add_field(name="🌾 SINH HOẠT", value="`k cauca` (CD:25s) `k daovang` (CD:60s)\n`k farm` `k dilamthem` `k gym`", inline=False)
    embed.add_field(name="⚔️ PK & GAME", value="`k pk @user <tiền>` `k duel @user <tiền>`\n`k nhansinh` `k marry @user`", inline=False)
    embed.add_field(name="🏢 CÔNG TY", value="`k cty tao <tên>` `k cty` `k daichien`", inline=False)
    embed.set_footer(text="v8.0 Real Stock Market | Spread 0.1% | Tax 0.1% | Circuit Breaker 7%")
    await ctx.reply(embed=embed, mention_author=False)

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
                custom_id=skill_id,
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
    try:
        def_boss_member = await interaction_or_ctx.guild.fetch_member(int(def_boss_id))
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
# KHỞI ĐỘNG
# =====================================================================
keep_alive() 

TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
