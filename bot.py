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
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]

users_col = db["users"]   
config_col = db["config"] 
companies_col = db["companies"]
kf_col = db["kallen_fantasy"]

DB_CACHE = {}
CONFIG_CACHE = {}
COMPANY_CACHE = {}
KF_CACHE = {}

def load_user(user_id):
    """Tải dữ liệu người dùng từ Database"""
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        document = users_col.find_one({"_id": user_id})
        if document:
            DB_CACHE[user_id] = document
        else:
            DB_CACHE[user_id] = {}
            
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
    """Lưu dữ liệu người dùng"""
    user_id = str(user_id)
    if user_id in DB_CACHE: 
        users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

def load_server_config(server_id):
    server_id = str(server_id)
    if server_id not in CONFIG_CACHE:
        document = config_col.find_one({"_id": server_id})
        if document: CONFIG_CACHE[server_id] = document
        else: CONFIG_CACHE[server_id] = {}
    return CONFIG_CACHE[server_id]

def load_company(company_id):
    company_id = str(company_id)
    if company_id not in COMPANY_CACHE:
        document = companies_col.find_one({"_id": company_id})
        if document: COMPANY_CACHE[company_id] = document
        else: return None
    return COMPANY_CACHE[company_id]

def save_company(company_id):
    company_id = str(company_id)
    if company_id in COMPANY_CACHE: 
        companies_col.update_one({"_id": company_id}, {"$set": COMPANY_CACHE[company_id]}, upsert=True)

def load_kf_profile(user_id):
    """Tải hồ sơ Kallen Fantasy"""
    user_id = str(user_id)
    if user_id not in KF_CACHE:
        doc = kf_col.find_one({"_id": user_id})
        if doc: KF_CACHE[user_id] = doc
        else: KF_CACHE[user_id] = {}
            
    defaults = {
        "level": 1, "exp": 0, "stamina": 100, "max_stamina": 100,
        "last_stamina_regen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "crystals": 0, "current_suit": "imayoh", "unlocked_suits": ["imayoh"],
        "inventory_weapons": ["wp_usp"], "equipped_weapon": "wp_usp",
        "inventory_stigmata": [], "equipped_stigmata": {"T": None, "M": None, "B": None},
        "cleared_stages": [], "abyss_floor": 1
    }
    
    for k, v in defaults.items():
        if k not in KF_CACHE[user_id]: KF_CACHE[user_id][k] = v
            
    last_regen = datetime.strptime(KF_CACHE[user_id]["last_stamina_regen"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    delta = now - last_regen
    minutes_passed = int(delta.total_seconds() / 60)
    
    if minutes_passed >= 5:
        stamina_to_add = minutes_passed // 5
        KF_CACHE[user_id]["stamina"] = min(KF_CACHE[user_id]["max_stamina"], KF_CACHE[user_id]["stamina"] + stamina_to_add)
        leftover_seconds = int(delta.total_seconds()) % 300
        new_regen_time = now - timedelta(seconds=leftover_seconds)
        KF_CACHE[user_id]["last_stamina_regen"] = new_regen_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Save ngay lập tức để đồng bộ database
        kf_col.update_one({"_id": user_id}, {"$set": KF_CACHE[user_id]}, upsert=True)

    return KF_CACHE[user_id]

def save_kf_profile(user_id):
    user_id = str(user_id)
    if user_id in KF_CACHE:
        kf_col.update_one({"_id": user_id}, {"$set": KF_CACHE[user_id]}, upsert=True)

# =====================================================================
# HÀM KIỂM TRA TỔNG THỂ (GLOBAL CHECKS)
# =====================================================================
@bot.check
async def global_jail_and_channel_check(ctx):
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
                            f"⏳ Thời gian mãn hạn tù: <t:{int(jail_end.timestamp())}:R>\n\n", 
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
    user_id = str(ctx.author.id)
    current_time = datetime.now()
    
    if user_id in gamble_cooldowns:
        time_difference = (current_time - gamble_cooldowns[user_id]).total_seconds()
        if time_difference < 4:
            time_left = int(4 - time_difference)
            embed_cooldown = discord.Embed(description=f"⏳ Đợi {time_left}s nữa hẵng lắc tiếp sếp ơi!", color=discord.Color.orange())
            await ctx.reply(embed=embed_cooldown, mention_author=False)
            return None, None
            
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) <= 0:
        embed_bankrupt = discord.Embed(description="💸 Tiền trong ví không có một xu mà đòi cá cược!", color=discord.Color.red())
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
        return None, None
        
    try: 
        if amount_str.lower() == "all":
            bet_amount = user_data["money"] if user_data["money"] <= 500000 else 500000
        else:
            bet_amount = int(amount_str)
    except ValueError: 
        embed_error = discord.Embed(description="⚠️ Nhập số tiền sai định dạng! Vui lòng nhập số hoặc chữ `all`.", color=discord.Color.red())
        await ctx.reply(embed=embed_error, mention_author=False)
        return None, None
        
    if bet_amount <= 0 or bet_amount > user_data["money"]: 
        embed_poor = discord.Embed(description=f"⚠️ Bạn chỉ có **{user_data['money']:,} 💰** trong ví thôi!", color=discord.Color.red())
        await ctx.reply(embed=embed_poor, mention_author=False)
        return None, None
        
    if bet_amount > 500000: 
        embed_max_bet = discord.Embed(description="🛑 Nhà cái quy định mỗi ván cược tối đa **500,000 💰** thôi nhé!", color=discord.Color.red())
        await ctx.reply(embed=embed_max_bet, mention_author=False)
        return None, None
        
    return user_data, bet_amount

# =====================================================================
# DATA KHO SHOP ĐẠI GIA (MỞ RỘNG CỰC LỚN)
# =====================================================================
SHOP_ITEMS = {
    # Hạng mục: Danh hiệu
    "title_1": {"type": "title", "name": "Dân Thường 🚶", "price": 10000, "emoji": "🏷️"},
    "title_2": {"type": "title", "name": "Học Sinh Ngoan 🎒", "price": 25000, "emoji": "🏷️"},
    "title_3": {"type": "title", "name": "Tiểu Thương 🏪", "price": 50000, "emoji": "🏷️"},
    "title_4": {"type": "title", "name": "Phú Nông 🌾", "price": 150000, "emoji": "🏷️"},
    "title_5": {"type": "title", "name": "Chủ Tịch 👔", "price": 500000, "emoji": "🏷️"},
    "title_6": {"type": "title", "name": "Đại Gia 💸", "price": 2000000, "emoji": "🏷️"},
    "title_7": {"type": "title", "name": "Tỷ Phú 💎", "price": 10000000, "emoji": "🏷️"},
    "title_8": {"type": "title", "name": "Tài Phiệt 🏛️", "price": 50000000, "emoji": "🏷️"},
    "title_9": {"type": "title", "name": "Thần Tài 🧧", "price": 200000000, "emoji": "🏷️"},
    "title_10": {"type": "title", "name": "Vua Của Thế Giới 👑", "price": 1000000000, "emoji": "👑"},

    # Hạng mục: Phương tiện di chuyển
    "vehicle_1": {"type": "vehicle", "name": "Giày Trượt Patin 🛹", "price": 5000, "emoji": "🛹"},
    "vehicle_2": {"type": "vehicle", "name": "Xe Đạp Thể Thao 🚲", "price": 15000, "emoji": "🚲"},
    "vehicle_3": {"type": "vehicle", "name": "Xe Đạp Điện 🛵", "price": 45000, "emoji": "🛵"},
    "vehicle_4": {"type": "vehicle", "name": "Honda Wave Alpha 🏍️", "price": 120000, "emoji": "🏍️"},
    "vehicle_5": {"type": "vehicle", "name": "Honda SH 150i 🏍️", "price": 350000, "emoji": "🏍️"},
    "vehicle_6": {"type": "vehicle", "name": "Kia Morning 🚗", "price": 1500000, "emoji": "🚗"},
    "vehicle_7": {"type": "vehicle", "name": "Toyota Camry 🚘", "price": 4000000, "emoji": "🚘"},
    "vehicle_8": {"type": "vehicle", "name": "Ford Everest 🚙", "price": 8000000, "emoji": "🚙"},
    "vehicle_9": {"type": "vehicle", "name": "Porsche Mustang 🏎️", "price": 15000000, "emoji": "🏎️"},
    "vehicle_10": {"type": "vehicle", "name": "Mercedes G63 🚙", "price": 30000000, "emoji": "🚙"},
    "vehicle_11": {"type": "vehicle", "name": "Lamborghini Aventador 🏎️", "price": 85000000, "emoji": "🏎️"},
    "vehicle_12": {"type": "vehicle", "name": "Trực Thăng Cá Nhân 🚁", "price": 250000000, "emoji": "🚁"},
    "vehicle_13": {"type": "vehicle", "name": "Du Thuyền Hạng Sang 🛥️", "price": 500000000, "emoji": "🛥️"},
    "vehicle_14": {"type": "vehicle", "name": "Máy Bay Phản Lực ✈️", "price": 1000000000, "emoji": "✈️"},
    "vehicle_15": {"type": "vehicle", "name": "Tàu Vũ Trụ UFO 🛸", "price": 5000000000, "emoji": "🛸"},

    # Hạng mục: Bất động sản
    "house_1": {"type": "house", "name": "Gầm Cầu 🌉", "price": 10000, "emoji": "🌉"},
    "house_2": {"type": "house", "name": "Lều Cắm Trại ⛺", "price": 50000, "emoji": "⛺"},
    "house_3": {"type": "house", "name": "Phòng Trọ 15m2 🛖", "price": 200000, "emoji": "🛖"},
    "house_4": {"type": "house", "name": "Chung Cư Mini 🏢", "price": 800000, "emoji": "🏢"},
    "house_5": {"type": "house", "name": "Nhà Cấp 4 🏠", "price": 2500000, "emoji": "🏠"},
    "house_6": {"type": "house", "name": "Nhà Phố 3 Tầng 🏘️", "price": 8000000, "emoji": "🏘️"},
    "house_7": {"type": "house", "name": "Penthouse Landmark 🏙️", "price": 25000000, "emoji": "🏙️"},
    "house_8": {"type": "house", "name": "Biệt Thự Vườn Hồ Tây 🏡", "price": 80000000, "emoji": "🏡"},
    "house_9": {"type": "house", "name": "Lâu Đài Phong Cách Âu 🏰", "price": 250000000, "emoji": "🏰"},
    "house_10": {"type": "house", "name": "Đảo Tư Nhân Maldives 🏝️", "price": 800000000, "emoji": "🏝️"},
    "house_11": {"type": "house", "name": "Căn Cứ Quân Sự Mật ☢️", "price": 2000000000, "emoji": "☢️"},
    "house_12": {"type": "house", "name": "Thành Phố Nổi Tương Lai 🌃", "price": 5000000000, "emoji": "🌃"},
    "house_13": {"type": "house", "name": "Mặt Trăng Của Riêng Bạn 🌕", "price": 10000000000, "emoji": "🌕"},
    "house_14": {"type": "house", "name": "Hành Tinh Namek 🪐", "price": 50000000000, "emoji": "🪐"},
    "house_15": {"type": "house", "name": "Lỗ Đen Vũ Trụ 🌌", "price": 100000000000, "emoji": "🌌"}
}

def get_asset_price(asset_name):
    """Bán lại tài sản cho chợ đen bị ép giá lỗ 30%"""
    for item_key, item_data in SHOP_ITEMS.items():
        if item_data["name"] == asset_name: 
            return int(item_data["price"] * 0.7)
    return 1000

# =====================================================================
# DATA GACHA THÚ CƯNG (MỞ RỘNG SỐ LƯỢNG)
# =====================================================================
PET_RATES = {
    "common": {
        "rate": 70.0, 
        "pool": [
            "Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", "Lợn Đất 🐖", "Cáo Nhỏ 🦊", "Chuột Đồng 🐁",
            "Cua Biển 🦀", "Rùa Đá 🐢", "Ếch Xanh 🐸", "Chuột Lang 🐹"
        ]
    },
    "rare": {
        "rate": 20.0, 
        "pool": [
            "Sói Tuyết 🐺", "Gấu Xám 🐻", "Đại Bàng 🦅", "Báo Gấm 🐆", "Linh Dương 🦌",
            "Đà Điểu 🦩", "Khỉ Vàng 🐒", "Cú Mèo 🦉"
        ]
    },
    "epic": {
        "rate": 7.0, 
        "pool": [
            "Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍", "Bạch Hổ 🐅", "Tê Giác Thiết Giáp 🦏",
            "Bò Cạp Độc 🦂", "Cá Mập Bạo Chúa 🦈", "Ngựa Hoang Mạc 🐎"
        ]
    },
    "legendary": {
        "rate": 2.5, 
        "pool": [
            "Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", "Phượng Hoàng Lửa 🦚", "Thủy Quái Leviathan 🐙",
            "Nhện Ma Thuật 🕷️", "Quạ Địa Ngục 🐦‍⬛"
        ]
    },
    "mythic": {
        "rate": 0.5, 
        "pool": [
            "Thần Long Hoàng Kim 🐲", "Hắc Ám Cự Thú 🦇", "Mèo Thần Tài Siêu Cấp 😻", "Godzilla Vĩ Đại 🦖",
            "King Kong Bất Diệt 🦧", "Thần Rùa Genbu 🐢"
        ]
    }
}

def get_pet_sell_price(pet_name):
    """Định giá bán thú cưng vào chợ đen theo độ hiếm"""
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 5000      
            if rarity == "rare": return 20000       
            if rarity == "epic": return 150000      
            if rarity == "legendary": return 800000 
            if rarity == "mythic": return 10000000   
    return 1000

# =====================================================================
# DATA KALLEN FANTASY (NHÂN VẬT, VŨ KHÍ, VẾT THÁNH MỞ RỘNG KHỦNG)
# =====================================================================
KALLEN_BATTLESUITS = {
    "imayoh": {
        "id": "imayoh", "name": "Ritual Imayoh (MECH)", "type": "MECH", "rarity": "A", 
        "base_hp": 1200, "base_atk": 250, "base_def": 150, "base_crt": 30, 
        "skill_basic_name": "Súng Kata", "skill_basic_dmg": 1.2, 
        "skill_combo_name": "Mưa Đạn Động Năng", "skill_combo_dmg": 2.5, 
        "skill_ult_name": "Khúc Ca Elysia", "skill_ult_dmg": 6.0, "ult_sp_cost": 80, 
        "evade_name": "Vết Nứt Không Gian", "emoji": "🔫"
    },
    "sundenjager": {
        "id": "sundenjager", "name": "Sündenjäger (MECH)", "type": "MECH", "rarity": "A", 
        "base_hp": 1400, "base_atk": 220, "base_def": 180, "base_crt": 25, 
        "skill_basic_name": "Xạ Kích Liên Thanh", "skill_basic_dmg": 1.0, 
        "skill_combo_name": "Càn Quét Tội Lỗi", "skill_combo_dmg": 2.2, 
        "skill_ult_name": "Oanh Tạc Quỹ Đạo", "skill_ult_dmg": 5.5, "ult_sp_cost": 75, 
        "evade_name": "Phản Xạ Vượt Cấp", "emoji": "🦇"
    },
    "sixth_serenade": {
        "id": "sixth_serenade", "name": "Sixth Serenade (PSY)", "type": "PSY", "rarity": "S", 
        "base_hp": 1500, "base_atk": 320, "base_def": 140, "base_crt": 40, 
        "skill_basic_name": "Dạ Khúc Dạ Tưởng", "skill_basic_dmg": 1.5, 
        "skill_combo_name": "Dấu Ấn Quạ Đen", "skill_combo_dmg": 3.0, 
        "skill_ult_name": "Bản Tình Ca Bóng Tối", "skill_ult_dmg": 8.0, "ult_sp_cost": 100, 
        "evade_name": "Vũ Điệu Quạ Đen", "emoji": "🎭"
    },
    "divine_prayer": {
        "id": "divine_prayer", "name": "Divine Prayer (BIO)", "type": "BIO", "rarity": "A", 
        "base_hp": 1800, "base_atk": 200, "base_def": 250, "base_crt": 20, 
        "skill_basic_name": "Quyền Cước Ánh Sáng", "skill_basic_dmg": 1.0, 
        "skill_combo_name": "Trừng Phạt Kẻ Thù", "skill_combo_dmg": 2.0, 
        "skill_ult_name": "Valkyrie Bộc Phát", "skill_ult_dmg": 5.0, "ult_sp_cost": 70, 
        "evade_name": "Thời Gian Ngưng Đọng", "emoji": "✨"
    },
    "herrscher_reason": {
        "id": "herrscher_reason", "name": "Herrscher of Reason (MECH)", "type": "MECH", "rarity": "S", 
        "base_hp": 1600, "base_atk": 400, "base_def": 200, "base_crt": 50, 
        "skill_basic_name": "Súng Pháo Lõi R", "skill_basic_dmg": 1.8, 
        "skill_combo_name": "Pháo Kích Oanh Tạc", "skill_combo_dmg": 3.5, 
        "skill_ult_name": "Dự Án Bunny Đột Kích", "skill_ult_dmg": 10.0, "ult_sp_cost": 120, 
        "evade_name": "Kiến Tạo Không Gian", "emoji": "🏍️"
    }
}

KALLEN_WEAPONS = {
    "wp_usp": {"id": "wp_usp", "name": "Súng Ngắn USP", "rarity": 2, "atk": 50, "crt": 5},
    "wp_colt": {"id": "wp_colt", "name": "Colt Peacemaker", "rarity": 3, "atk": 120, "crt": 10},
    "wp_water": {"id": "wp_water", "name": "Water Spirit Type-II", "rarity": 4, "atk": 200, "crt": 15},
    "wp_jingwei": {"id": "wp_jingwei", "name": "Cánh Chim Jingwei", "rarity": 4, "atk": 230, "crt": 20},
    "wp_aria": {"id": "wp_aria", "name": "Tranquil Arias", "rarity": 5, "atk": 350, "crt": 35},
    "wp_keys": {"id": "wp_keys", "name": "Keys of the Void", "rarity": 5, "atk": 380, "crt": 40},
    "wp_domain": {"id": "wp_domain", "name": "Domain of Revelation", "rarity": 5, "atk": 420, "crt": 45},
    "wp_judah": {"id": "wp_judah", "name": "Oath of Judah", "rarity": 5, "atk": 450, "crt": 20},
    "wp_shamash": {"id": "wp_shamash", "name": "Judgment of Shamash", "rarity": 5, "atk": 500, "crt": 10}
}

KALLEN_STIGMATA = {
    # Set Attila (Vật lý cơ bản)
    "stig_attila_t": {"id": "stig_attila_t", "name": "Attila (T)", "type": "T", "rarity": 3, "hp": 200, "atk": 40, "def": 30, "crt": 0},
    "stig_attila_m": {"id": "stig_attila_m", "name": "Attila (M)", "type": "M", "rarity": 3, "hp": 220, "atk": 0, "def": 45, "crt": 5},
    "stig_attila_b": {"id": "stig_attila_b", "name": "Attila (B)", "type": "B", "rarity": 3, "hp": 210, "atk": 30, "def": 35, "crt": 5},
    
    # Set Michelangelo (Sát thương bạo kích)
    "stig_michel_t": {"id": "stig_michel_t", "name": "Michelangelo (T)", "type": "T", "rarity": 5, "hp": 400, "atk": 100, "def": 50, "crt": 0},
    "stig_michel_m": {"id": "stig_michel_m", "name": "Michelangelo (M)", "type": "M", "rarity": 5, "hp": 450, "atk": 0, "def": 120, "crt": 10},
    "stig_michel_b": {"id": "stig_michel_b", "name": "Michelangelo (B)", "type": "B", "rarity": 5, "hp": 420, "atk": 70, "def": 60, "crt": 15},
    
    # Set Nohime (Sát thương Băng)
    "stig_nohime_t": {"id": "stig_nohime_t", "name": "Nohime (T)", "type": "T", "rarity": 5, "hp": 420, "atk": 110, "def": 40, "crt": 0},
    "stig_nohime_m": {"id": "stig_nohime_m", "name": "Nohime (M)", "type": "M", "rarity": 5, "hp": 480, "atk": 0, "def": 150, "crt": 5},
    "stig_nohime_b": {"id": "stig_nohime_b", "name": "Nohime (B)", "type": "B", "rarity": 5, "hp": 450, "atk": 80, "def": 50, "crt": 10},

    # Set Sirin Ascendant (Sát thương Vật lý trấn phái S)
    "stig_sirin_t": {"id": "stig_sirin_t", "name": "Sirin Ascendant (T)", "type": "T", "rarity": 5, "hp": 500, "atk": 125, "def": 60, "crt": 0},
    "stig_sirin_m": {"id": "stig_sirin_m", "name": "Sirin Ascendant (M)", "type": "M", "rarity": 5, "hp": 550, "atk": 20, "def": 180, "crt": 15},
    "stig_sirin_b": {"id": "stig_sirin_b", "name": "Sirin Ascendant (B)", "type": "B", "rarity": 5, "hp": 520, "atk": 85, "def": 80, "crt": 20},
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
    "1-3": {"name": "1-3: Bóng trắng đêm đen (Boss)", "enemies": ["zombie_1", "zombie_boss"], "reward_money": 15000, "reward_xp": 300},
    "2-1": {"name": "2-1: Cảnh báo Honkai", "enemies": ["beast_1", "beast_2", "beast_2"], "reward_money": 10000, "reward_xp": 200},
    "2-2": {"name": "2-2: Xung đột Titan", "enemies": ["mecha_1", "mecha_1", "mecha_2"], "reward_money": 12000, "reward_xp": 250},
    "2-3": {"name": "2-3: Đế vương sụp đổ (Boss)", "enemies": ["beast_2", "beast_boss"], "reward_money": 25000, "reward_xp": 500},
    "3-1": {"name": "3-1: Bầu trời cơ khí", "enemies": ["mecha_2", "mecha_2", "beast_2"], "reward_money": 18000, "reward_xp": 350},
    "3-2": {"name": "3-2: Vũ khí hủy diệt (Boss)", "enemies": ["mecha_1", "mecha_boss"], "reward_money": 40000, "reward_xp": 800},
    "4-1": {"name": "Chung Cuộc: Luật Giả (Raid Boss)", "enemies": ["god_boss"], "reward_money": 100000, "reward_xp": 2000}
}

def calculate_kallen_stats(user_id):
    p = load_kf_profile(user_id)
    suit = KALLEN_BATTLESUITS[p["current_suit"]]
    
    total_hp = suit["base_hp"]
    total_atk = suit["base_atk"]
    total_def = suit["base_def"]
    total_crt = suit["base_crt"]
    
    if p["equipped_weapon"]:
        wp = KALLEN_WEAPONS[p["equipped_weapon"]]
        total_atk += wp["atk"]
        total_crt += wp["crt"]
        
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
        "hp": int(total_hp * (1 + (p["level"] - 1) * 0.1)), 
        "atk": int(total_atk * (1 + (p["level"] - 1) * 0.1)),
        "def": int(total_def * (1 + (p["level"] - 1) * 0.1)),
        "crt": int(total_crt * (1 + (p["level"] - 1) * 0.1)),
    }

def get_type_advantage(attacker_type, defender_type):
    if attacker_type == "MECH" and defender_type == "BIO": return 1.3
    if attacker_type == "BIO" and defender_type == "PSY": return 1.3
    if attacker_type == "PSY" and defender_type == "MECH": return 1.3
    if attacker_type == "BIO" and defender_type == "MECH": return 0.7
    if attacker_type == "PSY" and defender_type == "BIO": return 0.7
    if attacker_type == "MECH" and defender_type == "PSY": return 0.7
    return 1.0
    # =====================================================================
# KALLEN FANTASY - GIAO DIỆN GACHA & QUẢN LÝ TÀI KHOẢN
# =====================================================================
class KallenGachaView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Tiếp Tế x1 (280 💎)", style=discord.ButtonStyle.primary, emoji="📦")
    async def roll_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 1)

    @discord.ui.button(label="Tiếp Tế x10 (2800 💎)", style=discord.ButtonStyle.danger, emoji="🎁")
    async def roll_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 10)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: 
            await interaction.response.send_message("⚠️ Không thể quay ké của người khác!", ephemeral=True)
            return False
        return True

    async def process_gacha(self, interaction: discord.Interaction, times: int):
        user_id = str(interaction.user.id)
        p = load_kf_profile(user_id)
        cost = 280 * times
        
        if p["crystals"] < cost:
            return await interaction.response.send_message(f"⚠️ Thuyền trưởng không đủ Pha lê! Cần {cost:,} 💎.", ephemeral=True)
            
        p["crystals"] -= cost
        results = []
        
        for _ in range(times):
            roll = random.uniform(0, 100)
            if roll <= 1.5: 
                suit = "herrscher_reason" if random.random() > 0.5 else "sixth_serenade"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"🌟 **VALKYRIE CẤP S:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"🌟 Valkyrie Cấp S (Trùng lặp, chuyển thành 1000 💎)")
                    p["crystals"] += 1000
            elif roll <= 5.0: 
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] == 5] + [k for k, v in KALLEN_STIGMATA.items() if v["rarity"] == 5]
                item = random.choice(pool)
                if item in KALLEN_WEAPONS:
                    p["inventory_weapons"].append(item)
                    results.append(f"🔶 **Vũ Khí 5★:** {KALLEN_WEAPONS[item]['name']}")
                else:
                    p["inventory_stigmata"].append(item)
                    results.append(f"💠 **Vết Thánh 5★:** {KALLEN_STIGMATA[item]['name']}")
            elif roll <= 15.0: 
                pool_suits = ["sundenjager", "divine_prayer"]
                suit = random.choice(pool_suits)
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"⭐ **VALKYRIE CẤP A:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"⭐ Valkyrie Cấp A (Trùng lặp, chuyển thành 280 💎)")
                    p["crystals"] += 280
            elif roll <= 45.0: 
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] == 4]
                if pool:
                    item = random.choice(pool)
                    p["inventory_weapons"].append(item)
                    results.append(f"🟦 Vũ Khí 4★: {KALLEN_WEAPONS[item]['name']}")
                else:
                    results.append("🟦 Tài nguyên Nâng cấp (50 💎)")
                    p["crystals"] += 50
            else: 
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] <= 3] + [k for k, v in KALLEN_STIGMATA.items() if v["rarity"] <= 3]
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
        embed.set_footer(text=f"Pha lê còn lại: {p['crystals']:,} 💎", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.edit_message(embed=embed, view=self)

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
    
    embed.add_field(name="Đang xuất chiến", value=f"**{suit['emoji']} {suit['name']}**", inline=False)
    embed.add_field(name="Chỉ số chiến đấu", value=f"❤️ HP: {stats['hp']} | ⚔️ ATK: {stats['atk']}\n🛡️ DEF: {stats['def']} | 💥 CRT: {stats['crt']}", inline=False)
    
    wp_name = KALLEN_WEAPONS[p["equipped_weapon"]]["name"] if p["equipped_weapon"] else "Tay Không"
    stig_t = KALLEN_STIGMATA[p["equipped_stigmata"]["T"]]["name"] if p["equipped_stigmata"]["T"] else "Trống"
    stig_m = KALLEN_STIGMATA[p["equipped_stigmata"]["M"]]["name"] if p["equipped_stigmata"]["M"] else "Trống"
    stig_b = KALLEN_STIGMATA[p["equipped_stigmata"]["B"]]["name"] if p["equipped_stigmata"]["B"] else "Trống"
    
    embed.add_field(name="Trang bị hiện tại", value=f"🔫 Vũ khí: {wp_name}\n💠 Vết thánh (T): {stig_t}\n💠 Vết thánh (M): {stig_m}\n💠 Vết thánh (B): {stig_b}", inline=False)
    
    cmds = (
        "`k kallen gacha` • Mở Kênh Tiếp Tế (Dùng Pha lê)\n"
        "`k kallen doipha <số lượng>` • Đổi Tiền mặt 💰 sang Pha lê 💎 (Tỷ giá 1,000💰 = 1💎)\n"
        "`k kallen equip <loại> <id>` • Lắp trang bị (loại: suit/wp/stig_t/stig_m/stig_b)\n"
        "`k kallen story <mã ải>` • Đi Cốt truyện\n"
        "`k kallen abyss` • Leo tháp Vực Sâu vô tận"
    )
    embed.add_field(name="Bảng Điều Khiển Hệ Thống", value=cmds, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command()
async def doipha(ctx, amount: int):
    """Đổi tiền server sang Pha lê Kallen Fantasy (Tỷ giá 1000 💰 = 1 💎)"""
    if amount <= 0: return await ctx.reply("Vui lòng nhập số lớn hơn 0.")
    
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

@kallen.command()
async def equip(ctx, category: str, item_id: str):
    """Trang bị Valkyrie, Vũ khí hoặc Vết thánh"""
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    category = category.lower()
    
    if category == "suit":
        if item_id not in KALLEN_BATTLESUITS: return await ctx.reply("⚠️ Tên Giáp Valkyrie không tồn tại.")
        if item_id not in p["unlocked_suits"]: return await ctx.reply("⚠️ Thuyền trưởng chưa mở khóa Giáp Valkyrie này (Vui lòng đi Gacha).")
        p["current_suit"] = item_id
        save_kf_profile(user_id)
        return await ctx.reply(f"✅ Đã xuất chiến Giáp Valkyrie: **{KALLEN_BATTLESUITS[item_id]['name']}**")
        
    elif category == "wp":
        if item_id not in KALLEN_WEAPONS: return await ctx.reply("⚠️ Mã Vũ khí không tồn tại.")
        if item_id not in p["inventory_weapons"]: return await ctx.reply("⚠️ Thuyền trưởng không sở hữu Vũ khí này.")
        p["equipped_weapon"] = item_id
        save_kf_profile(user_id)
        return await ctx.reply(f"✅ Đã trang bị Vũ khí: **{KALLEN_WEAPONS[item_id]['name']}**")
        
    elif category in ["stig_t", "stig_m", "stig_b"]:
        pos = category.split("_")[1].upper()
        if item_id not in KALLEN_STIGMATA: return await ctx.reply("⚠️ Mã Vết thánh không tồn tại.")
        if item_id not in p["inventory_stigmata"]: return await ctx.reply("⚠️ Thuyền trưởng không sở hữu Vết thánh này.")
        if KALLEN_STIGMATA[item_id]["type"] != pos: return await ctx.reply(f"⚠️ Vết thánh này không phải mảnh ({pos}).")
            
        p["equipped_stigmata"][pos] = item_id
        save_kf_profile(user_id)
        return await ctx.reply(f"✅ Đã lắp Vết thánh mảnh ({pos}): **{KALLEN_STIGMATA[item_id]['name']}**")
    else:
        await ctx.reply("⚠️ Sai cú pháp. Dùng: `suit`, `wp`, `stig_t`, `stig_m`, `stig_b`.")

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
# KALLEN FANTASY - LÕI CHIẾN ĐẤU (TURN-BASED COMBAT)
# =====================================================================
class KallenCombatView(discord.ui.View):
    def __init__(self, author, player_stats, stage_data, p_profile, is_abyss=False):
        super().__init__(timeout=300) 
        self.author = author
        self.p_stats = player_stats
        self.stage = stage_data
        self.p_profile = p_profile
        self.is_abyss = is_abyss
        
        self.p_hp = self.p_stats["hp"]
        self.p_max_hp = self.p_stats["hp"]
        self.p_sp = 0 
        self.p_evade_cooldown = 0
        
        self.crystals_earned = 0
        self.abyss_floor = 1

        if not self.is_abyss:
            self.enemy_list = self.stage["enemies"].copy()
            self.current_enemy_idx = 0
            self.load_enemy()
        else:
            self.load_abyss_enemy()

    def load_enemy(self):
        if self.current_enemy_idx < len(self.enemy_list):
            enemy_id = self.enemy_list[self.current_enemy_idx]
            base_enemy = KALLEN_ENEMIES[enemy_id]
            self.e_data = {
                "name": base_enemy["name"], "type": base_enemy["type"], "hp": base_enemy["hp"],
                "max_hp": base_enemy["hp"], "atk": base_enemy["atk"], "def": base_enemy["def"], "sp_drop": base_enemy["sp_drop"]
            }
            return True
        return False

    def load_abyss_enemy(self):
        enemy_pool = [e for k, e in KALLEN_ENEMIES.items() if "god_boss" not in k]
        base_enemy = random.choice(enemy_pool)
        multiplier = 1.0 + (self.abyss_floor * 0.15)
        self.e_data = {
            "name": f"{base_enemy['name']} (Tầng {self.abyss_floor})", "type": base_enemy["type"],
            "hp": int(base_enemy["hp"] * multiplier), "max_hp": int(base_enemy["hp"] * multiplier),
            "atk": int(base_enemy["atk"] * multiplier), "def": int(base_enemy["def"] * multiplier),
            "sp_drop": base_enemy["sp_drop"] + int(self.abyss_floor / 5)
        }

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Không thể can thiệp vào trận chiến của người khác!", ephemeral=True)
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
        if self.e_data["hp"] <= 0: return 0, "Quái vật đã bị tiêu diệt, không thể tấn công!"
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        final_dmg = int(max(5, raw_dmg))
        self.p_hp -= final_dmg
        return final_dmg, f"💥 **{self.e_data['name']}** phản công gây **{final_dmg}** sát thương!"

    async def update_battle_ui(self, interaction: discord.Interaction, combat_log: str):
        if self.e_data["hp"] <= 0:
            self.p_sp += self.e_data["sp_drop"] 
            combat_log += f"\n💀 **{self.e_data['name']}** đã bị hạ gục! Nhận {self.e_data['sp_drop']} SP."
            
            if self.is_abyss:
                crystal_drop = random.randint(5, 15) + int(self.abyss_floor / 2)
                self.crystals_earned += crystal_drop
                combat_log += f"\n✅ Vượt Tầng {self.abyss_floor}! Rớt {crystal_drop} 💎."
                
                heal_amount = int(self.p_max_hp * 0.1)
                self.p_hp = min(self.p_max_hp, self.p_hp + heal_amount)
                combat_log += f" Valkyrie được hồi {heal_amount} HP."
                
                self.abyss_floor += 1
                self.load_abyss_enemy()
                combat_log += f"\n👹 **CẢNH BÁO:** {self.e_data['name']} xuất hiện!"
            else:
                self.current_enemy_idx += 1
                if not self.load_enemy(): return await self.win_stage(interaction, combat_log)
                else: combat_log += f"\n⚠️ **CẢNH BÁO:** Kẻ địch tiếp theo [**{self.e_data['name']}**] xuất hiện!"

        if self.p_hp <= 0:
            return await self.lose_stage(interaction, combat_log)

        if self.p_evade_cooldown > 0: self.p_evade_cooldown -= 1

        p_hp_bar = make_progress_bar(max(0, self.p_hp), self.p_max_hp, 10)
        e_hp_bar = make_progress_bar(max(0, self.e_data["hp"]), self.e_data["max_hp"], 10)
        
        embed = discord.Embed(
            title=f"🌋 VỰC SÂU ABYSS - TẦNG {self.abyss_floor}" if self.is_abyss else f"⚔️ {self.stage['name'].upper()}",
            description=combat_log,
            color=discord.Color.dark_red() if self.is_abyss else discord.Color.red()
        )
        
        suit = self.p_stats["suit"]
        embed.add_field(
            name=f"{suit['emoji']} {suit['name']}",
            value=f"❤️ HP: {max(0, self.p_hp)}/{self.p_max_hp}\n`{p_hp_bar}`\n⚡ SP: {self.p_sp}" + (f" | Thu thập: {self.crystals_earned} 💎" if self.is_abyss else ""),
            inline=True
        )
        embed.add_field(name="VS", value="⚡", inline=True)
        type_icon = "🔺" if get_type_advantage(suit["type"], self.e_data["type"]) > 1 else ("🔻" if get_type_advantage(suit["type"], self.e_data["type"]) < 1 else "➖")
        embed.add_field(
            name=f"👹 {self.e_data['name']} ({self.e_data['type']}) {type_icon}",
            value=f"❤️ HP: {max(0, self.e_data['hp'])}/{self.e_data['max_hp']}\n`{e_hp_bar}`",
            inline=True
        )

        self.btn_ult.disabled = self.p_sp < suit["ult_sp_cost"]
        self.btn_evade.disabled = self.p_evade_cooldown > 0

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

    async def win_stage(self, interaction: discord.Interaction, combat_log: str):
        for child in self.children: child.disabled = True
        user_id = str(self.author.id)
        user_data = load_user(user_id)
        
        money_reward = self.stage["reward_money"]
        xp_reward = self.stage["reward_xp"]
        
        user_data["money"] += money_reward
        self.p_profile["exp"] += xp_reward
        
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
        for child in self.children: child.disabled = True
        user_id = str(self.author.id)
        
        if self.is_abyss:
            self.p_profile["crystals"] += self.crystals_earned
            if self.abyss_floor > self.p_profile.get("abyss_floor", 0):
                self.p_profile["abyss_floor"] = self.abyss_floor
            save_kf_profile(user_id)
            
            embed = discord.Embed(
                title="💀 KẾT THÚC CHUỖI SINH TỒN VỰC SÂU",
                description=f"{combat_log}\n\nValkyrie đã gục ngã tại **Tầng {self.abyss_floor}**.\n\n"
                            f"🎁 **TỔNG KẾT PHẦN THƯỞNG:**\n💎 Nhận được: **{self.crystals_earned:,} Pha lê**\n🏆 Kỷ lục: **Tầng {self.p_profile['abyss_floor']}**",
                color=discord.Color.dark_grey()
            )
        else:
            embed = discord.Embed(
                title="💀 NHIỆM VỤ THẤT BẠI",
                description=f"{combat_log}\n\nValkyrie của bạn đã gục ngã. Thể lực đã mất sẽ không được hoàn trả. Hãy nâng cấp trang bị và thử lại!",
                color=discord.Color.dark_grey()
            )
            
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, custom_id="btn_atk")
    async def btn_atk(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_basic_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp += 5 
        
        crit_txt = " (💥 BẠO KÍCH)" if is_crit else ""
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
        
        crit_txt = " (💥 BẠO KÍCH)" if is_crit else ""
        log = f"⚔️ Tung đòn Nhánh **{suit['skill_combo_name']}** gây **{dmg}** ST{crit_txt}."
        
        e_dmg, e_log = self.enemy_turn()
        log += f"\n{e_log}"
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, custom_id="btn_ult")
    async def btn_ult(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_sp < suit["ult_sp_cost"]: return await interaction.response.send_message("⚠️ Không đủ Năng lượng (SP)!", ephemeral=True)
            
        self.p_sp -= suit["ult_sp_cost"]
        dmg, is_crit, t_adv = self.calculate_damage(suit["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        
        crit_txt = " (💥 BẠO KÍCH)" if is_crit else ""
        log = f"🔥 Kích hoạt Tất Sát **{suit['skill_ult_name']}** gây **{dmg}** ST khủng khiếp{crit_txt}!"
        
        if self.e_data["hp"] > 0: log += f"\n🛡️ Đối phương bị choáng ngợp, bỏ qua lượt!"
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Né Cực Hạn", style=discord.ButtonStyle.secondary, custom_id="btn_evade")
    async def btn_evade(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_evade_cooldown > 0: return await interaction.response.send_message("⚠️ Kỹ năng Né đang hồi chiêu!", ephemeral=True)
            
        self.p_evade_cooldown = 3 
        self.p_sp += 15 
        
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        e_dmg = int(max(5, raw_dmg))
        
        log = f"💨 Dùng **{suit['evade_name']}**! Né hoàn toàn **{e_dmg}** sát thương, hồi 15 SP."
        await self.update_battle_ui(interaction, log)

@kallen.command()
async def story(ctx, stage_id: str = None):
    """Đi ải cốt truyện Kallen Fantasy"""
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

    if stage_id not in KALLEN_STAGES: return await ctx.reply("⚠️ Mã ải không tồn tại. Gõ `k kallen story list` để xem.")
    if p["stamina"] < 10: return await ctx.reply(f"⚠️ Thể lực hiện tại ({p['stamina']}/100) không đủ (Cần 10 ⚡).")
        
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
    
    view = KallenCombatView(ctx.author, stats, stage_data, p, is_abyss=False)
    await view.update_battle_ui(ctx, f"Bắt đầu ải: {stage_data['name']}. Kẻ địch đã xuất hiện!")

@kallen.command()
async def abyss(ctx):
    """Gọi chế độ Vực Sâu (Abyss) leo tháp vô tận"""
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    
    if p["stamina"] < 20: return await ctx.reply(f"⚠️ Thể lực hiện tại ({p['stamina']}/100) không đủ vào Vực Sâu (Cần 20 ⚡).")
        
    p["stamina"] -= 20
    save_kf_profile(user_id)
    stats = calculate_kallen_stats(user_id)
    
    embed_start = discord.Embed(
        title="🌋 VỰC SÂU VÔ TẬN - MỞ CỔNG",
        description="Quái vật ở đây mạnh lên không ngừng theo từng tầng. Bạn sẽ trụ được bao lâu?\n\n*Đang dịch chuyển Valkyrie...*",
        color=discord.Color.dark_red()
    )
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(2)
    
    view = KallenCombatView(ctx.author, stats, None, p, is_abyss=True)
    await view.update_battle_ui(ctx, f"Cửa Vực Sâu mở ra. {view.e_data['name']} lao về phía bạn!")

# =====================================================================
# GIAO DIỆN UI: CỬA HÀNG ĐẠI GIA VÀ CHỢ ĐEN (SHOP)
# =====================================================================
class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        options = []
        for key, item_data in SHOP_ITEMS.items():
            if item_data["type"] == category_type:
                options.append(discord.SelectOption(label=item_data['name'], description=f"Giá: {item_data['price']:,} 💰", value=key, emoji=item_data['emoji']))
        super().__init__(placeholder="Nhấn vào đây để chọn món đồ muốn tậu...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_info = SHOP_ITEMS[self.values[0]]
        
        if user_data.get("money", 0) < item_info["price"]:
            return await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ Thẻ từ chối! Cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", color=discord.Color.red()), ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            success_message = f"🎉 Tiền trao cháo múc! Đã trang bị danh hiệu: **{item_info['name']}**."
        else:
            if item_info["name"] in user_data.get("assets", []):
                user_data["money"] += item_info["price"] 
                return await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ Bạn đã sở hữu **{item_info['name']}** rồi!", color=discord.Color.orange()), ephemeral=True)
            
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Chúc mừng đại gia! Bạn vừa đập hộp siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        
        embed_success = discord.Embed(title="🛍️ GIAO DỊCH HOÀN TẤT!", description=success_message, color=discord.Color.green())
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
        await interaction.response.edit_message(embed=discord.Embed(title="🛍️ QUẦY BÁN DANH HIỆU", description="Mua danh hiệu VIP.", color=discord.Color.blue()), view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("vehicle"))
        await interaction.response.edit_message(embed=discord.Embed(title="🛍️ SHOWROOM XE CỘ", description="Mua phương tiện di chuyển.", color=discord.Color.green()), view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("house"))
        await interaction.response.edit_message(embed=discord.Embed(title="🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN", description="Đầu tư nhà đất.", color=discord.Color.red()), view=view)

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
                    options.append(discord.SelectOption(label=pet, description=f"Đang có: {quantity} | Thu: {get_pet_sell_price(pet):,} 💰", value=pet))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(label=asset, description=f"Ép giá còn: {get_asset_price(asset):,} 💰", value=asset))
                
        super().__init__(placeholder="Chọn món đồ muốn bán...", min_values=1, max_values=1, options=options)

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
            success_message = f"✅ Thương lái đã mua bé **{item_value}**. Nhận **{sell_price:,} 💰**!"
        else:
            if item_value not in user_data.get("assets", []): 
                return await interaction.response.send_message("Lỗi: Không có tài sản này!", ephemeral=True)
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            success_message = f"✅ Đã thâu tóm **{item_value}**. Bạn chịu lỗ nhận lại **{sell_price:,} 💰**!"

        user_data["money"] += sell_price
        save_user(user_id)
        await interaction.response.edit_message(embed=discord.Embed(title="🤝 GIAO DỊCH HOÀN TẤT", description=success_message, color=discord.Color.dark_orange()), view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Cắm Sổ Đỏ / Cầm Xe", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: return await interaction.response.send_message(embed=discord.Embed(description="Bạn không có tài sản nào để bán!", color=discord.Color.red()), ephemeral=True)
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        await interaction.response.edit_message(embed=discord.Embed(title="🏷️ CẦM ĐỒ BĐS & XE CỘ", description="Bán lại lỗ 30%.", color=discord.Color.orange()), view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(quantity == 0 for quantity in pets.values()): return await interaction.response.send_message(embed=discord.Embed(description="Chưa có thú cưng nào!", color=discord.Color.red()), ephemeral=True)
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        await interaction.response.edit_message(embed=discord.Embed(title="🏷️ THU MUA THÚ CƯNG", description="Bán thú cưng lấy tiền.", color=discord.Color.green()), view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id

# =====================================================================
# GIAO DIỆN UI: TRẠM TREO MÁY AFK & NHÂN SINH
# =====================================================================
class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Phần thưởng dự kiến: ~450 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Phần thưởng dự kiến: ~1000 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Phần thưởng dự kiến: ~2000 💰", emoji="🏛️", value="12")
        ]
        super().__init__(placeholder="Lựa chọn địa điểm hạ trại...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        hours = int(self.values[0])
        
        if hours == 4: reward = random.randint(300, 600)
        elif hours == 8: reward = random.randint(700, 1200)
        else: reward = random.randint(1500, 2500)
            
        end_time = datetime.now() + timedelta(hours=hours)
        user_data["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = reward
        save_user(user_id)

        await interaction.response.edit_message(embed=discord.Embed(title="⛺ LÊN ĐƯỜNG BÌNH AN!", description=f"Cắm trại **{hours} giờ**. Gõ `k phai` để thu hoạch sau.", color=discord.Color.green()), view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())
    async def interaction_check(self, interaction: discord.Interaction): 
        return interaction.user.id == self.author.id

class NhanSinhGameView(discord.ui.View):
    """Hệ thống lõi của Game Nhân Sinh Hardcore"""
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        self.ev = random.choice(EVENTS_P1)

        if self.stats["may_man"] >= 8: self.logs.append("👶 **Tuổi 0:** Sinh ra đã ngậm thìa vàng, bố mẹ là tài phiệt.")
        elif self.stats["may_man"] >= 4: self.logs.append("👶 **Tuổi 0:** Sinh ra trong gia đình công chức bình dân.")
        else: self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bị vứt ở bãi rác.")

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
            await interaction.response.send_message("⚠️ Nhân quả của ai người nấy gánh!", ephemeral=True)
            return False
        return True

    async def choice_a(self, interaction: discord.Interaction): await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        # Max rate = 85% dù điểm may mắn cao, buff mỗi điểm may mắn 1.5%
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
        log_entry = f"🎲 Tỉ lệ: **{final_rate:.1f}%** (Đổ ra: {roll:.1f})\n{status_icon}: {result_msg} ({money_change:,} 💰)"
        
        if self.phase == 1: tuoi_hien_tai = 15
        elif self.phase == 2: tuoi_hien_tai = 25
        elif self.phase == 3: tuoi_hien_tai = 35
        elif self.phase == 4: tuoi_hien_tai = 50
        else: tuoi_hien_tai = 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời khép lại.**")
            self.phase = 99 
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}")
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH (HARDCORE)", description=f"Ký chủ luân hồi: {self.author.mention}", color=discord.Color.teal())
        embed.add_field(name="🍀 Chỉ số ban đầu", value=f"May mắn: **{self.stats['may_man']}/10** *(Buff +{self.stats['may_man']*1.5}% Tỉ lệ)*", inline=False)

        story = "...\n\n" + "\n\n".join(self.logs[-4:]) if len(self.logs) > 4 else "\n\n".join(self.logs)
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase <= 5:
            tuoi_next = [15, 25, 35, 50, 70][self.phase-1]
            embed.add_field(name=f"❓ Ngã rẽ quyết định tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label, self.btn_b.label, self.btn_c.label, self.btn_d.label = f"A. {self.ev['choices'][0]['text'][:70]}", f"B. {self.ev['choices'][1]['text'][:70]}", f"C. {self.ev['choices'][2]['text'][:70]}", f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.btn_a.disabled = self.btn_b.disabled = self.btn_c.disabled = self.btn_d.disabled = True
            self.clear_items() 
            
            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

            user_data = load_user(user_id)
            user_data["money"] += self.tien_an
            save_user(user_id)

            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại một đống nợ khổng lồ, chủ nợ đến siết nhà.\n❌ **BÁO NHÀ!** Khoản nợ phải gánh: **{self.tien_an:,} 💰**", inline=False)
            elif self.tien_an >= 500000:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa vinh hoa.\n👑 **TỶ PHÚ!** Di sản: **+{self.tien_an:,} 💰**", inline=False)
            else:
                embed.color = discord.Color.blue()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Một cuộc đời êm ấm trôi qua.\n💼 **DƯ DẢ!** Di sản: **+{self.tien_an:,} 💰**", inline=False)

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)
            # =====================================================================
# GIAO DIỆN UI: ĐẤU TRƯỜNG SOLO OẲN TÙ TÌ
# =====================================================================
class SoloOTTGame(discord.ui.View):
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1
        self.player_2 = player_2
        self.bet_amount = bet_amount
        self.msg = None
        self.choices = {str(player_1.id): None, str(player_2.id): None}

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "🪨")

    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "📄")

    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "✂️")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = str(interaction.user.id)
        if user_id not in self.choices: return await interaction.response.send_message("⚠️ Tránh ra chỗ khác, đây là trận chiến riêng tư!", ephemeral=True)
        if self.choices[user_id] is not None: return await interaction.response.send_message("⚠️ Bạn đã ra chiêu rồi!", ephemeral=True)
            
        self.choices[user_id] = choice
        await interaction.response.send_message(embed=discord.Embed(description=f"🤫 Bạn đã chọn **{choice}**. Hãy chờ đối thủ...", color=discord.Color.green()), ephemeral=True)

        if self.choices[str(self.player_1.id)] is not None and self.choices[str(self.player_2.id)] is not None:
            for child in self.children: child.disabled = True
            choice_1, choice_2 = self.choices[str(self.player_1.id)], self.choices[str(self.player_2.id)]
            p1_data, p2_data = load_user(self.player_1.id), load_user(self.player_2.id)
            tong_thuong = self.bet_amount * 2
            
            if choice_1 == choice_2:
                ket_qua = "🤝 **HÒA NHAU!** Tiền cược được trả lại."
                p1_data["money"] += self.bet_amount
                p2_data["money"] += self.bet_amount
            elif (choice_1 == "🪨" and choice_2 == "✂️") or (choice_1 == "📄" and choice_2 == "🪨") or (choice_1 == "✂️" and choice_2 == "📄"):
                ket_qua = f"🎉 **{self.player_1.name} ĐÃ CHIẾN THẮNG!**\nHúp trọn **{tong_thuong:,} 💰**."
                p1_data["money"] += tong_thuong
            else:
                ket_qua = f"🎉 **{self.player_2.name} ĐÃ CHIẾN THẮNG!**\nHúp trọn **{tong_thuong:,} 💰**."
                p2_data["money"] += tong_thuong
                
            save_user(self.player_1.id); save_user(self.player_2.id)
            embed_result = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed_result.add_field(name=self.player_1.name, value=f"Ra {choice_1}", inline=True)
            embed_result.add_field(name="VS", value="⚡", inline=True)
            embed_result.add_field(name=self.player_2.name, value=f"Ra {choice_2}", inline=True)
            embed_result.add_field(name="KẾT QUẢ", value=ket_qua, inline=False)
            await self.msg.edit(embed=embed_result, view=self)
            self.stop()

    async def on_timeout(self):
        if self.choices[str(self.player_1.id)] is None or self.choices[str(self.player_2.id)] is None:
            p1_data, p2_data = load_user(self.player_1.id), load_user(self.player_2.id)
            p1_data["money"] += self.bet_amount
            p2_data["money"] += self.bet_amount
            save_user(self.player_1.id); save_user(self.player_2.id)
            try: await self.msg.edit(embed=discord.Embed(title="⏳ HẾT GIỜ", description="Trận đấu bị hủy, tiền cược đã hoàn trả!", color=discord.Color.dark_gray()), view=None)
            except Exception: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1, self.player_2, self.bet_amount = player_1, player_2, bet_amount

    @discord.ui.button(label="Nhận Kèo!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_2.id: return await interaction.response.send_message("⚠️ Kèo này gạ người khác!", ephemeral=True)
        p1_data, p2_data = load_user(self.player_1.id), load_user(self.player_2.id)
        
        if p1_data.get("money", 0) < self.bet_amount or p2_data.get("money", 0) < self.bet_amount:
            return await interaction.response.send_message("⚠️ Lỗi! Một trong hai không đủ tiền!", ephemeral=True)
        
        p1_data["money"] -= self.bet_amount
        p2_data["money"] -= self.bet_amount
        save_user(self.player_1.id); save_user(self.player_2.id)

        game_view = SoloOTTGame(self.player_1, self.player_2, self.bet_amount)
        embed_game = discord.Embed(title="⚔️ PK OẲN TÙ TÌ", description=f"{self.player_1.mention} 🆚 {self.player_2.mention}\nTiền cược: **{self.bet_amount:,} 💰**\n\n👇 **BẤM NÚT ĐỂ CHỌN CHIÊU**", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed_game, view=game_view)
        game_view.msg = interaction.message
        self.stop()

class MarryAccept(discord.ui.View):
    def __init__(self, sender, receiver):
        super().__init__(timeout=60)
        self.sender, self.receiver = sender, receiver
        
    @discord.ui.button(label="Đồng Ý", style=discord.ButtonStyle.success, emoji="💍")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: return await interaction.response.send_message("⚠️ Của người khác!", ephemeral=True)
        sender_data, receiver_data = load_user(self.sender.id), load_user(self.receiver.id)
        if sender_data.get("money", 0) < 1000000: return await interaction.response.send_message("⚠️ Chú rể hết tiền mua nhẫn rồi!", ephemeral=True)
            
        sender_data["money"] -= 1000000
        sender_data["spouse"] = str(self.receiver.id)
        receiver_data["spouse"] = str(self.sender.id)
        save_user(self.sender.id); save_user(self.receiver.id)
        
        for child in self.children: child.disabled = True
        embed_success = discord.Embed(title="💒 KẾT HÔN THÀNH CÔNG", description=f"🎉 Chúc mừng hai vợ chồng {self.sender.mention} và {self.receiver.mention}!", color=discord.Color.magenta())
        embed_success.set_image(url=GIF_LINKS["marry"])
        await interaction.response.edit_message(embed=embed_success, view=self)
        self.stop()
        
    @discord.ui.button(label="Từ Chối", style=discord.ButtonStyle.danger, emoji="💔")
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(description=f"💔 {self.receiver.mention} đã từ chối phũ phàng {self.sender.mention}...", color=discord.Color.dark_grey()), view=self)
        self.stop()

class CompanyInviteView(discord.ui.View):
    def __init__(self, comp_id, comp_name, target_user):
        super().__init__(timeout=60)
        self.comp_id, self.comp_name, self.target_user = comp_id, comp_name, target_user

    @discord.ui.button(label="Gia nhập", style=discord.ButtonStyle.success, emoji="🤝")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Không dành cho bạn!", ephemeral=True)
        target_id = str(self.target_user.id)
        target_data = load_user(target_id)
        if target_data.get("company"): return await interaction.response.send_message("⚠️ Bạn đã có cty!", ephemeral=True)
        
        comp = load_company(self.comp_id)
        if not comp: return await interaction.response.send_message("⚠️ Công ty đã phá sản!", ephemeral=True)
        
        comp["members"][target_id] = "nhanvien"
        target_data["company"] = self.comp_id
        save_company(self.comp_id); save_user(target_id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=f"🎉 {self.target_user.mention} đã gia nhập **{self.comp_name}**!", color=discord.Color.green()), view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=f"❌ {self.target_user.mention} đã từ chối lời mời của **{self.comp_name}**.", color=discord.Color.red()), view=None)

# =====================================================================
# KALLEN FANTASY - LÕI CHIẾN ĐẤU (TURN-BASED COMBAT UI)
# =====================================================================
class KallenCombatView(discord.ui.View):
    def __init__(self, author, player_stats, stage_data, p_profile, is_abyss=False):
        super().__init__(timeout=300) 
        self.author = author
        self.p_stats = player_stats
        self.stage = stage_data
        self.p_profile = p_profile
        self.is_abyss = is_abyss
        
        self.p_hp = self.p_stats["hp"]
        self.p_max_hp = self.p_stats["hp"]
        self.p_sp = 0 
        self.p_evade_cooldown = 0
        
        self.crystals_earned = 0
        self.abyss_floor = self.p_profile.get("abyss_floor", 1) if is_abyss else 1

        if not self.is_abyss:
            self.enemy_list = self.stage["enemies"].copy()
            self.current_enemy_idx = 0
            self.load_enemy()
        else:
            self.load_abyss_enemy()

    def load_enemy(self):
        if self.current_enemy_idx < len(self.enemy_list):
            enemy_id = self.enemy_list[self.current_enemy_idx]
            base_enemy = KALLEN_ENEMIES[enemy_id]
            self.e_data = {
                "name": base_enemy["name"], "type": base_enemy["type"], "hp": base_enemy["hp"],
                "max_hp": base_enemy["hp"], "atk": base_enemy["atk"], "def": base_enemy["def"], "sp_drop": base_enemy["sp_drop"]
            }
            return True
        return False

    def load_abyss_enemy(self):
        enemy_pool = [e for k, e in KALLEN_ENEMIES.items() if "god_boss" not in k]
        base_enemy = random.choice(enemy_pool)
        multiplier = 1.0 + (self.abyss_floor * 0.15)
        self.e_data = {
            "name": f"{base_enemy['name']} (Tầng {self.abyss_floor})", "type": base_enemy["type"],
            "hp": int(base_enemy["hp"] * multiplier), "max_hp": int(base_enemy["hp"] * multiplier),
            "atk": int(base_enemy["atk"] * multiplier), "def": int(base_enemy["def"] * multiplier),
            "sp_drop": base_enemy["sp_drop"] + int(self.abyss_floor / 5)
        }

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: return False
        return True

    def calculate_damage(self, dmg_multiplier):
        base_atk = self.p_stats["atk"]
        enemy_def = self.e_data["def"]
        type_adv = get_type_advantage(self.p_stats["suit"]["type"], self.e_data["type"])
        
        is_crit = False
        crit_mult = 1.0
        if random.uniform(0, 100) <= min(100, self.p_stats["crt"]):
            is_crit, crit_mult = True, 2.0 
                
        raw_dmg = (base_atk * dmg_multiplier * type_adv * crit_mult) - (enemy_def * 0.5)
        return int(max(10, raw_dmg)), is_crit

    def enemy_turn(self):
        if self.e_data["hp"] <= 0: return 0, "Quái vật đã bị tiêu diệt!"
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        final_dmg = int(max(5, raw_dmg))
        self.p_hp -= final_dmg
        return final_dmg, f"💥 **{self.e_data['name']}** phản công gây **{final_dmg}** sát thương!"

    async def update_battle_ui(self, interaction: discord.Interaction, combat_log: str):
        if self.e_data["hp"] <= 0:
            self.p_sp += self.e_data["sp_drop"] 
            combat_log += f"\n💀 **{self.e_data['name']}** bị hạ! Nhận {self.e_data['sp_drop']} SP."
            
            if self.is_abyss:
                crystal_drop = random.randint(5, 15) + int(self.abyss_floor / 2)
                self.crystals_earned += crystal_drop
                heal_amount = int(self.p_max_hp * 0.1)
                self.p_hp = min(self.p_max_hp, self.p_hp + heal_amount)
                combat_log += f"\n✅ Vượt Tầng {self.abyss_floor}! Rớt {crystal_drop} 💎. Hồi {heal_amount} HP."
                self.abyss_floor += 1
                self.load_abyss_enemy()
                combat_log += f"\n👹 **CẢNH BÁO:** {self.e_data['name']} xuất hiện!"
            else:
                self.current_enemy_idx += 1
                if not self.load_enemy():
                    for child in self.children: child.disabled = True
                    u_data = load_user(self.author.id)
                    u_data["money"] += self.stage["reward_money"]
                    self.p_profile["exp"] += self.stage["reward_xp"]
                    save_user(self.author.id); save_kf_profile(self.author.id)
                    embed = discord.Embed(title="🎉 VƯỢT ẢI THÀNH CÔNG!", description=f"{combat_log}\n\n🎁 **THƯỞNG:** {self.stage['reward_money']:,} 💰 | {self.stage['reward_xp']} EXP", color=discord.Color.green())
                    await interaction.response.edit_message(embed=embed, view=self)
                    return self.stop()
                else: combat_log += f"\n⚠️ **CẢNH BÁO:** Kẻ địch [**{self.e_data['name']}**] xuất hiện!"

        if self.p_hp <= 0:
            for child in self.children: child.disabled = True
            if self.is_abyss:
                self.p_profile["crystals"] += self.crystals_earned
                if self.abyss_floor > self.p_profile.get("abyss_floor", 0): self.p_profile["abyss_floor"] = self.abyss_floor
                save_kf_profile(self.author.id)
                desc = f"{combat_log}\n\nGục ngã tại **Tầng {self.abyss_floor}**.\n🎁 **THƯỞNG:** {self.crystals_earned:,} 💎"
            else: desc = f"{combat_log}\n\nValkyrie đã gục ngã. Hãy thử lại!"
            await interaction.response.edit_message(embed=discord.Embed(title="💀 NHIỆM VỤ THẤT BẠI", description=desc, color=discord.Color.dark_grey()), view=self)
            return self.stop()

        if self.p_evade_cooldown > 0: self.p_evade_cooldown -= 1

        p_hp_bar = make_progress_bar(max(0, self.p_hp), self.p_max_hp, 10)
        e_hp_bar = make_progress_bar(max(0, self.e_data["hp"]), self.e_data["max_hp"], 10)
        
        embed = discord.Embed(title=f"🌋 VỰC SÂU ABYSS - TẦNG {self.abyss_floor}" if self.is_abyss else f"⚔️ {self.stage['name'].upper()}", description=combat_log, color=discord.Color.dark_red() if self.is_abyss else discord.Color.red())
        suit = self.p_stats["suit"]
        embed.add_field(name=f"{suit['emoji']} {suit['name']}", value=f"❤️ HP: {max(0, self.p_hp)}/{self.p_max_hp}\n`{p_hp_bar}`\n⚡ SP: {self.p_sp}" + (f" | {self.crystals_earned} 💎" if self.is_abyss else ""), inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=f"👹 {self.e_data['name']} ({self.e_data['type']})", value=f"❤️ HP: {max(0, self.e_data['hp'])}/{self.e_data['max_hp']}\n`{e_hp_bar}`", inline=True)

        self.btn_ult.disabled = self.p_sp < suit["ult_sp_cost"]
        self.btn_evade.disabled = self.p_evade_cooldown > 0

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, custom_id="btn_atk")
    async def btn_atk(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit = self.calculate_damage(suit["skill_basic_dmg"])
        self.e_data["hp"] -= dmg; self.p_sp += 5 
        log = f"🗡️ Dùng **{suit['skill_basic_name']}** gây **{dmg}** ST" + (" (💥)" if is_crit else "") + "."
        e_dmg, e_log = self.enemy_turn()
        await self.update_battle_ui(interaction, log + f"\n{e_log}")

    @discord.ui.button(label="Combo", style=discord.ButtonStyle.success, custom_id="btn_combo")
    async def btn_combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit = self.calculate_damage(suit["skill_combo_dmg"])
        self.e_data["hp"] -= dmg; self.p_sp += 2
        log = f"⚔️ Đòn Nhánh **{suit['skill_combo_name']}** gây **{dmg}** ST" + (" (💥)" if is_crit else "") + "."
        e_dmg, e_log = self.enemy_turn()
        await self.update_battle_ui(interaction, log + f"\n{e_log}")

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, custom_id="btn_ult")
    async def btn_ult(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_sp < suit["ult_sp_cost"]: return await interaction.response.send_message("⚠️ Không đủ SP!", ephemeral=True)
        self.p_sp -= suit["ult_sp_cost"]; dmg, is_crit = self.calculate_damage(suit["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        log = f"🔥 Tất Sát **{suit['skill_ult_name']}** gây **{dmg}** ST khủng khiếp!" + (" (💥)" if is_crit else "")
        if self.e_data["hp"] > 0: log += f"\n🛡️ Đối phương bị choáng ngợp, bỏ qua lượt!"
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Né", style=discord.ButtonStyle.secondary, custom_id="btn_evade")
    async def btn_evade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.p_evade_cooldown > 0: return await interaction.response.send_message("⚠️ Đang hồi chiêu!", ephemeral=True)
        self.p_evade_cooldown = 3; self.p_sp += 15 
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        e_dmg = int(max(5, (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)))
        await self.update_battle_ui(interaction, f"💨 Dùng **{self.p_stats['suit']['evade_name']}**! Né hoàn toàn **{e_dmg}** ST, hồi 15 SP.")

# =====================================================================
# LỆNH KALLEN FANTASY CƠ BẢN (STORY & ABYSS)
# =====================================================================
@kallen.command()
async def story(ctx, stage_id: str = None):
    """Đi ải cốt truyện Kallen Fantasy"""
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    
    if stage_id is None or stage_id.lower() == "list":
        desc = "".join([f"{'✅' if s_id in p['cleared_stages'] else '🔒'} **Ải {s_id}**: {s_data['name']} (Thưởng: {s_data['reward_money']:,} 💰)\n" for s_id, s_data in KALLEN_STAGES.items()])
        return await ctx.reply(embed=discord.Embed(title="📜 DANH SÁCH ẢI CỐT TRUYỆN", description=desc, color=discord.Color.dark_purple()).set_footer(text="Dùng: k kallen story <mã> (Tốn 10 Thể lực)"), mention_author=False)

    if stage_id not in KALLEN_STAGES: return await ctx.reply("⚠️ Mã ải không tồn tại.")
    if p["stamina"] < 10: return await ctx.reply(f"⚠️ Không đủ thể lực ({p['stamina']}/100). Cần 10 ⚡.")
        
    p["stamina"] -= 10
    save_kf_profile(user_id)
    stage_data = KALLEN_STAGES[stage_id]
    
    msg = await ctx.reply(embed=discord.Embed(title=f"🚀 XUẤT KÍCH: {stage_data['name']}", description="Đang tải dữ liệu chiến trường...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(2)
    view = KallenCombatView(ctx.author, calculate_kallen_stats(user_id), stage_data, p, is_abyss=False)
    await view.update_battle_ui(ctx, f"Bắt đầu ải: {stage_data['name']}. Kẻ địch đã xuất hiện!")

@kallen.command()
async def abyss(ctx):
    """Chế độ Vực Sâu (Abyss) leo tháp vô tận"""
    user_id = str(ctx.author.id)
    p = load_kf_profile(user_id)
    if p["stamina"] < 20: return await ctx.reply(f"⚠️ Không đủ thể lực ({p['stamina']}/100). Cần 20 ⚡.")
        
    p["stamina"] -= 20
    save_kf_profile(user_id)
    msg = await ctx.reply(embed=discord.Embed(title="🌋 VỰC SÂU VÔ TẬN - MỞ CỔNG", description="Quái vật mạnh dần theo từng tầng. Bạn trụ được bao lâu?", color=discord.Color.dark_red()), mention_author=False)
    await asyncio.sleep(2)
    view = KallenCombatView(ctx.author, calculate_kallen_stats(user_id), None, p, is_abyss=True)
    await view.update_battle_ui(ctx, f"Cửa Vực Sâu mở ra. {view.e_data['name']} lao về phía bạn!")
    # =====================================================================
# HỆ THỐNG CÔNG TY, NGÂN HÀNG & CHỨNG KHOÁN (IPO)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    u = load_user(ctx.author.id)
    embed = discord.Embed(title="🏦 NGÂN HÀNG TRUNG ƯƠNG SERVER", description="Gửi tiền an toàn tuyệt đối khỏi trộm cắp và Casino!\n📥 `k bank gui <tiền / all>`\n📤 `k bank rut <tiền / all>`", color=discord.Color.blue())
    embed.add_field(name="💳 Ví (Wallet)", value=f"**{u.get('money', 0):,} 💰**", inline=True)
    embed.add_field(name="🏦 Két sắt (Bank)", value=f"**{u.get('bank', 0):,} 💰**", inline=True)
    embed.set_thumbnail(url=GIF_LINKS["bank"])
    await ctx.reply(embed=embed, mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    u = load_user(ctx.author.id)
    try: amt = u["money"] if amount.lower() == "all" else int(amount)
    except ValueError: return await ctx.reply("⚠️ Lỗi định dạng.")
    if amt <= 0 or amt > u["money"]: return await ctx.reply("⚠️ Số tiền trong ví không đủ để gửi!")
    u["money"] -= amt; u["bank"] = u.get("bank", 0) + amt
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Đã gửi an toàn **{amt:,} 💰** vào két sắt!", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    u = load_user(ctx.author.id)
    bank_bal = u.get("bank", 0)
    try: amt = bank_bal if amount.lower() == "all" else int(amount)
    except ValueError: return await ctx.reply("⚠️ Lỗi định dạng.")
    if amt <= 0 or amt > bank_bal: return await ctx.reply("⚠️ Số dư két sắt không đủ!")
    u["bank"] -= amt; u["money"] += amt
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Đã rút **{amt:,} 💰** ra ví!", color=discord.Color.green()), mention_author=False)

@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    all_stocks = get_all_stocks()
    embed = discord.Embed(title="📈 SÀN CHỨNG KHOÁN (IPO & MẶC ĐỊNH)", description=f"Cập nhật giá mới vào: <t:{get_next_hour_timestamp()}:R>\n🛒 Mua: `k ck buy <MÃ> <SL>` | 💸 Bán: `k ck sell <MÃ> <SL>`\n🏢 Lên Sàn: `k ck ipo`", color=discord.Color.blue())
    for code, name in all_stocks.items():
        price_now = get_stock_price(code, 0)
        price_old = get_stock_price(code, -1)
        if price_now <= 1000: trend, diff = "💀 HỦY NIÊM YẾT", 0
        else: trend, diff = ("🟩 Lên", price_now - price_old) if price_now > price_old else ("🟥 Xuống", price_old - price_now)
        embed.add_field(name=f"🏢 {code} - {name}", value=f"Giá: **{price_now:,} 💰**\n*({trend} {diff:,})*", inline=False)
        
    my_stocks = load_user(ctx.author.id).get("stocks", {})
    inv_str = "".join([f"🔸 {c}: {q} CP (Trị giá: {get_stock_price(c, 0) * q:,} 💰)\n" for c, q in my_stocks.items() if q > 0])
    embed.add_field(name="🎒 Cổ phiếu nắm giữ", value=inv_str if inv_str else "Trống trơn.", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    if code not in get_all_stocks(): return await ctx.reply("⚠️ Mã CK không tồn tại!")
    if qty <= 0: return await ctx.reply("⚠️ Số lượng > 0!")
    price = get_stock_price(code, 0)
    if price <= 1000: return await ctx.reply("⚠️ Công ty đã phá sản/hủy niêm yết!")
    total = price * qty
    u = load_user(ctx.author.id)
    if u.get("money", 0) < total: return await ctx.reply(f"⚠️ Thiếu tiền! Cần **{total:,} 💰**.")
    u["money"] -= total
    
    # RUG PULL (15% nổ nếu đầu tư > 50 triệu)
    if total >= 50000000 and random.randint(1, 100) <= 15:
        save_user(ctx.author.id)
        embed = discord.Embed(title="🚨 RUG PULL 🚨", description=f"**CEO CÔNG TY ÔM TIỀN BỎ TRỐN!**\nSàn đóng băng mã {code}, bạn mất trắng **{total:,} 💰**!", color=discord.Color.red())
        embed.set_image(url=GIF_LINKS["rugpull"])
        return await ctx.reply(embed=embed, mention_author=False)
        
    u.setdefault("stocks", {})[code] = u.get("stocks", {}).get(code, 0) + qty
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ BUY thành công **{qty} {code}** hết **{total:,} 💰**.", color=discord.Color.green()), mention_author=False)

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper()
    u = load_user(ctx.author.id)
    if code not in get_all_stocks() or u.get("stocks", {}).get(code, 0) < qty or qty <= 0: return await ctx.reply("⚠️ Không hợp lệ hoặc không đủ số lượng!")
    total = get_stock_price(code, 0) * qty
    u["stocks"][code] -= qty
    if u["stocks"][code] == 0: del u["stocks"][code]
    u["money"] += total
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ SELL thành công **{qty} {code}**, thu về **{total:,} 💰**.", color=discord.Color.gold()), mention_author=False)

@chungkhoan.command()
async def ipo(ctx):
    comp_id = load_user(ctx.author.id).get("company")
    if not comp_id: return await ctx.reply("⚠️ Cần gia nhập/tạo công ty trước!")
    comp = load_company(comp_id)
    if comp["members"].get(str(ctx.author.id)) != "boss": return await ctx.reply("⚠️ Chỉ Chủ Tịch mới được quyền IPO!")
    if comp.get("is_ipo"): return await ctx.reply("⚠️ Công ty đã lên sàn rồi!")
    if comp["treasury"] < 50000000: return await ctx.reply("⚠️ Quỹ công ty phải đạt **50 Triệu 💰** mới được niêm yết!")
    comp["is_ipo"] = True
    save_company(comp_id)
    await ctx.reply(embed=discord.Embed(title="📈 CHÀO SÀN", description=f"Tập đoàn **{comp['name']}** đã IPO!\nMã cổ phiếu: **{comp['name'][:4].upper()}**", color=discord.Color.green()), mention_author=False)

@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    u = load_user(ctx.author.id)
    comp_id = u.get("company")
    if not comp_id: return await ctx.send(embed=discord.Embed(title="🏢 CÔNG TY", description="Bạn đang thất nghiệp. Gõ `k cty tao <tên>` (500k 💰).", color=discord.Color.red()))
    comp = load_company(comp_id)
    if not comp:
        u["company"] = None; save_user(ctx.author.id)
        return await ctx.send("Công ty đã phá sản!")
    role = comp["members"].get(str(ctx.author.id), "nhanvien")
    embed = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed.add_field(name="Chức vụ", value=f"**{comp['roles'].get(role, role)}**", inline=False)
    cmds = "`k cty gop <tiền>` | `k cty thulai` | `k cty roi`"
    if role in ["boss", "quanly"]: cmds += "\n`k cty tuyen @user` | `k cty duoi @user`"
    if role == "boss": cmds += "\n`k cty luong <tiền>` | `k cty chucvu @user <role>` | `k cty doitenchuc <role> <tên>`"
    embed.add_field(name="Bảng Lệnh", value=cmds, inline=False)
    await ctx.send(embed=embed)

@cty.command()
async def tao(ctx, *, name: str):
    u_id = str(ctx.author.id)
    u = load_user(u_id)
    if u.get("company"): return await ctx.reply("⚠️ Bạn đã có cty!")
    if u.get("money", 0) < 500000: return await ctx.reply("⚠️ Phí tạo là 500k!")
    u["money"] -= 500000; u["company"] = u_id
    COMPANY_CACHE[u_id] = {"_id": u_id, "name": name, "treasury": 0, "members": {u_id: "boss"}, "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, "last_interest": "2000-01-01 00:00:00", "is_ipo": False}
    save_company(u_id); save_user(u_id)
    await ctx.send(embed=discord.Embed(title="🏢 KHAI TRƯƠNG", description=f"Tạo thành công **{name}**!", color=discord.Color.green()))

@cty.command()
async def roi(ctx):
    u_id = str(ctx.author.id)
    u = load_user(u_id)
    c_id = u.get("company")
    if not c_id: return await ctx.reply("Bạn chưa có cty!")
    comp = load_company(c_id)
    if comp and comp["members"].get(u_id) == "boss":
        COMPANY_CACHE.pop(c_id, None); companies_col.delete_one({"_id": c_id})
        for m_id in list(comp["members"].keys()): 
            m = load_user(m_id); m["company"] = None; save_user(m_id)
        embed = discord.Embed(description="🏢 Bão tố! Chủ tịch bỏ trốn, công ty **PHÁ SẢN**!", color=discord.Color.red())
        embed.set_image(url=GIF_LINKS["bankrupt"])
        await ctx.reply(embed=embed, mention_author=False)
    else:
        if comp and u_id in comp["members"]: del comp["members"][u_id]
        u["company"] = None; save_user(u_id); save_company(c_id)
        await ctx.reply(embed=discord.Embed(description="🎒 Bạn đã từ chức.", color=discord.Color.dark_grey()), mention_author=False)

@bot.command()
async def daichien(ctx, member: discord.Member = None, tactic: str = None):
    u_id = str(ctx.author.id)
    c_id = load_user(u_id).get("company")
    if not member or not tactic or tactic.lower() not in ["hack", "phot", "giangho"]:
        embed = discord.Embed(title="⚔️ ĐẠI CHIẾN CÔNG TY", description="Cách dùng: `k daichien @user <hack/phot/giangho>`", color=discord.Color.red())
        embed.set_image(url=GIF_LINKS["fight"])
        return await ctx.send(embed=embed)
    
    t_cid = load_user(member.id).get("company")
    if u_id == str(member.id) or not c_id or not t_cid or c_id == t_cid: return await ctx.reply("⚠️ Lỗi không hợp lệ!")
    
    now = datetime.now()
    if c_id in cty_cooldowns and (now - cty_cooldowns[c_id]).total_seconds() < 3600: return await ctx.reply("⏳ Công ty đang nghỉ ngơi, đợi 1h!")
    
    c1, c2 = load_company(c_id), load_company(t_cid)
    if c2["treasury"] < 10000: return await ctx.reply("⚠️ Quỹ đối thủ quá nghèo!")
    
    cty_cooldowns[c_id] = now
    tc = tactic.lower()
    wr, w_pct, l_pct, nm = (30, 0.1, 0.05, "HACK") if tc == "hack" else (50, 0.05, 0.02, "PHỐT") if tc == "phot" else (70, 0.02, 0.01, "GIANG HỒ")
    
    msg = await ctx.send(embed=discord.Embed(description=f"⚔️ **{c1['name']}** đang dùng **{nm}** lên **{c2['name']}**...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= wr:
        steal = int(c2["treasury"] * w_pct)
        c1["treasury"] += steal; c2["treasury"] -= steal
        save_company(c_id); save_company(t_cid)
        await msg.edit(embed=discord.Embed(description=f"🔥 **ĐẠI THẮNG!** Cướp được **{steal:,} 💰**!", color=discord.Color.green()).set_image(url=GIF_LINKS["fight"]))
    else:
        fine = int(c1["treasury"] * l_pct)
        c1["treasury"] -= fine; c2["treasury"] += fine
        save_company(c_id); save_company(t_cid)
        await msg.edit(embed=discord.Embed(description=f"💀 **THẤT BẠI!** Đền bù **{fine:,} 💰**.", color=discord.Color.red()))

# =====================================================================
# HỆ THỐNG LỆNH CƠ BẢN VÀ MINIGAME (RANK, CASINO, CƯỚP BANK...)
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH BOT UPDATE 2026", description="Tiền tố: `k ` hoặc `K `.", color=discord.Color.blurple())
    embed.add_field(name="🏦 KINH TẾ", value="`k rank`, `k tuido`, `k bank`, `k cuahang`, `k choden`\n`k daily`, `k lixi`, `k give`, `k top`, `k marry @user`", inline=False)
    embed.add_field(name="🏢 CÔNG TY & CHỨNG KHOÁN", value="`k cty tao <tên>`, `k cty`, `k ck`, `k daichien @user`", inline=False)
    embed.add_field(name="🎮 CASINO", value="`k coin <tiền>`, `k taixiu <tài/xỉu> <tiền>`, `k baucua <vật> <tiền>`, `k duathu <vật> <tiền>`, `k nohu <tiền>`", inline=False)
    embed.add_field(name="⛏️ NHẬP VAI", value="`k cuopnganhang`, `k daovang`, `k nhansinh`, `k thamhiem`, `k phai`, `k gacha`", inline=False)
    embed.add_field(name="🌌 KALLEN FANTASY (Gacha RPG)", value="`k kallen`, `k kallen gacha`, `k kallen equip`, `k kallen story`, `k kallen abyss`", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def rank(ctx):
    u = load_user(ctx.author.id)
    embed = discord.Embed(title=f"💳 CĂN CƯỚC: {ctx.author.name.upper()}", color=discord.Color.gold() if u.get("money",0) > 1000000 else discord.Color.teal())
    embed.set_thumbnail(url=GIF_LINKS["rank"])
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{u.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {u.get('level',1)}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{u.get('money',0):,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{u.get('bank',0):,} 💰**", inline=True)
    embed.add_field(name="✨ Kinh Nghiệm", value=f"`{make_progress_bar(u.get('xp',0), u.get('level',1)*100)}`\n**{u.get('xp',0)}/{u.get('level',1)*100} XP**", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    u_id = str(ctx.author.id); u = load_user(u_id); now = datetime.now()
    if u.get("money", 0) < 50000: return await ctx.reply(embed=discord.Embed(description="⚠️ Cần 50k mua súng M4A1!", color=discord.Color.red()), mention_author=False)
    if u_id in cty_cooldowns and (now - cty_cooldowns[u_id]).total_seconds() < 3600: return await ctx.reply("⏳ Truy nã 5 sao! Đợi 1 tiếng.", mention_author=False)
    cty_cooldowns[u_id] = now
    
    msg = await ctx.send(embed=discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Xông vào Ngân hàng Trung ương...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= 20: 
        loot = random.randint(200000, 800000); u["money"] += loot; save_user(u_id)
        await msg.edit(embed=discord.Embed(title="🎉 TRÓT LỌT!", description=f"Vơ vét sạch! Húp **{loot:,} 💰**!", color=discord.Color.green()).set_image(url=GIF_LINKS["rob_success"]))
    else: 
        u["money"] -= 50000; u["jail_time"] = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"); save_user(u_id)
        await msg.edit(embed=discord.Embed(title="🚨 BỊ TÓM GỌN", description="Đặc nhiệm SWAT ập tới! Mất 50k và đi tù 10 phút!", color=discord.Color.red()).set_image(url=GIF_LINKS["rob_fail"]))

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    u_id = str(ctx.author.id); u = load_user(u_id); now = datetime.now()
    if u_id in work_cooldowns and (now - work_cooldowns[u_id]).total_seconds() < 30: return await ctx.reply("⏳ Đợi 30s!", mention_author=False)
    
    if "Cuốc Chim ⛏️" not in u.get("assets", []):
        if u.get("money", 0) < 5000: return await ctx.reply("⚠️ Cần 5000 💰 mua cuốc!")
        u["money"] -= 5000; u["assets"].append("Cuốc Chim ⛏️")
        await ctx.send("🛒 Đã trừ 5k mua Cuốc Chim.")
        
    work_cooldowns[u_id] = now
    msg = await ctx.send(embed=discord.Embed(description="⛏️ Cạch... Đang đào...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2)
    
    roll = random.randint(1, 100)
    if roll <= 40: name, val = "Đá 🪨", 0
    elif roll <= 70: name, val = "Sắt Vụn 🔩", random.randint(1000, 3000)
    elif roll <= 90: name, val = "Vàng 🥇", random.randint(8000, 15000)
    elif roll <= 98: name, val = "Kim Cương 💎", random.randint(50000, 100000)
    else: 
        pen = int(u["money"] * 0.1); u["money"] -= pen; save_user(u_id)
        return await msg.edit(embed=discord.Embed(description=f"💥 **BÙM!** Đào trúng bom! Phạt **{pen:,} 💰**.", color=discord.Color.red()))

    u["money"] += val; save_user(u_id)
    await msg.edit(embed=discord.Embed(description=f"⛏️ Đào trúng: **{name}**\nBán được: **{val:,} 💰**", color=discord.Color.green()).set_thumbnail(url=GIF_LINKS["mine"]))

@bot.command()
async def coin(ctx, amount: str):
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    u_id = str(ctx.author.id); u["money"] -= bet; save_user(u_id); gamble_cooldowns[u_id] = datetime.now()
    
    msg = await ctx.reply(embed=discord.Embed(description=f"🪙 Tung **{bet:,} 💰**...").set_thumbnail(url=GIF_LINKS["casino"]), mention_author=False)
    await asyncio.sleep(2) 
    
    if random.choice([True, False]):
        u["money"] += bet * 2; save_user(u_id)
        await msg.edit(embed=discord.Embed(description=f"🪙 **NGỬA!** Húp **{bet * 2:,} 💰**!", color=discord.Color.green()))
    else: await msg.edit(embed=discord.Embed(description=f"🪙 **SẤP!** Mất trắng **{bet:,} 💰**.", color=discord.Color.red()))

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    choice = choice.lower().replace("à", "a").replace("ỉ", "i")
    if choice not in ["tai", "xiu"]: return await ctx.reply("⚠️ Dùng `tai` hoặc `xiu`.")
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    u_id = str(ctx.author.id); u["money"] -= bet; save_user(u_id); gamble_cooldowns[u_id] = datetime.now()
    
    msg = await ctx.reply(embed=discord.Embed(title="🎲 LẮC CASINO", description=f"Cược **{bet:,} 💰** vào **{choice.upper()}**...").set_thumbnail(url=GIF_LINKS["casino"]), mention_author=False)
    await asyncio.sleep(2.5)
    
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    res = "xiu" if total <= 10 else "tai"
    
    embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    if choice == res: 
        if d1 == d2 == d3: win = bet * 5; txt = f"🔥 **BÃO {d1}-{d2}-{d3}! X5 TÀI SẢN!**\nHúp **{win:,} 💰**!"
        else: win = bet * 2; txt = f"✅ **THẮNG!** Nhận **{win:,} 💰**!"
        u["money"] += win; embed.color = discord.Color.green()
    else: txt = f"💀 **THUA!** Mất **{bet:,} 💰**."; embed.color = discord.Color.red()
    
    save_user(u_id)
    embed.description = f"**[ {d1} | {d2} | {d3} ]** (Tổng: {total} - Cửa **{res.upper()}**)\n\n{txt}"
    await msg.edit(embed=embed)

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    u_id = str(ctx.author.id); u["money"] -= bet; save_user(u_id); gamble_cooldowns[u_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    r = [random.choice(items) for _ in range(3)]
    
    embed = discord.Embed(title="🎰 MÁY XÈNG 🎰", color=discord.Color.gold()).set_thumbnail(url=GIF_LINKS["casino"])
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    for _ in range(2): embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đang quay..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    for _ in range(2): embed.description = f"**[ {r[0]} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Chốt ô 1..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    for _ in range(2): embed.description = f"**[ {r[0]} | {r[1]} | {random.choice(items)} ]**\n\n🔄 Nín thở..."; await msg.edit(embed=embed); await asyncio.sleep(1)
        
    if r[0] == r[1] == r[2]:
        win = bet * 50 if r[0] == "👑" else (bet * 20 if r[0] == "💎" else bet * 10)
        txt = f"🔥 **JACKPOT NỔ HŨ!** Húp trọn **{win:,} 💰**!"
        u["money"] += win
    elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
        win = bet * 2; txt = f"🎉 **THẮNG NHỎ!** Nhận **{win:,} 💰**."; u["money"] += win
    else: txt = f"💀 **TOANG!** Mất **{bet:,} 💰**."
        
    save_user(u_id); embed.description = f"**[ {r[0]} | {r[1]} | {r[2]} ]**\n\n{txt}"
    await msg.edit(embed=embed)

@bot.command()
async def daily(ctx):
    u = load_user(ctx.author.id); now = datetime.now()
    if u.get("last_daily"):
        last = datetime.strptime(u["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last < timedelta(days=1): return await ctx.reply(embed=discord.Embed(description=f"⏳ Vẫn còn <t:{int((last + timedelta(days=1)).timestamp())}:R> nữa.", color=discord.Color.orange()), mention_author=False)
    
    u["money"] += 1000; u["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(title="🎁 QUÀ ĐIỂM DANH", description=f"Nhận **1,000 💰**!\nVí: **{u['money']:,} 💰**", color=discord.Color.green()).set_thumbnail(url=GIF_LINKS["daily"]), mention_author=False)

@bot.command()
async def tuido(ctx):
    u = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO BÁU CỦA {ctx.author.name.upper()}", color=discord.Color.dark_purple())
    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
    embed.add_field(name="🏠 Tài Sản", value="Trống." if not u.get("assets") else "\n".join([f"🔸 {a}" for a in u["assets"]]), inline=False)
    embed.add_field(name="🐾 Thú Cưng", value="Trống." if not u.get("pets") else "\n".join([f"{p} (x{c})" for p, c in u["pets"].items()]), inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx):
    danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in list(users_col.find())], key=lambda x: x[1], reverse=True)
    desc = "".join([f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'**#{i+1}**'} **Tỷ phú {uid[-4:]}** ━ {tien:,} 💰\n\n" for i, (uid, tien) in enumerate(danh_sach[:10])])
    await ctx.send(embed=discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA", description=desc, color=discord.Color.gold()))

# =====================================================================
# SỰ KIỆN HỆ THỐNG LÕI CỦA BOT (ON_MESSAGE, ON_READY)
# =====================================================================
@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = str(message.author.id)
    u = load_user(user_id)
    
    if u.get("jail_time") and datetime.now() < datetime.strptime(u["jail_time"], "%Y-%m-%d %H:%M:%S"): return await bot.process_commands(message)
            
    u["xp"] += random.randint(5, 15)
    lv = u.get("level", 1)
    
    if u["xp"] >= lv * 100:
        u["xp"] -= lv * 100; u["level"] += 1; rw = u["level"] * 150; u["money"] += rw
        try: await message.channel.send(embed=discord.Embed(description=f"🎉 **{message.author.mention}** đã thăng cấp **Lv.{u['level']}**!\nThưởng: **{rw:,} 💰**", color=discord.Color.gold()))
        except Exception: pass
            
    save_user(user_id)
    await bot.process_commands(message)

@bot.event
async def on_ready(): 
    print('================================================')
    print(f'>>> SIÊU BOT {bot.user} ĐÃ SẴN SÀNG CÀN QUÉT!')
    print('>>> BẢN 4.0 SIÊU HARDCORE - KALLEN FANTASY TÍCH HỢP')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="Kallen Fantasy & Sinh Tồn | k help"))

# =====================================================================
# KHỞI ĐỘNG SERVER 24/7 VÀ CHẠY BOT BẰNG TOKEN
# =====================================================================
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
