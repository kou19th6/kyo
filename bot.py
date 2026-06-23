import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 

# =====================================================================
# THIẾT LẬP CƠ BẢN CỦA BOT
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

# =====================================================================
# QUẢN LÝ TRẠNG THÁI (COOLDOWN)
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

# Khởi tạo kết nối DB
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]
users_col = db["users"]   
config_col = db["config"] 
companies_col = db["companies"]

# Khởi tạo Cache để giảm tải cho DB (Tăng tốc độ phản hồi của Bot)
DB_CACHE = {}
CONFIG_CACHE = {}
COMPANY_CACHE = {}

def load_user(user_id):
    """
    Tải dữ liệu người dùng từ Database. 
    Nếu người dùng chưa tồn tại hoặc có tính năng mới, tự động khởi tạo mặc định.
    """
    user_id = str(user_id)
    
    if user_id not in DB_CACHE:
        doc = users_col.find_one({"_id": user_id})
        if doc:
            DB_CACHE[user_id] = doc
        else:
            DB_CACHE[user_id] = {}
            
    # Bộ khung dữ liệu chuẩn của người chơi
    defaults = {
        "xp": 0, 
        "level": 1, 
        "money": 0, 
        "bank": 0,
        "title": "Dân Nghèo 🚶", 
        "assets": [], 
        "pets": {}, 
        "company": None, 
        "stocks": {}, 
        "jail_time": None,
        "spouse": None
    }
    
    # Kiểm tra và bù đắp dữ liệu thiếu
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
    """Tải cấu hình Server (Chặn kênh, báo cấp...)"""
    server_id = str(server_id)
    
    if server_id not in CONFIG_CACHE:
        doc = config_col.find_one({"_id": server_id})
        if doc:
            CONFIG_CACHE[server_id] = doc
        else:
            CONFIG_CACHE[server_id] = {}
            
    return CONFIG_CACHE[server_id]

def load_company(comp_id):
    """Tải dữ liệu Công ty / Bang hội"""
    comp_id = str(comp_id)
    
    if comp_id not in COMPANY_CACHE:
        doc = companies_col.find_one({"_id": comp_id})
        if doc: 
            COMPANY_CACHE[comp_id] = doc
        else: 
            return None
            
    return COMPANY_CACHE[comp_id]

def save_company(comp_id):
    """Lưu dữ liệu Công ty lên Database"""
    comp_id = str(comp_id)
    if comp_id in COMPANY_CACHE: 
        companies_col.update_one(
            {"_id": comp_id}, 
            {"$set": COMPANY_CACHE[comp_id]}, 
            upsert=True
        )

# =====================================================================
# HÀM KIỂM TRA TOÀN CỤC (ĐI TÙ, CHẶN KÊNH)
# =====================================================================
@bot.check
async def global_jail_check(ctx):
    """Chặn 100% lệnh nếu người dùng đang ở trong tù"""
    
    # Quản trị viên và lệnh help được miễn trừ
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
                            f"Hãy tự vấn lương tâm rồi quay lại sau khi ra tù nhé!", 
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)
            return False
        else:
            # Hết thời gian phạt, xóa án tích
            user_data["jail_time"] = None
            save_user(ctx.author.id)
            
    # Kiểm tra kẹt kênh (Chỉ cho phép dùng bot ở kênh được chỉ định)
    if ctx.guild:
        config = load_server_config(ctx.guild.id)
        allowed_channels = config.get("allowed_channels", [])
        
        if allowed_channels and ctx.channel.id not in allowed_channels: 
            return False
            
    return True

def make_progress_bar(current, total, length=12):
    """Tạo thanh tiến trình hiển thị kinh nghiệm bằng Emoji"""
    progress = int((current / total) * length)
    return "🟩" * progress + "⬛" * (length - progress)

async def check_gamble_conditions(ctx, amount_str):
    """
    Kiểm tra điều kiện cờ bạc:
    1. Cooldown spam lệnh
    2. Kiểm tra nợ nần
    3. Kiểm tra số tiền hợp lệ (hoặc All-in)
    4. Kiểm tra giới hạn mức cược tối đa (500k)
    """
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    # Kiểm tra Spam lệnh (Cooldown 4 giây)
    if user_id in gamble_cooldowns:
        time_diff = (now - gamble_cooldowns[user_id]).total_seconds()
        if time_diff < 4:
            time_left = int(4 - time_diff)
            embed = discord.Embed(
                description=f"⏳ Tay mỏi rồi! Đợi {time_left}s nữa hẵng lắc tiếp sếp ơi!", 
                color=discord.Color.orange()
            )
            await ctx.reply(embed=embed, mention_author=False)
            return None, None
            
    user_data = load_user(user_id)
    
    # Kiểm tra tình trạng nợ nần
    if user_data.get("money", 0) <= 0:
        embed = discord.Embed(
            description="💸 Kẻ tổn thương lại muốn tổn thương sòng bạc à? Tiền không có mà đòi cá cược! Hãy dùng lệnh `k daily` để nhận trợ cấp.", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed, mention_author=False)
        return None, None
        
    # Chuyển đổi số tiền cược
    try: 
        if amount_str.lower() == "all":
            # Nếu all-in lớn hơn 500k, tự động giới hạn ở 500k
            bet = user_data["money"] if user_data["money"] <= 500000 else 500000
        else:
            bet = int(amount_str)
    except ValueError: 
        embed = discord.Embed(
            description="⚠️ Nhập số tiền sai định dạng rồi! Vui lòng nhập số hoặc chữ `all`.", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed, mention_author=False)
        return None, None
        
    # Kiểm tra giới hạn ví tiền
    if bet <= 0 or bet > user_data["money"]: 
        embed = discord.Embed(
            description=f"⚠️ Bốc phét à? Sếp chỉ có **{user_data['money']:,} 💰** trong ví thôi!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed, mention_author=False)
        return None, None
        
    # Kiểm tra giới hạn cược tối đa
    if bet > 500000: 
        embed = discord.Embed(
            description="🛑 Nhà cái quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed, mention_author=False)
        return None, None
        
    return user_data, bet
    # =====================================================================
# KHO DỮ LIỆU CỬA HÀNG VÀ CHỢ ĐEN CẦM ĐỒ
# =====================================================================
SHOP_ITEMS = {
    # --- DANH HIỆU KHÈ NHAU ---
    "t1": {
        "type": "title", 
        "name": "Kẻ Lưu Đày 🛖", 
        "price": 10000, 
        "emoji": "🏷️"
    },
    "t2": {
        "type": "title", 
        "name": "Tiểu Thương 🏪", 
        "price": 50000, 
        "emoji": "🏷️"
    },
    "t3": {
        "type": "title", 
        "name": "Phú Nông 🌾", 
        "price": 200000, 
        "emoji": "🏷️"
    },
    "t4": {
        "type": "title", 
        "name": "Đại Gia 💸", 
        "price": 1000000, 
        "emoji": "🏷️"
    },
    "t5": {
        "type": "title", 
        "name": "Tỷ Phú 💎", 
        "price": 5000000, 
        "emoji": "🏷️"
    },
    "t6": {
        "type": "title", 
        "name": "Thần Tài 🧧", 
        "price": 20000000, 
        "emoji": "🏷️"
    },
    "t7": {
        "type": "title", 
        "name": "Kẻ Thống Trị Vũ Trụ 🌌", 
        "price": 100000000, 
        "emoji": "👑"
    },
    
    # --- SIÊU XE VÀ PHƯƠNG TIỆN ---
    "v1": {
        "type": "vehicle", 
        "name": "Xe Đạp Địa Hình 🚲", 
        "price": 15000, 
        "emoji": "🚲"
    },
    "v2": {
        "type": "vehicle", 
        "name": "Honda SH 150i 🏍️", 
        "price": 300000, 
        "emoji": "🏍️"
    },
    "v3": {
        "type": "vehicle", 
        "name": "Toyota Camry 🚗", 
        "price": 2000000, 
        "emoji": "🚗"
    },
    "v4": {
        "type": "vehicle", 
        "name": "Mercedes G63 🚙", 
        "price": 8000000, 
        "emoji": "🚙"
    },
    "v5": {
        "type": "vehicle", 
        "name": "Lamborghini Aventador 🏎️", 
        "price": 25000000, 
        "emoji": "🏎️"
    },
    "v6": {
        "type": "vehicle", 
        "name": "Du Thuyền Hạng Sang 🛥️", 
        "price": 150000000, 
        "emoji": "🛥️"
    },
    "v7": {
        "type": "vehicle", 
        "name": "Trạm Không Gian UFO 🛸", 
        "price": 900000000, 
        "emoji": "🛸"
    },
    
    # --- BẤT ĐỘNG SẢN ---
    "h1": {
        "type": "house", 
        "name": "Nhà Trọ Ẩm Thấp ⛺", 
        "price": 50000, 
        "emoji": "⛺"
    },
    "h2": {
        "type": "house", 
        "name": "Chung Cư Mini 🏢", 
        "price": 500000, 
        "emoji": "🏢"
    },
    "h3": {
        "type": "house", 
        "name": "Nhà Phố 3 Tầng 🏘️", 
        "price": 5000000, 
        "emoji": "🏘️"
    },
    "h4": {
        "type": "house", 
        "name": "Biệt Thự Hồ Tây 🏡", 
        "price": 30000000, 
        "emoji": "🏡"
    },
    "h5": {
        "type": "house", 
        "name": "Lâu Đài Cổ Tích 🏰", 
        "price": 150000000, 
        "emoji": "🏰"
    },
    "h6": {
        "type": "house", 
        "name": "Đảo Tư Nhân Maldives 🏝️", 
        "price": 600000000, 
        "emoji": "🏝️"
    },
    "h7": {
        "type": "house", 
        "name": "Hành Tinh Namek 🪐", 
        "price": 2000000000, 
        "emoji": "🪐"
    }
}

# =====================================================================
# DATA GACHA THÚ CƯNG
# =====================================================================
PET_RATES = {
    "common": {
        "rate": 70.0, 
        "pool": [
            "Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", 
            "Lợn Đất 🐖", "Cáo Nhỏ 🦊", "Chuột Đồng 🐁"
        ]
    },
    "rare": {
        "rate": 20.0, 
        "pool": [
            "Sói Tuyết 🐺", "Gấu Xám 🐻", 
            "Đại Bàng 🦅", "Báo Gấm 🐆"
        ]
    },
    "epic": {
        "rate": 7.0, 
        "pool": [
            "Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍", 
            "Bạch Hổ 🐅", "Tê Giác Thiết Giáp 🦏"
        ]
    },
    "legendary": {
        "rate": 2.5, 
        "pool": [
            "Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", 
            "Phượng Hoàng Lửa 🦚", "Thủy Quái Leviathan 🐙"
        ]
    },
    "mythic": {
        "rate": 0.5, 
        "pool": [
            "Thần Long Hoàng Kim 🐲", "Hắc Ám Cự Thú 🦇", 
            "Mèo Thần Tài Siêu Cấp 😻", "Godzilla Vĩ Đại 🦖"
        ]
    }
}

# =====================================================================
# DATA SÀN CHỨNG KHOÁN (CẬP NHẬT THEO GIỜ THỰC TẾ)
# =====================================================================
STOCKS = {
    "VIN": "Tập Đoàn VIN", 
    "FLC": "Hàng Không FLC", 
    "VNZ": "Công Nghệ VNZ", 
    "DOGE": "Doge Coin", 
    "BTC": "Bitcoin", 
    "AAPL": "Apple Inc.", 
    "TSLA": "Tesla"
}

def get_stock_price(stock_code, hour_offset=0):
    """
    Tính giá cổ phiếu thay đổi theo từng giờ thực tế.
    Dùng seed thời gian để tất cả người chơi đều thấy chung 1 mức giá.
    """
    target_time = datetime.now() + timedelta(hours=hour_offset)
    seed = int(target_time.strftime("%Y%m%d%H")) + sum(ord(c) for c in stock_code)
    rng = random.Random(seed)
    # Cổ phiếu dao động từ 5k đến 500k
    return rng.randint(5, 500) * 1000

def get_next_hour_timestamp():
    """Lấy Timestamp của khung giờ tiếp theo để hiển thị đếm ngược"""
    next_hour = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int(next_hour.timestamp())

def get_asset_price(asset_name):
    """Tính giá bán lại tài sản vào chợ đen (Bị ép giá, lỗ 30%)"""
    for item_data in SHOP_ITEMS.values():
        if item_data["name"] == asset_name: 
            return int(item_data["price"] * 0.7)
    return 1000

def get_pet_sell_price(pet_name):
    """Tính giá bán thú cưng theo độ hiếm (Đảm bảo cân bằng kinh tế)"""
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 5000      
            if rarity == "rare": return 20000       
            if rarity == "epic": return 150000      
            if rarity == "legendary": return 800000 
            if rarity == "mythic": return 10000000   
    return 1000

# =====================================================================
# DATA KHU RỪNG THÁM HIỂM (VŨ KHÍ & KỊCH BẢN)
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {
        "price": 50, 
        "name": "🪵 Gậy Gỗ Mục", 
        "terrible": 25, "bad": 40, "neutral": 15, "good": 15, "great": 5, "jackpot": 0
    },
    "sung_cao_su": {
        "price": 100, 
        "name": "🪀 Súng Cao Su", 
        "terrible": 20, "bad": 35, "neutral": 20, "good": 20, "great": 5, "jackpot": 0
    },
    "kiem_sat": {
        "price": 200, 
        "name": "🗡️ Kiếm Sắt Thường", 
        "terrible": 15, "bad": 25, "neutral": 20, "good": 25, "great": 13, "jackpot": 2
    },
    "kiem_hiep_si": {
        "price": 500, 
        "name": "⚔️ Kiếm Hiệp Sĩ", 
        "terrible": 10, "bad": 20, "neutral": 15, "good": 30, "great": 20, "jackpot": 5
    },
    "riu_chien": {
        "price": 1000, 
        "name": "🪓 Rìu Phá Giáp", 
        "terrible": 10, "bad": 15, "neutral": 15, "good": 30, "great": 25, "jackpot": 5
    },
    "thanh_kiem": {
        "price": 1500, 
        "name": "🔱 Thánh Kiếm Mạ Vàng", 
        "terrible": 5, "bad": 10, "neutral": 10, "good": 35, "great": 30, "jackpot": 10
    },
    "sung_phong_luu": {
        "price": 3000, 
        "name": "🚀 Súng Phóng Lựu RPG", 
        "terrible": 5, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 15
    },
    "gang_tay": {
        "price": 5000, 
        "name": "🧤 Găng Tay Vô Cực", 
        "terrible": 2, "bad": 5, "neutral": 5, "good": 20, "great": 40, "jackpot": 28
    }
}

SCENARIOS = {
    "terrible": [ 
        {
            "mult": -2.0, 
            "msg": "🐘 **KING KONG NỔI GIẬN!**\nBạn chọc tức chúa tể rừng xanh. Bị đấm bay xa 10km, rớt sạch đồ đạc!"
        },
        {
            "mult": -1.5, 
            "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền!"
        },
        {
            "mult": -1.3, 
            "msg": "🕳️ **SỤP HỐ CHÔNG!**\nRơi thẳng xuống hố chông của thợ săn. Gãy 2 cái sườn, nôn hết tiền mặt ra."
        }
    ],
    "bad": [ 
        {
            "mult": -0.5, 
            "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."
        },
        {
            "mult": -0.6, 
            "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước hết hạn từ máy bán hàng tự động trong rừng. Bị đau bụng tốn tiền viện phí."
        },
        {
            "mult": -0.8, 
            "msg": "💩 **TRƯỢT CHÂN VÀO BÃI MÌN!**\nBạn dẫm trúng bãi mìn khổng lồ của voi rừng. Tốn tiền mua bộ đồ mới."
        }
    ],
    "neutral": [ 
        {
            "mult": 0, 
            "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."
        },
        {
            "mult": 0, 
            "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."
        }
    ],
    "good": [ 
        {
            "mult": 0.5, 
            "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."
        },
        {
            "mult": 0.8, 
            "msg": "🍄 **NẤM LINH CHI!**\nHái được cây nấm linh chi đỏ rực. Tiệm thuốc trả cho bạn một khoản hời."
        }
    ],
    "great": [ 
        {
            "mult": 1.5, 
            "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp và tịch thu kho báu của chúng!"
        },
        {
            "mult": 2.5, 
            "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nPhát hiện ra một rương kho báu vàng chóe bị chôn vùi. Mở ra toàn tiền!"
        }
    ],
    "jackpot": [ 
        {
            "mult": 5.0, 
            "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng ĐẶC BIỆT!"
        },
        {
            "mult": 12.0, 
            "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR! (ULTRAPOT)**\nDưới đáy đầm, bạn vớt được Vương miện nạm 100 viên kim cương. Bạn thành tỷ phú!!"
        }
    ]
}

# =====================================================================
# DATA NHÂN SINH (CÁC SỰ KIỆN CUỘC ĐỜI THEO TỪNG ĐỘ TUỔI)
# =====================================================================
EVENTS_P1 = [
    {
        "q": "Tuổi 15: Bạn tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", 
        "choices": [
            {
                "text": "Đem nộp lên công an", 
                "rate": 80, 
                "win": "Chủ ví là tổng tài, hậu tạ bạn món tiền lớn.", 
                "lose": "Bị giam ở phường viết bản tường trình 3 ngày.", 
                "tien_w": 2500, 
                "tien_l": -100
            }, 
            {
                "text": "Bỏ túi xài luôn", 
                "rate": 20, 
                "win": "Không ai biết, bạn bao lớp ăn chè thỏa thích.", 
                "lose": "Bị check camera, bồi thường gấp đôi và bị đuổi học.", 
                "tien_w": 3000, 
                "tien_l": -8000
            }, 
            {
                "text": "Lấy tờ 500k rồi vứt lại ví", 
                "rate": 40, 
                "win": "Trót lọt, bạn nạp game lên VIP.", 
                "lose": "Chủ nhân báo mất, bị tra hỏi phạt nặng.", 
                "tien_w": 1000, 
                "tien_l": -4000
            }, 
            {
                "text": "Giả vờ không thấy", 
                "rate": 95, 
                "win": "Thong thả đi học tiếp, chẳng rước họa vào thân.", 
                "lose": "Đứa đi sau nhặt được đổ oan cho bạn.", 
                "tien_w": 0, 
                "tien_l": -500
            }
        ]
    },
    {
        "q": "Tuổi 15: Crush rủ bạn cúp học đi xem phim.", 
        "choices": [
            {
                "text": "Đi luôn sợ gì", 
                "rate": 60, 
                "win": "Crush tỏ tình, hai người có kỷ niệm đẹp.", 
                "lose": "Cô giáo bắt được, mời phụ huynh.", 
                "tien_w": 0, 
                "tien_l": -1000
            }, 
            {
                "text": "Từ chối, bảo phải ôn bài", 
                "rate": 90, 
                "win": "Thi học sinh giỏi được giải nhất.", 
                "lose": "Crush dỗi, đi quen thằng lớp bên.", 
                "tien_w": 5000, 
                "tien_l": -2000
            }, 
            {
                "text": "Rủ thêm cả đám bạn đi chung", 
                "rate": 80, 
                "win": "Vui vẻ cả làng, không ai bị bắt.", 
                "lose": "Ồn ào quá bị bảo vệ rạp đuổi ra ngoài.", 
                "tien_w": 0, 
                "tien_l": -500
            }, 
            {
                "text": "Mách cô giáo", 
                "rate": 100, 
                "win": "Được phong làm sao đỏ.", 
                "lose": "Bị cả lớp tẩy chay.", 
                "tien_w": 500, 
                "tien_l": -2000
            }
        ]
    },
    {
        "q": "Tuổi 15: Bạn thấy mấy anh lớn đang trấn lột tiền bạn cùng lớp.", 
        "choices": [
            {
                "text": "Lao vào đấm nhau", 
                "rate": 15, 
                "win": "Đánh thắng 3 thằng, thành đại ca trường.", 
                "lose": "Bị đấm sưng mỏ, nhập viện.", 
                "tien_w": 3000, 
                "tien_l": -5000
            }, 
            {
                "text": "Báo giám thị", 
                "rate": 85, 
                "win": "Bọn cướp bị đuổi học, bạn được tuyên dương.", 
                "lose": "Giám thị không tin bạn.", 
                "tien_w": 1000, 
                "tien_l": -200
            }, 
            {
                "text": "Hét to 'CÔNG AN TỚI' rồi chạy", 
                "rate": 60, 
                "win": "Bọn nó hoảng loạn bỏ chạy.", 
                "lose": "Bị bọn nó rượt theo đánh.", 
                "tien_w": 500, 
                "tien_l": -2000
            }, 
            {
                "text": "Đứng quay Tiktok", 
                "rate": 40, 
                "win": "Video viral, kênh lên triệu view kiếm bộn tiền.", 
                "lose": "Bị giật điện thoại đập nát.", 
                "tien_w": 10000, 
                "tien_l": -15000
            }
        ]
    }
]

EVENTS_P2 = [
    {
        "q": "Tuổi 25: Bạn có 100 củ tiền tiết kiệm, bạn sẽ làm gì?", 
        "choices": [
            {
                "text": "All-in tiền ảo (Crypto)", 
                "rate": 30, 
                "win": "Bitcoin x10! Bạn mua được Mẹc.", 
                "lose": "Thị trường sập, bạn ra đê ở.", 
                "tien_w": 50000, 
                "tien_l": -90000
            }, 
            {
                "text": "Gửi ngân hàng", 
                "rate": 95, 
                "win": "Cuộc sống bình yên ăn lãi.", 
                "lose": "Ngân hàng phá sản (hiếm nhưng có).", 
                "tien_w": 5000, 
                "tien_l": -100000
            }, 
            {
                "text": "Mở quán cafe khởi nghiệp", 
                "rate": 50, 
                "win": "Khách đông nườm nượp, mở chuỗi 5 quán.", 
                "lose": "Dịch bệnh ập tới, đóng cửa sang nhượng.", 
                "tien_w": 30000, 
                "tien_l": -50000
            }, 
            {
                "text": "Đi du lịch vòng quanh thế giới", 
                "rate": 80, 
                "win": "Trải nghiệm mở mang tầm mắt, viết sách bán chạy.", 
                "lose": "Bị trộm móc túi ở Paris.", 
                "tien_w": 15000, 
                "tien_l": -30000
            }
        ]
    },
    {
        "q": "Tuổi 25: Sếp chửi bạn xối xả giữa công ty dù bạn không sai.", 
        "choices": [
            {
                "text": "Đập bàn nghỉ việc", 
                "rate": 40, 
                "win": "Công ty đối thủ mời bạn làm Giám đốc.", 
                "lose": "Thất nghiệp ròng rã 6 tháng.", 
                "tien_w": 40000, 
                "tien_l": -20000
            }, 
            {
                "text": "Nhịn nhục xin lỗi", 
                "rate": 90, 
                "win": "Cuối năm được tăng lương chút xíu.", 
                "lose": "Trầm cảm, tốn tiền đi khám tâm lý.", 
                "tien_w": 5000, 
                "tien_l": -10000
            }, 
            {
                "text": "Chửi tay đôi với sếp", 
                "rate": 20, 
                "win": "Sếp nể phục sự thẳng thắn, thăng chức cho bạn.", 
                "lose": "Bị đuổi việc ngay lập tức không đền bù.", 
                "tien_w": 35000, 
                "tien_l": -15000
            }, 
            {
                "text": "Bóc phốt lên mạng xã hội", 
                "rate": 50, 
                "win": "Công ty bị tẩy chay, sếp bị đuổi.", 
                "lose": "Bị công ty kiện tội vu khống.", 
                "tien_w": 10000, 
                "tien_l": -30000
            }
        ]
    }
]

EVENTS_P3 = [
    {
        "q": "Tuổi 35: Cò đất rủ bạn chung vốn lướt sóng khu quy hoạch.", 
        "choices": [
            {
                "text": "Cầm nhà quất liền", 
                "rate": 20, 
                "win": "Giá đất x5! Bạn thành tỷ phú.", 
                "lose": "Dính bẫy lừa đảo, nhảy cầu.", 
                "tien_w": 150000, 
                "tien_l": -200000, 
                "die_l": True
            }, 
            {
                "text": "Mua 1 lô nhỏ an toàn", 
                "rate": 60, 
                "win": "Lãi gấp đôi sau 2 năm.", 
                "lose": "Đất dính quy hoạch treo, giam vốn.", 
                "tien_w": 40000, 
                "tien_l": -30000
            }, 
            {
                "text": "Làm cò đất ăn hoa hồng", 
                "rate": 80, 
                "win": "Bán được chục lô, ấm no.", 
                "lose": "Bị giang hồ bảo kê tranh địa bàn đánh.", 
                "tien_w": 25000, 
                "tien_l": -15000
            }, 
            {
                "text": "Mua vàng cất két", 
                "rate": 95, 
                "win": "Vàng lên giá vù vù.", 
                "lose": "Trộm vào nhà cạy két.", 
                "tien_w": 20000, 
                "tien_l": -50000
            }
        ]
    },
    {
        "q": "Tuổi 35: Bạn học cũ đột nhiên gọi điện hỏi vay 50 triệu.", 
        "choices": [
            {
                "text": "Cho vay không lấy lãi", 
                "rate": 30, 
                "win": "Bạn làm ăn phất lên, trả lại gấp 3.", 
                "lose": "Nó chặn số, bom tiền luôn.", 
                "tien_w": 150000, 
                "tien_l": -50000
            }, 
            {
                "text": "Bảo không có tiền", 
                "rate": 95, 
                "win": "Giữ được tiền, không sứt mẻ gì.", 
                "lose": "Bị nó chửi là đồ ki bo.", 
                "tien_w": 0, 
                "tien_l": 0
            }, 
            {
                "text": "Cho vay lãi cắt cổ", 
                "rate": 40, 
                "win": "Thu lãi ngập mồm hàng tháng.", 
                "lose": "Bị công an bế đi vì tội cho vay nặng lãi.", 
                "tien_w": 80000, 
                "tien_l": -100000
            }, 
            {
                "text": "Đòi vay ngược lại nó", 
                "rate": 80, 
                "win": "Nó hoảng quá cúp máy luôn.", 
                "lose": "Nó chửi bạn rồi bóc phốt lên mạng.", 
                "tien_w": 0, 
                "tien_l": -2000
            }
        ]
    }
]

EVENTS_P4 = [
    {
        "q": "Tuổi 50: Bạn bước vào giai đoạn khủng hoảng tuổi trung niên trầm trọng.", 
        "choices": [
            {
                "text": "Bán nhà mua siêu xe Mẹc G63", 
                "rate": 15, 
                "win": "Chiến thắng giải đua không chuyên, nổi đình đám.", 
                "lose": "Đạp nhầm chân ga tông xe tải, thăng thiên tại chỗ.", 
                "tien_w": 100000, 
                "tien_l": -150000, 
                "die_l": True
            }, 
            {
                "text": "Sưu tầm Lan Đột Biến", 
                "rate": 35, 
                "win": "Bán chậu lan giá trên trời cho tỷ phú.", 
                "lose": "Thị trường sập, ôm bó cỏ khô.", 
                "tien_w": 80000, 
                "tien_l": -50000
            }, 
            {
                "text": "Cặp Baby cho hồi xuân", 
                "rate": 25, 
                "win": "Tâm hồn trẻ lại phơi phới.", 
                "lose": "Bị vợ/chồng bắt ghen thu hết tài sản.", 
                "tien_w": 5000, 
                "tien_l": -200000
            }, 
            {
                "text": "Tập Thiền, dọn về quê nuôi cá", 
                "rate": 90, 
                "win": "Tâm hồn thanh tịnh, khí huyết lưu thông.", 
                "lose": "Về quê bị muỗi vằn đốt sốt xuất huyết.", 
                "tien_w": 15000, 
                "tien_l": -5000
            }
        ]
    },
    {
        "q": "Tuổi 50: Đi khám tổng quát, bác sĩ bảo bạn có khối u.", 
        "choices": [
            {
                "text": "Bán nhà sang Mỹ chữa trị", 
                "rate": 80, 
                "win": "Chữa khỏi hoàn toàn, sống khỏe thêm 30 năm.", 
                "lose": "Tai nạn máy bay trên đường đi.", 
                "tien_w": 0, 
                "tien_l": -100000, 
                "die_l": True
            }, 
            {
                "text": "Uống thuốc lá của thầy lang", 
                "rate": 10, 
                "win": "Mèo mù vớ cá rán, u tự teo lại thần kỳ.", 
                "lose": "Suy gan suy thận, chết tức tưởi sau 1 tuần.", 
                "tien_w": 0, 
                "tien_l": -10000, 
                "die_l": True
            }, 
            {
                "text": "Bán hết tài sản đi phượt xuyên Việt", 
                "rate": 50, 
                "win": "Tâm trạng vui vẻ, bệnh tự khỏi thần kỳ.", 
                "lose": "Bệnh phát tác giữa đèo Hải Vân, rơi vực.", 
                "tien_w": 0, 
                "tien_l": -50000, 
                "die_l": True
            }, 
            {
                "text": "Nghe lời bác sĩ mổ ngay trong nước", 
                "rate": 70, 
                "win": "Phẫu thuật thành công rực rỡ.", 
                "lose": "Nhiễm trùng vết mổ tốn tiền tỉ hồi sức.", 
                "tien_w": 0, 
                "tien_l": -80000
            }
        ]
    }
]

EVENTS_P5 = [
    {
        "q": "Tuổi 70: Bạn đào đất sau vườn thấy một chiếc rương cổ.", 
        "choices": [
            {
                "text": "Giao nộp nhà nước", 
                "rate": 85, 
                "win": "Được thưởng bằng khen và 1 cục tiền.", 
                "lose": "Rương rỗng, tốn công khiêng.", 
                "tien_w": 50000, 
                "tien_l": 0
            }, 
            {
                "text": "Tự mở ra xem", 
                "rate": 20, 
                "win": "Bên trong đầy vàng thỏi, bạn thành tài phiệt!", 
                "lose": "Trúng bẫy độc của cổ nhân, đột tử.", 
                "tien_w": 500000, 
                "tien_l": -10000, 
                "die_l": True
            }, 
            {
                "text": "Bán ra chợ đen", 
                "rate": 40, 
                "win": "Con buôn đồ cổ trả giá cực cao.", 
                "lose": "Bị công an bắt quả tang buôn lậu.", 
                "tien_w": 200000, 
                "tien_l": -150000
            }, 
            {
                "text": "Chôn lại chỗ cũ", 
                "rate": 100, 
                "win": "Bình yên vô sự.", 
                "lose": "Không có.", 
                "tien_w": 0, 
                "tien_l": 0
            }
        ]
    },
    {
        "q": "Tuổi 70: Có người gạ bán Linh Đan Cải Lão Hoàn Đồng.", 
        "choices": [
            {
                "text": "Vung tiền mua ngay", 
                "rate": 5, 
                "win": "Kỳ tích! Bạn trở lại tuổi 20 sung mãn!", 
                "lose": "Uống nhầm thủy ngân, thăng thiên sớm.", 
                "tien_w": 1000000, 
                "tien_l": -50000, 
                "die_l": True
            }, 
            {
                "text": "Lập di chúc chia tài sản cho con", 
                "rate": 75, 
                "win": "Con cháu hòa thuận mừng thọ.", 
                "lose": "Con cháu đánh nhau giành giật, bạn tức quá đột quỵ.", 
                "tien_w": 10000, 
                "tien_l": -20000, 
                "die_l": True
            }, 
            {
                "text": "Quyên góp từ thiện hết", 
                "rate": 90, 
                "win": "Được nhà nước tạc tượng vinh danh.", 
                "lose": "Tổ chức từ thiện cuỗm tiền chạy mất.", 
                "tien_w": 20000, 
                "tien_l": -100000, 
                "die_l": True
            }, 
            {
                "text": "Lên Las Vegas quất 1 ván Casino cuối đời", 
                "rate": 15, 
                "win": "Trúng Jackpot 50 triệu đô!", 
                "lose": "Thua trắng tay, nhồi máu cơ tim gục tại bàn.", 
                "tien_w": 2000000, 
                "tien_l": -100000, 
                "die_l": True
            }
        ]
    }
]
        # =====================================================================
# GIAO DIỆN UI NÚT BẤM: TRẠM AFK & NHÂN SINH GAME
# =====================================================================
class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Phần thưởng: ~450 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Phần thưởng: ~1000 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Phần thưởng: ~2000 💰", emoji="🏛️", value="12")
        ]
        super().__init__(placeholder="Chọn khu vực cắm trại...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        hours = int(self.values[0])
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

        embed = discord.Embed(
            title="⛺ LÊN ĐƯỜNG BÌNH AN!", 
            description=f"Hành lý đã chuẩn bị xong. Bạn bắt đầu cắm trại **{hours} giờ**.\nKhi nào hết thời gian, hãy gõ lệnh `k phai` để thu hoạch nhé.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, interaction: discord.Interaction): 
        return interaction.user == self.author

class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        self.ev = random.choice(EVENTS_P1)

        # Mở bài theo độ may mắn
        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng, chạy quanh nhà bằng siêu xe đồ chơi.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm, bình yên.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài đầu đường xó chợ từ nhỏ.")

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
        if user_id in dang_choi_nhansinh: 
            dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user != self.author:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng bấm lung tung!", ephemeral=True)
            return False
        return True

    async def choice_a(self, interaction: discord.Interaction): await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        final_rate = min(95, base_rate + (self.stats["may_man"] * 2))
        roll = random.randint(1, 100)
        is_win = roll <= final_rate
        
        res = choice_data["win"] if is_win else choice_data["lose"]
        tien = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        is_dead = False
        if is_win and choice_data.get("die_w", False): is_dead = True
        if not is_win and choice_data.get("die_l", False): is_dead = True

        self.tien_an += tien
        
        kq_thung = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ: **{final_rate}%** (Đổ ra: {roll})\n{kq_thung}: {res} ({tien:,} 💰)"
        
        tuoi_hien_tai = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời khép lại sớm.**")
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
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH", description=f"Ký chủ luân hồi: {self.author.mention}", color=discord.Color.teal())
        
        stats_text = f"Tâm linh / May mắn: **{self.stats['may_man']}/10** *(Được buff +{self.stats['may_man']*2}% Tỉ lệ thành công)*"
        embed.add_field(name="🍀 Chỉ số ban đầu", value=stats_text, inline=False)

        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase <= 5:
            tuoi_next = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
            embed.add_field(name=f"❓ Ngã rẽ quyết định tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.clear_items() 
            user_id = str(self.author.id)
            
            if user_id in dang_choi_nhansinh: 
                dang_choi_nhansinh.remove(user_id)

            user_data = load_user(user_id)
            user_data["money"] += self.tien_an
            save_user(user_id)

            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại một đống nợ khổng lồ.\n❌ **BÁO NHÀ!** Khoản nợ: **{self.tien_an:,} 💰**", inline=False)
            elif self.tien_an >= 30000:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa vinh hoa.\n👑 **ĐẠI PHÚ HÀO!** Di sản để lại: **+{self.tien_an:,} 💰**", inline=False)
            else:
                embed.color = discord.Color.blue()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Một cuộc đời êm ấm trôi qua.\n💼 **DƯ DẢ!** Di sản để lại: **+{self.tien_an:,} 💰**", inline=False)

        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)

# =====================================================================
# GIAO DIỆN UI NÚT BẤM: ĐẠI CHIẾN, KẾT HÔN VÀ CÔNG TY
# =====================================================================
class SoloOTTGame(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        self.bet = bet
        self.msg = None
        self.choices = {str(p1.id): None, str(p2.id): None}

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
            return await interaction.response.send_message("Tránh ra chỗ khác, đây là trận chiến riêng tư!", ephemeral=True)
            
        if self.choices[user_id] is not None:
            return await interaction.response.send_message("Bạn đã ra chiêu rồi, không được rút lại đâu!", ephemeral=True)
            
        self.choices[user_id] = choice
        await interaction.response.send_message(f"🤫 Bạn đã giấu tay chọn **{choice}**. Hãy chờ đối thủ ra chiêu...", ephemeral=True)

        if self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]:
            for child in self.children: child.disabled = True
            
            c1 = self.choices[str(self.p1.id)]
            c2 = self.choices[str(self.p2.id)]
            
            u1_data = load_user(self.p1.id)
            u2_data = load_user(self.p2.id)
            tong_thuong = self.bet * 2
            
            if c1 == c2:
                res = "🤝 **HÒA NHAU!** Tiền cược được trả lại cho cả hai người."
                u1_data["money"] += self.bet
                u2_data["money"] += self.bet
            elif (c1 == "🪨" and c2 == "✂️") or (c1 == "📄" and c2 == "🪨") or (c1 == "✂️" and c2 == "📄"):
                res = f"🎉 **{self.p1.name} ĐÃ CHIẾN THẮNG!**\nHúp trọn nồi lẩu **{tong_thuong:,} 💰**."
                u1_data["money"] += tong_thuong
            else:
                res = f"🎉 **{self.p2.name} ĐÃ CHIẾN THẮNG!**\nHúp trọn nồi lẩu **{tong_thuong:,} 💰**."
                u2_data["money"] += tong_thuong
                
            save_user(self.p1.id)
            save_user(self.p2.id)
            
            embed = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed.add_field(name=self.p1.name, value=f"Ra {c1}", inline=True)
            embed.add_field(name="VS", value="⚡", inline=True)
            embed.add_field(name=self.p2.name, value=f"Ra {c2}", inline=True)
            embed.add_field(name="KẾT QUẢ CUỐI CÙNG", value=res, inline=False)
            
            await self.msg.edit(embed=embed, view=self)
            self.stop()

    async def on_timeout(self):
        if not (self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]):
            u1_data = load_user(self.p1.id)
            u2_data = load_user(self.p2.id)
            
            u1_data["money"] += self.bet
            u2_data["money"] += self.bet
            
            save_user(self.p1.id)
            save_user(self.p2.id)
            
            embed = discord.Embed(
                title="⏳ HẾT GIỜ KHIẾP SỢ", 
                description="Có người nhát gan không dám ra chiêu. Trận đấu bị hủy, tiền cược đã hoàn trả!", 
                color=discord.Color.dark_gray()
            )
            try: 
                await self.msg.edit(embed=embed, view=None)
            except: 
                pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        self.bet = bet

    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.p2.id:
            return await interaction.response.send_message("Kèo này gạ người khác, ông chui vào đây làm gì!", ephemeral=True)
        
        u1_data = load_user(self.p1.id)
        u2_data = load_user(self.p2.id)
        
        if u1_data.get("money",0) < self.bet or u2_data.get("money",0) < self.bet:
            return await interaction.response.send_message("⚠️ Lỗi! Một trong hai người đã tiêu cạn tiền, không đủ lúa để chơi ván này nữa!", ephemeral=True)
        
        u1_data["money"] -= self.bet
        u2_data["money"] -= self.bet
        save_user(self.p1.id)
        save_user(self.p2.id)

        game_view = SoloOTTGame(self.p1, self.p2, self.bet)
        embed = discord.Embed(
            title="⚔️ PK OẲN TÙ TÌ", 
            description=f"{self.p1.mention} 🆚 {self.p2.mention}\nTiền cược: **{self.bet:,} 💰**\n\n👇 **HÃY BẤM NÚT ĐỂ CHỌN CHIÊU (Lựa chọn của bạn sẽ bị giấu kín)**", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=game_view)
        game_view.msg = interaction.message
        self.stop()

class MarryAccept(discord.ui.View):
    def __init__(self, p1, p2):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        
    @discord.ui.button(label="Đồng Ý", style=discord.ButtonStyle.success, emoji="💍")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.p2.id: 
            return await interaction.response.send_message("Không phải hỏi bạn, đừng có bấm bậy!", ephemeral=True)
            
        u1_data = load_user(self.p1.id)
        u2_data = load_user(self.p2.id)
        
        if u1_data.get("money", 0) < 1000000: 
            return await interaction.response.send_message(f"⚠️ {self.p1.name} không đủ 1 Triệu tiền sắm Lễ Cưới nữa rồi!", ephemeral=True)
            
        u1_data["money"] -= 1000000
        u1_data["spouse"] = str(self.p2.id)
        u2_data["spouse"] = str(self.p1.id)
        
        save_user(self.p1.id)
        save_user(self.p2.id)
        
        for child in self.children: 
            child.disabled = True
            
        embed = discord.Embed(
            title="💒 KẾT HÔN THÀNH CÔNG", 
            description=f"🎉 Xin chúc mừng hai vợ chồng {self.p1.mention} và {self.p2.mention}!\nTrăm năm hạnh phúc, rước dâu bằng Mẹc G63 nhé!", 
            color=discord.Color.magenta()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        
    @discord.ui.button(label="Từ Chối", style=discord.ButtonStyle.danger, emoji="💔")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.p2.id: 
            return await interaction.response.send_message("Tránh ra!", ephemeral=True)
            
        for child in self.children: 
            child.disabled = True
            
        embed = discord.Embed(
            description=f"💔 Đắng cay! {self.p2.mention} đã từ chối phũ phàng lời cầu hôn của {self.p1.mention}...", 
            color=discord.Color.dark_grey()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

class CompanyInviteView(discord.ui.View):
    def __init__(self, comp_id, comp_name, target_user):
        super().__init__(timeout=60)
        self.comp_id = comp_id
        self.comp_name = comp_name
        self.target_user = target_user

    @discord.ui.button(label="Gia nhập", style=discord.ButtonStyle.success, emoji="🤝")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: 
            return await interaction.response.send_message("Lệnh mời này không dành cho bạn!", ephemeral=True)
        
        target_id = str(self.target_user.id)
        target_data = load_user(target_id)
        
        if target_data.get("company"): 
            return await interaction.response.send_message("Bạn đã có công ty rồi, phải thoát trước khi gia nhập chỗ mới!", ephemeral=True)
        
        comp = load_company(self.comp_id)
        if not comp: 
            return await interaction.response.send_message("Công ty này đã phá sản hoặc không tồn tại!", ephemeral=True)
        
        comp["members"][target_id] = "nhanvien"
        target_data["company"] = self.comp_id
        
        save_company(self.comp_id)
        save_user(target_id)
        
        await interaction.response.edit_message(content=f"🎉 {self.target_user.mention} đã chính thức gia nhập công ty **{self.comp_name}**!", view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: 
            return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        await interaction.response.edit_message(content=f"❌ {self.target_user.mention} đã chê thẳng thừng lời mời của **{self.comp_name}**.", view=None)
        # =====================================================================
# HỆ THỐNG LỆNH CƠ BẢN VÀ CÀY CUỐC
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH BOT UPDATE 2026", description="Tiền tố lệnh là `k` hoặc `K`.", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(name="🏦 KINH TẾ VIP", value="`k rank` • Thẻ Căn Cước\n`k bank` • Gửi/Rút Két sắt\n`k marry @user` • Kết hôn\n`k cuahang`, `k choden` • Mua bán\n`k daily`, `k lixi`, `k give`", inline=False)
    embed.add_field(name="🏢 CÔNG TY & CHỨNG KHOÁN", value="`k cty tao <tên>` • Lập cty 500k\n`k cty` • Mở Dashboard Cty\n`k daichien @user <hack/phot/giangho>`\n`k ck` • Sàn chứng khoán", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <tài/xỉu> <tiền>`\n`k baucua <con vật> <tiền>`\n`k duathu <con vật> <tiền>`\n`k nohu <tiền>`, `k vietlott <số> <tiền>`", inline=False)
    embed.add_field(name="⛏️ NHẬP VAI SINH TỒN", value="`k cuopnganhang` • Cướp nhà băng\n`k daovang` • Nghề đào mỏ\n`k nhansinh` • Mô phỏng cuộc sống\n`k thamhiem`, `k gacha`, `k phai`", inline=False)
    
    embed.set_footer(text="Chúc các dân chơi sớm mua được Đảo Tư Nhân!", icon_url=ctx.author.display_avatar.url)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def rank(ctx):
    user_data = load_user(ctx.author.id)
    lv = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    tien = user_data.get("money", 0)
    
    embed = discord.Embed(title=f"💳 CĂN CƯỚC CÔNG DÂN: {ctx.author.name.upper()}", color=discord.Color.gold() if tien > 1000000 else discord.Color.teal())
    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
    
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {lv}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    
    if user_data.get("spouse"):
        try:
            spouse_user = await bot.fetch_user(int(user_data["spouse"]))
            spouse_name = spouse_user.name
        except: 
            spouse_name = "Ẩn danh"
        embed.add_field(name="💍 Tình Trạng", value=f"**Đã kết hôn với {spouse_name}**", inline=False)
        
    if user_data.get("company"): 
        comp_info = load_company(user_data['company'])
        if comp_info:
            embed.add_field(name="🏢 Công ty", value=f"**{comp_info['name']}**", inline=False)
            
    if user_data.get("jail_time"): 
        embed.add_field(name="🚨 Trạng thái", value="**Đang bóc lịch trong trại giam!**", inline=False)
    
    embed.add_field(name="✨ Kinh nghiệm", value=f"`{make_progress_bar(xp, lv * 100)}`\n**{xp}/{lv * 100} XP**", inline=False)
    
    assets = user_data.get('assets', [])
    embed.set_footer(text=f"BĐS Sở hữu: {', '.join(assets[:2])}..." if assets else "Gia cảnh: Vô Gia Cư")
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def tuido(ctx):
    user_data = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO BÁU CỦA {ctx.author.name.upper()}", color=discord.Color.dark_purple())
    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
    
    assets = user_data.get("assets", [])
    embed.add_field(name="🏠 Tài Sản Cá Nhân", value="Trống không." if not assets else "\n".join([f"🔸 {a}" for a in assets]), inline=False)
    
    pets = user_data.get("pets", {})
    embed.add_field(name="🐾 Trang Trại Thú Cưng", value="Chưa bắt được con nào." if not pets else "\n".join([f"{p} (x{c})" for p, c in pets.items()]), inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    # Tính tổng tiền ví + tiền ngân hàng để đua TOP
    danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
    
    desc = ""
    for i, (uid, tien) in enumerate(danh_sach[:10]):
        user = bot.get_user(int(uid))
        try: 
            if not user: user = await bot.fetch_user(int(uid))
        except: pass
        ten = user.name if user else f"Người chơi {uid[-4:]}"
        icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**#{i+1}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
        
    embed = discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("last_daily"):
        last_daily = datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            next_t = int((last_daily + timedelta(days=1)).timestamp())
            embed = discord.Embed(description=f"⏳ Tính scam à? Lương tiếp theo nhận vào: <t:{next_t}:R>.", color=discord.Color.orange())
            return await ctx.reply(embed=embed, mention_author=False)
    
    user_data["money"] += 1000
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(title="🎁 QUÀ ĐIỂM DANH", description=f"Nhận **1,000 💰** thành công!\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.green())
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def lixi(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("last_lixi"):
        last_lixi = datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S")
        if now - last_lixi < timedelta(hours=12):
            next_t = int((last_lixi + timedelta(hours=12)).timestamp())
            embed = discord.Embed(description=f"🧧 Lì xì tiếp theo nhận vào: <t:{next_t}:R>.", color=discord.Color.orange())
            return await ctx.reply(embed=embed, mention_author=False)

    tien = random.randint(1000, 8000) 
    user_data["money"] += tien
    user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(description=f"🧧 Bạn mở phong bao đỏ và nhận được **{tien:,} 💰**!\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.red())
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    n_gui = str(ctx.author.id)
    n_nhan = str(member.id)
    gui_data = load_user(n_gui)
    nhan_data = load_user(n_nhan)
    
    if amount <= 0 or gui_data.get("money", 0) < amount or n_gui == n_nhan: 
        embed = discord.Embed(description="⚠️ Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển cho mình).", color=discord.Color.red())
        return await ctx.reply(embed=embed, mention_author=False)
        
    gui_data["money"] -= amount
    nhan_data["money"] += amount
    save_user(n_gui)
    save_user(n_nhan)
    
    embed = discord.Embed(title="💸 CHUYỂN KHOẢN THÀNH CÔNG", description=f"{ctx.author.mention} đã chuyển cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green())
    await ctx.send(embed=embed)


# =====================================================================
# HỆ THỐNG NGÂN HÀNG VÀ KẾT HÔN
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    user_data = load_user(ctx.author.id)
    bank_bal = user_data.get("bank", 0)
    wallet = user_data.get("money", 0)
    
    embed = discord.Embed(
        title="🏦 NGÂN HÀNG TRUNG ƯƠNG", 
        description="Gửi tiền an toàn không lo bị cướp hay lỡ tay đánh bạc hết!\n\n`k bank gui <số tiền/all>`: Gửi tiền vào két sắt\n`k bank rut <số tiền/all>`: Rút tiền ra ví", 
        color=discord.Color.blue()
    )
    embed.add_field(name="💳 Ví tiền mặt", value=f"**{wallet:,} 💰**", inline=True)
    embed.add_field(name="🏦 Số dư Két sắt", value=f"**{bank_bal:,} 💰**", inline=True)
    await ctx.reply(embed=embed, mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    try: 
        amt = user_data["money"] if amount.lower() == "all" else int(amount)
    except ValueError: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập số tiền sai định dạng!", color=discord.Color.red()), mention_author=False)
    
    if amt <= 0 or amt > user_data["money"]: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Số tiền trong ví không đủ để gửi!", color=discord.Color.red()), mention_author=False)
        
    user_data["money"] -= amt
    user_data["bank"] = user_data.get("bank", 0) + amt
    save_user(user_id)
    
    embed = discord.Embed(description=f"✅ Đã đóng gói và gửi an toàn **{amt:,} 💰** vào két sắt ngân hàng!", color=discord.Color.green())
    await ctx.reply(embed=embed, mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    bank_bal = user_data.get("bank", 0)
    
    try: 
        amt = bank_bal if amount.lower() == "all" else int(amount)
    except ValueError: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập số tiền sai định dạng!", color=discord.Color.red()), mention_author=False)
    
    if amt <= 0 or amt > bank_bal: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Số tiền trong ngân hàng không đủ!", color=discord.Color.red()), mention_author=False)
        
    user_data["bank"] -= amt
    user_data["money"] += amt
    save_user(user_id)
    
    embed = discord.Embed(description=f"✅ Đã rút **{amt:,} 💰** từ két sắt mang ra ví tiền mặt!", color=discord.Color.green())
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def marry(ctx, member: discord.Member):
    u1_data = load_user(ctx.author.id)
    u2_data = load_user(member.id)
    
    if ctx.author.id == member.id or member.bot: 
        return await ctx.reply("Lỗi mục tiêu!")
        
    if u1_data.get("spouse"): 
        return await ctx.reply("Bạn đã có vợ/chồng rồi! Muốn ngoại tình à?")
        
    if u2_data.get("spouse"): 
        return await ctx.reply(f"{member.name} là hoa đã có chủ, đập chậu cướp hoa không được đâu!")
        
    if u1_data.get("money", 0) < 1000000: 
        embed = discord.Embed(description="⚠️ Nhẫn cưới kim cương giá **1,000,000 💰**. Bạn không đủ tiền cưới vợ đâu!", color=discord.Color.red())
        return await ctx.reply(embed=embed)
    
    embed = discord.Embed(
        title="💍 CẦU HÔN", 
        description=f"{member.mention} ơi! Đại gia {ctx.author.mention} mang sính lễ 1 củ đang quỳ gối cầu hôn bạn kìa!\n\nBạn có đồng ý sánh bước trăm năm không?", 
        color=discord.Color.pink()
    )
    await ctx.send(embed=embed, view=MarryAccept(ctx.author, member))

@bot.command()
async def divorce(ctx):
    u1_id = str(ctx.author.id)
    u1_data = load_user(u1_id)
    
    if not u1_data.get("spouse"): 
        return await ctx.reply("Bạn đang ế mà ly hôn với ma à?")
    
    u2_id = u1_data["spouse"]
    u2_data = load_user(u2_id)
    
    u1_data["spouse"] = None
    u2_data["spouse"] = None
    
    save_user(u1_id)
    save_user(u2_id)
    
    embed = discord.Embed(description=f"💔 Bạn đã nộp đơn ly hôn ra tòa. Mọi giấy tờ đã được giải quyết, từ nay đường ai nấy đi!", color=discord.Color.dark_grey())
    await ctx.reply(embed=embed, mention_author=False)

# =====================================================================
# HỆ THỐNG CÔNG TY VÀ ĐẠI CHIẾN (FIX LỖI CTY ROI 100%)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")

    if not comp_id:
        embed = discord.Embed(
            title="🏢 SÀN GIAO DỊCH DOANH NGHIỆP", 
            description="Bạn hiện đang thất nghiệp.\nĐể thành lập công ty, gõ:\n`k cty tao <tên công ty>` (Phí: 500,000 💰)", 
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None
        save_user(user_id)
        return await ctx.send("Công ty của bạn đã phá sản từ trước rồi! Hãy lập công ty mới.")
        
    my_role = comp["members"].get(user_id, "nhanvien")
    role_name = comp["roles"].get(my_role, my_role)
    
    embed = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed.add_field(name="Chức vụ của bạn", value=f"**{role_name}**", inline=False)
    
    cmds = "`k cty gop <tiền>`: Góp quỹ\n`k cty thulai`: Nhận lãi mỗi ngày\n`k cty roi`: Nộp đơn nghỉ việc"
    if my_role in ["boss", "quanly"]:
        cmds += "\n`k cty tuyen @user`: Tuyển nhân viên\n`k cty duoi @user`: Đuổi việc"
    if my_role == "boss":
        cmds += "\n`k cty luong <tiền>`: Phát lương toàn Cty\n`k cty chucvu @user <quanly/nhanvien>`\n`k cty doitenchuc <boss/quanly/nhanvien> <Tên>`"
        
    embed.add_field(name="Bảng Lệnh Quản Lý", value=cmds, inline=False)
    await ctx.send(embed=embed)

@cty.command()
async def tao(ctx, *, name: str):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("company"): 
        return await ctx.reply("Bạn đã ở trong một công ty rồi! Thoát ra trước khi tạo mới.", mention_author=False)
        
    if user_data.get("money", 0) < 500000: 
        return await ctx.reply("⚠️ Phí thành lập công ty là **500,000 💰**. Cày thêm đi sếp!", mention_author=False)
    
    user_data["money"] -= 500000
    user_data["company"] = user_id
    
    new_comp = {
        "_id": user_id, 
        "name": name, 
        "treasury": 0, 
        "members": {user_id: "boss"}, 
        "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, 
        "last_interest": "2000-01-01 00:00:00"
    }
    COMPANY_CACHE[user_id] = new_comp
    save_company(user_id)
    save_user(user_id)
    
    embed = discord.Embed(
        title="🏢 KHAI TRƯƠNG HỒNG PHÁT", 
        description=f"Chúc mừng sếp {ctx.author.mention} đã thành lập **{name}**!\nGõ `k cty` để mở bảng điều khiển quản lý.", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@cty.command()
async def tuyen(ctx, member: discord.Member):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.reply("Bạn có công ty đâu mà đòi tuyển người!", mention_author=False)
        
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: 
        return await ctx.reply("Chỉ sếp lớn mới được tuyển người!", mention_author=False)
        
    if load_user(member.id).get("company"): 
        return await ctx.reply("Người này đang làm việc cho công ty khác rồi.", mention_author=False)
    
    view = CompanyInviteView(comp_id, comp["name"], member)
    await ctx.send(f"🏢 {member.mention}, bạn có thư mời nhận việc tại **{comp['name']}**! Bấm nút bên dưới để quyết định.", view=view)

@cty.command()
async def duoi(ctx, member: discord.Member):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: 
        return await ctx.reply("Bạn không có quyền đuổi người!", mention_author=False)
        
    target_id = str(member.id)
    if target_id not in comp["members"]: 
        return await ctx.reply("Người này không có trong công ty!", mention_author=False)
        
    if comp["members"][target_id] == "boss": 
        return await ctx.reply("Tính làm phản hả? Không ai đuổi được sếp tổng đâu!", mention_author=False)
    
    # Xóa khỏi danh sách và clear data người dùng
    del comp["members"][target_id]
    target_data = load_user(target_id)
    target_data["company"] = None
    
    save_company(comp_id)
    save_user(target_id)
    
    await ctx.reply(f"👢 Bộ phận Nhân sự đã đuổi cổ {member.mention} ra khỏi công ty!", mention_author=False)

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.reply("Bạn chưa gia nhập công ty nào.", mention_author=False)
        
    if user_data.get("money", 0) < amount: 
        return await ctx.reply("Không đủ tiền trong ví để góp!", mention_author=False)
    
    comp = load_company(comp_id)
    user_data["money"] -= amount
    comp["treasury"] += amount
    
    save_user(user_id)
    save_company(comp_id)
    
    await ctx.reply(f"💰 Bạn đã cống hiến **{amount:,} 💰** vào quỹ công ty. Tổng quỹ hiện tại: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def thulai(ctx):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": 
        return await ctx.reply("Chỉ Chủ tịch mới được ký giấy thu lãi ngân hàng!", mention_author=False)
    
    now = datetime.now()
    last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    
    if now - last < timedelta(days=1):
        return await ctx.reply("⏳ Kế toán chưa chốt sổ! Mỗi ngày công ty chỉ được thu lãi 1 lần.", mention_author=False)
        
    lai = int(comp["treasury"] * 0.05) 
    if lai > 100000: 
        lai = 100000 # Giới hạn max lãi 100k/ngày để tránh lạm phát kinh tế Server
    
    comp["treasury"] += lai
    comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    
    await ctx.reply(f"📈 Công ty đã nhận được **{lai:,} 💰** tiền lãi hôm nay! Tổng quỹ tăng lên: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def luong(ctx, amount: int):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    if not comp_id: return
    
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": 
        return await ctx.reply("Chỉ Chủ tịch mới được quyền ký quỹ phát lương!", mention_author=False)
        
    mem_count = len(comp["members"])
    total_cost = amount * mem_count
    
    if total_cost > comp["treasury"]: 
        return await ctx.reply(f"Quỹ không đủ! Bạn cần tới {total_cost:,} 💰 để phát cho {mem_count} người.", mention_author=False)
    
    comp["treasury"] -= total_cost
    for m_id in list(comp["members"].keys()):
        m_data = load_user(m_id)
        m_data["money"] += amount
        save_user(m_id)
        
    save_company(comp_id)
    await ctx.send(embed=discord.Embed(description=f"💸 Sếp tổng đã hào phóng phát **{amount:,} 💰** lương cho mỗi nhân viên!\nTổng tiền quỹ bị trừ: **{total_cost:,} 💰**", color=discord.Color.green()))

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
    # LỖI KẸT CÔNG TY ĐÃ ĐƯỢC FIX CỨNG TẠI ĐÂY
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.reply("Bạn chưa gia nhập công ty nào cả!", mention_author=False)
        
    comp = load_company(comp_id)
    if not comp:
        # Nếu DB công ty đã bị xóa nhưng người dùng vẫn còn dính ID
        user_data["company"] = None
        save_user(user_id)
        return await ctx.reply("Công ty của bạn đã không còn tồn tại trên hệ thống.", mention_author=False)
    
    my_role = comp["members"].get(user_id)
    
    if my_role == "boss":
        # Chủ tịch rời đi -> Xóa hoàn toàn công ty khỏi Cache và DB
        COMPANY_CACHE.pop(comp_id, None)
        companies_col.delete_one({"_id": comp_id})
        
        # Lặp qua danh sách nhân viên cũ và giải tán họ an toàn
        for m_id in list(comp["members"].keys()):
            m_data = load_user(m_id)
            m_data["company"] = None
            save_user(m_id)
            
        embed = discord.Embed(description="🏢 Bão tố ập tới! Chủ tịch đã bỏ trốn, công ty tuyên bố **PHÁ SẢN** và giải tán toàn bộ nhân sự!", color=discord.Color.red())
        await ctx.reply(embed=embed, mention_author=False)
    else:
        # Nhân viên tự nộp đơn xin nghỉ
        if user_id in comp["members"]:
            del comp["members"][user_id]
            
        user_data["company"] = None
        save_user(user_id)
        save_company(comp_id)
        
        embed = discord.Embed(description="🎒 Bạn đã nộp đơn xin nghỉ việc, thu dọn hành lý rời khỏi công ty.", color=discord.Color.dark_grey())
        await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def daichien(ctx, member: discord.Member = None, tactic: str = None):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    
    if not member or not tactic or tactic.lower() not in ["hack", "phot", "giangho"]:
        embed = discord.Embed(
            title="⚔️ ĐẠI CHIẾN THƯƠNG TRƯỜNG (SÁNG TẠO)", 
            description="Hãy dùng trí tuệ thay vì số đông để hạ gục đối thủ!\nCách dùng: `k daichien @user <chiến_thuật>`", 
            color=discord.Color.red()
        )
        embed.add_field(name="1. hack (Tấn công mạng)", value="Tỉ lệ thắng: **30%**\nPhần thưởng: Cướp **10%** quỹ đối thủ.\nThất bại: Đền bù **5%** quỹ của mình.", inline=False)
        embed.add_field(name="2. phot (Thuê KOL bóc phốt)", value="Tỉ lệ thắng: **50%**\nPhần thưởng: Cướp **5%** quỹ đối thủ.\nThất bại: Đền bù **2%** quỹ của mình.", inline=False)
        embed.add_field(name="3. giangho (Vũ lực)", value="Tỉ lệ thắng: **70%**\nPhần thưởng: Cướp **2%** quỹ đối thủ.\nThất bại: Đền bù **1%** quỹ của mình.", inline=False)
        return await ctx.send(embed=embed)
        
    target_id = str(member.id)
    target_comp_id = load_user(target_id).get("company")
    
    if user_id == target_id or member.bot: 
        return await ctx.reply("⚠️ Đánh với ai chứ đừng tự kỷ hoặc đi đánh Bot.", mention_author=False)
        
    if not comp_id or not target_comp_id: 
        return await ctx.reply("⚠️ Cả 2 đều phải ở trong công ty thì mới được PK!", mention_author=False)
        
    if comp_id == target_comp_id: 
        return await ctx.reply("⚠️ Cùng một công ty, anh em tương tàn làm gì!", mention_author=False)
    
    now = datetime.now()
    if comp_id in cty_cooldowns and (now - cty_cooldowns[comp_id]).total_seconds() < 3600:
        return await ctx.reply(embed=discord.Embed(description="⏳ Công ty bạn vừa xuất quân rồi! Phải đợi 1 tiếng để hồi phục binh lực.", color=discord.Color.orange()), mention_author=False)
    
    comp1 = load_company(comp_id)
    comp2 = load_company(target_comp_id)
    
    if comp2["treasury"] < 10000: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Quỹ công ty đối thủ nghèo quá (<10k), không đáng để tốn sức cất quân đi đánh!", color=discord.Color.red()), mention_author=False)
    
    cty_cooldowns[comp_id] = now
    tactic = tactic.lower()
    
    if tactic == "hack": 
        win_rate, win_pct, lose_pct, name = 30, 0.10, 0.05, "TẤN CÔNG MẠNG"
    elif tactic == "phot": 
        win_rate, win_pct, lose_pct, name = 50, 0.05, 0.02, "THUÊ BÁO CHÍ BÓC PHỐT"
    else: 
        win_rate, win_pct, lose_pct, name = 70, 0.02, 0.01, "ĐƯA GIANG HỒ ĐẾN ĐẬP PHÁ"
    
    embed = discord.Embed(description=f"⚔️ **{comp1['name']}** đang dùng chiến thuật **{name}** lên đầu **{comp2['name']}**...", color=discord.Color.dark_grey())
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2)
    
    if random.randint(1, 100) <= win_rate:
        steal = int(comp2["treasury"] * win_pct)
        comp1["treasury"] += steal
        comp2["treasury"] -= steal
        save_company(comp_id)
        save_company(target_comp_id)
        
        win_embed = discord.Embed(description=f"🔥 **ĐẠI THẮNG!** Binh pháp quá đỉnh!\n💰 Lính của bạn đã cướp được **{steal:,} 💰** mang về quỹ công ty!", color=discord.Color.green())
        await msg.edit(embed=win_embed)
    else:
        fine = int(comp1["treasury"] * lose_pct)
        comp1["treasury"] -= fine
        comp2["treasury"] += fine
        save_company(comp_id)
        save_company(target_comp_id)
        
        lose_embed = discord.Embed(description=f"💀 **THẤT BẠI NHỤC NHÃ!** Đối thủ đã phòng bị!\nBạn bị kiện ngược và công ty phải đền bù **{fine:,} 💰** cho quỹ đối thủ.", color=discord.Color.red())
        await msg.edit(embed=lose_embed)

# =====================================================================
# HỆ THỐNG SÀN CHỨNG KHOÁN, ĐÀO VÀNG, CƯỚP NGÂN HÀNG, SỔ XỐ
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    next_ts = get_next_hour_timestamp()
    embed = discord.Embed(
        title="📈 SÀN CHỨNG KHOÁN PHỐ WALL", 
        description=f"Cổ phiếu sẽ cập nhật giá mới vào: <t:{next_ts}:R>\n\n🛒 Mua: `k ck buy <MÃ> <SL>`\n💸 Bán: `k ck sell <MÃ> <SL>`", 
        color=discord.Color.blue()
    )
    
    for code, name in STOCKS.items():
        p_now = get_stock_price(code, 0)
        p_old = get_stock_price(code, -1)
        trend = "🟩 Đang Lên" if p_now > p_old else "🟥 Đang Xuống"
        diff = abs(p_now - p_old)
        embed.add_field(name=f"🏢 {code} - {name}", value=f"Giá: **{p_now:,} 💰**\n*(Biến động: {trend} {diff:,})*", inline=False)
        
    user_data = load_user(ctx.author.id)
    my_stocks = user_data.get("stocks", {})
    
    inv = "\n".join([f"🔸 {k}: {v} cổ phiếu" for k, v in my_stocks.items() if v > 0])
    embed.add_field(name="🎒 Cổ phiếu bạn đang giữ", value=inv if inv else "Trống trơn.", inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    if code not in STOCKS or qty <= 0: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Mã cổ phiếu hoặc số lượng không hợp lệ!", color=discord.Color.red()), mention_author=False)
        
    cost = get_stock_price(code, 0) * qty
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) < cost: 
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ Thiếu lúa! Bạn cần **{cost:,} 💰** để mua.", color=discord.Color.red()), mention_author=False)
        
    user_data["money"] -= cost
    user_data["stocks"][code] = user_data.get("stocks", {}).get(code, 0) + qty
    save_user(user_id)
    
    embed = discord.Embed(description=f"✅ Lệnh BUY khớp! Bạn đã mua **{qty} {code}** hết **{cost:,} 💰**.", color=discord.Color.green())
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper()
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    my_qty = user_data.get("stocks", {}).get(code, 0)
    
    if code not in STOCKS or qty <= 0 or my_qty < qty: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn không đủ số lượng cổ phiếu này để bán hoặc nhập mã sai!", color=discord.Color.red()), mention_author=False)
        
    gain = get_stock_price(code, 0) * qty
    user_data["stocks"][code] -= qty
    user_data["money"] += gain
    save_user(user_id)
    
    embed = discord.Embed(description=f"✅ Lệnh SELL khớp! Bạn chốt lời **{qty} {code}** thu về **{gain:,} 💰**.", color=discord.Color.gold())
    await ctx.reply(embed=embed, mention_author=False)

@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("money", 0) < 50000: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn cần phải có tối thiểu 50,000 💰 để làm vốn mua súng M4A1 mới đi cướp được!", color=discord.Color.red()), mention_author=False)
    
    if user_id in cty_cooldowns and (now - cty_cooldowns[user_id]).total_seconds() < 3600:
        return await ctx.reply(embed=discord.Embed(description="⏳ Đang bị truy nã gắt gao cấp độ 5 sao! Hãy đi trốn 1 tiếng nữa rồi hẵng cướp tiếp.", color=discord.Color.orange()), mention_author=False)
    
    cty_cooldowns[user_id] = now
    
    embed = discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Bạn đang đeo mặt nạ đen, cầm súng đạp cửa xông vào Ngân hàng Nhà nước...", color=discord.Color.dark_grey())
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= 20: 
        loot = random.randint(200000, 800000)
        user_data["money"] += loot
        save_user(user_id)
        
        embed.color = discord.Color.green()
        embed.description = f"🎉 **TRÓT LỌT!** Bạn nổ súng uy hiếp giám đốc, vơ vét sạch két sắt và chuồn êm qua đường cống ngầm.\n\n💰 Vụ này húp trọn: **{loot:,} 💰**!"
    else: 
        user_data["money"] -= 50000 
        jail_time = now + timedelta(minutes=10)
        user_data["jail_time"] = jail_time.strftime("%Y-%m-%d %H:%M:%S")
        save_user(user_id)
        
        embed.color = discord.Color.red()
        embed.description = f"🚨 **WEE WOO WEE WOO!** Đặc nhiệm SWAT ập tới thả bom mù!\nBạn bị tóm gọn, xích tay lôi đi.\n\n❌ Mất 50,000 💰 tiền mua súng.\n⛔ **BỊ CẤM DÙNG MỌI LỆNH BOT ĐẾN: <t:{int(jail_time.timestamp())}:R>**!"
        
    await msg.edit(embed=embed)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_id in work_cooldowns and (now - work_cooldowns[user_id]).total_seconds() < 30:
        time_left = int(30 - (now - work_cooldowns[user_id]).total_seconds())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Tay mỏi nhừ rồi sếp! Nghỉ {time_left}s nữa hẵng cuốc tiếp.", color=discord.Color.orange()), mention_author=False)
    
    if "Cuốc Chim ⛏️" not in user_data.get("assets", []):
        if user_data.get("money", 0) < 5000: 
            return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn không có Cuốc Chim, mà tiền ví cũng không đủ 5,000 💰 để mua luôn! Đi cày đi.", color=discord.Color.red()), mention_author=False)
        
        user_data["money"] -= 5000
        user_data["assets"].append("Cuốc Chim ⛏️")
        await ctx.send(embed=discord.Embed(description="🛒 Đã tự động trừ 5k để mua **Cuốc Chim ⛏️** từ cửa hàng và bắt đầu đào!", color=discord.Color.blue()))
    
    work_cooldowns[user_id] = now
    
    msg = await ctx.send(embed=discord.Embed(description="⛏️ Cạch... Cạch... Bạn đang vung cuốc đập đá ở hầm mỏ...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2)
    
    r = random.randint(1, 100)
    if r <= 40: 
        res, val = "Cục Đá Vô Dụng 🪨", 0
    elif r <= 70: 
        res, val = "Mảnh Sắt Vụn 🔩", random.randint(1000, 3000)
    elif r <= 90: 
        res, val = "Thỏi Vàng Ròng 🥇", random.randint(8000, 15000)
    elif r <= 98: 
        res, val = "Viên Kim Cương To Chà Bá 💎", random.randint(50000, 100000)
    else: 
        penalty = int(user_data["money"] * 0.1) if user_data["money"] > 0 else 0
        user_data["money"] -= penalty
        save_user(user_id)
        return await msg.edit(embed=discord.Embed(description=f"💥 **BÙMMMMM!** Xui xẻo đào trúng quả bom thời chiến!\nBệnh viện đã thu viện phí của bạn: **{penalty:,} 💰**!", color=discord.Color.red()))

    user_data["money"] += val
    save_user(user_id)
    embed_color = discord.Color.green() if val > 0 else discord.Color.light_grey()
    await msg.edit(embed=discord.Embed(description=f"⛏️ Đào trúng: **{res}**\nĐem bán được: **{val:,} 💰**", color=embed_color))

@bot.command()
async def vietlott(ctx, so: int, amount: str):
    if so < 0 or so > 99:
        return await ctx.reply(embed=discord.Embed(description="⚠️ Vui lòng chọn 1 con số từ 00 đến 99!", color=discord.Color.red()), mention_author=False)
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    embed = discord.Embed(description=f"🎫 Bạn đã mua vé số **{so:02d}** với giá **{bet:,} 💰**.\n\n🎲 Lồng cầu đang quay...", color=discord.Color.blue())
    msg = await ctx.reply(embed=embed, mention_author=False)
    await asyncio.sleep(3)
    
    kq = random.randint(0, 99)
    
    if so == kq:
        win = bet * 70
        user_data = load_user(user_id)
        user_data["money"] += win
        save_user(user_id)
        
        win_embed = discord.Embed(description=f"🎉 **TRÚNG ĐỘC ĐẮC!** Kết quả xổ số là **{kq:02d}**!\n\nBạn đã trúng gấp 70 lần tiền cược, thu về **{win:,} 💰**!", color=discord.Color.green())
        await msg.edit(embed=win_embed)
    else:
        lose_embed = discord.Embed(description=f"💀 **TRẬT LẤT!** Kết quả xổ số là **{kq:02d}**.\n\nChúc bạn may mắn lần sau, tờ vé số cắn mất của bạn **{bet:,} 💰**.", color=discord.Color.red())
        await msg.edit(embed=lose_embed)


# =====================================================================
# HỆ THỐNG CASINO & GACHA (ĐÃ THÊM TÍNH NĂNG REPLY)
# =====================================================================
@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    embed = discord.Embed(description=f"🪙 {ctx.author.mention} ném **{bet:,} 💰** lên trời...\n🔄 Đồng xu xoay tít trên không...", color=discord.Color.gold())
    msg = await ctx.reply(embed=embed, mention_author=False)
    await asyncio.sleep(2) 

    if random.choice([True, False]):
        user_data = load_user(user_id)
        user_data["money"] += bet * 2
        save_user(user_id)
        win_embed = discord.Embed(description=f"🪙 **MẶT NGỬA!**\n🎉 Chúc mừng đại gia húp trọn **{bet * 2:,} 💰**!\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.green())
        await msg.edit(embed=win_embed)
    else:
        user_data = load_user(user_id)
        lose_embed = discord.Embed(description=f"🪙 **MẶT SẤP!**\n💀 Nhờn với nhà cái! Bay mất **{bet:,} 💰**.\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.red())
        await msg.edit(embed=lose_embed)

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    if choice.lower() not in ["tai", "tài", "xiu", "xỉu"]: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Vui lòng gõ `k taixiu tai <tiền>` hoặc `xiu`.", color=discord.Color.red()), mention_author=False)
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    embed = discord.Embed(title="🎲 LẮC XÍ NGẦU CASINO", description=f"{ctx.author.mention} cược **{bet:,} 💰** vào cửa **{choice.upper()}**.\n\nNhà cái đang lắc... 🫨", color=discord.Color.gold())
    msg = await ctx.reply(embed=embed, mention_author=False)
    await asyncio.sleep(2.5)
    
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    res_str = "xiu" if total <= 10 else "tai"
    
    result_embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    if choice.replace("à", "a").replace("ỉ", "i").lower() == res_str: 
        if d1 == d2 == d3: 
            win_amt = bet * 5
            user_data["money"] += win_amt
            result_txt = f"🔥 **BÃO {d1}-{d2}-{d3}!!! ĐẠI THẮNG x5!**\nHúp trọn **{win_amt:,} 💰**!"
        else: 
            win_amt = bet * 2
            user_data["money"] += win_amt
            result_txt = f"✅ **THẮNG RỒI!** Nhận **{win_amt:,} 💰**!"
        result_embed.color = discord.Color.green()
    else: 
        result_txt = f"💀 **CẮNG RĂNG THUA!** Mất trắng **{bet:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    result_embed.description = f"Kết quả: **[ {d1} | {d2} | {d3} ]** (Tổng: {total} - **{res_str.upper()}**)\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=result_embed)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    valid_choices = {"bau":"🥒", "cua":"🦀", "tom":"🦐", "ca":"🐟", "ga":"🐓", "huou":"🦌"}
    choice_clean = choice.replace("ầ","a").replace("ô","o").lower()
    
    if choice_clean not in valid_choices: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Tên sai! Các cửa gồm: `bau, cua, tom, ca, ga, huou`.", color=discord.Color.red()), mention_author=False)
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    user_icon = valid_choices[choice_clean]
    
    embed = discord.Embed(title="🎲 BẦU CUA TÔM CÁ", description=f"{ctx.author.mention} cược **{bet:,} 💰** vào ô **{user_icon}**.\n\nĐang xóc dĩa... 🫨", color=discord.Color.gold())
    msg = await ctx.reply(embed=embed, mention_author=False)
    await asyncio.sleep(2.5)
    
    dice = [random.choice(list(valid_choices.values())) for _ in range(3)]
    match_count = dice.count(user_icon)
    
    result_embed = discord.Embed(title="🎲 MỞ BÁT KẾT QUẢ")
    if match_count > 0: 
        win_amt = bet + (bet * match_count)
        user_data["money"] += win_amt
        result_txt = f"🎉 **TRÚNG {match_count} Ô!** Thu về **{win_amt:,} 💰**."
        result_embed.color = discord.Color.green()
    else: 
        result_txt = f"💀 **TRẬT LẤT!** Mất trắng **{bet:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    result_embed.description = f"**[ {dice[0]} | {dice[1]} | {dice[2]} ]**\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=result_embed)

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    choice = choice.lower()
    
    if choice not in animals: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Chọn sai con vật! Các cửa cược: `heo`, `cho`, `ngua`, `chuot`.", color=discord.Color.red()), mention_author=False)
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    track_length = 20
    positions = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def get_track():
        txt = f"🏇 **ĐƯỜNG ĐUA THÚ MỞ BÁT!** ({ctx.author.name} cược {bet:,} 💰 vào {animals[choice]})\n\n"
        for pet, pos in positions.items():
            dash_count = min(pos, track_length)
            space_count = track_length - dash_count
            txt += f"🏁{'~'*dash_count}{pet}{' '*space_count}⛩️\n"
        return txt

    msg = await ctx.reply(get_track(), mention_author=False)
    winner = None
    
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in positions:
            positions[pet] += random.randint(2, 6) 
            if positions[pet] >= track_length and winner is None: 
                winner = pet
        await msg.edit(content=get_track())
        if winner: break
        
    if not winner:
        winner = max(positions, key=positions.get)
        positions[winner] = track_length
        await msg.edit(content=get_track())
        
    user_data = load_user(user_id)
    if animals[choice] == winner:
        user_data["money"] += bet * 3
        res_txt = f"\n🏆 **{winner} ĐÃ VỀ NHẤT!** Quá đỉnh, ăn được **x3 tiền ({bet * 3:,} 💰)**!"
    else:
        res_txt = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} của bạn xịt rồi. Mất sạch **{bet:,} 💰**."
        
    save_user(user_id)
    await msg.edit(content=get_track() + res_txt)

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    slots = [random.choice(items) for _ in range(3)]
    
    embed = discord.Embed(title="🎰 MÁY XÈNG CASINO 🎰", color=discord.Color.gold())
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    for _ in range(3):
        embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Máy đang quay tít mù..."
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        
    for _ in range(2):
        embed.description = f"**[ {slots[0]} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đã chốt ô đầu tiên..."
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        
    for _ in range(2):
        embed.description = f"**[ {slots[0]} | {slots[1]} | {random.choice(items)} ]**\n\n🔄 Nín thở chờ ô cuối..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
        
    if slots[0] == slots[1] == slots[2]:
        win_amt = bet * 50 if slots[0] == "👑" else bet * 20 if slots[0] == "💎" else bet * 10
        res = f"🔥 **JACKPOT!!! ĐẠI NỔ HŨ!** Trúng 3 ô {slots[0]}\nBạn húp trọn **{win_amt:,} 💰**!"
        user_data["money"] += win_amt
    elif slots[0] == slots[1] or slots[1] == slots[2] or slots[0] == slots[2]:
        win_amt = bet * 2
        res = f"🎉 **THẮNG NHỎ!** Trúng 2 ô giống nhau.\nBạn nhận được **{win_amt:,} 💰**."
        user_data["money"] += win_amt
    else:
        res = f"💀 **TOANG!** Cờ bạc là bác thằng bần.\nMất sạch **{bet:,} 💰**."
        
    save_user(user_id)
    embed.description = f"**[ {slots[0]} | {slots[1]} | {slots[2]} ]**\n\n{res}"
    embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    cost = 30000
    
    if user_data.get("money", 0) < cost: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Trứng Gacha giá 30k lận. Đi cày thêm đi sếp!", color=discord.Color.red()), mention_author=False)
        
    user_data["money"] -= cost
    save_user(user_id)
    
    embed = discord.Embed(title="🥚 ĐẬP TRỨNG GACHA", description=f"{ctx.author.mention} đang vung búa đập trứng...", color=discord.Color.orange())
    msg = await ctx.reply(embed=embed, mention_author=False)
    await asyncio.sleep(1.5)
    
    embed.description = "⚡ Vỏ nứt rạn... Ánh sáng chói lóa phát ra..."
    await msg.edit(embed=embed)
    await asyncio.sleep(1.5)
    
    r = random.uniform(0, 100)
    if r <= 0.5: ra, t, c = "mythic", "🌌 THẦN THOẠI", discord.Color.dark_purple()
    elif r <= 3.0: ra, t, c = "legendary", "👑 HUYỀN THOẠI", discord.Color.gold()
    elif r <= 10.0: ra, t, c = "epic", "🔮 SỬ THI", discord.Color.magenta()
    elif r <= 30.0: ra, t, c = "rare", "💎 HIẾM", discord.Color.blue()
    else: ra, t, c = "common", "🪵 PHỔ THÔNG", discord.Color.light_grey()
    
    pet_name = random.choice(PET_RATES[ra]["pool"])
    user_data["pets"][pet_name] = user_data["pets"].get(pet_name, 0) + 1
    save_user(user_id)
    
    embed.color = c
    embed.description = f"🎉 Chúc mừng! Trứng nở ra Phẩm chất **{t}**:\n\n✨ Nhận được bé: **{pet_name}**!"
    embed.set_footer(text="Gõ 'k tuido' để ngắm, 'k ban' để bán.", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)

@bot.command()
async def soloott(ctx, member: discord.Member, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    if member.id == ctx.author.id or member.bot: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Lỗi: Không thể thác đấu với chính mình hoặc với Bot.", color=discord.Color.red()), mention_author=False)
        
    if load_user(member.id).get("money", 0) < bet: 
        return await ctx.reply(embed=discord.Embed(description=f"⚠️ {member.mention} đang nghèo, không đủ **{bet:,} 💰** để nhận kèo đâu!", color=discord.Color.red()), mention_author=False)
    
    embed = discord.Embed(
        title="🔥 THÁCH ĐẬU OẲN TÙ TÌ", 
        description=f"{ctx.author.mention} vừa cầm **{bet:,} 💰** đập bàn, thách đấu solo với {member.mention}!\n\nNhanh tay bấm **Nhận Kèo** trong vòng 60 giây nếu dám chơi!", 
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=SoloOTTAccept(ctx.author, member, bet))


# =====================================================================
# LỆNH ADMIN & KẾT THÚC
# =====================================================================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    server_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]: 
            del CONFIG_CACHE[server_id]["allowed_channels"]
        return await ctx.send(embed=discord.Embed(description="✅ Đã gỡ bỏ giới hạn. Bot sẽ nhận lệnh ở **mọi kênh**.", color=discord.Color.green()))

    mentions = ctx.message.channel_mentions
    if not mentions: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Vui lòng tag các kênh. VD: `k setup #kenh-1`", color=discord.Color.red()))
        
    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids
    
    await ctx.send(embed=discord.Embed(description=f"✅ Đã cài đặt! Bot từ nay **CHỈ** nhận lệnh tại: {', '.join(c.mention for c in mentions)}", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount > 0: 
        user_id = str(member.id)
        user_data = load_user(user_id)
        user_data["money"] += amount
        save_user(user_id)
        await ctx.send(embed=discord.Embed(description=f"✅ Sếp tổng {ctx.author.mention} vừa buff nóng cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount > 0: 
        user_id = str(member.id)
        user_data = load_user(user_id)
        user_data["money"] -= amount
        save_user(user_id)
        await ctx.send(embed=discord.Embed(description=f"⚖️ Admin đã tước đoạt **{amount:,} 💰** từ tài khoản của {member.mention}!", color=discord.Color.red()))

@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = str(message.author.id)
    user_data = load_user(user_id)
    
    # Check đi tù không cho nhận EXP chat
    if user_data.get("jail_time"):
        jail_end = datetime.strptime(user_data["jail_time"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            return await bot.process_commands(message)
            
    # Xử lý lên level
    user_data["xp"] += random.randint(5, 15)
    max_xp = user_data["level"] * 100
    
    if user_data["xp"] >= max_xp:
        user_data["xp"] -= max_xp
        user_data["level"] += 1
        thuong = user_data["level"] * 150
        user_data["money"] += thuong
        try: 
            embed = discord.Embed(
                description=f"🎉 **{message.author.mention}** đã đột phá cảnh giới lên **Cấp {user_data['level']}**!\nPhần thưởng: **{thuong:,} 💰**", 
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)
        except: 
            pass
            
    save_user(user_id)
    await bot.process_commands(message)

@bot.event
async def on_ready(): 
    print(f'>>> SIÊU BOT {bot.user} ĐÃ SẴN SÀNG CÀN QUÉT!')

keep_alive() 

# === HAI NỬA MÃ TOKEN ===
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
nua_sau = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'
bot.run(nua_dau + nua_sau)
