import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 

# =====================================================================
# THIẾT LẬP CƠ BẢN CỦA BOT SIÊU VIP 4.0
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
# Xóa lệnh help mặc định của Discord để dùng lệnh help custom siêu đẹp
bot.remove_command('help')

# =====================================================================
# KHO ẢNH GIF ĐỘNG SIÊU VIP 
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
    "bankrupt": "https://media.giphy.com/media/3o6UB5RrlQuMfZp82Y/giphy.gif"
}

# =====================================================================
# QUẢN LÝ TRẠNG THÁI (COOLDOWN & BỘ ĐẾM)
# =====================================================================
gamble_cooldowns = {} 
nhansinh_cooldowns = {} 
dang_choi_nhansinh = [] 
cty_cooldowns = {}
work_cooldowns = {} 
vietlott_players = {}

# =====================================================================
# KẾT NỐI MONGODB VÀ HỆ THỐNG BỘ ĐỆM (CACHE)
# =====================================================================
# Sếp nhớ giữ nguyên chuỗi URI này của sếp nhé
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]

users_col = db["users"]   
config_col = db["config"] 
companies_col = db["companies"]

# Khởi tạo Cache để giảm tải cho DB, chống giật lag khi nhiều người chơi
DB_CACHE = {}
CONFIG_CACHE = {}
COMPANY_CACHE = {}

def load_user(user_id):
    """
    Tải dữ liệu người dùng từ Database. 
    Nếu người dùng chưa tồn tại, tự động khởi tạo mặc định đầy đủ.
    """
    user_id = str(user_id)
    
    if user_id not in DB_CACHE:
        document = users_col.find_one({"_id": user_id})
        if document:
            DB_CACHE[user_id] = document
        else:
            DB_CACHE[user_id] = {}
            
    # Bộ khung dữ liệu chuẩn của người chơi (Thêm is_ipo cho Cổ phiếu)
    defaults = {
        "xp": 0, 
        "level": 1, 
        "money": 0, 
        "bank": 0,
        "title": "Dân Đáy Xã Hội 🧱", 
        "assets": [], 
        "pets": {}, 
        "company": None, 
        "stocks": {}, 
        "jail_time": None,
        "spouse": None
    }
    
    for key, value in defaults.items():
        if key not in DB_CACHE[user_id]: 
            DB_CACHE[user_id][key] = value
            
    return DB_CACHE[user_id]

def save_user(user_id):
    """Lưu dữ liệu người dùng từ Cache lên Database"""
    user_id = str(user_id)
    if user_id in DB_CACHE: 
        users_col.update_one(
            {"_id": user_id}, 
            {"$set": DB_CACHE[user_id]}, 
            upsert=True
        )

def load_server_config(server_id):
    """Tải cấu hình của Server (Chặn kênh...)"""
    server_id = str(server_id)
    
    if server_id not in CONFIG_CACHE:
        document = config_col.find_one({"_id": server_id})
        if document:
            CONFIG_CACHE[server_id] = document
        else:
            CONFIG_CACHE[server_id] = {}
            
    return CONFIG_CACHE[server_id]

def load_company(company_id):
    """Tải dữ liệu Công ty / Bang hội của người chơi"""
    company_id = str(company_id)
    
    if company_id not in COMPANY_CACHE:
        document = companies_col.find_one({"_id": company_id})
        if document: 
            COMPANY_CACHE[company_id] = document
        else: 
            return None
            
    return COMPANY_CACHE[company_id]

def save_company(company_id):
    """Đẩy dữ liệu Công ty từ RAM lên Database"""
    company_id = str(company_id)
    if company_id in COMPANY_CACHE: 
        companies_col.update_one(
            {"_id": company_id}, 
            {"$set": COMPANY_CACHE[company_id]}, 
            upsert=True
        )

# =====================================================================
# HÀM KIỂM TRA TỔNG THỂ (GLOBAL CHECKS)
# =====================================================================
@bot.check
async def global_jail_and_channel_check(ctx):
    """Chặn lệnh nếu đi tù hoặc sai kênh"""
    if ctx.author.guild_permissions.administrator or ctx.command.name == "help": 
        return True
        
    user_data = load_user(ctx.author.id)
    jail_time_str = user_data.get("jail_time")
    
    if jail_time_str:
        jail_end = datetime.strptime(jail_time_str, "%Y-%m-%d %H:%M:%S")
        
        if datetime.now() < jail_end:
            embed = discord.Embed(
                title="🚨 BÁO ĐỘNG ĐỎ!", 
                description=f"{ctx.author.mention} đang bóc lịch trong trại giam do vi phạm pháp luật!\n\n"
                            f"⏳ Thời gian mãn hạn tù: <t:{int(jail_end.timestamp())}:R>\n\n"
                            f"Hãy tự vấn lương tâm trong phòng biệt giam rồi quay lại sau khi mãn hạn nhé!", 
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=GIF_LINKS["jail"])
            await ctx.reply(embed=embed, mention_author=False)
            return False
        else:
            user_data["jail_time"] = None
            save_user(ctx.author.id)
            
    if ctx.guild:
        server_config = load_server_config(ctx.guild.id)
        allowed_channels = server_config.get("allowed_channels", [])
        
        if allowed_channels and ctx.channel.id not in allowed_channels: 
            return False
            
    return True

def make_progress_bar(current_value, total_value, bar_length=12):
    progress_blocks = int((current_value / total_value) * bar_length)
    empty_blocks = bar_length - progress_blocks
    return "🟩" * progress_blocks + "⬛" * empty_blocks

async def check_gamble_conditions(ctx, amount_str):
    """Xác thực điều kiện cờ bạc khắt khe"""
    user_id = str(ctx.author.id)
    current_time = datetime.now()
    
    if user_id in gamble_cooldowns:
        time_difference = (current_time - gamble_cooldowns[user_id]).total_seconds()
        if time_difference < 4:
            time_left = int(4 - time_difference)
            embed_cooldown = discord.Embed(
                description=f"⏳ Tay mỏi rồi! Đợi {time_left}s nữa hẵng lắc tiếp sếp ơi!", 
                color=discord.Color.orange()
            )
            await ctx.reply(embed=embed_cooldown, mention_author=False)
            return None, None
            
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) <= 0:
        embed_bankrupt = discord.Embed(
            description="💸 Kẻ tổn thương lại muốn tổn thương sòng bạc à? Tiền trong ví không có một xu mà đòi cá cược!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
        return None, None
        
    try: 
        if amount_str.lower() == "all":
            bet_amount = user_data["money"] if user_data["money"] <= 500000 else 500000
        else:
            bet_amount = int(amount_str)
    except ValueError: 
        embed_error = discord.Embed(
            description="⚠️ Nhập số tiền sai định dạng rồi! Vui lòng nhập số hoặc chữ `all`.", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_error, mention_author=False)
        return None, None
        
    if bet_amount <= 0 or bet_amount > user_data["money"]: 
        embed_poor = discord.Embed(
            description=f"⚠️ Bốc phét à? Sếp chỉ có **{user_data['money']:,} 💰** trong ví thôi!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_poor, mention_author=False)
        return None, None
        
    if bet_amount > 500000: 
        embed_max_bet = discord.Embed(
            description="🛑 Nhà cái quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_max_bet, mention_author=False)
        return None, None
        
    return user_data, bet_amount

# =====================================================================
# DATA CỬA HÀNG ĐẠI GIA VÀ CHỢ ĐEN (BUNG LỤA HOÀN TOÀN)
# =====================================================================
SHOP_ITEMS = {
    "title_1": {
        "type": "title", 
        "name": "Kẻ Lưu Đày 🛖", 
        "price": 10000, 
        "emoji": "🏷️"
    },
    "title_2": {
        "type": "title", 
        "name": "Tiểu Thương 🏪", 
        "price": 50000, 
        "emoji": "🏷️"
    },
    "title_3": {
        "type": "title", 
        "name": "Phú Nông 🌾", 
        "price": 200000, 
        "emoji": "🏷️"
    },
    "title_4": {
        "type": "title", 
        "name": "Đại Gia 💸", 
        "price": 1000000, 
        "emoji": "🏷️"
    },
    "title_5": {
        "type": "title", 
        "name": "Tỷ Phú 💎", 
        "price": 5000000, 
        "emoji": "🏷️"
    },
    "title_6": {
        "type": "title", 
        "name": "Thần Tài 🧧", 
        "price": 20000000, 
        "emoji": "🏷️"
    },
    "title_7": {
        "type": "title", 
        "name": "Kẻ Thống Trị Vũ Trụ 🌌", 
        "price": 100000000, 
        "emoji": "👑"
    },
    "vehicle_1": {
        "type": "vehicle", 
        "name": "Xe Đạp Địa Hình 🚲", 
        "price": 15000, 
        "emoji": "🚲"
    },
    "vehicle_2": {
        "type": "vehicle", 
        "name": "Honda SH 150i 🏍️", 
        "price": 300000, 
        "emoji": "🏍️"
    },
    "vehicle_3": {
        "type": "vehicle", 
        "name": "Toyota Camry 🚗", 
        "price": 2000000, 
        "emoji": "🚗"
    },
    "vehicle_4": {
        "type": "vehicle", 
        "name": "Mercedes G63 🚙", 
        "price": 8000000, 
        "emoji": "🚙"
    },
    "vehicle_5": {
        "type": "vehicle", 
        "name": "Lamborghini Aventador 🏎️", 
        "price": 25000000, 
        "emoji": "🏎️"
    },
    "vehicle_6": {
        "type": "vehicle", 
        "name": "Du Thuyền Hạng Sang 🛥️", 
        "price": 150000000, 
        "emoji": "🛥️"
    },
    "vehicle_7": {
        "type": "vehicle", 
        "name": "Trạm Không Gian UFO 🛸", 
        "price": 900000000, 
        "emoji": "🛸"
    },
    "house_1": {
        "type": "house", 
        "name": "Nhà Trọ Ẩm Thấp ⛺", 
        "price": 50000, 
        "emoji": "⛺"
    },
    "house_2": {
        "type": "house", 
        "name": "Chung Cư Mini 🏢", 
        "price": 500000, 
        "emoji": "🏢"
    },
    "house_3": {
        "type": "house", 
        "name": "Nhà Phố 3 Tầng 🏘️", 
        "price": 5000000, 
        "emoji": "🏘️"
    },
    "house_4": {
        "type": "house", 
        "name": "Biệt Thự Hồ Tây 🏡", 
        "price": 30000000, 
        "emoji": "🏡"
    },
    "house_5": {
        "type": "house", 
        "name": "Lâu Đài Cổ Tích 🏰", 
        "price": 150000000, 
        "emoji": "🏰"
    },
    "house_6": {
        "type": "house", 
        "name": "Đảo Tư Nhân Maldives 🏝️", 
        "price": 600000000, 
        "emoji": "🏝️"
    },
    "house_7": {
        "type": "house", 
        "name": "Hành Tinh Namek 🪐", 
        "price": 2000000000, 
        "emoji": "🪐"
    }
}

def get_asset_price(asset_name):
    """Bán lại lỗ 30%"""
    for item_key, item_data in SHOP_ITEMS.items():
        if item_data["name"] == asset_name: 
            return int(item_data["price"] * 0.7)
    return 1000

# =====================================================================
# DATA GACHA THÚ CƯNG
# =====================================================================
PET_RATES = {
    "common": {
        "rate": 70.0, 
        "pool": ["Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", "Lợn Đất 🐖", "Cáo Nhỏ 🦊", "Chuột Đồng 🐁"]
    },
    "rare": {
        "rate": 20.0, 
        "pool": ["Sói Tuyết 🐺", "Gấu Xám 🐻", "Đại Bàng 🦅", "Báo Gấm 🐆"]
    },
    "epic": {
        "rate": 7.0, 
        "pool": ["Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍", "Bạch Hổ 🐅", "Tê Giác Thiết Giáp 🦏"]
    },
    "legendary": {
        "rate": 2.5, 
        "pool": ["Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", "Phượng Hoàng Lửa 🦚", "Thủy Quái Leviathan 🐙"]
    },
    "mythic": {
        "rate": 0.5, 
        "pool": ["Thần Long Hoàng Kim 🐲", "Hắc Ám Cự Thú 🦇", "Mèo Thần Tài Siêu Cấp 😻", "Godzilla Vĩ Đại 🦖"]
    }
}

def get_pet_sell_price(pet_name):
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 5000      
            if rarity == "rare": return 20000       
            if rarity == "epic": return 150000      
            if rarity == "legendary": return 800000 
            if rarity == "mythic": return 10000000   
    return 1000

# =====================================================================
# HỆ THỐNG SÀN CHỨNG KHOÁN (CÓ HỦY NIÊM YẾT & IPO CÔNG TY)
# =====================================================================
STANDARD_STOCKS = {
    "VIN": "Tập Đoàn VIN", 
    "FLC": "Hàng Không FLC", 
    "VNZ": "Công Nghệ VNZ", 
    "DOGE": "Doge Coin", 
    "BTC": "Bitcoin", 
    "AAPL": "Apple Inc.", 
    "TSLA": "Tesla"
}

def get_all_stocks():
    """Lấy danh sách mã CK: Gồm Mặc định + Công ty người chơi đã IPO"""
    all_stocks = STANDARD_STOCKS.copy()
    
    # Tìm các công ty đã IPO (Lên sàn)
    ipo_companies = companies_col.find({"is_ipo": True})
    for comp in ipo_companies:
        # Lấy 4 chữ cái đầu của tên công ty làm mã CK
        code = comp["name"][:4].upper()
        all_stocks[code] = comp["name"]
        
    return all_stocks

def get_stock_price(stock_code, hour_offset=0):
    """
    Tính giá cổ phiếu. Có tỉ lệ PHÁ SẢN (Hủy niêm yết) rơi về 1000 VNĐ.
    Nếu là công ty IPO, giá phụ thuộc vào số dư quỹ Công ty.
    """
    # Nếu là công ty IPO của người chơi
    ipo_comp = companies_col.find_one({"is_ipo": True, "name": {"$regex": f"^{stock_code}", "$options": "i"}})
    if ipo_comp:
        # Giá = Quỹ công ty / 1000. Tối thiểu 5000.
        base_price = max(5000, int(ipo_comp.get("treasury", 0) / 1000))
        # Thêm sự dao động nhẹ theo giờ
        target_time = datetime.now() + timedelta(hours=hour_offset)
        seed_value = int(target_time.strftime("%Y%m%d%H")) + sum(ord(char) for char in stock_code)
        rng = random.Random(seed_value)
        fluctuation = rng.uniform(0.8, 1.2) # Dao động +- 20%
        return int(base_price * fluctuation)

    # Nếu là cổ phiếu mặc định
    target_time = datetime.now() + timedelta(hours=hour_offset)
    seed_value = int(target_time.strftime("%Y%m%d%H")) + sum(ord(char) for char in stock_code)
    rng = random.Random(seed_value)
    
    # Random từ 5k đến 800k
    price = rng.randint(5, 800) * 1000
    
    # Cơ chế phá sản (5% mỗi khung giờ, mã đó sẽ cắm đầu về 1000 VND)
    if rng.randint(1, 100) <= 5:
        return 1000 
        
    return price

def get_next_hour_timestamp():
    next_hour = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int(next_hour.timestamp())
    # =====================================================================
# DATA KHU RỪNG THÁM HIỂM (VŨ KHÍ & KỊCH BẢN TƯỜNG MINH)
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {
        "price": 50, 
        "name": "🪵 Gậy Gỗ Mục", 
        "terrible": 25, 
        "bad": 40, 
        "neutral": 15, 
        "good": 15, 
        "great": 5, 
        "jackpot": 0
    },
    "sung_cao_su": {
        "price": 100, 
        "name": "🪀 Súng Cao Su", 
        "terrible": 20, 
        "bad": 35, 
        "neutral": 20, 
        "good": 20, 
        "great": 5, 
        "jackpot": 0
    },
    "kiem_sat": {
        "price": 200, 
        "name": "🗡️ Kiếm Sắt Thường", 
        "terrible": 15, 
        "bad": 25, 
        "neutral": 20, 
        "good": 25, 
        "great": 13, 
        "jackpot": 2
    },
    "kiem_hiep_si": {
        "price": 500, 
        "name": "⚔️ Kiếm Hiệp Sĩ", 
        "terrible": 10, 
        "bad": 20, 
        "neutral": 15, 
        "good": 30, 
        "great": 20, 
        "jackpot": 5
    },
    "riu_chien": {
        "price": 1000, 
        "name": "🪓 Rìu Phá Giáp", 
        "terrible": 10, 
        "bad": 15, 
        "neutral": 15, 
        "good": 30, 
        "great": 25, 
        "jackpot": 5
    },
    "thanh_kiem": {
        "price": 1500, 
        "name": "🔱 Thánh Kiếm Mạ Vàng", 
        "terrible": 5, 
        "bad": 10, 
        "neutral": 10, 
        "good": 35, 
        "great": 30, 
        "jackpot": 10
    },
    "sung_phong_luu": {
        "price": 3000, 
        "name": "🚀 Súng Phóng Lựu RPG", 
        "terrible": 5, 
        "bad": 5, 
        "neutral": 10, 
        "good": 30, 
        "great": 35, 
        "jackpot": 15
    },
    "gang_tay": {
        "price": 5000, 
        "name": "🧤 Găng Tay Vô Cực", 
        "terrible": 2, 
        "bad": 5, 
        "neutral": 5, 
        "good": 20, 
        "great": 40, 
        "jackpot": 28
    }
}

SCENARIOS = {
    "terrible": [ 
        {
            "mult": -2.0, 
            "msg": "🐘 **KING KONG NỔI GIẬN!**\nBạn vô tình chọc tức chúa tể rừng xanh. Bị đấm bay xa 10km, rớt sạch đồ đạc!"
        },
        {
            "mult": -1.5, 
            "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại đang ngủ. Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền!"
        },
        {
            "mult": -1.3, 
            "msg": "🕳️ **SỤP HỐ CHÔNG!**\nRơi thẳng xuống hố chông của thợ săn. Gãy 2 cái sườn, nôn hết tiền mặt ra đóng viện phí."
        }
    ],
    "bad": [ 
        {
            "mult": -0.5, 
            "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ từ trên cây nhảy xuống giật lấy túi tiền của bạn rồi đu cây biến mất."
        },
        {
            "mult": -0.6, 
            "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước suối hết hạn từ cái máy bán hàng tự động ma quái trong rừng. Bị đau bụng tốn tiền viện phí."
        },
        {
            "mult": -0.8, 
            "msg": "💩 **TRƯỢT CHÂN VÀO BÃI MÌN!**\nBạn dẫm trúng bãi mìn khổng lồ của đàn voi rừng. Tốn tiền đi tắm gội mua bộ đồ mới."
        }
    ],
    "neutral": [ 
        {
            "mult": 0, 
            "msg": "🍂 **LÁ KHÔ XÀO XẠC...**\nBạn vạch lùm cây ra và... chẳng có gì cả, chỉ là một đống lá khô."
        },
        {
            "mult": 0, 
            "msg": "📦 **RƯƠNG RỖNG TOẾCH!**\nHáo hức mở một cái rương cũ kỹ, nhưng bên trong chả có gì ngoài mạng nhện."
        }
    ],
    "good": [ 
        {
            "mult": 0.5, 
            "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."
        },
        {
            "mult": 0.8, 
            "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc Bắc đã trả cho bạn một khoản hời."
        }
    ],
    "great": [ 
        {
            "mult": 1.5, 
            "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp rừng và tịch thu kho báu của chúng!"
        },
        {
            "mult": 2.5, 
            "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nPhát hiện ra một rương kho báu vàng chóe bị chôn vùi. Mở ra toàn tiền là tiền!"
        }
    ],
    "jackpot": [ 
        {
            "mult": 5.0, 
            "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng giải ĐẶC BIỆT!"
        },
        {
            "mult": 12.0, 
            "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR! (ULTRAPOT)**\nDưới đáy đầm lầy, bạn vớt được Vương miện nạm 100 viên kim cương. Bạn thành tỷ phú rồi!!"
        }
    ]
}

# =====================================================================
# DATA NHÂN SINH BẢN HARDCORE (CỰC KỲ KHẮC NGHIỆT)
# =====================================================================
EVENTS_P1 = [
    {
        "q": "Tuổi 15: Bạn tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", 
        "choices": [
            {
                "text": "Đem nộp lên công an phường", 
                "rate": 50, 
                "win": "Chủ ví là một giám đốc lớn, khen thưởng bạn tiền mặt.", 
                "lose": "Bị công an nghi ngờ là người ăn cắp, phạt lao động công ích.", 
                "tien_w": 5000, 
                "tien_l": -10000
            }, 
            {
                "text": "Bỏ túi xài luôn, không nói ai", 
                "rate": 20, 
                "win": "Trót lọt, bạn bao cả lớp ăn chè thỏa thích.", 
                "lose": "Bị check camera, bồi thường tiền và bị đuổi học.", 
                "tien_w": 8000, 
                "tien_l": -25000
            }, 
            {
                "text": "Rút tờ 500k rồi vứt lại ví", 
                "rate": 30, 
                "win": "Trót lọt, bạn dùng tiền đó nạp game.", 
                "lose": "Chủ nhân báo mất, bị giang hồ mạng truy lùng bắt đền gấp 10.", 
                "tien_w": 500, 
                "tien_l": -50000
            }, 
            {
                "text": "Giả vờ không thấy, đi thẳng", 
                "rate": 80, 
                "win": "Bình yên vô sự, cuộc đời không có biến động.", 
                "lose": "Đứa đi sau nhặt được đổ oan cho bạn, phải tự bỏ tiền túi ra đền.", 
                "tien_w": 0, 
                "tien_l": -15000
            }
        ]
    }
]

EVENTS_P2 = [
    {
        "q": "Tuổi 25: Bạn có 500 triệu tiền tiết kiệm, hãy đưa ra quyết định đầu tư.", 
        "choices": [
            {
                "text": "All-in Tiền ảo (Crypto / Memecoin)", 
                "rate": 15, 
                "win": "Giá x100 lần! Bạn chốt lời mua biệt thự và siêu xe.", 
                "lose": "Bị 'úp bô' sập sàn, cháy túi và gánh nợ ngân hàng.", 
                "tien_w": 2500000, 
                "tien_l": -500000
            }, 
            {
                "text": "Gửi tiết kiệm ngân hàng", 
                "rate": 70, 
                "win": "Lãi suất ổn định, cuộc sống an nhàn qua ngày.", 
                "lose": "Ngân hàng bị thanh tra, giám đốc ôm tiền bỏ trốn. Mất sạch.", 
                "tien_w": 50000, 
                "tien_l": -500000
            }, 
            {
                "text": "Khởi nghiệp kinh doanh nhà hàng", 
                "rate": 30, 
                "win": "Khách đông nườm nượp, mở chuỗi 5 chi nhánh.", 
                "lose": "Bị đối thủ chơi bẩn bóc phốt trên Tiktok, phá sản ôm nợ.", 
                "tien_w": 500000, 
                "tien_l": -800000
            }, 
            {
                "text": "Mua vàng cất vào két sắt", 
                "rate": 60, 
                "win": "Vàng tăng giá phi mã, bạn chốt lời đậm.", 
                "lose": "Bị trộm cạy cửa vào nhà khiêng luôn két sắt.", 
                "tien_w": 100000, 
                "tien_l": -500000
            }
        ]
    }
]

EVENTS_P3 = [
    {
        "q": "Tuổi 35: Cò đất rủ bạn chung vốn lướt sóng khu quy hoạch mới.", 
        "choices": [
            {
                "text": "Cắm sổ đỏ vay nặng lãi quất liền", 
                "rate": 10, 
                "win": "Thành công vang dội! Giá đất x5, bạn thành tỷ phú bất động sản.", 
                "lose": "Dính bẫy dự án ma của Công ty lừa đảo. Giang hồ siết nợ, ra đê ở.", 
                "tien_w": 5000000, 
                "tien_l": -2000000
            }, 
            {
                "text": "Mua 1 lô nhỏ bằng vốn tự có", 
                "rate": 40, 
                "win": "Đất lên nhẹ, bạn chốt lời an toàn.", 
                "lose": "Đất dính quy hoạch làm nghĩa trang, giam vốn không ai mua.", 
                "tien_w": 300000, 
                "tien_l": -200000
            }, 
            {
                "text": "Làm 'Cò đất' ăn hoa hồng", 
                "rate": 50, 
                "win": "Chốt được chục lô, hoa hồng nhận mỏi tay.", 
                "lose": "Khách hàng bùng kèo, bị chủ đất giam tiền cọc bắt đền.", 
                "tien_w": 200000, 
                "tien_l": -100000
            }, 
            {
                "text": "Không quan tâm nhà đất", 
                "rate": 80, 
                "win": "Cuộc sống trôi qua bình yên, tập trung lo cho gia đình.", 
                "lose": "Lạm phát tăng cao, tiền giấy mất giá trầm trọng.", 
                "tien_w": 0, 
                "tien_l": -50000
            }
        ]
    },
    {
        "q": "Tuổi 35: Bạn thân cũ gọi điện khóc lóc, hỏi vay 300 triệu lo viện phí.", 
        "choices": [
            {
                "text": "Cho vay ngay, không cần giấy tờ", 
                "rate": 20, 
                "win": "Bạn qua cơn bĩ cực, làm ăn phất lên trả ơn bạn gấp 5 lần.", 
                "lose": "Nó cầm tiền đi đánh tài xỉu thua sạch, chặn số bom tiền.", 
                "tien_w": 1500000, 
                "tien_l": -300000
            }, 
            {
                "text": "Từ chối khéo, bảo không có tiền", 
                "rate": 90, 
                "win": "Bạn giữ được tiền, tuy có chút áy náy.", 
                "lose": "Bị nó bóc phốt lên Facebook là đồ bạn bè sống lỗi.", 
                "tien_w": 0, 
                "tien_l": -10000
            }, 
            {
                "text": "Chỉ cho vay 5 triệu gọi là giúp đỡ", 
                "rate": 70, 
                "win": "Nó nhận tiền và cảm ơn bạn rối rít.", 
                "lose": "Nó chê ít, chửi bạn một trận rồi cúp máy.", 
                "tien_w": 0, 
                "tien_l": -5000
            }, 
            {
                "text": "Cho vay nhưng bắt ký giấy thế chấp xe", 
                "rate": 50, 
                "win": "Nó không trả được, bạn siết luôn con xe SH mang đi bán.", 
                "lose": "Xe là xe gian (trộm cắp), bạn bị công an phạt vì tội tiêu thụ đồ gian.", 
                "tien_w": 100000, 
                "tien_l": -150000
            }
        ]
    }
]

EVENTS_P4 = [
    {
        "q": "Tuổi 50: Bạn bước vào giai đoạn khủng hoảng tuổi trung niên.", 
        "choices": [
            {
                "text": "Bán đất mua siêu xe để tìm lại thanh xuân", 
                "rate": 10, 
                "win": "Tham gia giải đua xe, trở nên nổi tiếng và kiếm bồn tiền từ quảng cáo.", 
                "lose": "Đạp nhầm chân ga tông nát xe, đền tiền sửa chữa và tiền thuốc men.", 
                "tien_w": 800000, 
                "tien_l": -1000000
            }, 
            {
                "text": "Cặp Sugar Baby / Phi công trẻ", 
                "rate": 20, 
                "win": "Tâm hồn trẻ lại, sung mãn như thanh niên.", 
                "lose": "Bị vợ/chồng bắt ghen tung lên mạng, ra tòa ly hôn mất trắng tài sản.", 
                "tien_w": 10000, 
                "tien_l": -2000000
            }, 
            {
                "text": "Chơi đồ cổ, lan đột biến", 
                "rate": 30, 
                "win": "Bán được bình gốm cổ cho đại gia nước ngoài, thu lãi cực đậm.", 
                "lose": "Thị trường sập, ôm đống rác trong nhà, nợ nần chồng chất.", 
                "tien_w": 600000, 
                "tien_l": -500000
            }, 
            {
                "text": "Tập Thiền, đi chùa, ăn chay", 
                "rate": 80, 
                "win": "Tâm hồn thanh tịnh, sức khỏe dồi dào, sống thọ.", 
                "lose": "Bị gian thương bán nấm chay có độc, phải đi rửa ruột.", 
                "tien_w": 50000, 
                "tien_l": -80000
            }
        ]
    }
]

EVENTS_P5 = [
    {
        "q": "Tuổi 70: Bạn đã già yếu. Có người đến gạ bán Linh Đan Cải Lão Hoàn Đồng giá 1 Tỷ.", 
        "choices": [
            {
                "text": "Vung tiền mua ngay không chần chừ", 
                "rate": 5, 
                "win": "Phép màu xảy ra! Bạn trở lại tuổi 20 sung mãn, sức mạnh vô địch!", 
                "lose": "Thuốc giả chứa chì và thủy ngân. Bạn thăng thiên sớm, để lại khoản nợ.", 
                "tien_w": 5000000, 
                "tien_l": -1000000,
                "die_l": True
            }, 
            {
                "text": "Lập di chúc chia tài sản cho con cháu", 
                "rate": 60, 
                "win": "Con cháu hiếu thảo, tổ chức lễ mừng thọ hoành tráng.", 
                "lose": "Con cháu bất hiếu, đánh nhau giành giật gia tài. Bạn tức quá đột quỵ.", 
                "tien_w": 200000, 
                "tien_l": -500000,
                "die_l": True
            }, 
            {
                "text": "Quyên góp 100% tài sản đi làm từ thiện", 
                "rate": 70, 
                "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", 
                "lose": "Tổ chức từ thiện cuỗm tiền chạy mất. Bạn ôm hận qua đời.", 
                "tien_w": 500000, 
                "tien_l": -1000000,
                "die_l": True
            }, 
            {
                "text": "Lên Las Vegas quất 1 ván Casino All-in cuối đời", 
                "rate": 10, 
                "win": "Trúng Jackpot 50 triệu đô! Lên báo quốc tế, trở thành huyền thoại.", 
                "lose": "Thua trắng tay, nhồi máu cơ tim gục tại bàn sòng bạc.", 
                "tien_w": 10000000, 
                "tien_l": -1000000,
                "die_l": True
            }
        ]
    }
]
# =====================================================================
# GIAO DIỆN UI: CỬA HÀNG ĐẠI GIA VÀ CHỢ ĐEN CẦM ĐỒ
# =====================================================================
class ShopItemSelect(discord.ui.Select):
    """Bảng Dropdown chọn đồ trong Cửa Hàng"""
    def __init__(self, category_type):
        options = []
        for key, item_data in SHOP_ITEMS.items():
            if item_data["type"] == category_type:
                options.append(
                    discord.SelectOption(
                        label=item_data['name'], 
                        description=f"Giá: {item_data['price']:,} 💰", 
                        value=key, 
                        emoji=item_data['emoji']
                    )
                )
                
        super().__init__(
            placeholder="Nhấn vào đây để chọn món đồ muốn tậu...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_info = SHOP_ITEMS[self.values[0]]
        
        # Kiểm tra túi tiền
        if user_data.get("money", 0) < item_info["price"]:
            embed_fail = discord.Embed(
                description=f"⚠️ Thẻ từ chối! Bạn cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        # Xử lý mua Danh hiệu
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            success_message = f"🎉 Tiền trao cháo múc! Bạn đã trang bị danh hiệu: **{item_info['name']}**."
        else:
            # Xử lý mua Đồ vật (Xe, Nhà...)
            if item_info["name"] in user_data.get("assets", []):
                # Nếu đã có, hoàn lại tiền và báo lỗi
                user_data["money"] += item_info["price"] 
                embed_exist = discord.Embed(
                    description=f"⚠️ Bạn đã đứng tên sở hữu **{item_info['name']}** rồi, mua thêm chi cho chật nhà!", 
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed_exist, ephemeral=True)
            
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Chúc mừng đại gia! Bạn vừa đập hộp siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        
        embed_success = discord.Embed(
            title="🛍️ GIAO DỊCH HOÀN TẤT!", 
            description=success_message, 
            color=discord.Color.green()
        )
        embed_success.set_footer(
            text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    """Menu chọn danh mục trong Cửa hàng Đại Gia"""
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(
            title="🛍️ QUẦY BÁN DANH HIỆU", 
            description="Tút tát lại vẻ đẹp trai bằng một danh hiệu xịn xò dán lên Căn Cước.", 
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(
            title="🛍️ SHOWROOM XE CỘ & PHI CƠ", 
            description="Đẳng cấp thể hiện qua tốc độ. Hãy chọn một con xe ưng ý.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(
            title="🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN", 
            description="Đầu tư nhà đất là kênh an toàn nhất để xưng vương.", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Ai gọi lệnh người đó mua nha, đừng có bấm giành!", ephemeral=True)
            return False
        return True

class SellItemSelect(discord.ui.Select):
    """Bảng Dropdown chọn đồ muốn bán cho Chợ đen"""
    def __init__(self, items, is_pet=False):
        self.is_pet = is_pet
        options = []
        
        if is_pet:
            count = 0
            for pet, quantity in list(items.items()):
                if count >= 25: break
                if quantity > 0: 
                    options.append(discord.SelectOption(
                        label=pet, 
                        description=f"Đang có: {quantity} con | Chợ đen thâu tóm: {get_pet_sell_price(pet):,} 💰", 
                        value=pet
                    ))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(
                    label=asset, 
                    description=f"Bị ép giá còn: {get_asset_price(asset):,} 💰", 
                    value=asset
                ))
                
        super().__init__(placeholder="Chọn món đồ bạn muốn cắm sổ / bán...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_value = self.values[0]
        
        if self.is_pet:
            if user_data.get("pets", {}).get(item_value, 0) <= 0: 
                return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này trong chuồng!", ephemeral=True)
                
            sell_price = get_pet_sell_price(item_value)
            user_data["pets"][item_value] -= 1
            
            if user_data["pets"][item_value] == 0: 
                del user_data["pets"][item_value]
                
            success_message = f"✅ Thương lái đã mang bé **{item_value}** đi.\nBạn nhận được **{sell_price:,} 💰** tiền tươi thóc thật!"
        else:
            if item_value not in user_data.get("assets", []): 
                return await interaction.response.send_message("Lỗi: Bạn làm gì có tài sản này mà đòi đem cắm!", ephemeral=True)
                
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            success_message = f"✅ Chủ tiệm cầm đồ đã thâu tóm **{item_value}**.\nBạn cắn răng chịu lỗ, vớt vát lại được **{sell_price:,} 💰**!"

        user_data["money"] += sell_price
        save_user(user_id)
        
        embed = discord.Embed(
            title="🤝 GIAO DỊCH HOÀN TẤT", 
            description=success_message, 
            color=discord.Color.dark_orange()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class SellCategoryMenu(discord.ui.View):
    """Menu chọn danh mục bán trong Chợ đen"""
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Cắm Sổ Đỏ / Cầm Xe", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: 
            embed_err = discord.Embed(description="Bạn không có tài sản nào để bán cả! Nghèo rớt mồng tơi.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        
        embed = discord.Embed(
            title="🏷️ CẦM ĐỒ BĐS & XE CỘ", 
            description="Lưu ý: Bạn sẽ bị con buôn ép giá tơi bời, chịu lỗ 30% giá trị so với lúc mua.", 
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(quantity == 0 for quantity in pets.values()): 
            embed_err = discord.Embed(description="Bạn chưa đập được con Thú cưng nào để bán cả!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        
        embed = discord.Embed(
            title="🏷️ TRẠM THU MUA THÚ CƯNG", 
            description="Thu mua thú cưng đổi lấy tiền mặt nhanh gọn lẹ. Pet càng hiếm giá càng cao.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: 
            return False
        return True

# =====================================================================
# GIAO DIỆN UI: TRẠM TREO MÁY AFK
# =====================================================================
class ExpSelect(discord.ui.Select):
    """Bảng chọn thời gian treo máy dã ngoại"""
    def __init__(self):
        options = [
            discord.SelectOption(
                label="4 Giờ (Bãi Cỏ Yên Bình)", 
                description="Rủi ro thấp, phần thưởng dự kiến: ~450 💰", 
                emoji="🌿", 
                value="4"
            ),
            discord.SelectOption(
                label="8 Giờ (Hang Động Tối Tăm)", 
                description="Rủi ro trung bình, phần thưởng dự kiến: ~1000 💰", 
                emoji="🦇", 
                value="8"
            ),
            discord.SelectOption(
                label="12 Giờ (Di Tích Nguy Hiểm)", 
                description="Rủi ro cao, phần thưởng dự kiến: ~2000 💰", 
                emoji="🏛️", 
                value="12"
            )
        ]
        super().__init__(
            placeholder="Lựa chọn địa điểm hạ trại...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        hours = int(self.values[0])
        
        # Ngẫu nhiên phần thưởng tương xứng
        if hours == 4: 
            reward = random.randint(300, 600)
        elif hours == 8: 
            reward = random.randint(700, 1200)
        else: 
            reward = random.randint(1500, 2500)
            
        end_time = datetime.now() + timedelta(hours=hours)
        
        user_data["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = reward
        save_user(user_id)

        embed_success = discord.Embed(
            title="⛺ LÊN ĐƯỜNG BÌNH AN!", 
            description=f"Hành lý đã chuẩn bị xong. Bạn vác balo tiến vào rừng và bắt đầu cắm trại **{hours} giờ**.\n\n⏳ Khi nào hết thời gian, hãy gõ lại lệnh `k phai` để thu hoạch chiến lợi phẩm mang về nhé.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed_success, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            return False
        return True

# =====================================================================
# GIAO DIỆN UI: GAME NHÂN SINH LỰA CHỌN ĐA VŨ TRỤ (HARDCORE)
# =====================================================================
class NhanSinhGameView(discord.ui.View):
    """Hệ thống lõi của Game Nhân Sinh - Xử lý ngã rẽ cuộc đời"""
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        # Khởi tạo kịch bản tuổi 15
        self.ev = random.choice(EVENTS_P1)

        # Mở bài theo điểm may mắn
        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng, bố mẹ là tài phiệt ác ma.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức bình dân êm ấm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài bãi rác từ nhỏ.")

        # Khởi tạo 4 Nút Lựa Chọn A, B, C, D
        self.btn_a = discord.ui.Button(
            label=f"A. {self.ev['choices'][0]['text'][:70]}", 
            style=discord.ButtonStyle.primary, 
            custom_id="btn_a"
        )
        self.btn_b = discord.ui.Button(
            label=f"B. {self.ev['choices'][1]['text'][:70]}", 
            style=discord.ButtonStyle.secondary, 
            custom_id="btn_b"
        )
        self.btn_c = discord.ui.Button(
            label=f"C. {self.ev['choices'][2]['text'][:70]}", 
            style=discord.ButtonStyle.success, 
            custom_id="btn_c"
        )
        self.btn_d = discord.ui.Button(
            label=f"D. {self.ev['choices'][3]['text'][:70]}", 
            style=discord.ButtonStyle.danger, 
            custom_id="btn_d"
        )
        
        # Gắn callback
        self.btn_a.callback = self.choice_a
        self.btn_b.callback = self.choice_b
        self.btn_c.callback = self.choice_c
        self.btn_d.callback = self.choice_d
        
        self.add_item(self.btn_a)
        self.add_item(self.btn_b)
        self.add_item(self.btn_c)
        self.add_item(self.btn_d)

    async def on_timeout(self):
        """Xử lý khi người chơi AFK bỏ dở game"""
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: 
            dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng xen vào cuộc đời của người khác!", ephemeral=True)
            return False
        return True

    # Các hàm liên kết nút bấm tới index của mảng
    async def choice_a(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        """Xử lý Logic cốt lõi khi bấm 1 nút lựa chọn"""
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        # Tỉ lệ thành công = Tỉ lệ gốc + (May Mắn * 1.5). Khóa giới hạn tối đa 85% để tạo độ rủi ro Hardcore.
        calculated_rate = base_rate + (self.stats["may_man"] * 1.5)
        final_rate = min(85.0, calculated_rate)
        
        roll = random.uniform(0, 100)
        is_win = roll <= final_rate
        
        result_msg = choice_data["win"] if is_win else choice_data["lose"]
        money_change = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        # Kiểm tra cờ Đột tử (die)
        is_dead = False
        if is_win and choice_data.get("die_w", False): 
            is_dead = True
        if not is_win and choice_data.get("die_l", False): 
            is_dead = True

        self.tien_an += money_change
        
        # Tạo nhật ký (Log) để ghi lại hành trình
        status_icon = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ thành công: **{final_rate:.1f}%** (Xúc xắc: {roll:.1f})\n{status_icon}: {result_msg} ({money_change:,} 💰)"
        
        if self.phase == 1: 
            tuoi_hien_tai = 15
        elif self.phase == 2: 
            tuoi_hien_tai = 25
        elif self.phase == 3: 
            tuoi_hien_tai = 35
        elif self.phase == 4: 
            tuoi_hien_tai = 50
        else: 
            tuoi_hien_tai = 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Bạn chọn con đường {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời luân hồi khép lại sớm.**")
            self.phase = 99 # Đẩy phase lên mức max để ngắt game
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Bạn chọn con đường {letter}.\n{log_entry}")
            self.phase += 1
            
            # Sang giai đoạn mới, load kịch bản tiếp theo ngẫu nhiên
            if self.phase == 2: 
                self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: 
                self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: 
                self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: 
                self.ev = random.choice(EVENTS_P5)

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        """Cập nhật lại giao diện sau mỗi lượt chơi"""
        embed = discord.Embed(
            title="🌀 MÔ PHỎNG NHÂN SINH", 
            description=f"Ký chủ luân hồi: {self.author.mention}", 
            color=discord.Color.teal()
        )
        
        stats_text = f"Tâm linh / May mắn: **{self.stats['may_man']}/10** *(Được buff +{self.stats['may_man']*1.5}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số ban đầu", value=stats_text, inline=False)

        # Rút gọn log nếu quá dài để không bị quá ký tự giới hạn của embed (hiển thị 4 turn gần nhất)
        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        # Game tiếp tục
        if self.phase <= 5:
            if self.phase == 1: tuoi_next = 15
            elif self.phase == 2: tuoi_next = 25
            elif self.phase == 3: tuoi_next = 35
            elif self.phase == 4: tuoi_next = 50
            else: tuoi_next = 70
            
            embed.add_field(name=f"❓ Ngã rẽ quyết định tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
            
        # Game kết thúc
        else:
            # Khóa và Xóa toàn bộ nút bấm
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.btn_c.disabled = True
            self.btn_d.disabled = True
            self.clear_items() 
            
            # Dọn dẹp cờ trạng thái
            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: 
                dang_choi_nhansinh.remove(user_id)

            # Thanh toán tiền
            user_data = load_user(user_id)
            user_data["money"] += self.tien_an
            save_user(user_id)

            # Cập nhật thông báo cuối cùng
            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(
                    name="🪦 Về với Cát Bụi", 
                    value=f"Sống lỗi để lại một đống nợ khổng lồ, chủ nợ đến siết nhà.\n❌ **BÁO NHÀ!** Khoản nợ phải gánh: **{self.tien_an:,} 💰**", 
                    inline=False
                )
            elif self.tien_an >= 500000:
                embed.color = discord.Color.gold()
                embed.add_field(
                    name="🪦 Về với Cát Bụi", 
                    value=f"Hưởng thọ trong nhung lụa vinh hoa, con cháu kính trọng.\n👑 **TỶ PHÚ ĐỜI THẬT!** Di sản để lại: **+{self.tien_an:,} 💰**", 
                    inline=False
                )
            else:
                embed.color = discord.Color.blue()
                embed.add_field(
                    name="🪦 Về với Cát Bụi", 
                    value=f"Một cuộc đời êm ấm trôi qua, không còn gì nuối tiếc.\n💼 **DƯ DẢ!** Di sản để lại: **+{self.tien_an:,} 💰**", 
                    inline=False
                )

        # Cập nhật tin nhắn
        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)
            # =====================================================================
# GIAO DIỆN UI: ĐẤU TRƯỜNG SOLO OẲN TÙ TÌ
# =====================================================================
class SoloOTTGame(discord.ui.View):
    """Bảng chọn chiêu thức ẩn danh trong trận Oẳn Tù Tì"""
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1
        self.player_2 = player_2
        self.bet_amount = bet_amount
        self.msg = None
        
        # Lưu trữ lựa chọn của hai người chơi
        self.choices = {
            str(player_1.id): None, 
            str(player_2.id): None
        }

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "🪨")

    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "📄")

    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "✂️")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = str(interaction.user.id)
        
        if user_id not in self.choices:
            embed_err = discord.Embed(description="⚠️ Tránh ra chỗ khác, đây là trận chiến vinh dự riêng tư của hai người họ!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        if self.choices[user_id] is not None:
            embed_err = discord.Embed(description="⚠️ Quân tử nhất ngôn! Bạn đã ra chiêu rồi, không được rút lại đâu!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        self.choices[user_id] = choice
        embed_success = discord.Embed(description=f"🤫 Bạn đã giấu tay chọn **{choice}**. Hãy nín thở chờ đối thủ ra chiêu...", color=discord.Color.green())
        await interaction.response.send_message(embed=embed_success, ephemeral=True)

        if self.choices[str(self.player_1.id)] is not None and self.choices[str(self.player_2.id)] is not None:
            for child in self.children: 
                child.disabled = True
                
            choice_1 = self.choices[str(self.player_1.id)]
            choice_2 = self.choices[str(self.player_2.id)]
            
            p1_data = load_user(self.player_1.id)
            p2_data = load_user(self.player_2.id)
            tong_thuong = self.bet_amount * 2
            
            if choice_1 == choice_2:
                ket_qua = "🤝 **HÒA NHAU!** Bất phân thắng bại, tiền cược được trả lại."
                p1_data["money"] += self.bet_amount
                p2_data["money"] += self.bet_amount
            elif (choice_1 == "🪨" and choice_2 == "✂️") or (choice_1 == "📄" and choice_2 == "🪨") or (choice_1 == "✂️" and choice_2 == "📄"):
                ket_qua = f"🎉 **{self.player_1.name} ĐÃ CHIẾN THẮNG!**\nĐè bẹp đối thủ và húp trọn **{tong_thuong:,} 💰**."
                p1_data["money"] += tong_thuong
            else:
                ket_qua = f"🎉 **{self.player_2.name} ĐÃ CHIẾN THẮNG!**\nĐè bẹp đối thủ và húp trọn **{tong_thuong:,} 💰**."
                p2_data["money"] += tong_thuong
                
            save_user(self.player_1.id)
            save_user(self.player_2.id)
            
            embed_result = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed_result.add_field(name=self.player_1.name, value=f"Ra {choice_1}", inline=True)
            embed_result.add_field(name="VS", value="⚡", inline=True)
            embed_result.add_field(name=self.player_2.name, value=f"Ra {choice_2}", inline=True)
            embed_result.add_field(name="KẾT QUẢ CUỐI CÙNG", value=ket_qua, inline=False)
            
            await self.msg.edit(embed=embed_result, view=self)
            self.stop()

    async def on_timeout(self):
        if self.choices[str(self.player_1.id)] is None or self.choices[str(self.player_2.id)] is None:
            p1_data = load_user(self.player_1.id)
            p2_data = load_user(self.player_2.id)
            
            p1_data["money"] += self.bet_amount
            p2_data["money"] += self.bet_amount
            save_user(self.player_1.id)
            save_user(self.player_2.id)
            
            embed_timeout = discord.Embed(
                title="⏳ HẾT GIỜ KHIẾP SỢ", 
                description="Có người nhát gan không dám ra chiêu. Trận đấu bị hủy, tiền cược đã hoàn trả!", 
                color=discord.Color.dark_gray()
            )
            try: await self.msg.edit(embed=embed_timeout, view=None)
            except Exception: pass

class SoloOTTAccept(discord.ui.View):
    """Bảng hiển thị lời thách đấu và nút Nhận Kèo"""
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1
        self.player_2 = player_2
        self.bet_amount = bet_amount

    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_2.id:
            embed_err = discord.Embed(description="⚠️ Kèo này gạ người khác, ông chui vào đây bấm làm gì!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        p1_data = load_user(self.player_1.id)
        p2_data = load_user(self.player_2.id)
        
        if p1_data.get("money", 0) < self.bet_amount or p2_data.get("money", 0) < self.bet_amount:
            embed_err = discord.Embed(description="⚠️ Lỗi! Một trong hai người đã tiêu cạn tiền trong ví, không đủ lúa để chơi ván này nữa!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        p1_data["money"] -= self.bet_amount
        p2_data["money"] -= self.bet_amount
        save_user(self.player_1.id)
        save_user(self.player_2.id)

        game_view = SoloOTTGame(self.player_1, self.player_2, self.bet_amount)
        embed_game = discord.Embed(
            title="⚔️ PK OẲN TÙ TÌ", 
            description=f"{self.player_1.mention} 🆚 {self.player_2.mention}\nTiền cược mỗi bên: **{self.bet_amount:,} 💰**\n\n👇 **HÃY BẤM NÚT ĐỂ CHỌN CHIÊU (Sẽ bị giấu kín)**", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed_game, view=game_view)
        game_view.msg = interaction.message
        self.stop()

class MarryAccept(discord.ui.View):
    """Bảng hỏi cưới hiển thị cho Crush"""
    def __init__(self, sender, receiver):
        super().__init__(timeout=60)
        self.sender = sender
        self.receiver = receiver
        
    @discord.ui.button(label="Em Đồng Ý", style=discord.ButtonStyle.success, emoji="💍")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: 
            embed_err = discord.Embed(description="⚠️ Người ta đang cầu hôn người khác, vô duyên đừng có bấm bậy!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        sender_data = load_user(self.sender.id)
        receiver_data = load_user(self.receiver.id)
        
        if sender_data.get("money", 0) < 1000000: 
            embed_err = discord.Embed(description=f"⚠️ Ôi không! {self.sender.name} đã lỡ tiêu hết tiền, không đủ 1 Triệu sắm Lễ Cưới nữa rồi!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        sender_data["money"] -= 1000000
        sender_data["spouse"] = str(self.receiver.id)
        receiver_data["spouse"] = str(self.sender.id)
        
        save_user(self.sender.id)
        save_user(self.receiver.id)
        
        for child in self.children: 
            child.disabled = True
            
        embed_success = discord.Embed(
            title="💒 KẾT HÔN THÀNH CÔNG", 
            description=f"🎉 Pháo hoa nổ rợp trời! Xin chúc mừng hai vợ chồng {self.sender.mention} và {self.receiver.mention}!\nTừ nay các bạn đã là của nhau. Trăm năm hạnh phúc nhé!", 
            color=discord.Color.magenta()
        )
        embed_success.set_image(url=GIF_LINKS["marry"])
        await interaction.response.edit_message(embed=embed_success, view=self)
        self.stop()
        
    @discord.ui.button(label="Em Từ Chối", style=discord.ButtonStyle.danger, emoji="💔")
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: 
            return await interaction.response.send_message("Tránh ra!", ephemeral=True)
            
        for child in self.children: 
            child.disabled = True
            
        embed_fail = discord.Embed(
            description=f"💔 Quá đắng cay! Tình yêu không thể gượng ép...\n{self.receiver.mention} đã từ chối phũ phàng lời cầu hôn của {self.sender.mention}...", 
            color=discord.Color.dark_grey()
        )
        await interaction.response.edit_message(embed=embed_fail, view=self)
        self.stop()

class CompanyInviteView(discord.ui.View):
    """Bảng mời gia nhập Công ty"""
    def __init__(self, comp_id, comp_name, target_user):
        super().__init__(timeout=60)
        self.comp_id = comp_id
        self.comp_name = comp_name
        self.target_user = target_user

    @discord.ui.button(label="Đồng ý Gia nhập", style=discord.ButtonStyle.success, emoji="🤝")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: 
            return await interaction.response.send_message("Lệnh mời này không dành cho bạn!", ephemeral=True)
        
        target_id = str(self.target_user.id)
        target_data = load_user(target_id)
        
        if target_data.get("company"): 
            embed_err = discord.Embed(description="⚠️ Bạn đã thuộc về một công ty rồi, phải thoát trước khi gia nhập chỗ mới!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        comp = load_company(self.comp_id)
        if not comp: 
            embed_err = discord.Embed(description="⚠️ Công ty này đã tuyên bố phá sản hoặc không còn tồn tại!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        comp["members"][target_id] = "nhanvien"
        target_data["company"] = self.comp_id
        
        save_company(self.comp_id)
        save_user(target_id)
        
        embed_success = discord.Embed(
            description=f"🎉 Chúc mừng! {self.target_user.mention} đã chính thức ký hợp đồng gia nhập công ty **{self.comp_name}**!", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(content=None, embed=embed_success, view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: 
            return await interaction.response.send_message("Tránh ra!", ephemeral=True)
            
        embed_fail = discord.Embed(description=f"❌ {self.target_user.mention} đã xé bỏ hợp đồng, chê thẳng thừng lời mời của **{self.comp_name}**.", color=discord.Color.red())
        await interaction.response.edit_message(content=None, embed=embed_fail, view=None)

# =====================================================================
# HỆ THỐNG SÀN CHỨNG KHOÁN (CÓ CƠ CHẾ IPO VÀ RUG PULL)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    """Bảng hiển thị giá trị cổ phiếu trên thị trường chứng khoán"""
    next_timestamp = get_next_hour_timestamp()
    all_stocks = get_all_stocks()
    
    embed = discord.Embed(
        title="📈 SÀN CHỨNG KHOÁN PHỐ WALL (IPO & MẶC ĐỊNH)", 
        description=f"Thị trường sẽ đóng phiên và cập nhật giá mới vào: <t:{next_timestamp}:R>\n\n"
                    f"🛒 Lệnh Mua: `k ck buy <MÃ> <Số lượng>`\n"
                    f"💸 Lệnh Bán: `k ck sell <MÃ> <Số lượng>`\n"
                    f"🏢 Lên Sàn: `k ck ipo` (Dành cho cty quỹ >50 Triệu)", 
        color=discord.Color.blue()
    )
    
    # Liệt kê các mã cổ phiếu và giá hiện tại
    for code, name in all_stocks.items():
        price_now = get_stock_price(code, 0)
        price_old = get_stock_price(code, -1)
        
        # Cảnh báo phá sản / Hủy niêm yết
        if price_now <= 1000:
            trend = "💀 HỦY NIÊM YẾT / ĐÁY XÃ HỘI"
            difference = 0
        else:
            if price_now > price_old:
                trend = "🟩 Đang Lên"
            else:
                trend = "🟥 Đang Xuống"
            difference = abs(price_now - price_old)
        
        embed.add_field(
            name=f"🏢 {code} - {name}", 
            value=f"Giá niêm yết: **{price_now:,} 💰**\n*(Biến động: {trend} {difference:,})*", 
            inline=False
        )
        
    user_data = load_user(ctx.author.id)
    my_stocks = user_data.get("stocks", {})
    
    inventory_str = ""
    for code, quantity in my_stocks.items():
        if quantity > 0:
            # Hiện giá trị đang nắm giữ
            current_val = get_stock_price(code, 0) * quantity
            inventory_str += f"🔸 {code}: {quantity} CP (Đang có giá trị: {current_val:,} 💰)\n"
            
    if not inventory_str:
        inventory_str = "Ví đầu tư của bạn đang trống trơn."
        
    embed.add_field(name="🎒 Cổ phiếu bạn đang nắm giữ", value=inventory_str, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    """Lệnh mua cổ phiếu (Có cơ chế Rug Pull)"""
    code = code.upper()
    all_stocks = get_all_stocks()
    
    if code not in all_stocks:
        embed_err = discord.Embed(description="⚠️ Mã cổ phiếu này không tồn tại trên sàn giao dịch!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if qty <= 0: 
        embed_err = discord.Embed(description="⚠️ Số lượng mua phải lớn hơn 0!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    stock_price = get_stock_price(code, 0)
    
    if stock_price <= 1000:
        embed_err = discord.Embed(description="⚠️ Công ty này đã bị hủy niêm yết / rớt đáy xã hội, sàn chứng khoán khóa chức năng mua!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)

    total_cost = stock_price * qty
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) < total_cost: 
        embed_err = discord.Embed(description=f"⚠️ Thiếu lúa rồi đại gia ơi! Bạn cần tới **{total_cost:,} 💰** để khớp lệnh.", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    # TRỪ TIỀN TRƯỚC TIÊN ĐỂ KIỂM TRA RUG PULL
    user_data["money"] -= total_cost
    
    # CƠ CHẾ RUG PULL: Đầu tư hơn 50 triệu có 15% bị úp bô
    if total_cost >= 50000000:
        if random.randint(1, 100) <= 15:
            save_user(user_id)
            embed_rugpull = discord.Embed(
                title="🚨 CẢNH BÁO TỘI PHẠM KINH TẾ (RUG PULL) 🚨", 
                description=f"**Trời ơi tin được không!**\nKhi bạn vừa chuyển khoản **{total_cost:,} 💰** để mua lượng lớn cổ phiếu **{code}**...\n\n"
                            f"CEO của công ty này đã ôm toàn bộ số tiền của bạn, lên phi cơ riêng trốn ra nước ngoài!\n"
                            f"Sàn chứng khoán đóng băng mã này, bạn mất trắng số tiền vừa mua!", 
                color=discord.Color.red()
            )
            embed_rugpull.set_image(url=GIF_LINKS["rugpull"])
            return await ctx.reply(embed=embed_rugpull, mention_author=False)
            
    # Thêm cổ phiếu vào túi đồ bình thường nếu không bị Rug pull
    current_qty = user_data.get("stocks", {}).get(code, 0)
    user_data["stocks"][code] = current_qty + qty
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Lệnh BUY đã khớp! Bạn vừa đầu tư mua **{qty} {code}** với tổng số tiền là **{total_cost:,} 💰**.", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    """Lệnh chốt lời/cắt lỗ cổ phiếu"""
    code = code.upper()
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    all_stocks = get_all_stocks()
    
    if code not in all_stocks:
        embed_err = discord.Embed(description="⚠️ Mã cổ phiếu này không tồn tại!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    my_qty = user_data.get("stocks", {}).get(code, 0)
    
    if qty <= 0 or my_qty < qty: 
        embed_err = discord.Embed(description="⚠️ Bạn không đủ số lượng cổ phiếu này để bán!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    total_gain = get_stock_price(code, 0) * qty
    
    user_data["stocks"][code] -= qty
    if user_data["stocks"][code] == 0:
        del user_data["stocks"][code]
        
    user_data["money"] += total_gain
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Lệnh SELL đã khớp! Bạn vừa bán **{qty} {code}** và thu về **{total_gain:,} 💰**.", 
        color=discord.Color.gold()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

# =====================================================================
# HỆ THỐNG MINIGAME: CƯỚP BANK, ĐÀO VÀNG, VIETLOTT
# =====================================================================
@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    """Cướp ngân hàng có GIF"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("money", 0) < 50000: 
        embed_err = discord.Embed(description="⚠️ Bạn cần phải có tối thiểu **50,000 💰** trong ví để làm vốn mua súng M4A1 mới đi cướp được!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
    
    if user_id in cty_cooldowns:
        time_diff = (now - cty_cooldowns[user_id]).total_seconds()
        if time_diff < 3600:
            embed_err = discord.Embed(description="⏳ Bạn đang bị truy nã gắt gao cấp độ 5 sao! Hãy đi trốn 1 tiếng nữa rồi hẵng quay lại cướp tiếp.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)
    
    cty_cooldowns[user_id] = now
    
    embed_start = discord.Embed(
        title="🔫 PHI VỤ THẾ KỶ", 
        description="Bạn đang đeo mặt nạ đen, tay lăm lăm khẩu súng đạp cửa xông vào Ngân hàng Trung ương...", 
        color=discord.Color.dark_grey()
    )
    msg = await ctx.send(embed=embed_start)
    await asyncio.sleep(2.5)
    
    roll = random.randint(1, 100)
    if roll <= 20: 
        loot_amount = random.randint(200000, 800000)
        user_data["money"] += loot_amount
        save_user(user_id)
        
        embed_win = discord.Embed(
            title="🎉 PHI VỤ TRÓT LỌT!", 
            description=f"Bạn uy hiếp giám đốc, vơ vét sạch két sắt và chuồn êm qua đường cống ngầm.\n\n💰 Vụ này húp trọn: **{loot_amount:,} 💰**!", 
            color=discord.Color.green()
        )
        embed_win.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed_win)
    else: 
        user_data["money"] -= 50000 
        jail_time = now + timedelta(minutes=10)
        user_data["jail_time"] = jail_time.strftime("%Y-%m-%d %H:%M:%S")
        save_user(user_id)
        
        embed_lose = discord.Embed(
            title="🚨 BỊ CÔNG AN TÓM GỌN", 
            description=f"**WEE WOO WEE WOO!** Đặc nhiệm SWAT ập tới thả bom mù!\nBạn bị tóm gọn, xích tay lôi đi.\n\n"
                        f"❌ Trịch thu **50,000 💰** tiền vốn mua súng.\n"
                        f"⛔ **BẠN BỊ TƯỚC QUYỀN CÔNG DÂN VÀ CẤM DÙNG MỌI LỆNH BOT ĐẾN: <t:{int(jail_time.timestamp())}:R>**!", 
            color=discord.Color.red()
        )
        embed_lose.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed_lose)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    """Đào vàng có GIF"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_id in work_cooldowns:
        time_diff = (now - work_cooldowns[user_id]).total_seconds()
        if time_diff < 30:
            time_left = int(30 - time_diff)
            embed_err = discord.Embed(description=f"⏳ Tay mỏi nhừ rồi sếp! Nghỉ {time_left}s nữa hẵng cuốc tiếp.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)
    
    if "Cuốc Chim ⛏️" not in user_data.get("assets", []):
        if user_data.get("money", 0) < 5000: 
            embed_err = discord.Embed(description="⚠️ Bạn không có Cuốc Chim, mà tiền ví cũng không đủ **5,000 💰** để mua luôn! Hãy đi cày thêm.", color=discord.Color.red())
            return await ctx.reply(embed=embed_err, mention_author=False)
        
        user_data["money"] -= 5000
        user_data["assets"].append("Cuốc Chim ⛏️")
        
        embed_buy = discord.Embed(description="🛒 Đã tự động trừ 5k để mua **Cuốc Chim ⛏️** từ cửa hàng và bắt đầu đào!", color=discord.Color.blue())
        await ctx.send(embed=embed_buy)
    
    work_cooldowns[user_id] = now
    
    embed_start = discord.Embed(description="⛏️ Cạch... Cạch... Bạn đang vung cuốc đập đá ở hầm mỏ âm u...", color=discord.Color.dark_grey())
    msg = await ctx.send(embed=embed_start)
    await asyncio.sleep(2)
    
    roll = random.randint(1, 100)
    if roll <= 40: 
        result_name = "Cục Đá Vô Dụng 🪨"
        value = 0
    elif roll <= 70: 
        result_name = "Mảnh Sắt Vụn 🔩"
        value = random.randint(1000, 3000)
    elif roll <= 90: 
        result_name = "Thỏi Vàng Ròng 🥇"
        value = random.randint(8000, 15000)
    elif roll <= 98: 
        result_name = "Viên Kim Cương To Chà Bá 💎"
        value = random.randint(50000, 100000)
    else: 
        penalty = int(user_data["money"] * 0.1) if user_data["money"] > 0 else 0
        user_data["money"] -= penalty
        save_user(user_id)
        
        embed_lose = discord.Embed(
            description=f"💥 **BÙMMMMM!** Bạn vô tình đào trúng quả bom chưa nổ thời chiến!\nBệnh viện đã thu viện phí **{penalty:,} 💰** của bạn!", 
            color=discord.Color.red()
        )
        return await msg.edit(embed=embed_lose)

    user_data["money"] += value
    save_user(user_id)
    
    embed_color = discord.Color.green() if value > 0 else discord.Color.light_grey()
    embed_win = discord.Embed(
        description=f"⛏️ Chúc mừng! Bạn đào trúng: **{result_name}**\nĐem ra chợ bán được: **{value:,} 💰**", 
        color=embed_color
    )
    embed_win.set_thumbnail(url=GIF_LINKS["mine"])
    await msg.edit(embed=embed_win)

@bot.command()
async def vietlott(ctx, so: int, amount: str):
    """Xổ số Vietlott tự chọn"""
    if so < 0 or so > 99:
        embed_err = discord.Embed(description="⚠️ Vui lòng chọn 1 con số từ 00 đến 99!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet_amount
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    embed_start = discord.Embed(
        description=f"🎫 Bạn đã mua vé số **{so:02d}** với giá **{bet_amount:,} 💰**.\n\n🎲 Lồng cầu đang quay...", 
        color=discord.Color.blue()
    )
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(3)
    
    ket_qua = random.randint(0, 99)
    
    if so == ket_qua:
        win_amount = bet_amount * 70
        user_data = load_user(user_id) 
        user_data["money"] += win_amount
        save_user(user_id)
        
        win_embed = discord.Embed(
            description=f"🎉 **TRÚNG ĐỘC ĐẮC!** Kết quả xổ số là **{ket_qua:02d}**!\n\nBạn đã trúng gấp 70 lần tiền cược, thu về **{win_amount:,} 💰**!", 
            color=discord.Color.green()
        )
        await msg.edit(embed=win_embed)
    else:
        lose_embed = discord.Embed(
            description=f"💀 **TRẬT LẤT!** Kết quả xổ số là **{ket_qua:02d}**.\n\nChúc bạn may mắn lần sau, tờ vé số đã cắn mất của bạn **{bet_amount:,} 💰**.", 
            color=discord.Color.red()
        )
        await msg.edit(embed=lose_embed)

# =====================================================================
# HỆ THỐNG CASINO VIP CÓ TÍNH NĂNG REPLY TRỰC TIẾP
# =====================================================================
@bot.command()
async def coin(ctx, amount: str):
    """Tung đồng xu có GIF"""
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet_amount
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    embed_start = discord.Embed(
        description=f"🪙 Bạn tung **{bet_amount:,} 💰** lên trời...\n🔄 Đồng xu xoay tít trên không...", 
        color=discord.Color.gold()
    )
    embed_start.set_thumbnail(url=GIF_LINKS["casino"])
    
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(2) 

    is_win = random.choice([True, False])
    user_data = load_user(user_id)
    
    if is_win:
        win_amount = bet_amount * 2
        user_data["money"] += win_amount
        save_user(user_id)
        
        win_embed = discord.Embed(
            description=f"🪙 **ĐỒNG XU NGỬA!**\n🎉 Chúc mừng đại gia húp trọn **{win_amount:,} 💰**!\n💳 Số dư ví hiện tại: **{user_data['money']:,} 💰**", 
            color=discord.Color.green()
        )
        await msg.edit(embed=win_embed)
    else:
        lose_embed = discord.Embed(
            description=f"🪙 **ĐỒNG XU SẤP!**\n💀 Nhờn với nhà cái à! Bay mất **{bet_amount:,} 💰**.\n💳 Số dư ví hiện tại: **{user_data['money']:,} 💰**", 
            color=discord.Color.red()
        )
        await msg.edit(embed=lose_embed)

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    """Lắc tài xỉu 3 xí ngầu"""
    choice = choice.lower()
    if choice not in ["tai", "tài", "xiu", "xỉu"]: 
        embed_err = discord.Embed(description="⚠️ Vui lòng gõ `k taixiu tai <tiền>` hoặc `xiu`.", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet_amount
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    embed_start = discord.Embed(
        title="🎲 LẮC XÍ NGẦU CASINO", 
        description=f"Bạn cược **{bet_amount:,} 💰** vào cửa **{choice.upper()}**.\n\nNhà cái đang lắc... 🫨", 
        color=discord.Color.gold()
    )
    embed_start.set_thumbnail(url=GIF_LINKS["casino"])
    
    msg = await ctx.reply(embed_start, mention_author=False)
    await asyncio.sleep(2.5)
    
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    d3 = random.randint(1, 6)
    total_score = d1 + d2 + d3
    
    result_type = "xiu" if total_score <= 10 else "tai"
    
    result_embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    choice_clean = choice.replace("à", "a").replace("ỉ", "i")
    
    if choice_clean == result_type: 
        if d1 == d2 and d2 == d3: 
            win_amt = bet_amount * 5
            user_data["money"] += win_amt
            result_txt = f"🔥 **BÃO {d1}-{d2}-{d3}!!! ĐẠI THẮNG GẤP 5 LẦN!**\nHúp trọn **{win_amt:,} 💰**!"
        else: 
            win_amt = bet_amount * 2
            user_data["money"] += win_amt
            result_txt = f"✅ **THẮNG RỒI!** Bạn nhận được **{win_amt:,} 💰**!"
            
        result_embed.color = discord.Color.green()
    else: 
        result_txt = f"💀 **CẮNG RĂNG THUA!** Mất trắng **{bet_amount:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    result_embed.description = f"**[ {d1} | {d2} | {d3} ]** (Tổng điểm: {total_score} - Cửa **{result_type.upper()}**)\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    
    await msg.edit(embed=result_embed)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    """Lắc bầu cua tôm cá"""
    valid_choices = {
        "bau": "🥒", "bầu": "🥒", 
        "cua": "🦀", 
        "tom": "🦐", "tôm": "🦐", 
        "ca": "🐟", "cá": "🐟", 
        "ga": "🐓", "gà": "🐓", 
        "huou": "🦌", "hươu": "🦌"
    }
    choice_clean = choice.lower()
    
    if choice_clean not in valid_choices: 
        embed_err = discord.Embed(description="⚠️ Tên con vật sai! Các cửa gồm: `bau, cua, tom, ca, ga, huou`.", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet_amount
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    user_icon = valid_choices[choice_clean]
    
    embed_start = discord.Embed(
        title="🎲 BẦU CUA TÔM CÁ", 
        description=f"Bạn cược **{bet_amount:,} 💰** vào ô **{user_icon}**.\n\nNhà cái đang xóc dĩa... 🫨", 
        color=discord.Color.gold()
    )
    embed_start.set_thumbnail(url=GIF_LINKS["casino"])
    
    msg = await ctx.reply(embed_start, mention_author=False)
    await asyncio.sleep(2.5)
    
    dice_faces = ["🥒", "🦀", "🦐", "🐟", "🐓", "🦌"]
    dice_result = [random.choice(dice_faces) for _ in range(3)]
    
    match_count = dice_result.count(user_icon)
    
    result_embed = discord.Embed(title="🎲 MỞ BÁT KẾT QUẢ BẦU CUA")
    
    if match_count > 0: 
        win_amt = bet_amount + (bet_amount * match_count)
        user_data["money"] += win_amt
        result_txt = f"🎉 **TRÚNG {match_count} Ô!** Nhà cái đền cho bạn **{win_amt:,} 💰**."
        result_embed.color = discord.Color.green()
    else: 
        result_txt = f"💀 **TRẬT LẤT!** Nhà cái hốt trọn **{bet_amount:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    result_embed.description = f"**[ {dice_result[0]} | {dice_result[1]} | {dice_result[2]} ]**\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    
    await msg.edit(embed=result_embed)

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    """Đua thú bằng Animation text"""
    animals = {
        "heo": "🐖", 
        "cho": "🐕", "chó": "🐕", 
        "ngua": "🐎", "ngựa": "🐎", 
        "chuot": "🐀", "chuột": "🐀"
    }
    choice = choice.lower()
    
    if choice not in animals: 
        embed_err = discord.Embed(description="⚠️ Chọn sai con vật! Các cửa cược: `heo`, `cho`, `ngua`, `chuot`.", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet_amount
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    track_length = 20
    positions = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def generate_track_frame():
        frame_text = f"🏇 **ĐƯỜNG ĐUA THÚ MỞ BÁT!**\nBạn cược {bet_amount:,} 💰 vào con {animals[choice]}\n\n"
        for pet, distance in positions.items():
            run_distance = min(distance, track_length)
            space_distance = track_length - run_distance
            frame_text += f"🏁{'~' * run_distance}{pet}{' ' * space_distance}⛩️\n"
        return frame_text

    msg = await ctx.reply(generate_track_frame(), mention_author=False)
    winner = None
    
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in positions:
            positions[pet] += random.randint(2, 6) 
            if positions[pet] >= track_length and winner is None: 
                winner = pet
                
        await msg.edit(content=generate_track_frame())
        if winner: break
        
    if not winner:
        winner = max(positions, key=positions.get)
        positions[winner] = track_length
        await msg.edit(content=generate_track_frame())
        
    user_data = load_user(user_id)
    if animals[choice] == winner:
        user_data["money"] += bet_amount * 3
        final_text = f"\n🏆 **{winner} ĐÃ VỀ NHẤT!** Quá đỉnh, ăn được gấp 3 lần tiền cược: **{bet_amount * 3:,} 💰**!"
    else:
        final_text = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} của bạn xịt rồi. Mất sạch **{bet_amount:,} 💰**."
        
    save_user(user_id)
    await msg.edit(content=generate_track_frame() + final_text)

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    """Lệnh quay xèng Nổ Hũ"""
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet_amount
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    slots_result = [random.choice(items) for _ in range(3)]
    
    embed = discord.Embed(title="🎰 MÁY XÈNG NỔ HŨ 🎰", color=discord.Color.gold())
    embed.set_thumbnail(url=GIF_LINKS["casino"])
    
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    for _ in range(3):
        embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Máy đang quay tít mù..."
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        
    for _ in range(2):
        embed.description = f"**[ {slots_result[0]} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đã chốt ô đầu tiên..."
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        
    for _ in range(2):
        embed.description = f"**[ {slots_result[0]} | {slots_result[1]} | {random.choice(items)} ]**\n\n🔄 Nín thở chờ ô cuối..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
        
    if slots_result[0] == slots_result[1] and slots_result[1] == slots_result[2]:
        if slots_result[0] == "👑": 
            win_amt = bet_amount * 50
        elif slots_result[0] == "💎": 
            win_amt = bet_amount * 20
        else: 
            win_amt = bet_amount * 10
            
        result_text = f"🔥 **JACKPOT!!! ĐẠI NỔ HŨ!** Trúng 3 ô {slots_result[0]}\nBạn húp trọn **{win_amt:,} 💰**!"
        user_data["money"] += win_amt
    elif slots_result[0] == slots_result[1] or slots_result[1] == slots_result[2] or slots_result[0] == slots_result[2]:
        win_amt = bet_amount * 2
        result_text = f"🎉 **THẮNG NHỎ!** Trúng 2 ô giống nhau.\nBạn nhận được **{win_amt:,} 💰**."
        user_data["money"] += win_amt
    else:
        result_text = f"💀 **TOANG!** Cờ bạc là bác thằng bần.\nMất sạch **{bet_amount:,} 💰**."
        
    save_user(user_id)
    embed.description = f"**[ {slots_result[0]} | {slots_result[1]} | {slots_result[2]} ]**\n\n{result_text}"
    embed.set_footer(text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)

@bot.command()
async def gacha(ctx):
    """Mở trứng thú cưng (Gacha)"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    cost = 30000
    
    if user_data.get("money", 0) < cost: 
        embed_err = discord.Embed(description="⚠️ Trứng Gacha cao cấp giá 30k lận. Đi cày thêm đi sếp!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data["money"] -= cost
    save_user(user_id)
    
    embed_start = discord.Embed(title="🥚 ĐẬP TRỨNG GACHA", description=f"{ctx.author.mention} đang vung búa đập vỡ lớp vỏ quả trứng...", color=discord.Color.orange())
    embed_start.set_image(url=GIF_LINKS["gacha"])
    
    msg = await ctx.reply(embed_start, mention_author=False)
    await asyncio.sleep(1.5)
    
    embed_start.description = "⚡ Vỏ trứng nứt rạn... Một ánh sáng chói lóa phát ra..."
    await msg.edit(embed=embed_start)
    await asyncio.sleep(1.5)
    
    roll = random.uniform(0, 100)
    if roll <= 0.5: 
        rarity = "mythic"
        title_text = "🌌 THẦN THOẠI"
        embed_color = discord.Color.dark_purple()
    elif roll <= 3.0: 
        rarity = "legendary"
        title_text = "👑 HUYỀN THOẠI"
        embed_color = discord.Color.gold()
    elif roll <= 10.0: 
        rarity = "epic"
        title_text = "🔮 SỬ THI"
        embed_color = discord.Color.magenta()
    elif roll <= 30.0: 
        rarity = "rare"
        title_text = "💎 HIẾM"
        embed_color = discord.Color.blue()
    else: 
        rarity = "common"
        title_text = "🪵 PHỔ THÔNG"
        embed_color = discord.Color.light_grey()
    
    pet_name = random.choice(PET_RATES[rarity]["pool"])
    
    current_pet_count = user_data["pets"].get(pet_name, 0)
    user_data["pets"][pet_name] = current_pet_count + 1
    save_user(user_id)
    
    embed_result = discord.Embed(
        title=f"🎉 NỔ TRỨNG: PHẨM CHẤT {title_text}!", 
        description=f"Tuyệt vời! Ánh sáng tan đi, bạn nhận được một bé: **{pet_name}**!", 
        color=embed_color
    )
    embed_result.set_footer(text="Gõ lệnh 'k tuido' để ngắm, lệnh 'k ban' để bán.", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed_result)
    # =====================================================================
# HỆ THỐNG CHỨNG KHOÁN (BỔ SUNG LỆNH IPO CÔNG TY LÊN SÀN)
# =====================================================================
@chungkhoan.command()
async def ipo(ctx):
    """Lệnh đưa công ty lên sàn chứng khoán"""
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    
    if not comp_id:
        embed_err = discord.Embed(description="⚠️ Bạn chưa gia nhập công ty nào cả!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss":
        embed_err = discord.Embed(description="⚠️ Chỉ Chủ Tịch mới có quyền quyết định đưa công ty lên sàn chứng khoán!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if comp.get("is_ipo"):
        embed_err = discord.Embed(description="⚠️ Công ty của bạn đã được niêm yết trên sàn chứng khoán rồi!", color=discord.Color.orange())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if comp["treasury"] < 50000000:
        embed_err = discord.Embed(description="⚠️ Điều kiện niêm yết: Quỹ công ty phải đạt tối thiểu **50,000,000 💰**.\nHãy kêu gọi cổ đông đóng góp thêm!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    # Kích hoạt trạng thái IPO
    comp["is_ipo"] = True
    save_company(comp_id)
    
    mã_ck = comp["name"][:4].upper()
    embed_success = discord.Embed(
        title="📈 CHÀO SÀN CHỨNG KHOÁN THÀNH CÔNG", 
        description=f"Chúc mừng tập đoàn **{comp['name']}** đã chính thức IPO và được niêm yết trên Sàn Chứng Khoán Phố Wall!\n\n"
                    f"Mã cổ phiếu: **{mã_ck}**\n"
                    f"Từ giờ phút này, giá trị cổ phiếu sẽ biến động dựa trên số tiền trong Quỹ Công Ty và biến động thị trường.", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)
# =====================================================================
# HỆ THỐNG LỆNH NGÂN HÀNG TRUNG ƯƠNG
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    """Dashboard quản lý ngân hàng trung ương"""
    user_data = load_user(ctx.author.id)
    bank_balance = user_data.get("bank", 0)
    wallet_balance = user_data.get("money", 0)
    
    embed = discord.Embed(
        title="🏦 NGÂN HÀNG TRUNG ƯƠNG SERVER", 
        description="Gửi tiền an toàn tuyệt đối. Tiền nằm trong ngân hàng sẽ không bao giờ bị mất do Casino, bị trộm hay bị đánh thuế!\n\n"
                    "📥 `k bank gui <số tiền / all>`: Gửi tiền mặt vào két sắt\n"
                    "📤 `k bank rut <số tiền / all>`: Rút tiền từ két sắt ra ví", 
        color=discord.Color.blue()
    )
    embed.add_field(name="💳 Ví tiền mặt (Wallet)", value=f"**{wallet_balance:,} 💰**", inline=True)
    embed.add_field(name="🏦 Số dư Két sắt (Bank)", value=f"**{bank_balance:,} 💰**", inline=True)
    embed.set_thumbnail(url=GIF_LINKS.get("bank", ""))
    
    await ctx.reply(embed=embed, mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    """Lệnh gửi tiền vào ngân hàng"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    try: 
        if amount.lower() == "all":
            deposit_amount = user_data["money"]
        else:
            deposit_amount = int(amount)
    except ValueError: 
        embed_err = discord.Embed(description="⚠️ Vui lòng nhập đúng số tiền hoặc chữ `all`!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
    
    if deposit_amount <= 0 or deposit_amount > user_data["money"]: 
        embed_err = discord.Embed(description="⚠️ Số tiền trong ví không đủ để gửi!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data["money"] -= deposit_amount
    user_data["bank"] = user_data.get("bank", 0) + deposit_amount
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Nhân viên ngân hàng đã đóng gói và đưa **{deposit_amount:,} 💰** của bạn vào két sắt an toàn tuyệt đối!", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    """Lệnh rút tiền từ ngân hàng ra ví"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    bank_balance = user_data.get("bank", 0)
    
    try: 
        if amount.lower() == "all":
            withdraw_amount = bank_balance
        else:
            withdraw_amount = int(amount)
    except ValueError: 
        embed_err = discord.Embed(description="⚠️ Vui lòng nhập đúng số tiền hoặc chữ `all`!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
    
    if withdraw_amount <= 0 or withdraw_amount > bank_balance: 
        embed_err = discord.Embed(description="⚠️ Số dư trong ngân hàng của bạn không đủ!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data["bank"] -= withdraw_amount
    user_data["money"] += withdraw_amount
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Bạn đã rút thành công **{withdraw_amount:,} 💰** từ két sắt mang ra ngoài ví để ăn chơi!", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

# =====================================================================
# HỆ THỐNG LỆNH KẾT HÔN VÀ LY HÔN
# =====================================================================
@bot.command()
async def marry(ctx, member: discord.Member):
    """Lệnh cầu hôn tốn 1 triệu"""
    player_1_data = load_user(ctx.author.id)
    player_2_data = load_user(member.id)
    
    if ctx.author.id == member.id or member.bot: 
        return await ctx.reply("Lỗi: Bạn không thể tự kết hôn với bản thân hoặc với Bot!")
        
    if player_1_data.get("spouse"): 
        return await ctx.reply("Lỗi: Bạn đã có vợ/chồng rồi! Tham lam định lập phòng nhì à?")
        
    if player_2_data.get("spouse"): 
        return await ctx.reply(f"Lỗi: Xin lỗi, {member.name} là hoa đã có chủ, đập chậu cướp hoa không được đâu!")
        
    if player_1_data.get("money", 0) < 1000000: 
        embed_poor = discord.Embed(
            description="⚠️ Nhẫn cưới kim cương giá **1,000,000 💰**. Tiền trong ví bạn không đủ cưới vợ đâu, lo cày tiền trước đi!", 
            color=discord.Color.red()
        )
        return await ctx.reply(embed=embed_poor)
    
    embed_offer = discord.Embed(
        title="💍 LỜI CẦU HÔN TỪ ĐẠI GIA", 
        description=f"{member.mention} ơi! Đại gia {ctx.author.mention} mang sính lễ 1 củ đang quỳ gối cầu hôn bạn kìa!\n\nBạn có đồng ý sánh bước trăm năm cùng người ấy không?", 
        color=discord.Color.pink()
    )
    await ctx.send(embed=embed_offer, view=MarryAccept(ctx.author, member))

@bot.command()
async def divorce(ctx):
    """Lệnh ly hôn"""
    player_1_id = str(ctx.author.id)
    player_1_data = load_user(player_1_id)
    
    if not player_1_data.get("spouse"): 
        return await ctx.reply("Bạn đang ế chỏng chơ mà ly hôn với ma à?")
    
    player_2_id = player_1_data["spouse"]
    player_2_data = load_user(player_2_id)
    
    player_1_data["spouse"] = None
    player_2_data["spouse"] = None
    
    save_user(player_1_id)
    save_user(player_2_id)
    
    embed_divorce = discord.Embed(
        description=f"💔 Tình yêu như bát bún thiu... Bạn đã nộp đơn ly hôn ra tòa. Mọi giấy tờ đã được giải quyết, từ nay đường ai nấy đi!", 
        color=discord.Color.dark_grey()
    )
    await ctx.reply(embed=embed_divorce, mention_author=False)

# =====================================================================
# HỆ THỐNG LỆNH QUẢN LÝ CÔNG TY ĐẦY ĐỦ
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    """Dashboard trung tâm quản lý công ty"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")

    if not comp_id:
        embed_none = discord.Embed(
            title="🏢 SÀN GIAO DỊCH DOANH NGHIỆP", 
            description="Bạn hiện đang là kẻ lang thang thất nghiệp.\nĐể thành lập công ty, gõ:\n`k cty tao <tên công ty>` (Phí thành lập: 500,000 💰)", 
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed_none)
    
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None
        save_user(user_id)
        return await ctx.send("Công ty của bạn đã phá sản từ trước rồi! Hãy dọn dẹp đống đổ nát và lập công ty mới.")
        
    my_role = comp["members"].get(user_id, "nhanvien")
    role_name = comp["roles"].get(my_role, my_role)
    
    embed_dashboard = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed_dashboard.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed_dashboard.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed_dashboard.add_field(name="Chức vụ của bạn", value=f"**{role_name}**", inline=False)
    
    cmds = "`k cty gop <tiền>`: Đóng góp tiền túi vào quỹ công ty\n`k cty thulai`: Nhận lãi suất ngân hàng mỗi ngày\n`k cty roi`: Nộp đơn từ chức nghỉ việc"
    
    if my_role in ["boss", "quanly"]:
        cmds += "\n\n**Quyền Quản Lý:**\n`k cty tuyen @user`: Tuyển dụng nhân viên\n`k cty duoi @user`: Sa thải nhân viên"
        
    if my_role == "boss":
        cmds += "\n\n**Quyền Chủ Tịch:**\n`k cty luong <tiền>`: Rút quỹ phát lương cho toàn Cty\n`k cty chucvu @user <quanly/nhanvien>`: Set role\n`k cty doitenchuc <boss/quanly/nhanvien> <Tên>`: Đổi tên hiển thị"
        
    embed_dashboard.add_field(name="Bảng Lệnh Công Ty", value=cmds, inline=False)
    await ctx.send(embed=embed_dashboard)

@cty.command()
async def tao(ctx, *, name: str):
    """Lệnh thành lập công ty tốn 500k"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("company"): 
        return await ctx.reply("Bạn đã ký hợp đồng với một công ty rồi! Hãy thoát ra trước khi tạo mới.", mention_author=False)
        
    if user_data.get("money", 0) < 500000: 
        return await ctx.reply("⚠️ Phí đăng ký doanh nghiệp là **500,000 💰**. Cày thêm đi sếp!", mention_author=False)
    
    user_data["money"] -= 500000
    user_data["company"] = user_id
    
    new_comp = {
        "_id": user_id, 
        "name": name, 
        "treasury": 0, 
        "members": {user_id: "boss"}, 
        "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, 
        "last_interest": "2000-01-01 00:00:00",
        "is_ipo": False
    }
    
    COMPANY_CACHE[user_id] = new_comp
    save_company(user_id)
    save_user(user_id)
    
    embed_success = discord.Embed(
        title="🏢 KHAI TRƯƠNG HỒNG PHÁT", 
        description=f"Cắt băng khánh thành! Chúc mừng sếp {ctx.author.mention} đã thành lập doanh nghiệp **{name}**!\n\nGõ `k cty` để mở bảng điều khiển và bắt đầu tuyển dụng.", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed_success)

@cty.command()
async def tuyen(ctx, member: discord.Member):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.reply("Bạn có công ty đâu mà đòi tuyển nhân sự!", mention_author=False)
        
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: 
        return await ctx.reply("Quyền hạn không đủ! Chỉ Giám đốc và Chủ tịch mới được tuyển người!", mention_author=False)
        
    if load_user(member.id).get("company"): 
        return await ctx.reply("Người này đang làm việc cho công ty khác rồi.", mention_author=False)
    
    view = CompanyInviteView(comp_id, comp["name"], member)
    await ctx.send(f"🏢 {member.mention}, bạn có một lá thư mời nhận việc tại **{comp['name']}**! Bấm nút bên dưới để quyết định.", view=view)

@cty.command()
async def duoi(ctx, member: discord.Member):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: 
        return await ctx.reply("Bạn không có quyền sa thải nhân sự!", mention_author=False)
        
    target_id = str(member.id)
    if target_id not in comp["members"]: 
        return await ctx.reply("Lỗi: Người này không có mặt trong danh sách công ty!", mention_author=False)
        
    if comp["members"][target_id] == "boss": 
        return await ctx.reply("Tính làm phản hả? Không ai đuổi được sếp tổng đâu!", mention_author=False)
    
    del comp["members"][target_id]
    target_data = load_user(target_id)
    target_data["company"] = None
    
    save_company(comp_id)
    save_user(target_id)
    
    await ctx.reply(f"👢 Đóng mộc sa thải! Bộ phận Nhân sự đã đuổi cổ {member.mention} ra khỏi công ty!", mention_author=False)

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.reply("Bạn chưa gia nhập công ty nào để cống hiến.", mention_author=False)
        
    if user_data.get("money", 0) < amount: 
        return await ctx.reply("Trong ví làm gì có đủ tiền mà bấm góp!", mention_author=False)
    
    comp = load_company(comp_id)
    user_data["money"] -= amount
    comp["treasury"] += amount
    
    save_user(user_id)
    save_company(comp_id)
    
    await ctx.reply(f"💰 Tuyệt vời! Bạn đã cống hiến **{amount:,} 💰** vào quỹ đen của công ty. \nTổng quỹ hiện tại: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def thulai(ctx):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": 
        return await ctx.reply("Chỉ đích thân Chủ tịch mới được ký giấy thu lãi ngân hàng!", mention_author=False)
    
    now = datetime.now()
    last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    
    if now - last < timedelta(days=1):
        return await ctx.reply("⏳ Kế toán chưa chốt sổ! Mỗi ngày công ty chỉ được thu lãi từ Ngân hàng 1 lần.", mention_author=False)
        
    # Tính lãi 5%, giới hạn tối đa 100k
    lai_nhan_duoc = int(comp["treasury"] * 0.05) 
    if lai_nhan_duoc > 100000: 
        lai_nhan_duoc = 100000 
    
    comp["treasury"] += lai_nhan_duoc
    comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    
    await ctx.reply(f"📈 Chốt sổ kinh doanh! Công ty đã nhận được **{lai_nhan_duoc:,} 💰** tiền lãi hôm nay. \nTổng quỹ tăng lên: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def luong(ctx, amount: int):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": 
        return await ctx.reply("Lỗi: Chỉ Chủ tịch mới được quyền ký quỹ phát lương!", mention_author=False)
        
    mem_count = len(comp["members"])
    total_cost = amount * mem_count
    
    if total_cost > comp["treasury"]: 
        return await ctx.reply(f"Quỹ không đủ! Bạn cần tới **{total_cost:,} 💰** để phát đồng đều cho {mem_count} người.", mention_author=False)
    
    comp["treasury"] -= total_cost
    for m_id in list(comp["members"].keys()):
        m_data = load_user(m_id)
        m_data["money"] += amount
        save_user(m_id)
        
    save_company(comp_id)
    
    embed_salary = discord.Embed(
        description=f"💸 Sếp tổng đã hào phóng phát **{amount:,} 💰** lương cho mỗi nhân viên!\nTổng tiền quỹ bị trừ: **{total_cost:,} 💰**", 
        color=discord.Color.green()
    )
    await ctx.send(embed_salary)

@cty.command()
async def chucvu(ctx, member: discord.Member, role: str):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": 
        return await ctx.reply("Chỉ Chủ tịch mới được set chức vụ!", mention_author=False)
        
    target_id = str(member.id)
    if target_id not in comp["members"]: 
        return await ctx.reply("Người này không thuộc công ty.", mention_author=False)
        
    if target_id == user_id: 
        return await ctx.reply("Không thể tự đổi chức của bản thân, sếp vẫn là sếp!", mention_author=False)
        
    if role not in ["quanly", "nhanvien"]: 
        return await ctx.reply("Chức vụ bắt buộc phải là `quanly` hoặc `nhanvien`.", mention_author=False)
    
    comp["members"][target_id] = role
    save_company(comp_id)
    await ctx.reply(f"✅ Đã quyết định thăng/giáng chức {member.mention} thành **{comp['roles'][role]}**.", mention_author=False)

@cty.command()
async def doitenchuc(ctx, role: str, *, name: str):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": 
        return await ctx.reply("Chỉ Chủ tịch mới được quyền đổi tên chức vụ!", mention_author=False)
        
    if role not in ["boss", "quanly", "nhanvien"]: 
        return await ctx.reply("Hệ phái cần đổi phải là `boss`, `quanly` hoặc `nhanvien`.", mention_author=False)
    
    comp["roles"][role] = name
    save_company(comp_id)
    await ctx.reply(f"✅ Đã đổi tên hệ phái `{role}` thành **{name}**.", mention_author=False)

@cty.command()
async def roi(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.reply("Bạn chưa gia nhập công ty nào cả!", mention_author=False)
        
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None
        save_user(user_id)
        return await ctx.reply("Công ty của bạn đã không còn tồn tại trên hệ thống.", mention_author=False)
    
    my_role = comp["members"].get(user_id)
    
    if my_role == "boss":
        COMPANY_CACHE.pop(comp_id, None)
        companies_col.delete_one({"_id": comp_id})
        
        for m_id in list(comp["members"].keys()):
            m_data = load_user(m_id)
            m_data["company"] = None
            save_user(m_id)
            
        embed_bankrupt = discord.Embed(
            description="🏢 Bão tố ập tới! Chủ tịch đã bỏ trốn, công ty tuyên bố **PHÁ SẢN** và giải tán toàn bộ nhân sự!", 
            color=discord.Color.red()
        )
        embed_bankrupt.set_image(url=GIF_LINKS.get("bankrupt", "https://media.giphy.com/media/3o6UB5RrlQuMfZp82Y/giphy.gif"))
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
    else:
        if user_id in comp["members"]:
            del comp["members"][user_id]
            
        user_data["company"] = None
        save_user(user_id)
        save_company(comp_id)
        
        embed_leave = discord.Embed(
            description="🎒 Bạn đã nộp đơn xin từ chức, thu dọn hành lý rời khỏi công ty.", 
            color=discord.Color.dark_grey()
        )
        await ctx.reply(embed=embed_leave, mention_author=False)

@bot.command()
async def daichien(ctx, member: discord.Member = None, tactic: str = None):
    """Đại chiến thương trường cướp quỹ công ty"""
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    
    if not member or not tactic or tactic.lower() not in ["hack", "phot", "giangho"]:
        embed_help = discord.Embed(
            title="⚔️ ĐẠI CHIẾN THƯƠNG TRƯỜNG (SÁNG TẠO)", 
            description="Dùng trí tuệ và thủ đoạn để hạ gục công ty đối thủ!\nCách dùng: `k daichien @user <chiến_thuật>`", 
            color=discord.Color.red()
        )
        embed_help.add_field(name="1. hack (Tấn công mạng)", value="Tỉ lệ thắng: **30%**\nPhần thưởng: Cướp **10%** quỹ đối thủ.\nThất bại: Đền bù **5%** quỹ của mình.", inline=False)
        embed_help.add_field(name="2. phot (Thuê KOL bóc phốt)", value="Tỉ lệ thắng: **50%**\nPhần thưởng: Cướp **5%** quỹ đối thủ.\nThất bại: Đền bù **2%** quỹ của mình.", inline=False)
        embed_help.add_field(name="3. giangho (Vũ lực)", value="Tỉ lệ thắng: **70%**\nPhần thưởng: Cướp **2%** quỹ đối thủ.\nThất bại: Đền bù **1%** quỹ của mình.", inline=False)
        embed_help.set_image(url=GIF_LINKS.get("fight", ""))
        return await ctx.send(embed=embed_help)
        
    target_id = str(member.id)
    target_comp_id = load_user(target_id).get("company")
    
    if user_id == target_id or member.bot: 
        return await ctx.reply("⚠️ Đánh với ai chứ đừng tự kỷ hoặc đi đánh Bot.", mention_author=False)
        
    if not comp_id or not target_comp_id: 
        return await ctx.reply("⚠️ Cả 2 đều phải ở trong công ty thì mới được phép PK!", mention_author=False)
        
    if comp_id == target_comp_id: 
        return await ctx.reply("⚠️ Cùng một công ty, anh em tương tàn làm gì!", mention_author=False)
    
    now = datetime.now()
    if comp_id in cty_cooldowns and (now - cty_cooldowns[comp_id]).total_seconds() < 3600:
        return await ctx.reply(embed=discord.Embed(description="⏳ Công ty bạn vừa xuất quân rồi! Phải đợi 1 tiếng để hồi phục binh lực.", color=discord.Color.orange()), mention_author=False)
    
    comp1 = load_company(comp_id)
    comp2 = load_company(target_comp_id)
    
    if comp2["treasury"] < 10000: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Quỹ công ty đối thủ quá nghèo (<10k), không đáng để tốn sức cất quân đi đánh!", color=discord.Color.red()), mention_author=False)
    
    cty_cooldowns[comp_id] = now
    tactic = tactic.lower()
    
    if tactic == "hack": 
        win_rate, win_pct, lose_pct, name = 30, 0.10, 0.05, "TẤN CÔNG MẠNG"
    elif tactic == "phot": 
        win_rate, win_pct, lose_pct, name = 50, 0.05, 0.02, "THUÊ BÁO CHÍ BÓC PHỐT"
    else: 
        win_rate, win_pct, lose_pct, name = 70, 0.02, 0.01, "ĐƯA GIANG HỒ ĐẾN ĐẬP PHÁ"
    
    embed_start = discord.Embed(description=f"⚔️ **{comp1['name']}** đang dùng chiến thuật **{name}** lên đầu **{comp2['name']}**...", color=discord.Color.dark_grey())
    msg = await ctx.send(embed=embed_start)
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= win_rate:
        steal = int(comp2["treasury"] * win_pct)
        comp1["treasury"] += steal
        comp2["treasury"] -= steal
        save_company(comp_id)
        save_company(target_comp_id)
        
        win_embed = discord.Embed(
            description=f"🔥 **ĐẠI THẮNG!** Binh pháp quá đỉnh!\n💰 Phe bạn đã cướp được **{steal:,} 💰** mang về quỹ công ty!", 
            color=discord.Color.green()
        )
        win_embed.set_image(url=GIF_LINKS.get("fight", ""))
        await msg.edit(embed=win_embed)
    else:
        fine = int(comp1["treasury"] * lose_pct)
        comp1["treasury"] -= fine
        comp2["treasury"] += fine
        save_company(comp_id)
        save_company(target_comp_id)
        
        lose_embed = discord.Embed(
            description=f"💀 **THẤT BẠI NHỤC NHÃ!** Đối thủ đã phòng bị!\nBạn bị kiện ngược và công ty phải đền bù **{fine:,} 💰** cho quỹ đối thủ.", 
            color=discord.Color.red()
        )
        await msg.edit(embed=lose_embed)
# =====================================================================
# HỆ THỐNG LỆNH CƠ BẢN, NHẬP VAI, TOP VÀ CÀY CUỐC
# =====================================================================
@bot.command()
async def help(ctx):
    """Bảng hướng dẫn hệ thống lệnh của Bot"""
    embed = discord.Embed(
        title="📚 HỆ THỐNG LỆNH BOT UPDATE 2026", 
        description="Tiền tố gọi lệnh là `k` hoặc `K` (Có dấu cách hoặc viết liền đều được, VD: `k rank` hoặc `krank`).", 
        color=discord.Color.blurple()
    )
    if bot.user.avatar: 
        embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(name="🏦 KINH TẾ VIP", value="`k rank` • Thẻ Căn Cước\n`k bank` • Gửi/Rút Két sắt\n`k marry @user` • Kết hôn\n`k cuahang`, `k choden` • Mua bán\n`k daily`, `k lixi`, `k give`, `k top`", inline=False)
    embed.add_field(name="🏢 CÔNG TY & CHỨNG KHOÁN", value="`k cty tao <tên>` • Lập cty 500k\n`k cty` • Mở Dashboard Cty\n`k daichien @user <hack/phot/giangho>`\n`k ck` • Sàn chứng khoán", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <tài/xỉu> <tiền>`\n`k baucua <con vật> <tiền>`\n`k duathu <con vật> <tiền>`\n`k nohu <tiền>`, `k vietlott <số> <tiền>`", inline=False)
    embed.add_field(name="⛏️ NHẬP VAI SINH TỒN", value="`k cuopnganhang` • Cướp nhà băng\n`k daovang` (hoặc `k daomo`) • Nghề đào mỏ\n`k nhansinh` • Mô phỏng cuộc sống\n`k thamhiem`, `k gacha`, `k phai`", inline=False)
    
    embed.set_footer(text="Chúc các dân chơi sớm mua được Đảo Tư Nhân!", icon_url=ctx.author.display_avatar.url)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def rank(ctx):
    """Hiển thị Thẻ Căn Cước Công Dân"""
    user_data = load_user(ctx.author.id)
    level = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    tien = user_data.get("money", 0)
    
    embed_color = discord.Color.gold() if tien > 1000000 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 CĂN CƯỚC CÔNG DÂN: {ctx.author.name.upper()}", color=embed_color)
    
    embed.set_thumbnail(url=GIF_LINKS["rank"])
    
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {level}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    
    if user_data.get("spouse"):
        try:
            spouse_user = await bot.fetch_user(int(user_data["spouse"]))
            spouse_name = spouse_user.name
        except Exception: 
            spouse_name = "Người thương ẩn danh"
        embed.add_field(name="💍 Tình Trạng Hôn Nhân", value=f"**Đã kết hôn với {spouse_name}**", inline=False)
        
    if user_data.get("company"): 
        comp_info = load_company(user_data['company'])
        if comp_info:
            ipo_status = " (Đã lên sàn CK)" if comp_info.get("is_ipo") else ""
            embed.add_field(name="🏢 Doanh Nghiệp", value=f"**{comp_info['name']}**{ipo_status}", inline=False)
            
    if user_data.get("jail_time"): 
        embed.add_field(name="🚨 Trạng Thái Pháp Lý", value="**Đang bóc lịch trong trại giam!**", inline=False)
    
    embed.add_field(name="✨ Tiến Độ Kinh Nghiệm", value=f"`{make_progress_bar(xp, level * 100)}`\n**{xp}/{level * 100} XP**", inline=False)
    
    assets = user_data.get('assets', [])
    embed.set_footer(text=f"BĐS Sở hữu: {', '.join(assets[:2])}..." if assets else "Gia cảnh: Vô Gia Cư", icon_url=ctx.author.display_avatar.url)
    
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def tuido(ctx):
    """Hiển thị kho chứa đồ và thú cưng"""
    user_data = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO BÁU CỦA {ctx.author.name.upper()}", color=discord.Color.dark_purple())
    if ctx.author.avatar: 
        embed.set_thumbnail(url=ctx.author.avatar.url)
    
    assets = user_data.get("assets", [])
    embed.add_field(name="🏠 Tài Sản Cá Nhân", value="Trống không." if not assets else "\n".join([f"🔸 {a}" for a in assets]), inline=False)
    
    pets = user_data.get("pets", {})
    embed.add_field(name="🐾 Trang Trại Thú Cưng", value="Chưa bắt được con nào." if not pets else "\n".join([f"{p} (x{c})" for p, c in pets.items()]), inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx):
    """Bảng xếp hạng tổng tài sản"""
    all_users = list(users_col.find())
    danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
    
    desc = ""
    for index, (uid, tien) in enumerate(danh_sach[:10]):
        user = bot.get_user(int(uid))
        try: 
            if not user: 
                user = await bot.fetch_user(int(uid))
        except Exception: 
            pass
            
        ten = user.name if user else f"Tỷ phú {uid[-4:]}"
        icon = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else f"**#{index+1}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
        
    embed = discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA SERVER", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    """Điểm danh nhận quà mỗi ngày"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("last_daily"):
        last_daily = datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            next_time = int((last_daily + timedelta(days=1)).timestamp())
            embed_err = discord.Embed(description=f"⏳ Tính scam à? Lương tiếp theo nhận vào: <t:{next_time}:R>.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)
    
    user_data["money"] += 1000
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed_success = discord.Embed(
        title="🎁 QUÀ ĐIỂM DANH", 
        description=f"Nhận trợ cấp **1,000 💰** thành công!\n💳 Số dư ví: **{user_data['money']:,} 💰**", 
        color=discord.Color.green()
    )
    embed_success.set_thumbnail(url=GIF_LINKS["daily"])
    await ctx.reply(embed_success, mention_author=False)

@bot.command()
async def lixi(ctx):
    """Bốc lì xì 12h / lần"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("last_lixi"):
        last_lixi = datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S")
        if now - last_lixi < timedelta(hours=12):
            next_time = int((last_lixi + timedelta(hours=12)).timestamp())
            embed_err = discord.Embed(description=f"🧧 Lì xì tiếp theo nhận vào: <t:{next_time}:R>.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)

    tien = random.randint(1000, 8000) 
    user_data["money"] += tien
    user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"🧧 Bạn mở phong bao đỏ và nhận được **{tien:,} 💰**!\n💳 Số dư ví: **{user_data['money']:,} 💰**", 
        color=discord.Color.red()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    """Chuyển tiền cho người khác"""
    nguoi_gui = str(ctx.author.id)
    nguoi_nhan = str(member.id)
    
    gui_data = load_user(nguoi_gui)
    nhan_data = load_user(nguoi_nhan)
    
    if amount <= 0 or gui_data.get("money", 0) < amount or nguoi_gui == nguoi_nhan: 
        embed_err = discord.Embed(description="⚠️ Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển cho mình).", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    gui_data["money"] -= amount
    nhan_data["money"] += amount
    save_user(nguoi_gui)
    save_user(nguoi_nhan)
    
    embed_success = discord.Embed(
        title="💸 CHUYỂN KHOẢN THÀNH CÔNG", 
        description=f"{ctx.author.mention} đã chuyển cho {member.mention} **{amount:,} 💰**!", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed_success)

@bot.command(aliases=['ban', 'sell'])
async def choden(ctx): 
    """Gọi giao diện Chợ Đen để bán đồ"""
    embed = discord.Embed(title="⚖️ CHỢ ĐEN CẦM ĐỒ", description="Đem đồ ra đây cầm cố hoặc bán thú cưng lấy tiền liền tay!", color=discord.Color.dark_orange())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=SellCategoryMenu(ctx.author))

@bot.command(aliases=['shop'])
async def cuahang(ctx): 
    """Gọi giao diện Cửa hàng Đại gia"""
    embed = discord.Embed(title="🏪 ĐẠI SIÊU THỊ TRUNG TÂM", description="Nơi tiêu tiền của những kẻ giàu có!", color=discord.Color.brand_green())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx): 
    """Gọi Menu mua vũ khí đi Thám hiểm Rừng Sâu"""
    embed = discord.Embed(
        title="🛒 TRẠM TIẾP TẾ RỪNG SÂU", 
        description="Khu rừng rậm rạp đầy nguy hiểm nhưng cũng cất giấu đầy rương vàng kho báu.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA VŨ KHÍ TỰ VỆ TRƯỚC KHI VÀO RỪNG** 👇", 
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, view=KhungRungShopView(ctx.author, session_profit=0))

@bot.command()
async def phai(ctx):
    """Trạm cắm trại AFK nhặt kinh nghiệm và tiền"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    exp_end_str = user_data.get("exp_end")
    
    if exp_end_str:
        now = datetime.now()
        end_time = datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S")
        
        if now >= end_time:
            reward = user_data.get("exp_reward", 500)
            user_data["money"] += reward
            del user_data["exp_end"]
            del user_data["exp_reward"]
            save_user(user_id)
            
            embed_success = discord.Embed(
                title="🎉 TRỞ VỀ AN TOÀN!", 
                description=f"Bạn đã hoàn thành chuyến dã ngoại và thu hoạch được **{reward:,} 💰**!", 
                color=discord.Color.gold()
            )
            return await ctx.reply(embed=embed_success, mention_author=False)
        else:
            time_left = end_time - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed_wait = discord.Embed(
                description=f"⏳ Đang cày cuốc sấp mặt ở nơi hoang dã! Hãy chờ thêm **{hours} giờ {minutes} phút** nữa nhé.", 
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed_wait, mention_author=False)
            
    embed_start = discord.Embed(
        title="⛺ TRẠM THÁM HIỂM AFK", 
        description="Gửi nhân vật đi treo máy dã ngoại và nhặt tiền lúc trở về!\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ CHỌN KHU VỰC CẮM TRẠI** 👇", 
        color=discord.Color.dark_green()
    )
    await ctx.send(embed=embed_start, view=ExpView(ctx.author))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    """Game Nhân Sinh Mô Phỏng Lựa Chọn Đa Vũ Trụ"""
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    if user_id in dang_choi_nhansinh: 
        embed_err = discord.Embed(description="⏳ Bạn đang vướng bận trong một kiếp luân hồi dở dang rồi, hoàn thành kiếp trước đi đã!", color=discord.Color.orange())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if user_id in nhansinh_cooldowns:
        time_diff = (now - nhansinh_cooldowns[user_id]).total_seconds()
        if time_diff < 5: 
            embed_err = discord.Embed(description="⏳ Từ từ đã, đầu thai liên tục Diêm Vương mắng cho đấy!", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)

    user_data = load_user(user_id)
    if user_data.get("money", 0) < 100: 
        embed_err = discord.Embed(description="⚠️ Vé luân hồi đi chuyến tàu địa phủ giá **100 💰**. Túi rỗng thì không có cửa đầu thai đâu, ra đê!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)

    user_data["money"] -= 100
    nhansinh_cooldowns[user_id] = now
    dang_choi_nhansinh.append(user_id)
    save_user(user_id)

    initial_stats = {"may_man": random.randint(1, 10)}
    view = NhanSinhGameView(ctx.author, initial_stats)
    
    embed = discord.Embed(
        title="🌀 MÔ PHỎNG NHÂN SINH (HARDCORE)", 
        description=f"Ký chủ luân hồi: {ctx.author.mention}", 
        color=discord.Color.teal()
    )
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{initial_stats['may_man']}/10** *(Được buff thêm {initial_stats['may_man']*1.5}% Tỉ lệ thành công)*", inline=False)
    embed.add_field(name="📜 Hành trình cuộc đời", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Ngã rẽ quyết định tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    
    await ctx.reply(embed=embed, view=view, mention_author=False)
# =====================================================================
# [MODULE MỚI] KALLEN FANTASY - BẢN SAO HONKAI IMPACT 3
# =====================================================================
# Hệ thống Data, Kịch bản, Chỉ số nhân vật và Vết thánh

KALLEN_BATTLESUITS = {
    "imayoh": {
        "id": "imayoh",
        "name": "Ritual Imayoh (MECH)",
        "type": "MECH",
        "rarity": "A",
        "base_hp": 1200,
        "base_atk": 250,
        "base_def": 150,
        "base_crt": 30,
        "skill_basic_name": "Súng Kata",
        "skill_basic_dmg": 1.2,
        "skill_combo_name": "Mưa Đạn Động Năng",
        "skill_combo_dmg": 2.5,
        "skill_ult_name": "Khúc Ca Elysia",
        "skill_ult_dmg": 6.0,
        "ult_sp_cost": 80,
        "evade_name": "Vết Nứt Không Gian",
        "emoji": "🔫"
    },
    "sundenjager": {
        "id": "sundenjager",
        "name": "Sündenjäger (MECH)",
        "type": "MECH",
        "rarity": "A",
        "base_hp": 1400,
        "base_atk": 220,
        "base_def": 180,
        "base_crt": 25,
        "skill_basic_name": "Xạ Kích Liên Thanh",
        "skill_basic_dmg": 1.0,
        "skill_combo_name": "Càn Quét Tội Lỗi",
        "skill_combo_dmg": 2.2,
        "skill_ult_name": "Oanh Tạc Quỹ Đạo",
        "skill_ult_dmg": 5.5,
        "ult_sp_cost": 75,
        "evade_name": "Phản Xạ Vượt Cấp",
        "emoji": "🦇"
    },
    "sixth_serenade": {
        "id": "sixth_serenade",
        "name": "Sixth Serenade (PSY)",
        "type": "PSY",
        "rarity": "S",
        "base_hp": 1500,
        "base_atk": 320,
        "base_def": 140,
        "base_crt": 40,
        "skill_basic_name": "Dạ Khúc Dạ Tưởng",
        "skill_basic_dmg": 1.5,
        "skill_combo_name": "Dấu Ấn Quạ Đen",
        "skill_combo_dmg": 3.0,
        "skill_ult_name": "Bản Tình Ca Bóng Tối",
        "skill_ult_dmg": 8.0,
        "ult_sp_cost": 100,
        "evade_name": "Vũ Điệu Quạ Đen",
        "emoji": "🎭"
    }
}

KALLEN_WEAPONS = {
    "wp_usp": {
        "id": "wp_usp",
        "name": "Súng Ngắn USP",
        "rarity": 2,
        "atk": 50,
        "crt": 5,
        "ability": "Không có"
    },
    "wp_colt": {
        "id": "wp_colt",
        "name": "Colt Peacemaker",
        "rarity": 3,
        "atk": 120,
        "crt": 10,
        "ability": "Tăng 5% sát thương vật lý"
    },
    "wp_water": {
        "id": "wp_water",
        "name": "Water Spirit Type-II",
        "rarity": 4,
        "atk": 200,
        "crt": 15,
        "ability": "Tăng 15% sát thương khi địch bị đóng băng"
    },
    "wp_jingwei": {
        "id": "wp_jingwei",
        "name": "Cánh Chim Jingwei",
        "rarity": 4,
        "atk": 230,
        "crt": 20,
        "ability": "Đánh trúng địch 10 lần tăng 10% ATK"
    },
    "wp_aria": {
        "id": "wp_aria",
        "name": "Tranquil Arias",
        "rarity": 5,
        "atk": 350,
        "crt": 35,
        "ability": "Sau khi đổi nhân vật hoặc dùng Ulti, tăng 50% sát thương trong 5s"
    },
    "wp_keys": {
        "id": "wp_keys",
        "name": "Keys of the Void",
        "rarity": 5,
        "atk": 380,
        "crt": 40,
        "ability": "Tăng 20% sát thương bạo kích và 15% sát thương nguyên tố"
    }
}

KALLEN_STIGMATA = {
    "stig_attila_t": {
        "id": "stig_attila_t",
        "name": "Attila (T)",
        "set_name": "Attila",
        "type": "T",
        "rarity": 3,
        "hp": 200, "atk": 40, "def": 30, "crt": 0,
        "effect": "Combo > 10, tăng 15% Tốc độ di chuyển"
    },
    "stig_attila_m": {
        "id": "stig_attila_m",
        "name": "Attila (M)",
        "set_name": "Attila",
        "type": "M",
        "rarity": 3,
        "hp": 220, "atk": 0, "def": 45, "crt": 5,
        "effect": "Combo > 20, tăng 20% Phòng ngự"
    },
    "stig_attila_b": {
        "id": "stig_attila_b",
        "name": "Attila (B)",
        "set_name": "Attila",
        "type": "B",
        "rarity": 3,
        "hp": 210, "atk": 30, "def": 35, "crt": 5,
        "effect": "Combo > 30, tăng 31% Sát thương vật lý"
    },
    "stig_michelangelo_t": {
        "id": "stig_michelangelo_t",
        "name": "Michelangelo (T)",
        "set_name": "Michelangelo",
        "type": "T",
        "rarity": 5,
        "hp": 400, "atk": 100, "def": 50, "crt": 0,
        "effect": "Mỗi đòn đánh thường tăng 7.2% Sát thương vật lý, cộng dồn 5 lần"
    },
    "stig_michelangelo_m": {
        "id": "stig_michelangelo_m",
        "name": "Michelangelo (M)",
        "set_name": "Michelangelo",
        "type": "M",
        "rarity": 5,
        "hp": 450, "atk": 0, "def": 120, "crt": 10,
        "effect": "Mỗi đòn đánh thường tăng 3% Tỉ lệ bạo kích, cộng dồn 5 lần"
    },
    "stig_michelangelo_b": {
        "id": "stig_michelangelo_b",
        "name": "Michelangelo (B)",
        "set_name": "Michelangelo",
        "type": "B",
        "rarity": 5,
        "hp": 420, "atk": 70, "def": 60, "crt": 15,
        "effect": "Mỗi đòn đánh thường tăng 14% Sát thương bạo kích, cộng dồn 5 lần"
    },
    "stig_nohime_t": {
        "id": "stig_nohime_t",
        "name": "Nohime (T)",
        "set_name": "Nohime",
        "type": "T",
        "rarity": 5,
        "hp": 420, "atk": 110, "def": 40, "crt": 0,
        "effect": "Tấn công thường có 15% đóng băng địch trong 4s. Gây thêm sát thương nguyên tố Băng"
    },
    "stig_nohime_m": {
        "id": "stig_nohime_m",
        "name": "Nohime (M)",
        "set_name": "Nohime",
        "type": "M",
        "rarity": 5,
        "hp": 480, "atk": 0, "def": 150, "crt": 5,
        "effect": "Tăng 80% sát thương Băng lên kẻ địch bị đóng băng"
    },
    "stig_nohime_b": {
        "id": "stig_nohime_b",
        "name": "Nohime (B)",
        "set_name": "Nohime",
        "type": "B",
        "rarity": 5,
        "hp": 450, "atk": 80, "def": 50, "crt": 10,
        "effect": "Mỗi kẻ địch bị đóng băng/làm chậm trên sân tăng 10% Tốc chạy và 25% sát thương Băng (Max 3 stack)"
    }
}

KALLEN_ENEMIES = {
    "zombie_1": {"name": "Xác Sống Cầm Kiếm", "type": "BIO", "hp": 2000, "atk": 100, "def": 50, "sp_drop": 5},
    "zombie_2": {"name": "Cung Thủ Xác Sống", "type": "BIO", "hp": 1800, "atk": 150, "def": 40, "sp_drop": 8},
    "zombie_boss": {"name": "White Ninja (Boss)", "type": "BIO", "hp": 15000, "atk": 300, "def": 150, "sp_drop": 20},
    "beast_1": {"name": "Thú Honkai Kỵ Binh", "type": "PSY", "hp": 3000, "atk": 120, "def": 100, "sp_drop": 5},
    "beast_2": {"name": "Thú Honkai Bay", "type": "PSY", "hp": 2500, "atk": 180, "def": 80, "sp_drop": 8},
    "beast_boss": {"name": "Ganesha (Boss)", "type": "PSY", "hp": 25000, "atk": 400, "def": 250, "sp_drop": 30},
    "mecha_1": {"name": "Robot Tuần Tra", "type": "MECH", "hp": 3500, "atk": 80, "def": 200, "sp_drop": 5},
    "mecha_2": {"name": "Titan Nhện", "type": "MECH", "hp": 4500, "atk": 250, "def": 300, "sp_drop": 10},
    "mecha_boss": {"name": "RPC-6626 (Boss)", "type": "MECH", "hp": 30000, "atk": 500, "def": 400, "sp_drop": 50},
    "god_boss": {"name": "Herrscher of the Void", "type": "BIO", "hp": 100000, "atk": 1200, "def": 800, "sp_drop": 100}
}

KALLEN_STAGES = {
    "1-1": {"name": "1-1: Sự thức tỉnh", "enemies": ["zombie_1", "zombie_1", "zombie_2"], "reward_money": 5000, "reward_xp": 100},
    "1-2": {"name": "1-2: Cuộc vây hãm", "enemies": ["zombie_2", "beast_1", "beast_1"], "reward_money": 7000, "reward_xp": 150},
    "1-3": {"name": "1-3: Bóng trắng trong đêm (Boss)", "enemies": ["zombie_1", "zombie_boss"], "reward_money": 15000, "reward_xp": 300},
    "2-1": {"name": "2-1: Cảnh báo Honkai", "enemies": ["beast_1", "beast_2", "beast_2"], "reward_money": 10000, "reward_xp": 200},
    "2-2": {"name": "2-2: Xung đột Titan", "enemies": ["mecha_1", "mecha_1", "mecha_2"], "reward_money": 12000, "reward_xp": 250},
    "2-3": {"name": "2-3: Đế vương sụp đổ (Boss)", "enemies": ["beast_2", "beast_boss"], "reward_money": 25000, "reward_xp": 500},
    "3-1": {"name": "3-1: Bầu trời cơ khí", "enemies": ["mecha_2", "mecha_2", "beast_2"], "reward_money": 18000, "reward_xp": 350},
    "3-2": {"name": "3-2: Vũ khí hủy diệt (Boss)", "enemies": ["mecha_1", "mecha_boss"], "reward_money": 40000, "reward_xp": 800},
    "4-1": {"name": "Chung Cuộc: Luật Giả (Raid Boss)", "enemies": ["god_boss"], "reward_money": 100000, "reward_xp": 2000}
}

# =====================================================================
# KALLEN FANTASY - HỆ THỐNG DATABASE ĐỘC LẬP
# =====================================================================
# Tạo collection riêng cho Kallen Fantasy để không đụng chạm tới data Kinh tế
kf_col = db["kallen_fantasy"]
KF_CACHE = {}

def load_kf_profile(user_id):
    """Tải hồ sơ Kallen Fantasy của người chơi"""
    user_id = str(user_id)
    if user_id not in KF_CACHE:
        doc = kf_col.find_one({"_id": user_id})
        if doc:
            KF_CACHE[user_id] = doc
        else:
            KF_CACHE[user_id] = {}
            
    defaults = {
        "level": 1,
        "exp": 0,
        "stamina": 100, # Năng lượng để đi ải
        "max_stamina": 100,
        "last_stamina_regen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "crystals": 0, # Đơn vị nạp thẻ quay Gacha (Pha lê)
        "current_suit": "imayoh",
        "unlocked_suits": ["imayoh"],
        "inventory_weapons": ["wp_usp"],
        "equipped_weapon": "wp_usp",
        "inventory_stigmata": [],
        "equipped_stigmata": {"T": None, "M": None, "B": None},
        "cleared_stages": [],
        "abyss_floor": 1
    }
    
    for k, v in defaults.items():
        if k not in KF_CACHE[user_id]:
            KF_CACHE[user_id][k] = v
            
    # Hồi thể lực (1 stamina / 5 phút)
    last_regen = datetime.strptime(KF_CACHE[user_id]["last_stamina_regen"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    delta = now - last_regen
    minutes_passed = int(delta.total_seconds() / 60)
    
    if minutes_passed >= 5:
        stamina_to_add = minutes_passed // 5
        KF_CACHE[user_id]["stamina"] = min(KF_CACHE[user_id]["max_stamina"], KF_CACHE[user_id]["stamina"] + stamina_to_add)
        # Cập nhật lại mốc thời gian hồi (trừ đi phần lẻ chưa đủ 5 phút)
        leftover_seconds = int(delta.total_seconds()) % 300
        new_regen_time = now - timedelta(seconds=leftover_seconds)
        KF_CACHE[user_id]["last_stamina_regen"] = new_regen_time.strftime("%Y-%m-%d %H:%M:%S")
        save_kf_profile(user_id)

    return KF_CACHE[user_id]

def save_kf_profile(user_id):
    """Lưu hồ sơ Kallen Fantasy"""
    user_id = str(user_id)
    if user_id in KF_CACHE:
        kf_col.update_one(
            {"_id": user_id},
            {"$set": KF_CACHE[user_id]},
            upsert=True
        )

# =====================================================================
# KALLEN FANTASY - CHỈ SỐ NHÂN VẬT & LOGIC KHẮC HỆ
# =====================================================================
def calculate_kallen_stats(user_id):
    """Tính toán tổng chỉ số của Valkyrie bao gồm Base + Weapon + Stigmata"""
    p = load_kf_profile(user_id)
    suit = KALLEN_BATTLESUITS[p["current_suit"]]
    
    total_hp = suit["base_hp"]
    total_atk = suit["base_atk"]
    total_def = suit["base_def"]
    total_crt = suit["base_crt"]
    
    # Cộng chỉ số vũ khí
    if p["equipped_weapon"]:
        wp = KALLEN_WEAPONS[p["equipped_weapon"]]
        total_atk += wp["atk"]
        total_crt += wp["crt"]
        
    # Cộng chỉ số vết thánh (Stigmata)
    equipped_stig = p["equipped_stigmata"]
    for pos in ["T", "M", "B"]:
        stig_id = equipped_stig[pos]
        if stig_id:
            stig = KALLEN_STIGMATA[stig_id]
            total_hp += stig["hp"]
            total_atk += stig["atk"]
            total_def += stig["def"]
            total_crt += stig["crt"]
            
    return {
        "suit": suit,
        "hp": int(total_hp * (1 + (p["level"] - 1) * 0.1)), # Tăng 10% stats mỗi cấp
        "atk": int(total_atk * (1 + (p["level"] - 1) * 0.1)),
        "def": int(total_def * (1 + (p["level"] - 1) * 0.1)),
        "crt": int(total_crt * (1 + (p["level"] - 1) * 0.1)),
    }

def get_type_advantage(attacker_type, defender_type):
    """
    Hệ thống khắc hệ:
    MECH khắc BIO, BIO khắc PSY, PSY khắc MECH.
    Khắc hệ: Sát thương x1.3
    Bị khắc: Sát thương x0.7
    Bằng hệ: Sát thương x1.0
    """
    if attacker_type == "MECH" and defender_type == "BIO": return 1.3
    if attacker_type == "BIO" and defender_type == "PSY": return 1.3
    if attacker_type == "PSY" and defender_type == "MECH": return 1.3
    
    if attacker_type == "BIO" and defender_type == "MECH": return 0.7
    if attacker_type == "PSY" and defender_type == "BIO": return 0.7
    if attacker_type == "MECH" and defender_type == "PSY": return 0.7
    
    return 1.0

# =====================================================================
# KALLEN FANTASY - GIAO DIỆN LỆNH & GACHA (TIẾP TẾ)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['kf', 'honkai'])
async def kallen(ctx):
    """Trung tâm chỉ huy Hyperion của Kallen Fantasy"""
    p = load_kf_profile(ctx.author.id)
    stats = calculate_kallen_stats(ctx.author.id)
    suit = stats["suit"]
    
    embed = discord.Embed(
        title="🌌 KALLEN FANTASY - HYPERION BRIDGE",
        description=f"Thuyền trưởng: **{ctx.author.name}**\nCấp độ: **Lv.{p['level']}** | Thể lực: **{p['stamina']}/{p['max_stamina']}** ⚡ | Pha lê: **{p['crystals']:,}** 💎",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="Đang xuất chiến", 
        value=f"**{suit['emoji']} {suit['name']}**", 
        inline=False
    )
    embed.add_field(
        name="Chỉ số chiến đấu",
        value=f"❤️ HP: {stats['hp']} | ⚔️ ATK: {stats['atk']}\n🛡️ DEF: {stats['def']} | 💥 CRT: {stats['crt']}",
        inline=False
    )
    
    wp_name = KALLEN_WEAPONS[p["equipped_weapon"]]["name"] if p["equipped_weapon"] else "Tay Không"
    stig_t = KALLEN_STIGMATA[p["equipped_stigmata"]["T"]]["name"] if p["equipped_stigmata"]["T"] else "Trống"
    stig_m = KALLEN_STIGMATA[p["equipped_stigmata"]["M"]]["name"] if p["equipped_stigmata"]["M"] else "Trống"
    stig_b = KALLEN_STIGMATA[p["equipped_stigmata"]["B"]]["name"] if p["equipped_stigmata"]["B"] else "Trống"
    
    embed.add_field(
        name="Trang bị",
        value=f"🔫 Vũ khí: {wp_name}\n💠 Vết thánh (T): {stig_t}\n💠 Vết thánh (M): {stig_m}\n💠 Vết thánh (B): {stig_b}",
        inline=False
    )
    
    cmds = (
        "`k kallen gacha` • Vào kênh Tiếp Tế (Dùng Pha lê)\n"
        "`k kallen doipha` • Đổi Tiền 💰 sang Pha lê 💎\n"
        "`k kallen story` • Đi Cốt truyện\n"
        "`k kallen abyss` • Leo tháp Vực Sâu"
    )
    embed.add_field(name="Bảng Điều Khiển", value=cmds, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command()
async def doipha(ctx, amount: int):
    """Đổi tiền server sang Pha lê Kallen Fantasy (Tỷ giá 1000 💰 = 1 💎)"""
    if amount <= 0: return await ctx.reply("Nhập số lớn hơn 0.")
    
    user_id = str(ctx.author.id)
    u_data = load_user(user_id)
    cost = amount * 1000
    
    if u_data.get("money", 0) < cost:
        return await ctx.reply(f"⚠️ Sếp cần {cost:,} 💰 để đổi lấy {amount:,} Pha lê 💎. Đi cày thêm nhé!")
        
    u_data["money"] -= cost
    save_user(user_id)
    
    p = load_kf_profile(user_id)
    p["crystals"] += amount
    save_kf_profile(user_id)
    
    await ctx.reply(f"✅ Đã nạp thành công **{amount:,} Pha lê 💎** vào Kallen Fantasy. Thuyền trưởng hãy đi Gacha ngay!")

class KallenGachaView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Quay x1 (280 💎)", style=discord.ButtonStyle.primary, emoji="📦")
    async def roll_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 1)

    @discord.ui.button(label="Quay x10 (2800 💎)", style=discord.ButtonStyle.danger, emoji="🎁")
    async def roll_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 10)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: return False
        return True

    async def process_gacha(self, interaction: discord.Interaction, times: int):
        user_id = str(interaction.user.id)
        p = load_kf_profile(user_id)
        cost = 280 * times
        
        if p["crystals"] < cost:
            return await interaction.response.send_message(f"⚠️ Thuyền trưởng không đủ Pha lê! Cần {cost} 💎.", ephemeral=True)
            
        p["crystals"] -= cost
        results = []
        
        # Pool Gacha
        all_weapons = list(KALLEN_WEAPONS.keys())
        all_stigmatas = list(KALLEN_STIGMATA.keys())
        all_suits = list(KALLEN_BATTLESUITS.keys())
        
        for _ in range(times):
            roll = random.uniform(0, 100)
            if roll <= 1.5: # 1.5% ra Giáp S
                suit = "sixth_serenade"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"🌟 **GIÁP VALKYRIE S:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"🌟 Giáp S (Đã có, chuyển thành 1000 Pha lê)")
                    p["crystals"] += 1000
            elif roll <= 5.0: # 3.5% ra Vũ khí / Vết thánh 5 sao
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] == 5] + [k for k, v in KALLEN_STIGMATA.items() if v["rarity"] == 5]
                item = random.choice(pool)
                if item in KALLEN_WEAPONS:
                    p["inventory_weapons"].append(item)
                    results.append(f"🔶 **Vũ Khí 5★:** {KALLEN_WEAPONS[item]['name']}")
                else:
                    p["inventory_stigmata"].append(item)
                    results.append(f"💠 **Vết Thánh 5★:** {KALLEN_STIGMATA[item]['name']}")
            elif roll <= 15.0: # 10% ra Giáp A
                suit = "sundenjager"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"⭐ **GIÁP VALKYRIE A:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"⭐ Giáp A (Đã có, chuyển thành 280 Pha lê)")
                    p["crystals"] += 280
            elif roll <= 45.0: # 30% Đồ 4 sao
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] == 4]
                item = random.choice(pool)
                p["inventory_weapons"].append(item)
                results.append(f"🟦 Vũ Khí 4★: {KALLEN_WEAPONS[item]['name']}")
            else: # Rác 3 sao
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] <= 3] + [k for k, v in KALLEN_STIGMATA.items() if v["rarity"] == 3]
                item = random.choice(pool)
                if item in KALLEN_WEAPONS:
                    p["inventory_weapons"].append(item)
                    results.append(f"⬜ Vũ Khí 3★: {KALLEN_WEAPONS[item]['name']}")
                else:
                    p["inventory_stigmata"].append(item)
                    results.append(f"⬜ Vết Thánh 3★: {KALLEN_STIGMATA[item]['name']}")
                    
        save_kf_profile(user_id)
        
        desc = "\n".join(results)
        embed = discord.Embed(title="📦 KẾT QUẢ TIẾP TẾ", description=desc, color=discord.Color.gold())
        embed.set_footer(text=f"Pha lê còn lại: {p['crystals']} 💎")
        
        await interaction.response.edit_message(embed=embed, view=self)

@kallen.command()
async def gacha(ctx):
    """Mở giao diện Tiếp tế (Gacha) của Kallen Fantasy"""
    embed = discord.Embed(
        title="📦 KÊNH TIẾP TẾ KALLEN",
        description="Chào mừng Thuyền trưởng đến với Trung Tâm Tiếp Tế.\nHãy dùng Pha Lê 💎 để triệu hồi Giáp Valkyrie, Vũ khí và Vết thánh mới!",
        color=discord.Color.blue()
    )
    await ctx.reply(embed=embed, view=KallenGachaView(ctx.author), mention_author=False)
    # =====================================================================
# KALLEN FANTASY - HỆ THỐNG QUẢN LÝ TRANG BỊ (EQUIP)
# =====================================================================
@kallen.command()
async def equip(ctx, category: str, item_id: str):
    """
    Trang bị Valkyrie, Vũ khí hoặc Vết thánh
    Cách dùng: 
    - k kallen equip suit <id>
    - k kallen equip wp <id>
    - k kallen equip stig_<T/M/B> <id>
    """
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    category = category.lower()
    
    if category == "suit":
        if item_id not in KALLEN_BATTLESUITS:
            return await ctx.reply("⚠️ Tên Giáp Valkyrie không tồn tại.")
        if item_id not in p["unlocked_suits"]:
            return await ctx.reply("⚠️ Thuyền trưởng chưa mở khóa Giáp Valkyrie này (Vui lòng đi Gacha).")
        p["current_suit"] = item_id
        save_kf_profile(user_id)
        return await ctx.reply(f"✅ Đã xuất chiến Giáp Valkyrie: **{KALLEN_BATTLESUITS[item_id]['name']}**")
        
    elif category == "wp":
        if item_id not in KALLEN_WEAPONS:
            return await ctx.reply("⚠️ Mã Vũ khí không tồn tại.")
        if item_id not in p["inventory_weapons"]:
            return await ctx.reply("⚠️ Thuyền trưởng không sở hữu Vũ khí này.")
        p["equipped_weapon"] = item_id
        save_kf_profile(user_id)
        return await ctx.reply(f"✅ Đã trang bị Vũ khí: **{KALLEN_WEAPONS[item_id]['name']}**")
        
    elif category in ["stig_t", "stig_m", "stig_b"]:
        pos = category.split("_")[1].upper()
        if item_id not in KALLEN_STIGMATA:
            return await ctx.reply("⚠️ Mã Vết thánh không tồn tại.")
        if item_id not in p["inventory_stigmata"]:
            return await ctx.reply("⚠️ Thuyền trưởng không sở hữu Vết thánh này.")
        if KALLEN_STIGMATA[item_id]["type"] != pos:
            return await ctx.reply(f"⚠️ Vết thánh này không phải mảnh ({pos}).")
            
        p["equipped_stigmata"][pos] = item_id
        save_kf_profile(user_id)
        return await ctx.reply(f"✅ Đã lắp Vết thánh mảnh ({pos}): **{KALLEN_STIGMATA[item_id]['name']}**")
        
    else:
        await ctx.reply("⚠️ Sai cú pháp. Dùng: `suit`, `wp`, `stig_t`, `stig_m`, `stig_b`.")

# =====================================================================
# KALLEN FANTASY - LÕI CHIẾN ĐẤU (COMBAT UI & LOGIC)
# =====================================================================
class KallenCombatView(discord.ui.View):
    """Hệ thống Nút Bấm Xử Lý Chiến Đấu Theo Lượt"""
    def __init__(self, author, player_stats, stage_data, p_profile):
        super().__init__(timeout=300) # Timeout 5 phút cho một trận
        self.author = author
        self.p_stats = player_stats
        self.stage = stage_data
        self.p_profile = p_profile
        
        # Chỉ số khởi đầu của Player
        self.p_hp = self.p_stats["hp"]
        self.p_max_hp = self.p_stats["hp"]
        self.p_sp = 0 # Khởi đầu với 0 SP
        self.p_evade_cooldown = 0
        
        # Danh sách quái vật trong ải
        self.enemy_list = self.stage["enemies"].copy()
        self.current_enemy_idx = 0
        self.load_enemy()

    def load_enemy(self):
        """Tải dữ liệu quái vật hiện tại"""
        if self.current_enemy_idx < len(self.enemy_list):
            enemy_id = self.enemy_list[self.current_enemy_idx]
            base_enemy = KALLEN_ENEMIES[enemy_id]
            # Copy để không làm thay đổi data gốc
            self.e_data = {
                "name": base_enemy["name"],
                "type": base_enemy["type"],
                "hp": base_enemy["hp"],
                "max_hp": base_enemy["hp"],
                "atk": base_enemy["atk"],
                "def": base_enemy["def"],
                "sp_drop": base_enemy["sp_drop"]
            }
            return True
        return False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Không thể can thiệp vào trận chiến của người khác!", ephemeral=True)
            return False
        return True

    def calculate_damage(self, dmg_multiplier, is_crit_allowed=True):
        """Hàm tính toán sát thương người chơi đánh vào quái"""
        base_atk = self.p_stats["atk"]
        enemy_def = self.e_data["def"]
        
        # Hệ số khắc hệ
        type_adv = get_type_advantage(self.p_stats["suit"]["type"], self.e_data["type"])
        
        # Tính bạo kích (Crit)
        is_crit = False
        crit_mult = 1.0
        if is_crit_allowed:
            crit_chance = min(100, self.p_stats["crt"])
            if random.uniform(0, 100) <= crit_chance:
                is_crit = True
                crit_mult = 2.0 # Sát thương bạo kích mặc định x2
                
        # Công thức sát thương giảm trừ phòng ngự cơ bản
        raw_dmg = (base_atk * dmg_multiplier * type_adv * crit_mult) - (enemy_def * 0.5)
        final_dmg = int(max(10, raw_dmg)) # Ít nhất gây 10 dmg
        
        return final_dmg, is_crit, type_adv

    def enemy_turn(self):
        """Lượt của quái vật tấn công người chơi"""
        if self.e_data["hp"] <= 0:
            return 0, "Quái vật đã bị tiêu diệt, không thể tấn công!"
            
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        final_dmg = int(max(5, raw_dmg))
        
        self.p_hp -= final_dmg
        return final_dmg, f"💥 **{self.e_data['name']}** phản công gây **{final_dmg}** sát thương!"

    async def update_battle_ui(self, interaction: discord.Interaction, combat_log: str):
        """Cập nhật Giao diện sau mỗi lượt đánh"""
        # Kiểm tra chết quái
        if self.e_data["hp"] <= 0:
            self.p_sp += self.e_data["sp_drop"] # Nhận SP khi giết quái
            combat_log += f"\n💀 **{self.e_data['name']}** đã bị hạ gục! Nhận {self.e_data['sp_drop']} SP."
            self.current_enemy_idx += 1
            
            if not self.load_enemy():
                # Hoàn thành ải
                return await self.win_stage(interaction, combat_log)
            else:
                combat_log += f"\n⚠️ **CẢNH BÁO:** Kẻ địch tiếp theo [**{self.e_data['name']}**] xuất hiện!"

        # Kiểm tra người chơi chết
        if self.p_hp <= 0:
            return await self.lose_stage(interaction, combat_log)

        # Giảm hồi chiêu Né
        if self.p_evade_cooldown > 0:
            self.p_evade_cooldown -= 1

        # Cập nhật thanh máu
        p_hp_bar = make_progress_bar(max(0, self.p_hp), self.p_max_hp, 10)
        e_hp_bar = make_progress_bar(max(0, self.e_data["hp"]), self.e_data["max_hp"], 10)
        
        embed = discord.Embed(
            title=f"⚔️ {self.stage['name'].upper()}",
            description=combat_log,
            color=discord.Color.red()
        )
        
        # Info Valkyrie
        suit = self.p_stats["suit"]
        embed.add_field(
            name=f"Thuyền trưởng {self.author.name}\n{suit['emoji']} {suit['name']}",
            value=f"❤️ HP: {max(0, self.p_hp)}/{self.p_max_hp}\n`{p_hp_bar}`\n⚡ SP: {self.p_sp}",
            inline=True
        )
        embed.add_field(name="VS", value="⚡", inline=True)
        # Info Enemy
        type_icon = "🔺" if get_type_advantage(suit["type"], self.e_data["type"]) > 1 else ("🔻" if get_type_advantage(suit["type"], self.e_data["type"]) < 1 else "➖")
        embed.add_field(
            name=f"Kẻ địch {self.current_enemy_idx + 1}/{len(self.enemy_list)}\n👹 {self.e_data['name']} ({self.e_data['type']}) {type_icon}",
            value=f"❤️ HP: {max(0, self.e_data['hp'])}/{self.e_data['max_hp']}\n`{e_hp_bar}`",
            inline=True
        )

        # Khóa nút Ultimate nếu không đủ SP, Khóa Né nếu đang CD
        self.btn_ult.disabled = self.p_sp < suit["ult_sp_cost"]
        self.btn_evade.disabled = self.p_evade_cooldown > 0

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def win_stage(self, interaction: discord.Interaction, combat_log: str):
        """Xử lý khi vượt ải thành công"""
        for child in self.children:
            child.disabled = True
            
        user_id = str(self.author.id)
        user_data = load_user(user_id)
        
        # Nhận thưởng
        money_reward = self.stage["reward_money"]
        xp_reward = self.stage["reward_xp"]
        
        user_data["money"] += money_reward
        self.p_profile["exp"] += xp_reward
        
        # Level up logic đơn giản cho KF Profile
        if self.p_profile["exp"] >= self.p_profile["level"] * 500:
            self.p_profile["exp"] -= self.p_profile["level"] * 500
            self.p_profile["level"] += 1
            combat_log += f"\n🆙 Cấp Thuyền Trưởng tăng lên **Lv.{self.p_profile['level']}**!"
            
        save_user(user_id)
        save_kf_profile(user_id)
        
        embed = discord.Embed(
            title="🎉 VƯỢT ẢI THÀNH CÔNG!",
            description=f"{combat_log}\n\n🎁 **PHẦN THƯỞNG:**\n💰 {money_reward:,} VNĐ\n✨ {xp_reward} KF-EXP",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def lose_stage(self, interaction: discord.Interaction, combat_log: str):
        """Xử lý khi Valkyrie gục ngã"""
        for child in self.children:
            child.disabled = True
            
        embed = discord.Embed(
            title="💀 NHIỆM VỤ THẤT BẠI",
            description=f"{combat_log}\n\nValkyrie của bạn đã gục ngã. Thể lực đã mất sẽ không được hoàn trả. Hãy nâng cấp trang bị và thử lại!",
            color=discord.Color.dark_grey()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    # --- ĐỊNH NGHĨA CÁC NÚT BẤM KỸ NĂNG ---

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, custom_id="btn_atk")
    async def btn_atk(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_basic_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp += 5 # Đánh thường hồi 5 SP
        
        crit_txt = " (💥 **BẠO KÍCH**)" if is_crit else ""
        log = f"🗡️ Dùng **{suit['skill_basic_name']}** gây **{dmg}** ST{crit_txt}."
        
        e_dmg, e_log = self.enemy_turn()
        log += f"\n{e_log}"
        
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Combo (Nhánh)", style=discord.ButtonStyle.success, custom_id="btn_combo")
    async def btn_combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_combo_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp += 2
        
        crit_txt = " (💥 **BẠO KÍCH**)" if is_crit else ""
        log = f"⚔️ Tung đòn Nhánh **{suit['skill_combo_name']}** gây **{dmg}** ST{crit_txt}."
        
        e_dmg, e_log = self.enemy_turn()
        log += f"\n{e_log}"
        
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, custom_id="btn_ult")
    async def btn_ult(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_sp < suit["ult_sp_cost"]:
            return await interaction.response.send_message("⚠️ Không đủ Năng lượng (SP)!", ephemeral=True)
            
        self.p_sp -= suit["ult_sp_cost"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        
        crit_txt = " (💥 **BẠO KÍCH**)" if is_crit else ""
        log = f"🔥 Kích hoạt Tất Sát **{suit['skill_ult_name']}** gây lượng sát thương khủng khiếp **{dmg}** ST{crit_txt}!"
        
        # Ulti thường có i-frame, địch không đánh lại trong turn này (nếu chưa chết)
        if self.e_data["hp"] > 0:
            log += f"\n🛡️ Đối phương bị choáng ngợp bởi chiêu Tất sát, bỏ qua lượt!"
            
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Né Cực Hạn", style=discord.ButtonStyle.secondary, custom_id="btn_evade")
    async def btn_evade(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_evade_cooldown > 0:
            return await interaction.response.send_message("⚠️ Kỹ năng Né đang hồi chiêu!", ephemeral=True)
            
        self.p_evade_cooldown = 3 # Cooldown 3 lượt
        self.p_sp += 15 # Né thành công hồi nhiều SP
        
        # Địch tấn công nhưng bị né
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        e_dmg = int(max(5, raw_dmg))
        
        log = f"💨 Kích hoạt **{suit['evade_name']}**! Né hoàn toàn **{e_dmg}** sát thương từ địch, hồi 15 SP."
        await self.update_battle_ui(interaction, log)

# =====================================================================
# KALLEN FANTASY - LỆNH GỌI CỐT TRUYỆN (STORY)
# =====================================================================
@kallen.command()
async def story(ctx, stage_id: str = None):
    """
    Đi ải cốt truyện Kallen Fantasy
    Cách dùng: k kallen story <Mã Ải> (VD: 1-1, 1-2)
    Gõ 'k kallen story list' để xem danh sách ải.
    """
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    
    if stage_id is None or stage_id.lower() == "list":
        embed = discord.Embed(title="📜 DANH SÁCH ẢI CỐT TRUYỆN", color=discord.Color.dark_purple())
        desc = ""
        for s_id, s_data in KALLEN_STAGES.items():
            status = "✅" if s_id in p["cleared_stages"] else "🔒"
            desc += f"{status} **Ải {s_id}**: {s_data['name']} (Thưởng: {s_data['reward_money']:,} 💰)\n"
        embed.description = desc
        embed.set_footer(text="Dùng lệnh: k kallen story <mã ải> để xuất kích (Tốn 10 Thể lực)")
        return await ctx.reply(embed=embed, mention_author=False)

    if stage_id not in KALLEN_STAGES:
        return await ctx.reply("⚠️ Mã ải không tồn tại. Gõ `k kallen story list` để xem.")
        
    if p["stamina"] < 10:
        return await ctx.reply(f"⚠️ Thể lực hiện tại ({p['stamina']}/100) không đủ để xuất kích (Cần 10 ⚡).")
        
    # Trừ thể lực
    p["stamina"] -= 10
    save_kf_profile(user_id)
    
    stage_data = KALLEN_STAGES[stage_id]
    stats = calculate_kallen_stats(user_id)
    
    embed_start = discord.Embed(
        title=f"🚀 XUẤT KÍCH: {stage_data['name']}",
        description="Đang tải dữ liệu chiến trường... Hyperion, sẵn sàng!",
        color=discord.Color.blue()
    )
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(2)
    
    # Kích hoạt giao diện chiến đấu
    view = KallenCombatView(ctx.author, stats, stage_data, p)
    
    # Tạo log khởi đầu mồi
    initial_log = f"Bắt đầu ải: {stage_data['name']}. Kẻ địch đã xuất hiện!"
    
    # Gắn view vào hàm cập nhật để tạo embed đầu tiên
    await view.update_battle_ui(ctx, initial_log)
    
    # Gán msg để view có thể edit (nếu cần xử lý ngoài hàm interaction)
    view.message = msg
    # =====================================================================
# KALLEN FANTASY - CHẾ ĐỘ VỰC SÂU (ABYSS - LEO THÁP VÔ TẬN)
# =====================================================================
def generate_abyss_enemy(floor_level):
    """Tạo ra quái vật Vực Sâu với chỉ số tăng tiến theo tầng"""
    # Loại bỏ các boss rườm rà, chỉ lấy quái thường hoặc boss nhỏ để làm base
    enemy_pool = [e for k, e in KALLEN_ENEMIES.items() if "god_boss" not in k]
    base_enemy = random.choice(enemy_pool)
    
    # Hệ số sức mạnh: Mỗi tầng tăng 15% chỉ số
    multiplier = 1.0 + (floor_level * 0.15)
    
    return {
        "name": f"{base_enemy['name']} (Tầng {floor_level})",
        "type": base_enemy["type"],
        "hp": int(base_enemy["hp"] * multiplier),
        "max_hp": int(base_enemy["hp"] * multiplier),
        "atk": int(base_enemy["atk"] * multiplier),
        "def": int(base_enemy["def"] * multiplier),
        "sp_drop": base_enemy["sp_drop"] + int(floor_level / 5)
    }

class AbyssCombatView(discord.ui.View):
    """Hệ thống UI Chiến đấu vô tận cho Vực Sâu"""
    def __init__(self, author, player_stats, p_profile):
        super().__init__(timeout=300) # Cho phép 5 phút suy nghĩ mỗi lượt
        self.author = author
        self.p_stats = player_stats
        self.p_profile = p_profile
        
        # Chỉ số người chơi
        self.p_hp = self.p_stats["hp"]
        self.p_max_hp = self.p_stats["hp"]
        self.p_sp = 0 
        self.p_evade_cooldown = 0
        
        # Thông tin Vực Sâu
        self.current_floor = 1
        self.e_data = generate_abyss_enemy(self.current_floor)
        self.crystals_earned = 0

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Chỗ người ta đang leo tháp, đừng bấm phá!", ephemeral=True)
            return False
        return True

    def calculate_damage(self, dmg_multiplier, is_crit_allowed=True):
        base_atk = self.p_stats["atk"]
        enemy_def = self.e_data["def"]
        type_adv = get_type_advantage(self.p_stats["suit"]["type"], self.e_data["type"])
        
        is_crit = False
        crit_mult = 1.0
        if is_crit_allowed:
            crit_chance = min(100, self.p_stats["crt"])
            if random.uniform(0, 100) <= crit_chance:
                is_crit = True
                crit_mult = 2.0 
                
        raw_dmg = (base_atk * dmg_multiplier * type_adv * crit_mult) - (enemy_def * 0.5)
        return int(max(10, raw_dmg)), is_crit, type_adv

    def enemy_turn(self):
        if self.e_data["hp"] <= 0:
            return 0, "Quái vật đã tan biến..."
            
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        final_dmg = int(max(5, raw_dmg))
        
        self.p_hp -= final_dmg
        return final_dmg, f"💥 **{self.e_data['name']}** vung vũ khí gây **{final_dmg}** ST!"

    async def update_battle_ui(self, interaction: discord.Interaction, combat_log: str):
        # Nếu quái chết -> Lên tầng mới
        if self.e_data["hp"] <= 0:
            self.p_sp += self.e_data["sp_drop"]
            crystal_drop = random.randint(5, 15) + int(self.current_floor / 2)
            self.crystals_earned += crystal_drop
            
            combat_log += f"\n✅ Vượt Tầng {self.current_floor}! Rớt {crystal_drop} 💎."
            
            # Hồi 10% HP cho Valkyrie khi qua ải
            heal_amount = int(self.p_max_hp * 0.1)
            self.p_hp = min(self.p_max_hp, self.p_hp + heal_amount)
            combat_log += f" Valkyrie được hồi {heal_amount} HP."
            
            self.current_floor += 1
            self.e_data = generate_abyss_enemy(self.current_floor)
            combat_log += f"\n👹 **CẢNH BÁO:** {self.e_data['name']} xuất hiện!"

        # Nếu người chơi chết -> Tổng kết tháp
        if self.p_hp <= 0:
            for child in self.children:
                child.disabled = True
                
            user_id = str(self.author.id)
            self.p_profile["crystals"] += self.crystals_earned
            if self.current_floor > self.p_profile.get("abyss_floor", 0):
                self.p_profile["abyss_floor"] = self.current_floor
                
            save_kf_profile(user_id)
            
            embed_lose = discord.Embed(
                title="💀 KẾT THÚC CHUỖI SINH TỒN VỰC SÂU",
                description=f"{combat_log}\n\nValkyrie đã gục ngã tại **Tầng {self.current_floor}**.\n\n"
                            f"🎁 **TỔNG KẾT PHẦN THƯỞNG:**\n"
                            f"💎 Nhận được: **{self.crystals_earned:,} Pha lê**\n"
                            f"🏆 Kỷ lục cao nhất của bạn: **Tầng {self.p_profile['abyss_floor']}**",
                color=discord.Color.dark_grey()
            )
            await interaction.response.edit_message(embed=embed_lose, view=self)
            self.stop()
            return

        if self.p_evade_cooldown > 0:
            self.p_evade_cooldown -= 1

        p_hp_bar = make_progress_bar(max(0, self.p_hp), self.p_max_hp, 10)
        e_hp_bar = make_progress_bar(max(0, self.e_data["hp"]), self.e_data["max_hp"], 10)
        
        embed = discord.Embed(
            title=f"🌋 VỰC SÂU ABYSS - TẦNG {self.current_floor}",
            description=combat_log,
            color=discord.Color.dark_red()
        )
        
        suit = self.p_stats["suit"]
        embed.add_field(
            name=f"{suit['emoji']} {suit['name']}",
            value=f"❤️ HP: {max(0, self.p_hp)}/{self.p_max_hp}\n`{p_hp_bar}`\n⚡ SP: {self.p_sp} | Thu thập: {self.crystals_earned} 💎",
            inline=True
        )
        embed.add_field(name="VS", value="⚡", inline=True)
        type_icon = "🔺" if get_type_advantage(suit["type"], self.e_data["type"]) > 1 else ("🔻" if get_type_advantage(suit["type"], self.e_data["type"]) < 1 else "➖")
        embed.add_field(
            name=f"👹 {self.e_data['name']} {type_icon}",
            value=f"❤️ HP: {max(0, self.e_data['hp'])}/{self.e_data['max_hp']}\n`{e_hp_bar}`",
            inline=True
        )

        self.btn_ult.disabled = self.p_sp < suit["ult_sp_cost"]
        self.btn_evade.disabled = self.p_evade_cooldown > 0

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, custom_id="btn_atk")
    async def btn_atk(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_basic_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp += 5 
        
        crit_txt = " (💥)" if is_crit else ""
        log = f"🗡️ Dùng **{suit['skill_basic_name']}** gây **{dmg}** ST{crit_txt}."
        
        e_dmg, e_log = self.enemy_turn()
        log += f"\n{e_log}"
        
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Combo (Nhánh)", style=discord.ButtonStyle.success, custom_id="btn_combo")
    async def btn_combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_combo_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp += 2
        
        crit_txt = " (💥)" if is_crit else ""
        log = f"⚔️ Tung đòn Nhánh **{suit['skill_combo_name']}** gây **{dmg}** ST{crit_txt}."
        
        e_dmg, e_log = self.enemy_turn()
        log += f"\n{e_log}"
        
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, custom_id="btn_ult")
    async def btn_ult(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_sp < suit["ult_sp_cost"]:
            return await interaction.response.send_message("⚠️ Không đủ Năng lượng (SP)!", ephemeral=True)
            
        self.p_sp -= suit["ult_sp_cost"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        
        crit_txt = " (💥)" if is_crit else ""
        log = f"🔥 Kích hoạt **{suit['skill_ult_name']}** gây **{dmg}** ST{crit_txt}!"
        
        if self.e_data["hp"] > 0:
            log += f"\n🛡️ Kẻ địch bị choáng ngợp, bỏ qua lượt!"
            
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Né Cực Hạn", style=discord.ButtonStyle.secondary, custom_id="btn_evade")
    async def btn_evade(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_evade_cooldown > 0:
            return await interaction.response.send_message("⚠️ Kỹ năng Né đang hồi chiêu!", ephemeral=True)
            
        self.p_evade_cooldown = 3
        self.p_sp += 15 
        
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        e_dmg = int(max(5, raw_dmg))
        
        log = f"💨 Dùng **{suit['evade_name']}**! Né được **{e_dmg}** sát thương, hồi 15 SP."
        await self.update_battle_ui(interaction, log)

@kallen.command()
async def abyss(ctx):
    """
    Gọi chế độ Vực Sâu (Abyss) leo tháp vô tận
    Tốn 20 Thể lực, leo càng cao nhận càng nhiều Pha lê
    """
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    
    if p["stamina"] < 20:
        return await ctx.reply(f"⚠️ Thể lực hiện tại ({p['stamina']}/100) không đủ để vào Vực Sâu (Cần 20 ⚡).")
        
    p["stamina"] -= 20
    save_kf_profile(user_id)
    
    stats = calculate_kallen_stats(user_id)
    
    embed_start = discord.Embed(
        title="🌋 VỰC SÂU VÔ TẬN - MỞ CỔNG",
        description="Chào mừng đến Vực Sâu. Quái vật ở đây mạnh lên không ngừng. Bạn sẽ trụ được bao lâu?\n\n*Đang dịch chuyển Valkyrie...*",
        color=discord.Color.dark_red()
    )
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(2)
    
    view = AbyssCombatView(ctx.author, stats, p)
    initial_log = f"Cửa Vực Sâu mở ra. {view.e_data['name']} lao về phía bạn!"
    
    await view.update_battle_ui(ctx, initial_log)
    view.message = msg
# =====================================================================
# SỰ KIỆN HỆ THỐNG LÕI CỦA BOT (ON_MESSAGE, ON_READY)
# =====================================================================
@bot.event
async def on_message(message):
    """
    Sự kiện đọc tin nhắn:
    - Xử lý hệ thống kinh nghiệm (XP) cho người dùng chat
    - Không cấp XP cho người đang đi tù
    """
    if message.author.bot: 
        return
        
    user_id = str(message.author.id)
    user_data = load_user(user_id)
    
    # Kiểm tra án phạt: Nếu đang đi tù, không cho chat lên level
    jail_time_str = user_data.get("jail_time")
    if jail_time_str:
        jail_end = datetime.strptime(jail_time_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            # Cho phép process các lệnh (sẽ bị block ở global check) nhưng không cộng XP
            return await bot.process_commands(message)
            
    # Xử lý lên level bằng cách chat
    user_data["xp"] += random.randint(5, 15)
    
    current_level = user_data.get("level", 1)
    max_xp_required = current_level * 100
    
    # Thăng cấp
    if user_data["xp"] >= max_xp_required:
        user_data["xp"] -= max_xp_required
        user_data["level"] += 1
        
        # Phần thưởng thăng cấp
        reward = user_data["level"] * 150
        user_data["money"] += reward
        
        try: 
            embed_levelup = discord.Embed(
                description=f"🎉 Chúc mừng **{message.author.mention}** đã đột phá cảnh giới lên **Cấp độ {user_data['level']}**!\nPhần thưởng thăng cấp: **{reward:,} 💰**", 
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed_levelup)
        except Exception: 
            pass
            
    # Lưu lại DB sau mỗi lần chat
    save_user(user_id)
    
    # Kích hoạt xử lý các Commands
    await bot.process_commands(message)

@bot.event
async def on_ready(): 
    """Sự kiện chạy khi Bot online thành công"""
    print('================================================')
    print(f'>>> SIÊU BOT {bot.user} ĐÃ SẴN SÀNG CÀN QUÉT!')
    print('>>> BẢN CẬP NHẬT VIP 4.0 SIÊU HARDCORE - FULL TÍNH NĂNG VÀ GIF')
    print('================================================')
    
    # Thiết lập hoạt động hiển thị của Bot trên Discord
    await bot.change_presence(activity=discord.Game(name="Quản lý Sòng Bạc & Kinh Tế | k help"))

# =====================================================================
# LỆNH ADMIN (QUẢN TRỊ VIÊN) VÀ BƠM TIỀN
# =====================================================================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    """Thiết lập kênh cho phép dùng Bot"""
    server_id = str(ctx.guild.id)
    
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]: 
            del CONFIG_CACHE[server_id]["allowed_channels"]
            
        embed_clear = discord.Embed(description="✅ Đã gỡ bỏ giới hạn. Bot sẽ nhận lệnh ở **mọi kênh**.", color=discord.Color.green())
        return await ctx.send(embed=embed_clear)

    mentions = ctx.message.channel_mentions
    if not mentions: 
        embed_err = discord.Embed(description="⚠️ Vui lòng tag các kênh. VD: `k setup #kenh-1`", color=discord.Color.red())
        return await ctx.send(embed=embed_err)
        
    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    
    if server_id not in CONFIG_CACHE: 
        CONFIG_CACHE[server_id] = {}
        
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids
    
    embed_success = discord.Embed(description=f"✅ Đã cài đặt! Bot từ nay **CHỈ** nhận lệnh tại: {', '.join(c.mention for c in mentions)}", color=discord.Color.green())
    await ctx.send(embed=embed_success)

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    """Admin bơm tiền cho người chơi"""
    if amount > 0: 
        user_id = str(member.id)
        user_data = load_user(user_id)
        user_data["money"] += amount
        save_user(user_id)
        
        embed = discord.Embed(description=f"✅ Sếp tổng {ctx.author.mention} vừa buff nóng cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green())
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    """Admin trừ tiền người chơi"""
    if amount > 0: 
        user_id = str(member.id)
        user_data = load_user(user_id)
        user_data["money"] -= amount
        save_user(user_id)
        
        embed = discord.Embed(description=f"⚖️ Admin đã tước đoạt **{amount:,} 💰** từ tài khoản của {member.mention}!", color=discord.Color.red())
        await ctx.send(embed=embed)

# =====================================================================
# KHỞI ĐỘNG SERVER 24/7 VÀ CHẠY BOT BẰNG TOKEN
# =====================================================================
# Kích hoạt máy chủ web giả để Render/UptimeRobot ping giữ cho Bot online 24/7
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
