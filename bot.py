import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 

# =====================================================================
# THIẾT LẬP CƠ BẢN CỦA BOT SIÊU VIP 6.0
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Bắt buộc để game Ma Sói có thể nhắn tin riêng (DM)

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
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
werewolf_lobbies = {}

# =====================================================================
# KẾT NỐI MONGODB VÀ HỆ THỐNG BỘ ĐỆM (CACHE)
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
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
        document = users_col.find_one({"_id": user_id})
        if document:
            DB_CACHE[user_id] = document
        else:
            DB_CACHE[user_id] = {}
            
    defaults = {
        "xp": 0, "level": 1, "money": 0, "bank": 0, "title": "Dân Đáy Xã Hội 🧱", 
        "assets": [], "pets": {}, "company": None, "stocks": {}, 
        "jail_time": None, "spouse": None, "history": [],
        "farm": {"seed": None, "plant_time": None}, "last_interest": "2000-01-01 00:00:00"
    }
    
    for key, value in defaults.items():
        if key not in DB_CACHE[user_id]: 
            DB_CACHE[user_id][key] = value
            
    return DB_CACHE[user_id]

def save_user(user_id):
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
        if document: 
            if "reputation" not in document: document["reputation"] = 100 
            if "has_scandal" not in document: document["has_scandal"] = False
            if "atk_level" not in document: document["atk_level"] = 1
            if "def_level" not in document: document["def_level"] = 1
            COMPANY_CACHE[company_id] = document
        else: return None
    return COMPANY_CACHE[company_id]

def save_company(company_id):
    company_id = str(company_id)
    if company_id in COMPANY_CACHE: 
        companies_col.update_one({"_id": company_id}, {"$set": COMPANY_CACHE[company_id]}, upsert=True)

def add_history(user_id, entry):
    user_data = load_user(user_id)
    if "history" not in user_data: user_data["history"] = []
    time_str = datetime.now().strftime('%H:%M %d/%m')
    user_data["history"].insert(0, f"[`{time_str}`] {entry}")
    if len(user_data["history"]) > 10: user_data["history"].pop()

# =====================================================================
# HÀM KIỂM TRA TỔNG THỂ (GLOBAL CHECKS)
# =====================================================================
@bot.check
async def global_jail_and_channel_check(ctx):
    if ctx.author.guild_permissions.administrator or ctx.command.name == "help": return True
        
    user_data = load_user(ctx.author.id)
    jail_time_str = user_data.get("jail_time")
    
    if jail_time_str:
        jail_end = datetime.strptime(jail_time_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            embed = discord.Embed(
                title="🚨 BÁO ĐỘNG ĐỎ!", 
                description=f"{ctx.author.mention} đang bóc lịch trong trại giam do vi phạm pháp luật!\n\n"
                            f"⏳ Thời gian mãn hạn tù: <t:{int(jail_end.timestamp())}:R>\n\n"
                            f"Hãy tự vấn lương tâm trong phòng biệt giam rồi quay lại sau nhé!", 
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
        if allowed_channels and ctx.channel.id not in allowed_channels: return False
    return True

def make_progress_bar(current_value, total_value, bar_length=12):
    progress_blocks = int((current_value / total_value) * bar_length)
    empty_blocks = bar_length - progress_blocks
    return "🟩" * progress_blocks + "⬛" * empty_blocks

async def check_gamble_conditions(ctx, amount_str):
    user_id = str(ctx.author.id)
    current_time = datetime.now()
    
    if user_id in gamble_cooldowns:
        time_diff = (current_time - gamble_cooldowns[user_id]).total_seconds()
        if time_diff < 4:
            embed_cd = discord.Embed(description=f"⏳ Tay mỏi rồi! Đợi {int(4 - time_diff)}s nữa hẵng lắc tiếp sếp ơi!", color=discord.Color.orange())
            await ctx.reply(embed=embed_cd, mention_author=False)
            return None, None
            
    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        embed_bankrupt = discord.Embed(description="💸 Kẻ tổn thương lại muốn tổn thương sòng bạc à? Tiền trong ví không có một xu!", color=discord.Color.red())
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
        return None, None
        
    try: 
        if amount_str.lower() == "all": bet_amount = user_data["money"] if user_data["money"] <= 500000 else 500000
        else: bet_amount = int(amount_str)
    except ValueError: 
        embed_err = discord.Embed(description="⚠️ Nhập số tiền sai định dạng! Vui lòng nhập số hoặc chữ `all`.", color=discord.Color.red())
        await ctx.reply(embed=embed_err, mention_author=False)
        return None, None
        
    if bet_amount <= 0 or bet_amount > user_data["money"]: 
        embed_poor = discord.Embed(description=f"⚠️ Bốc phét à? Sếp chỉ có **{user_data['money']:,} 💰** trong ví thôi!", color=discord.Color.red())
        await ctx.reply(embed=embed_poor, mention_author=False)
        return None, None
        
    if bet_amount > 500000: 
        embed_max = discord.Embed(description="🛑 Nhà cái quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé!", color=discord.Color.red())
        await ctx.reply(embed=embed_max, mention_author=False)
        return None, None
        
    return user_data, bet_amount

# =====================================================================
# DATA HỆ THỐNG CỬA HÀNG, PET, CHỨNG KHOÁN, NÔNG TRẠI
# =====================================================================
FARM_SEEDS = {
    "lua": {"name": "Lúa Mì 🌾", "cost": 5000, "time_hours": 4, "profit_min": 15000, "profit_max": 25000},
    "ngo": {"name": "Ngô Đồng 🌽", "cost": 15000, "time_hours": 8, "profit_min": 40000, "profit_max": 65000},
    "cachua": {"name": "Cà Chua Đỏ 🍅", "cost": 30000, "time_hours": 12, "profit_min": 90000, "profit_max": 140000},
    "nhansam": {"name": "Nhân Sâm Ngàn Năm 🌿", "cost": 100000, "time_hours": 24, "profit_min": 350000, "profit_max": 600000}
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
    "house_7": {"type": "house", "name": "Hành Tinh Namek 🪐", "price": 2000000000, "emoji": "🪐"}
}

def get_asset_price(asset_name):
    for item_key, item_data in SHOP_ITEMS.items():
        if item_data["name"] == asset_name: return int(item_data["price"] * 0.7)
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
            if rarity == "common": return 5000      
            if rarity == "rare": return 20000       
            if rarity == "epic": return 150000      
            if rarity == "legendary": return 800000 
            if rarity == "mythic": return 10000000   
    return 1000

STANDARD_STOCKS = {
    "VIN": "Tập Đoàn VIN", "FLC": "Hàng Không FLC", "VNZ": "Công Nghệ VNZ", 
    "DOGE": "Doge Coin", "BTC": "Bitcoin", "AAPL": "Apple Inc.", "TSLA": "Tesla"
}

def get_all_stocks():
    all_stocks = STANDARD_STOCKS.copy()
    ipo_companies = companies_col.find({"is_ipo": True})
    for comp in ipo_companies:
        code = comp["name"][:4].upper()
        all_stocks[code] = comp["name"]
    return all_stocks

def get_stock_price(stock_code, hour_offset=0):
    ipo_comp = companies_col.find_one({"is_ipo": True, "name": {"$regex": f"^{stock_code}", "$options": "i"}})
    target_time = datetime.now() + timedelta(hours=hour_offset)
    rng = random.Random(int(target_time.strftime("%Y%m%d%H")) + sum(ord(char) for char in stock_code))
    
    if ipo_comp:
        base_price = max(5000, int(ipo_comp.get("treasury", 0) / 1000))
        rep_multiplier = max(0.1, ipo_comp.get("reputation", 100) / 100.0) 
        scandal_penalty = 0.6 if ipo_comp.get("has_scandal", False) else 1.0 
        market_fluctuation = rng.uniform(0.85, 1.15)
        
        final_price = int(base_price * rep_multiplier * scandal_penalty * market_fluctuation)
        return max(1000, final_price) 

    base = rng.randint(5, 800) * 1000
    if rng.randint(1, 100) <= 5: return 1000 
    return base

def get_next_hour_timestamp():
    next_hour = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int(next_hour.timestamp())

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
        {"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!**\nBạn vô tình chọc tức chúa tể rừng xanh. Bị đấm bay xa 10km, rớt sạch đồ đạc!"},
        {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại đang ngủ. Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền!"},
        {"mult": -1.3, "msg": "🕳️ **SỤP HỐ CHÔNG!**\nRơi thẳng xuống hố chông của thợ săn. Gãy 2 cái sườn, nôn hết tiền mặt ra đóng viện phí."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ từ trên cây nhảy xuống giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước suối hết hạn từ cái máy bán hàng tự động ma quái trong rừng. Bị đau bụng tốn tiền viện phí."},
        {"mult": -0.8, "msg": "💩 **TRƯỢT CHÂN VÀO BÃI MÌN!**\nBạn dẫm trúng bãi mìn khổng lồ của đàn voi rừng. Tốn tiền đi tắm gội mua bộ đồ mới."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ XÀO XẠC...**\nBạn vạch lùm cây ra và... chẳng có gì cả, chỉ là một đống lá khô."},
        {"mult": 0, "msg": "📦 **RƯƠNG RỖNG TOẾCH!**\nHáo hức mở một cái rương cũ kỹ, nhưng bên trong chả có gì ngoài mạng nhện."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc Bắc đã trả cho bạn một khoản hời."}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp rừng và tịch thu kho báu của chúng!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nPhát hiện ra một rương kho báu vàng chóe bị chôn vùi. Mở ra toàn tiền là tiền!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng giải ĐẶC BIỆT!"},
        {"mult": 12.0, "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR! (ULTRAPOT)**\nDưới đáy đầm lầy, bạn vớt được Vương miện nạm 100 viên kim cương. Bạn thành tỷ phú rồi!!"}
    ]
}

EVENTS_P1 = [
    {
        "q": "Tuổi 15: Bạn tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", 
        "choices": [
            {"text": "Đem nộp lên công an phường", "rate": 50, "win": "Chủ ví là một giám đốc lớn, khen thưởng bạn tiền mặt.", "lose": "Bị công an nghi ngờ là người ăn cắp, phạt lao động công ích.", "tien_w": 5000, "tien_l": -10000}, 
            {"text": "Bỏ túi xài luôn, không nói ai", "rate": 20, "win": "Trót lọt, bạn bao cả lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường tiền và bị đuổi học.", "tien_w": 8000, "tien_l": -25000}, 
            {"text": "Rút tờ 500k rồi vứt lại ví", "rate": 30, "win": "Trót lọt, bạn dùng tiền đó nạp game.", "lose": "Chủ nhân báo mất, bị giang hồ mạng truy lùng bắt đền gấp 10.", "tien_w": 500, "tien_l": -50000}, 
            {"text": "Giả vờ không thấy, đi thẳng", "rate": 80, "win": "Bình yên vô sự, cuộc đời không có biến động.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn, phải tự bỏ tiền túi ra đền.", "tien_w": 0, "tien_l": -15000}
        ]
    }
]

EVENTS_P2 = [
    {
        "q": "Tuổi 25: Bạn có 500 triệu tiền tiết kiệm, hãy đưa ra quyết định đầu tư.", 
        "choices": [
            {"text": "All-in Tiền ảo (Crypto / Memecoin)", "rate": 15, "win": "Giá x100 lần! Bạn chốt lời mua biệt thự và siêu xe.", "lose": "Bị 'úp bô' sập sàn, cháy túi và gánh nợ ngân hàng.", "tien_w": 2500000, "tien_l": -500000}, 
            {"text": "Gửi tiết kiệm ngân hàng", "rate": 70, "win": "Lãi suất ổn định, cuộc sống an nhàn qua ngày.", "lose": "Ngân hàng bị thanh tra, giám đốc ôm tiền bỏ trốn. Mất sạch.", "tien_w": 50000, "tien_l": -500000}, 
            {"text": "Khởi nghiệp kinh doanh nhà hàng", "rate": 30, "win": "Khách đông nườm nượp, mở chuỗi 5 chi nhánh.", "lose": "Bị đối thủ chơi bẩn bóc phốt trên Tiktok, phá sản ôm nợ.", "tien_w": 500000, "tien_l": -800000}, 
            {"text": "Mua vàng cất vào két sắt", "rate": 60, "win": "Vàng tăng giá phi mã, bạn chốt lời đậm.", "lose": "Bị trộm cạy cửa vào nhà khiêng luôn két sắt.", "tien_w": 100000, "tien_l": -500000}
        ]
    }
]
EVENTS_P3 = [
    {
        "q": "Tuổi 35: Cò đất rủ bạn chung vốn lướt sóng khu quy hoạch mới.", 
        "choices": [
            {"text": "Cắm sổ đỏ vay nặng lãi quất liền", "rate": 10, "win": "Thành công vang dội! Giá đất x5, bạn thành tỷ phú bất động sản.", "lose": "Dính bẫy dự án ma của Công ty lừa đảo. Giang hồ siết nợ, ra đê ở.", "tien_w": 5000000, "tien_l": -2000000}, 
            {"text": "Mua 1 lô nhỏ bằng vốn tự có", "rate": 40, "win": "Đất lên nhẹ, bạn chốt lời an toàn.", "lose": "Đất dính quy hoạch làm nghĩa trang, giam vốn không ai mua.", "tien_w": 300000, "tien_l": -200000}, 
            {"text": "Làm 'Cò đất' ăn hoa hồng", "rate": 50, "win": "Chốt được chục lô, hoa hồng nhận mỏi tay.", "lose": "Khách hàng bùng kèo, bị chủ đất giam tiền cọc bắt đền.", "tien_w": 200000, "tien_l": -100000}, 
            {"text": "Không quan tâm nhà đất", "rate": 80, "win": "Cuộc sống trôi qua bình yên, tập trung lo cho gia đình.", "lose": "Lạm phát tăng cao, tiền giấy mất giá trầm trọng.", "tien_w": 0, "tien_l": -50000}
        ]
    },
    {
        "q": "Tuổi 35: Bạn thân cũ gọi điện khóc lóc, hỏi vay 300 triệu lo viện phí.", 
        "choices": [
            {"text": "Cho vay ngay, không cần giấy tờ", "rate": 20, "win": "Bạn qua cơn bĩ cực, làm ăn phất lên trả ơn bạn gấp 5 lần.", "lose": "Nó cầm tiền đi đánh tài xỉu thua sạch, chặn số bom tiền.", "tien_w": 1500000, "tien_l": -300000}, 
            {"text": "Từ chối khéo, bảo không có tiền", "rate": 90, "win": "Bạn giữ được tiền, tuy có chút áy náy.", "lose": "Bị nó bóc phốt lên Facebook là đồ bạn bè sống lỗi.", "tien_w": 0, "tien_l": -10000}, 
            {"text": "Chỉ cho vay 5 triệu gọi là giúp đỡ", "rate": 70, "win": "Nó nhận tiền và cảm ơn bạn rối rít.", "lose": "Nó chê ít, chửi bạn một trận rồi cúp máy.", "tien_w": 0, "tien_l": -5000}, 
            {"text": "Cho vay nhưng bắt ký giấy thế chấp xe", "rate": 50, "win": "Nó không trả được, bạn siết luôn con xe SH mang đi bán.", "lose": "Xe là xe gian (trộm cắp), bạn bị công an phạt vì tội tiêu thụ đồ gian.", "tien_w": 100000, "tien_l": -150000}
        ]
    }
]

EVENTS_P4 = [
    {
        "q": "Tuổi 50: Bạn bước vào giai đoạn khủng hoảng tuổi trung niên.", 
        "choices": [
            {"text": "Bán đất mua siêu xe để tìm lại thanh xuân", "rate": 10, "win": "Tham gia giải đua xe, trở nên nổi tiếng và kiếm bồn tiền từ quảng cáo.", "lose": "Đạp nhầm chân ga tông nát xe, đền tiền sửa chữa và tiền thuốc men.", "tien_w": 800000, "tien_l": -1000000}, 
            {"text": "Cặp Sugar Baby / Phi công trẻ", "rate": 20, "win": "Tâm hồn trẻ lại, sung mãn như thanh niên.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, ra tòa ly hôn mất trắng tài sản.", "tien_w": 10000, "tien_l": -2000000}, 
            {"text": "Chơi đồ cổ, lan đột biến", "rate": 30, "win": "Bán được bình gốm cổ cho đại gia nước ngoài, thu lãi cực đậm.", "lose": "Thị trường sập, ôm đống rác trong nhà, nợ nần chồng chất.", "tien_w": 600000, "tien_l": -500000}, 
            {"text": "Tập Thiền, đi chùa, ăn chay", "rate": 80, "win": "Tâm hồn thanh tịnh, sức khỏe dồi dào, sống thọ.", "lose": "Bị gian thương bán nấm chay có độc, phải đi rửa ruột.", "tien_w": 50000, "tien_l": -80000}
        ]
    }
]

EVENTS_P5 = [
    {
        "q": "Tuổi 70: Bạn đã già yếu. Có người đến gạ bán Linh Đan Cải Lão Hoàn Đồng giá 1 Tỷ.", 
        "choices": [
            {"text": "Vung tiền mua ngay không chần chừ", "rate": 5, "win": "Phép màu xảy ra! Bạn trở lại tuổi 20 sung mãn, sức mạnh vô địch!", "lose": "Thuốc giả chứa chì và thủy ngân. Bạn thăng thiên sớm, để lại khoản nợ.", "tien_w": 5000000, "tien_l": -1000000, "die_l": True}, 
            {"text": "Lập di chúc chia tài sản cho con cháu", "rate": 60, "win": "Con cháu hiếu thảo, tổ chức lễ mừng thọ hoành tráng.", "lose": "Con cháu bất hiếu, đánh nhau giành giật gia tài. Bạn tức quá đột quỵ.", "tien_w": 200000, "tien_l": -500000, "die_l": True}, 
            {"text": "Quyên góp 100% tài sản đi làm từ thiện", "rate": 70, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền chạy mất. Bạn ôm hận qua đời.", "tien_w": 500000, "tien_l": -1000000, "die_l": True}, 
            {"text": "Lên Las Vegas quất 1 ván Casino All-in cuối đời", "rate": 10, "win": "Trúng Jackpot 50 triệu đô! Lên báo quốc tế, trở thành huyền thoại.", "lose": "Thua trắng tay, nhồi máu cơ tim gục tại bàn sòng bạc.", "tien_w": 10000000, "tien_l": -1000000, "die_l": True}
        ]
    }
]

# =====================================================================
# GIAO DIỆN UI: CỬA HÀNG ĐẠI GIA VÀ CHỢ ĐEN CẦM ĐỒ
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
            embed_fail = discord.Embed(description=f"⚠️ Thẻ từ chối! Bạn cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            success_message = f"🎉 Tiền trao cháo múc! Bạn đã trang bị danh hiệu: **{item_info['name']}**."
        else:
            if item_info["name"] in user_data.get("assets", []):
                user_data["money"] += item_info["price"] 
                embed_exist = discord.Embed(description=f"⚠️ Bạn đã đứng tên sở hữu **{item_info['name']}** rồi, mua thêm chi cho chật nhà!", color=discord.Color.orange())
                return await interaction.response.send_message(embed=embed_exist, ephemeral=True)
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Chúc mừng đại gia! Bạn vừa đập hộp siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        add_history(user_id, f"Mua {item_info['name']} tại Store (-{item_info['price']:,} 💰)")
        
        embed_success = discord.Embed(title="🛍️ GIAO DỊCH HOÀN TẤT!", description=success_message, color=discord.Color.green())
        embed_success.set_footer(text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(title="🛍️ QUẦY BÁN DANH HIỆU", description="Tút tát lại vẻ đẹp trai bằng một danh hiệu xịn xò dán lên Căn Cước.", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(title="🛍️ SHOWROOM XE CỘ & PHI CƠ", description="Đẳng cấp thể hiện qua tốc độ. Hãy chọn một con xe ưng ý.", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(title="🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN", description="Đầu tư nhà đất là kênh an toàn nhất để xưng vương.", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Ai gọi lệnh người đó mua nha, đừng có bấm giành!", ephemeral=True)
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
                    options.append(discord.SelectOption(label=pet, description=f"Đang có: {quantity} con | Chợ đen thâu tóm: {get_pet_sell_price(pet):,} 💰", value=pet))
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
            if user_data.get("pets", {}).get(item_value, 0) <= 0: return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này trong chuồng!", ephemeral=True)
            sell_price = get_pet_sell_price(item_value)
            user_data["pets"][item_value] -= 1
            if user_data["pets"][item_value] == 0: del user_data["pets"][item_value]
            success_message = f"✅ Thương lái đã mang bé **{item_value}** đi.\nBạn nhận được **{sell_price:,} 💰** tiền tươi thóc thật!"
        else:
            if item_value not in user_data.get("assets", []): return await interaction.response.send_message("Lỗi: Bạn làm gì có tài sản này mà đòi đem cắm!", ephemeral=True)
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            success_message = f"✅ Chủ tiệm cầm đồ đã thâu tóm **{item_value}**.\nBạn cắn răng chịu lỗ, vớt vát lại được **{sell_price:,} 💰**!"

        user_data["money"] += sell_price
        save_user(user_id)
        add_history(user_id, f"Bán {item_value} cho Chợ đen (+{sell_price:,} 💰)")
        
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
            embed_err = discord.Embed(description="Bạn không có tài sản nào để bán cả! Nghèo rớt mồng tơi.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        embed = discord.Embed(title="🏷️ CẦM ĐỒ BĐS & XE CỘ", description="Lưu ý: Bạn sẽ bị con buôn ép giá tơi bời, chịu lỗ 30% giá trị so với lúc mua.", color=discord.Color.orange())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(quantity == 0 for quantity in pets.values()): 
            embed_err = discord.Embed(description="Bạn chưa đập được con Thú cưng nào để bán cả!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        embed = discord.Embed(title="🏷️ TRẠM THU MUA THÚ CƯNG", description="Thu mua thú cưng đổi lấy tiền mặt nhanh gọn lẹ. Pet càng hiếm giá càng cao.", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction): return interaction.user.id == self.author.id

class KhungRungShopView(discord.ui.View):
    def __init__(self, author, session_profit=0):
        super().__init__(timeout=60)
        self.author = author
        self.session_profit = session_profit

    @discord.ui.button(label="Gậy Gỗ Mục (50 💰)", style=discord.ButtonStyle.secondary, emoji="🪵")
    async def btn_buy_gaygo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Sếp đã mua Gậy Gỗ Mục. Tính năng đi rừng đang tiếp tục hoàn thiện!", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction): return interaction.user.id == self.author.id

class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Rủi ro thấp, phần thưởng dự kiến: ~450 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Rủi ro trung bình, phần thưởng dự kiến: ~1000 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Rủi ro cao, phần thưởng dự kiến: ~2000 💰", emoji="🏛️", value="12")
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

        embed_success = discord.Embed(title="⛺ LÊN ĐƯỜNG BÌNH AN!", description=f"Hành lý đã chuẩn bị xong. Bạn vác balo tiến vào rừng và bắt đầu cắm trại **{hours} giờ**.\n\n⏳ Khi nào hết thời gian, hãy gõ lại lệnh `k phai` để thu hoạch chiến lợi phẩm mang về nhé.", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed_success, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user.id == self.author.id
    class NhanSinhGameView(discord.ui.View):
        def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        self.ev = random.choice(EVENTS_P1)

        if self.stats["may_man"] >= 8: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng, bố mẹ là tài phiệt ác ma.")
        elif self.stats["may_man"] >= 4: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức bình dân êm ấm.")
        else: self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài bãi rác từ nhỏ.")

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
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng xen vào cuộc đời của người khác!", ephemeral=True)
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
        log_entry = f"🎲 Tỉ lệ thành công: **{final_rate:.1f}%** (Xúc xắc: {roll:.1f})\n{status_icon}: {result_msg} ({money_change:,} 💰)"
        
        if self.phase == 1: tuoi_hien_tai = 15
        elif self.phase == 2: tuoi_hien_tai = 25
        elif self.phase == 3: tuoi_hien_tai = 35
        elif self.phase == 4: tuoi_hien_tai = 50
        else: tuoi_hien_tai = 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Bạn chọn con đường {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời luân hồi khép lại sớm.**")
            self.phase = 99
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Bạn chọn con đường {letter}.\n{log_entry}")
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH", description=f"Ký chủ luân hồi: {self.author.mention}", color=discord.Color.teal())
        stats_text = f"Tâm linh / May mắn: **{self.stats['may_man']}/10** *(Được buff +{self.stats['may_man']*1.5}% Tỉ lệ)*"
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
            
            embed.add_field(name=f"❓ Ngã rẽ quyết định tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.btn_a.disabled = True; self.btn_b.disabled = True; self.btn_c.disabled = True; self.btn_d.disabled = True
            self.clear_items() 
            
            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

            user_data = load_user(user_id)
            user_data["money"] += self.tien_an
            save_user(user_id)
            add_history(user_id, f"Kết thúc Nhân Sinh ({'+' if self.tien_an >=0 else ''}{self.tien_an:,} 💰)")

            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại một đống nợ khổng lồ, chủ nợ đến siết nhà.\n❌ **BÁO NHÀ!** Khoản nợ phải gánh: **{self.tien_an:,} 💰**", inline=False)
            elif self.tien_an >= 500000:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa vinh hoa, con cháu kính trọng.\n👑 **TỶ PHÚ ĐỜI THẬT!** Di sản để lại: **+{self.tien_an:,} 💰**", inline=False)
            else:
                embed.color = discord.Color.blue()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Một cuộc đời êm ấm trôi qua, không còn gì nuối tiếc.\n💼 **DƯ DẢ!** Di sản để lại: **+{self.tien_an:,} 💰**", inline=False)

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

class SoloOTTGame(discord.ui.View):
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1; self.player_2 = player_2; self.bet_amount = bet_amount
        self.msg = None; self.choices = {str(player_1.id): None, str(player_2.id): None}

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "🪨")
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "📄")
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "✂️")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = str(interaction.user.id)
        if user_id not in self.choices: return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Tránh ra chỗ khác, đây là trận chiến vinh dự riêng tư của hai người họ!", color=discord.Color.red()), ephemeral=True)
        if self.choices[user_id] is not None: return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Quân tử nhất ngôn! Bạn đã ra chiêu rồi!", color=discord.Color.red()), ephemeral=True)
            
        self.choices[user_id] = choice
        await interaction.response.send_message(embed=discord.Embed(description=f"🤫 Bạn đã giấu tay chọn **{choice}**. Hãy nín thở chờ đối thủ ra chiêu...", color=discord.Color.green()), ephemeral=True)

        if self.choices[str(self.player_1.id)] is not None and self.choices[str(self.player_2.id)] is not None:
            for child in self.children: child.disabled = True
            choice_1 = self.choices[str(self.player_1.id)]
            choice_2 = self.choices[str(self.player_2.id)]
            p1_data = load_user(self.player_1.id); p2_data = load_user(self.player_2.id)
            tong_thuong = self.bet_amount * 2
            
            if choice_1 == choice_2:
                ket_qua = "🤝 **HÒA NHAU!** Bất phân thắng bại, tiền cược được trả lại."
                p1_data["money"] += self.bet_amount; p2_data["money"] += self.bet_amount
            elif (choice_1 == "🪨" and choice_2 == "✂️") or (choice_1 == "📄" and choice_2 == "🪨") or (choice_1 == "✂️" and choice_2 == "📄"):
                ket_qua = f"🎉 **{self.player_1.name} ĐÃ CHIẾN THẮNG!**\nĐè bẹp đối thủ và húp trọn **{tong_thuong:,} 💰**."
                p1_data["money"] += tong_thuong
                add_history(self.player_1.id, f"Thắng PK Oẳn Tù Tì (+{tong_thuong:,} 💰)")
            else:
                ket_qua = f"🎉 **{self.player_2.name} ĐÃ CHIẾN THẮNG!**\nĐè bẹp đối thủ và húp trọn **{tong_thuong:,} 💰**."
                p2_data["money"] += tong_thuong
                add_history(self.player_2.id, f"Thắng PK Oẳn Tù Tì (+{tong_thuong:,} 💰)")
                
            save_user(self.player_1.id); save_user(self.player_2.id)
            
            embed_result = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed_result.add_field(name=self.player_1.name, value=f"Ra {choice_1}", inline=True)
            embed_result.add_field(name="VS", value="⚡", inline=True)
            embed_result.add_field(name=self.player_2.name, value=f"Ra {choice_2}", inline=True)
            embed_result.add_field(name="KẾT QUẢ CUỐI CÙNG", value=ket_qua, inline=False)
            
            await self.msg.edit(embed=embed_result, view=self)
            self.stop()

    async def on_timeout(self):
        if self.choices[str(self.player_1.id)] is None or self.choices[str(self.player_2.id)] is None:
            p1_data = load_user(self.player_1.id); p2_data = load_user(self.player_2.id)
            p1_data["money"] += self.bet_amount; p2_data["money"] += self.bet_amount
            save_user(self.player_1.id); save_user(self.player_2.id)
            try: await self.msg.edit(embed=discord.Embed(title="⏳ HẾT GIỜ KHIẾP SỢ", description="Có người nhát gan không dám ra chiêu. Trận đấu bị hủy, tiền cược đã hoàn trả!", color=discord.Color.dark_gray()), view=None)
            except Exception: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, player_1, player_2, bet_amount):
        super().__init__(timeout=60)
        self.player_1 = player_1; self.player_2 = player_2; self.bet_amount = bet_amount

    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def btn_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_2.id:
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Kèo này gạ người khác, ông chui vào đây bấm làm gì!", color=discord.Color.red()), ephemeral=True)
        
        p1_data = load_user(self.player_1.id); p2_data = load_user(self.player_2.id)
        if p1_data.get("money", 0) < self.bet_amount or p2_data.get("money", 0) < self.bet_amount:
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Lỗi! Một trong hai người đã tiêu cạn tiền trong ví, không đủ lúa để chơi ván này nữa!", color=discord.Color.red()), ephemeral=True)
        
        p1_data["money"] -= self.bet_amount; p2_data["money"] -= self.bet_amount
        save_user(self.player_1.id); save_user(self.player_2.id)

        game_view = SoloOTTGame(self.player_1, self.player_2, self.bet_amount)
        embed_game = discord.Embed(title="⚔️ PK OẲN TÙ TÌ", description=f"{self.player_1.mention} 🆚 {self.player_2.mention}\nTiền cược mỗi bên: **{self.bet_amount:,} 💰**\n\n👇 **HÃY BẤM NÚT ĐỂ CHỌN CHIÊU (Sẽ bị giấu kín)**", color=discord.Color.red())
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
            return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Người ta đang cầu hôn người khác, vô duyên đừng có bấm bậy!", color=discord.Color.red()), ephemeral=True)
            
        sender_data = load_user(self.sender.id); receiver_data = load_user(self.receiver.id)
        if sender_data.get("money", 0) < 1000000: 
            return await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ Ôi không! {self.sender.name} đã lỡ tiêu hết tiền, không đủ 1 Triệu sắm Lễ Cưới nữa rồi!", color=discord.Color.red()), ephemeral=True)
            
        sender_data["money"] -= 1000000
        sender_data["spouse"] = str(self.receiver.id)
        receiver_data["spouse"] = str(self.sender.id)
        save_user(self.sender.id); save_user(self.receiver.id)
        
        for child in self.children: child.disabled = True
            
        embed_success = discord.Embed(title="💒 KẾT HÔN THÀNH CÔNG", description=f"🎉 Pháo hoa nổ rợp trời! Xin chúc mừng hai vợ chồng {self.sender.mention} và {self.receiver.mention}!\nTừ nay các bạn đã là của nhau. Trăm năm hạnh phúc nhé!", color=discord.Color.magenta())
        embed_success.set_image(url=GIF_LINKS["marry"])
        await interaction.response.edit_message(embed=embed_success, view=self)
        self.stop()
        
    @discord.ui.button(label="Em Từ Chối", style=discord.ButtonStyle.danger, emoji="💔")
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        for child in self.children: child.disabled = True
        embed_fail = discord.Embed(description=f"💔 Quá đắng cay! Tình yêu không thể gượng ép...\n{self.receiver.mention} đã từ chối phũ phàng lời cầu hôn của {self.sender.mention}...", color=discord.Color.dark_grey())
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
        
        if target_data.get("company"): return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Bạn đã thuộc về một công ty rồi, phải thoát trước khi gia nhập chỗ mới!", color=discord.Color.red()), ephemeral=True)
        
        comp = load_company(self.comp_id)
        if not comp: return await interaction.response.send_message(embed=discord.Embed(description="⚠️ Công ty này đã tuyên bố phá sản hoặc không còn tồn tại!", color=discord.Color.red()), ephemeral=True)
        
        comp["members"][target_id] = "nhanvien"
        target_data["company"] = self.comp_id
        save_company(self.comp_id); save_user(target_id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=f"🎉 Chúc mừng! {self.target_user.mention} đã chính thức ký hợp đồng gia nhập công ty **{self.comp_name}**!", color=discord.Color.green()), view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def btn_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=discord.Embed(description=f"❌ {self.target_user.mention} đã xé bỏ hợp đồng, chê thẳng thừng lời mời của **{self.comp_name}**.", color=discord.Color.red()), view=None)

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
        # =====================================================================
# HỆ THỐNG LỆNH CÔNG TY (CHỈNH SỬA, NÂNG CẤP, PHỐT, IPO)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.send(embed=discord.Embed(title="🏢 SÀN GIAO DỊCH DOANH NGHIỆP", description="Bạn chưa có công ty.\n`k cty tao <tên công ty>` (Phí thành lập: 500,000 💰)", color=discord.Color.red()))
    
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None; save_user(user_id)
        return await ctx.send("Công ty của bạn đã phá sản từ trước rồi! Hãy dọn dẹp đống đổ nát và lập công ty mới.")
        
    my_role = comp["members"].get(user_id, "nhanvien")
    role_name = comp["roles"].get(my_role, my_role)
    atk, df = comp.get("atk_level", 1), comp.get("def_level", 1)
    
    embed_db = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed_db.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed_db.add_field(name="Sức Mạnh", value=f"⚔️ Công: Lv{atk} | 🛡️ Thủ: Lv{df}", inline=True)
    
    rep = comp.get("reputation", 100)
    rep_status = "Tốt" if rep > 80 else "Trung Bình" if rep > 50 else "Cảnh báo Đỏ"
    scandal_str = "\n🚨 **ĐANG DÍNH PHỐT! Mất 40% giá trị CK!**" if comp.get("has_scandal") else ""
    embed_db.add_field(name="Danh Tiếng", value=f"**{rep}/100** ({rep_status}){scandal_str}", inline=True)
    
    embed_db.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed_db.add_field(name="Chức vụ của bạn", value=f"**{role_name}**", inline=False)
    
    cmds = "`k cty gop <tiền>`: Đóng góp tiền túi vào quỹ công ty\n`k cty thulai`: Nhận lãi suất ngân hàng mỗi ngày\n`k cty dinhchinh`: Dập phốt, cứu giá CK\n`k cty nangcap <cong/thu>`: Tăng lực chiến\n`k daichien dotham @user`: Xem lén đối thủ\n`k cty roi`: Nộp đơn từ chức nghỉ việc"
    if my_role in ["boss", "quanly"]: cmds += "\n\n**Quyền Quản Lý:**\n`k cty tuyen @user`: Tuyển dụng nhân viên\n`k cty duoi @user`: Sa thải nhân viên"
    if my_role == "boss": cmds += "\n\n**Quyền Chủ Tịch:**\n`k cty luong <tiền>`: Rút quỹ phát lương cho toàn Cty\n`k ck ipo`: Đưa cty lên Sàn Chứng Khoán\n`k cty chucvu @user <quanly/nhanvien>`: Set role\n`k cty doitenchuc <boss/quanly/nhanvien> <Tên>`: Đổi tên hiển thị"
        
    embed_db.add_field(name="Bảng Lệnh Công Ty", value=cmds, inline=False)
    await ctx.send(embed=embed_db)

@cty.command()
async def tao(ctx, *, name: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    if user_data.get("company"): return await ctx.reply("Bạn đã ký hợp đồng với một công ty rồi! Hãy thoát ra trước khi tạo mới.", mention_author=False)
    if user_data.get("money", 0) < 500000: return await ctx.reply("⚠️ Phí đăng ký doanh nghiệp là **500,000 💰**. Cày thêm đi sếp!", mention_author=False)
    
    user_data["money"] -= 500000; user_data["company"] = user_id
    new_comp = {
        "_id": user_id, "name": name, "treasury": 0, "members": {user_id: "boss"}, 
        "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, 
        "reputation": 100, "has_scandal": False, "atk_level": 1, "def_level": 1,
        "last_interest": "2000-01-01 00:00:00", "is_ipo": False
    }
    COMPANY_CACHE[user_id] = new_comp; save_company(user_id); save_user(user_id)
    await ctx.send(embed=discord.Embed(title="🏢 KHAI TRƯƠNG HỒNG PHÁT", description=f"Cắt băng khánh thành! Chúc mừng sếp {ctx.author.mention} đã thành lập doanh nghiệp **{name}**!\n\nGõ `k cty` để mở bảng điều khiển và bắt đầu tuyển dụng.", color=discord.Color.green()))

@cty.command()
async def dinhchinh(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn chưa có công ty!")
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Chỉ Ban Giám Đốc mới được duyệt chi ngân sách truyền thông!")
    if not comp.get("has_scandal") and comp.get("reputation", 100) >= 100: return await ctx.reply("Công ty đang hoàn toàn trong sạch, không cần đính chính!")

    cost = max(100000, int(comp["treasury"] * 0.05))
    if comp["treasury"] < cost: return await ctx.reply(f"⚠️ Quỹ công ty không đủ **{cost:,} 💰** để thuê báo chí gỡ bài tẩy trắng!")

    comp["treasury"] -= cost
    comp["has_scandal"] = False
    recovered_rep = random.randint(15, 30)
    comp["reputation"] = min(100, comp.get("reputation", 50) + recovered_rep)
    save_company(comp_id)
    
    embed = discord.Embed(
        title="📰 XỬ LÝ KHỦNG HOẢNG THÀNH CÔNG", 
        description=f"Ban truyền thông đã chi **{cost:,} 💰** để dập tắt dư luận xấu!\n\n"
                    f"✅ **Đã gỡ bỏ trạng thái Phốt!** Cổ phiếu ngừng rơi.\n"
                    f"📈 Danh tiếng hồi phục: **+{recovered_rep}** (Hiện tại: {comp['reputation']}/100).", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed, mention_author=False)

@cty.command()
async def nangcap(ctx, stat: str):
    stat = stat.lower(); user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn chưa có công ty!")
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Chỉ Sếp mới được mua vũ khí!")
    
    if stat == "cong":
        current_lvl = comp.get("atk_level", 1)
        cost = current_lvl * 500000
        if comp["treasury"] < cost: return await ctx.reply(f"⚠️ Quỹ công ty không đủ **{cost:,} 💰** để nâng CÔNG lên Lv{current_lvl+1}!")
        comp["treasury"] -= cost; comp["atk_level"] = current_lvl + 1
        msg = f"⚔️ Nâng cấp CÔNG thành công lên Lv{current_lvl+1}! (Đã trừ {cost:,} 💰 từ quỹ)"
    elif stat == "thu":
        current_lvl = comp.get("def_level", 1)
        cost = current_lvl * 300000
        if comp["treasury"] < cost: return await ctx.reply(f"⚠️ Quỹ công ty không đủ **{cost:,} 💰** để nâng THỦ lên Lv{current_lvl+1}!")
        comp["treasury"] -= cost; comp["def_level"] = current_lvl + 1
        msg = f"🛡️ Nâng cấp KHIÊN THỦ thành công lên Lv{current_lvl+1}! (Đã trừ {cost:,} 💰 từ quỹ)"
    else: return await ctx.reply("⚠️ Gõ sai lệnh. Dùng `k cty nangcap cong` hoặc `k cty nangcap thu`.")
        
    save_company(comp_id)
    await ctx.reply(embed=discord.Embed(description=msg, color=discord.Color.green()), mention_author=False)

@cty.command()
async def tuyen(ctx, member: discord.Member):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply("Bạn có công ty đâu mà đòi tuyển nhân sự!", mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Quyền hạn không đủ! Chỉ Giám đốc và Chủ tịch mới được tuyển người!", mention_author=False)
    if load_user(member.id).get("company"): return await ctx.reply("Người này đang làm việc cho công ty khác rồi.", mention_author=False)
    view = CompanyInviteView(comp_id, comp["name"], member)
    await ctx.send(f"🏢 {member.mention}, bạn có một lá thư mời nhận việc tại **{comp['name']}**! Bấm nút bên dưới để quyết định.", view=view)

@cty.command()
async def duoi(ctx, member: discord.Member):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.reply("Bạn không có quyền sa thải nhân sự!", mention_author=False)
    target_id = str(member.id)
    if target_id not in comp["members"]: return await ctx.reply("Lỗi: Người này không có mặt trong danh sách công ty!", mention_author=False)
    if comp["members"][target_id] == "boss": return await ctx.reply("Tính làm phản hả? Không ai đuổi được sếp tổng đâu!", mention_author=False)
    del comp["members"][target_id]
    target_data = load_user(target_id); target_data["company"] = None
    save_company(comp_id); save_user(target_id)
    await ctx.reply(f"👢 Đóng mộc sa thải! Bộ phận Nhân sự đã đuổi cổ {member.mention} ra khỏi công ty!", mention_author=False)

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.reply("Bạn chưa gia nhập công ty nào để cống hiến.", mention_author=False)
    if user_data.get("money", 0) < amount: return await ctx.reply("Trong ví làm gì có đủ tiền mà bấm góp!", mention_author=False)
    comp = load_company(comp_id)
    user_data["money"] -= amount; comp["treasury"] += amount
    save_user(user_id); save_company(comp_id)
    await ctx.reply(f"💰 Tuyệt vời! Bạn đã cống hiến **{amount:,} 💰** vào quỹ đen của công ty. \nTổng quỹ hiện tại: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def thulai(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ đích thân Chủ tịch mới được ký giấy thu lãi ngân hàng!", mention_author=False)
    now = datetime.now()
    last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    if now - last < timedelta(days=1): return await ctx.reply("⏳ Kế toán chưa chốt sổ! Mỗi ngày công ty chỉ được thu lãi từ Ngân hàng 1 lần.", mention_author=False)
    lai_nhan_duoc = min(int(comp["treasury"] * 0.05), 100000) 
    comp["treasury"] += lai_nhan_duoc; comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    await ctx.reply(f"📈 Chốt sổ kinh doanh! Công ty đã nhận được **{lai_nhan_duoc:,} 💰** tiền lãi hôm nay. \nTổng quỹ tăng lên: **{comp['treasury']:,} 💰**.", mention_author=False)

@cty.command()
async def luong(ctx, amount: int):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Lỗi: Chỉ Chủ tịch mới được quyền ký quỹ phát lương!", mention_author=False)
    mem_count = len(comp["members"]); total_cost = amount * mem_count
    if total_cost > comp["treasury"]: return await ctx.reply(f"Quỹ không đủ! Bạn cần tới **{total_cost:,} 💰** để phát đồng đều cho {mem_count} người.", mention_author=False)
    comp["treasury"] -= total_cost
    for m_id in list(comp["members"].keys()):
        m_data = load_user(m_id); m_data["money"] += amount; save_user(m_id)
    save_company(comp_id)
    await ctx.send(embed=discord.Embed(description=f"💸 Sếp tổng đã hào phóng phát **{amount:,} 💰** lương cho mỗi nhân viên!\nTổng tiền quỹ bị trừ: **{total_cost:,} 💰**", color=discord.Color.green()))

@cty.command()
async def chucvu(ctx, member: discord.Member, role: str):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ Chủ tịch mới được set chức vụ!", mention_author=False)
    target_id = str(member.id)
    if target_id not in comp["members"]: return await ctx.reply("Người này không thuộc công ty.", mention_author=False)
    if target_id == user_id: return await ctx.reply("Không thể tự đổi chức của bản thân, sếp vẫn là sếp!", mention_author=False)
    if role not in ["quanly", "nhanvien"]: return await ctx.reply("Chức vụ bắt buộc phải là `quanly` hoặc `nhanvien`.", mention_author=False)
    comp["members"][target_id] = role; save_company(comp_id)
    await ctx.reply(f"✅ Đã quyết định thăng/giáng chức {member.mention} thành **{comp['roles'][role]}**.", mention_author=False)

@cty.command()
async def doitenchuc(ctx, role: str, *, name: str):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply("Chỉ Chủ tịch mới được quyền đổi tên chức vụ!", mention_author=False)
    if role not in ["boss", "quanly", "nhanvien"]: return await ctx.reply("Hệ phái cần đổi phải là `boss`, `quanly` hoặc `nhanvien`.", mention_author=False)
    comp["roles"][role] = name; save_company(comp_id)
    await ctx.reply(f"✅ Đã đổi tên hệ phái `{role}` thành **{name}**.", mention_author=False)

@cty.command()
async def roi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.reply("Bạn chưa gia nhập công ty nào cả!", mention_author=False)
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None; save_user(user_id)
        return await ctx.reply("Công ty của bạn đã không còn tồn tại trên hệ thống.", mention_author=False)
    my_role = comp["members"].get(user_id)
    if my_role == "boss":
        COMPANY_CACHE.pop(comp_id, None); companies_col.delete_one({"_id": comp_id})
        for m_id in list(comp["members"].keys()):
            m_data = load_user(m_id); m_data["company"] = None; save_user(m_id)
        embed_bankrupt = discord.Embed(description="🏢 Bão tố ập tới! Chủ tịch đã bỏ trốn, công ty tuyên bố **PHÁ SẢN** và giải tán toàn bộ nhân sự!", color=discord.Color.red())
        embed_bankrupt.set_image(url=GIF_LINKS.get("bankrupt", "https://media.giphy.com/media/3o6UB5RrlQuMfZp82Y/giphy.gif"))
        await ctx.reply(embed=embed_bankrupt, mention_author=False)
    else:
        if user_id in comp["members"]: del comp["members"][user_id]
        user_data["company"] = None; save_user(user_id); save_company(comp_id)
        await ctx.reply(embed=discord.Embed(description="🎒 Bạn đã nộp đơn xin từ chức, thu dọn hành lý rời khỏi công ty.", color=discord.Color.dark_grey()), mention_author=False)

@bot.command()
async def daichien(ctx, action: str = None, member: discord.Member = None, tactic: str = None):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    
    if not action or action.lower() not in ["dotham", "danh"]:
        embed_help = discord.Embed(
            title="⚔️ ĐẠI CHIẾN THƯƠNG TRƯỜNG VIP", 
            description="`k daichien dotham @user`: Tốn 50k quỹ để xem lén sức mạnh đối thủ.\n`k daichien danh @user <hack/phot/giangho>`: Tấn công công ty của họ.", 
            color=discord.Color.red()
        )
        embed_help.add_field(name="1. hack (Tấn công mạng)", value="Tỉ lệ phụ thuộc Công/Thủ\nThắng: Cướp 10% quỹ địch.\nThua: Mất 5% quỹ phe ta.", inline=False)
        embed_help.add_field(name="2. phot (Bóc phốt)", value="Tỉ lệ phụ thuộc Công/Thủ\nThắng: Gây **Scandal**, Giảm 20-40 Danh Tiếng của địch (CK rớt 40%).\nThua: Mất 5% quỹ phe ta.", inline=False)
        embed_help.add_field(name="3. giangho (Vũ lực)", value="Tỉ lệ phụ thuộc Công/Thủ\nThắng: Cướp 2% quỹ địch.\nThua: Mất 1% quỹ phe ta.", inline=False)
        embed_help.set_image(url=GIF_LINKS.get("fight", ""))
        return await ctx.send(embed=embed_help)
        
    if not member or member.bot: return await ctx.reply("⚠️ Tag một người chơi cụ thể!")
    target_id = str(member.id); target_comp_id = load_user(target_id).get("company")
    
    if not comp_id or not target_comp_id: return await ctx.reply("⚠️ Cả 2 đều phải ở trong công ty thì mới được phép PK!")
    if comp_id == target_comp_id: return await ctx.reply("⚠️ Đánh người cùng công ty làm gì!")
    
    comp1 = load_company(comp_id); comp2 = load_company(target_comp_id)
    
    if action.lower() == "dotham":
        if comp1["treasury"] < 50000: return await ctx.reply("Quỹ không đủ 50k để thuê thám tử!")
        comp1["treasury"] -= 50000; save_company(comp_id)
        embed = discord.Embed(title="🕵️ KẾT QUẢ DO THÁM", description=f"Mục tiêu: **{comp2['name']}**\n💰 Quỹ ước tính: **~{int(comp2['treasury']*random.uniform(0.8, 1.2)):,} 💰**\n🛡️ Cấp phòng thủ: **Lv{comp2.get('def_level', 1)}**", color=discord.Color.blurple())
        return await ctx.reply(embed=embed, mention_author=False)
        
    if action.lower() == "danh":
        if not tactic or tactic.lower() not in ["hack", "phot", "giangho"]: return await ctx.reply("⚠️ Chọn sai chiến thuật! Dùng `hack`, `phot`, hoặc `giangho`.")
        now = datetime.now()
        if comp_id in cty_cooldowns and (now - cty_cooldowns[comp_id]).total_seconds() < 3600: return await ctx.reply(embed=discord.Embed(description="⏳ Công ty đang nghỉ ngơi, 1 tiếng sau mới xuất quân lại được.", color=discord.Color.orange()), mention_author=False)
        if comp2["treasury"] < 10000: return await ctx.reply("⚠️ Công ty đối thủ quá nghèo, đánh không bõ!")
        
        cty_cooldowns[comp_id] = now; tactic = tactic.lower()
        if tactic == "hack": win_rate, win_pct, lose_pct, name = 30, 0.10, 0.05, "TẤN CÔNG MẠNG"
        elif tactic == "phot": win_rate, win_pct, lose_pct, name = 50, 0.05, 0.05, "THUÊ BÁO CHÍ BÓC PHỐT"
        else: win_rate, win_pct, lose_pct, name = 70, 0.02, 0.01, "ĐƯA GIANG HỒ ĐẾN ĐẬP PHÁ"
        
        atk_diff = comp1.get("atk_level", 1) - comp2.get("def_level", 1)
        final_win_rate = min(90, max(5, win_rate + (atk_diff * 5)))
        
        msg = await ctx.send(embed=discord.Embed(description=f"⚔️ **{comp1['name']}** đang dùng **{name}** lên **{comp2['name']}**...\n*(Tỉ lệ thắng: {final_win_rate}%)*", color=discord.Color.dark_grey()))
        await asyncio.sleep(2.5)
        
        if random.randint(1, 100) <= final_win_rate:
            if tactic == "phot":
                rep_dmg = random.randint(20, 40)
                comp2["reputation"] = max(0, comp2.get("reputation", 100) - rep_dmg)
                comp2["has_scandal"] = True
                save_company(target_comp_id)
                await msg.edit(embed=discord.Embed(title="🔥 LIÊN HOÀN PHỐT", description=f"Truyền thông phe bạn đã tung bằng chứng giả, bóc phốt **{comp2['name']}** bóc lột nhân viên!\n\n📉 Danh tiếng đối thủ giảm **{rep_dmg}** điểm và **dính Scandal**. Cổ phiếu địch sẽ rớt thảm hại!", color=discord.Color.red()))
            else:
                steal = int(comp2["treasury"] * win_pct)
                comp1["treasury"] += steal; comp2["treasury"] -= steal
                save_company(comp_id); save_company(target_comp_id)
                await msg.edit(embed=discord.Embed(description=f"🔥 **ĐẠI THẮNG!** Binh pháp quá đỉnh!\n💰 Phe bạn đã cướp được **{steal:,} 💰**!", color=discord.Color.green()))
        else:
            fine = int(comp1["treasury"] * lose_pct)
            comp1["treasury"] -= fine; comp2["treasury"] += fine
            save_company(comp_id); save_company(target_comp_id)
            await msg.edit(embed=discord.Embed(description=f"💀 **THẤT BẠI NHỤC NHÃ!** Kẻ địch thủ quá trâu!\nBạn đền bù **{fine:,} 💰** cho quỹ đối thủ.", color=discord.Color.red()))

# =====================================================================
# SÀN CHỨNG KHOÁN (CỔ TỨC & IPO)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    all_stocks = get_all_stocks()
    embed = discord.Embed(
        title="📈 SÀN CHỨNG KHOÁN PHỐ WALL (IPO & MẶC ĐỊNH)", 
        description=f"Giá thay đổi mỗi giờ. Công ty dính phốt rớt 40% giá trị.\n\n"
                    f"🛒 Mua: `k ck buy <MÃ> <SL>` | 💸 Bán: `k ck sell <MÃ> <SL>`\n"
                    f"🏢 Lên Sàn: `k ck ipo`", 
        color=discord.Color.blue()
    )
    for code, name in all_stocks.items():
        price_now = get_stock_price(code, 0)
        price_old = get_stock_price(code, -1)
        if price_now <= 1000: trend = "💀 ĐÁY XÃ HỘI"
        else: trend = "🟩 Lên" if price_now > price_old else "🟥 Xuống"
        
        ipo_comp = companies_col.find_one({"is_ipo": True, "name": {"$regex": f"^{code}", "$options": "i"}})
        scandal_mark = " 🚨(Phốt)" if ipo_comp and ipo_comp.get("has_scandal") else ""
        
        embed.add_field(name=f"🏢 {code} - {name}{scandal_mark}", value=f"Giá: **{price_now:,} 💰** *(Biến động: {trend})*", inline=False)
        
    my_stocks = load_user(ctx.author.id).get("stocks", {})
    inv_str = "\n".join([f"🔸 {c}: {q} CP (Giá: {get_stock_price(c)*q:,} 💰)" for c, q in my_stocks.items() if q > 0])
    embed.add_field(name="🎒 Cổ phiếu bạn nắm giữ", value=inv_str if inv_str else "Ví đầu tư trống.", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper(); all_stocks = get_all_stocks()
    if code not in all_stocks: return await ctx.reply("⚠️ Mã CK không tồn tại!")
    if qty <= 0: return await ctx.reply("⚠️ Số lượng > 0!")
        
    stock_price = get_stock_price(code)
    if stock_price <= 1000: return await ctx.reply("⚠️ Sàn khóa mua vào mã rác rưởi/hủy niêm yết!")

    total_cost = stock_price * qty
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    if user_data.get("money", 0) < total_cost: return await ctx.reply(f"⚠️ Thiếu lúa! Cần **{total_cost:,} 💰**.")
        
    user_data["money"] -= total_cost
    if total_cost >= 50000000 and random.randint(1, 100) <= 15:
        save_user(user_id); add_history(user_id, f"Bị Úp Bô CK {code} (-{total_cost:,} 💰)")
        return await ctx.reply(embed=discord.Embed(title="🚨 RUG PULL", description=f"CEO ôm **{total_cost:,} 💰** của bạn bỏ trốn! Mất trắng!", color=discord.Color.red()))
            
    user_data["stocks"][code] = user_data.get("stocks", {}).get(code, 0) + qty
    save_user(user_id); add_history(user_id, f"Mua {qty} CP {code} (-{total_cost:,} 💰)")
    await ctx.reply(embed=discord.Embed(description=f"✅ Lệnh BUY khớp! Mua **{qty} {code}** hết **{total_cost:,} 💰**.", color=discord.Color.green()))

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper(); user_id = str(ctx.author.id); user_data = load_user(user_id)
    if code not in get_all_stocks(): return await ctx.reply("⚠️ Mã CK không tồn tại!")
    if qty <= 0 or user_data.get("stocks", {}).get(code, 0) < qty: return await ctx.reply("⚠️ Không đủ cổ phiếu để bán!")
        
    total_gain = get_stock_price(code) * qty
    user_data["stocks"][code] -= qty
    if user_data["stocks"][code] == 0: del user_data["stocks"][code]
    user_data["money"] += total_gain
    save_user(user_id); add_history(user_id, f"Bán {qty} CP {code} (+{total_gain:,} 💰)")
    await ctx.reply(embed=discord.Embed(description=f"✅ Lệnh SELL khớp! Bán **{qty} {code}** thu về **{total_gain:,} 💰**.", color=discord.Color.gold()))

@chungkhoan.command()
async def ipo(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn chưa gia nhập công ty nào cả!", color=discord.Color.red()), mention_author=False)
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.reply(embed=discord.Embed(description="⚠️ Chỉ Chủ Tịch mới có quyền quyết định đưa công ty lên sàn chứng khoán!", color=discord.Color.red()), mention_author=False)
    if comp.get("is_ipo"): return await ctx.reply(embed=discord.Embed(description="⚠️ Công ty của bạn đã được niêm yết trên sàn chứng khoán rồi!", color=discord.Color.orange()), mention_author=False)
    if comp["treasury"] < 50000000: return await ctx.reply(embed=discord.Embed(description="⚠️ Điều kiện niêm yết: Quỹ công ty phải đạt tối thiểu **50,000,000 💰**.\nHãy kêu gọi cổ đông đóng góp thêm!", color=discord.Color.red()), mention_author=False)
    
    comp["is_ipo"] = True; save_company(comp_id)
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
# HỆ THỐNG NGÂN HÀNG TRUNG ƯƠNG
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    user_data = load_user(ctx.author.id)
    bank_balance = user_data.get("bank", 0)
    wallet_balance = user_data.get("money", 0)
    embed = discord.Embed(
        title="🏦 NGÂN HÀNG TRUNG ƯƠNG SERVER", 
        description="Gửi tiền an toàn tuyệt đối.\n"
                    "📥 `k bank gui <số tiền / all>`: Gửi tiền mặt vào két sắt\n"
                    "📤 `k bank rut <số tiền / all>`: Rút tiền từ két sắt ra ví\n"
                    "📈 `k bank laisuat`: Nhận lãi 0.2% mỗi ngày", 
        color=discord.Color.blue()
    )
    embed.add_field(name="💳 Ví tiền mặt (Wallet)", value=f"**{wallet_balance:,} 💰**", inline=True)
    embed.add_field(name="🏦 Số dư Két sắt (Bank)", value=f"**{bank_balance:,} 💰**", inline=True)
    embed.set_thumbnail(url=GIF_LINKS.get("bank", ""))
    await ctx.reply(embed=embed, mention_author=False)

@bank.command()
async def laisuat(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); bank_bal = user_data.get("bank", 0)
    if bank_bal < 10000: return await ctx.reply(embed=discord.Embed(description="⚠️ Ngân hàng chê! Gửi trên 10k mới được tính lãi suất nhé.", color=discord.Color.red()), mention_author=False)
    now = datetime.now()
    last = datetime.strptime(user_data.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    if now - last < timedelta(days=1):
        next_time = int((last + timedelta(days=1)).timestamp())
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Bạn đã nhận lãi hôm nay rồi. Quay lại vào: <t:{next_time}:R>", color=discord.Color.orange()), mention_author=False)
        
    interest = int(bank_bal * 0.002) 
    user_data["bank"] += interest; user_data["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id); add_history(user_id, f"Nhận lãi ngân hàng (+{interest:,} 💰)")
    await ctx.reply(embed=discord.Embed(description=f"📈 Tinh tinh! Ngân hàng đã cộng **{interest:,} 💰** (0.2%) tiền lãi vào két sắt của bạn.", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    try: 
        if amount.lower() == "all": deposit_amount = user_data["money"]
        else: deposit_amount = int(amount)
    except ValueError: return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập đúng số tiền hoặc chữ `all`!", color=discord.Color.red()), mention_author=False)
    
    if deposit_amount <= 0 or deposit_amount > user_data["money"]: return await ctx.reply(embed=discord.Embed(description="⚠️ Số tiền trong ví không đủ để gửi!", color=discord.Color.red()), mention_author=False)
    user_data["money"] -= deposit_amount; user_data["bank"] = user_data.get("bank", 0) + deposit_amount
    save_user(user_id); await ctx.reply(embed=discord.Embed(description=f"✅ Đã đóng gói **{deposit_amount:,} 💰** vào két sắt an toàn!", color=discord.Color.green()), mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    user_id = str(ctx.author.id); user_data = load_user(user_id); bank_balance = user_data.get("bank", 0)
    try: 
        if amount.lower() == "all": withdraw_amount = bank_balance
        else: withdraw_amount = int(amount)
    except ValueError: return await ctx.reply(embed=discord.Embed(description="⚠️ Nhập đúng số tiền hoặc chữ `all`!", color=discord.Color.red()), mention_author=False)
    
    if withdraw_amount <= 0 or withdraw_amount > bank_balance: return await ctx.reply(embed=discord.Embed(description="⚠️ Số dư trong ngân hàng không đủ!", color=discord.Color.red()), mention_author=False)
    user_data["bank"] -= withdraw_amount; user_data["money"] += withdraw_amount
    save_user(user_id); await ctx.reply(embed=discord.Embed(description=f"✅ Bạn đã rút **{withdraw_amount:,} 💰** ra ví!", color=discord.Color.green()), mention_author=False)

# =====================================================================
# HỆ THỐNG NÔNG TRẠI VÀ XEM LỊCH SỬ
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
    
    if not farm.get("seed"):
        embed.description = "Đất trống.\n🛒 Mua hạt: `k farm mua <lua/ngo/cachua/nhansam>`\n🌱 Trồng: `k farm trong <loại>`"
    else:
        seed_info = FARM_SEEDS[farm["seed"]]
        harvest_time = datetime.strptime(farm["plant_time"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=seed_info["time_hours"])
        if datetime.now() >= harvest_time: embed.description = f"🌾 **{seed_info['name']}** đã chín! Gõ `k farm thuhoach`"; embed.color = discord.Color.gold()
        else: embed.description = f"🌱 Đang trồng **{seed_info['name']}**.\n⏳ Thu hoạch: <t:{int(harvest_time.timestamp())}:R>"
    await ctx.reply(embed=embed)

@nongtrai.command()
async def mua(ctx, seed: str):
    seed = seed.lower()
    if seed not in FARM_SEEDS: return await ctx.reply("⚠️ Chỉ có: `lua`, `ngo`, `cachua`, `nhansam`.")
    user_id = str(ctx.author.id); user_data = load_user(user_id); cost = FARM_SEEDS[seed]["cost"]
    if user_data.get("money", 0) < cost: return await ctx.reply(f"⚠️ Thiếu lúa, cần **{cost:,} 💰**.")
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
    seed_info = FARM_SEEDS[farm["seed"]]
    harvest_time = datetime.strptime(farm["plant_time"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=seed_info["time_hours"])
    if datetime.now() < harvest_time: return await ctx.reply(f"⏳ Cây chưa chín! Chờ đến <t:{int(harvest_time.timestamp())}:R>.")
    profit = random.randint(seed_info["profit_min"], seed_info["profit_max"])
    user_data["money"] += profit; user_data["farm"] = {"seed": None, "plant_time": None}
    save_user(user_id); add_history(user_id, f"Thu hoạch {seed_info['name']} (+{profit:,})")
    await ctx.reply(embed=discord.Embed(description=f"🌾 Gặt **{seed_info['name']}** bán được **{profit:,} 💰**!", color=discord.Color.gold()))

# =====================================================================
# MINIGAME: CƯỚP BANK, ĐÀO VÀNG, VIETLOTT, CASINO, GACHA
# =====================================================================
@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    bank_bal = user_data.get("bank", 0)
    
    if bank_bal < 100000: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Bạn cần gửi ít nhất **100,000 💰** trong ngân hàng để có thông tin làm nội gián cướp két sắt!", color=discord.Color.red()), mention_author=False)
    
    if user_id in work_cooldowns and (now - work_cooldowns[user_id]).total_seconds() < 3600:
        return await ctx.reply(embed=discord.Embed(description="⏳ Bạn đang bị truy nã! Hãy đi trốn 1 tiếng nữa.", color=discord.Color.orange()), mention_author=False)
    
    work_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Bạn đang lợi dụng quyền VIP để lẻn vào két sắt ngân hàng...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= 25: 
        loot_amount = int(bank_bal * random.uniform(0.05, 0.15))
        user_data["money"] += loot_amount; save_user(user_id)
        add_history(user_id, f"Cướp Bank trót lọt (+{loot_amount:,} 💰)")
        embed_win = discord.Embed(title="🎉 PHI VỤ TRÓT LỌT!", description=f"Dựa vào thông tin VIP, bạn vơ vét được **{loot_amount:,} 💰** rồi chuồn êm!", color=discord.Color.green())
        embed_win.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed_win)
    else: 
        fine = int(bank_bal * 0.1)
        user_data["bank"] -= fine
        jail_time = now + timedelta(minutes=10)
        user_data["jail_time"] = jail_time.strftime("%Y-%m-%d %H:%M:%S")
        save_user(user_id); add_history(user_id, f"Cướp Bank xịt (Phạt trong két -{fine:,} 💰)")
        embed_lose = discord.Embed(title="🚨 BỊ CÔNG AN TÓM GỌN", description=f"**WEE WOO WEE WOO!** Đặc nhiệm tóm gọn bạn!\n❌ Ngân hàng siết nợ **{fine:,} 💰** từ két sắt của bạn.\n⛔ **BẠN BỊ TƯỚC QUYỀN CÔNG DÂN ĐẾN: <t:{int(jail_time.timestamp())}:R>**!", color=discord.Color.red())
        embed_lose.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed_lose)

@bot.command(aliases=['mine', 'daomo'])
async def daovang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_id in work_cooldowns and (now - work_cooldowns[user_id]).total_seconds() < 30:
        return await ctx.reply(embed=discord.Embed(description=f"⏳ Tay mỏi nhừ rồi sếp! Nghỉ {int(30 - (now - work_cooldowns[user_id]).total_seconds())}s nữa hẵng cuốc tiếp.", color=discord.Color.orange()), mention_author=False)
    
    if "Cuốc Chim ⛏️" not in user_data.get("assets", []):
        if user_data.get("money", 0) < 5000: return await ctx.reply(embed=discord.Embed(description="⚠️ Không đủ **5,000 💰** mua Cuốc Chim!", color=discord.Color.red()), mention_author=False)
        user_data["money"] -= 5000; user_data["assets"].append("Cuốc Chim ⛏️")
        await ctx.send(embed=discord.Embed(description="🛒 Đã tự động trừ 5k để mua **Cuốc Chim ⛏️**!", color=discord.Color.blue()))
    
    work_cooldowns[user_id] = now
    msg = await ctx.send(embed=discord.Embed(description="⛏️ Cạch... Cạch... Bạn đang vung cuốc đập đá ở hầm mỏ âm u...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2)
    
    roll = random.randint(1, 100)
    if roll <= 40: result_name, value = "Cục Đá Vô Dụng 🪨", 0
    elif roll <= 70: result_name, value = "Mảnh Sắt Vụn 🔩", random.randint(1000, 3000)
    elif roll <= 90: result_name, value = "Thỏi Vàng Ròng 🥇", random.randint(8000, 15000)
    elif roll <= 98: result_name, value = "Viên Kim Cương To Chà Bá 💎", random.randint(50000, 100000)
    else: 
        penalty = int(user_data["money"] * 0.1) if user_data["money"] > 0 else 0
        user_data["money"] -= penalty; save_user(user_id)
        add_history(user_id, f"Đào trúng bom (-{penalty:,} 💰)")
        return await msg.edit(embed=discord.Embed(description=f"💥 **BÙMMMMM!** Bạn vô tình đào trúng quả bom!\nBệnh viện đã thu viện phí **{penalty:,} 💰**!", color=discord.Color.red()))

    user_data["money"] += value; save_user(user_id)
    if value > 0: add_history(user_id, f"Đào được {result_name} (+{value:,} 💰)")
    embed_win = discord.Embed(description=f"⛏️ Chúc mừng! Bạn đào trúng: **{result_name}**\nBán được: **{value:,} 💰**", color=discord.Color.green() if value > 0 else discord.Color.light_grey())
    embed_win.set_thumbnail(url=GIF_LINKS["mine"])
    await msg.edit(embed=embed_win)

@bot.command()
async def vietlott(ctx, so: int, amount: str):
    if so < 0 or so > 99: return await ctx.reply(embed=discord.Embed(description="⚠️ Chọn số từ 00 đến 99!", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    msg = await ctx.reply(embed=discord.Embed(description=f"🎫 Bạn đã mua vé số **{so:02d}** với giá **{bet_amount:,} 💰**.\n\n🎲 Lồng cầu đang quay...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(3)
    
    ket_qua = random.randint(0, 99)
    if so == ket_qua:
        win_amount = bet_amount * 70; user_data["money"] += win_amount; save_user(user_id)
        add_history(user_id, f"Trúng Vietlott (+{win_amount:,} 💰)")
        await msg.edit(embed=discord.Embed(description=f"🎉 **TRÚNG ĐỘC ĐẮC!** Kết quả xổ số là **{ket_qua:02d}**!\n\nBạn đã trúng gấp 70 lần tiền cược, thu về **{win_amount:,} 💰**!", color=discord.Color.green()))
    else:
        add_history(user_id, f"Trượt Vietlott (-{bet_amount:,} 💰)")
        await msg.edit(embed=discord.Embed(description=f"💀 **TRẬT LẤT!** Kết quả xổ số là **{ket_qua:02d}**.\n\nChúc bạn may mắn lần sau, tờ vé số đã cắn mất của bạn **{bet_amount:,} 💰**.", color=discord.Color.red()))

@bot.command()
async def coin(ctx, amount: str):
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    embed_start = discord.Embed(description=f"🪙 Bạn tung **{bet_amount:,} 💰** lên trời...\n🔄 Đồng xu xoay tít trên không...", color=discord.Color.gold())
    embed_start.set_thumbnail(url=GIF_LINKS["casino"])
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(2) 

    if random.choice([True, False]):
        user_data["money"] += bet_amount * 2; save_user(user_id); add_history(user_id, f"Chơi Tung xu Thắng (+{bet_amount:,} 💰)")
        await msg.edit(embed=discord.Embed(description=f"🪙 **ĐỒNG XU NGỬA!**\n🎉 Chúc mừng đại gia húp trọn **{bet_amount * 2:,} 💰**!\n💳 Số dư ví hiện tại: **{user_data['money']:,} 💰**", color=discord.Color.green()))
    else:
        add_history(user_id, f"Chơi Tung xu Thua (-{bet_amount:,} 💰)")
        await msg.edit(embed=discord.Embed(description=f"🪙 **ĐỒNG XU SẤP!**\n💀 Nhờn với nhà cái à! Bay mất **{bet_amount:,} 💰**.\n💳 Số dư ví hiện tại: **{user_data['money']:,} 💰**", color=discord.Color.red()))

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    choice = choice.lower()
    if choice not in ["tai", "tài", "xiu", "xỉu"]: return await ctx.reply(embed=discord.Embed(description="⚠️ Vui lòng gõ `k taixiu tai <tiền>` hoặc `xiu`.", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    embed_start = discord.Embed(title="🎲 LẮC XÍ NGẦU CASINO", description=f"Bạn cược **{bet_amount:,} 💰** vào cửa **{choice.upper()}**.\n\nNhà cái đang lắc... 🫨", color=discord.Color.gold())
    embed_start.set_thumbnail(url=GIF_LINKS["casino"])
    msg = await ctx.reply(embed=embed_start, mention_author=False)
    await asyncio.sleep(2.5)
    
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total_score = d1 + d2 + d3
    result_type = "xiu" if total_score <= 10 else "tai"
    result_embed = discord.Embed(title="🎲 KẾT QUẢ TÀI XỈU")
    
    if choice.replace("à", "a").replace("ỉ", "i") == result_type:
        win_amt = bet_amount * 5 if d1 == d2 == d3 else bet_amount * 2
        user_data["money"] += win_amt; add_history(user_id, f"Tài Xỉu Thắng (+{win_amt - bet_amount:,} 💰)")
        result_txt = f"🔥 **BÃO {d1}-{d2}-{d3}!!! ĐẠI THẮNG GẤP 5 LẦN!**\nHúp trọn **{win_amt:,} 💰**!" if d1 == d2 == d3 else f"✅ **THẮNG RỒI!** Bạn nhận được **{win_amt:,} 💰**!"
        result_embed.color = discord.Color.green()
    else: 
        add_history(user_id, f"Tài Xỉu Thua (-{bet_amount:,} 💰)")
        result_txt = f"💀 **CẮNG RĂNG THUA!** Mất trắng **{bet_amount:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    result_embed.description = f"**[ {d1} | {d2} | {d3} ]** (Tổng điểm: {total_score} - Cửa **{result_type.upper()}**)\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=result_embed)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    valid_choices = {"bau": "🥒", "bầu": "🥒", "cua": "🦀", "tom": "🦐", "tôm": "🦐", "ca": "🐟", "cá": "🐟", "ga": "🐓", "gà": "🐓", "huou": "🦌", "hươu": "🦌"}
    choice_clean = choice.lower()
    if choice_clean not in valid_choices: return await ctx.reply(embed=discord.Embed(description="⚠️ Tên con vật sai! Các cửa gồm: `bau, cua, tom, ca, ga, huou`.", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    user_icon = valid_choices[choice_clean]
    embed_start = discord.Embed(title="🎲 BẦU CUA TÔM CÁ", description=f"Bạn cược **{bet_amount:,} 💰** vào ô **{user_icon}**.\n\nNhà cái đang xóc dĩa... 🫨", color=discord.Color.gold())
    embed_start.set_thumbnail(url=GIF_LINKS["casino"])
    msg = await ctx.reply(embed_start, mention_author=False)
    await asyncio.sleep(2.5)
    
    dice_faces = ["🥒", "🦀", "🦐", "🐟", "🐓", "🦌"]
    dice_result = [random.choice(dice_faces) for _ in range(3)]
    match_count = dice_result.count(user_icon)
    result_embed = discord.Embed(title="🎲 MỞ BÁT KẾT QUẢ BẦU CUA")
    
    if match_count > 0: 
        win_amt = bet_amount + (bet_amount * match_count)
        user_data["money"] += win_amt; add_history(user_id, f"Bầu Cua Thắng (+{win_amt - bet_amount:,} 💰)")
        result_txt = f"🎉 **TRÚNG {match_count} Ô!** Nhà cái đền cho bạn **{win_amt:,} 💰**."
        result_embed.color = discord.Color.green()
    else: 
        add_history(user_id, f"Bầu Cua Thua (-{bet_amount:,} 💰)")
        result_txt = f"💀 **TRẬT LẤT!** Nhà cái hốt trọn **{bet_amount:,} 💰**."
        result_embed.color = discord.Color.red()
    
    save_user(user_id)
    result_embed.description = f"**[ {dice_result[0]} | {dice_result[1]} | {dice_result[2]} ]**\n\n{result_txt}"
    result_embed.set_footer(text=f"Số dư ví: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=result_embed)

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    choice = choice.lower()
    if choice not in animals: return await ctx.reply(embed=discord.Embed(description="⚠️ Chọn sai con vật! Các cửa cược: `heo`, `cho`, `ngua`, `chuot`.", color=discord.Color.red()), mention_author=False)
    user_data, bet_amount = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id); user_data["money"] -= bet_amount; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    track_length = 20; positions = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def generate_track_frame():
        frame_text = f"🏇 **ĐƯỜNG ĐUA THÚ MỞ BÁT!**\nBạn cược {bet_amount:,} 💰 vào con {animals[choice]}\n\n"
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
        final_text = f"\n🏆 **{winner} ĐÃ VỀ NHẤT!** Quá đỉnh, ăn được gấp 3 lần tiền cược: **{bet_amount * 3:,} 💰**!"
    else:
        add_history(user_id, f"Đua thú Thua (-{bet_amount:,} 💰)")
        final_text = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} của bạn xịt rồi. Mất sạch **{bet_amount:,} 💰**."
        
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
    embed.set_thumbnail(url=GIF_LINKS["casino"])
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    for _ in range(3): embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Máy đang quay tít mù..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    for _ in range(2): embed.description = f"**[ {slots_result[0]} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đã chốt ô đầu tiên..."; await msg.edit(embed=embed); await asyncio.sleep(0.8)
    for _ in range(2): embed.description = f"**[ {slots_result[0]} | {slots_result[1]} | {random.choice(items)} ]**\n\n🔄 Nín thở chờ ô cuối..."; await msg.edit(embed=embed); await asyncio.sleep(1)
        
    if slots_result[0] == slots_result[1] and slots_result[1] == slots_result[2]:
        if slots_result[0] == "👑": win_amt = bet_amount * 50
        elif slots_result[0] == "💎": win_amt = bet_amount * 20
        else: win_amt = bet_amount * 10
        result_text = f"🔥 **JACKPOT!!! ĐẠI NỔ HŨ!** Trúng 3 ô {slots_result[0]}\nBạn húp trọn **{win_amt:,} 💰**!"
        user_data["money"] += win_amt; add_history(user_id, f"Nổ Hũ (+{win_amt:,} 💰)")
    elif slots_result[0] == slots_result[1] or slots_result[1] == slots_result[2] or slots_result[0] == slots_result[2]:
        win_amt = bet_amount * 2
        result_text = f"🎉 **THẮNG NHỎ!** Trúng 2 ô giống nhau.\nBạn nhận được **{win_amt:,} 💰**."
        user_data["money"] += win_amt; add_history(user_id, f"Máy Xèng Thắng (+{win_amt - bet_amount:,} 💰)")
    else:
        result_text = f"💀 **TOANG!** Cờ bạc là bác thằng bần.\nMất sạch **{bet_amount:,} 💰**."
        add_history(user_id, f"Máy Xèng Thua (-{bet_amount:,} 💰)")
        
    save_user(user_id)
    embed.description = f"**[ {slots_result[0]} | {slots_result[1]} | {slots_result[2]} ]**\n\n{result_text}"
    embed.set_footer(text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); cost = 30000
    if user_data.get("money", 0) < cost: return await ctx.reply(embed=discord.Embed(description="⚠️ Trứng Gacha cao cấp giá 30k lận. Đi cày thêm đi sếp!", color=discord.Color.red()), mention_author=False)
        
    user_data["money"] -= cost; save_user(user_id)
    embed_start = discord.Embed(title="🥚 ĐẬP TRỨNG GACHA", description=f"{ctx.author.mention} đang vung búa đập vỡ lớp vỏ quả trứng...", color=discord.Color.orange())
    embed_start.set_image(url=GIF_LINKS["gacha"])
    msg = await ctx.reply(embed_start, mention_author=False)
    await asyncio.sleep(1.5)
    
    embed_start.description = "⚡ Vỏ trứng nứt rạn... Một ánh sáng chói lóa phát ra..."
    await msg.edit(embed=embed_start)
    await asyncio.sleep(1.5)
    
    roll = random.uniform(0, 100)
    if roll <= 0.5: rarity, title_text, embed_color = "mythic", "🌌 THẦN THOẠI", discord.Color.dark_purple()
    elif roll <= 3.0: rarity, title_text, embed_color = "legendary", "👑 HUYỀN THOẠI", discord.Color.gold()
    elif roll <= 10.0: rarity, title_text, embed_color = "epic", "🔮 SỬ THI", discord.Color.magenta()
    elif roll <= 30.0: rarity, title_text, embed_color = "rare", "💎 HIẾM", discord.Color.blue()
    else: rarity, title_text, embed_color = "common", "🪵 PHỔ THÔNG", discord.Color.light_grey()
    
    pet_name = random.choice(PET_RATES[rarity]["pool"])
    user_data["pets"][pet_name] = user_data["pets"].get(pet_name, 0) + 1
    save_user(user_id); add_history(user_id, f"Quay Gacha ra {pet_name}")
    
    embed_result = discord.Embed(title=f"🎉 NỔ TRỨNG: PHẨM CHẤT {title_text}!", description=f"Tuyệt vời! Ánh sáng tan đi, bạn nhận được một bé: **{pet_name}**!", color=embed_color)
    embed_result.set_footer(text="Gõ lệnh 'k tuido' để ngắm, lệnh 'k ban' để bán.", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed_result)

# =====================================================================
# GAME MA SÓI (1 ĐÊM)
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
    await ctx.send(f"🐺 {ctx.author.mention} đã tạo phòng Ma Sói! Gõ `k masoi join` để tham gia. Khi đủ người, host gõ `k masoi start`.")

@masoi.command()
async def join(ctx):
    server_id = str(ctx.guild.id)
    if server_id not in werewolf_lobbies: return await ctx.send("Chưa có phòng nào. Gõ `k masoi tao` trước.")
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
    if ctx.author != lobby["host"]: return await ctx.send("Chỉ chủ phòng mới được bắt đầu game!")
    players = lobby["players"]
    if len(players) < 3: return await ctx.send("Cần ít nhất 3 người để chơi!")
    
    lobby["status"] = "playing"; random.shuffle(players)
    wolf = players[0]; seer = players[1]
    lobby["roles"][str(wolf.id)] = "Wolf"; lobby["roles"][str(seer.id)] = "Seer"
    for p in players[2:]: lobby["roles"][str(p.id)] = "Villager"
    
    await ctx.send("🌙 **ĐÊM BUÔNG XUỐNG LÀNG LÁCH...**\nBot đang gửi tin nhắn bí mật cho từng người. Hãy kiểm tra DM của bạn!")
    try:
        await wolf.send("🐺 **Bạn là MA SÓI!** Đêm nay bạn sẽ cắn chết 1 người chơi. Cố gắng không bị treo cổ vào ngày mai!")
        target = random.choice([p for p in players if p != seer])
        is_wolf = "LÀ SÓI" if target == wolf else "LÀ DÂN"
        await seer.send(f"🔮 **Bạn là TIÊN TRI!** Bạn soi vào quả cầu pha lê và thấy: **{target.name} {is_wolf}**!")
        for p in players[2:]: await p.send("🧑 **Bạn là DÂN LÀNG!** Hãy cố gắng tìm ra Sói vào sáng mai nhé.")
    except Exception:
        del werewolf_lobbies[server_id]; return await ctx.send("Lỗi: Không thể DM cho người chơi (Có người chặn tin nhắn người lạ). Đã hủy phòng!")
        
    await asyncio.sleep(10)
    await ctx.send("☀️ **TRỜI ĐÃ SÁNG!**\nMọi người tỉnh dậy và thấy có dấu vết sói trong làng.\n⏰ Các bạn có 60 giây để tranh luận và bấm nút Vote để treo cổ 1 người!")
    view = MaSoiVoteView(lobby)
    msg = await ctx.send("👇 **BẢNG VOTE HÀNH QUYẾT**", view=view)
    await asyncio.sleep(60)
    
    votes = lobby["votes"]
    if not votes: await ctx.send("Kết quả: Không ai bị treo cổ. 🐺 SÓI ĐÃ CHIẾN THẮNG vì còn sống sót!")
    else:
        vote_counts = {}
        for target_id in votes.values(): vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        max_votes = max(vote_counts.values())
        hanged_ids = [k for k, v in vote_counts.items() if v == max_votes]
        
        if len(hanged_ids) > 1: await ctx.send("Kết quả: Bầu phiếu hòa! Không ai bị hành quyết.\n🐺 SÓI ĐÃ CHIẾN THẮNG vì còn sống sót!")
        else:
            hanged_id = hanged_ids[0]
            if hanged_id == str(wolf.id): await ctx.send(f"💀 Làng đã thống nhất treo cổ <@{hanged_id}>.\n🎉 Hắn ta chính là **MA SÓI**! Làng đã bình yên. **DÂN LÀNG CHIẾN THẮNG!**")
            else: await ctx.send(f"💀 Làng đã thống nhất treo cổ <@{hanged_id}>.\n❌ Ôi không, hắn chỉ là Dân Thường! 🐺 Sói {wolf.mention} ôm bụng cười trong đêm. **SÓI CHIẾN THẮNG!**")
    if server_id in werewolf_lobbies: del werewolf_lobbies[server_id]

# =====================================================================
# CÁC LỆNH INFO, HELP, TOP VÀ GIAO DỊCH
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH BOT UPDATE VIP 6.0", description="Tiền tố gọi lệnh là `k` hoặc `K` (Ví dụ: `k rank`).", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.add_field(name="🏦 KINH TẾ VIP", value="`k rank` • Thẻ Căn Cước\n`k bank` • Gửi/Rút Két sắt\n`k marry @user` • Kết hôn\n`k cuahang`, `k choden` • Mua bán\n`k daily`, `k lixi`, `k give`, `k top`, `k ls`", inline=False)
    embed.add_field(name="🏢 CÔNG TY & CHỨNG KHOÁN", value="`k cty tao <tên>` • Lập cty 500k\n`k cty` • Mở Dashboard Cty\n`k daichien @user <hack/phot/giangho>`\n`k ck` • Sàn chứng khoán", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <tài/xỉu> <tiền>`\n`k baucua <con vật> <tiền>`\n`k duathu <con vật> <tiền>`\n`k nohu <tiền>`, `k vietlott <số> <tiền>`", inline=False)
    embed.add_field(name="⛏️ NHẬP VAI SINH TỒN", value="`k farm` • Nông trại\n`k masoi` • Game Ma Sói\n`k cuopnganhang` • Cướp nhà băng\n`k daovang` • Nghề đào mỏ\n`k nhansinh` • Mô phỏng cuộc sống\n`k thamhiem`, `k gacha`, `k phai`", inline=False)
    embed.set_footer(text="Chúc các dân chơi sớm mua được Đảo Tư Nhân!", icon_url=ctx.author.display_avatar.url)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def rank(ctx):
    user_data = load_user(ctx.author.id)
    level = user_data.get("level", 1); xp = user_data.get("xp", 0); tien = user_data.get("money", 0)
    embed_color = discord.Color.gold() if tien > 1000000 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 CĂN CƯỚC CÔNG DÂN: {ctx.author.name.upper()}", color=embed_color)
    embed.set_thumbnail(url=GIF_LINKS["rank"])
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{user_data.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {level}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{user_data.get('bank', 0):,} 💰**", inline=True)
    
    if user_data.get("spouse"):
        try: spouse_name = (await bot.fetch_user(int(user_data["spouse"]))).name
        except Exception: spouse_name = "Người thương ẩn danh"
        embed.add_field(name="💍 Tình Trạng Hôn Nhân", value=f"**Đã kết hôn với {spouse_name}**", inline=False)
        
    if user_data.get("company"): 
        comp_info = load_company(user_data['company'])
        if comp_info: embed.add_field(name="🏢 Doanh Nghiệp", value=f"**{comp_info['name']}**{' (Đã lên sàn CK)' if comp_info.get('is_ipo') else ''}", inline=False)
            
    if user_data.get("jail_time"): embed.add_field(name="🚨 Trạng Thái Pháp Lý", value="**Đang bóc lịch trong trại giam!**", inline=False)
    embed.add_field(name="✨ Tiến Độ Kinh Nghiệm", value=f"`{make_progress_bar(xp, level * 100)}`\n**{xp}/{level * 100} XP**", inline=False)
    assets = user_data.get('assets', [])
    embed.set_footer(text=f"BĐS Sở hữu: {', '.join(assets[:2])}..." if assets else "Gia cảnh: Vô Gia Cư", icon_url=ctx.author.display_avatar.url)
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
    danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
    desc = ""
    for index, (uid, tien) in enumerate(danh_sach[:10]):
        user = bot.get_user(int(uid))
        try: 
            if not user: user = await bot.fetch_user(int(uid))
        except Exception: pass
        ten = user.name if user else f"Tỷ phú {uid[-4:]}"
        icon = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else f"**#{index+1}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
    await ctx.send(embed=discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA SERVER", description=desc, color=discord.Color.gold()))

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_daily"):
        last_daily = datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            next_time = int((last_daily + timedelta(days=1)).timestamp())
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Lương tiếp theo nhận vào: <t:{next_time}:R>.", color=discord.Color.orange()), mention_author=False)
    
    user_data["money"] += 1000; user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    embed_success = discord.Embed(title="🎁 QUÀ ĐIỂM DANH", description=f"Nhận trợ cấp **1,000 💰** thành công!\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.green())
    embed_success.set_thumbnail(url=GIF_LINKS["daily"]); await ctx.reply(embed=embed_success, mention_author=False)

@bot.command()
async def lixi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_lixi"):
        last_lixi = datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S")
        if now - last_lixi < timedelta(hours=12):
            next_time = int((last_lixi + timedelta(hours=12)).timestamp())
            return await ctx.reply(embed=discord.Embed(description=f"🧧 Lì xì tiếp theo nhận vào: <t:{next_time}:R>.", color=discord.Color.orange()), mention_author=False)

    tien = random.randint(1000, 8000) 
    user_data["money"] += tien; user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    await ctx.reply(embed=discord.Embed(description=f"🧧 Bạn mở phong bao đỏ và nhận được **{tien:,} 💰**!\n💳 Số dư ví: **{user_data['money']:,} 💰**", color=discord.Color.red()), mention_author=False)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    nguoi_gui = str(ctx.author.id); nguoi_nhan = str(member.id); gui_data = load_user(nguoi_gui); nhan_data = load_user(nguoi_nhan)
    if amount <= 0 or gui_data.get("money", 0) < amount or nguoi_gui == nguoi_nhan: return await ctx.reply(embed=discord.Embed(description="⚠️ Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển).", color=discord.Color.red()), mention_author=False)
    gui_data["money"] -= amount; nhan_data["money"] += amount
    save_user(nguoi_gui); save_user(nguoi_nhan)
    await ctx.send(embed=discord.Embed(title="💸 CHUYỂN KHOẢN THÀNH CÔNG", description=f"{ctx.author.mention} đã chuyển cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green()))

@bot.command(aliases=['ban', 'sell'])
async def choden(ctx): 
    embed = discord.Embed(title="⚖️ CHỢ ĐEN CẦM ĐỒ", description="Đem đồ ra đây cầm cố hoặc bán thú cưng lấy tiền liền tay!", color=discord.Color.dark_orange())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=SellCategoryMenu(ctx.author))

@bot.command(aliases=['shop'])
async def cuahang(ctx): 
    embed = discord.Embed(title="🏪 ĐẠI SIÊU THỊ TRUNG TÂM", description="Nơi tiêu tiền của những kẻ giàu có!", color=discord.Color.brand_green())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command()
async def thamhiem(ctx): 
    embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ RỪNG SÂU", description="Khu rừng rậm rạp đầy nguy hiểm nhưng cũng cất giấu đầy rương vàng kho báu.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA VŨ KHÍ TỰ VỆ TRƯỚC KHI VÀO RỪNG** 👇", color=discord.Color.orange())
    await ctx.send(embed=embed, view=KhungRungShopView(ctx.author, session_profit=0))

@bot.command()
async def phai(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); exp_end_str = user_data.get("exp_end")
    if exp_end_str:
        now = datetime.now(); end_time = datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S")
        if now >= end_time:
            reward = user_data.get("exp_reward", 500); user_data["money"] += reward
            del user_data["exp_end"]; del user_data["exp_reward"]; save_user(user_id)
            return await ctx.reply(embed=discord.Embed(title="🎉 TRỞ VỀ AN TOÀN!", description=f"Bạn đã hoàn thành chuyến dã ngoại và thu hoạch được **{reward:,} 💰**!", color=discord.Color.gold()), mention_author=False)
        else:
            time_left = end_time - now; hours, remainder = divmod(int(time_left.total_seconds()), 3600); minutes, seconds = divmod(remainder, 60)
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Đang cày cuốc sấp mặt ở nơi hoang dã! Hãy chờ thêm **{hours} giờ {minutes} phút** nữa nhé.", color=discord.Color.orange()), mention_author=False)
    embed_start = discord.Embed(title="⛺ TRẠM THÁM HIỂM AFK", description="Gửi nhân vật đi treo máy dã ngoại và nhặt tiền lúc trở về!\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ CHỌN KHU VỰC CẮM TRẠI** 👇", color=discord.Color.dark_green())
    await ctx.send(embed=embed_start, view=ExpView(ctx.author))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id); now = datetime.now()
    if user_id in dang_choi_nhansinh: return await ctx.reply(embed=discord.Embed(description="⏳ Đang trong một kiếp luân hồi dở dang rồi, hoàn thành kiếp trước đi đã!", color=discord.Color.orange()), mention_author=False)
    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5: return await ctx.reply(embed=discord.Embed(description="⏳ Từ từ đã, đầu thai liên tục Diêm Vương mắng cho đấy!", color=discord.Color.orange()), mention_author=False)
    user_data = load_user(user_id)
    if user_data.get("money", 0) < 100: return await ctx.reply(embed=discord.Embed(description="⚠️ Vé luân hồi đi chuyến tàu địa phủ giá **100 💰**.", color=discord.Color.red()), mention_author=False)

    user_data["money"] -= 100; nhansinh_cooldowns[user_id] = now; dang_choi_nhansinh.append(user_id); save_user(user_id)
    initial_stats = {"may_man": random.randint(1, 10)}; view = NhanSinhGameView(ctx.author, initial_stats)
    
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH (HARDCORE)", description=f"Ký chủ luân hồi: {ctx.author.mention}", color=discord.Color.teal())
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{initial_stats['may_man']}/10** *(Buff thêm {initial_stats['may_man']*1.5}% Tỉ lệ)*", inline=False)
    embed.add_field(name="📜 Hành trình cuộc đời", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Ngã rẽ quyết định tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    await ctx.reply(embed=embed, view=view, mention_author=False)

# =====================================================================
# SỰ KIỆN HỆ THỐNG LÕI CỦA BOT VÀ KHỞI CHẠY (GHI NGUYÊN TOKEN GỐC)
# =====================================================================
@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = str(message.author.id); user_data = load_user(user_id)
    
    if user_data.get("jail_time") and datetime.now() < datetime.strptime(user_data["jail_time"], "%Y-%m-%d %H:%M:%S"):
        return await bot.process_commands(message)
            
    user_data["xp"] += random.randint(5, 15)
    max_xp_required = user_data.get("level", 1) * 100
    
    if user_data["xp"] >= max_xp_required:
        user_data["xp"] -= max_xp_required; user_data["level"] += 1
        reward = user_data["level"] * 150; user_data["money"] += reward
        add_history(user_id, f"Thăng cấp Lv{user_data['level']} (+{reward:,} 💰)")
        try: await message.channel.send(embed=discord.Embed(description=f"🎉 **{message.author.mention}** đã đột phá lên **Cấp độ {user_data['level']}**!\nThưởng: **{reward:,} 💰**", color=discord.Color.gold()))
        except Exception: pass
            
    save_user(user_id)
    await bot.process_commands(message)

@bot.event
async def on_ready(): 
    print('================================================')
    print(f'>>> SIÊU BOT {bot.user} ĐÃ SẴN SÀNG CÀN QUÉT!')
    print('>>> FULL CODE UNCESORED (NÔNG TRẠI, MA SÓI, CTY)')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="Mô phỏng Kinh Tế | k help"))

# =====================================================================
# LỆNH ADMIN (QUẢN TRỊ VIÊN) VÀ BƠM TIỀN
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
    if not mentions: return await ctx.send(embed=discord.Embed(description="⚠️ Vui lòng tag các kênh. VD: `k setup #chat`", color=discord.Color.red()))
    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids
    await ctx.send(embed=discord.Embed(description=f"✅ Bot CHỈ nhận lệnh tại: {', '.join(c.mention for c in mentions)}", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount > 0: 
        user_id = str(member.id); user_data = load_user(user_id)
        user_data["money"] += amount; save_user(user_id)
        add_history(user_id, f"Được Admin bơm (+{amount:,} 💰)")
        await ctx.send(embed=discord.Embed(description=f"✅ Bơm thành công cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount > 0: 
        user_id = str(member.id); user_data = load_user(user_id)
        user_data["money"] -= amount; save_user(user_id)
        await ctx.send(embed=discord.Embed(description=f"⚖️ Admin đã tước đoạt **{amount:,} 💰** từ tài khoản của {member.mention}!", color=discord.Color.red()))

# =====================================================================
# KHỞI ĐỘNG SERVER 24/7 VÀ CHẠY BOT BẰNG TOKEN CỦA SẾP
# =====================================================================
keep_alive() 

TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
