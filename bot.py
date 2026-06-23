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
# Xóa lệnh help mặc định của Discord để dùng lệnh help custom siêu đẹp
bot.remove_command('help')

# =====================================================================
# KHO ẢNH GIF ĐỘNG SIÊU VIP (MỚI THÊM)
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
    "fight": "https://media.giphy.com/media/3o7TKsWbXJMIdURvkk/giphy.gif"
}

# =====================================================================
# QUẢN LÝ TRẠNG THÁI (COOLDOWN & BỘ ĐẾM)
# =====================================================================
# Dùng dictionary để lưu trữ thời gian cooldown của từng người chơi, tránh spam lệnh
gamble_cooldowns = {} 
nhansinh_cooldowns = {} 
dang_choi_nhansinh = [] 
cty_cooldowns = {}
work_cooldowns = {} 
vietlott_players = {}

# =====================================================================
# KẾT NỐI MONGODB VÀ HỆ THỐNG BỘ ĐỆM (CACHE)
# =====================================================================
# Chuỗi kết nối đến cơ sở dữ liệu MongoDB của bạn
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

# Khởi tạo kết nối DB
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]

# Các bảng dữ liệu (Collections)
users_col = db["users"]   
config_col = db["config"] 
companies_col = db["companies"]

# Khởi tạo Cache để giảm tải cho DB (Tăng tốc độ phản hồi của Bot lên mức tối đa)
DB_CACHE = {}
CONFIG_CACHE = {}
COMPANY_CACHE = {}

def load_user(user_id):
    """
    Tải dữ liệu người dùng từ Database. 
    Nếu người dùng chưa tồn tại hoặc hệ thống vừa cập nhật tính năng mới, 
    bot sẽ tự động bù đắp các trường dữ liệu còn thiếu.
    """
    user_id = str(user_id)
    
    # Nếu dữ liệu chưa có trong RAM (Cache), tải từ MongoDB
    if user_id not in DB_CACHE:
        document = users_col.find_one({"_id": user_id})
        if document:
            DB_CACHE[user_id] = document
        else:
            DB_CACHE[user_id] = {}
            
    # Bộ khung dữ liệu chuẩn của người chơi (Bổ sung đầy đủ tính năng)
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
    
    # Kiểm tra và bù đắp dữ liệu thiếu một cách an toàn
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
    """Tải cấu hình của Server (Chặn kênh, báo cấp, quyền admin...)"""
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
# HÀM KIỂM TRA TỔNG THỂ (GLOBAL CHECKS) - FIX LỖI CACHE
# =====================================================================
@bot.check
async def global_jail_and_channel_check(ctx):
    """
    Hàm này chạy trước MỌI lệnh của bot.
    Nó sẽ kiểm tra xem người dùng có đang bị đi tù hay không,
    và kiểm tra xem kênh hiện tại có được phép dùng bot hay không.
    """
    # Miễn trừ cho Quản trị viên và lệnh xem hướng dẫn (Help)
    if ctx.author.guild_permissions.administrator or ctx.command.name == "help": 
        return True
        
    user_data = load_user(ctx.author.id)
    jail_time_str = user_data.get("jail_time")
    
    # Xử lý án phạt tù
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
            # Hết thời gian phạt, tự động xóa án tích
            user_data["jail_time"] = None
            save_user(ctx.author.id)
            
    # Xử lý kẹt kênh (Chỉ cho phép dùng bot ở kênh được chỉ định)
    if ctx.guild:
        server_config = load_server_config(ctx.guild.id)
        allowed_channels = server_config.get("allowed_channels", [])
        
        if allowed_channels and ctx.channel.id not in allowed_channels: 
            return False
            
    return True

def make_progress_bar(current_value, total_value, bar_length=12):
    """
    Tạo thanh tiến trình hiển thị điểm kinh nghiệm (XP) bằng Emoji siêu đẹp.
    Ví dụ: 🟩🟩🟩🟩⬛⬛⬛⬛⬛⬛
    """
    progress_blocks = int((current_value / total_value) * bar_length)
    empty_blocks = bar_length - progress_blocks
    return "🟩" * progress_blocks + "⬛" * empty_blocks

async def check_gamble_conditions(ctx, amount_str):
    """
    Hàm xác thực điều kiện cờ bạc khắt khe nhất để chống spam và chống lỗi.
    Đã bổ sung thêm logic chống âm tiền tuyệt đối.
    """
    user_id = str(ctx.author.id)
    current_time = datetime.now()
    
    # 1. Kiểm tra Cooldown chống spam lệnh (4 giây)
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
    
    # 2. Kiểm tra tình trạng nợ nần
    if user_data.get("money", 0) <= 0:
        embed_bankrupt = discord.Embed(
            description="💸 Kẻ tổn thương lại muốn tổn thương sòng bạc à? Tiền trong ví không có một xu mà đòi cá cược! Hãy dùng lệnh `k daily` để nhận trợ cấp xã hội.", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
        return None, None
        
    # 3. Chuyển đổi và xác thực số tiền cược
    try: 
        if amount_str.lower() == "all":
            # Xử lý lệnh all-in: Tự động giới hạn ở mức 500k nếu tiền trong ví lớn hơn 500k
            bet_amount = user_data["money"] if user_data["money"] <= 500000 else 500000
        else:
            bet_amount = int(amount_str)
    except ValueError: 
        embed_error = discord.Embed(
            description="⚠️ Nhập số tiền sai định dạng rồi! Vui lòng nhập số cụ thể hoặc chữ `all`.", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_error, mention_author=False)
        return None, None
        
    # 4. Kiểm tra giới hạn ví tiền
    if bet_amount <= 0 or bet_amount > user_data["money"]: 
        embed_poor = discord.Embed(
            description=f"⚠️ Bốc phét à? Sếp chỉ có **{user_data['money']:,} 💰** trong ví thôi, đào đâu ra mà cược lắm thế!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_poor, mention_author=False)
        return None, None
        
    # 5. Kiểm tra giới hạn cược tối đa
    if bet_amount > 500000: 
        embed_max_bet = discord.Embed(
            description="🛑 Nhà cái quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_max_bet, mention_author=False)
        return None, None
        
    return user_data, bet_amount

# =====================================================================
# DATA CỬA HÀNG ĐẠI GIA VÀ CHỢ ĐEN CẦM ĐỒ (KHÔNG RÚT GỌN)
# =====================================================================
SHOP_ITEMS = {
    # ------------------ DANH HIỆU KHÈ NHAU ------------------
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
    
    # ------------------ SIÊU XE VÀ PHƯƠNG TIỆN ------------------
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
    
    # ------------------ BẤT ĐỘNG SẢN ------------------
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
# =====================================================================
# DATA GACHA THÚ CƯNG (TỶ LỆ VÀ DANH SÁCH)
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
    Sử dụng seed sinh số ngẫu nhiên theo GIỜ. Ai kiểm tra cũng ra giá giống nhau,
    chỉ thay đổi khi qua giờ mới.
    """
    target_time = datetime.now() + timedelta(hours=hour_offset)
    # Tạo chuỗi seed dựa trên Thời gian (Năm Tháng Ngày Giờ) và Mã cổ phiếu
    seed_value = int(target_time.strftime("%Y%m%d%H")) + sum(ord(char) for char in stock_code)
    random_generator = random.Random(seed_value)
    
    # Cổ phiếu dao động mạnh từ 5k đến 500k
    return random_generator.randint(5, 500) * 1000

def get_next_hour_timestamp():
    """Lấy Timestamp của khung giờ tiếp theo để hiển thị đếm ngược trên tin nhắn"""
    next_hour = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int(next_hour.timestamp())

def get_asset_price(asset_name):
    """Tính giá bán lại tài sản vào chợ đen (Bị ép giá, lỗ 30%)"""
    for item_key, item_data in SHOP_ITEMS.items():
        if item_data["name"] == asset_name: 
            return int(item_data["price"] * 0.7)
    return 1000

def get_pet_sell_price(pet_name):
    """
    Tính giá bán thú cưng theo độ hiếm. 
    Common/Rare thì bán lỗ, Epic/Legendary/Mythic thì bán lãi cực mạnh.
    """
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 5000      
            if rarity == "rare": return 20000       
            if rarity == "epic": return 150000      
            if rarity == "legendary": return 800000 
            if rarity == "mythic": return 10000000   
    return 1000

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
# DATA NHÂN SINH (CÁC SỰ KIỆN CUỘC ĐỜI THEO TỪNG ĐỘ TUỔI)
# =====================================================================
# Kịch bản được trình bày chuẩn PEP8, không rút gọn, dễ dàng thêm bớt
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
        "q": "Tuổi 15: Bạn thấy mấy anh giang hồ đang trấn lột tiền bạn cùng lớp.", 
        "choices": [
            {
                "text": "Lao vào đấm nhau", 
                "rate": 15, 
                "win": "Đánh thắng 3 thằng, thành đại ca trường.", 
                "lose": "Bị đấm sưng mỏ, phải nhập viện.", 
                "tien_w": 3000, 
                "tien_l": -5000
            }, 
            {
                "text": "Báo ngay cho giám thị", 
                "rate": 85, 
                "win": "Bọn cướp bị đuổi học, bạn được tuyên dương.", 
                "lose": "Giám thị không tin lời bạn nói.", 
                "tien_w": 1000, 
                "tien_l": -200
            }, 
            {
                "text": "Hét to 'CÔNG AN TỚI' rồi chạy", 
                "rate": 60, 
                "win": "Bọn nó hoảng loạn bỏ chạy tán loạn.", 
                "lose": "Bị bọn nó phát hiện và rượt theo đánh.", 
                "tien_w": 500, 
                "tien_l": -2000
            }, 
            {
                "text": "Đứng quay Tiktok", 
                "rate": 40, 
                "win": "Video viral, kênh lên triệu view kiếm bộn tiền.", 
                "lose": "Bị bọn giang hồ giật điện thoại đập nát.", 
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
                "win": "Bitcoin x10! Bạn mua được Mẹc G63.", 
                "lose": "Thị trường sập, bạn mất trắng ra đê ở.", 
                "tien_w": 50000, 
                "tien_l": -90000
            }, 
            {
                "text": "Gửi tiết kiệm ngân hàng", 
                "rate": 95, 
                "win": "Cuộc sống bình yên ăn lãi qua ngày.", 
                "lose": "Ngân hàng phá sản (hiếm nhưng có).", 
                "tien_w": 5000, 
                "tien_l": -100000
            }, 
            {
                "text": "Mở quán cafe khởi nghiệp", 
                "rate": 50, 
                "win": "Khách đông nườm nượp, mở chuỗi 5 chi nhánh.", 
                "lose": "Dịch bệnh ập tới, đóng cửa sang nhượng chịu lỗ.", 
                "tien_w": 30000, 
                "tien_l": -50000
            }, 
            {
                "text": "Đi du lịch vòng quanh thế giới", 
                "rate": 80, 
                "win": "Trải nghiệm mở mang tầm mắt, viết sách bán chạy.", 
                "lose": "Bị trộm móc túi sạch sẽ ở Paris.", 
                "tien_w": 15000, 
                "tien_l": -30000
            }
        ]
    },
    {
        "q": "Tuổi 25: Sếp chửi bạn xối xả giữa công ty dù bạn không hề sai.", 
        "choices": [
            {
                "text": "Đập bàn nghỉ việc", 
                "rate": 40, 
                "win": "Công ty đối thủ mời bạn làm Giám đốc ngay hôm sau.", 
                "lose": "Thất nghiệp ròng rã 6 tháng trời.", 
                "tien_w": 40000, 
                "tien_l": -20000
            }, 
            {
                "text": "Nhịn nhục xin lỗi", 
                "rate": 90, 
                "win": "Cuối năm được thăng chức và tăng lương chút xíu.", 
                "lose": "Uất ức sinh trầm cảm, tốn tiền đi khám tâm lý.", 
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
                "win": "Công ty bị cộng đồng mạng tẩy chay, sếp bị đuổi.", 
                "lose": "Bị công ty kiện ra tòa tội vu khống.", 
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
                "lose": "Dính bẫy lừa đảo dự án ma, ra đê ở.", 
                "tien_w": 150000, 
                "tien_l": -200000, 
                "die_l": True
            }, 
            {
                "text": "Mua 1 lô nhỏ an toàn", 
                "rate": 60, 
                "win": "Lãi gấp đôi sau 2 năm.", 
                "lose": "Đất dính quy hoạch treo, giam vốn 10 năm.", 
                "tien_w": 40000, 
                "tien_l": -30000
            }, 
            {
                "text": "Làm cò đất ăn hoa hồng", 
                "rate": 80, 
                "win": "Bán được chục lô, cuộc sống ấm no.", 
                "lose": "Bị giang hồ bảo kê tranh địa bàn đánh đập.", 
                "tien_w": 25000, 
                "tien_l": -15000
            }, 
            {
                "text": "Mua vàng cất két sắt", 
                "rate": 95, 
                "win": "Vàng lên giá vù vù.", 
                "lose": "Trộm vào nhà cạy két lấy sạch.", 
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
                "win": "Bạn làm ăn phất lên, trả lại gấp 3 đền ơn.", 
                "lose": "Nó chặn số, bom tiền chạy mất tiêu.", 
                "tien_w": 150000, 
                "tien_l": -50000
            }, 
            {
                "text": "Bảo không có tiền", 
                "rate": 95, 
                "win": "Giữ được tiền, không sứt mẻ gì.", 
                "lose": "Bị nó chửi là đồ ki bo kẹt xỉ.", 
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
                "lose": "Thị trường sập, ôm bó cỏ khô lỗ chổng vó.", 
                "tien_w": 80000, 
                "tien_l": -50000
            }, 
            {
                "text": "Cặp Sugar Baby cho hồi xuân", 
                "rate": 25, 
                "win": "Tâm hồn trẻ lại phơi phới.", 
                "lose": "Bị vợ/chồng bắt ghen thu hết tài sản.", 
                "tien_w": 5000, 
                "tien_l": -200000
            }, 
            {
                "text": "Tập Thiền, dọn về quê nuôi cá", 
                "rate": 90, 
                "win": "Tâm hồn thanh tịnh, khí huyết lưu thông trường thọ.", 
                "lose": "Về quê bị muỗi vằn đốt sốt xuất huyết.", 
                "tien_w": 15000, 
                "tien_l": -5000
            }
        ]
    },
    {
        "q": "Tuổi 50: Đi khám tổng quát, bác sĩ bảo bạn có khối u ác tính.", 
        "choices": [
            {
                "text": "Bán nhà sang Mỹ chữa trị", 
                "rate": 80, 
                "win": "Chữa khỏi hoàn toàn, sống khỏe thêm 30 năm.", 
                "lose": "Tai nạn máy bay trên đường đi chữa bệnh.", 
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
                "win": "Được thưởng bằng khen và một cục tiền lớn.", 
                "lose": "Rương rỗng, tốn công khiêng lên phường.", 
                "tien_w": 50000, 
                "tien_l": 0
            }, 
            {
                "text": "Tự mở ra xem", 
                "rate": 20, 
                "win": "Bên trong đầy vàng thỏi, bạn thành tài phiệt!", 
                "lose": "Trúng bẫy độc của cổ nhân, đột tử tại chỗ.", 
                "tien_w": 500000, 
                "tien_l": -10000, 
                "die_l": True
            }, 
            {
                "text": "Bán ra chợ đen", 
                "rate": 40, 
                "win": "Con buôn đồ cổ trả giá cực cao.", 
                "lose": "Bị công an bắt quả tang buôn lậu cổ vật.", 
                "tien_w": 200000, 
                "tien_l": -150000
            }, 
            {
                "text": "Chôn lại chỗ cũ", 
                "rate": 100, 
                "win": "Bình yên vô sự, con cháu sau này hưởng.", 
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
                "win": "Con cháu hòa thuận mừng thọ linh đình.", 
                "lose": "Con cháu đánh nhau giành giật, bạn tức quá đột quỵ.", 
                "tien_w": 10000, 
                "tien_l": -20000, 
                "die_l": True
            }, 
            {
                "text": "Quyên góp từ thiện hết", 
                "rate": 90, 
                "win": "Được nhà nước tạc tượng vinh danh công đức.", 
                "lose": "Tổ chức từ thiện cuỗm tiền chạy mất.", 
                "tien_w": 20000, 
                "tien_l": -100000, 
                "die_l": True
            }, 
            {
                "text": "Lên Las Vegas quất 1 ván Casino cuối đời", 
                "rate": 15, 
                "win": "Trúng Jackpot 50 triệu đô! Lên báo quốc tế.", 
                "lose": "Thua trắng tay, nhồi máu cơ tim gục tại bàn.", 
                "tien_w": 2000000, 
                "tien_l": -100000, 
                "die_l": True
            }
        ]
    }
]

# =====================================================================
# GIAO DIỆN UI: CỬA HÀNG ĐẠI GIA VÀ CHỢ ĐEN CẦM ĐỒ
# =====================================================================
class ShopItemSelect(discord.ui.Select):
    """Bảng chọn đồ trong Cửa Hàng (Dropdown Menu)"""
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
            placeholder="Nhấn vào đây để chọn món đồ muốn mua...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_info = SHOP_ITEMS[self.values[0]]
        
        # Kiểm tra tiền
        if user_data.get("money", 0) < item_info["price"]:
            embed_fail = discord.Embed(
                description=f"⚠️ Tiền trong ví không đủ! Bạn cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        # Xử lý mua Danh hiệu
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            msg = f"🎉 Chúc mừng! Bạn đã trang bị danh hiệu mới: **{item_info['name']}**."
        else:
            # Xử lý mua Đồ vật
            if item_info["name"] in user_data["assets"]:
                # Nếu đã có, hoàn lại tiền và báo lỗi
                user_data["money"] += item_info["price"] 
                embed_exist = discord.Embed(
                    description=f"⚠️ Bạn đã sở hữu **{item_info['name']}** rồi, không cần mua thêm nữa đâu đại gia!", 
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed_exist, ephemeral=True)
            
            user_data["assets"].append(item_info["name"])
            msg = f"🎉 Chúc mừng! Bạn vừa tậu thành công siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        
        embed_success = discord.Embed(
            title="🛍️ GIAO DỊCH THÀNH CÔNG!", 
            description=msg, 
            color=discord.Color.green()
        )
        embed_success.set_footer(
            text=f"Số dư ví còn lại: {user_data['money']:,} 💰", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    """Menu chọn 3 danh mục trong Cửa hàng"""
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(
            title="🛍️ QUẦY BÁN DANH HIỆU", 
            description="Mua danh hiệu xịn để gắn lên Thẻ Căn Cước.", 
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Phương Tiện", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(
            title="🛍️ SHOWROOM XE CỘ & PHI CƠ", 
            description="Đẳng cấp siêu xe chỉ dành cho người có tiền.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(
            title="🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN", 
            description="Đầu tư nhà đất không bao giờ lỗ.", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        # Chỉ người gõ lệnh mới được bấm nút
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
            for pet, qty in list(items.items()):
                if count >= 25: break
                if qty > 0: 
                    options.append(discord.SelectOption(
                        label=pet, 
                        description=f"Số lượng đang có: {qty} | Giá bán: {get_pet_sell_price(pet):,} 💰", 
                        value=pet
                    ))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(
                    label=asset, 
                    description=f"Con buôn thu mua: {get_asset_price(asset):,} 💰", 
                    value=asset
                ))
                
        super().__init__(placeholder="Chọn món đồ đem đi cầm cố để lấy tiền...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_value = self.values[0]
        
        if self.is_pet:
            # Kiểm tra xem có ăn gian không
            if user_data.get("pets", {}).get(item_value, 0) <= 0: 
                return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này trong túi đồ!", ephemeral=True)
                
            sell_price = get_pet_sell_price(item_value)
            user_data["pets"][item_value] -= 1
            if user_data["pets"][item_value] == 0: 
                del user_data["pets"][item_value]
                
            msg = f"✅ Thương lái đã thu mua lại **{item_value}**.\nBạn nhận được **{sell_price:,} 💰** tiền mặt!"
        else:
            if item_value not in user_data.get("assets", []): 
                return await interaction.response.send_message("Lỗi: Không tìm thấy tài sản này trong kho!", ephemeral=True)
                
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            msg = f"✅ Chủ tiệm cầm đồ đã thâu tóm **{item_value}**.\nBạn vớt vát lại được **{sell_price:,} 💰**!"

        user_data["money"] += sell_price
        save_user(user_id)
        
        embed = discord.Embed(
            title="🤝 GIAO DỊCH HOÀN TẤT", 
            description=msg, 
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
            embed_err = discord.Embed(description="Bạn không có tài sản nào để bán cả!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        
        embed = discord.Embed(
            title="🏷️ CẦM ĐỒ BĐS & XE CỘ", 
            description="Lưu ý: Bạn sẽ bị con buôn ép giá, bán lại sẽ mất 30% giá trị so với lúc mua.", 
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        # Kiểm tra xem có pet nào số lượng > 0 không
        if not pets or all(qty == 0 for qty in pets.values()): 
            embed_err = discord.Embed(description="Bạn chưa bắt được con Thú cưng nào để bán cả!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        
        embed = discord.Embed(
            title="🏷️ TRẠM THU MUA THÚ CƯNG", 
            description="Thu mua thú cưng đổi lấy tiền mặt nhanh gọn lẹ.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: 
            return False
        return True
        # =====================================================================
# GIAO DIỆN UI NÚT BẤM: KHU RỪNG THÁM HIỂM (MINIGAME NHÂN PHẨM)
# =====================================================================
class BushButton(discord.ui.Button):
    """Nút bấm đại diện cho các lùm cây trong rừng"""
    def __init__(self, label, custom_id):
        super().__init__(
            label=label, 
            style=discord.ButtonStyle.success, 
            custom_id=custom_id, 
            emoji="🌲"
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        weapon_info = WEAPON_ODDS[view.weapon_val]
        
        # Khóa tất cả các nút ngay khi người chơi vừa bấm để tránh bug spam 2 lần
        for child in view.children: 
            child.disabled = True
            
        # Tạo hiệu ứng hồi hộp khi bước vào lùm cây
        loading_embed = discord.Embed(
            description=f"🌲 {interaction.user.mention} đang vác **{weapon_info['name']}** lén lút tiến vào lùm cây...", 
            color=discord.Color.dark_green()
        )
        await interaction.response.edit_message(embed=loading_embed, view=view)
        await asyncio.sleep(2)

        # Lấy dữ liệu người dùng
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        old_money = user_data.get("money", 0)

        # Tính toán xác suất dựa trên vũ khí người chơi đang cầm
        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [
            weapon_info["terrible"], 
            weapon_info["bad"], 
            weapon_info["neutral"], 
            weapon_info["good"], 
            weapon_info["great"], 
            weapon_info["jackpot"]
        ]
        
        # Chọn ra loại sự kiện sẽ xảy ra
        category = random.choices(choices, weights=weights, k=1)[0]
        
        # Chọn ngẫu nhiên 1 câu thoại trong loại sự kiện đó
        scenario = random.choice(SCENARIOS[category])
        
        # Tính toán số tiền thưởng hoặc phạt
        if "mult" in scenario:
            thuong_phat = int(weapon_info['price'] * scenario["mult"])
        else:
            thuong_phat = 0
            
        # Cập nhật tiền cho người chơi
        user_data["money"] += thuong_phat
        
        # Tính toán lợi nhuận của toàn bộ chuyến đi (bao gồm cả các lượt trước)
        actual_change = user_data["money"] - old_money
        new_session_profit = view.session_profit + actual_change
        
        save_user(user_id)
        
        # Thiết lập màu sắc và text hiển thị dựa trên kết quả
        if new_session_profit > 0:
            profit_text = f"LÃI +{new_session_profit:,} 💰"
        elif new_session_profit < 0:
            profit_text = f"LỖ {new_session_profit:,} 💰"
        else:
            profit_text = "HUỀ VỐN"
            
        if thuong_phat > 0:
            embed_color = discord.Color.green()
        elif thuong_phat < 0:
            embed_color = discord.Color.red()
        else:
            embed_color = discord.Color.light_gray()
        
        # Tạo bảng kết quả trả về
        res_embed = discord.Embed(
            title="MỞ LÙM CÂY TÌM ĐƯỢC...", 
            description=f"**{scenario['msg']}**", 
            color=embed_color
        )
        
        if thuong_phat > 0:
            res_embed.add_field(name="Thu Hoạch", value=f"**+{thuong_phat:,} 💰**", inline=True)
        elif thuong_phat < 0:
            res_embed.add_field(name="Thua Lỗ", value=f"**{thuong_phat:,} 💰**", inline=True)
        else:
            res_embed.add_field(name="Kết Quả", value="**Trắng tay**", inline=True)
            
        res_embed.add_field(name="Tổng Lợi Nhuận Chuyến Đi", value=f"**{profit_text}**", inline=True)
        res_embed.set_footer(
            text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", 
            icon_url=interaction.user.display_avatar.url
        )
        
        # Chuyển sang View hỏi người chơi có muốn đi tiếp không
        res_view = ResultView(interaction.user, new_session_profit)
        msg = await interaction.original_response()
        await msg.edit(content=None, embed=res_embed, view=res_view)

class ResultView(discord.ui.View):
    """Bảng hiển thị hỏi người chơi đi tiếp hay về nhà"""
    def __init__(self, author, session_profit):
        super().__init__(timeout=120)
        self.author = author
        self.session_profit = session_profit
        
        # Nút đi tiếp
        btn_tiep = discord.ui.Button(
            label="Tiếp tục Khám Phá", 
            style=discord.ButtonStyle.primary, 
            emoji="🔄"
        )
        btn_tiep.callback = self.continue_explore
        self.add_item(btn_tiep)
        
        # Nút dừng lại
        btn_dung = discord.ui.Button(
            label="Về Nhà (Dừng lại)", 
            style=discord.ButtonStyle.danger, 
            emoji="🛑"
        )
        btn_dung.callback = self.stop_explore
        self.add_item(btn_dung)

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Của ai người nấy chơi nhé, bạn không được bấm!", ephemeral=True)
            return False
        return True

    async def continue_explore(self, interaction: discord.Interaction):
        # Mở lại trạm tiếp tế để người chơi mua vũ khí mới
        shop_embed = discord.Embed(
            title="🛒 TRẠM TIẾP TẾ THÁM HIỂM", 
            description="Hãy nghỉ ngơi và chọn mua vũ khí mới để đi sâu hơn vào rừng.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA** 👇", 
            color=discord.Color.orange()
        )
        
        if self.session_profit >= 0:
            profit_str = f"Đang LÃI +{self.session_profit:,} 💰"
        else:
            profit_str = f"Đang LỖ {self.session_profit:,} 💰"
            
        shop_embed.set_footer(text=f"Kỷ lục chuyến đi hiện tại: {profit_str}")
        
        view = KhungRungShopView(self.author, self.session_profit)
        await interaction.response.edit_message(embed=shop_embed, view=view)

    async def stop_explore(self, interaction: discord.Interaction):
        # Chốt sổ và vô hiệu hóa nút
        for child in self.children: 
            child.disabled = True
            
        if self.session_profit > 0:
            profit_text = f"LÃI +{self.session_profit:,} 💰"
        elif self.session_profit < 0:
            profit_text = f"LỖ {self.session_profit:,} 💰"
        else:
            profit_text = "HUỀ VỐN"
            
        end_embed = discord.Embed(
            title="🛑 KẾT THÚC CHUYẾN ĐI", 
            description=f"Bạn đã an toàn trở về nhà.\nTổng kết sau chuyến đi dài, bạn mang về: **{profit_text}**", 
            color=discord.Color.dark_grey()
        )
        await interaction.response.edit_message(embed=end_embed, view=self)

class BushView(discord.ui.View):
    """View chứa 5 lùm cây cho người chơi lựa chọn"""
    def __init__(self, author, weapon_val, session_profit):
        super().__init__(timeout=60)
        self.author = author
        self.weapon_val = weapon_val
        self.session_profit = session_profit
        
        # Khởi tạo 5 nút lùm cây
        for i in range(5): 
            self.add_item(BushButton(label=f"Lùm Cây {i+1}", custom_id=f"bush_{i}"))

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            return False
        return True

class WeaponSelect(discord.ui.Select):
    """Bảng Dropdown chọn vũ khí tại trạm tiếp tế"""
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = []
        
        # Đọc danh sách vũ khí từ DATA
        for key, item in WEAPON_ODDS.items():
            options.append(
                discord.SelectOption(
                    label=item['name'], 
                    description=f"Giá: {item['price']:,} 💰", 
                    value=key
                )
            )
            
        super().__init__(
            placeholder="Nhấn để chọn vũ khí muốn mua...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        weapon_id = self.values[0]
        price = WEAPON_ODDS[weapon_id]["price"]
        
        # Kiểm tra tiền
        if user_data.get("money", 0) < price:
            embed_err = discord.Embed(
                description=f"⚠️ Nghèo quá! Bạn không đủ **{price:,} 💰** để mua vũ khí này!", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        # Trừ tiền mua vũ khí
        user_data["money"] -= price
        save_user(user_id)
        
        embed_start = discord.Embed(
            title="🌲 RỪNG SÂU NƯỚC ĐỘC 🌲", 
            description=f"Bạn đã trang bị **{WEAPON_ODDS[weapon_id]['name']}**.\nPhía trước mặt có 5 lùm cây khả nghi. Hãy nhấp vào 1 lùm cây để khám phá!", 
            color=discord.Color.dark_green()
        )
        
        view_bush = BushView(interaction.user, weapon_id, self.session_profit - price)
        await interaction.response.edit_message(embed=embed_start, view=view_bush)

class KhungRungShopView(discord.ui.View):
    """View bao bọc bảng chọn vũ khí"""
    def __init__(self, author, session_profit=0):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(WeaponSelect(session_profit))

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            return False
        return True

# =====================================================================
# GIAO DIỆN UI NÚT BẤM: TRẠM TREO MÁY AFK
# =====================================================================
class ExpSelect(discord.ui.Select):
    """Bảng chọn thời gian treo máy"""
    def __init__(self):
        options = [
            discord.SelectOption(
                label="4 Giờ (Bãi Cỏ Yên Bình)", 
                description="Phần thưởng dự kiến: ~450 💰", 
                emoji="🌿", 
                value="4"
            ),
            discord.SelectOption(
                label="8 Giờ (Hang Động Tối Tăm)", 
                description="Phần thưởng dự kiến: ~1000 💰", 
                emoji="🦇", 
                value="8"
            ),
            discord.SelectOption(
                label="12 Giờ (Di Tích Nguy Hiểm)", 
                description="Phần thưởng dự kiến: ~2000 💰", 
                emoji="🏛️", 
                value="12"
            )
        ]
        super().__init__(
            placeholder="Chọn khu vực cắm trại...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        hours = int(self.values[0])
        
        # Random phần thưởng theo thời gian
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
            description=f"Hành lý đã chuẩn bị xong. Bạn bắt đầu cắm trại **{hours} giờ**.\nKhi nào hết thời gian, hãy gõ lại lệnh `k phai` để thu hoạch nhé.", 
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
# GIAO DIỆN UI: GAME NHÂN SINH LỰA CHỌN ĐA VŨ TRỤ
# =====================================================================
class NhanSinhGameView(discord.ui.View):
    """Hệ thống lõi của Game Nhân Sinh"""
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        # Khởi tạo kịch bản tuổi 15
        self.ev = random.choice(EVENTS_P1)

        # Mở bài theo độ may mắn
        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng, chạy quanh nhà bằng siêu xe đồ chơi.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm, bình yên.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài đầu đường xó chợ từ nhỏ.")

        # Khởi tạo Nút lựa chọn A, B, C, D
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
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng bấm vào cuộc đời của người khác!", ephemeral=True)
            return False
        return True

    # Các hàm liên kết nút bấm
    async def choice_a(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 0, "A")
        
    async def choice_b(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 1, "B")
        
    async def choice_c(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 2, "C")
        
    async def choice_d(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        # May mắn sẽ cộng thêm tỉ lệ % thành công
        final_rate = min(95, base_rate + (self.stats["may_man"] * 2))
        roll = random.randint(1, 100)
        is_win = roll <= final_rate
        
        res = choice_data["win"] if is_win else choice_data["lose"]
        tien = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        # Kiểm tra cái chết
        is_dead = False
        if is_win and choice_data.get("die_w", False): 
            is_dead = True
        if not is_win and choice_data.get("die_l", False): 
            is_dead = True

        self.tien_an += tien
        
        # Lưu log
        kq_thung = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ thành công: **{final_rate}%** (Bạn đổ ra: {roll})\n{kq_thung}: {res} ({tien:,} 💰)"
        
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
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Bạn chọn {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời khép lại sớm.**")
            self.phase = 99 # Đẩy phase lên max để ngưng game
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Bạn chọn {letter}.\n{log_entry}")
            self.phase += 1
            
            # Cập nhật câu hỏi tiếp theo
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
        embed = discord.Embed(
            title="🌀 MÔ PHỎNG NHÂN SINH", 
            description=f"Ký chủ luân hồi: {self.author.mention}", 
            color=discord.Color.teal()
        )
        
        stats_text = f"Tâm linh / May mắn: **{self.stats['may_man']}/10** *(Được buff +{self.stats['may_man']*2}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số ban đầu", value=stats_text, inline=False)

        # Rút gọn log nếu quá dài tránh tràn Discord embed
        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        # Cập nhật hoặc Kết thúc
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
        else:
            # Khóa và Xóa nút
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.btn_c.disabled = True
            self.btn_d.disabled = True
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
        
        # Kiểm tra xem người bấm có phải là 1 trong 2 người chơi không
        if user_id not in self.choices:
            embed_err = discord.Embed(
                description="⚠️ Tránh ra chỗ khác, đây là trận chiến vinh dự riêng tư của hai người họ!", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        # Kiểm tra xem người này đã ra chiêu chưa
        if self.choices[user_id] is not None:
            embed_err = discord.Embed(
                description="⚠️ Quân tử nhất ngôn! Bạn đã ra chiêu rồi, không được rút lại đâu!", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        # Ghi nhận lựa chọn
        self.choices[user_id] = choice
        embed_success = discord.Embed(
            description=f"🤫 Bạn đã giấu tay chọn **{choice}**. Hãy nín thở chờ đối thủ ra chiêu...", 
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=True)

        # Nếu cả 2 người đã chọn xong, tiến hành mở bát
        if self.choices[str(self.player_1.id)] is not None and self.choices[str(self.player_2.id)] is not None:
            # Khóa toàn bộ các nút bấm
            for child in self.children: 
                child.disabled = True
                
            choice_1 = self.choices[str(self.player_1.id)]
            choice_2 = self.choices[str(self.player_2.id)]
            
            p1_data = load_user(self.player_1.id)
            p2_data = load_user(self.player_2.id)
            
            tong_thuong = self.bet_amount * 2
            
            # Xử lý Logic thắng thua của Oẳn Tù Tì
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
                
            # Lưu dữ liệu lên Database
            save_user(self.player_1.id)
            save_user(self.player_2.id)
            
            # Cập nhật tin nhắn công khai hiển thị kết quả
            embed_result = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed_result.add_field(name=self.player_1.name, value=f"Ra {choice_1}", inline=True)
            embed_result.add_field(name="VS", value="⚡", inline=True)
            embed_result.add_field(name=self.player_2.name, value=f"Ra {choice_2}", inline=True)
            embed_result.add_field(name="KẾT QUẢ CUỐI CÙNG", value=ket_qua, inline=False)
            
            await self.msg.edit(embed=embed_result, view=self)
            self.stop()

    async def on_timeout(self):
        """Nếu hết 60s mà có người không chịu ra chiêu, tự động hủy kèo hoàn tiền"""
        if self.choices[str(self.player_1.id)] is None or self.choices[str(self.player_2.id)] is None:
            p1_data = load_user(self.player_1.id)
            p2_data = load_user(self.player_2.id)
            
            # Hoàn trả tiền
            p1_data["money"] += self.bet_amount
            p2_data["money"] += self.bet_amount
            
            save_user(self.player_1.id)
            save_user(self.player_2.id)
            
            embed_timeout = discord.Embed(
                title="⏳ HẾT GIỜ KHIẾP SỢ", 
                description="Có người nhát gan không dám ra chiêu. Trận đấu bị hủy, tiền cược đã hoàn trả!", 
                color=discord.Color.dark_gray()
            )
            try: 
                await self.msg.edit(embed=embed_timeout, view=None)
            except Exception: 
                pass

class SoloOTTAccept(discord.ui.View):
    """Bảng hiển thị lời thách đấu và nút Nhận Kèo"""
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1
        self.player_2 = player_2
        self.bet_amount = bet_amount

    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Chặn người ngoài bấm nhận kèo
        if interaction.user.id != self.player_2.id:
            embed_err = discord.Embed(description="⚠️ Kèo này gạ người khác, ông chui vào đây bấm làm gì!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        p1_data = load_user(self.player_1.id)
        p2_data = load_user(self.player_2.id)
        
        # Kiểm tra tiền lần 2 phòng trường hợp trong 60s chờ có người lỡ tiêu hết tiền
        if p1_data.get("money", 0) < self.bet_amount or p2_data.get("money", 0) < self.bet_amount:
            embed_err = discord.Embed(description="⚠️ Lỗi! Một trong hai người đã tiêu cạn tiền trong ví, không đủ lúa để chơi ván này nữa!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        # Trừ tiền cả 2 để đưa vào "bàn cược"
        p1_data["money"] -= self.bet_amount
        p2_data["money"] -= self.bet_amount
        save_user(self.player_1.id)
        save_user(self.player_2.id)

        # Chuyển sang View 3 nút Oẳn Tù Tì
        game_view = SoloOTTGame(self.player_1, self.player_2, self.bet_amount)
        embed_game = discord.Embed(
            title="⚔️ PK OẲN TÙ TÌ", 
            description=f"{self.player_1.mention} 🆚 {self.player_2.mention}\nTiền cược của mỗi bên: **{self.bet_amount:,} 💰**\n\n👇 **HÃY BẤM NÚT ĐỂ CHỌN CHIÊU (Lựa chọn của bạn sẽ bị giấu kín)**", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed_game, view=game_view)
        
        # Truyền object message vào view để cập nhật khi xong
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
        
        # Kiểm tra xem chú rể còn đủ tiền mua nhẫn không (1 triệu)
        if sender_data.get("money", 0) < 1000000: 
            embed_err = discord.Embed(description=f"⚠️ Ôi không! {self.sender.name} đã lỡ tiêu hết tiền, không đủ 1 Triệu sắm Lễ Cưới nữa rồi!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        # Trừ 1 triệu tiền cưới, set trạng thái cho cả hai
        sender_data["money"] -= 1000000
        sender_data["spouse"] = str(self.receiver.id)
        receiver_data["spouse"] = str(self.sender.id)
        
        save_user(self.sender.id)
        save_user(self.receiver.id)
        
        # Khóa nút
        for child in self.children: 
            child.disabled = True
            
        embed_success = discord.Embed(
            title="💒 KẾT HÔN THÀNH CÔNG", 
            description=f"🎉 Pháo hoa nổ rợp trời! Xin chúc mừng hai vợ chồng {self.sender.mention} và {self.receiver.mention}!\nTừ nay các bạn đã là của nhau. Trăm năm hạnh phúc, rước dâu bằng Mẹc G63 nhé!", 
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
        
        # Kiểm tra xem người này có lén gia nhập cty khác lúc chờ chưa
        if target_data.get("company"): 
            embed_err = discord.Embed(description="⚠️ Bạn đã thuộc về một công ty rồi, phải thoát trước khi gia nhập chỗ mới!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        comp = load_company(self.comp_id)
        if not comp: 
            embed_err = discord.Embed(description="⚠️ Công ty này đã tuyên bố phá sản hoặc không còn tồn tại trên hệ thống!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        
        # Thêm người này vào danh sách nhân viên
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
            
        embed_fail = discord.Embed(
            description=f"❌ {self.target_user.mention} đã xé bỏ hợp đồng, chê thẳng thừng lời mời của **{self.comp_name}**.", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(content=None, embed=embed_fail, view=None)
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
    
    # Thêm ảnh GIF cho sống động
    embed.set_thumbnail(url=GIF_LINKS["bank"])
    
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
    
    # Xóa thông tin spouse của cả hai
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
        # Xử lý rác dữ liệu: Cty bị sập nhưng user vẫn dính ID
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
        "last_interest": "2000-01-01 00:00:00"
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
    
    # Xóa khỏi danh sách và clear data
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
    await ctx.send(embed=embed_salary)

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
        # Chủ tịch rời đi -> Xóa hoàn toàn công ty
        COMPANY_CACHE.pop(comp_id, None)
        companies_col.delete_one({"_id": comp_id})
        
        # Xóa nhân viên khỏi công ty
        for m_id in list(comp["members"].keys()):
            m_data = load_user(m_id)
            m_data["company"] = None
            save_user(m_id)
            
        embed_bankrupt = discord.Embed(
            description="🏢 Bão tố ập tới! Chủ tịch đã bỏ trốn, công ty tuyên bố **PHÁ SẢN** và giải tán toàn bộ nhân sự!", 
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
    else:
        # Nhân viên rời đi
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
        
        # Thêm GIF đập lộn
        embed_help.set_image(url=GIF_LINKS["fight"])
        
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
        win_embed.set_image(url=GIF_LINKS["fight"])
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
# HỆ THỐNG SÀN CHỨNG KHOÁN (CẬP NHẬT THEO GIỜ THỰC TẾ)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    """Bảng hiển thị giá trị cổ phiếu trên thị trường chứng khoán phố Wall"""
    next_timestamp = get_next_hour_timestamp()
    
    embed = discord.Embed(
        title="📈 SÀN CHỨNG KHOÁN PHỐ WALL", 
        description=f"Thị trường sẽ đóng phiên và cập nhật giá mới vào: <t:{next_timestamp}:R>\n\n"
                    f"🛒 Lệnh Mua: `k ck buy <MÃ> <Số lượng>`\n"
                    f"💸 Lệnh Bán: `k ck sell <MÃ> <Số lượng>`", 
        color=discord.Color.blue()
    )
    
    # Liệt kê các mã cổ phiếu và giá hiện tại
    for code, name in STOCKS.items():
        price_now = get_stock_price(code, 0)
        price_old = get_stock_price(code, -1)
        
        if price_now > price_old:
            trend = "🟩 Đang Lên"
        else:
            trend = "🟥 Đang Xuống"
            
        difference = abs(price_now - price_old)
        
        embed.add_field(
            name=f"🏢 {code} - {name}", 
            value=f"Giá niêm yết: **{price_now:,} 💰**\n*(Biến động so với giờ trước: {trend} {difference:,})*", 
            inline=False
        )
        
    # Lấy dữ liệu túi đồ của người chơi
    user_data = load_user(ctx.author.id)
    my_stocks = user_data.get("stocks", {})
    
    inventory_str = ""
    for code, quantity in my_stocks.items():
        if quantity > 0:
            inventory_str += f"🔸 {code}: {quantity} cổ phiếu\n"
            
    if not inventory_str:
        inventory_str = "Ví đầu tư của bạn đang trống trơn."
        
    embed.add_field(name="🎒 Cổ phiếu bạn đang nắm giữ", value=inventory_str, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    """Lệnh mua cổ phiếu"""
    code = code.upper()
    
    if code not in STOCKS:
        embed_err = discord.Embed(description="⚠️ Mã cổ phiếu này không tồn tại trên sàn giao dịch!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if qty <= 0: 
        embed_err = discord.Embed(description="⚠️ Số lượng mua phải lớn hơn 0!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    total_cost = get_stock_price(code, 0) * qty
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) < total_cost: 
        embed_err = discord.Embed(description=f"⚠️ Thiếu lúa rồi đại gia ơi! Bạn cần tới **{total_cost:,} 💰** để mua khớp lệnh.", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data["money"] -= total_cost
    
    # Thêm cổ phiếu vào túi đồ
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
    
    if code not in STOCKS:
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
# HỆ THỐNG MINIGAME NHẬP VAI: CƯỚP BANK, ĐÀO VÀNG, VIETLOTT
# =====================================================================
@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    """Lệnh cướp ngân hàng - Liều ăn nhiều, thua thì đi tù"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("money", 0) < 50000: 
        embed_err = discord.Embed(description="⚠️ Bạn cần phải có tối thiểu **50,000 💰** trong ví để làm vốn mua súng M4A1 mới đi cướp được!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
    
    # Cooldown 1 tiếng để tránh spam cướp liên tục
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
    
    # Tỉ lệ 20% thành công
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
        # THÊM ẢNH GIF CƯỚP BANK THÀNH CÔNG
        embed_win.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed_win)
    else: 
        # 80% thất bại, mất vốn và vào tù
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
        # THÊM ẢNH GIF ĐI TÙ
        embed_lose.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed_lose)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    """Nghề thợ mỏ đào vàng"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    # Cooldown 30s chống spam
    if user_id in work_cooldowns:
        time_diff = (now - work_cooldowns[user_id]).total_seconds()
        if time_diff < 30:
            time_left = int(30 - time_diff)
            embed_err = discord.Embed(description=f"⏳ Tay mỏi nhừ rồi sếp! Nghỉ {time_left}s nữa hẵng cuốc tiếp.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)
    
    # Kiểm tra xem có Cuốc chim trong túi không
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
        # 2% đạp mìn nổ tung chết
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
    # THÊM ẢNH GIF ĐÀO MỎ
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
# HỆ THỐNG CASINO VIP CÓ TÍNH NĂNG REPLY TRỰC TIẾP (DỄ NHÌN HƠN)
# =====================================================================
@bot.command()
async def coin(ctx, amount: str):
    """Lệnh tung đồng xu"""
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
    # THÊM GIF CASINO
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
    """Lệnh lắc tài xỉu 3 xí ngầu"""
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
    
    # Tung 3 xúc xắc
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    d3 = random.randint(1, 6)
    total_score = d1 + d2 + d3
    
    # Logic tài xỉu (Dưới 10 là xỉu, trên 10 là tài)
    result_type = "xiu" if total_score <= 10 else "tai"
    
    result_embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    choice_clean = choice.replace("à", "a").replace("ỉ", "i")
    
    if choice_clean == result_type: 
        # Nếu nổ bão (3 mặt giống nhau) thì x5
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
    """Lệnh lắc bầu cua tôm cá"""
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
    
    # Tung 3 cục xí ngầu bầu cua
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
    """Minigame Đua thú bằng Animation text"""
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
        """Hàm sinh ra khung hình đường đua tại thời điểm hiện tại"""
        frame_text = f"🏇 **ĐƯỜNG ĐUA THÚ MỞ BÁT!**\nBạn cược {bet_amount:,} 💰 vào con {animals[choice]}\n\n"
        for pet, distance in positions.items():
            run_distance = min(distance, track_length)
            space_distance = track_length - run_distance
            frame_text += f"🏁{'~' * run_distance}{pet}{' ' * space_distance}⛩️\n"
        return frame_text

    msg = await ctx.reply(generate_track_frame(), mention_author=False)
    winner = None
    
    # Chạy vòng lặp animation 4 khung hình
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in positions:
            positions[pet] += random.randint(2, 6) 
            # Ai chạm đích trước thì thắng
            if positions[pet] >= track_length and winner is None: 
                winner = pet
                
        await msg.edit(content=generate_track_frame())
        if winner: break
        
    # Nếu sau 4 lượt chưa ai tới đích, ép con chạy xa nhất làm winner
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
    # Chọn trước kết quả
    slots_result = [random.choice(items) for _ in range(3)]
    
    embed = discord.Embed(title="🎰 MÁY XÈNG NỔ HŨ 🎰", color=discord.Color.gold())
    embed.set_thumbnail(url=GIF_LINKS["casino"])
    
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    # Hiệu ứng quay tít
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
        
    # Tính toán thắng thua
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
    """Lệnh mở trứng thú cưng (Gacha)"""
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
    
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(1.5)
    
    embed_start.description = "⚡ Vỏ trứng nứt rạn... Một ánh sáng chói lóa phát ra..."
    await msg.edit(embed=embed_start)
    await asyncio.sleep(1.5)
    
    # Tính toán tỉ lệ Gacha
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
    
    # Thêm pet vào túi đồ
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
# HỆ THỐNG LỆNH ADMIN (QUẢN TRỊ VIÊN) VÀ BƠM TIỀN
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
# HỆ THỐNG LỆNH CƠ BẢN, NHÂN SINH, TOP VÀ CÀY CUỐC
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
    
    # Đổi màu thẻ nếu là đại gia
    embed_color = discord.Color.gold() if tien > 1000000 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 CĂN CƯỚC CÔNG DÂN: {ctx.author.name.upper()}", color=embed_color)
    
    # Gắn GIF ngầu lòi cho thẻ rank
    embed.set_thumbnail(url=GIF_LINKS["rank"])
    
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {level}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    
    # Kiểm tra tình trạng kết hôn
    if user_data.get("spouse"):
        try:
            spouse_user = await bot.fetch_user(int(user_data["spouse"]))
            spouse_name = spouse_user.name
        except Exception: 
            spouse_name = "Người thương ẩn danh"
        embed.add_field(name="💍 Tình Trạng Hôn Nhân", value=f"**Đã kết hôn với {spouse_name}**", inline=False)
        
    # Kiểm tra tình trạng Công ty
    if user_data.get("company"): 
        comp_info = load_company(user_data['company'])
        if comp_info:
            embed.add_field(name="🏢 Doanh Nghiệp", value=f"**{comp_info['name']}**", inline=False)
            
    # Hiển thị án phạt tù
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
    """Bảng xếp hạng tổng tài sản (Ví + Ngân hàng) của toàn bộ Server"""
    all_users = list(users_col.find())
    
    # Tính tổng tiền ví + tiền ngân hàng để đua TOP công bằng
    danh_sach = sorted(
        [(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], 
        key=lambda x: x[1], 
        reverse=True
    )
    
    desc = ""
    for index, (uid, tien) in enumerate(danh_sach[:10]):
        user = bot.get_user(int(uid))
        try: 
            if not user: 
                user = await bot.fetch_user(int(uid))
        except Exception: 
            pass
            
        ten = user.name if user else f"Tỷ phú ẩn danh {uid[-4:]}"
        icon = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else f"**#{index+1}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
        
    embed = discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA SERVER", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    """Điểm danh nhận quà mỗi ngày (Có đếm ngược)"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("last_daily"):
        last_daily = datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            next_time = int((last_daily + timedelta(days=1)).timestamp())
            embed_err = discord.Embed(description=f"⏳ Khôn như bạn quê mình đầy! Lương điểm danh tiếp theo nhận vào: <t:{next_time}:R>.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)
    
    user_data["money"] += 1000
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed_success = discord.Embed(
        title="🎁 QUÀ ĐIỂM DANH MỖI NGÀY", 
        description=f"Nhận trợ cấp **1,000 💰** thành công!\n💳 Số dư ví hiện tại: **{user_data['money']:,} 💰**", 
        color=discord.Color.green()
    )
    embed_success.set_thumbnail(url=GIF_LINKS["daily"])
    await ctx.reply(embed=embed_success, mention_author=False)

@bot.command()
async def lixi(ctx):
    """Bốc lì xì ngẫu nhiên (12 tiếng / 1 lần)"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("last_lixi"):
        last_lixi = datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S")
        if now - last_lixi < timedelta(hours=12):
            next_time = int((last_lixi + timedelta(hours=12)).timestamp())
            embed_err = discord.Embed(description=f"🧧 Bạn đã bốc rồi! Bao lì xì tiếp theo phát vào: <t:{next_time}:R>.", color=discord.Color.orange())
            return await ctx.reply(embed=embed_err, mention_author=False)

    tien = random.randint(1000, 8000) 
    user_data["money"] += tien
    user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"🧧 Bạn vui vẻ mở phong bao đỏ và nhận được **{tien:,} 💰**!\n💳 Số dư ví: **{user_data['money']:,} 💰**", 
        color=discord.Color.red()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    """Chuyển tiền cho người chơi khác"""
    nguoi_gui = str(ctx.author.id)
    nguoi_nhan = str(member.id)
    
    gui_data = load_user(nguoi_gui)
    nhan_data = load_user(nguoi_nhan)
    
    if amount <= 0 or gui_data.get("money", 0) < amount or nguoi_gui == nguoi_nhan: 
        embed_err = discord.Embed(description="⚠️ Giao dịch thất bại! (Tiền âm, không đủ tiền trong ví hoặc tự chuyển cho chính mình).", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    gui_data["money"] -= amount
    nhan_data["money"] += amount
    save_user(nguoi_gui)
    save_user(nguoi_nhan)
    
    embed_success = discord.Embed(
        title="💸 CHUYỂN KHOẢN THÀNH CÔNG", 
        description=f"{ctx.author.mention} đã chuyển khoản nóng cho {member.mention} **{amount:,} 💰**!", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed_success)

@bot.command(aliases=['ban', 'sell'])
async def choden(ctx): 
    """Gọi giao diện Chợ Đen để bán đồ"""
    embed = discord.Embed(
        title="⚖️ CHỢ ĐEN CẦM ĐỒ", 
        description="Đem đồ ra đây cầm cố hoặc bán thú cưng lấy tiền liền tay!", 
        color=discord.Color.dark_orange()
    )
    if bot.user.avatar: 
        embed.set_thumbnail(url=bot.user.avatar.url)
        
    await ctx.send(embed=embed, view=SellCategoryMenu(ctx.author))

@bot.command(aliases=['shop'])
async def cuahang(ctx): 
    """Gọi giao diện Cửa hàng Đại gia"""
    embed = discord.Embed(
        title="🏪 ĐẠI SIÊU THỊ TRUNG TÂM", 
        description="Nơi tiêu tiền của những kẻ giàu có! Bán tất cả mọi thứ từ xe đạp đến Phi thuyền không gian!", 
        color=discord.Color.brand_green()
    )
    if bot.user.avatar: 
        embed.set_thumbnail(url=bot.user.avatar.url)
        
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
                description=f"Bạn đã hoàn thành chuyến dã ngoại, mang chiến lợi phẩm về và thu hoạch được **{reward:,} 💰**!", 
                color=discord.Color.gold()
            )
            return await ctx.reply(embed=embed_success, mention_author=False)
        else:
            time_left = end_time - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed_wait = discord.Embed(
                description=f"⏳ Đang cày cuốc sấp mặt ở nơi hoang dã! Hãy kiên nhẫn chờ thêm **{hours} giờ {minutes} phút** nữa để nhân vật trở về nhé.", 
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

    # Khởi tạo điểm may mắn ngẫu nhiên cho kiếp này
    initial_stats = {"may_man": random.randint(1, 10)}
    view = NhanSinhGameView(ctx.author, initial_stats)
    
    embed = discord.Embed(
        title="🌀 MÔ PHỎNG NHÂN SINH", 
        description=f"Ký chủ luân hồi: {ctx.author.mention}", 
        color=discord.Color.teal()
    )
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{initial_stats['may_man']}/10** *(Được buff thêm {initial_stats['may_man']*2}% Tỉ lệ thành công cho mọi quyết định)*", inline=False)
    embed.add_field(name="📜 Hành trình cuộc đời", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Ngã rẽ quyết định tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    
    await ctx.reply(embed=embed, view=view, mention_author=False)
# =====================================================================
# SỰ KIỆN LÕI CỦA BOT (ON_MESSAGE, ON_READY)
# =====================================================================
@bot.event
async def on_message(message):
    """
    Sự kiện đọc tin nhắn:
    - Xử lý hệ thống kinh nghiệm (XP) cho người dùng chat
    - Không cấp XP cho người đang đi tù
    """
    # Bỏ qua tin nhắn của các Bot khác
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
    print('>>> BẢN CẬP NHẬT VIP 2026 - FULL TÍNH NĂNG VÀ GIF')
    print('================================================')
    
    # Thiết lập hoạt động hiển thị của Bot trên Discord
    await bot.change_presence(activity=discord.Game(name="Quản lý Sòng Bạc & Kinh Tế | k help"))

# =====================================================================
# KHỞI ĐỘNG SERVER 24/7 VÀ CHẠY BOT BẰNG TOKEN
# =====================================================================
# Kích hoạt máy chủ web giả để Render/UptimeRobot ping giữ cho Bot online 24/7
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
