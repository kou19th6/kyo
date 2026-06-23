import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 

# Thiết lập cơ bản của Bot
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

# Khởi tạo Cache để giảm tải cho DB
DB_CACHE = {}
CONFIG_CACHE = {}
COMPANY_CACHE = {}

def load_user(user_id):
    """Tải dữ liệu người dùng từ Database và khởi tạo các trường mặc định nếu thiếu"""
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
        "title": "Dân Đáy Xã Hội 🧱", 
        "assets": [], 
        "pets": {}, 
        "company": None, 
        "stocks": {}, 
        "jail_time": None
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
    """Lưu dữ liệu Công ty"""
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
                description=f"{ctx.author.mention} đang bóc lịch trong trại giam!\n\n"
                            f"⏳ Mãn hạn tù: <t:{int(jail_end.timestamp())}:R>\n\n"
                            f"Hãy tự vấn lương tâm rồi quay lại sau nhé!", 
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return False
        else:
            user_data["jail_time"] = None
            save_user(ctx.author.id)
            
    # Kiểm tra chặn kênh
    config = load_server_config(ctx.guild.id) if ctx.guild else {}
    allowed_channels = config.get("allowed_channels", [])
    if allowed_channels and ctx.channel.id not in allowed_channels: 
        return False
        
    return True

def make_progress_bar(current, total, length=12):
    """Tạo thanh tiến trình hiển thị kinh nghiệm"""
    progress = int((current / total) * length)
    return "🟩" * progress + "⬛" * (length - progress)

async def check_gamble_conditions(ctx, amount_str):
    """Kiểm tra điều kiện cờ bạc (Tiền âm, Mức cược, Cooldown)"""
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    # Check cooldown mỏi tay
    if user_id in gamble_cooldowns and (now - gamble_cooldowns[user_id]).total_seconds() < 4:
        time_left = int(4 - (now - gamble_cooldowns[user_id]).total_seconds())
        embed = discord.Embed(
            description=f"⏳ Tay mỏi rồi! Đợi {time_left}s nữa hẵng lắc tiếp sếp ơi!", 
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return None, None
        
    user_data = load_user(user_id)
    
    # Check nợ nần
    if user_data.get("money", 0) <= 0:
        embed = discord.Embed(
            description="💸 Kẻ tổn thương lại muốn tổn thương sòng bạc à? Tiền không có mà đòi cá cược!", 
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return None, None
        
    # Check lệnh all in
    try: 
        if amount_str.lower() == "all":
            bet = user_data["money"]
        else:
            bet = int(amount_str)
    except: 
        embed = discord.Embed(description="⚠️ Nhập số tiền sai rồi!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return None, None
        
    # Check tiền trong ví
    if bet <= 0 or bet > user_data["money"]: 
        embed = discord.Embed(
            description=f"⚠️ Bốc phét à? Sếp chỉ có **{user_data['money']:,} 💰** thôi!", 
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return None, None
        
    # Check max cược 500k
    if bet > 500000: 
        embed = discord.Embed(
            description="🛑 Nhà cái quy định max cược là **500,000 💰** thôi!", 
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return None, None
        
    return user_data, bet

# =====================================================================
# DATA CỬA HÀNG VÀ TÀI SẢN (BUNG LỤA HOÀN TOÀN)
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

STOCKS = {
    "VIN": "Tập Đoàn VIN", 
    "FLC": "Hàng Không FLC", 
    "VNZ": "Công Nghệ VNZ", 
    "DOGE": "Doge Coin", 
    "BTC": "Bitcoin", 
    "AAPL": "Apple Inc.", 
    "TSLA": "Tesla"
}

# =====================================================================
# DATA NHÂN SINH (CÁC SỰ KIỆN CUỘC ĐỜI)
# =====================================================================
EVENTS_P1 = [
    {
        "q": "Tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", 
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
    }
]

EVENTS_P2 = [
    {
        "q": "Tích cóp được chút vốn, bạn muốn làm giàu nhanh.", 
        "choices": [
            {
                "text": "Bắt đáy chứng khoán", 
                "rate": 30, 
                "win": "Cổ phiếu tím lịm! Tiền lãi mua được cả căn nhà.", 
                "lose": "Bị chủ tịch úp bô, cổ phiếu rác hủy niêm yết.", 
                "tien_w": 15000, 
                "tien_l": -25000
            }, 
            {
                "text": "Cắm sổ đỏ đánh xóc đĩa", 
                "rate": 5, 
                "win": "Ăn thông 10 ván! Bạn mua hẳn siêu xe Mẹc-xê-đét.", 
                "lose": "Cháy túi, nhảy cầu kết thúc cuộc đời.", 
                "tien_w": 80000, 
                "tien_l": -50000, 
                "die_l": True
            }, 
            {
                "text": "Khởi nghiệp bún đậu mắm tôm", 
                "rate": 60, 
                "win": "Đông khách nườm nượp, mở 5 chi nhánh.", 
                "lose": "Bị phốt mắm tôm có giòi, sập tiệm đền tiền.", 
                "tien_w": 12000, 
                "tien_l": -8000
            }, 
            {
                "text": "Gửi tiết kiệm ngân hàng", 
                "rate": 95, 
                "win": "Cuộc sống bình yên, có lãi ra tiêu vặt.", 
                "lose": "Lạm phát phi mã, tiền bốc hơi từ từ.", 
                "tien_w": 2000, 
                "tien_l": -1500
            }
        ]
    }
]

EVENTS_P3 = [
    {
        "q": "Bất Động Sản đang sốt, cò đất rủ bạn lướt sóng phân lô bán nền.", 
        "choices": [
            {
                "text": "Cầm nhà ngân hàng quất liền", 
                "rate": 20, 
                "win": "Giá đất x5 trong một đêm! Bạn thành đại gia nghìn tỷ.", 
                "lose": "Dính bẫy lừa đảo dự án ma, ra đê ở, treo cổ tự tử.", 
                "tien_w": 60000, 
                "tien_l": -70000, 
                "die_l": True
            }, 
            {
                "text": "Mua miếng đất nhỏ vùng ven", 
                "rate": 55, 
                "win": "Chính phủ mở đường qua, đất nhân 3 giá trị.", 
                "lose": "Đất dính quy hoạch mỏ đá, bán không ai mua.", 
                "tien_w": 15000, 
                "tien_l": -10000
            }, 
            {
                "text": "Mở lớp dạy làm giàu từ BĐS", 
                "rate": 40, 
                "win": "Lùa được đàn gà đông đảo, thu học phí ngập mồm.", 
                "lose": "Bị học viên bóc phốt úp sọt, đánh nhập viện.", 
                "tien_w": 12000, 
                "tien_l": -15000
            }, 
            {
                "text": "Không quan tâm, lo giữ gia đình", 
                "rate": 95, 
                "win": "Nhà cửa êm ấm, vợ/chồng con cái hạnh phúc.", 
                "lose": "Kinh tế khó khăn, đôi lúc cãi nhau vì tiền điện nước.", 
                "tien_w": 3000, 
                "tien_l": -1500
            }
        ]
    }
]

EVENTS_P4 = [
    {
        "q": "Bước vào tuổi 50, bạn rơi vào khủng hoảng tuổi trung niên trầm trọng.", 
        "choices": [
            {
                "text": "Bán nhà mua siêu xe Mẹc G63", 
                "rate": 15, 
                "win": "Chiến thắng giải đua không chuyên, nổi đình đám ăn quảng cáo.", 
                "lose": "Đạp nhầm chân ga tông xe tải, thăng thiên tại chỗ.", 
                "tien_w": 35000, 
                "tien_l": -40000, 
                "die_l": True
            }, 
            {
                "text": "Sưu tầm Lan Đột Biến", 
                "rate": 35, 
                "win": "Bán chậu lan giá trên trời cho tỷ phú.", 
                "lose": "Thị trường sập, ôm nhánh cỏ khô lỗ chổng vó.", 
                "tien_w": 25000, 
                "tien_l": -20000
            }, 
            {
                "text": "Cặp Sugar Baby cho hồi xuân", 
                "rate": 25, 
                "win": "Nuôi êm thấm, tâm hồn trẻ lại phơi phới.", 
                "lose": "Bị vợ/chồng bắt ghen tung lên mạng, mất sạch tài sản.", 
                "tien_w": 2000, 
                "tien_l": -50000
            }, 
            {
                "text": "Tập Thiền, dọn về quê nuôi cá", 
                "rate": 90, 
                "win": "Tâm hồn thanh tịnh, khí huyết lưu thông.", 
                "lose": "Về quê bị muỗi vằn chích sốt xuất huyết.", 
                "tien_w": 5000, 
                "tien_l": -3000
            }
        ]
    }
]

EVENTS_P5 = [
    {
        "q": "Chạm mốc 70 tuổi, một nhà sư bảo bạn sắp tới số.", 
        "choices": [
            {
                "text": "Vung tiền mua Linh Đan Tu Tiên", 
                "rate": 5, 
                "win": "Kỳ tích! Bạn cải lão hoàn đồng thành thanh niên 20 tuổi!", 
                "lose": "Uống nhầm thủy ngân, nội tạng nát vụn thăng thiên sớm.", 
                "tien_w": 200000, 
                "tien_l": -20000, 
                "die_l": True
            }, 
            {
                "text": "Lập di chúc chia đều tài sản", 
                "rate": 75, 
                "win": "Con cháu hòa thuận, tổ chức mừng thọ linh đình.", 
                "lose": "Con cháu chê ít, đánh nhau mẻ đầu, bạn tức quá đột tử.", 
                "tien_w": 5000, 
                "tien_l": -15000, 
                "die_l": True
            }, 
            {
                "text": "Quyên góp 100% làm từ thiện", 
                "rate": 90, 
                "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", 
                "lose": "Tổ chức từ thiện cuỗm tiền bốc hơi, bạn trầm cảm đi luôn.", 
                "tien_w": 15000, 
                "tien_l": -50000, 
                "die_l": True
            }, 
            {
                "text": "Lên Las Vegas đánh Casino lần cuối", 
                "rate": 20, 
                "win": "Thắng Jackpot 50 triệu đô! Lên báo quốc tế rình rang.", 
                "lose": "Thua sạch bong, lên cơn nhồi máu cơ tim gục tại bàn.", 
                "tien_w": 100000, 
                "tien_l": -40000, 
                "die_l": True
            }
        ]
    }
]

# =====================================================================
# DATA KHU RỪNG THÁM HIỂM
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
        {"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!**\nBạn chọc tức chúa tể rừng xanh. Bị đấm bay xa 10km, rớt sạch đồ đạc!"},
        {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền!"},
        {"mult": -1.3, "msg": "🕳️ **SỤP HỐ CHÔNG!**\nRơi thẳng xuống hố chông của thợ săn. Gãy 2 cái sườn, nôn hết tiền mặt ra."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước hết hạn từ máy bán hàng tự động trong rừng. Đau bụng tốn tiền viện phí."},
        {"mult": -0.8, "msg": "💩 **TRƯỢT CHÂN VÀO BÃI MÌN!**\nBạn dẫm trúng bãi mìn khổng lồ của voi rừng. Tốn tiền mua bộ đồ mới."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"mult": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được cây nấm linh chi đỏ rực. Tiệm thuốc trả cho bạn một khoản hời."}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp và tịch thu kho báu của chúng!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nPhát hiện ra một rương kho báu vàng chóe bị chôn vùi. Mở ra toàn tiền!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng ĐẶC BIỆT!"},
        {"mult": 12.0, "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR! (ULTRAPOT)**\nDưới đáy đầm, bạn vớt được Vương miện nạm 100 viên kim cương. Bạn thành tỷ phú!!"}
    ]
}

# HÀM XỬ LÝ GIÁ TÀI SẢN
def get_asset_price(asset_name):
    """Tính giá bán lại tài sản vào chợ đen (Lỗ 30%)"""
    for item_data in SHOP_ITEMS.values():
        if item_data["name"] == asset_name: 
            return int(item_data["price"] * 0.7)
    return 1000

def get_pet_sell_price(pet_name):
    """Tính giá bán thú cưng theo độ hiếm"""
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 5000      
            if rarity == "rare": return 20000       
            if rarity == "epic": return 150000      
            if rarity == "legendary": return 800000 
            if rarity == "mythic": return 10000000   
    return 1000

def get_stock_price(stock_code, hour_offset=0):
    """Tính giá cổ phiếu thay đổi theo từng giờ thực tế"""
    target_time = datetime.now() + timedelta(hours=hour_offset)
    # Seed tạo ra sự ngẫu nhiên nhưng CỐ ĐỊNH trong cùng 1 khung giờ
    seed = int(target_time.strftime("%Y%m%d%H")) + sum(ord(c) for c in stock_code)
    rng = random.Random(seed)
    return rng.randint(5, 500) * 1000

def get_next_hour_timestamp():
    """Lấy Timestamp của khung giờ tiếp theo để đếm ngược"""
    next_hour = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int(next_hour.timestamp())
# =====================================================================
# GIAO DIỆN UI (MENU CỬA HÀNG VÀ CHỢ ĐEN)
# =====================================================================
class ShopItemSelect(discord.ui.Select):
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
        
        if user_data.get("money", 0) < item_info["price"]:
            embed_fail = discord.Embed(
                description=f"⚠️ Tiền trong ví không đủ! Bạn cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            msg = f"🎉 Chúc mừng! Bạn đã trang bị danh hiệu mới: **{item_info['name']}**."
        else:
            if item_info["name"] in user_data["assets"]:
                user_data["money"] += item_info["price"] 
                embed_exist = discord.Embed(
                    description=f"⚠️ Bạn đã sở hữu **{item_info['name']}** rồi, không cần mua nữa đâu đại gia!", 
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
            text=f"Số dư còn lại: {user_data['money']:,} 💰", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(
            title="🛍️ QUẦY BÁN DANH HIỆU", 
            description="Mua danh hiệu xịn để gắn lên Căn Cước.", 
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
        if interaction.user != self.author:
            await interaction.response.send_message("Ai gọi lệnh người đó mua nha!", ephemeral=True)
            return False
        return True

class SellItemSelect(discord.ui.Select):
    def __init__(self, items, is_pet=False):
        self.is_pet = is_pet
        options = []
        if is_pet:
            count = 0
            for pet, qty in list(items.items()):
                if count >= 25: break
                if qty > 0: 
                    options.append(discord.SelectOption(label=pet, description=f"Số lượng: {qty} | Giá bán: {get_pet_sell_price(pet):,} 💰", value=pet))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(label=asset, description=f"Thu mua: {get_asset_price(asset):,} 💰", value=asset))
                
        super().__init__(placeholder="Chọn món đồ đem đi cầm cố...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        val = self.values[0]
        
        if self.is_pet:
            if user_data.get("pets", {}).get(val, 0) <= 0: 
                return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng!", ephemeral=True)
            sell_price = get_pet_sell_price(val)
            user_data["pets"][val] -= 1
            if user_data["pets"][val] == 0: 
                del user_data["pets"][val]
            msg = f"✅ Thương lái đã mua lại **{val}**.\nBạn nhận được **{sell_price:,} 💰**!"
        else:
            if val not in user_data.get("assets", []): 
                return await interaction.response.send_message("Lỗi: Không tìm thấy tài sản!", ephemeral=True)
            sell_price = get_asset_price(val)
            user_data["assets"].remove(val)
            msg = f"✅ Chủ tiệm cầm đồ đã thâu tóm **{val}**.\nBạn vớt vát được **{sell_price:,} 💰**!"

        user_data["money"] += sell_price
        save_user(user_id)
        
        embed = discord.Embed(
            title="🤝 GIAO DỊCH HOÀN TẤT", 
            description=msg, 
            color=discord.Color.dark_orange()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Cắm Sổ Đỏ / Cầm Xe", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: 
            return await interaction.response.send_message(embed=discord.Embed(description="Bạn không có tài sản nào để bán!", color=discord.Color.red()), ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        embed = discord.Embed(
            title="🏷️ CẦM ĐỒ BĐS & XE CỘ", 
            description="Lưu ý: Bạn sẽ bị con buôn ép giá mất 30% giá trị gốc lúc mua.", 
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(v == 0 for v in pets.values()): 
            return await interaction.response.send_message(embed=discord.Embed(description="Bạn không có con Thú cưng nào để bán cả!", color=discord.Color.red()), ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        embed = discord.Embed(
            title="🏷️ TRẠM THU MUA THÚ CƯNG", 
            description="Thu mua thú cưng với giá cao, nhanh gọn lẹ.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author: 
            return False
        return True

# =====================================================================
# GIAO DIỆN UI (KHU RỪNG THÁM HIỂM)
# =====================================================================
class BushButton(discord.ui.Button):
    def __init__(self, label, custom_id):
        super().__init__(label=label, style=discord.ButtonStyle.success, custom_id=custom_id, emoji="🌲")

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        weapon_info = WEAPON_ODDS[view.weapon_val]
        
        # Khóa tất cả các nút để tránh spam
        for child in view.children: 
            child.disabled = True
            
        loading_embed = discord.Embed(
            description=f"🌲 {interaction.user.mention} đang cầm **{weapon_info['name']}** lén lút tiến vào lùm cây...", 
            color=discord.Color.dark_green()
        )
        await interaction.response.edit_message(embed=loading_embed, view=view)
        await asyncio.sleep(2)

        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        old_money = user_data.get("money", 0)

        # Tính toán kết quả
        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [
            weapon_info["terrible"], weapon_info["bad"], weapon_info["neutral"], 
            weapon_info["good"], weapon_info["great"], weapon_info["jackpot"]
        ]
        
        category = random.choices(choices, weights=weights, k=1)[0]
        scenario = random.choice(SCENARIOS[category])
        
        if "mult" in scenario:
            thuong_phat = int(weapon_info['price'] * scenario["mult"])
        else:
            thuong_phat = 0
            
        user_data["money"] += thuong_phat
        actual_change = user_data["money"] - old_money
        new_session_profit = view.session_profit + actual_change
        save_user(user_id)
        
        # Xây dựng bảng kết quả
        profit_text = f"LÃI +{new_session_profit:,} 💰" if new_session_profit > 0 else f"LỖ {new_session_profit:,} 💰" if new_session_profit < 0 else "HUỀ VỐN"
        embed_color = discord.Color.green() if thuong_phat > 0 else discord.Color.red() if thuong_phat < 0 else discord.Color.light_gray()
        
        res_embed = discord.Embed(
            title="MỞ LÙM CÂY TÌM ĐƯỢC...", 
            description=f"**{scenario['msg']}**", 
            color=embed_color
        )
        res_embed.add_field(name="Thu Hoạch / Thua Lỗ", value=f"**{thuong_phat:,} 💰**", inline=True)
        res_embed.add_field(name="Tổng Lợi Nhuận Chuyến Đi", value=f"**{profit_text}**", inline=True)
        res_embed.set_footer(text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", icon_url=interaction.user.display_avatar.url)
        
        res_view = ResultView(interaction.user, new_session_profit)
        msg = await interaction.original_response()
        await msg.edit(content=None, embed=res_embed, view=res_view)

class ResultView(discord.ui.View):
    def __init__(self, author, session_profit):
        super().__init__(timeout=120)
        self.author = author
        self.session_profit = session_profit
        
        btn_tiep = discord.ui.Button(label="Tiếp tục Khám Phá", style=discord.ButtonStyle.primary, emoji="🔄")
        btn_tiep.callback = self.continue_explore
        self.add_item(btn_tiep)
        
        btn_dung = discord.ui.Button(label="Về Nhà (Dừng lại)", style=discord.ButtonStyle.danger, emoji="🛑")
        btn_dung.callback = self.stop_explore
        self.add_item(btn_dung)

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user != self.author:
            await interaction.response.send_message("Của ai người nấy chơi nhé!", ephemeral=True)
            return False
        return True

    async def continue_explore(self, interaction: discord.Interaction):
        shop_embed = discord.Embed(
            title="🛒 TRẠM TIẾP TẾ THÁM HIỂM", 
            description="Nghỉ ngơi và chọn mua vũ khí mới để đi tiếp.\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA** 👇", 
            color=discord.Color.orange()
        )
        profit_str = f"Đang LÃI +{self.session_profit:,} 💰" if self.session_profit >= 0 else f"Đang LỖ {self.session_profit:,} 💰"
        shop_embed.set_footer(text=f"Kỷ lục chuyến đi hiện tại: {profit_str}")
        
        view = KhungRungShopView(self.author, self.session_profit)
        await interaction.response.edit_message(embed=shop_embed, view=view)

    async def stop_explore(self, interaction: discord.Interaction):
        for child in self.children: 
            child.disabled = True
            
        profit_text = f"LÃI +{self.session_profit:,} 💰" if self.session_profit > 0 else f"LỖ {self.session_profit:,} 💰" if self.session_profit < 0 else "HUỀ VỐN"
        end_embed = discord.Embed(
            title="🛑 KẾT THÚC CHUYẾN ĐI", 
            description=f"Tổng kết sau chuyến đi dài, bạn mang về: **{profit_text}**", 
            color=discord.Color.dark_grey()
        )
        await interaction.response.edit_message(embed=end_embed, view=self)

class BushView(discord.ui.View):
    def __init__(self, author, weapon_val, session_profit):
        super().__init__(timeout=60)
        self.author = author
        self.weapon_val = weapon_val
        self.session_profit = session_profit
        
        for i in range(5): 
            self.add_item(BushButton(label=f"Lùm Cây {i+1}", custom_id=f"bush_{i}"))

    async def interaction_check(self, interaction: discord.Interaction): 
        return interaction.user == self.author

class WeaponSelect(discord.ui.Select):
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = []
        for key, item in WEAPON_ODDS.items():
            options.append(
                discord.SelectOption(
                    label=item['name'], 
                    description=f"Giá: {item['price']:,} 💰", 
                    value=key
                )
            )
        super().__init__(placeholder="Nhấn để chọn vũ khí muốn mua...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        weapon_id = self.values[0]
        price = WEAPON_ODDS[weapon_id]["price"]
        
        if user_data.get("money", 0) < price:
            embed = discord.Embed(
                description=f"⚠️ Nghèo quá! Bạn không đủ **{price:,} 💰** để mua vũ khí này!", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        user_data["money"] -= price
        save_user(user_id)
        
        embed = discord.Embed(
            title="🌲 RỪNG SÂU NƯỚC ĐỘC 🌲", 
            description=f"Bạn đang trang bị **{WEAPON_ODDS[weapon_id]['name']}**.\nPhía trước mặt có 5 lùm cây khả nghi. Hãy chọn 1 lùm!", 
            color=discord.Color.dark_green()
        )
        
        view = BushView(interaction.user, weapon_id, self.session_profit - price)
        await interaction.response.edit_message(embed=embed, view=view)

class KhungRungShopView(discord.ui.View):
    def __init__(self, author, session_profit=0):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(WeaponSelect(session_profit))

    async def interaction_check(self, interaction: discord.Interaction): 
        return interaction.user == self.author
        # =====================================================================
# GIAO DIỆN UI (TRẠM AFK, NHÂN SINH, PVP SOLO)
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
        if hours == 4: reward = random.randint(300, 600)
        elif hours == 8: reward = random.randint(700, 1200)
        else: reward = random.randint(1500, 2500)
        
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

        # Mở bài
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
        if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

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
        log_entry = f"🎲 Tỉ lệ: **{final_rate}%** (Đổ ra: {roll})\n{kq_thung}: {res} ({tien} 💰)"
        
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

        # Rút gọn log nếu quá dài
        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        # Chuyển Phase
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
# LỆNH HỆ THỐNG CƠ BẢN
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH CỦA BOT VIP", description="Tiền tố lệnh là `k` hoặc `K`.", color=discord.Color.blurple())
    if bot.user.avatar: 
        embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(name="🏢 THƯƠNG TRƯỜNG & CHỨNG KHOÁN", value="`k cty tao <tên>` • Lập công ty (500k)\n`k cty` • Mở Quản lý Công ty\n`k daichien @user <hack/phot/giangho>` • Tấn công Cty khác\n`k ck` • Sàn chứng khoán biến động theo giờ", inline=False)
    embed.add_field(name="💳 KINH TẾ & TÀI SẢN", value="`k rank` • Thẻ Căn Cước\n`k cuahang` • TTTM Bán nhà, bán xe\n`k ban` • Cầm đồ khét lẹt\n`k cuopnganhang` • Vào tù ra tội\n`k tuido` • Xem đồ đạc\n`k daily`, `k lixi` • Điểm danh", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu\n`k duathu <heo/cho/ngua/chuot> <tiền>`\n`k baucua <con vật> <tiền>` • Bầu cua\n`k nohu <tiền>` • Quay xèng Jackpot\n`k soloott @user <tiền>` • PK Solo Oẳn Tù Tì", inline=False)
    embed.add_field(name="⛏️ NHẬP VAI CÀY CUỐC", value="`k gacha` • Đập trứng thú cưng (30k)\n`k daovang` • Nghề thợ mỏ\n`k thamhiem` • Đi rừng lụm rác\n`k nhansinh` • Mô phỏng cuộc sống\n`k phai` • Treo máy AFK", inline=False)
    
    embed.set_footer(text="Chúc các dân chơi sớm tậu được Hành Tinh Namek!", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def rank(ctx):
    user_data = load_user(ctx.author.id)
    lv = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    tien = user_data.get("money", 0)
    
    embed = discord.Embed(title=f"💳 CĂN CƯỚC CÔNG DÂN: {ctx.author.name}", color=discord.Color.gold() if tien > 1000000 else discord.Color.teal())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {lv}**", inline=True)
    embed.add_field(name="💰 Tài sản", value=f"**{tien:,} 💰** {'*(ĐANG NỢ)*' if tien<0 else ''}", inline=True)
    
    if user_data.get("company"): 
        embed.add_field(name="🏢 Công ty", value=f"**{load_company(user_data['company'])['name']}**", inline=False)
        
    if user_data.get("jail_time"): 
        embed.add_field(name="🚨 Trạng thái", value="**Đang bóc lịch trong trại giam!**", inline=False)
    
    embed.add_field(name="✨ Kinh nghiệm", value=f"`{make_progress_bar(xp, lv * 100)}`\n**{xp}/{lv * 100} XP**", inline=False)
    
    assets = user_data.get('assets', [])
    embed.set_footer(text=f"BĐS Sở hữu: {', '.join(assets[:2])}..." if assets else "Gia cảnh: Vô Gia Cư")
    await ctx.send(embed=embed)

@bot.command()
async def tuido(ctx):
    user_data = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO BÁU CỦA {ctx.author.name.upper()}", color=discord.Color.dark_purple())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    embed.add_field(name="🏠 Tài Sản Cá Nhân", value="Trống không." if not user_data.get("assets") else "\n".join([f"🔸 {a}" for a in user_data["assets"]]), inline=False)
    embed.add_field(name="🐾 Trang Trại Thú Cưng", value="Chưa bắt được con nào." if not user_data.get("pets") else "\n".join([f"{p} (x{c})" for p, c in user_data["pets"].items()]), inline=False)
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
            return await ctx.send(embed=embed)
    
    user_data["money"] += 500
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(title="🎁 QUÀ ĐIỂM DANH", description=f"Nhận **500 💰** thành công!\nSố dư: {user_data['money']:,} 💰", color=discord.Color.green())
    await ctx.send(embed=embed)

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
            return await ctx.send(embed=embed)

    tien = random.randint(1000, 8000) 
    user_data["money"] += tien
    user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(description=f"🧧 Bạn mở phong bao đỏ và nhận được **{tien:,} 💰**!\n💳 Số dư: **{user_data['money']:,} 💰**", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    danh_sach = sorted([(doc["_id"], doc.get("money", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
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
async def give(ctx, member: discord.Member, amount: int):
    n_gui = str(ctx.author.id)
    n_nhan = str(member.id)
    gui_data = load_user(n_gui)
    nhan_data = load_user(n_nhan)
    
    if amount <= 0 or gui_data.get("money", 0) < amount or n_gui == n_nhan: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển cho mình).", color=discord.Color.red()))
        
    gui_data["money"] -= amount
    nhan_data["money"] += amount
    save_user(n_gui)
    save_user(n_nhan)
    
    embed = discord.Embed(title="💸 CHUYỂN KHOẢN THÀNH CÔNG", description=f"{ctx.author.mention} đã chuyển cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green())
    await ctx.send(embed=embed)

# =====================================================================
# LỆNH CỬA HÀNG VÀ CHỢ ĐEN
# =====================================================================
@bot.command(aliases=['ban', 'sell'])
async def choden(ctx): 
    embed = discord.Embed(title="⚖️ CHỢ ĐEN CẦM ĐỒ", description="Đem đồ ra đây cầm, nhận tiền liền tay!", color=discord.Color.dark_orange())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=SellCategoryMenu(ctx.author))

@bot.command(aliases=['shop'])
async def cuahang(ctx): 
    embed = discord.Embed(title="🏪 ĐẠI SIÊU THỊ TRUNG TÂM", description="Bán tất cả mọi thứ từ xe đạp đến Phi thuyền không gian!", color=discord.Color.brand_green())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

# =====================================================================
# CÁC LỆNH CHỨNG KHOÁN, ĐÀO VÀNG, CƯỚP BANK VÀ RPG
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    next_ts = get_next_hour_timestamp()
    embed = discord.Embed(title="📈 SÀN CHỨNG KHOÁN PHỐ WALL", description=f"Cổ phiếu sẽ cập nhật giá mới vào: <t:{next_ts}:R>\n\n🛒 Mua: `k ck buy <MÃ> <SL>`\n💸 Bán: `k ck sell <MÃ> <SL>`", color=discord.Color.blue())
    
    for code, name in STOCKS.items():
        p_now = get_stock_price(code, 0)
        p_old = get_stock_price(code, -1)
        trend = "🟩 Lên" if p_now > p_old else "🟥 Xuống"
        embed.add_field(name=f"🏢 {code} - {name}", value=f"Giá: **{p_now:,} 💰**\n*(Biến động: {trend} {abs(p_now - p_old):,})*", inline=False)
        
    my_stocks = load_user(ctx.author.id).get("stocks", {})
    inv = "\n".join([f"🔸 {k}: {v} cổ phiếu" for k, v in my_stocks.items() if v > 0])
    embed.add_field(name="🎒 Cổ phiếu bạn đang giữ", value=inv if inv else "Trống trơn.", inline=False)
    
    await ctx.send(embed=embed)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    if code not in STOCKS or qty <= 0: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Mã cổ phiếu hoặc số lượng không hợp lệ!", color=discord.Color.red()))
        
    cost = get_stock_price(code, 0) * qty
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) < cost: 
        return await ctx.send(embed=discord.Embed(description=f"⚠️ Thiếu lúa! Cần **{cost:,} 💰**.", color=discord.Color.red()))
        
    user_data["money"] -= cost
    user_data["stocks"][code] = user_data.get("stocks", {}).get(code, 0) + qty
    save_user(user_id)
    
    embed = discord.Embed(description=f"✅ Lệnh BUY khớp! Mua **{qty} {code}** hết **{cost:,} 💰**.", color=discord.Color.green())
    await ctx.send(embed=embed)

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper()
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    my_qty = user_data.get("stocks", {}).get(code, 0)
    
    if code not in STOCKS or qty <= 0 or my_qty < qty: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Bạn không đủ số cổ phiếu này hoặc mã sai!", color=discord.Color.red()))
        
    gain = get_stock_price(code, 0) * qty
    user_data["stocks"][code] -= qty
    user_data["money"] += gain
    save_user(user_id)
    
    embed = discord.Embed(description=f"✅ Lệnh SELL khớp! Chốt lời **{qty} {code}** thu về **{gain:,} 💰**.", color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_data.get("money", 0) < 50000: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Bạn cần tối thiểu 50,000 💰 mua súng M4A1 mới đi cướp được!", color=discord.Color.red()))
    
    if user_id in cty_cooldowns and (now - cty_cooldowns[user_id]).total_seconds() < 3600:
        return await ctx.send(embed=discord.Embed(description="⏳ Đang bị truy nã gắt gao cấp độ 5 sao! Trốn 1 tiếng nữa rồi cướp tiếp.", color=discord.Color.orange()))
    
    cty_cooldowns[user_id] = now
    embed = discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Bạn đang đeo mặt nạ, cầm súng đạp cửa xông vào Ngân hàng Nhà nước...", color=discord.Color.dark_grey())
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= 20: 
        loot = random.randint(200000, 800000)
        user_data["money"] += loot
        save_user(user_id)
        
        embed.color = discord.Color.green()
        embed.description = f"🎉 **TRÓT LỌT!** Bạn uy hiếp giám đốc, vơ vét sạch két sắt và chuồn êm qua đường cống ngầm.\n\n💰 Húp trọn: **{loot:,} 💰**!"
    else: 
        user_data["money"] -= 50000
        jail_time = now + timedelta(minutes=10)
        user_data["jail_time"] = jail_time.strftime("%Y-%m-%d %H:%M:%S")
        save_user(user_id)
        
        embed.color = discord.Color.red()
        embed.description = f"🚨 **WEE WOO WEE WOO!** Đặc nhiệm SWAT ập tới thả bom mù!\nBạn bị tóm gọn, xích tay lôi đi.\n\n❌ Mất 50,000 💰 tiền mua súng.\n⛔ **BỊ CẤM DÙNG BOT ĐẾN: <t:{int(jail_time.timestamp())}:R>**!"
        
    await msg.edit(embed=embed)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    now = datetime.now()
    
    if user_id in work_cooldowns and (now - work_cooldowns[user_id]).total_seconds() < 30:
        time_left = int(30 - (now - work_cooldowns[user_id]).total_seconds())
        return await ctx.send(embed=discord.Embed(description=f"⏳ Tay mỏi nhừ rồi! Nghỉ {time_left}s nữa hẵng cuốc tiếp.", color=discord.Color.orange()))
    
    if "Cuốc Chim ⛏️" not in user_data.get("assets", []):
        if user_data.get("money", 0) < 5000: 
            return await ctx.send(embed=discord.Embed(description="⚠️ Bạn không có Cuốc Chim, mà tiền cũng không đủ 5,000 💰 để mua luôn! Đi cày đi.", color=discord.Color.red()))
        
        user_data["money"] -= 5000
        user_data["assets"].append("Cuốc Chim ⛏️")
        await ctx.send(embed=discord.Embed(description="🛒 Đã tự động mua **Cuốc Chim ⛏️** giá 5,000 💰 từ cửa hàng để bắt đầu đào!", color=discord.Color.blue()))
    
    work_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(description="⛏️ Cạch... Cạch... Bạn đang vung cuốc đập đá...", color=discord.Color.dark_grey()))
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
        return await msg.edit(embed=discord.Embed(description=f"💥 **BÙMMMMM!** Bạn đào trúng quả bom chưa nổ thời chiến tranh!\nBệnh viện thu viện phí **{penalty:,} 💰**!", color=discord.Color.red()))

    user_data["money"] += val
    save_user(user_id)
    embed_color = discord.Color.green() if val > 0 else discord.Color.light_grey()
    await msg.edit(embed=discord.Embed(description=f"⛏️ Đào trúng: **{res}**\nĐem bán được: **{val:,} 💰**", color=embed_color))

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    cost = 30000
    
    if user_data.get("money", 0) < cost: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Trứng Gacha giá 30k lận. Đi cày thêm đi sếp!", color=discord.Color.red()))
        
    user_data["money"] -= cost
    save_user(user_id)
    
    embed = discord.Embed(title="🥚 ĐẬP TRỨNG GACHA", description=f"{ctx.author.mention} đang vung búa đập trứng...", color=discord.Color.orange())
    msg = await ctx.send(embed=embed)
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

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx): 
    embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ RỪNG SÂU", description="Mua vũ khí xịn để tăng tỉ lệ sống sót nhé!", color=discord.Color.orange())
    await ctx.send(embed=embed, view=KhungRungShopView(ctx.author, 0))

@bot.command()
async def phai(ctx):
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
            embed = discord.Embed(title="🎉 TRỞ VỀ AN TOÀN!", description=f"{ctx.author.mention} đã thu hoạch được **{reward:,} 💰**!", color=discord.Color.gold())
            return await ctx.send(embed=embed)
        else:
            time_left = end_time - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            embed = discord.Embed(description=f"⏳ Đang cày cuốc sấp mặt! Hãy kiên nhẫn chờ thêm **{hours} giờ {minutes} phút** nữa nhé.", color=discord.Color.orange())
            return await ctx.send(embed=embed)
            
    embed = discord.Embed(title="⛺ TRẠM THÁM HIỂM AFK", description="Gửi nhân vật đi treo máy và nhặt tiền lúc trở về!\n\n👇 **MỞ MENU ĐỂ CHỌN KHU VỰC** 👇", color=discord.Color.dark_green())
    await ctx.send(embed=embed, view=ExpView(ctx.author))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id)
    now = datetime.now()
    
    if user_id in dang_choi_nhansinh: 
        return await ctx.send(embed=discord.Embed(description=f"⏳ {ctx.author.mention}, bạn đang luân hồi dở dang rồi!", color=discord.Color.orange()))
        
    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5: 
        return await ctx.send(embed=discord.Embed(description="⏳ Đợi một chút mới được đầu thai tiếp.", color=discord.Color.orange()))

    user_data = load_user(user_id)
    if user_data.get("money", 0) < 100: 
        return await ctx.send(embed=discord.Embed(description=f"⚠️ Vé luân hồi giá **100 💰**. Túi rỗng thì không có cửa đầu thai đâu!", color=discord.Color.red()))

    user_data["money"] -= 100
    nhansinh_cooldowns[user_id] = now
    dang_choi_nhansinh.append(user_id)
    save_user(user_id)

    view = NhanSinhGameView(ctx.author, {"may_man": random.randint(1, 10)})
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH", description=f"Ký chủ luân hồi: {ctx.author.mention}", color=discord.Color.teal())
    embed.add_field(name="📜 Hành trình cuộc đời", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Quyết định tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    await ctx.send(embed=embed, view=view)


# =====================================================================
# HỆ THỐNG CÔNG TY & ĐẠI CHIẾN
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
        return await ctx.send("Công ty của bạn đã phá sản! Hãy lập công ty mới.")
        
    my_role = comp["members"].get(user_id, "nhanvien")
    role_name = comp["roles"].get(my_role, my_role)
    
    embed = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed.add_field(name="Chức vụ của bạn", value=f"**{role_name}**", inline=False)
    
    cmds = "`k cty gop <tiền>`: Góp quỹ\n`k cty thulai`: Nhận lãi mỗi ngày\n`k cty roi`: Nghỉ việc"
    if my_role in ["boss", "quanly"]:
        cmds += "\n`k cty tuyen @user`: Tuyển nhân viên\n`k cty duoi @user`: Đuổi việc"
    if my_role == "boss":
        cmds += "\n`k cty luong <tiền>`: Phát lương\n`k cty chucvu @user <quanly/nhanvien>`\n`k cty doitenchuc <boss/quanly/nhanvien> <Tên>`"
        
    embed.add_field(name="Bảng Lệnh Công Ty", value=cmds, inline=False)
    await ctx.send(embed=embed)

@cty.command()
async def tao(ctx, *, name: str):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("company"): 
        return await ctx.send("Bạn đã ở trong một công ty rồi! Thoát ra trước khi tạo mới.")
        
    if user_data.get("money", 0) < 500000: 
        return await ctx.send("⚠️ Phí thành lập công ty là **500,000 💰**. Cày thêm đi sếp!")
    
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
        description=f"Chúc mừng sếp {ctx.author.mention} đã thành lập **{name}**!\nGõ `k cty` để xem bảng điều khiển.", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@cty.command()
async def tuyen(ctx, member: discord.Member):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.send("Bạn có công ty đâu mà đòi tuyển người!")
        
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: 
        return await ctx.send("Chỉ sếp lớn mới được tuyển người!")
        
    if load_user(member.id).get("company"): 
        return await ctx.send("Người này đã có công ty rồi.")
    
    view = CompanyInviteView(comp_id, comp["name"], member)
    await ctx.send(f"🏢 {member.mention}, bạn có lời mời vào làm việc tại **{comp['name']}**! Bấm nút bên dưới để quyết định.", view=view)

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")
    
    if not comp_id: 
        return await ctx.send("Bạn chưa có công ty.")
        
    if user_data.get("money", 0) < amount: 
        return await ctx.send("Không đủ tiền để góp!")
    
    comp = load_company(comp_id)
    user_data["money"] -= amount
    comp["treasury"] += amount
    
    save_user(user_id)
    save_company(comp_id)
    await ctx.send(f"💰 Bạn đã góp **{amount:,} 💰** vào quỹ công ty. Tổng quỹ: **{comp['treasury']:,} 💰**.")

@cty.command()
async def thulai(ctx):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    
    if not comp_id: return
    comp = load_company(comp_id)
    
    if comp["members"].get(user_id) != "boss": 
        return await ctx.send("Chỉ Chủ tịch mới được thu lãi ngân hàng!")
    
    now = datetime.now()
    last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    
    if now - last < timedelta(days=1):
        return await ctx.send("⏳ Ngân hàng chưa chốt sổ! Mỗi ngày chỉ được thu lãi 1 lần.")
        
    lai = int(comp["treasury"] * 0.05) 
    if lai > 100000: lai = 100000 
    
    comp["treasury"] += lai
    comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    await ctx.send(f"📈 Công ty đã nhận được **{lai:,} 💰** tiền lãi hôm nay! Tổng quỹ: **{comp['treasury']:,} 💰**.")

@bot.command()
async def daichien(ctx, member: discord.Member = None, tactic: str = None):
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    
    if not member or not tactic or tactic.lower() not in ["hack", "phot", "giangho"]:
        embed = discord.Embed(
            title="⚔️ ĐẠI CHIẾN THƯƠNG TRƯỜNG", 
            description="Cách dùng: `k daichien @user <chiến_thuật>`", 
            color=discord.Color.red()
        )
        embed.add_field(name="1. hack (Tấn công mạng)", value="Tỉ lệ thắng: **30%**\nPhần thưởng: Cướp **10%** quỹ đối thủ.\nThất bại: Đền bù **5%** quỹ của mình.", inline=False)
        embed.add_field(name="2. phot (Thuê KOL bóc phốt)", value="Tỉ lệ thắng: **50%**\nPhần thưởng: Cướp **5%** quỹ đối thủ.\nThất bại: Đền bù **2%** quỹ của mình.", inline=False)
        embed.add_field(name="3. giangho (Vũ lực)", value="Tỉ lệ thắng: **70%**\nPhần thưởng: Cướp **2%** quỹ đối thủ.\nThất bại: Đền bù **1%** quỹ của mình.", inline=False)
        return await ctx.send(embed=embed)
        
    target_id = str(member.id)
    target_comp_id = load_user(target_id).get("company")
    
    if user_id == target_id or member.bot: 
        return await ctx.send("⚠️ Đánh với ai chứ đừng tự kỷ hoặc đánh Bot.")
        
    if not comp_id or not target_comp_id: 
        return await ctx.send("⚠️ Cả 2 đều phải có công ty mới được PK!")
        
    if comp_id == target_comp_id: 
        return await ctx.send("⚠️ Cùng một công ty, anh em tương tàn làm gì!")
    
    now = datetime.now()
    if comp_id in cty_cooldowns and (now - cty_cooldowns[comp_id]).total_seconds() < 3600:
        return await ctx.send(embed=discord.Embed(description="⏳ Công ty bạn vừa xuất quân rồi! Đợi 1 tiếng để hồi phục binh lực.", color=discord.Color.orange()))
    
    comp1 = load_company(comp_id)
    comp2 = load_company(target_comp_id)
    
    if comp2["treasury"] < 10000: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Quỹ công ty đối thủ nghèo quá (<10k), không đáng để cất quân đi đánh!", color=discord.Color.red()))
    
    cty_cooldowns[comp_id] = now
    tactic = tactic.lower()
    
    if tactic == "hack": win_rate, win_pct, lose_pct, name = 30, 0.10, 0.05, "TẤN CÔNG MẠNG"
    elif tactic == "phot": win_rate, win_pct, lose_pct, name = 50, 0.05, 0.02, "BÓC PHỐT"
    else: win_rate, win_pct, lose_pct, name = 70, 0.02, 0.01, "GIANG HỒ"
    
    embed = discord.Embed(description=f"⚔️ **{comp1['name']}** đang dùng chiến thuật **{name}** lên **{comp2['name']}**...", color=discord.Color.dark_grey())
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2)
    
    if random.randint(1, 100) <= win_rate:
        steal = int(comp2["treasury"] * win_pct)
        comp1["treasury"] += steal
        comp2["treasury"] -= steal
        save_company(comp_id)
        save_company(target_comp_id)
        
        win_embed = discord.Embed(description=f"🔥 **ĐẠI THẮNG!** Binh pháp quá đỉnh!\n💰 Cướp được **{steal:,} 💰** mang về quỹ công ty!", color=discord.Color.green())
        await msg.edit(embed=win_embed)
    else:
        fine = int(comp1["treasury"] * lose_pct)
        comp1["treasury"] -= fine
        comp2["treasury"] += fine
        save_company(comp_id)
        save_company(target_comp_id)
        
        lose_embed = discord.Embed(description=f"💀 **THẤT BẠI!** Đối thủ đã phòng bị!\nBạn bị kiện ngược và phải đền bù **{fine:,} 💰** cho quỹ đối thủ.", color=discord.Color.red())
        await msg.edit(embed=lose_embed)

# =====================================================================
# HỆ THỐNG CỜ BẠC CASINO FULL
# =====================================================================
@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    embed = discord.Embed(description=f"🪙 {ctx.author.mention} ném **{bet:,} 💰** lên trời...\n🔄 Đồng xu xoay tít...", color=discord.Color.gold())
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2) 

    if random.choice([True, False]):
        user_data = load_user(user_id)
        user_data["money"] += bet * 2
        save_user(user_id)
        
        win_embed = discord.Embed(description=f"🪙 **MẶT NGỬA!**\n🎉 Húp trọn **{bet * 2:,} 💰**!\n💳 Số dư: {user_data['money']:,} 💰", color=discord.Color.green())
        await msg.edit(embed=win_embed)
    else:
        user_data = load_user(user_id)
        lose_embed = discord.Embed(description=f"🪙 **MẶT SẤP!**\n💀 Nhờn! Mất **{bet:,} 💰**.\n💳 Số dư: {user_data['money']:,} 💰", color=discord.Color.red())
        await msg.edit(embed=lose_embed)

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    if choice.lower() not in ["tai", "tài", "xiu", "xỉu"]: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Vui lòng gõ `k taixiu tai <tiền>` hoặc `xiu`.", color=discord.Color.red()))
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    embed = discord.Embed(
        title="🎲 LẮC XÍ NGẦU", 
        description=f"{ctx.author.mention} cược **{bet:,} 💰** vào cửa **{choice.upper()}**.\n\nNhà cái đang lắc... 🫨", 
        color=discord.Color.gold()
    )
    msg = await ctx.send(embed=embed)
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
    result_embed.description = f"**[ {d1} | {d2} | {d3} ]** (Tổng: {total} - **{res_str.upper()}**)\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=result_embed)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    valid_choices = {"bau":"🥒", "cua":"🦀", "tom":"🦐", "ca":"🐟", "ga":"🐓", "huou":"🦌"}
    choice_clean = choice.replace("ầ","a").replace("ô","o").lower()
    
    if choice_clean not in valid_choices: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Tên sai! Các cửa gồm: `bau, cua, tom, ca, ga, huou`.", color=discord.Color.red()))
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    user_icon = valid_choices[choice_clean]
    
    embed = discord.Embed(
        title="🎲 BẦU CUA TÔM CÁ", 
        description=f"{ctx.author.mention} cược **{bet:,} 💰** vào ô **{user_icon}**.\n\nĐang xóc dĩa... 🫨", 
        color=discord.Color.gold()
    )
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2.5)
    
    dice = [random.choice(list(valid_choices.values())) for _ in range(3)]
    match_count = dice.count(user_icon)
    
    result_embed = discord.Embed(title="🎲 MỞ BÁT")
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
    result_embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=result_embed)

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo":"🐖", "cho":"🐕", "ngua":"🐎", "chuot":"🐀"}
    choice = choice.lower()
    if choice not in animals: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Nhập sai! Các cửa gồm: `heo, cho, ngua, chuot`.", color=discord.Color.red()))
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    track_len = 20
    pos = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def generate_track(): 
        track = f"🏇 **ĐƯỜNG ĐUA THÚ**\n{ctx.author.name} cược {bet:,} 💰 vào {animals[choice]}\n\n"
        for pet, distance in pos.items():
            run = min(distance, track_len)
            space = track_len - run
            track += f"🏁{'~' * run}{pet}{' ' * space}⛩️\n"
        return track
        
    msg = await ctx.send(generate_track())
    winner = None
    
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in pos: 
            pos[pet] += random.randint(2, 6)
            if pos[pet] >= track_len and not winner: 
                winner = pet
        await msg.edit(content=generate_track())
        if winner: break
        
    if not winner: 
        winner = max(pos, key=pos.get)
        pos[winner] = track_len
        await msg.edit(content=generate_track())
        
    if animals[choice] == winner: 
        user_data["money"] += bet * 3
        res = f"\n🏆 **{winner} VỀ NHẤT!** Quá đỉnh, ăn được **x3 tiền ({bet * 3:,} 💰)**!"
    else: 
        res = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} của bạn xịt rồi. Mất sạch **{bet:,} 💰**."
        
    save_user(user_id)
    await msg.edit(content=generate_track() + res)

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
    
    embed = discord.Embed(title="🎰 MÁY XÈNG NỔ HŨ 🎰", color=discord.Color.gold())
    msg = await ctx.send(embed=embed)
    
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
        user_data["money"] += win_amt
        res = f"🔥 **JACKPOT NỔ HŨ!!!** Trúng 3 ô {slots[0]}\nHúp trọn **{win_amt:,} 💰**!"
    elif slots[0] == slots[1] or slots[1] == slots[2] or slots[0] == slots[2]: 
        win_amt = bet * 2
        user_data["money"] += win_amt
        res = f"🎉 **THẮNG NHỎ!** Trúng 2 ô.\nNhận **{win_amt:,} 💰**."
    else: 
        res = f"💀 **TOANG!** Xịt mất **{bet:,} 💰**."
        
    save_user(user_id)
    embed.description = f"**[ {slots[0]} | {slots[1]} | {slots[2]} ]**\n\n{res}"
    embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)

@bot.command()
async def soloott(ctx, member: discord.Member, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    if member.id == ctx.author.id or member.bot: 
        return await ctx.send(embed=discord.Embed(description="⚠️ Bạn không thể thác đấu với chính mình hoặc với Bot.", color=discord.Color.red()))
        
    if load_user(member.id).get("money", 0) < bet: 
        return await ctx.send(embed=discord.Embed(description=f"⚠️ Đối thủ {member.mention} đang nghèo, không đủ **{bet:,} 💰** để nhận kèo đâu!", color=discord.Color.red()))
    
    embed = discord.Embed(
        title="🔥 THÁCH ĐẬU OẲN TÙ TÌ", 
        description=f"{ctx.author.mention} vừa cầm **{bet:,} 💰** đập bàn, thách đấu solo với {member.mention}!\n\nNhanh tay bấm **Nhận Kèo** trong vòng 60 giây nếu dám chơi!", 
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=SoloOTTAccept(ctx.author, member, bet))


# =====================================================================
# HỆ THỐNG LEVEL & QUẢN TRỊ VIÊN
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
