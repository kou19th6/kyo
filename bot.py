import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 

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
    "rugpull": "https://media.giphy.com/media/3o6gDWzmToltqKtvRo/giphy.gif",
    "bankrupt": "https://media.giphy.com/media/3o6UB5RrlQuMfZp82Y/giphy.gif",
    "fishing": "https://media.giphy.com/media/3o7TKFZLmO0nqnO4mA/giphy.gif",
    "work": "https://media.giphy.com/media/LmNwrBhejkK9EFP504/giphy.gif",
    "level_up": "https://media.giphy.com/media/3o7btNhMBytxAM6YBa/giphy.gif",
    "quest": "https://media.giphy.com/media/xT0GqGUyFPeYZsNzO0/giphy.gif",
    "duel": "https://media.giphy.com/media/3o7TKsWbXJMIdURvkk/giphy.gif",
}

# =====================================================================
# QUẢN LÝ TRẠNG THÁI (COOLDOWN & BỘ ĐẾM)
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
vietlott_players = {}
werewolf_lobbies = {}
duel_invites = {}

# Lock tránh race condition
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
# KẾT NỐI MONGODB VÀ HỆ THỐNG BỘ ĐỆM (CACHE)
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

# FIX: thêm timeout và retry cho MongoDB
mongo_client = pymongo.MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,   # FIX: timeout 5 giây thay vì chờ mãi
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    retryWrites=True,
)
db = mongo_client["DiscordBotDB"]

users_col = db["users"]   
config_col = db["config"] 
companies_col = db["companies"]

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
            # FIX: nếu DB lỗi, dùng cache rỗng thay vì crash
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
            # FIX: log lỗi save thay vì crash hoàn toàn
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
    if len(user_data["history"]) > 15: user_data["history"].pop()

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
# FIX CHÍNH: HÀM KIỂM TRA TỔNG THỂ
# =====================================================================
@bot.check
async def global_jail_and_channel_check(ctx):
    # FIX: bỏ qua check cho admin và lệnh help như cũ
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
            # FIX: nếu parse jail_time lỗi, xóa luôn thay vì crash
            user_data["jail_time"] = None
            save_user(ctx.author.id)
            
    if ctx.guild:
        try:
            server_config = load_server_config(ctx.guild.id)
            allowed_channels = server_config.get("allowed_channels", [])
            if allowed_channels and ctx.channel.id not in allowed_channels:
                # FIX: thông báo cho người dùng biết sai kênh thay vì im lặng
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
            # FIX: nếu check kênh lỗi, vẫn cho người dùng dùng được thay vì block
            pass

    return True

# =====================================================================
# FIX: ERROR HANDLER TOÀN CỤC - bắt mọi lỗi không xử lý
# =====================================================================
@bot.event
async def on_command_error(ctx, error):
    # FIX: bỏ qua lỗi check thất bại (đã xử lý trong check)
    if isinstance(error, commands.CheckFailure):
        return
    
    # FIX: thông báo lỗi thiếu quyền
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply(embed=discord.Embed(
            description="❌ Bạn không có quyền dùng lệnh này!",
            color=discord.Color.red()
        ), mention_author=False)
        return
    
    # FIX: thông báo lỗi thiếu argument
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(embed=discord.Embed(
            description=f"⚠️ Thiếu thông tin! Gõ `k help` để xem hướng dẫn.",
            color=discord.Color.orange()
        ), mention_author=False)
        return

    # FIX: thông báo lỗi member không tìm thấy
    if isinstance(error, commands.MemberNotFound):
        await ctx.reply(embed=discord.Embed(
            description="⚠️ Không tìm thấy người dùng này! Hãy tag trực tiếp @tên.",
            color=discord.Color.orange()
        ), mention_author=False)
        return

    # FIX: thông báo lỗi lệnh không tìm thấy (không spam)
    if isinstance(error, commands.CommandNotFound):
        return  # im lặng, không cần báo

    # FIX: giải phóng lock nếu có lỗi không mong muốn
    release_lock(ctx.author.id)

    # FIX: log lỗi ra console để debug
    print(f"[ERROR] Lệnh '{ctx.command}' của {ctx.author} gặp lỗi: {error}")

    # FIX: báo lỗi chung cho người dùng thay vì im lặng
    try:
        await ctx.reply(embed=discord.Embed(
            description="⚙️ Có lỗi xảy ra! Thử lại sau hoặc báo admin.",
            color=discord.Color.red()
        ), mention_author=False)
    except Exception:
        pass

# =====================================================================
# (Phần còn lại của code giữ nguyên từ đây)
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

STANDARD_STOCKS = {
    "VIN": "Tập Đoàn VIN", "FLC": "Hàng Không FLC", "VNZ": "Công Nghệ VNZ", 
    "DOGE": "Doge Coin", "BTC": "Bitcoin", "AAPL": "Apple Inc.", "TSLA": "Tesla"
}

STOCK_TAX_RATE = 0.05
STOCK_SPREAD = 0.03

def get_all_stocks():
    all_stocks = STANDARD_STOCKS.copy()
    try:
        ipo_companies = companies_col.find({"is_ipo": True})
        for comp in ipo_companies:
            code = comp["name"][:4].upper()
            all_stocks[code] = comp["name"]
    except Exception as e:
        print(f"[WARN] get_all_stocks error: {e}")
    return all_stocks

def get_stock_price(stock_code, hour_offset=0):
    try:
        ipo_comp = companies_col.find_one({"is_ipo": True, "name": {"$regex": f"^{stock_code}", "$options": "i"}})
    except Exception:
        ipo_comp = None
    target_time = datetime.now() + timedelta(hours=hour_offset)
    rng = random.Random(int(target_time.strftime("%Y%m%d%H%M")) // 15 + sum(ord(char) for char in stock_code))
    
    if ipo_comp:
        base_price = max(5000, int(ipo_comp.get("treasury", 0) / 1000))
        rep_multiplier = max(0.1, ipo_comp.get("reputation", 100) / 100.0) 
        scandal_penalty = 0.5 if ipo_comp.get("has_scandal", False) else 1.0 
        market_fluctuation = rng.uniform(0.80, 1.20)
        final_price = int(base_price * rep_multiplier * scandal_penalty * market_fluctuation)
        return max(1000, final_price) 

    base = rng.randint(5, 800) * 1000
    if rng.randint(1, 100) <= 8: return 1000 
    return base

def get_stock_buy_price(stock_code):
    market_price = get_stock_price(stock_code)
    return int(market_price * (1 + STOCK_SPREAD))

def get_stock_sell_price(stock_code):
    market_price = get_stock_price(stock_code)
    return int(market_price * (1 - STOCK_SPREAD) * (1 - STOCK_TAX_RATE))

def get_next_15min_timestamp():
    now = datetime.now()
    next_update = now + timedelta(minutes=15 - (now.minute % 15))
    next_update = next_update.replace(second=0, microsecond=0)
    return int(next_update.timestamp())

DAILY_QUESTS = [
    {"id": "gamble5", "name": "Tay Chơi Cứng", "desc": "Chơi casino 5 lần", "target": 5, "type": "gamble", "reward": 15000},
    {"id": "mine3", "name": "Thợ Mỏ Chăm Chỉ", "desc": "Đào vàng 3 lần", "target": 3, "type": "mine", "reward": 12000},
    {"id": "fish10", "name": "Ngư Dân Đạo Nghĩa", "desc": "Câu cá 10 lần", "target": 10, "type": "fish", "reward": 25000},
    {"id": "give1", "name": "Bố Thí Hào Phóng", "desc": "Chuyển tiền cho 1 người", "target": 1, "type": "give", "reward": 8000},
    {"id": "farm1", "name": "Lão Nông Tri Điền", "desc": "Thu hoạch nông trại 1 lần", "target": 1, "type": "farm", "reward": 20000},
    {"id": "gacha3", "name": "Nghiện Gacha", "desc": "Quay gacha 3 lần", "target": 3, "type": "gacha", "reward": 40000},
    {"id": "work3", "name": "Nhân Viên Mẫn Cán", "desc": "Đi làm thêm 3 lần", "target": 3, "type": "work", "reward": 30000},
]

def get_or_assign_quest(user_data):
    now = datetime.now()
    last_quest_str = user_data.get("last_quest", "2000-01-01 00:00:00")
    try:
        last_quest = datetime.strptime(last_quest_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        last_quest = datetime(2000, 1, 1)
    
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
    if not quest: return None
    if quest["type"] != quest_type: return None
    
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
# DATA NHÂN SINH, VŨ KHÍ, KỊCH BẢN
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "🪵 Gậy Gỗ Mục", "terrible": 25, "bad": 40, "neutral": 15, "good": 15, "great": 5, "jackpot": 0},
    "sung_cao_su": {"price": 100, "name": "🪀 Súng Cao Su", "terrible": 20, "bad": 35, "neutral": 20, "good": 20, "great": 5, "jackpot": 0},
    "kiem_sat": {"price": 200, "name": "🗡️ Kiếm Sắt Thường", "terrible": 15, "bad": 25, "neutral": 20, "good": 25, "great": 13, "jackpot": 2},
    "kiem_hiep_si": {"price": 500, "name": "⚔️ Kiếm Hiệp Sĩ", "terrible": 10, "bad": 20, "neutral": 15, "good": 30, "great": 20, "jackpot": 5},
    "riu_chien": {"price": 1000, "name": "🪓 Rìu Phá Giáp", "terrible": 10, "bad": 15, "neutral": 15, "good": 30, "great": 25, "jackpot": 5},
    "thanh_kiem": {"price": 1500, "name": "🔱 Thánh Kiếm Mạ Vàng", "terrible": 5, "bad": 10, "neutral": 10, "good": 35, "great": 30, "jackpot": 10},
    "sung_phong_luu": {"price": 3000, "name": "🚀 Súng Phóng Lựu RPG", "terrible": 5, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 15},
    "gang_tay": {"price": 5000, "name": "🧤 Găng Tay Vô Cực", "terrible": 2, "bad": 5, "neutral": 5, "good": 20, "great": 40, "jackpot": 28}
}

SCENARIOS = {
    "terrible": [ 
        {"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!**\nBị đấm bay xa, rớt sạch đồ đạc!"},
        {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!**\nBị nó khè lửa, rớt bộn tiền!"},
        {"mult": -1.3, "msg": "🕳️ **SỤP HỐ CHÔNG!**\nGãy 2 cái sườn, nôn hết tiền ra đóng viện phí."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ giật túi tiền rồi đu cây biến mất."},
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nBị đau bụng tốn tiền viện phí."},
        {"mult": -0.8, "msg": "💩 **TRƯỢT CHÂN VÀO BÃI MÌN!**\nTốn tiền đi tắm gội mua bộ đồ mới."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ XÀO XẠC...**\nChẳng có gì cả."},
        {"mult": 0, "msg": "📦 **RƯƠNG RỖNG TOẾCH!**\nBên trong chả có gì ngoài mạng nhện."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nNhặt được một chiếc ví nhỏ."},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được nấm linh chi, bán được giá hời."}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nTịch thu kho báu của toán cướp rừng!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nPhát hiện kho báu vàng chóe!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrúng giải ĐẶC BIỆT!"},
        {"mult": 12.0, "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR! (ULTRAPOT)**\nVớt được vương miện 100 viên kim cương!"}
    ]
}

EVENTS_P1 = [
    {
        "q": "Tuổi 15: Bạn tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", 
        "choices": [
            {"text": "Đem nộp lên công an phường", "rate": 50, "win": "Chủ ví là giám đốc lớn, khen thưởng tiền mặt.", "lose": "Bị công an nghi là kẻ ăn cắp, phạt lao động công ích.", "tien_w": 5000, "tien_l": -10000}, 
            {"text": "Bỏ túi xài luôn, không nói ai", "rate": 20, "win": "Trót lọt, bao cả lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường và bị đuổi học.", "tien_w": 8000, "tien_l": -25000}, 
            {"text": "Rút tờ 500k rồi vứt lại ví", "rate": 30, "win": "Trót lọt, dùng tiền đó nạp game.", "lose": "Chủ nhân báo mất, bị giang hồ mạng truy lùng đền gấp 10.", "tien_w": 500, "tien_l": -50000}, 
            {"text": "Giả vờ không thấy, đi thẳng", "rate": 80, "win": "Bình yên vô sự.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn, phải tự bỏ tiền túi ra đền.", "tien_w": 0, "tien_l": -15000}
        ]
    }
]

EVENTS_P2 = [
    {
        "q": "Tuổi 25: Bạn có 500 triệu tiết kiệm, hãy đưa ra quyết định đầu tư.", 
        "choices": [
            {"text": "All-in Tiền ảo (Crypto / Memecoin)", "rate": 15, "win": "Giá x100 lần! Mua biệt thự và siêu xe.", "lose": "Bị sập sàn, cháy túi và gánh nợ ngân hàng.", "tien_w": 2500000, "tien_l": -500000}, 
            {"text": "Gửi tiết kiệm ngân hàng", "rate": 70, "win": "Lãi suất ổn định, cuộc sống an nhàn.", "lose": "Ngân hàng bị thanh tra, giám đốc ôm tiền bỏ trốn. Mất sạch.", "tien_w": 50000, "tien_l": -500000}, 
            {"text": "Khởi nghiệp kinh doanh nhà hàng", "rate": 30, "win": "Khách đông nườm nượp, mở chuỗi 5 chi nhánh.", "lose": "Bị đối thủ chơi bẩn bóc phốt, phá sản ôm nợ.", "tien_w": 500000, "tien_l": -800000}, 
            {"text": "Mua vàng cất vào két sắt", "rate": 60, "win": "Vàng tăng giá phi mã, chốt lời đậm.", "lose": "Bị trộm cạy cửa khiêng luôn két sắt.", "tien_w": 100000, "tien_l": -500000}
        ]
    }
]

EVENTS_P3 = [
    {
        "q": "Tuổi 35: Cò đất rủ chung vốn lướt sóng khu quy hoạch mới.", 
        "choices": [
            {"text": "Cắm sổ đỏ vay nặng lãi quất liền", "rate": 10, "win": "Giá đất x5, trở thành tỷ phú bất động sản.", "lose": "Dính bẫy dự án ma. Giang hồ siết nợ, ra đê ở.", "tien_w": 5000000, "tien_l": -2000000}, 
            {"text": "Mua 1 lô nhỏ bằng vốn tự có", "rate": 40, "win": "Đất lên nhẹ, chốt lời an toàn.", "lose": "Đất dính quy hoạch làm nghĩa trang, giam vốn không ai mua.", "tien_w": 300000, "tien_l": -200000}, 
            {"text": "Làm 'Cò đất' ăn hoa hồng", "rate": 50, "win": "Chốt được chục lô, hoa hồng nhận mỏi tay.", "lose": "Khách hàng bùng kèo, bị chủ đất giam tiền cọc bắt đền.", "tien_w": 200000, "tien_l": -100000}, 
            {"text": "Không quan tâm nhà đất", "rate": 80, "win": "Cuộc sống trôi qua bình yên.", "lose": "Lạm phát tăng cao, tiền giấy mất giá trầm trọng.", "tien_w": 0, "tien_l": -50000}
        ]
    },
    {
        "q": "Tuổi 35: Bạn thân cũ gọi điện khóc lóc, hỏi vay 300 triệu lo viện phí.", 
        "choices": [
            {"text": "Cho vay ngay, không cần giấy tờ", "rate": 20, "win": "Bạn qua cơn bĩ cực, làm ăn phất lên trả ơn gấp 5 lần.", "lose": "Nó cầm tiền đi đánh tài xỉu, chặn số bom tiền.", "tien_w": 1500000, "tien_l": -300000}, 
            {"text": "Từ chối khéo, bảo không có tiền", "rate": 90, "win": "Giữ được tiền, tuy có chút áy náy.", "lose": "Bị nó bóc phốt lên Facebook là đồ bạn bè sống lỗi.", "tien_w": 0, "tien_l": -10000}, 
            {"text": "Chỉ cho vay 5 triệu gọi là giúp đỡ", "rate": 70, "win": "Nó nhận tiền và cảm ơn rối rít.", "lose": "Nó chê ít, chửi bạn một trận rồi cúp máy.", "tien_w": 0, "tien_l": -5000}, 
            {"text": "Cho vay nhưng bắt ký giấy thế chấp xe", "rate": 50, "win": "Nó không trả được, bạn siết luôn con xe SH mang đi bán.", "lose": "Xe là xe gian (trộm cắp), bạn bị công an phạt.", "tien_w": 100000, "tien_l": -150000}
        ]
    }
]

EVENTS_P4 = [
    {
        "q": "Tuổi 50: Bạn bước vào giai đoạn khủng hoảng tuổi trung niên.", 
        "choices": [
            {"text": "Bán đất mua siêu xe để tìm lại thanh xuân", "rate": 10, "win": "Tham gia giải đua xe, trở nên nổi tiếng kiếm bộn tiền quảng cáo.", "lose": "Đạp nhầm chân ga tông nát xe, đền tiền sửa chữa và thuốc men.", "tien_w": 800000, "tien_l": -1000000}, 
            {"text": "Cặp Sugar Baby / Phi công trẻ", "rate": 20, "win": "Tâm hồn trẻ lại, sung mãn như thanh niên.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, ra tòa ly hôn mất trắng tài sản.", "tien_w": 10000, "tien_l": -2000000}, 
            {"text": "Chơi đồ cổ, lan đột biến", "rate": 30, "win": "Bán được bình gốm cổ cho đại gia nước ngoài, thu lãi cực đậm.", "lose": "Thị trường sập, ôm đống rác trong nhà, nợ nần chồng chất.", "tien_w": 600000, "tien_l": -500000}, 
            {"text": "Tập Thiền, đi chùa, ăn chay", "rate": 80, "win": "Tâm hồn thanh tịnh, sức khỏe dồi dào, sống thọ.", "lose": "Bị gian thương bán nấm chay có độc, phải đi rửa ruột.", "tien_w": 50000, "tien_l": -80000}
        ]
    }
]

EVENTS_P5 = [
    {
        "q": "Tuổi 70: Có người đến gạ bán Linh Đan Cải Lão Hoàn Đồng giá 1 Tỷ.", 
        "choices": [
            {"text": "Vung tiền mua ngay không chần chừ", "rate": 5, "win": "Phép màu xảy ra! Bạn trở lại tuổi 20 sung mãn!", "lose": "Thuốc giả chứa chì và thủy ngân. Bạn thăng thiên sớm.", "tien_w": 5000000, "tien_l": -1000000, "die_l": True}, 
            {"text": "Lập di chúc chia tài sản cho con cháu", "rate": 60, "win": "Con cháu hiếu thảo, tổ chức lễ mừng thọ hoành tráng.", "lose": "Con cháu bất hiếu, đánh nhau giành giật gia tài. Bạn tức quá đột quỵ.", "tien_w": 200000, "tien_l": -500000, "die_l": True}, 
            {"text": "Quyên góp 100% tài sản đi làm từ thiện", "rate": 70, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền chạy mất. Bạn ôm hận qua đời.", "tien_w": 500000, "tien_l": -1000000, "die_l": True}, 
            {"text": "Lên Las Vegas quất 1 ván Casino All-in cuối đời", "rate": 10, "win": "Trúng Jackpot 50 triệu đô! Lên báo quốc tế, thành huyền thoại.", "lose": "Thua trắng tay, nhồi máu cơ tim gục tại sòng bạc.", "tien_w": 10000000, "tien_l": -1000000, "die_l": True}
        ]
    }
]

FISH_TABLE = {
    "common": {
        "rate": 50,
        "pool": [
            ("Cá Rô Đồng 🐟", 300, 1000),
            ("Cá Trê Béo 🐠", 500, 1500),
            ("Cá Chép Vàng 🐡", 700, 1800),
            ("Cá Mương Nhỏ 🐟", 200, 600),
        ]
    },
    "rare": {
        "rate": 28,
        "pool": [
            ("Cá Hồi Nguyên Chất 🍣", 4000, 10000),
            ("Cá Mú Đỏ 🦈", 5000, 12000),
            ("Cá Vược Bạc 🐟", 3000, 8000),
        ]
    },
    "epic": {
        "rate": 13,
        "pool": [
            ("Cá Ngừ Đại Dương 🐋", 18000, 45000),
            ("Cá Kiếm Thần Tốc ⚡", 22000, 55000),
            ("Bạch Tuộc Khổng Lồ 🐙", 25000, 60000),
        ]
    },
    "legendary": {
        "rate": 4,
        "pool": [
            ("Cá Vàng Thần Kỳ ✨", 90000, 200000),
            ("Rồng Biển Cổ Đại 🐲", 150000, 400000),
        ]
    },
    "trash": {
        "rate": 5,
        "pool": [
            ("Cái Giày Cũ 👟", -2000, -1000),
            ("Lon Nước Rỉ Sét 🥫", -1500, -500),
            ("Cần Câu Gãy 🪤", -3000, -1000),
        ]
    }
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
]

# =====================================================================
# GIAO DIỆN UI (giữ nguyên toàn bộ từ code gốc)
# =====================================================================
class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        options = []
        for key, item_data in SHOP_ITEMS.items():
            if item_data["type"] == category_type:
                options.append(discord.SelectOption(label=item_data['name'], description=f"Giá: {item_data['price']:,} 💰", value=key, emoji=item_data['emoji']))
        super().__init__(placeholder="Nhấn vào đây để chọn món đồ muốn tậu...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_info = SHOP_ITEMS[self.values[0]]
        
        if user_data.get("money", 0) < item_info["price"]:
            embed_fail = discord.Embed(description=f"⚠️ Thẻ từ chối! Cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            success_message = f"🎉 Tiền trao cháo múc! Bạn đã trang bị danh hiệu: **{item_info['name']}**."
        elif item_info["type"] == "tool":
            if item_info["name"] in user_data.get("assets", []):
                user_data["money"] += item_info["price"]
                embed_exist = discord.Embed(description=f"⚠️ Bạn đã có **{item_info['name']}** rồi!", color=discord.Color.orange())
                return await interaction.response.send_message(embed=embed_exist, ephemeral=True)
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Đã mua **{item_info['name']}**! Câu cá sẽ hiệu quả hơn."
        else:
            if item_info["name"] in user_data.get("assets", []):
                user_data["money"] += item_info["price"]
                embed_exist = discord.Embed(description=f"⚠️ Bạn đã sở hữu **{item_info['name']}** rồi!", color=discord.Color.orange())
                return await interaction.response.send_message(embed=embed_exist, ephemeral=True)
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Bạn vừa đập hộp siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        add_history(user_id, f"Mua {item_info['name']} tại Store (-{item_info['price']:,} 💰)")
        
        new_achievements = check_achievement(user_id, user_data)
        ach_text = ""
        if new_achievements:
            save_user(user_id)
            ach_text = "\n\n🏅 **THÀNH TÍCH MỚI:** " + ", ".join(new_achievements)
        
        embed_success = discord.Embed(title="🛍️ GIAO DỊCH HOÀN TẤT!", description=success_message + ach_text, color=discord.Color.green())
        embed_success.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(title="🛍️ QUẦY BÁN DANH HIỆU", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(title="🛍️ SHOWROOM XE CỘ & PHI CƠ", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(title="🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Dụng Cụ Câu Cá", style=discord.ButtonStyle.secondary, emoji="🎣")
    async def btn_tool(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("tool"))
        embed = discord.Embed(title="🎣 TRẠM CÂU CÁ THIẾT BỊ", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Ai gọi lệnh người đó mua nha!", ephemeral=True)
            return False
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
                    options.append(discord.SelectOption(label=pet, description=f"Đang có: {quantity} con | Giá: {get_pet_sell_price(pet):,} 💰", value=pet))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(label=asset, description=f"Bị ép giá còn: {get_asset_price(asset):,} 💰", value=asset))
                
        super().__init__(placeholder="Chọn món đồ bạn muốn cắm sổ / bán...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_value = self.values[0]
        
        if self.is_pet:
            if user_data.get("pets", {}).get(item_value, 0) <= 0: 
                return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này!", ephemeral=True)
            sell_price = get_pet_sell_price(item_value)
            user_data["pets"][item_value] -= 1
            if user_data["pets"][item_value] == 0: del user_data["pets"][item_value]
            success_message = f"✅ Thương lái đã mang bé **{item_value}** đi.\nBạn nhận được **{sell_price:,} 💰**!"
        else:
            if item_value not in user_data.get("assets", []): 
                return await interaction.response.send_message("Lỗi: Bạn không có tài sản này!", ephemeral=True)
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            success_message = f"✅ Chủ tiệm cầm đồ đã thâu tóm **{item_value}**.\nBạn vớt vát lại được **{sell_price:,} 💰**!"

        user_data["money"] += sell_price
        save_user(user_id)
        add_history(user_id, f"Bán {item_value} (+{sell_price:,} 💰)")
        
        embed = discord.Embed(title="🤝 GIAO DỊCH HOÀN TẤT", description=success_message, color=discord.Color.dark_orange())
        await interaction.response.edit_message(embed=embed, view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Cắm Sổ Đỏ / Cầm Xe", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: 
            return await interaction.response.send_message("Bạn không có tài sản nào để bán!", ephemeral=True)
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        embed = discord.Embed(title="🏷️ CẦM ĐỒ BĐS & XE CỘ", description="Bị ép giá 40% so với giá mua.", color=discord.Color.orange())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(quantity == 0 for quantity in pets.values()): 
            return await interaction.response.send_message("Bạn chưa có Thú cưng nào để bán!", ephemeral=True)
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        embed = discord.Embed(title="🏷️ TRẠM THU MUA THÚ CƯNG", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction): 
        return interaction.user.id == self.author.id

class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Rủi ro thấp, phần thưởng: ~350 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Rủi ro trung bình, phần thưởng: ~800 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Rủi ro cao, phần thưởng: ~1500 💰", emoji="🏛️", value="12")
        ]
        super().__init__(placeholder="Lựa chọn địa điểm hạ trại...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        hours = int(self.values[0])
        if hours == 4: reward = random.randint(200, 500)
        elif hours == 8: reward = random.randint(500, 1000)
        else: reward = random.randint(1000, 2000)
            
        end_time = datetime.now() + timedelta(hours=hours)
        user_data["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = reward
        save_user(user_id)

        embed_success = discord.Embed(title="⛺ LÊN ĐƯỜNG BÌNH AN!", description=f"Bạn bắt đầu cắm trại **{hours} giờ**.\n\n⏳ Gõ lại `k phai` để thu hoạch khi hết giờ nhé.", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed_success, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, interaction: discord.Interaction): 
        return interaction.user.id == self.author.id

# =====================================================================
# CLASS NHÂN SINH GAME
# =====================================================================
class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        self.ev = random.choice(EVENTS_P1)

        if self.stats["may_man"] >= 8: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng, bố mẹ là tài phiệt.")
        elif self.stats["may_man"] >= 4: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức bình dân.")
        else: self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt ra ngoài bãi rác từ nhỏ.")

        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text'][:70]}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text'][:70]}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text'][:70]}", style=discord.ButtonStyle.success, custom_id="btn_c")
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text'][:70]}", style=discord.ButtonStyle.danger, custom_id="btn_d")
        
        self.btn_a.callback = self.choice_a
        self.btn_b.callback = self.choice_b
        self.btn_c.callback = self.choice_c
        self.btn_d.callback = self.choice_d
        
        self.add_item(self.btn_a)
        self.add_item(self.btn_b)
        self.add_item(self.btn_c)
        self.add_item(self.btn_d)

    async def on_timeout(self):
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh!", ephemeral=True)
            return False
        return True

    async def choice_a(self, interaction: discord.Interaction): await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        calculated_rate = base_rate + (self.stats["may_man"] * 1.5)
        final_rate = min(85.0, calculated_rate)
        
        roll = random.uniform(0, 100)
        is_win = roll <= final_rate
        
        result_msg = choice_data["win"] if is_win else choice_data["lose"]
        money_change = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        is_dead = False
        if is_win and choice_data.get("die_w", False): is_dead = True
        if not is_win and choice_data.get("die_l", False): is_dead = True

        self.tien_an += money_change
        
        status_icon = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ: **{final_rate:.1f}%** (Roll: {roll:.1f})\n{status_icon}: {result_msg} ({money_change:,} 💰)"
        
        if self.phase == 1: tuoi_hien_tai = 15
        elif self.phase == 2: tuoi_hien_tai = 25
        elif self.phase == 3: tuoi_hien_tai = 35
        elif self.phase == 4: tuoi_hien_tai = 50
        else: tuoi_hien_tai = 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Bạn chọn {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ!**")
            self.phase = 99
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Bạn chọn {letter}.\n{log_entry}")
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH", description=f"Ký chủ: {self.author.mention}", color=discord.Color.teal())
        stats_text = f"Tâm linh / May mắn: **{self.stats['may_man']}/10** *(Buff +{self.stats['may_man']*1.5}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số ban đầu", value=stats_text, inline=False)

        if len(self.logs) > 4: story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else: story = "\n\n".join(self.logs)
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase <= 5:
            if self.phase == 1: tuoi_next = 15
            elif self.phase == 2: tuoi_next = 25
            elif self.phase == 3: tuoi_next = 35
            elif self.phase == 4: tuoi_next = 50
            else: tuoi_next = 70
            
            embed.add_field(name=f"❓ Ngã rẽ tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.clear_items() 
            
            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

            user_data = load_user(user_id)
            user_data["money"] = max(0, user_data["money"] + self.tien_an)
            save_user(user_id)
            add_history(user_id, f"Kết thúc Nhân Sinh ({'+' if self.tien_an >= 0 else ''}{self.tien_an:,} 💰)")

            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại một đống nợ.\n❌ **BÁO NHÀ!** Khoản nợ: **{self.tien_an:,} 💰**", inline=False)
            elif self.tien_an >= 500000:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa vinh hoa.\n👑 **TỶ PHÚ ĐỜI THẬT!** Di sản: **+{self.tien_an:,} 💰**", inline=False)
            else:
                embed.color = discord.Color.blue()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Một cuộc đời êm ấm trôi qua.\n💼 **DƯ DẢ!** Di sản: **+{self.tien_an:,} 💰**", inline=False)

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

class SoloOTTGame(discord.ui.View):
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1; self.player_2 = player_2; self.bet_amount = bet_amount
        self.msg = None; self.choices = {str(player_1.id): None, str(player_2.id): None}
        self.finished = False

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "🪨")
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "📄")
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "✂️")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = str(interaction.user.id)
        if user_id not in self.choices: 
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Đây là trận chiến riêng tư của hai người họ!", color=discord.Color.red()), ephemeral=True)
        if self.choices[user_id] is not None: 
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Bạn đã ra chiêu rồi!", color=discord.Color.red()), ephemeral=True)
            
        self.choices[user_id] = choice
        await interaction.response.send_message(embed=discord.Embed(description=f"🤫 Bạn đã chọn **{choice}**. Chờ đối thủ ra chiêu...", color=discord.Color.green()), ephemeral=True)

        if self.choices[str(self.player_1.id)] is not None and self.choices[str(self.player_2.id)] is not None:
            if self.finished: return
            self.finished = True
            for child in self.children: child.disabled = True
            choice_1 = self.choices[str(self.player_1.id)]
            choice_2 = self.choices[str(self.player_2.id)]
            p1_data = load_user(self.player_1.id); p2_data = load_user(self.player_2.id)
            tong_thuong = self.bet_amount * 2
            
            if choice_1 == choice_2:
                ket_qua = "🤝 **HÒA NHAU!** Tiền cược được trả lại."
                p1_data["money"] += self.bet_amount; p2_data["money"] += self.bet_amount
            elif (choice_1 == "🪨" and choice_2 == "✂️") or (choice_1 == "📄" and choice_2 == "🪨") or (choice_1 == "✂️" and choice_2 == "📄"):
                ket_qua = f"🎉 **{self.player_1.name} ĐÃ CHIẾN THẮNG!** Húp trọn **{tong_thuong:,} 💰**."
                p1_data["money"] += tong_thuong
                add_history(self.player_1.id, f"Thắng PK OTT (+{tong_thuong:,} 💰)")
            else:
                ket_qua = f"🎉 **{self.player_2.name} ĐÃ CHIẾN THẮNG!** Húp trọn **{tong_thuong:,} 💰**."
                p2_data["money"] += tong_thuong
                add_history(self.player_2.id, f"Thắng PK OTT (+{tong_thuong:,} 💰)")
                
            save_user(self.player_1.id); save_user(self.player_2.id)
            
            embed_result = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed_result.add_field(name=self.player_1.name, value=f"Ra {choice_1}", inline=True)
            embed_result.add_field(name="VS", value="⚡", inline=True)
            embed_result.add_field(name=self.player_2.name, value=f"Ra {choice_2}", inline=True)
            embed_result.add_field(name="KẾT QUẢ", value=ket_qua, inline=False)
            
            await self.msg.edit(embed=embed_result, view=self)
            self.stop()

    async def on_timeout(self):
        if self.finished: return
        p1_data = load_user(self.player_1.id); p2_data = load_user(self.player_2.id)
        p1_data["money"] += self.bet_amount; p2_data["money"] += self.bet_amount
        save_user(self.player_1.id); save_user(self.player_2.id)
        try: await self.msg.edit(embed=discord.Embed(title="⏳ HẾT GIỜ", description="Trận đấu bị hủy, tiền cược đã hoàn trả!", color=discord.Color.dark_gray()), view=None)
        except Exception: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1; self.player_2 = player_2; self.bet_amount = bet_amount

    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_2.id:
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Kèo này không dành cho bạn!", color=discord.Color.red()), ephemeral=True)
        
        p1_data = load_user(self.player_1.id); p2_data = load_user(self.player_2.id)
        if p1_data.get("money", 0) < self.bet_amount or p2_data.get("money", 0) < self.bet_amount:
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Một trong hai không đủ tiền!", color=discord.Color.red()), ephemeral=True)
        
        p1_data["money"] -= self.bet_amount; p2_data["money"] -= self.bet_amount
        save_user(self.player_1.id); save_user(self.player_2.id)

        game_view = SoloOTTGame(self.player_1, self.player_2, self.bet_amount)
        embed_game = discord.Embed(title="⚔️ PK OẲN TÙ TÌ", description=f"{self.player_1.mention} 🆚 {self.player_2.mention}\nTiền cược: **{self.bet_amount:,} 💰**\n\n👇 **BẤM NÚT ĐỂ CHỌN CHIÊU (Bí mật)**", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed_game, view=game_view)
        game_view.msg = interaction.message
        self.stop()

class MarryAccept(discord.ui.View):
    def __init__(self, sender, receiver):
        super().__init__(timeout=60)
        self.sender = sender; self.receiver = receiver
        
    @discord.ui.button(label="Em Đồng Ý", style=discord.ButtonStyle.success, emoji="💍")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: 
            return await interaction.response.send_message("Người ta đang cầu hôn người khác!", ephemeral=True)
            
        sender_data = load_user(self.sender.id); receiver_data = load_user(self.receiver.id)
        if sender_data.get("money", 0) < 1000000: 
            return await interaction.response.send_message(f"⚠️ {self.sender.name} không đủ 1 Triệu sắm Lễ Cưới!", ephemeral=True)
            
        sender_data["money"] -= 1000000
        sender_data["spouse"] = str(self.receiver.id)
        receiver_data["spouse"] = str(self.sender.id)
        save_user(self.sender.id); save_user(self.receiver.id)
        
        for child in self.children: child.disabled = True
            
        embed_success = discord.Embed(title="💒 KẾT HÔN THÀNH CÔNG", description=f"🎉 Xin chúc mừng {self.sender.mention} và {self.receiver.mention}!\nTrăm năm hạnh phúc nhé!", color=discord.Color.magenta())
        embed_success.set_image(url=GIF_LINKS["marry"])
        await interaction.response.edit_message(embed=embed_success, view=self)
        self.stop()
        
    @discord.ui.button(label="Em Từ Chối", style=discord.ButtonStyle.danger, emoji="💔")
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        for child in self.children: child.disabled = True
        embed_fail = discord.Embed(description=f"💔 {self.receiver.mention} đã từ chối phũ phàng lời cầu hôn của {self.sender.mention}...", color=discord.Color.dark_grey())
        await interaction.response.edit_message(embed=embed_fail, view=self)
        self.stop()

class CompanyInviteView(discord.ui.View):
    def __init__(self, comp_id, comp_name, target_user):
        super().__init__(timeout=60)
        self.comp_id = comp_id; self.comp_name = comp_name; self.target_user = target_user

    @discord.ui.button(label="Đồng ý Gia nhập", style=discord.ButtonStyle.success, emoji="🤝")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Lệnh mời này không dành cho bạn!", ephemeral=True)
        target_id = str(self.target_user.id); target_data = load_user(target_id)
        
        if target_data.get("company"): return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Bạn đang thuộc về một công ty rồi!", color=discord.Color.red()), ephemeral=True)
        
        comp = load_company(self.comp_id)
        if not comp: return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Công ty này đã không còn tồn tại!", color=discord.Color.red()), ephemeral=True)
        
        comp["members"][target_id] = "nhanvien"
        target_data["company"] = self.comp_id
        save_company(self.comp_id); save_user(target_id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=f"🎉 {self.target_user.mention} đã gia nhập công ty **{self.comp_name}**!", color=discord.Color.green()), view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=f"❌ {self.target_user.mention} đã từ chối lời mời của **{self.comp_name}**.", color=discord.Color.red()), view=None)

class MaSoiVoteView(discord.ui.View):
    def __init__(self, lobby):
        super().__init__(timeout=60)
        self.lobby = lobby
        options = [discord.SelectOption(label=p.name, value=str(p.id)) for p in lobby["players"]]
        self.select = discord.ui.Select(placeholder="Chọn người bạn nghi là Sói...", options=options)
        self.select.callback = self.vote_callback
        self.add_item(self.select)

    async def vote_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in [str(p.id) for p in self.lobby["players"]]:
            return await interaction.response.send_message("Bạn không có trong ván chơi này!", ephemeral=True)
            
        target_id = self.select.values[0]
        self.lobby["votes"][user_id] = target_id
        await interaction.response.send_message(f"Bạn đã bỏ phiếu treo cổ <@{target_id}>.", ephemeral=True)

class DuelAccept(discord.ui.View):
    def __init__(self, challenger, target, bet):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target
        self.bet = bet
        self.finished = False

    @discord.ui.button(label="Chấp Nhận Thách Đấu!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("Không phải bạn được thách đấu!", ephemeral=True)
        if self.finished: return
        self.finished = True
        
        c_data = load_user(self.challenger.id)
        t_data = load_user(self.target.id)
        
        if c_data.get("money", 0) < self.bet or t_data.get("money", 0) < self.bet:
            return await interaction.response.send_message("Một trong hai không đủ tiền!", ephemeral=True)
        
        c_data["money"] -= self.bet
        t_data["money"] -= self.bet
        save_user(self.challenger.id)
        save_user(self.target.id)
        
        c_hp = 100; t_hp = 100
        battle_log = []
        rounds = 0
        
        while c_hp > 0 and t_hp > 0 and rounds < 10:
            rounds += 1
            c_atk = random.randint(8, 28)
            t_atk = random.randint(8, 28)
            t_hp -= c_atk
            c_hp -= t_atk
            battle_log.append(f"**Vòng {rounds}:** {self.challenger.name} gây {c_atk} ST | {self.target.name} gây {t_atk} ST")
        
        if c_hp > t_hp:
            winner = self.challenger
            loser = self.target
        elif t_hp > c_hp:
            winner = self.target
            loser = self.challenger
        else:
            winner = random.choice([self.challenger, self.target])
            loser = self.target if winner == self.challenger else self.challenger
        
        prize = self.bet * 2
        winner_data = load_user(winner.id)
        winner_data["money"] += prize
        save_user(winner.id)
        add_history(winner.id, f"Thắng Duel vs {loser.name} (+{prize:,} 💰)")
        
        embed = discord.Embed(title="⚔️ KẾT QUẢ QUYẾT ĐẤU", color=discord.Color.gold())
        embed.add_field(name="📜 Diễn Biến Trận Đấu", value="\n".join(battle_log[-5:]), inline=False)
        embed.add_field(name="🏆 KẾT QUẢ", value=f"**{winner.mention}** đã chiến thắng và nhận **{prize:,} 💰**!", inline=False)
        embed.set_image(url=GIF_LINKS["duel"])
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="Nhút Nhát Từ Chối", style=discord.ButtonStyle.secondary, emoji="🏳️")
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("Không phải bạn!", ephemeral=True)
        await interaction.response.edit_message(embed=discord.Embed(description=f"🏳️ {self.target.mention} đã bỏ chạy nhục nhã! Không có tiền nào thay đổi tay.", color=discord.Color.dark_grey()), view=None)
        self.stop()

# =====================================================================
# HỆ THỐNG LỆNH CÔNG TY (giữ nguyên từ code gốc)
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
async def nangcap(ctx, stat: str):
    stat = stat.lower(); user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn chưa có công ty!")
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Chỉ Sếp mới được nâng cấp!")
    if stat == "cong":
        current_lvl = comp.get("atk_level", 1); cost = current_lvl * 500000
        if comp["treasury"] < cost: return await ctx.reply(f"⚠️ Quỹ không đủ **{cost:,} 💰**!")
        comp["treasury"] -= cost; comp["atk_level"] = current_lvl + 1
        msg = f"⚔️ Nâng CÔNG lên Lv{current_lvl+1}! (Trừ {cost:,} 💰 từ quỹ)"
    elif stat == "thu":
        current_lvl = comp.get("def_level", 1); cost = current_lvl * 300000
        if comp["treasury"] < cost: return await ctx.reply(f"⚠️ Quỹ không đủ **{cost:,} 💰**!")
        comp["treasury"] -= cost; comp["def_level"] = current_lvl + 1
        msg = f"🛡️ Nâng KHIÊN THỦ lên Lv{current_lvl+1}! (Trừ {cost:,} 💰 từ quỹ)"
    else: return await ctx.reply("⚠️ Dùng `k cty nangcap cong` hoặc `k cty nangcap thu`.")
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

@bot.command()
async def daichien(ctx, action: str = None, member: discord.Member = None, tactic: str = None):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    
    if not action or action.lower() not in ["dotham", "danh"]:
        embed_help = discord.Embed(title="⚔️ ĐẠI CHIẾN THƯƠNG TRƯỜNG", description="`k daichien dotham @user`: Xem lén sức mạnh đối thủ (50k quỹ).\n`k daichien danh @user <hack/phot/giangho>`: Tấn công.", color=discord.Color.red())
        embed_help.set_image(url=GIF_LINKS.get("fight", ""))
        return await ctx.send(embed=embed_help)
        
    if not member or member.bot: return await ctx.reply("⚠️ Tag một người chơi cụ thể!")
    target_id = str(member.id); target_comp_id = load_user(target_id).get("company")
    
    if not comp_id or not target_comp_id: return await ctx.reply("⚠️ Cả 2 đều phải ở trong công ty!")
    if comp_id == target_comp_id: return await ctx.reply("⚠️ Đánh người cùng công ty làm gì!")
    
    comp1 = load_company(comp_id); comp2 = load_company(target_comp_id)
    
    if action.lower() == "dotham":
        if comp1["treasury"] < 50000: return await ctx.reply("Quỹ không đủ 50k để thuê thám tử!")
        comp1["treasury"] -= 50000; save_company(comp_id)
        embed = discord.Embed(title="🕵️ KẾT QUẢ DO THÁM", description=f"Mục tiêu: **{comp2['name']}**\n💰 Quỹ ước tính: **~{int(comp2['treasury']*random.uniform(0.8, 1.2)):,} 💰**\n🛡️ Cấp phòng thủ: **Lv{comp2.get('def_level', 1)}**", color=discord.Color.blurple())
        return await ctx.reply(embed=embed, mention_author=False)
        
    if action.lower() == "danh":
        if not tactic or tactic.lower() not in ["hack", "phot", "giangho"]: return await ctx.reply("⚠️ Chọn chiến thuật: `hack`, `phot`, hoặc `giangho`.")
        now = datetime.now()
        if comp_id in cty_cooldowns and (now - cty_cooldowns[comp_id]).total_seconds() < 3600: return await ctx.reply(embed=discord.Embed(description="⏳ Công ty đang nghỉ ngơi, 1 tiếng sau mới xuất quân được.", color=discord.Color.orange()), mention_author=False)
        if comp2["treasury"] < 10000: return await ctx.reply("⚠️ Công ty đối thủ quá nghèo, đánh không bõ!")
        
        cty_cooldowns[comp_id] = now; tactic = tactic.lower()
        if tactic == "hack": win_rate, win_pct, lose_pct, name = 30, 0.10, 0.05, "TẤN CÔNG MẠNG"
        elif tactic == "phot": win_rate, win_pct, lose_pct, name = 50, 0.05, 0.05, "THUÊ BÁO CHÍ BÓC PHỐT"
        else: win_rate, win_pct, lose_pct, name = 70, 0.02, 0.01, "ĐƯA GIANG HỒ ĐẾN ĐẬP PHÁ"
        
        atk_diff = comp1.get("atk_level", 1) - comp2.get("def_level", 1)
        final_win_rate = min(90, max(5, win_rate + (atk_diff * 5)))
        
        msg = await ctx.send(embed=discord.Embed(description=f"⚔️ **{comp1['name']}** dùng **{name}** lên **{comp2['name']}**...\n*(Tỉ lệ thắng: {final_win_rate}%)*", color=discord.Color.dark_grey()))
        await asyncio.sleep(2.5)
        
        if random.randint(1, 100) <= final_win_rate:
            if tactic == "phot":
                rep_dmg = random.randint(20, 40)
                comp2["reputation"] = max(0, comp2.get("reputation", 100) - rep_dmg)
                comp2["has_scandal"] = True
                save_company(target_comp_id)
                await msg.edit(embed=discord.Embed(title="🔥 LIÊN HOÀN PHỐT", description=f"Đã bóc phốt **{comp2['name']}**!\n📉 Danh tiếng giảm **{rep_dmg}** điểm và **dính Scandal**!", color=discord.Color.red()))
            else:
                steal = int(comp2["treasury"] * win_pct)
                comp1["treasury"] += steal; comp2["treasury"] -= steal
                save_company(comp_id); save_company(target_comp_id)
                await msg.edit(embed=discord.Embed(description=f"🔥 **ĐẠI THẮNG!** Cướp được **{steal:,} 💰**!", color=discord.Color.green()))
        else:
            fine = int(comp1["treasury"] * lose_pct)
            comp1["treasury"] -= fine; comp2["treasury"] += fine
            save_company(comp_id); save_company(target_comp_id)
            await msg.edit(embed=discord.Embed(description=f"💀 **THẤT BẠI!** Đền bù **{fine:,} 💰** cho đối thủ.", color=discord.Color.red()))

# =====================================================================
# SÀN CHỨNG KHOÁN
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    all_stocks = get_all_stocks()
    embed = discord.Embed(
        title="📈 SÀN CHỨNG KHOÁN PHỐ WALL", 
        description=(
            f"Giá cập nhật mỗi **15 phút** (cập nhật tiếp: <t:{get_next_15min_timestamp()}:R>)\n"
            f"💸 Phí giao dịch: Spread **3%** + Thuế bán **5%**\n"
            f"⏳ Cooldown mua/bán: **10 phút** mỗi lệnh\n\n"
            f"🛒 Mua: `k ck buy <MÃ> <SL>` | 💸 Bán: `k ck sell <MÃ> <SL>`\n"
            f"🏢 Lên Sàn: `k ck ipo`"
        ),
        color=discord.Color.blue()
    )
    for code, name in all_stocks.items():
        market_price = get_stock_price(code, 0)
        buy_price = get_stock_buy_price(code)
        sell_price = get_stock_sell_price(code)
        price_old = get_stock_price(code, -1)
        trend = "💀 ĐÁY XÃ HỘI" if market_price <= 1000 else ("🟩 Lên" if market_price > price_old else "🟥 Xuống")
        try:
            ipo_comp = companies_col.find_one({"is_ipo": True, "name": {"$regex": f"^{code}", "$options": "i"}})
        except Exception:
            ipo_comp = None
        scandal_mark = " 🚨(Phốt)" if ipo_comp and ipo_comp.get("has_scandal") else ""
        embed.add_field(
            name=f"🏢 {code} - {name}{scandal_mark}", 
            value=f"Mua: **{buy_price:,}** | Bán: **{sell_price:,}** 💰 *({trend})*", 
            inline=False
        )
    my_stocks = load_user(ctx.author.id).get("stocks", {})
    inv_str = "\n".join([f"🔸 {c}: {q} CP" for c, q in my_stocks.items() if q > 0])
    embed.add_field(name="🎒 Cổ phiếu bạn nắm giữ", value=inv_str if inv_str else "Ví đầu tư trống.", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    user_id = str(ctx.author.id)
    
    if not acquire_lock(user_id):
        return await ctx.reply(embed=discord.Embed(description="⚠️ Đang xử lý lệnh trước, vui lòng chờ!", color=discord.Color.orange()), mention_author=False)
    
    try:
        now = datetime.now()
        if user_id in stock_cooldowns:
            diff = (now - stock_cooldowns[user_id]).total_seconds()
            if diff < 600:
                return await ctx.reply(embed=discord.Embed(
                    description=f"⏳ Phải chờ **{int((600 - diff) / 60)}p {int((600 - diff) % 60)}s** trước khi giao dịch tiếp!",
                    color=discord.Color.orange()
                ), mention_author=False)
        
        code = code.upper()
        all_stocks = get_all_stocks()
        if code not in all_stocks:
            return await ctx.reply("⚠️ Mã CK không tồn tại!")
        if qty <= 0:
            return await ctx.reply("⚠️ Số lượng > 0!")
        if qty > 1000:
            return await ctx.reply("⚠️ Tối đa **1,000 cổ phiếu** mỗi lệnh!")
        
        market_price = get_stock_price(code)
        if market_price <= 1000:
            return await ctx.reply("⚠️ Sàn khóa mua mã rác rưởi!")
        
        buy_price = get_stock_buy_price(code)
        total_cost = buy_price * qty
        
        user_data = load_user(user_id)
        if user_data.get("money", 0) < total_cost:
            return await ctx.reply(f"⚠️ Thiếu lúa! Cần **{total_cost:,} 💰** (Giá mua: {buy_price:,}/CP).")
        
        user_data["money"] -= total_cost
        
        if total_cost >= 30000000 and random.randint(1, 100) <= 20:
            add_history(user_id, f"Bị Úp Bô CK {code} (-{total_cost:,} 💰)")
            save_user(user_id)
            return await ctx.reply(embed=discord.Embed(title="🚨 RUG PULL", description=f"CEO ôm **{total_cost:,} 💰** của bạn bỏ trốn! Mất trắng!", color=discord.Color.red()))
        
        current_stocks = user_data.get("stocks", {})
        current_buy_prices = user_data.get("stock_buy_prices", {})
        
        old_qty = current_stocks.get(code, 0)
        old_avg_price = current_buy_prices.get(code, buy_price)
        new_qty = old_qty + qty
        new_avg_price = int((old_qty * old_avg_price + qty * buy_price) / new_qty)
        
        user_data["stocks"][code] = new_qty
        if "stock_buy_prices" not in user_data:
            user_data["stock_buy_prices"] = {}
        user_data["stock_buy_prices"][code] = new_avg_price
        
        stock_cooldowns[user_id] = now
        save_user(user_id)
        add_history(user_id, f"Mua {qty} CP {code} @ {buy_price:,} (-{total_cost:,} 💰)")
        
        await ctx.reply(embed=discord.Embed(
            description=f"✅ Mua **{qty} {code}** @ **{buy_price:,}/CP**\nTổng: **{total_cost:,} 💰**\n⏳ Cooldown giao dịch: 10 phút",
            color=discord.Color.green()
        ))
    finally:
        release_lock(user_id)

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    user_id = str(ctx.author.id)
    
    if not acquire_lock(user_id):
        return await ctx.reply(embed=discord.Embed(description="⚠️ Đang xử lý lệnh trước, vui lòng chờ!", color=discord.Color.orange()), mention_author=False)
    
    try:
        now = datetime.now()
        if user_id in stock_cooldowns:
            diff = (now - stock_cooldowns[user_id]).total_seconds()
            if diff < 600:
                return await ctx.reply(embed=discord.Embed(
                    description=f"⏳ Phải chờ **{int((600 - diff) / 60)}p {int((600 - diff) % 60)}s** trước khi giao dịch tiếp!",
                    color=discord.Color.orange()
                ), mention_author=False)
        
        code = code.upper()
        user_data = load_user(user_id)
        if code not in get_all_stocks():
            return await ctx.reply("⚠️ Mã CK không tồn tại!")
        
        owned_qty = user_data.get("stocks", {}).get(code, 0)
        if qty <= 0 or owned_qty < qty:
            return await ctx.reply(f"⚠️ Bạn chỉ có **{owned_qty} CP {code}**!")
        
        sell_price = get_stock_sell_price(code)
        total_gain = sell_price * qty
        
        avg_buy_price = user_data.get("stock_buy_prices", {}).get(code, sell_price)
        profit = (sell_price - avg_buy_price) * qty
        profit_pct = ((sell_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0
        
        user_data["stocks"][code] -= qty
        if user_data["stocks"][code] == 0:
            del user_data["stocks"][code]
            if code in user_data.get("stock_buy_prices", {}):
                del user_data["stock_buy_prices"][code]
        
        user_data["money"] += total_gain
        stock_cooldowns[user_id] = now
        save_user(user_id)
        add_history(user_id, f"Bán {qty} CP {code} @ {sell_price:,} (+{total_gain:,} 💰)")
        
        profit_text = f"📈 Lãi: **+{profit:,} 💰** (+{profit_pct:.1f}%)" if profit >= 0 else f"📉 Lỗ: **{profit:,} 💰** ({profit_pct:.1f}%)"
        color = discord.Color.green() if profit >= 0 else discord.Color.red()
        
        await ctx.reply(embed=discord.Embed(
            description=f"✅ Bán **{qty} {code}** @ **{sell_price:,}/CP**\nThu về: **{total_gain:,} 💰** (đã trừ thuế 5%)\n{profit_text}\n⏳ Cooldown giao dịch: 10 phút",
            color=color
        ))
    finally:
        release_lock(user_id)

@chungkhoan.command()
async def ipo(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn chưa có công ty!", color=discord.Color.red()), mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply(embed=discord.Embed(description="⚠️ Chỉ Chủ Tịch mới được quyết định IPO!", color=discord.Color.red()), mention_author=False)
    if comp.get("is_ipo"): return await ctx.reply(embed=discord.Embed(description="⚠️ Công ty đã được niêm yết rồi!", color=discord.Color.orange()), mention_author=False)
    if comp["treasury"] < 50000000: return await ctx.reply(embed=discord.Embed(description="⚠️ Điều kiện niêm yết: Quỹ tối thiểu **50,000,000 💰**.", color=discord.Color.red()), mention_author=False)
    comp["is_ipo"] = True; save_company(comp_id)
    mã_ck = comp["name"][:4].upper()
    embed_success = discord.Embed(title="📈 CHÀO SÀN THÀNH CÔNG", description=f"**{comp['name']}** đã IPO!\nMã cổ phiếu: **{mã_ck}**\n\n⚠️ Lưu ý: Giá sẽ biến động mỗi 15 phút, có spread 3% và thuế bán 5%.", color=discord.Color.green())
    await ctx.reply(embed=embed_success, mention_author=False)

# =====================================================================
# HỆ THỐNG NGÂN HÀNG
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    user_data = load_user(ctx.author.id)
    embed = discord.Embed(title="🏦 NGÂN HÀNG TRUNG ƯƠNG SERVER", description="📥 `k bank gui <số tiền / all>`: Gửi tiền\n📤 `k bank rut <số tiền / all>`: Rút tiền\n📈 `k bank laisuat`: Nhận lãi **0.1%/ngày**", color=discord.Color.blue())
    embed.add_field(name="💳 Ví Tiền Mặt", value=f"**{user_data.get('money', 0):,} 💰**", inline=True)
    embed.add_field(name="🏦 Két Sắt", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    embed.set_thumbnail(url=GIF_LINKS.get("bank", ""))
    await ctx.reply(embed=embed, mention_author=False)

@bank.command()
async def laisuat(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); bank_bal = user_data.get("bank", 0)
    if bank_bal < 50000: return await ctx.reply(embed=discord.Embed(description="⚠️ Gửi trên 50k mới được tính lãi suất.", color=discord.Color.red()), mention_author=False)
    now = datetime.now()
    try:
        last = datetime.strptime(user_data.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    except Exception:
        last = datetime(2000, 1, 1)
    if now - last < timedelta(days=1):
        next_time = int((last + timedelta(days=1)).timestamp())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Quay lại vào: <t:{next_time}:R>", color=discord.Color.orange()), mention_author=False)
    interest = int(bank_bal * 0.001)
    user_data["bank"] += interest; user_data["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id); add_history(user_id, f"Nhận lãi ngân hàng (+{interest:,} 💰)")
    await ctx.reply(embed=discord.Embed(description=f"📈 Ngân hàng cộng **{interest:,} 💰** (0.1%) vào két sắt.", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    try: 
        deposit_amount = user_data["money"] if amount.lower() == "all" else int(amount)
    except ValueError: return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập số tiền hoặc `all`!", color=discord.Color.red()), mention_author=False)
    if deposit_amount <= 0 or deposit_amount > user_data["money"]: return await ctx.reply(embed=discord.Embed(description="⚠️ Không đủ tiền để gửi!", color=discord.Color.red()), mention_author=False)
    user_data["money"] -= deposit_amount; user_data["bank"] = user_data.get("bank", 0) + deposit_amount
    save_user(user_id); await ctx.reply(embed=discord.Embed(description=f"✅ Gửi **{deposit_amount:,} 💰** vào két sắt!", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id); bank_balance = user_data.get("bank", 0)
    try: 
        withdraw_amount = bank_balance if amount.lower() == "all" else int(amount)
    except ValueError: return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập số tiền hoặc `all`!", color=discord.Color.red()), mention_author=False)
    if withdraw_amount <= 0 or withdraw_amount > bank_balance: return await ctx.reply(embed=discord.Embed(description="⚠️ Số dư không đủ!", color=discord.Color.red()), mention_author=False)
    user_data["bank"] -= withdraw_amount; user_data["money"] += withdraw_amount
    save_user(user_id); await ctx.reply(embed=discord.Embed(description=f"✅ Rút **{withdraw_amount:,} 💰** ra ví!", color=discord.Color.green()), mention_author=False)

# =====================================================================
# HỆ THỐNG NÔNG TRẠI
# =====================================================================
@bot.command(aliases=['ls'])
async def lichsu(ctx):
    history = load_user(ctx.author.id).get("history", [])
    if not history: return await ctx.reply(embed=discord.Embed(description="Chưa có lịch sử giao dịch.", color=discord.Color.light_grey()))
    await ctx.reply(embed=discord.Embed(title=f"📜 LỊCH SỬ {ctx.author.name}", description="\n".join(history), color=discord.Color.blue()))

@bot.group(invoke_without_command=True, aliases=['farm'])
async def nongtrai(ctx):
    user_data = load_user(ctx.author.id)
    farm = user_data.get("farm", {"seed": None, "plant_time": None})
    embed = discord.Embed(title="🏡 NÔNG TRẠI VUI VẺ", color=discord.Color.green())
    seed_list = "\n".join([f"`{k}`: {v['name']} | Giá: {v['cost']:,} 💰 | Thời gian: {v['time_hours']}h" for k, v in FARM_SEEDS.items()])
    
    if not farm.get("seed"):
        embed.description = f"Đất trống.\n\n**Danh sách hạt giống:**\n{seed_list}\n\n🛒 Mua: `k farm mua <tên>` | 🌱 Trồng: `k farm trong <tên>`"
    else:
        seed_info = FARM_SEEDS.get(farm["seed"])
        if not seed_info:
            embed.description = "Lỗi: Hạt giống không hợp lệ. Đất đã được dọn sạch."
            user_data["farm"] = {"seed": None, "plant_time": None}
            save_user(ctx.author.id)
        else:
            try:
                harvest_time = datetime.strptime(farm["plant_time"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=seed_info["time_hours"])
                if datetime.now() >= harvest_time: embed.description = f"🌾 **{seed_info['name']}** đã chín! Gõ `k farm thuhoach`"; embed.color = discord.Color.gold()
                else: embed.description = f"🌱 Đang trồng **{seed_info['name']}**.\n⏳ Thu hoạch: <t:{int(harvest_time.timestamp())}:R>"
            except Exception:
                embed.description = "Lỗi đọc thời gian trồng. Đất đã được dọn sạch."
                user_data["farm"] = {"seed": None, "plant_time": None}
                save_user(ctx.author.id)
    await ctx.reply(embed=embed)

@nongtrai.command()
async def mua(ctx, seed: str):
    seed = seed.lower()
    if seed not in FARM_SEEDS: return await ctx.reply(f"⚠️ Các loại: {', '.join(FARM_SEEDS.keys())}")
    user_id = str(ctx.author.id); user_data = load_user(user_id); cost = FARM_SEEDS[seed]["cost"]
    if user_data.get("money", 0) < cost: return await ctx.reply(f"⚠️ Cần **{cost:,} 💰**.")
    user_data["money"] -= cost; user_data["assets"].append(f"Hạt giống {FARM_SEEDS[seed]['name']}")
    save_user(user_id); add_history(user_id, f"Mua Hạt {FARM_SEEDS[seed]['name']} (-{cost:,})")
    await ctx.reply(embed=discord.Embed(description=f"🛒 Mua thành công! Gõ `k farm trong {seed}`.", color=discord.Color.green()))

@nongtrai.command()
async def trong(ctx, seed: str):
    seed = seed.lower(); user_id = str(ctx.author.id); user_data = load_user(user_id)
    seed_asset = f"Hạt giống {FARM_SEEDS.get(seed, {}).get('name', '')}"
    if seed_asset not in user_data.get("assets", []): return await ctx.reply("⚠️ Không có hạt giống này trong kho!")
    if user_data.get("farm", {}).get("seed"): return await ctx.reply("⚠️ Đất đang bận trồng cây khác!")
    user_data["assets"].remove(seed_asset)
    user_data["farm"] = {"seed": seed, "plant_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"🌱 Đã gieo **{FARM_SEEDS[seed]['name']}** xuống đất.", color=discord.Color.green()))

@nongtrai.command()
async def thuhoach(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); farm = user_data.get("farm", {})
    if not farm.get("seed"): return await ctx.reply("⚠️ Đất trống lấy gì thu hoạch!")
    seed_info = FARM_SEEDS.get(farm["seed"])
    if not seed_info:
        user_data["farm"] = {"seed": None, "plant_time": None}
        save_user(user_id)
        return await ctx.reply("⚠️ Hạt giống lỗi, đã dọn sạch đất.")
    try:
        harvest_time = datetime.strptime(farm["plant_time"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=seed_info["time_hours"])
    except Exception:
        user_data["farm"] = {"seed": None, "plant_time": None}
        save_user(user_id)
        return await ctx.reply("⚠️ Lỗi dữ liệu farm, đã reset.")
    if datetime.now() < harvest_time: return await ctx.reply(f"⏳ Cây chưa chín! Chờ đến <t:{int(harvest_time.timestamp())}:R>.")
    profit = random.randint(seed_info["profit_min"], seed_info["profit_max"])
    user_data["money"] += profit; user_data["farm"] = {"seed": None, "plant_time": None}
    save_user(user_id); add_history(user_id, f"Thu hoạch {seed_info['name']} (+{profit:,})")
    
    quest_msg = update_quest_progress(user_id, "farm")
    result_text = f"🌾 Gặt **{seed_info['name']}** bán được **{profit:,} 💰**!"
    if quest_msg: result_text += f"\n\n{quest_msg}"
    await ctx.reply(embed=discord.Embed(description=result_text, color=discord.Color.gold()))

# =====================================================================
# HỆ THỐNG CÂU CÁ
# =====================================================================
@bot.command(aliases=['caudu', 'fish'])
async def cauca(ctx):
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    if user_id in fishing_cooldowns:
        diff = (now - fishing_cooldowns[user_id]).total_seconds()
        if diff < 25:
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Đợi thêm {int(25 - diff)}s để cá cắn câu tiếp!", color=discord.Color.orange()), mention_author=False)
    
    user_data = load_user(user_id)
    assets = user_data.get("assets", [])
    
    if not any("Cần Câu" in a or "Máy Câu" in a for a in assets):
        return await ctx.reply(embed=discord.Embed(description="🎣 Bạn cần mua **Cần Câu** trước!\nVào `k cuahang` → **Dụng Cụ Câu Cá** để mua.", color=discord.Color.red()), mention_author=False)
    
    fishing_cooldowns[user_id] = now
    bonus = get_fish_bonus(user_data)
    
    msg = await ctx.reply(embed=discord.Embed(description="🎣 Đang thả mồi... câu đang chìm xuống...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(2)
    await msg.edit(embed=discord.Embed(description="🌊 Phao bắt đầu rung rung... có gì đó cắn câu!", color=discord.Color.teal()))
    await asyncio.sleep(1.5)
    
    roll = random.uniform(0, 100)
    cumulative = 0
    caught_rarity = "common"
    for rarity, data in FISH_TABLE.items():
        cumulative += data["rate"]
        if roll <= cumulative:
            caught_rarity = rarity
            break
    
    fish_pool = FISH_TABLE[caught_rarity]["pool"]
    fish_name, min_val, max_val = random.choice(fish_pool)
    fish_value = int(random.randint(min_val, max_val) * bonus)
    
    user_data["fish_count"] = user_data.get("fish_count", 0) + 1
    
    rarity_labels = {
        "common": ("🟤 PHỔ THÔNG", discord.Color.light_grey()),
        "rare": ("🔵 HIẾM", discord.Color.blue()),
        "epic": ("🟣 SỬ THI", discord.Color.purple()),
        "legendary": ("🟡 HUYỀN THOẠI", discord.Color.gold()),
        "trash": ("🗑️ RÁC", discord.Color.dark_grey()),
    }
    label, color = rarity_labels.get(caught_rarity, ("🟤 PHỔ THÔNG", discord.Color.light_grey()))
    
    if fish_value > 0:
        user_data["money"] += fish_value
        result_text = f"🎣 Câu được: **{fish_name}** [{label}]\n💰 Bán được: **{fish_value:,} 💰**"
    else:
        user_data["money"] += fish_value
        result_text = f"🗑️ Câu trúng: **{fish_name}** [{label}]\n😭 Chi phí dọn dẹp: **{fish_value:,} 💰**"
    
    save_user(user_id)
    add_history(user_id, f"Câu được {fish_name} ({'+' if fish_value > 0 else ''}{fish_value:,} 💰)")
    
    quest_msg = update_quest_progress(user_id, "fish")
    if quest_msg: result_text += f"\n\n{quest_msg}"
    
    new_achievements = check_achievement(user_id, user_data)
    if new_achievements:
        save_user(user_id)
        result_text += f"\n\n🏅 **THÀNH TÍCH MỚI:** " + ", ".join(new_achievements)
    
    embed_result = discord.Embed(title="🎣 KẾT QUẢ CÂU CÁ", description=result_text, color=color)
    embed_result.set_footer(text=f"Tổng câu được: {user_data.get('fish_count', 0)} con | Ví: {user_data.get('money', 0):,} 💰")
    await msg.edit(embed=embed_result)

# =====================================================================
# ĐI LÀM THÊM
# =====================================================================
@bot.command(aliases=['lamviec', 'work'])
async def dilamthem(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    last_work_str = user_data.get("last_work", "2000-01-01 00:00:00")
    try:
        last_work = datetime.strptime(last_work_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        last_work = datetime(2000, 1, 1)
    
    if now - last_work < timedelta(minutes=45):
        next_time = int((last_work + timedelta(minutes=45)).timestamp())
        return await ctx.reply(embed=discord.Embed(description=f"😓 Mệt quá rồi! Nghỉ ngơi đến <t:{next_time}:R> rồi đi làm tiếp.", color=discord.Color.orange()), mention_author=False)
    
    job = random.choice(JOBS)
    wage = random.randint(job["min"], job["max"])
    
    bad_event = None
    if random.randint(1, 100) <= 10:
        accident_cost = random.randint(1000, wage // 2)
        wage -= accident_cost
        bad_event = f"⚠️ Gặp sự cố trong ca làm! Mất **{accident_cost:,} 💰** chi phí phát sinh."
    
    wage = max(0, wage)
    user_data["money"] += wage
    user_data["last_work"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    add_history(user_id, f"Đi làm {job['name']} (+{wage:,} 💰)")
    
    quest_msg = update_quest_progress(user_id, "work")
    
    embed = discord.Embed(title="💼 NHẬN LƯƠNG RỒI!", description=f"Công việc hôm nay: **{job['name']}**\n_{job['desc']}_\n\n💰 Tiền lương nhận được: **{wage:,} 💰**", color=discord.Color.green())
    if bad_event: embed.description += f"\n\n{bad_event}"
    embed.set_thumbnail(url=GIF_LINKS["work"])
    embed.set_footer(text=f"Ví hiện tại: {user_data['money']:,} 💰 | Cooldown: 45 phút")
    if quest_msg: embed.description += f"\n\n{quest_msg}"
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# NHIỆM VỤ HÀNG NGÀY
# =====================================================================
@bot.command(aliases=['nhv', 'mission'])
async def nhiemvu(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    quest, is_new = get_or_assign_quest(user_data)
    save_user(user_id)
    
    if not quest:
        return await ctx.reply(embed=discord.Embed(description="Không có nhiệm vụ khả dụng.", color=discord.Color.red()))
    
    progress = user_data.get("quest_progress", 0)
    target = quest["target"]
    completed = progress >= target
    
    embed = discord.Embed(title="📋 NHIỆM VỤ HÀNG NGÀY", color=discord.Color.gold() if completed else discord.Color.blue())
    embed.add_field(name=f"{'✅' if completed else '🔄'} {quest['name']}", value=quest["desc"], inline=False)
    embed.add_field(name="📊 Tiến Độ", value=f"`{make_progress_bar(min(progress, target), target)}` {min(progress, target)}/{target}", inline=False)
    embed.add_field(name="🎁 Phần Thưởng", value=f"**{quest['reward']:,} 💰**", inline=True)
    
    if completed:
        embed.description = "✅ **Đã hoàn thành!** Nhiệm vụ mới sẽ xuất hiện sau 24 giờ."
    else:
        embed.set_footer(text="Nhiệm vụ reset mỗi 24 giờ.", icon_url=ctx.author.display_avatar.url)
    
    if is_new:
        embed.description = "🆕 Bạn vừa nhận nhiệm vụ mới!"
    
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# THÀNH TÍCH
# =====================================================================
@bot.command(aliases=['achievement', 'ach'])
async def thanhtich(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_data = load_user(target.id)
    achievements = user_data.get("achievements", [])
    
    ach_names = {
        "millionaire": "💰 Triệu Phú Đầu Tiên",
        "billionaire": "👑 Tỷ Phú Đồng",
        "level10": "⭐ Đạt Cấp 10",
        "level50": "🌟 Huyền Thoại Cấp 50",
        "pet_collector": "🐾 Nhà Thú Cưng (5 loài)",
        "fisher": "🎣 Ngư Dân Lão Luyện (50 cá)",
        "streak7": "🔥 Chuỗi 7 Ngày Điểm Danh",
        "streak30": "🌈 Chuỗi 30 Ngày Điểm Danh",
    }
    
    embed = discord.Embed(title=f"🏅 THÀNH TÍCH CỦA {target.name.upper()}", color=discord.Color.gold())
    
    if not achievements:
        embed.description = "Chưa có thành tích nào. Hãy chơi nhiều hơn!"
    else:
        ach_text = "\n".join([f"✅ {ach_names.get(a, a)}" for a in achievements])
        locked_text = "\n".join([f"🔒 {v}" for k, v in ach_names.items() if k not in achievements])
        embed.add_field(name=f"Đã đạt được ({len(achievements)}/{len(ach_names)})", value=ach_text, inline=False)
        if locked_text: embed.add_field(name="Chưa đạt", value=locked_text, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# MINIGAMES
# =====================================================================
@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    bank_bal = user_data.get("bank", 0)
    
    if bank_bal < 200000:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn cần gửi ít nhất **200,000 💰** trong ngân hàng để làm nội gián!", color=discord.Color.red()), mention_author=False)
    
    if user_id in rob_cooldowns and (now - rob_cooldowns[user_id]).total_seconds() < 7200:
        remaining = int(7200 - (now - rob_cooldowns[user_id]).total_seconds())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Đang bị truy nã! Hãy đi trốn **{remaining//60}p {remaining%60}s** nữa.", color=discord.Color.orange()), mention_author=False)
    
    rob_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Bạn đang lẻn vào két sắt ngân hàng...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= 20: 
        loot_amount = int(bank_bal * random.uniform(0.03, 0.10))
        user_data["money"] += loot_amount; save_user(user_id)
        add_history(user_id, f"Cướp Bank trót lọt (+{loot_amount:,} 💰)")
        embed_win = discord.Embed(title="🎉 PHI VỤ TRÓT LỌT!", description=f"Vơ vét được **{loot_amount:,} 💰** rồi chuồn êm!\n⏳ Cooldown: 2 giờ", color=discord.Color.green())
        embed_win.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed_win)
    else: 
        fine = int(bank_bal * 0.15)
        user_data["bank"] -= fine
        jail_time = now + timedelta(minutes=20)
        user_data["jail_time"] = jail_time.strftime("%Y-%m-%d %H:%M:%S")
        save_user(user_id); add_history(user_id, f"Cướp Bank xịt (-{fine:,} 💰)")
        embed_lose = discord.Embed(title="🚨 BỊ CÔNG AN TÓM GỌN", description=f"Bị bắt!\nNgân hàng siết nợ **{fine:,} 💰** từ két sắt.\n⛔ **BỊ TÙ ĐẾN: <t:{int(jail_time.timestamp())}:R>**!", color=discord.Color.red())
        embed_lose.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed_lose)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    
    if user_id in mining_cooldowns and (now - mining_cooldowns[user_id]).total_seconds() < 60:
        remaining = int(60 - (now - mining_cooldowns[user_id]).total_seconds())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Tay mỏi nhừ! Nghỉ {remaining}s.", color=discord.Color.orange()), mention_author=False)
    
    if "Cuốc Chim ⛏️" not in user_data.get("assets", []):
        if user_data.get("money", 0) < 10000: return await ctx.reply(embed=discord.Embed(description="⚠️ Không đủ **10,000 💰** mua Cuốc Chim!", color=discord.Color.red()), mention_author=False)
        user_data["money"] -= 10000; user_data["assets"].append("Cuốc Chim ⛏️")
        await ctx.send(embed=discord.Embed(description="🛒 Đã tự động trừ 10k để mua **Cuốc Chim ⛏️**!", color=discord.Color.blue()))
    
    mining_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(description="⛏️ Cạch... Cạch... Đang đào hầm mỏ âm u...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2)
    
    roll = random.randint(1, 100)
    if roll <= 45: result_name, value = "Cục Đá Vô Dụng 🪨", 0
    elif roll <= 72: result_name, value = "Mảnh Sắt Vụn 🔩", random.randint(500, 2000)
    elif roll <= 90: result_name, value = "Thỏi Vàng Ròng 🥇", random.randint(5000, 12000)
    elif roll <= 98: result_name, value = "Viên Kim Cương 💎", random.randint(40000, 80000)
    else: 
        penalty = int(user_data["money"] * 0.15) if user_data["money"] > 0 else 0
        user_data["money"] -= penalty; save_user(user_id)
        add_history(user_id, f"Đào trúng bom (-{penalty:,} 💰)")
        return await msg.edit(embed=discord.Embed(description=f"💥 **BÙMMMMM!** Đào trúng quả bom!\nViện phí: **{penalty:,} 💰**!", color=discord.Color.red()))

    user_data["money"] += value; save_user(user_id)
    if value > 0: add_history(user_id, f"Đào được {result_name} (+{value:,} 💰)")
    
    quest_msg = update_quest_progress(user_id, "mine")
    result_text = f"⛏️ Đào trúng: **{result_name}**\nBán được: **{value:,} 💰**"
    if quest_msg: result_text += f"\n\n{quest_msg}"
    
    embed_win = discord.Embed(description=result_text, color=discord.Color.green() if value > 0 else discord.Color.light_grey())
    embed_win.set_thumbnail(url=GIF_LINKS["mine"])
    await msg.edit(embed=embed_win)

@bot.command()
async def vietlott(ctx, so: int, amount: str):
    if so < 0 or so > 99: return await ctx.reply(embed=discord.Embed(description="⚠️ Chọn số từ 00 đến 99!", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    msg = await ctx.reply(embed=discord.Embed(description=f"🎫 Mua vé số **{so:02d}** giá **{bet_amount:,} 💰**.\n\n🎲 Lồng cầu đang quay...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(3)
    
    ket_qua = random.randint(0, 99)
    if so == ket_qua:
        win_amount = bet_amount * 60
        user_data["money"] += win_amount; save_user(user_id)
        add_history(user_id, f"Trúng Vietlott (+{win_amount:,} 💰)")
        await msg.edit(embed=discord.Embed(description=f"🎉 **TRÚNG ĐỘC ĐẮC!** Kết quả: **{ket_qua:02d}**!\nThu về **{win_amount:,} 💰** (gấp 60 lần)!", color=discord.Color.green()))
    else:
        add_history(user_id, f"Trượt Vietlott (-{bet_amount:,} 💰)")
        await msg.edit(embed=discord.Embed(description=f"💀 **TRẬT LẤT!** Kết quả: **{ket_qua:02d}**.\nMất **{bet_amount:,} 💰**.", color=discord.Color.red()))

@bot.command()
async def coin(ctx, amount: str):
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.reply(embed=discord.Embed(description=f"🪙 Tung **{bet_amount:,} 💰** lên trời...", color=discord.Color.gold()), mention_author=False)
    await asyncio.sleep(2) 

    if random.randint(1, 100) <= 48:
        user_data["money"] += bet_amount * 2; save_user(user_id)
        add_history(user_id, f"Tung xu Thắng (+{bet_amount:,} 💰)")
        quest_msg = update_quest_progress(user_id, "gamble")
        result = f"🪙 **ĐỒNG XU NGỬA!** Húp trọn **{bet_amount * 2:,} 💰**!"
        if quest_msg: result += f"\n\n{quest_msg}"
        await msg.edit(embed=discord.Embed(description=result, color=discord.Color.green()))
    else:
        add_history(user_id, f"Tung xu Thua (-{bet_amount:,} 💰)")
        quest_msg = update_quest_progress(user_id, "gamble")
        result = f"🪙 **ĐỒNG XU SẤP!** Mất **{bet_amount:,} 💰**."
        if quest_msg: result += f"\n\n{quest_msg}"
        await msg.edit(embed=discord.Embed(description=result, color=discord.Color.red()))

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    choice = choice.lower()
    if choice not in ["tai", "tài", "xiu", "xỉu"]: return await ctx.reply(embed=discord.Embed(description="⚠️ Dùng `k taixiu tai <tiền>` hoặc `xiu`.", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    msg = await ctx.reply(embed=discord.Embed(title="🎲 LẮC XÍ NGẦU", description=f"Cược **{bet_amount:,} 💰** vào cửa **{choice.upper()}**.\nNhà cái đang lắc... 🫨", color=discord.Color.gold()), mention_author=False)
    await asyncio.sleep(2.5)
    
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total_score = d1 + d2 + d3
    result_type = "xiu" if total_score <= 10 else "tai"
    result_embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    
    choice_map = {"tai": "tai", "tài": "tai", "xiu": "xiu", "xỉu": "xiu"}
    choice_key = choice_map.get(choice, "xiu")
    
    if choice_key == result_type:
        if d1 == d2 == d3:
            win_amt = bet_amount * 5
            result_txt = f"🔥 **BÃO {d1}-{d2}-{d3}!!! ĐẠI THẮNG x5!**\nHúp **{win_amt:,} 💰**!"
        else:
            win_amt = bet_amount * 2
            result_txt = f"✅ **THẮNG!** Nhận **{win_amt:,} 💰**!"
        user_data["money"] += win_amt
        add_history(user_id, f"Tài Xỉu Thắng (+{win_amt - bet_amount:,} 💰)")
        result_embed.color = discord.Color.green()
    else: 
        add_history(user_id, f"Tài Xỉu Thua (-{bet_amount:,} 💰)")
        result_txt = f"💀 **THUA!** Mất **{bet_amount:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    quest_msg = update_quest_progress(user_id, "gamble")
    result_embed.description = f"**[ {d1} | {d2} | {d3} ]** (Tổng: {total_score} - Cửa **{result_type.upper()}**)\n\n{result_txt}"
    if quest_msg: result_embed.description += f"\n\n{quest_msg}"
    await msg.edit(embed=result_embed)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    valid_choices = {"bau": "🥒", "bầu": "🥒", "cua": "🦀", "tom": "🦐", "tôm": "🦐", "ca": "🐟", "cá": "🐟", "ga": "🐓", "gà": "🐓", "huou": "🦌", "hươu": "🦌"}
    choice_clean = choice.lower()
    if choice_clean not in valid_choices: return await ctx.reply(embed=discord.Embed(description="⚠️ Các cửa: `bau, cua, tom, ca, ga, huou`.", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    user_icon = valid_choices[choice_clean]
    msg = await ctx.reply(embed=discord.Embed(title="🎲 BẦU CUA TÔM CÁ", description=f"Cược **{bet_amount:,} 💰** vào **{user_icon}**.\nNhà cái đang xóc dĩa... 🫨", color=discord.Color.gold()), mention_author=False)
    await asyncio.sleep(2.5)
    
    dice_faces = ["🥒", "🦀", "🦐", "🐟", "🐓", "🦌"]
    dice_result = [random.choice(dice_faces) for _ in range(3)]
    match_count = dice_result.count(user_icon)
    result_embed = discord.Embed(title="🎲 MỞ BÁT KẾT QUẢ")
    
    if match_count > 0: 
        win_amt = bet_amount + (bet_amount * match_count)
        user_data["money"] += win_amt; add_history(user_id, f"Bầu Cua Thắng (+{win_amt - bet_amount:,} 💰)")
        result_txt = f"🎉 **TRÚNG {match_count} Ô!** Nhận **{win_amt:,} 💰**."
        result_embed.color = discord.Color.green()
    else: 
        add_history(user_id, f"Bầu Cua Thua (-{bet_amount:,} 💰)")
        result_txt = f"💀 **TRẬT LẤT!** Mất **{bet_amount:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    quest_msg = update_quest_progress(user_id, "gamble")
    result_embed.description = f"**[ {dice_result[0]} | {dice_result[1]} | {dice_result[2]} ]**\n\n{result_txt}"
    if quest_msg: result_embed.description += f"\n\n{quest_msg}"
    await msg.edit(embed=result_embed)

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    choice = choice.lower()
    if choice not in animals: return await ctx.reply(embed=discord.Embed(description="⚠️ Chọn sai! Các cửa: `heo`, `cho`, `ngua`, `chuot`.", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    track_length = 20; positions = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def generate_track_frame():
        frame_text = f"🏇 **ĐƯỜNG ĐUA THÚ!**\nBạn cược {bet_amount:,} 💰 vào {animals[choice]}\n\n"
        for pet, distance in positions.items(): frame_text += f"🏁{'~' * min(distance, track_length)}{pet}{' ' * (track_length - min(distance, track_length))}⛩️\n"
        return frame_text

    msg = await ctx.reply(generate_track_frame(), mention_author=False)
    winner = None
    
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in positions:
            positions[pet] += random.randint(2, 6) 
            if positions[pet] >= track_length and winner is None: winner = pet
        await msg.edit(content=generate_track_frame())
        if winner: break
        
    if not winner: winner = max(positions, key=positions.get); positions[winner] = track_length; await msg.edit(content=generate_track_frame())
        
    user_data = load_user(user_id)
    if animals[choice] == winner:
        user_data["money"] += bet_amount * 3; add_history(user_id, f"Đua thú Thắng (+{bet_amount * 2:,} 💰)")
        final_text = f"\n🏆 **{winner} VỀ NHẤT!** Thắng **{bet_amount * 3:,} 💰**!"
    else:
        add_history(user_id, f"Đua thú Thua (-{bet_amount:,} 💰)")
        final_text = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} xịt. Mất **{bet_amount:,} 💰**."
        
    save_user(user_id)
    await msg.edit(content=generate_track_frame() + final_text)

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    slots_result = [random.choice(items) for _ in range(3)]
    
    embed = discord.Embed(title="🎰 MÁY XÈNG NỔ HŨ 🎰", color=discord.Color.gold())
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    for _ in range(3): embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đang quay..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    for _ in range(2): embed.description = f"**[ {slots_result[0]} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Chốt ô 1..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    for _ in range(2): embed.description = f"**[ {slots_result[0]} | {slots_result[1]} | {random.choice(items)} ]**\n\n🔄 Chốt ô cuối..."; await msg.edit(embed=embed); await asyncio.sleep(1)
        
    if slots_result[0] == slots_result[1] and slots_result[1] == slots_result[2]:
        if slots_result[0] == "👑": win_amt = bet_amount * 40
        elif slots_result[0] == "💎": win_amt = bet_amount * 15
        else: win_amt = bet_amount * 8
        result_text = f"🔥 **JACKPOT!!! ĐẠI NỔ HŨ!** 3 ô {slots_result[0]}\nHúp **{win_amt:,} 💰**!"
        user_data["money"] += win_amt; add_history(user_id, f"Nổ Hũ (+{win_amt:,} 💰)")
    elif slots_result[0] == slots_result[1] or slots_result[1] == slots_result[2] or slots_result[0] == slots_result[2]:
        win_amt = int(bet_amount * 1.5)
        result_text = f"🎉 **THẮNG NHỎ!** 2 ô giống nhau. Nhận **{win_amt:,} 💰**."
        user_data["money"] += win_amt; add_history(user_id, f"Máy Xèng Thắng nhỏ (+{win_amt - bet_amount:,} 💰)")
    else:
        result_text = f"💀 **TOANG!** Mất **{bet_amount:,} 💰**."
        add_history(user_id, f"Máy Xèng Thua (-{bet_amount:,} 💰)")
        
    save_user(user_id)
    quest_msg = update_quest_progress(user_id, "gamble")
    embed.description = f"**[ {slots_result[0]} | {slots_result[1]} | {slots_result[2]} ]**\n\n{result_text}"
    if quest_msg: embed.description += f"\n\n{quest_msg}"
    embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰")
    await msg.edit(embed=embed)

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    if user_id in gacha_cooldowns:
        diff = (now - gacha_cooldowns[user_id]).total_seconds()
        if diff < 300:
            return await ctx.reply(embed=discord.Embed(
                description=f"⏳ Trứng gacha cần ủ thêm **{int((300 - diff) / 60)}p {int((300 - diff) % 60)}s** nữa!", 
                color=discord.Color.orange()
            ), mention_author=False)
    
    user_data = load_user(user_id)
    cost = 50000
    if user_data.get("money", 0) < cost:
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ Trứng Gacha giá **{cost:,} 💰**. Đi cày thêm!", color=discord.Color.red()), mention_author=False)
        
    user_data["money"] -= cost
    gacha_cooldowns[user_id] = now
    save_user(user_id)
    
    msg = await ctx.reply(embed=discord.Embed(title="🥚 ĐẬP TRỨNG GACHA", description=f"{ctx.author.mention} đang đập trứng...", color=discord.Color.orange()), mention_author=False)
    await asyncio.sleep(1.5)
    
    roll = random.uniform(0, 100)
    if roll <= 0.5: rarity, title_text, embed_color = "mythic", "🌌 THẦN THOẠI", discord.Color.dark_purple()
    elif roll <= 3.0: rarity, title_text, embed_color = "legendary", "👑 HUYỀN THOẠI", discord.Color.gold()
    elif roll <= 10.0: rarity, title_text, embed_color = "epic", "🔮 SỬ THI", discord.Color.magenta()
    elif roll <= 30.0: rarity, title_text, embed_color = "rare", "💎 HIẾM", discord.Color.blue()
    else: rarity, title_text, embed_color = "common", "🪵 PHỔ THÔNG", discord.Color.light_grey()
    
    pet_name = random.choice(PET_RATES[rarity]["pool"])
    user_data["pets"][pet_name] = user_data["pets"].get(pet_name, 0) + 1
    save_user(user_id); add_history(user_id, f"Quay Gacha ra {pet_name} (-{cost:,} 💰)")
    
    quest_msg = update_quest_progress(user_id, "gacha")
    new_achievements = check_achievement(user_id, user_data)
    
    result_text = f"Bạn nhận được: **{pet_name}**!\n⏳ Cooldown: 5 phút"
    if quest_msg: result_text += f"\n\n{quest_msg}"
    if new_achievements:
        save_user(user_id)
        result_text += f"\n🏅 **THÀNH TÍCH MỚI:** " + ", ".join(new_achievements)
    
    embed_result = discord.Embed(title=f"🎉 PHẨM CHẤT {title_text}!", description=result_text, color=embed_color)
    await msg.edit(embed=embed_result)

# =====================================================================
# GAME MA SÓI
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['werewolf'])
async def masoi(ctx):
    embed = discord.Embed(title="🐺 MA SÓI LÀNG LÁCH (Bản 1 Đêm)", description="`k masoi tao`: Tạo phòng\n`k masoi join`: Tham gia\n`k masoi start`: Bắt đầu game", color=discord.Color.dark_theme())
    await ctx.send(embed=embed)

@masoi.command()
async def tao(ctx):
    server_id = str(ctx.guild.id)
    if server_id in werewolf_lobbies: return await ctx.send("Server này đang có một phòng Ma Sói rồi!")
    werewolf_lobbies[server_id] = {"host": ctx.author, "players": [ctx.author], "roles": {}, "votes": {}, "status": "waiting"}
    await ctx.send(f"🐺 {ctx.author.mention} đã tạo phòng Ma Sói! Gõ `k masoi join` để tham gia.")

@masoi.command()
async def join(ctx):
    server_id = str(ctx.guild.id)
    if server_id not in werewolf_lobbies: return await ctx.send("Chưa có phòng. Gõ `k masoi tao` trước.")
    lobby = werewolf_lobbies[server_id]
    if lobby["status"] != "waiting": return await ctx.send("Ván đấu đã bắt đầu rồi!")
    if ctx.author in lobby["players"]: return await ctx.send("Bạn đã ở trong phòng rồi!")
    lobby["players"].append(ctx.author)
    await ctx.send(f"✅ {ctx.author.mention} đã tham gia! (Hiện có {len(lobby['players'])} người)")

@masoi.command()
async def start(ctx):
    server_id = str(ctx.guild.id)
    if server_id not in werewolf_lobbies: return
    lobby = werewolf_lobbies[server_id]
    if ctx.author != lobby["host"]: return await ctx.send("Chỉ chủ phòng mới được bắt đầu!")
    players = lobby["players"]
    if len(players) < 3: return await ctx.send("Cần ít nhất 3 người!")
    
    lobby["status"] = "playing"; random.shuffle(players)
    wolf = players[0]; seer = players[1]
    lobby["roles"][str(wolf.id)] = "Wolf"; lobby["roles"][str(seer.id)] = "Seer"
    for p in players[2:]: lobby["roles"][str(p.id)] = "Villager"
    
    await ctx.send("🌙 **ĐÊM BUÔNG XUỐNG LÀNG LÁCH...**\nBot đang gửi tin nhắn bí mật!")
    try:
        await wolf.send("🐺 **Bạn là MA SÓI!** Hãy không bị treo cổ vào ngày mai!")
        target = random.choice([p for p in players if p != seer])
        is_wolf = "LÀ SÓI" if target == wolf else "LÀ DÂN"
        await seer.send(f"🔮 **Bạn là TIÊN TRI!** Bạn thấy: **{target.name} {is_wolf}**!")
        for p in players[2:]: await p.send("🧑 **Bạn là DÂN LÀNG!** Hãy tìm ra Sói vào sáng mai!")
    except Exception:
        del werewolf_lobbies[server_id]; return await ctx.send("Lỗi: Không thể DM cho người chơi. Đã hủy phòng!")
        
    await asyncio.sleep(10)
    await ctx.send("☀️ **TRỜI ĐÃ SÁNG!**\n⏰ Có 60 giây để vote treo cổ 1 người!")
    view = MaSoiVoteView(lobby)
    await ctx.send("👇 **BẢNG VOTE HÀNH QUYẾT**", view=view)
    await asyncio.sleep(60)
    
    votes = lobby["votes"]
    if not votes: await ctx.send("Kết quả: Không ai bị treo cổ. 🐺 SÓI CHIẾN THẮNG!")
    else:
        vote_counts = {}
        for target_id in votes.values(): vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        max_votes = max(vote_counts.values())
        hanged_ids = [k for k, v in vote_counts.items() if v == max_votes]
        
        if len(hanged_ids) > 1: await ctx.send("Kết quả: Bầu phiếu hòa! 🐺 SÓI CHIẾN THẮNG!")
        else:
            hanged_id = hanged_ids[0]
            if hanged_id == str(wolf.id): await ctx.send(f"💀 Đã treo cổ <@{hanged_id}>.\n🎉 Hắn là **MA SÓI**! **DÂN LÀNG CHIẾN THẮNG!**")
            else: await ctx.send(f"💀 Đã treo cổ <@{hanged_id}>.\n❌ Hắn là Dân Thường! 🐺 Sói {wolf.mention} thắng. **SÓI CHIẾN THẮNG!**")
    if server_id in werewolf_lobbies: del werewolf_lobbies[server_id]

# =====================================================================
# LỆNH QUYẾT ĐẤU 1 vs 1
# =====================================================================
@bot.command(aliases=['challenge', 'vs'])
async def duel(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Không thể thách đấu bot hoặc chính mình!", color=discord.Color.red()), mention_author=False)
    
    if amount <= 0 or amount > 300000:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Cược từ 1 đến 300,000 💰!", color=discord.Color.red()), mention_author=False)
    
    author_data = load_user(ctx.author.id)
    if author_data.get("money", 0) < amount:
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ Bạn chỉ có **{author_data['money']:,} 💰**!", color=discord.Color.red()), mention_author=False)
    
    embed = discord.Embed(title="⚔️ LỜI THÁCH ĐẤU", description=f"{ctx.author.mention} thách đấu {member.mention}!\n\n💰 Tiền cược mỗi bên: **{amount:,} 💰**\n\n{member.mention} hãy chấp nhận hoặc từ chối!", color=discord.Color.red())
    embed.set_image(url=GIF_LINKS["duel"])
    
    view = DuelAccept(ctx.author, member, amount)
    await ctx.send(embed=embed, view=view)

# =====================================================================
# CÁC LỆNH INFO, HELP, TOP VÀ GIAO DỊCH
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH BOT SIÊU VIP 7.1 (PATCHED)", description="Tiền tố: `k` hoặc `K` (Ví dụ: `k rank`)", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    
    embed.add_field(name="🏦 KINH TẾ", value="`k rank` `k bank` `k marry @user`\n`k cuahang` `k choden` `k daily` `k lixi`\n`k give @user <tiền>` `k top` `k ls`\n`k dilamthem` (CD: 45p) | `k nhiemvu`", inline=False)
    embed.add_field(name="🎣 SINH HOẠT", value="`k cauca` (CD: 25s - cần cần câu)\n`k daovang` (CD: 60s)\n`k farm` (Nông trại)\n`k phai` `k thamhiem`", inline=False)
    embed.add_field(name="🏢 DOANH NGHIỆP", value="`k cty tao <tên>` `k cty` (Dashboard)\n`k daichien @user <hack/phot/giangho>`\n`k ck` (CK: spread 3%, thuế 5%, CD 10p)", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 300K, CD 6s)", value="`k coin` `k taixiu <tai/xiu>` `k baucua`\n`k nohu` `k vietlott <số>` `k duathu`", inline=False)
    embed.add_field(name="⚔️ PK & GAME", value="`k pk @user <tiền>` (Oẳn Tù Tì)\n`k duel @user <tiền>` (Quyết Đấu RPG)\n`k masoi` (Game Ma Sói)\n`k nhansinh` (Mô phỏng cuộc sống)\n`k gacha` (CD: 5p, giá 50k)\n`k cuopnganhang` (CD: 2h)", inline=False)
    embed.add_field(name="📊 THỐNG KÊ", value="`k thanhtich` | `k tuido`", inline=False)
    embed.set_footer(text="v7.1 Patched", icon_url=ctx.author.display_avatar.url)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def rank(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_data = load_user(target.id)
    level = user_data.get("level", 1); xp = user_data.get("xp", 0); tien = user_data.get("money", 0)
    total_wealth = tien + user_data.get("bank", 0)
    
    embed_color = discord.Color.gold() if total_wealth > 1000000 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 CĂN CƯỚC: {target.name.upper()}", color=embed_color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {level}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    embed.add_field(name="💎 Tổng Tài Sản", value=f"**{total_wealth:,} 💰**", inline=True)
    embed.add_field(name="🔥 Chuỗi điểm danh", value=f"**{user_data.get('streak', 0)} ngày**", inline=True)
    embed.add_field(name="🐾 Thú cưng", value=f"**{len(user_data.get('pets', {}))} loại**", inline=True)
    
    if user_data.get("spouse"):
        try: spouse_name = (await bot.fetch_user(int(user_data["spouse"]))).name
        except Exception: spouse_name = "Người thương ẩn danh"
        embed.add_field(name="💍 Hôn nhân", value=f"**Đã kết hôn với {spouse_name}**", inline=False)
        
    if user_data.get("company"): 
        comp_info = load_company(user_data['company'])
        if comp_info: embed.add_field(name="🏢 Doanh Nghiệp", value=f"**{comp_info['name']}**{' 📈' if comp_info.get('is_ipo') else ''}", inline=False)
            
    if user_data.get("jail_time"): embed.add_field(name="🚨 Trạng Thái", value="**Đang bóc lịch trong tù!**", inline=False)
    
    achievements = user_data.get("achievements", [])
    if achievements: embed.add_field(name="🏅 Thành tích", value=f"**{len(achievements)} huy hiệu**", inline=True)
    
    embed.add_field(name="✨ Kinh Nghiệm", value=f"`{make_progress_bar(xp, level * 100)}`\n**{xp}/{level * 100} XP**", inline=False)
    assets = user_data.get('assets', [])
    embed.set_footer(text=f"Tài sản: {', '.join(assets[:2])}..." if assets else "Gia cảnh: Vô Gia Cư", icon_url=target.display_avatar.url)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def tuido(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_data = load_user(target.id)
    embed = discord.Embed(title=f"🎒 KHO BÁU CỦA {target.name.upper()}", color=discord.Color.dark_purple())
    embed.set_thumbnail(url=target.display_avatar.url)
    assets = user_data.get("assets", [])
    embed.add_field(name="🏠 Tài Sản Cá Nhân", value="Trống." if not assets else "\n".join([f"🔸 {a}" for a in assets]), inline=False)
    pets = user_data.get("pets", {})
    embed.add_field(name="🐾 Trang Trại Thú Cưng", value="Chưa bắt được con nào." if not pets else "\n".join([f"{p} (x{c})" for p, c in pets.items()]), inline=False)
    stocks = user_data.get("stocks", {})
    if stocks:
        stock_lines = []
        for code, qty in stocks.items():
            current_price = get_stock_sell_price(code)
            avg_buy = user_data.get("stock_buy_prices", {}).get(code, current_price)
            pnl = (current_price - avg_buy) * qty
            pnl_icon = "📈" if pnl >= 0 else "📉"
            stock_lines.append(f"{pnl_icon} **{code}**: {qty} CP | Giá bán: {current_price:,} | P&L: {pnl:+,} 💰")
        embed.add_field(name="📈 Danh Mục Cổ Phiếu", value="\n".join(stock_lines), inline=False)
    embed.add_field(name="🎣 Tổng Cá Câu Được", value=f"**{user_data.get('fish_count', 0)} con**", inline=True)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx, category: str = "tien"):
    try:
        all_users = list(users_col.find())
    except Exception as e:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Lỗi kết nối database, thử lại sau!", color=discord.Color.red()), mention_author=False)
    
    if category.lower() in ["level", "cap"]:
        danh_sach = sorted([(doc["_id"], doc.get("level", 1), doc.get("xp", 0)) for doc in all_users], key=lambda x: (x[1], x[2]), reverse=True)
        title = "🌟 TOP CẤP ĐỘ CAO NHẤT"
        def fmt(idx, uid, *args): return f"Lv{args[0]} ({args[1]} XP)"
    elif category.lower() in ["ca", "fish"]:
        danh_sach = sorted([(doc["_id"], doc.get("fish_count", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
        title = "🎣 TOP NGƯ DÂN"
        def fmt(idx, uid, *args): return f"{args[0]} con cá"
    else:
        danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
        title = "🏆 BẢNG VÀNG ĐẠI GIA SERVER"
        def fmt(idx, uid, *args): return f"{args[0]:,} 💰"
    
    desc = ""
    for index, data in enumerate(danh_sach[:10]):
        uid = data[0]; rest = data[1:]
        user = bot.get_user(int(uid))
        try: 
            if not user: user = await bot.fetch_user(int(uid))
        except Exception: pass
        ten = user.name if user else f"Ẩn Danh #{uid[-4:]}"
        icon = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else f"**#{index+1}**"
        desc += f"{icon} **{ten}** ━ {fmt(index, uid, *rest)}\n\n"
    
    embed = discord.Embed(title=title, description=desc, color=discord.Color.gold())
    embed.set_footer(text="k top | k top level | k top ca")
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_daily"):
        try:
            last_daily = datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            last_daily = datetime(2000, 1, 1)
        if now - last_daily < timedelta(days=1):
            next_time = int((last_daily + timedelta(days=1)).timestamp())
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Lương tiếp theo: <t:{next_time}:R>.", color=discord.Color.orange()), mention_author=False)
        if now - last_daily < timedelta(days=2):
            user_data["streak"] = user_data.get("streak", 0) + 1
        else:
            user_data["streak"] = 1
    else:
        user_data["streak"] = 1
    
    streak = user_data.get("streak", 1)
    base = 500
    streak_bonus = min(streak * 50, 2500)
    total = base + streak_bonus
    
    user_data["money"] += total
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    new_achievements = check_achievement(user_id, user_data)
    save_user(user_id)
    
    embed_success = discord.Embed(title="🎁 QUÀ ĐIỂM DANH", description=f"Nhận **{total:,} 💰** thành công!\n🔥 Chuỗi điểm danh: **{streak} ngày** (+{streak_bonus:,} bonus)\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.green())
    if new_achievements:
        embed_success.description += f"\n\n🏅 **THÀNH TÍCH MỚI:** " + ", ".join(new_achievements)
    embed_success.set_thumbnail(url=GIF_LINKS["daily"])
    await ctx.reply(embed=embed_success, mention_author=False)

@bot.command()
async def lixi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_lixi"):
        try:
            last_lixi = datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            last_lixi = datetime(2000, 1, 1)
        if now - last_lixi < timedelta(hours=12):
            next_time = int((last_lixi + timedelta(hours=12)).timestamp())
            return await ctx.reply(embed=discord.Embed(description=f"🧧 Lì xì tiếp theo: <t:{next_time}:R>.", color=discord.Color.orange()), mention_author=False)

    tien = random.randint(500, 5000)
    user_data["money"] += tien; user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"🧧 Mở phong bao đỏ nhận được **{tien:,} 💰**!\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.red()), mention_author=False)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    nguoi_gui = str(ctx.author.id); nguoi_nhan = str(member.id); gui_data = load_user(nguoi_gui); nhan_data = load_user(nguoi_nhan)
    if amount <= 0 or gui_data.get("money", 0) < amount or nguoi_gui == nguoi_nhan: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển).", color=discord.Color.red()), mention_author=False)
    gui_data["money"] -= amount; nhan_data["money"] += amount
    save_user(nguoi_gui); save_user(nguoi_nhan)
    add_history(nguoi_gui, f"Chuyển cho {member.name} (-{amount:,} 💰)")
    add_history(nguoi_nhan, f"Nhận từ {ctx.author.name} (+{amount:,} 💰)")
    
    quest_msg = update_quest_progress(nguoi_gui, "give")
    
    embed = discord.Embed(title="💸 CHUYỂN KHOẢN THÀNH CÔNG", description=f"{ctx.author.mention} đã chuyển cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green())
    if quest_msg: embed.description += f"\n\n{quest_msg}"
    await ctx.send(embed=embed)

@bot.command(aliases=['ban', 'sell'])
async def choden(ctx): 
    embed = discord.Embed(title="⚖️ CHỢ ĐEN CẦM ĐỒ", description="Đem đồ ra đây cầm cố hoặc bán thú cưng lấy tiền liền tay!", color=discord.Color.dark_orange())
    await ctx.send(embed=embed, view=SellCategoryMenu(ctx.author))

@bot.command(aliases=['shop'])
async def cuahang(ctx): 
    embed = discord.Embed(title="🏪 ĐẠI SIÊU THỊ TRUNG TÂM", description="Nơi tiêu tiền của những kẻ giàu có!", color=discord.Color.brand_green())
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command()
async def thamhiem(ctx): 
    embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ RỪNG SÂU", description="Khu rừng rậm rạp đầy nguy hiểm nhưng cũng đầy kho báu.\n\nGõ `k phai` để chọn địa điểm cắm trại!", color=discord.Color.orange())
    await ctx.send(embed=embed)

@bot.command()
async def phai(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); exp_end_str = user_data.get("exp_end")
    if exp_end_str:
        try:
            now = datetime.now(); end_time = datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            del user_data["exp_end"]
            if "exp_reward" in user_data: del user_data["exp_reward"]
            save_user(user_id)
            end_time = datetime.now()  # force reset
        if datetime.now() >= end_time:
            reward = user_data.get("exp_reward", 500); user_data["money"] += reward
            user_data.pop("exp_end", None); user_data.pop("exp_reward", None); save_user(user_id)
            return await ctx.reply(embed=discord.Embed(title="🎉 TRỞ VỀ AN TOÀN!", description=f"Hoàn thành chuyến dã ngoại! Thu hoạch **{reward:,} 💰**!", color=discord.Color.gold()), mention_author=False)
        else:
            time_left = end_time - datetime.now(); hours, remainder = divmod(int(time_left.total_seconds()), 3600); minutes, seconds = divmod(remainder, 60)
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Đang cày cuốc nơi hoang dã! Chờ thêm **{hours}h {minutes}m**.", color=discord.Color.orange()), mention_author=False)
    embed_start = discord.Embed(title="⛺ THÁM HIỂM AFK", description="Gửi nhân vật đi treo máy nhặt tiền!\n\n👇 **MỞ MENU CHỌN KHU VỰC CẮM TRẠI** 👇", color=discord.Color.dark_green())
    await ctx.send(embed=embed_start, view=ExpView(ctx.author))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id); now = datetime.now()
    if user_id in dang_choi_nhansinh: return await ctx.reply(embed=discord.Embed(description="⏳ Đang trong một kiếp luân hồi dở dang!", color=discord.Color.orange()), mention_author=False)
    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5: return await ctx.reply(embed=discord.Embed(description="⏳ Từ từ đã, đầu thai liên tục Diêm Vương mắng!", color=discord.Color.orange()), mention_author=False)
    user_data = load_user(user_id)
    if user_data.get("money", 0) < 500: return await ctx.reply(embed=discord.Embed(description="⚠️ Vé luân hồi giá **500 💰**.", color=discord.Color.red()), mention_author=False)

    user_data["money"] -= 500; nhansinh_cooldowns[user_id] = now; dang_choi_nhansinh.append(user_id); save_user(user_id)
    initial_stats = {"may_man": random.randint(1, 10)}; view = NhanSinhGameView(ctx.author, initial_stats)
    
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH (HARDCORE)", description=f"Ký chủ luân hồi: {ctx.author.mention}", color=discord.Color.teal())
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn: **{initial_stats['may_man']}/10** *(+{initial_stats['may_man']*1.5}% Tỉ lệ)*", inline=False)
    embed.add_field(name="📜 Hành trình cuộc đời", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Ngã rẽ tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    await ctx.reply(embed=embed, view=view, mention_author=False)

@bot.command(aliases=['ott'])
async def pk(ctx, member: discord.Member, amount: str):
    if member.bot or member.id == ctx.author.id: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Không thể thách đấu bot hoặc chính mình!", color=discord.Color.red()), mention_author=False)
    
    user_data = load_user(ctx.author.id)
    try:
        if amount.lower() == "all": bet = min(user_data.get("money", 0), 300000)
        else: bet = int(amount)
    except ValueError:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập số tiền hoặc `all`!", color=discord.Color.red()), mention_author=False)
    
    if bet <= 0 or bet > user_data.get("money", 0):
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ Không đủ tiền! Bạn có **{user_data['money']:,} 💰**.", color=discord.Color.red()), mention_author=False)
    if bet > 300000:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Tối đa **300,000 💰** mỗi ván!", color=discord.Color.red()), mention_author=False)
    
    embed = discord.Embed(title="⚔️ GẠ KÈO OẲN TÙ TÌ", description=f"{ctx.author.mention} thách {member.mention} chơi **Oẳn Tù Tì**!\nTiền cược: **{bet:,} 💰** mỗi bên.", color=discord.Color.red())
    view = SoloOTTAccept(ctx.author, member, bet)
    await ctx.send(f"{member.mention}", embed=embed, view=view)

@bot.command()
async def marry(ctx, member: discord.Member):
    if member.bot or member.id == ctx.author.id:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Không thể cầu hôn bot hoặc chính mình!", color=discord.Color.red()), mention_author=False)
    
    sender_data = load_user(ctx.author.id)
    if sender_data.get("spouse"):
        return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn đã kết hôn rồi! Phải ly hôn trước.", color=discord.Color.red()), mention_author=False)
    
    receiver_data = load_user(member.id)
    if receiver_data.get("spouse"):
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ {member.name} đã có người yêu rồi!", color=discord.Color.red()), mention_author=False)
    
    if sender_data.get("money", 0) < 1000000:
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ Lễ cưới cần **1,000,000 💰**. Bạn chỉ có **{sender_data['money']:,} 💰**.", color=discord.Color.red()), mention_author=False)
    
    embed = discord.Embed(title="💍 LỜI CẦU HÔN", description=f"💕 {ctx.author.mention} đang quỳ xuống và cầu hôn {member.mention}!\n\n💒 Lễ cưới trị giá **1,000,000 💰** sẽ được tổ chức nếu đồng ý!", color=discord.Color.pink())
    embed.set_image(url=GIF_LINKS["marry"])
    view = MarryAccept(ctx.author, member)
    await ctx.send(f"{member.mention}", embed=embed, view=view)

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
# KHỞI ĐỘNG
# =====================================================================
keep_alive() 

TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
