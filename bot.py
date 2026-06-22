import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
from datetime import datetime, timedelta 
import pymongo 

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

# --- QUẢN LÝ TRẠNG THÁI ---
gamble_cooldowns = {} 
nhansinh_cooldowns = {} 
dang_choi_nhansinh = [] 
cty_cooldowns = {}

# =====================================================================
# KẾT NỐI MONGODB VÀ BỘ ĐỆM
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
        doc = users_col.find_one({"_id": user_id})
        DB_CACHE[user_id] = doc if doc else {}
    
    defaults = {"xp": 0, "level": 1, "money": 0, "title": "Dân Nghèo 🚶", "assets": [], "pets": {}, "company": None, "stocks": {}, "jail_time": None}
    for key, value in defaults.items():
        if key not in DB_CACHE[user_id]: DB_CACHE[user_id][key] = value
    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE: users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

def load_server_config(server_id):
    server_id = str(server_id)
    if server_id not in CONFIG_CACHE:
        doc = config_col.find_one({"_id": server_id})
        CONFIG_CACHE[server_id] = doc if doc else {}
    return CONFIG_CACHE[server_id]

def load_company(comp_id):
    comp_id = str(comp_id)
    if comp_id not in COMPANY_CACHE:
        doc = companies_col.find_one({"_id": comp_id})
        if doc: COMPANY_CACHE[comp_id] = doc
        else: return None
    return COMPANY_CACHE[comp_id]

def save_company(comp_id):
    comp_id = str(comp_id)
    if comp_id in COMPANY_CACHE: companies_col.update_one({"_id": comp_id}, {"$set": COMPANY_CACHE[comp_id]}, upsert=True)

@bot.check
async def global_jail_check(ctx):
    if ctx.author.guild_permissions.administrator or ctx.command.name == "help": return True
    user_data = load_user(ctx.author.id)
    jt = user_data.get("jail_time")
    if jt:
        jail_end = datetime.strptime(jt, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            h, r = divmod(int((jail_end - datetime.now()).total_seconds()), 3600); m, s = divmod(r, 60)
            await ctx.send(f"🚨 **BÁO ĐỘNG!** {ctx.author.mention} đang bóc lịch trong tù do đi cướp nhà băng!\nHãy rèn luyện đạo đức thêm **{m} phút {s} giây** nữa mới được dùng bot.")
            return False
        else:
            user_data["jail_time"] = None; save_user(ctx.author.id)
            
    config = load_server_config(ctx.guild.id) if ctx.guild else {}
    allowed = config.get("allowed_channels", [])
    if allowed and ctx.channel.id not in allowed: return False
    return True

def make_progress_bar(current, total, length=10):
    progress = int((current / total) * length)
    return "█" * progress + "░" * (length - progress)

async def check_gamble_conditions(ctx, amount_str):
    user_id = str(ctx.author.id); now = datetime.now()
    if user_id in gamble_cooldowns and (now - gamble_cooldowns[user_id]).total_seconds() < 4:
        await ctx.send(f"⏳ Cờ bạc từ từ thôi! Đợi {int(4 - (now - gamble_cooldowns[user_id]).total_seconds())}s nữa nhé!"); return None, None
    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        if user_data.get("money", 0) < 0: return await ctx.send("Tài khoản đang **NỢ** mà dám vào casino à? Cày `k daily` trả nợ ngay!"), None
        else: return await ctx.send("Túi rỗng tếch mà đòi cá cược! Điểm danh đi."), None
    tien_hien_tai = user_data["money"]
    try: bet = tien_hien_tai if amount_str.lower() == "all" else int(amount_str)
    except: await ctx.send("Số cược không hợp lệ!"); return None, None
    if bet <= 0 or bet > tien_hien_tai: await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai:,} 💰**."); return None, None
    if bet > 500000: await ctx.send("⚠️ Sòng bài quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé."); return None, None
    return user_data, bet

# =====================================================================
# DỮ LIỆU GAME (Đầy đủ chi tiết)
# =====================================================================
EVENTS_P1 = [
    {"q": "Tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", "choices": [{"text": "Đem nộp lên công an", "rate": 80, "win": "Chủ ví là tổng tài, hậu tạ bạn món tiền lớn.", "lose": "Bị giam ở phường viết bản tường trình 3 ngày.", "tien_w": 2500, "tien_l": -100}, {"text": "Bỏ túi xài luôn", "rate": 20, "win": "Không ai biết, bạn bao lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường gấp đôi và bị đuổi học.", "tien_w": 3000, "tien_l": -8000}, {"text": "Lấy tờ 500k rồi vứt lại ví", "rate": 40, "win": "Trót lọt, bạn nạp game lên VIP.", "lose": "Chủ nhân báo mất, bị tra hỏi phạt nặng.", "tien_w": 1000, "tien_l": -4000}, {"text": "Giả vờ không thấy", "rate": 95, "win": "Thong thả đi học tiếp, chẳng rước họa vào thân.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn.", "tien_w": 0, "tien_l": -500}]},
    {"q": "Kỳ thi cuối cấp cận kề, bạn bè rủ cúp học đi net.", "choices": [{"text": "Ở nhà ôn bài kỹ", "rate": 85, "win": "Đỗ thủ khoa, được họ hàng thưởng nóng.", "lose": "Học tài thi phận, trượt vỏ chuối.", "tien_w": 2500, "tien_l": -500}, {"text": "Đi net cày rank", "rate": 10, "win": "Gặp idol ở quán net, được kéo lên Thách Đấu và cho tiền.", "lose": "Ngủ gục trên xe tông cột điện thăng thiên.", "tien_w": 3500, "tien_l": -10000, "die_l": True}, {"text": "Làm phao mang vào", "rate": 35, "win": "Mở phao mượt mà, điểm cao chót vót.", "lose": "Giám thị bắt quả tang, đình chỉ thi 0 điểm.", "tien_w": 2000, "tien_l": -5000}, {"text": "Ngủ cho khỏe", "rate": 50, "win": "Tinh thần sảng khoái, làm bài vừa đủ đậu.", "lose": "Ngủ nhiều lú não, làm sai phép tính cơ bản 1+1=3.", "tien_w": 800, "tien_l": -1000}]}
]
EVENTS_P2 = [
    {"q": "Tích cóp được chút vốn, bạn muốn làm giàu nhanh.", "choices": [{"text": "Bắt đáy chứng khoán", "rate": 30, "win": "Cổ phiếu tím lịm! Tiền lãi mua được cả căn nhà.", "lose": "Bị chủ tịch úp bô, cổ phiếu rác hủy niêm yết.", "tien_w": 15000, "tien_l": -25000}, {"text": "Cắm sổ đỏ đánh xóc đĩa", "rate": 5, "win": "Ăn thông 10 ván! Bạn mua hẳn siêu xe Mẹc-xê-đét.", "lose": "Cháy túi, nhảy cầu kết thúc cuộc đời.", "tien_w": 80000, "tien_l": -50000, "die_l": True}, {"text": "Khởi nghiệp bún đậu mắm tôm", "rate": 60, "win": "Đông khách nườm nượp, mở 5 chi nhánh.", "lose": "Bị phốt mắm tôm có giòi, sập tiệm đền tiền.", "tien_w": 12000, "tien_l": -8000}, {"text": "Gửi tiết kiệm ngân hàng", "rate": 95, "win": "Cuộc sống bình yên, có lãi ra tiêu vặt.", "lose": "Lạm phát phi mã, tiền bốc hơi từ từ.", "tien_w": 2000, "tien_l": -1500}]}
]
EVENTS_P3 = [
    {"q": "Bất Động Sản đang sốt, cò đất rủ bạn lướt sóng phân lô bán nền.", "choices": [{"text": "Cầm nhà ngân hàng quất liền", "rate": 20, "win": "Giá đất x5 trong một đêm! Bạn thành đại gia nghìn tỷ.", "lose": "Dính bẫy lừa đảo dự án ma, ra đê ở, treo cổ tự tử.", "tien_w": 60000, "tien_l": -70000, "die_l": True}, {"text": "Mua miếng đất nhỏ vùng ven", "rate": 55, "win": "Chính phủ mở đường qua, đất nhân 3 giá trị.", "lose": "Đất dính quy hoạch mỏ đá, bán không ai mua.", "tien_w": 15000, "tien_l": -10000}, {"text": "Mở lớp dạy làm giàu từ BĐS", "rate": 40, "win": "Lùa được đàn gà đông đảo, thu học phí ngập mồm.", "lose": "Bị học viên bóc phốt úp sọt, đánh nhập viện.", "tien_w": 12000, "tien_l": -15000}, {"text": "Không quan tâm, lo giữ gia đình", "rate": 95, "win": "Nhà cửa êm ấm, vợ/chồng con cái hạnh phúc.", "lose": "Kinh tế khó khăn, đôi lúc cãi nhau vì tiền điện nước.", "tien_w": 3000, "tien_l": -1500}]}
]
EVENTS_P4 = [
    {"q": "Bước vào tuổi 50, bạn rơi vào khủng hoảng tuổi trung niên trầm trọng.", "choices": [{"text": "Bán nhà mua siêu xe Mẹc G63", "rate": 15, "win": "Chiến thắng giải đua không chuyên, nổi đình đám ăn quảng cáo.", "lose": "Đạp nhầm chân ga tông xe tải, thăng thiên tại chỗ.", "tien_w": 35000, "tien_l": -40000, "die_l": True}, {"text": "Sưu tầm Lan Đột Biến", "rate": 35, "win": "Bán chậu lan giá trên trời cho tỷ phú.", "lose": "Thị trường sập, ôm nhánh cỏ khô lỗ chổng vó.", "tien_w": 25000, "tien_l": -20000}, {"text": "Cặp Sugar Baby cho hồi xuân", "rate": 25, "win": "Nuôi êm thấm, tâm hồn trẻ lại phơi phới.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, mất sạch tài sản.", "tien_w": 2000, "tien_l": -50000}, {"text": "Tập Thiền, dọn về quê nuôi cá", "rate": 90, "win": "Tâm hồn thanh tịnh, khí huyết lưu thông.", "lose": "Về quê bị muỗi vằn chích sốt xuất huyết.", "tien_w": 5000, "tien_l": -3000}]}
]
EVENTS_P5 = [
    {"q": "Chạm mốc 70 tuổi, một nhà sư bảo bạn sắp tới số.", "choices": [{"text": "Vung tiền mua Linh Đan Tu Tiên", "rate": 5, "win": "Kỳ tích! Bạn cải lão hoàn đồng thành thanh niên 20 tuổi!", "lose": "Uống nhầm thủy ngân, nội tạng nát vụn thăng thiên sớm.", "tien_w": 200000, "tien_l": -20000, "die_l": True}, {"text": "Lập di chúc chia đều tài sản", "rate": 75, "win": "Con cháu hòa thuận, tổ chức mừng thọ linh đình.", "lose": "Con cháu chê ít, đánh nhau mẻ đầu, bạn tức quá đột tử.", "tien_w": 5000, "tien_l": -15000, "die_l": True}, {"text": "Quyên góp 100% làm từ thiện", "rate": 90, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền bốc hơi, bạn trầm cảm đi luôn.", "tien_w": 15000, "tien_l": -50000, "die_l": True}, {"text": "Lên Las Vegas đánh Casino lần cuối", "rate": 20, "win": "Thắng Jackpot 50 triệu đô! Lên báo quốc tế rình rang.", "lose": "Thua sạch bong, lên cơn nhồi máu cơ tim gục tại bàn.", "tien_w": 100000, "tien_l": -40000, "die_l": True}]}
]

WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "🪵 Gậy Gỗ Mục", "terrible": 25, "bad": 40, "neutral": 15, "good": 15, "great": 5, "jackpot": 0},
    "sung_cao_su": {"price": 100, "name": "🪀 Súng Cao Su", "terrible": 20, "bad": 35, "neutral": 20, "good": 20, "great": 5, "jackpot": 0},
    "kiem_sat": {"price": 200, "name": "🗡️ Kiếm Sắt Thường", "terrible": 15, "bad": 25, "neutral": 20, "good": 25, "great": 13, "jackpot": 2},
    "kiem_hiep_si": {"price": 500, "name": "⚔️ Kiếm Hiệp Sĩ", "terrible": 10, "bad": 20, "neutral": 15, "good": 30, "great": 20, "jackpot": 5},
    "riu_chien": {"price": 1000, "name": "🪓 Rìu Phá Giáp", "terrible": 10, "bad": 15, "neutral": 15, "good": 30, "great": 25, "jackpot": 5},
    "thanh_kiem": {"price": 1500, "name": "🔱 Thánh Kiếm", "terrible": 5, "bad": 10, "neutral": 10, "good": 35, "great": 30, "jackpot": 10},
    "sung_phong_luu": {"price": 3000, "name": "🚀 Súng Phóng Lựu", "terrible": 5, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 15},
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
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước hết hạn từ máy bán hàng tự động trong rừng."},
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

SHOP_ITEMS = {
    "t1": {"type": "title", "name": "Tiểu Thương 🏪", "price": 50000, "emoji": "🏷️"},
    "t2": {"type": "title", "name": "Phú Nông 🌾", "price": 200000, "emoji": "🏷️"},
    "t3": {"type": "title", "name": "Đại Gia 💸", "price": 1000000, "emoji": "🏷️"},
    "t4": {"type": "title", "name": "Tỷ Phú 💎", "price": 5000000, "emoji": "🏷️"},
    "t5": {"type": "title", "name": "Thần Tài 🧧", "price": 20000000, "emoji": "🏷️"},
    "t6": {"type": "title", "name": "Chúa Tể Vũ Trụ 🌌", "price": 100000000, "emoji": "👑"},
    "v1": {"type": "vehicle", "name": "Xe Đạp Thống Nhất 🚲", "price": 15000, "emoji": "🚲"},
    "v2": {"type": "vehicle", "name": "Wave Alpha 🛵", "price": 80000, "emoji": "🛵"},
    "v3": {"type": "vehicle", "name": "Honda SH 150i 🏍️", "price": 300000, "emoji": "🏍️"},
    "v4": {"type": "vehicle", "name": "Kia Morning 🚗", "price": 1500000, "emoji": "🚗"},
    "v5": {"type": "vehicle", "name": "Mercedes G63 🚙", "price": 8000000, "emoji": "🚙"},
    "v6": {"type": "vehicle", "name": "Lamborghini 🏎️", "price": 25000000, "emoji": "🏎️"},
    "v7": {"type": "vehicle", "name": "Phi Cơ Riêng 🛩️", "price": 80000000, "emoji": "🛩️"},
    "h1": {"type": "house", "name": "Nhà Trọ ⛺", "price": 25000, "emoji": "⛺"},
    "h2": {"type": "house", "name": "Chung Cư Mini 🏢", "price": 250000, "emoji": "🏢"},
    "h3": {"type": "house", "name": "Chung Cư Cao Cấp 🏬", "price": 1500000, "emoji": "🏬"},
    "h4": {"type": "house", "name": "Nhà Mặt Phố 🏘️", "price": 5000000, "emoji": "🏘️"},
    "h5": {"type": "house", "name": "Biệt Thự Ven Biển 🏡", "price": 20000000, "emoji": "🏡"},
    "h6": {"type": "house", "name": "Lâu Đài Cổ Tích 🏰", "price": 100000000, "emoji": "🏰"},
    "h7": {"type": "house", "name": "Đảo Tư Nhân 🏝️", "price": 500000000, "emoji": "🏝️"}
}

PET_RATES = {
    "common": {"rate": 80.0, "pool": ["Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", "Lợn Đất 🐖", "Cá Chép 🐟", "Ếch Xanh 🐸", "Chuột Đồng 🐁", "Bò Sữa 🐄"]},
    "rare": {"rate": 15.0, "pool": ["Sói Tuyết 🐺", "Gấu Bự 🐻", "Cáo Chín Đuôi 🦊", "Đại Bàng 🦅", "Báo Gấm 🐆", "Hươu Sao 🦌"]},
    "epic": {"rate": 4.0, "pool": ["Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍", "Bạch Hổ 🐅", "Cá Mập Megalodon 🦈", "Tê Giác Đất 🦏"]},
    "legendary": {"rate": 0.9, "pool": ["Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", "Phượng Hoàng Lửa 🦚", "Thủy Quái Leviathan 🐙"]},
    "mythic": {"rate": 0.1, "pool": ["Thần Long Hoàng Kim 🐲", "Hắc Ám Cự Thú 🦇", "Mèo Thần Tài Vô Cực 😻"]}
}

STOCKS = {"VIN": "Tập Đoàn VIN", "FLC": "Hàng Không FLC", "VNZ": "Công Nghệ VNZ", "DOGE": "Doge Coin"}

def get_asset_price(asset_name):
    for v in SHOP_ITEMS.values():
        if v["name"] == asset_name: return int(v["price"] * 0.7)
    return 1000

def get_pet_sell_price(pet_name):
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 5000      
            if rarity == "rare": return 15000       
            if rarity == "epic": return 100000      
            if rarity == "legendary": return 500000 
            if rarity == "mythic": return 5000000   
    return 1000

def get_stock_price(stock_code, hour_offset=0):
    t = datetime.now() + timedelta(hours=hour_offset)
    seed = int(t.strftime("%Y%m%d%H")) + sum(ord(c) for c in stock_code)
    return random.Random(seed).randint(10, 300) * 1000

# =====================================================================
# GIAO DIỆN GAME NHÂN SINH (FULL ĐẸP)
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

        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, chạy quanh nhà bằng siêu xe.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài chợ từ nhỏ.")

        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text'][:70]}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_a.callback = self.choice_a
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text'][:70]}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_b.callback = self.choice_b
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text'][:70]}", style=discord.ButtonStyle.success, custom_id="btn_c")
        self.btn_c.callback = self.choice_c
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text'][:70]}", style=discord.ButtonStyle.danger, custom_id="btn_d")
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
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời khép lại sớm.**")
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
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.teal())

        stats_text = f"May mắn ban đầu: **{self.stats['may_man']}/10** *(+ {self.stats['may_man']*2}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số tâm linh", value=stats_text, inline=False)

        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase <= 5:
            tuoi_next = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
            embed.add_field(name=f"❓ Quyết định tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.btn_c.disabled = True
            self.btn_d.disabled = True
            self.clear_items() 

            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

            total_reward = self.tien_an 
            user_data = load_user(user_id)
            user_data["money"] += total_reward
            save_user(user_id)

            if total_reward < 0:
                embed.color = discord.Color.red()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại đống nợ khổng lồ.\n❌ **BÁO NHÀ!** Khoản nợ: **{total_reward} 💰**", inline=False)
            elif total_reward >= 30000:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa.\n👑 **ĐẠI PHÚ HÀO!** Di sản để lại: **+{total_reward} 💰**", inline=False)
            else:
                embed.color = discord.Color.blue()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Cuộc đời êm ấm.\n💼 **DƯ DẢ!** Di sản để lại: **+{total_reward} 💰**", inline=False)

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{user_data['money']:,} 💰**", inline=False)

        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)

# =====================================================================
# GIAO DIỆN KHU RỪNG THÁM HIỂM (FULL ĐẸP)
# =====================================================================
class BushButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, emoji):
        super().__init__(label=label, style=style, custom_id=custom_id, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        weapon_id = view.weapon_val
        weapon_info = WEAPON_ODDS[weapon_id]
        
        for child in view.children: child.disabled = True
        await interaction.response.edit_message(content=f"🌲 {interaction.user.mention} đang cầm **{weapon_info['name']}** tiến vào bụi rậm...", view=view)
        await asyncio.sleep(2)

        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        old_money = user_data.get("money", 0)

        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [weapon_info["terrible"], weapon_info["bad"], weapon_info["neutral"], weapon_info["good"], weapon_info["great"], weapon_info["jackpot"]]
        
        category = random.choices(choices, weights=weights, k=1)[0]
        scenario = random.choice(SCENARIOS[category])
        
        if "mult" in scenario:
            thuong_phat = int(weapon_info['price'] * scenario["mult"])
        else:
            thuong_phat = scenario.get("tien", 0)
        
        user_data["money"] += thuong_phat
        actual_change = user_data["money"] - old_money
        new_session_profit = view.session_profit + actual_change
        save_user(user_id)
        
        profit_text = f"LÃI +{new_session_profit:,} 💰" if new_session_profit > 0 else f"LỖ {new_session_profit:,} 💰" if new_session_profit < 0 else "HUỀ VỐN"
        embed_color = discord.Color.green() if thuong_phat > 0 else discord.Color.red() if thuong_phat < 0 else discord.Color.light_gray()
        
        res_embed = discord.Embed(title="MỞ LÙM CÂY...", description=f"**{scenario['msg']}**", color=embed_color)
        
        if thuong_phat > 0: res_embed.add_field(name="Thu Hoạch", value=f"📈 **+{thuong_phat:,} 💰**", inline=True)
        elif thuong_phat < 0: res_embed.add_field(name="Thua Lỗ", value=f"📉 **{thuong_phat:,} 💰**", inline=True)
        else: res_embed.add_field(name="Kết Quả", value="➖ **Trắng tay**", inline=True)
            
        res_embed.add_field(name="Tổng Kết Phiên", value=f"📊 **{profit_text}**", inline=True)
        res_embed.set_footer(text=f"Số dư: {user_data['money']:,} 💰", icon_url=interaction.user.display_avatar.url)
        
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
        btn_dung = discord.ui.Button(label="Dừng lại", style=discord.ButtonStyle.danger, emoji="🛑")
        btn_dung.callback = self.stop_explore
        self.add_item(btn_dung)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Hàng của người ta, cấm nhặt hôi!", ephemeral=True)
            return False
        return True

    async def continue_explore(self, interaction: discord.Interaction):
        shop_embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ THÁM HIỂM 🛒", description="Chọn vũ khí để bắt đầu chuyến đi mới.\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA** 👇", color=discord.Color.orange())
        if self.session_profit > 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LÃI +{self.session_profit:,} 💰")
        elif self.session_profit < 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LỖ {self.session_profit:,} 💰")
        else: shop_embed.set_footer(text="📊 Kỷ lục phiên này: Đang HUỀ VỐN")

        view = KhungRungShopView(self.author, self.session_profit)
        await interaction.response.edit_message(content=None, embed=shop_embed, view=view)

    async def stop_explore(self, interaction: discord.Interaction):
        for child in self.children: child.disabled = True
        profit_text = f"LÃI +{self.session_profit:,} 💰" if self.session_profit > 0 else f"LỖ {self.session_profit:,} 💰" if self.session_profit < 0 else "HUỀ VỐN"
        
        end_embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(color=discord.Color.default())
        end_embed.add_field(name="🛑 ĐÃ KẾT THÚC CHUYẾN ĐI", value=f"Tổng kết cả phiên của bạn: **{profit_text}**", inline=False)
        await interaction.response.edit_message(embed=end_embed, view=self)

class BushView(discord.ui.View):
    def __init__(self, author, weapon_val, session_profit):
        super().__init__(timeout=60)
        self.author = author
        self.weapon_val = weapon_val
        self.session_profit = session_profit
        
        emojis = ["🌲", "🌳", "🌴", "🌵", "🎋"]
        for i in range(5):
            self.add_item(BushButton(label=f"Lùm Cây {i+1}", style=discord.ButtonStyle.success, custom_id=f"bush_{i}", emoji=emojis[i]))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Tránh ra, lùm cây này tôi giành rồi!", ephemeral=True)
            return False
        return True

class WeaponSelect(discord.ui.Select):
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = [
            discord.SelectOption(label="Gậy Gỗ Mục", description="Giá: 50 💰 | Rẻ tiền, an toàn", emoji="🪵", value="gay_go"),
            discord.SelectOption(label="Súng Cao Su", description="Giá: 100 💰 | Bắn chim cò", emoji="🪀", value="sung_cao_su"),
            discord.SelectOption(label="Kiếm Sắt Thường", description="Giá: 200 💰 | Tỉ lệ hên: Khá", emoji="🗡️", value="kiem_sat"),
            discord.SelectOption(label="Kiếm Hiệp Sĩ", description="Giá: 500 💰 | Tỉ lệ hên: Tốt", emoji="⚔️", value="kiem_hiep_si"),
            discord.SelectOption(label="Rìu Phá Giáp", description="Giá: 1000 💰 | Chặt chém trâu bò", emoji="🪓", value="riu_chien"),
            discord.SelectOption(label="Thánh Kiếm Mạ Vàng", description="Giá: 1500 💰 | Tỉ lệ hên: Cực Tốt", emoji="🔱", value="thanh_kiem"),
            discord.SelectOption(label="Súng Phóng Lựu", description="Giá: 3000 💰 | Sức công phá lớn", emoji="🚀", value="sung_phong_luu"),
            discord.SelectOption(label="Găng Tay Vô Cực", description="Giá: 5000 💰 | Búng tay hủy diệt", emoji="🧤", value="gang_tay")
        ]
        super().__init__(placeholder="Nhấp vào để mua trang bị...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        weapon_id = self.values[0]
        price = WEAPON_ODDS[weapon_id]["price"]
        weapon_name = WEAPON_ODDS[weapon_id]["name"]
        
        if user_data.get("money", 0) < price:
            await interaction.response.send_message(f"Nghèo quá! Bạn không đủ **{price} 💰** để mua {weapon_name}!", ephemeral=True)
            return
            
        user_data["money"] -= price
        new_profit = self.session_profit - price 
        save_user(user_id)
        
        view = BushView(interaction.user, weapon_id, new_profit)
        
        embed = discord.Embed(
            title="🌲 KHU RỪNG KỲ BÍ 🌲",
            description=f"Bạn hiện đang cầm **{weapon_name}**.\nPhía trước có 5 lùm cây. Hãy chọn 1 lùm cây để khám phá!",
            color=discord.Color.dark_green()
        )
        embed.set_footer(text=f"Đã tốn {price} 💰 để mua trang bị.")
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class KhungRungShopView(discord.ui.View):
    def __init__(self, author, session_profit=0):
        super().__init__(timeout=60)
        self.author = author
        self.session_profit = session_profit
        self.add_item(WeaponSelect(self.session_profit))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Ai gọi lệnh thì người đó mua, đừng có giành!", ephemeral=True)
            return False
        return True

# =====================================================================
# GIAO DIỆN TRẠM AFK & CỬA HÀNG ĐẠI GIA (FULL ĐẸP)
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
        reward = 0
        if hours == 4: reward = random.randint(300, 600)
        elif hours == 8: reward = random.randint(700, 1200)
        elif hours == 12: reward = random.randint(1500, 2500)

        end_time = datetime.now() + timedelta(hours=hours)
        
        user_data["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = reward
        save_user(user_id)

        embed = discord.Embed(
            title="⛺ LÊN ĐƯỜNG!",
            description=f"Hành lý đã chuẩn bị xong. Bạn bắt đầu hành trình **{hours} giờ**.\nHãy dùng lại lệnh `k phai` khi hết thời gian để nhận thưởng.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Của ai người nấy bấm nhé!", ephemeral=True)
            return False
        return True

class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        options = []
        for k, v in SHOP_ITEMS.items():
            if v["type"] == category_type:
                options.append(discord.SelectOption(label=v['name'], description=f"Giá: {v['price']:,} 💰", value=k, emoji=v['emoji']))
                
        super().__init__(placeholder="Nhấn vào đây để chọn mua...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        item_id = self.values[0]
        item_info = SHOP_ITEMS[item_id]
        
        if user_data.get("money", 0) < item_info["price"]:
            return await interaction.response.send_message(f"⚠️ Tiền trong ví không đủ! Cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", ephemeral=True)
            
        user_data["money"] -= item_info["price"]
        
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            msg = f"🎉 Chúc mừng! Bạn đã trang bị danh hiệu **{item_info['name']}**."
        else:
            if item_info["name"] in user_data["assets"]:
                user_data["money"] += item_info["price"] 
                return await interaction.response.send_message(f"⚠️ Bạn đã sở hữu **{item_info['name']}** rồi, không cần mua nữa đâu đại gia!", ephemeral=True)
            
            user_data["assets"].append(item_info["name"])
            msg = f"🎉 Chúc mừng! Bạn vừa tậu thành công siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        
        embed = discord.Embed(title="🛍️ GIAO DỊCH THÀNH CÔNG!", description=msg, color=discord.Color.green())
        embed.set_footer(text=f"Số dư còn lại: {user_data['money']:,} 💰")
        await interaction.response.edit_message(content=None, embed=embed, view=None)

class ShopDetailView(discord.ui.View):
    def __init__(self, author, category_type):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ShopItemSelect(category_type))
        
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author: return False
        return True

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="**🛍️ QUẦY BÁN DANH HIỆU:**", embed=None, view=ShopDetailView(self.author, "title"))

    @discord.ui.button(label="Showroom Xe Cộ", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="**🛍️ SHOWROOM XE CỘ:**", embed=None, view=ShopDetailView(self.author, "vehicle"))

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="**🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN:**", embed=None, view=ShopDetailView(self.author, "house"))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Ai gọi lệnh người đó mua nha!", ephemeral=True)
            return False
        return True
        # =====================================================================
# GIAO DIỆN CHỢ ĐEN BÁN ĐỒ (FULL ĐẸP)
# =====================================================================
class SellAssetSelect(discord.ui.Select):
    def __init__(self, assets):
        options = []
        for asset in list(set(assets))[:25]: 
            options.append(discord.SelectOption(label=asset, description=f"Số lượng: {assets.count(asset)} | Thu mua: {get_asset_price(asset):,} 💰", value=asset))
        super().__init__(placeholder="Chọn tài sản để bán (Lỗ 30% so với mua)...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        asset_name = self.values[0]
        
        if asset_name not in user_data.get("assets", []):
            return await interaction.response.send_message("Lỗi: Bạn không còn tài sản này!", ephemeral=True)
            
        sell_price = get_asset_price(asset_name)
        user_data["assets"].remove(asset_name)
        user_data["money"] += sell_price
        save_user(user_id)
        
        await interaction.response.edit_message(content=f"✅ Bạn đã bán **{asset_name}** cho chợ đen và vớt vát được **{sell_price:,} 💰**!", embed=None, view=None)

class SellPetSelect(discord.ui.Select):
    def __init__(self, pets):
        options = []
        count = 0
        for pet, qty in pets.items():
            if count >= 25: break
            if qty > 0:
                options.append(discord.SelectOption(label=pet, description=f"Đang có: {qty} | Giá bán: {get_pet_sell_price(pet):,} 💰", value=pet))
                count += 1
        super().__init__(placeholder="Chọn thú cưng để bán...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        pet_name = self.values[0]
        
        if user_data.get("pets", {}).get(pet_name, 0) <= 0:
            return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này!", ephemeral=True)
            
        sell_price = get_pet_sell_price(pet_name)
        user_data["pets"][pet_name] -= 1
        if user_data["pets"][pet_name] == 0:
            del user_data["pets"][pet_name]
            
        user_data["money"] += sell_price
        save_user(user_id)
        await interaction.response.edit_message(content=f"✅ Bạn đã bán thành công 1 con **{pet_name}** và thu về **{sell_price:,} 💰**!", embed=None, view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Bán Tài Sản (Nhà/Xe)", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets:
            return await interaction.response.send_message("Bạn trắng tay, làm gì có tài sản nào mà bán!", ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellAssetSelect(assets))
        await interaction.response.edit_message(content="**🏷️ CHỢ ĐEN BẤT ĐỘNG SẢN & XE CỘ:**\n*(Lưu ý: Bán lại sẽ bị khấu hao mất 30% giá trị gốc)*", embed=None, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(v == 0 for v in pets.values()):
            return await interaction.response.send_message("Bạn chưa có con thú cưng nào để bán!", ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellPetSelect(pets))
        await interaction.response.edit_message(content="**🏷️ TRẠM THU MUA THÚ CƯNG:**", embed=None, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return False
        return True


# =====================================================================
# TÍNH NĂNG ĐẤU TRƯỜNG: SOLO OẲN TÙ TÌ
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
            return await interaction.response.send_message("Ông đã ra chiêu rồi, không được đổi rút lại đâu!", ephemeral=True)
            
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
                res = "🤝 **HÒA NHAU!** Tiền cược được trả lại cho cả hai."
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
            embed.add_field(name="KẾT QUẢ", value=res, inline=False)
            
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
            
            embed = discord.Embed(title="⏳ HẾT GIỜ KHIẾP SỢ", description="Có người nhát gan không dám ra chiêu. Trận đấu bị hủy, tiền cược đã hoàn trả!", color=discord.Color.dark_gray())
            try: await self.msg.edit(embed=embed, view=None)
            except: pass

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
        embed = discord.Embed(title="⚔️ QUYẾT CHIẾN OẲN TÙ TÌ", description=f"{self.p1.mention} 🆚 {self.p2.mention}\nTiền cược: **{self.bet:,} 💰**\n\n👇 **HÃY BẤM NÚT ĐỂ CHỌN! (Lựa chọn của bạn sẽ bị giấu kín)**")
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
        
        await interaction.response.edit_message(content=f"🎉 {self.target_user.mention} đã chính thức gia nhập **{self.comp_name}**!", view=None)

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id: return await interaction.response.send_message("Tránh ra!", ephemeral=True)
        await interaction.response.edit_message(content=f"❌ {self.target_user.mention} đã chê thẳng thừng lời mời của **{self.comp_name}**.", view=None)


# =====================================================================
# CÁC LỆNH CHÍNH (ĐẦY ĐỦ VÀ HOÀNH TRÁNG)
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH CỦA BOT", description="Tiền tố lệnh là `k` hoặc `K`.", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(name="🏢 THƯƠNG TRƯỜNG & CHỨNG KHOÁN", value="`k cty tao <tên>` • Lập công ty (500k)\n`k cty` • Mở Dashboard Quản lý\n`k daichien @user <chiến_thuật>` • Đánh sập công ty khác\n`k ck` • Sàn chứng khoán (Biến động mỗi giờ)", inline=False)
    embed.add_field(name="💳 KINH TẾ & TÀI SẢN", value="`k rank` • Xem thẻ căn cước\n`k daily` • Nhận lương\n`k lixi` • Bốc phong bao\n`k cuahang` • TTTM Bán nhà, bán xe\n`k sell` (`k ban`) • Chợ Đen Cầm đồ\n`k cuopnganhang` • Cướp nhà băng (Liều ăn nhiều)\n`k tuido` • Xem tài sản\n`k top` • BXH Đại gia\n`k give @user <tiền>`", inline=False)
    embed.add_field(name="🎮 CÁ CƯỢC (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu\n`k duathu <heo/cho/ngua/chuot> <tiền>`\n`k baucua <con vật> <tiền>` • Lắc bầu cua\n`k nohu <tiền>` • Quay xèng Casino\n`k soloott @user <tiền>` • PK Oẳn tù tì", inline=False)
    embed.add_field(name="🌲 NHẬP VAI & CÀY CUỐC", value="`k gacha` • Đập trứng thú cưng (30k)\n`k thamhiem` • Đi rừng nhân phẩm\n`k phai` • Treo máy AFK\n`k nhansinh` • Mô phỏng cuộc đời", inline=False)
    
    embed.set_footer(text="Chúc bạn cày cuốc vui vẻ không quạu!", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=['ban'])
async def sell(ctx):
    embed = discord.Embed(title="⚖️ CHỢ ĐEN CẦM ĐỒ", description="Bạn đang kẹt tiền? Đem đồ ra đây cầm, bao uy tín!\n\n👇 **CHỌN LOẠI ĐỒ BẠN MUỐN BÁN** 👇", color=discord.Color.dark_orange())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=SellCategoryMenu(ctx.author))

@bot.command()
async def cuahang(ctx):
    embed = discord.Embed(title="🏪 TRUNG TÂM THƯƠNG MẠI", description="Tiền nhiều để làm gì? Để mua danh hiệu khè nhau và tậu nhà lầu xe hơi chứ còn gì nữa!\n\n👇 **MỞ DANH SÁCH BÊN DƯỚI ĐỂ MUA SẮM** 👇", color=discord.Color.brand_green())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    cost = 30000

    if user_data.get("money", 0) < cost:
        return await ctx.send(f"⚠️ Trứng Gacha giá **{cost:,} 💰**! Trong ví bạn đang có {user_data.get('money', 0):,} 💰, cày thêm đi nhé!")

    user_data["money"] -= cost
    save_user(user_id)

    msg = await ctx.send(f"🥚 {ctx.author.mention} ném **30,000 💰** để đập một quả trứng Gacha kì bí...\n🔨 Đang gõ...")
    await asyncio.sleep(1.5)
    await msg.edit(content=f"🥚 Vỏ trứng bắt đầu nứt rạn...\n⚡ Ánh sáng chói lóa phát ra từ bên trong!")
    await asyncio.sleep(1.5)

    roll = random.uniform(0, 100)
    if roll <= PET_RATES["mythic"]["rate"]: rarity, color, text = "mythic", discord.Color.dark_purple(), "🌌 THẦN THOẠI (0.1%)"
    elif roll <= PET_RATES["mythic"]["rate"] + PET_RATES["legendary"]["rate"]: rarity, color, text = "legendary", discord.Color.gold(), "👑 HUYỀN THOẠI"
    elif roll <= PET_RATES["mythic"]["rate"] + PET_RATES["legendary"]["rate"] + PET_RATES["epic"]["rate"]: rarity, color, text = "epic", discord.Color.purple(), "🔮 SỬ THI"
    elif roll <= PET_RATES["mythic"]["rate"] + PET_RATES["legendary"]["rate"] + PET_RATES["epic"]["rate"] + PET_RATES["rare"]["rate"]: rarity, color, text = "rare", discord.Color.blue(), "💎 HIẾM"
    else: rarity, color, text = "common", discord.Color.light_grey(), "🪵 PHỔ THÔNG"

    pet_name = random.choice(PET_RATES[rarity]["pool"])
    
    if pet_name in user_data["pets"]: user_data["pets"][pet_name] += 1
    else: user_data["pets"][pet_name] = 1
    save_user(user_id)

    embed = discord.Embed(title=f"🎉 NỔ TRỨNG: {text}!", description=f"Tuyệt vời! Bạn vừa nở ra một bé **{pet_name}**!\n*(Gõ `k tuido` để ngắm, gõ `k sell` để bán lấy tiền)*", color=color)
    await msg.edit(content=ctx.author.mention, embed=embed)

@bot.command()
async def tuido(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    embed = discord.Embed(title=f"🎒 Kho Báu của {ctx.author.name}", color=discord.Color.dark_theme())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    assets = user_data.get("assets", [])
    if len(assets) == 0: assets_str = "Trắng tay, Khố rách áo ôm."
    else: assets_str = "\n".join([f"🔸 {a}" for a in assets])
    embed.add_field(name="🏠 Bất Động Sản & Phương Tiện", value=assets_str, inline=False)
    
    pets = user_data.get("pets", {})
    if len(pets) == 0: pets_str = "Chưa có thú cưng nào. Gõ `k gacha` để kiếm đê!"
    else: pets_str = "\n".join([f"{pet} (x{count})" for pet, count in pets.items()])
    embed.add_field(name="🐾 Trang Trại Thú Cưng", value=pets_str, inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def rank(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    lv, xp, tien = user_data.get("level", 1), user_data.get("xp", 0), user_data.get("money", 0)
    title = user_data.get("title", "Dân Nghèo 🚶")
    max_xp = lv * 100
    
    khung_mau = discord.Color.red() if tien < 0 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 Thẻ Căn Cước của {ctx.author.name}", color=khung_mau)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    embed.add_field(name="Danh hiệu", value=f"**{title}**", inline=False)
    embed.add_field(name="Cấp độ", value=f"🌟 **LV {lv}**", inline=True)
    
    tien_text = f"**{tien:,} 💰**\n*(ĐANG NỢ)*" if tien < 0 else f"**{tien:,} 💰**"
    embed.add_field(name="Tài sản", value=tien_text, inline=True)
    
    comp_id = user_data.get("company")
    if comp_id:
        comp = load_company(comp_id)
        if comp: embed.add_field(name="Công ty", value=f"🏢 **{comp['name']}**", inline=False)

    if user_data.get("jail_time"): 
        embed.add_field(name="Trạng thái", value="🚨 **Đang bóc lịch trong tù!**", inline=False)

    bar = make_progress_bar(xp, max_xp)
    embed.add_field(name="Kinh nghiệm", value=f"`{bar}`\n**{xp}/{max_xp} XP**", inline=False)
    
    assets = user_data.get("assets", [])
    if assets: embed.set_footer(text=f"Đang sở hữu: {', '.join(assets[:3])}{'...' if len(assets)>3 else ''}")
    else: embed.set_footer(text="Gia cảnh: Vô Gia Cư")
        
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    server_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]:
            del CONFIG_CACHE[server_id]["allowed_channels"]
        await ctx.send("✅ Đã gỡ bỏ giới hạn. Bot sẽ nhận lệnh ở **mọi kênh**.")
        return

    mentions = ctx.message.channel_mentions
    if not mentions:
        await ctx.send("⚠️ Vui lòng tag các kênh. VD: `k setup #kenh-1`")
        return

    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids
    channels_str = ", ".join(c.mention for c in mentions)
    await ctx.send(f"✅ Đã cài đặt! Bot từ nay **CHỈ** nhận lệnh tại: {channels_str}")

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền phải > 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] += amount
    save_user(user_id)
    embed = discord.Embed(title="BƠM VỐN THÀNH CÔNG", description=f"👑 Admin {ctx.author.mention} vừa buff nóng cho {member.mention} **{amount:,} 💰**!\n💳 Số dư mới: **{user_data['money']:,} 💰**", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền trừ đi phải > 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] -= amount
    save_user(user_id)
    embed = discord.Embed(title="THIÊN PHẠT GIÁNG XUỐNG", description=f"⚖️ Admin đã tước đoạt **{amount:,} 💰** từ tài khoản của {member.mention}!\n💳 Số dư mới: **{user_data['money']:,} 💰**", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)

    now = datetime.now()
    last_daily_str = user_data.get("last_daily")
    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            time_left = timedelta(days=1) - (now - last_daily)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"⏳ Quay lại sau **{hours} giờ {minutes} phút** nữa nhé.")
            return

    user_data["money"] += 500
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(title="QUÀ ĐIỂM DANH 🎁", color=discord.Color.blue())
    if user_data["money"] < 0:
        embed.description = f"Bạn nhận được **500 💰**!\n⚠️ Hệ thống siết nợ! Bạn còn nợ **{user_data['money']} 💰**."
        embed.color = discord.Color.red()
    else:
        embed.description = f"Bạn nhận được **500 💰**!\n💳 Số dư mới: **{user_data['money']:,} 💰**"
    await ctx.send(embed=embed)

@bot.command()
async def lixi(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)

    now = datetime.now()
    last_lixi_str = user_data.get("last_lixi")
    if last_lixi_str:
        last_lixi = datetime.strptime(last_lixi_str, "%Y-%m-%d %H:%M:%S")
        if now - last_lixi < timedelta(hours=12):
            time_left = timedelta(hours=12) - (now - last_lixi)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"🧧 Bạn đã bốc lì xì rồi! Hẹn quay lại sau **{hours} giờ {minutes} phút** nữa nhé.")
            return

    tien_lixi = random.randint(1000, 8000) 
    user_data["money"] += tien_lixi
    user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(title="🧧 TING TING! CÓ LÌ XÌ!", color=discord.Color.red())
    embed.description = f"Chúc mừng {ctx.author.mention} đã mở phong bao đỏ và nhận được **{tien_lixi:,} 💰**!\n💳 Số dư mới: **{user_data['money']:,} 💰**"
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    danh_sach_dai_gia = [(doc["_id"], doc.get("money", 0)) for doc in all_users]
    danh_sach_dai_gia.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA", color=discord.Color.gold())
    desc = ""
    thu_hang = 1
    for user_id, tien in danh_sach_dai_gia[:10]:
        user = bot.get_user(int(user_id))
        if user is None:
            try: user = await bot.fetch_user(int(user_id))
            except: pass
        ten = user.name if user else f"Người chơi {user_id[-4:]}"
        icon = "🥇" if thu_hang == 1 else "🥈" if thu_hang == 2 else "🥉" if thu_hang == 3 else f"**#{thu_hang}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
        thu_hang += 1
        
    embed.description = desc
    await ctx.send(embed=embed)

@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🪙 {ctx.author.mention} ném **{bet:,} 💰** lên trời...\n🔄 Đồng xu lộn nhào...\n💥 Rơi rầm xuống đất...")
    await asyncio.sleep(2) 

    user_data = load_user(user_id)
    if random.choice(["thắng", "thua"]) == "thắng":
        user_data["money"] += bet * 2
        save_user(user_id)
        await msg.edit(content=f"🪙 **MẶT NGỬA!**\n🎉 {ctx.author.mention} húp trọn **{bet * 2:,} 💰**! (Dư: **{user_data['money']:,} 💰**)")
    else:
        await msg.edit(content=f"🪙 **MẶT SẤP!**\n💀 Nhờn! Mất **{bet:,} 💰**. (Dư: **{user_data['money']:,} 💰**)")

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    choice = choice.lower()
    if choice not in ["tai", "tài", "xiu", "xỉu"]: return await ctx.send("⚠️ Bạn phải chọn `tài` hoặc `xỉu`.")
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🎲 {ctx.author.mention} cược **{bet:,} 💰** vào cửa **{choice.upper()}**.\nLạch cạch lạch cạch... 🫨")
    await asyncio.sleep(2)

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    res_str = "xỉu" if total <= 10 else "tài"
    user_data = load_user(user_id)
    
    if choice.replace("à", "a").replace("ỉ", "i") == res_str.replace("à", "a").replace("ỉ", "i"):
        if d1 == d2 == d3:
            user_data["money"] += bet * 5
            result_msg = f"🔥 **BÃO {d1}-{d2}-{d3}!!! ĐẠI THẮNG x5!**\n🎉 Húp trọn **{bet * 5:,} 💰**!"
        else:
            user_data["money"] += bet * 2
            result_msg = f"✅ **THẮNG RỒI!** Húp trọn **{bet * 2:,} 💰**!"
    else:
        result_msg = f"💀 **THUA CẮNG RĂNG!** Mất **{bet:,} 💰**."

    save_user(user_id)
    await msg.edit(content=f"🎲 KẾT QUẢ: **{d1} - {d2} - {d3}** (Tổng: {total} - **{res_str.upper()}**)\n" + result_msg + f"\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    valid = {"bau":"🥒", "bầu":"🥒", "cua":"🦀", "tom":"🦐", "tôm":"🦐", "ca":"🐟", "cá":"🐟", "ga":"🐓", "gà":"🐓", "huou":"🦌", "hươu":"🦌"}
    choice = choice.lower()
    
    if choice not in valid:
        return await ctx.send("⚠️ Ghi sai tên rồi! Các ô gồm: `bau`, `cua`, `tom`, `ca`, `ga`, `huou`.")
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    user_choice = valid[choice]
    faces = ["🥒", "🦀", "🦐", "🐟", "🐓", "🦌"]
    d1, d2, d3 = random.choice(faces), random.choice(faces), random.choice(faces)
    
    msg = await ctx.send(f"🎲 {ctx.author.mention} đặt **{bet:,} 💰** vào ô **{user_choice}**.\nNhà cái đang xóc đĩa... lạch cạch... 🫨")
    await asyncio.sleep(2)
    
    count = [d1, d2, d3].count(user_choice)
    
    if count > 0:
        win_amt = bet + (bet * count) 
        user_data["money"] += win_amt
        save_user(user_id)
        res = f"🎉 **TRÚNG {count} Ô!** Nhà cái đền **{bet * count:,} 💰** (Cộng cả vốn là {win_amt:,} 💰)."
    else:
        res = f"💀 **TRẬT LẤT!** Nhà cái hốt trọn **{bet:,} 💰** của bạn."
        
    await msg.edit(content=f"🎲 KẾT QUẢ MỞ BÁT: **[ {d1} | {d2} | {d3} ]**\n{res}\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    choice = choice.lower()
    if choice not in animals: return await ctx.send("⚠️ Chọn sai con vật! Có 4 con: `heo`, `cho`, `ngua`, `chuot`.")
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    track_length = 20
    positions = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def get_track():
        txt = f"🏇 **ĐUA THÚ MỞ BÁT!** ({ctx.author.name} cược {bet:,} 💰 vào {animals[choice]})\n"
        txt += "🏁" + "="*track_length + "⛩️\n"
        for pet, pos in positions.items():
            dash_count = min(pos, track_length)
            space_count = track_length - dash_count
            txt += f"🏁{'~'*dash_count}{pet}{' '*space_count}⛩️\n"
        return txt

    msg = await ctx.send(get_track())
    winner = None
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in positions:
            positions[pet] += random.randint(2, 6) 
            if positions[pet] >= track_length and winner is None: winner = pet
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
    await msg.edit(content=get_track() + res_txt + f"\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    
    s1, s2, s3 = random.choice(items), random.choice(items), random.choice(items)
    
    embed = discord.Embed(title="🎰 MÁY XÈNG CASINO 🎰", color=discord.Color.gold())
    msg = await ctx.send(embed=embed)
    
    for _ in range(3):
        embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Máy đang quay tít mù..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
        
    for _ in range(2):
        embed.description = f"**[ {s1} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đã chốt ô đầu tiên..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
        
    for _ in range(2):
        embed.description = f"**[ {s1} | {s2} | {random.choice(items)} ]**\n\n🔄 Nín thở chờ ô cuối..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
        
    if s1 == s2 == s3:
        if s1 == "👑": win_amt = bet * 50
        elif s1 == "💎": win_amt = bet * 20
        else: win_amt = bet * 10
        res = f"🔥 **JACKPOT!!! ĐẠI NỔ HŨ!** Trúng 3 ô {s1}\nBạn húp trọn **{win_amt:,} 💰**!"
        user_data["money"] += win_amt
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win_amt = bet * 2
        res = f"🎉 **THẮNG NHỎ!** Trúng 2 ô giống nhau.\nBạn nhận được **{win_amt:,} 💰**."
        user_data["money"] += win_amt
    else:
        res = f"💀 **TOANG!** Cờ bạc là bác thằng bần.\nMất sạch **{bet:,} 💰**."
        
    save_user(user_id)
    embed.description = f"**[ {s1} | {s2} | {s3} ]**\n\n{res}\n💳 Số dư: **{user_data['money']:,} 💰**"
    await msg.edit(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    n_gui, n_nhan = str(ctx.author.id), str(member.id)
    gui_data = load_user(n_gui)
    nhan_data = load_user(n_nhan)

    if amount <= 0 or gui_data.get("money", 0) < amount or n_gui == n_nhan:
        return await ctx.send("Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển cho mình).")

    gui_data["money"] -= amount
    nhan_data["money"] += amount
    save_user(n_gui)
    save_user(n_nhan)
    embed = discord.Embed(title="💸 CHUYỂN KHOẢN THÀNH CÔNG", color=discord.Color.green())
    embed.description = f"{ctx.author.mention} đã chuyển cho {member.mention} **{amount:,} 💰**!"
    await ctx.send(embed=embed)

@bot.command()
async def phai(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    exp_end_str = user_data.get("exp_end")
    if exp_end_str:
        exp_end = datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        if now >= exp_end:
            reward = user_data.get("exp_reward", 500)
            user_data["money"] = user_data.get("money", 0) + reward
            del user_data["exp_end"]
            del user_data["exp_reward"]
            save_user(user_id)
            embed = discord.Embed(title="🎉 TRỞ VỀ AN TOÀN!", color=discord.Color.gold())
            embed.description = f"{ctx.author.mention} đã thu hoạch được **{reward:,} 💰**!\n💳 Số dư hiện tại: **{user_data['money']:,} 💰**"
            await ctx.send(embed=embed)
        else:
            time_left = exp_end - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"⏳ Đang cày cuốc sấp mặt! Hãy kiên nhẫn chờ thêm **{hours} giờ {minutes} phút** nữa nhé.")
        return

    embed = discord.Embed(title="⛺ TRẠM THÁM HIỂM AFK", description="Gửi nhân vật đi treo máy và nhặt tiền lúc trở về!\n\n👇 **MỞ MENU ĐỂ CHỌN KHU VỰC** 👇", color=discord.Color.dark_green())
    view = ExpView(ctx.author)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    shop_embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ THÁM HIỂM", description="Rừng rậm đầy nguy hiểm nhưng cũng đầy kho báu.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA ĐỒ** 👇", color=discord.Color.orange())
    view = KhungRungShopView(ctx.author, session_profit=0)
    await ctx.send(embed=shop_embed, view=view)

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id)
    phi = 100
    now = datetime.now()

    if user_id in dang_choi_nhansinh: return await ctx.send(f"⏳ {ctx.author.mention}, bạn đang luân hồi dở dang rồi!")
    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5: return await ctx.send(f"⏳ Đợi một chút mới được đầu thai tiếp.")

    user_data = load_user(user_id)
    if user_data.get("money", 0) < phi: return await ctx.send(f"⚠️ Vé luân hồi giá **{phi} 💰**. Túi rỗng thì không có cửa đầu thai đâu!")

    user_data["money"] -= phi
    nhansinh_cooldowns[user_id] = now
    dang_choi_nhansinh.append(user_id)
    save_user(user_id)

    stats = {"may_man": random.randint(1, 10)}
    view = NhanSinhGameView(ctx.author, stats)
    
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.purple())
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{stats['may_man']}/10** *(+ {stats['may_man']*2}% Tỉ lệ)*", inline=False)
    embed.add_field(name="📜 Hành trình cuộc đời", value="\n\n".join(view.logs), inline=False)
    embed.add_field(name="❓ Ngã rẽ tuổi 15", value=f"**{view.ev['q']}**", inline=False)

    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['ott'])
async def oantuti(ctx, choice: str, amount: str):
    valid_choices = {"bua": "🪨", "búa": "🪨", "bao": "📄", "giay": "📄", "giấy": "📄", "keo": "✂️", "kéo": "✂️"}
    choice = choice.lower()
    if choice not in valid_choices: return await ctx.send("⚠️ Phải ra `bua`, `bao` hoặc `keo`!")

    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    bot_options = ["🪨", "📄", "✂️"]
    bot_choice = random.choice(bot_options)
    user_choice = valid_choices[choice]
    
    msg = await ctx.send(f"🤔 Bạn ra {user_choice}. Bot đang suy nghĩ...\n💥 Oẳn... tù... tì... RA CÁI GÌ RA CÁI NÀY!!")
    await asyncio.sleep(1.5)

    user_data = load_user(user_id)
    if user_choice == bot_choice:
        user_data["money"] += bet
        res = "🤝 **HÒA NHAU!** Trả lại tiền cược."
    elif (user_choice == "🪨" and bot_choice == "✂️") or (user_choice == "📄" and bot_choice == "🪨") or (user_choice == "✂️" and bot_choice == "📄"):
        user_data["money"] += bet * 2
        res = f"🎉 **BẠN THẮNG RỒI!** Húp trọn **{bet * 2:,} 💰**."
    else:
        res = f"💀 **BOT THẮNG!** Mất **{bet:,} 💰**."

    save_user(user_id)
    await msg.edit(content=f"💥 Bot ra: **{bot_choice}** | Bạn ra: **{user_choice}**\n{res}\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command()
async def soloott(ctx, member: discord.Member, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    
    if member.id == ctx.author.id: return await ctx.send("⚠️ Chơi bị khùng à mà gạ đánh với chính mình?")
    if member.bot: return await ctx.send("⚠️ Bot không có tiền để solo với bạn đâu! Hãy gõ `k ott` để đánh với hệ thống.")
        
    u2_data = load_user(member.id)
    if u2_data.get("money", 0) < bet:
        return await ctx.send(f"⚠️ Đối thủ {member.mention} đang nghèo rớt mồng tơi, không đủ **{bet:,} 💰** để nhận kèo đâu!")
        
    view = SoloOTTAccept(ctx.author, member, bet)
    embed = discord.Embed(title="🔥 THÁCH ĐẬU OẲN TÙ TÌ", description=f"{ctx.author.mention} vừa cầm **{bet:,} 💰** đập bàn, thách đấu solo với {member.mention}!\n\nNhanh tay bấm **Nhận Kèo** trong vòng 60 giây nếu dám chơi!", color=discord.Color.red())
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
        embed = discord.Embed(title="🏢 SÀN GIAO DỊCH DOANH NGHIỆP", description="Bạn hiện đang thất nghiệp.\nĐể thành lập công ty, gõ:\n`k cty tao <tên công ty>` (Phí: 500,000 💰)", color=discord.Color.red())
        return await ctx.send(embed=embed)
    
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None; save_user(user_id)
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
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    if user_data.get("company"): return await ctx.send("Bạn đã ở trong một công ty rồi! Thoát ra trước khi tạo mới.")
    if user_data.get("money", 0) < 500000: return await ctx.send("⚠️ Phí thành lập công ty là **500,000 💰**. Cày thêm đi sếp!")
    
    user_data["money"] -= 500000
    user_data["company"] = user_id
    
    new_comp = {
        "_id": user_id, "name": name, "treasury": 0, 
        "members": {user_id: "boss"}, 
        "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, 
        "last_interest": "2000-01-01 00:00:00"
    }
    COMPANY_CACHE[user_id] = new_comp
    save_company(user_id); save_user(user_id)
    await ctx.send(embed=discord.Embed(title="🏢 KHAI TRƯƠNG HỒNG PHÁT", description=f"Chúc mừng sếp {ctx.author.mention} đã thành lập **{name}**!\nGõ `k cty` để xem bảng điều khiển.", color=discord.Color.green()))

@cty.command()
async def tuyen(ctx, member: discord.Member):
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.send("Bạn có công ty đâu mà đòi tuyển người!")
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.send("Chỉ sếp lớn mới được tuyển người!")
    if load_user(member.id).get("company"): return await ctx.send("Người này đã có công ty rồi.")
    
    view = CompanyInviteView(comp_id, comp["name"], member)
    await ctx.send(f"🏢 {member.mention}, bạn có lời mời vào làm việc tại **{comp['name']}**! Bấm nút bên dưới để quyết định.", view=view)

@cty.command()
async def duoi(ctx, member: discord.Member):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) not in ["boss", "quanly"]: return await ctx.send("Bạn không có quyền đuổi người!")
    target_id = str(member.id)
    if target_id not in comp["members"]: return await ctx.send("Người này không có trong công ty!")
    if comp["members"][target_id] == "boss": return await ctx.send("Tính làm phản hả? Không đuổi được sếp tổng đâu!")
    
    del comp["members"][target_id]
    target_data = load_user(target_id); target_data["company"] = None
    save_company(comp_id); save_user(target_id)
    await ctx.send(f"👢 Đã đuổi cổ {member.mention} ra khỏi công ty!")

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.send("Bạn chưa có công ty.")
    if user_data.get("money", 0) < amount: return await ctx.send("Không đủ tiền để góp!")
    
    comp = load_company(comp_id)
    user_data["money"] -= amount; comp["treasury"] += amount
    save_user(user_id); save_company(comp_id)
    await ctx.send(f"💰 Bạn đã góp **{amount:,} 💰** vào quỹ công ty. Tổng quỹ: **{comp['treasury']:,} 💰**.")

@cty.command()
async def thulai(ctx):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.send("Chỉ Chủ tịch mới được thu lãi ngân hàng!")
    
    now = datetime.now()
    last = datetime.strptime(comp.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
    if now - last < timedelta(days=1):
        return await ctx.send("⏳ Ngân hàng chưa chốt sổ! Mỗi ngày chỉ được thu lãi 1 lần.")
        
    lai = int(comp["treasury"] * 0.05) # Lãi 5% quỹ
    if lai > 100000: lai = 100000 # Max lãi 100k/ngày để tránh buff tiền ảo
    
    comp["treasury"] += lai
    comp["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_company(comp_id)
    await ctx.send(f"📈 Công ty đã nhận được **{lai:,} 💰** tiền lãi hôm nay! Tổng quỹ: **{comp['treasury']:,} 💰**.")

@cty.command()
async def luong(ctx, amount: int):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.send("Chỉ Chủ tịch mới được ký quỹ phát lương!")
    mem_count = len(comp["members"])
    if amount * mem_count > comp["treasury"]: return await ctx.send(f"Quỹ không đủ! Cần {amount*mem_count:,} 💰 để phát cho {mem_count} người.")
    
    comp["treasury"] -= (amount * mem_count)
    for m_id in comp["members"]:
        m_data = load_user(m_id)
        m_data["money"] += amount
        save_user(m_id)
    save_company(comp_id)
    await ctx.send(f"💸 Sếp đã phát **{amount:,} 💰** lương cho mỗi nhân viên! (Tổng chi: {amount*mem_count:,} 💰)")

@cty.command()
async def chucvu(ctx, member: discord.Member, role: str):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.send("Chỉ Chủ tịch mới được set chức!")
    target_id = str(member.id)
    if target_id not in comp["members"]: return await ctx.send("Người này không thuộc công ty.")
    if target_id == user_id: return await ctx.send("Không thể tự đổi chức của bản thân.")
    if role not in ["quanly", "nhanvien"]: return await ctx.send("Chức vụ phải là `quanly` hoặc `nhanvien`.")
    
    comp["members"][target_id] = role; save_company(comp_id)
    await ctx.send(f"✅ Đã thăng/giáng chức {member.mention} thành **{comp['roles'][role]}**.")

@cty.command()
async def doitenchuc(ctx, role: str, *, name: str):
    user_id = str(ctx.author.id); comp_id = load_user(user_id).get("company")
    if not comp_id: return
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss": return await ctx.send("Chỉ Chủ tịch mới được đổi tên chức vụ!")
    if role not in ["boss", "quanly", "nhanvien"]: return await ctx.send("Hệ phái phải là `boss`, `quanly` hoặc `nhanvien`.")
    
    comp["roles"][role] = name; save_company(comp_id)
    await ctx.send(f"✅ Đã đổi tên hệ phái `{role}` thành **{name}**.")

@cty.command()
async def roi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); comp_id = user_data.get("company")
    if not comp_id: return await ctx.send("Bạn làm gì có công ty mà đòi rời!")
    comp = load_company(comp_id)
    
    if comp["members"][user_id] == "boss":
        del COMPANY_CACHE[comp_id]; companies_col.delete_one({"_id": comp_id})
        for m_id in comp["members"]:
            m_data = load_user(m_id); m_data["company"] = None; save_user(m_id)
        await ctx.send("🏢 Chủ tịch đã rời đi. Công ty tuyên bố PHÁ SẢN!")
    else:
        del comp["members"][user_id]; user_data["company"] = None
        save_user(user_id); save_company(comp_id)
        await ctx.send("🎒 Bạn đã thu dọn hành lý rời khỏi công ty.")

@bot.command()
async def daichien(ctx, member: discord.Member = None, tactic: str = None):
    u1 = str(ctx.author.id)
    c1_id = load_user(u1).get("company")
    
    if not member or not tactic or tactic.lower() not in ["hack", "phot", "giangho"]:
        embed = discord.Embed(title="⚔️ ĐẠI CHIẾN THƯƠNG TRƯỜNG (SÁNG TẠO)", description="Không cần đông người, quan trọng là chiến thuật!\nCách dùng: `k daichien @user <chiến_thuật>`", color=discord.Color.red())
        embed.add_field(name="1. hack (Tấn công mạng)", value="Tỉ lệ thắng: **30%**\nPhần thưởng: Cướp **10%** quỹ đối thủ.\nThất bại: Đền bù **5%** quỹ của mình.", inline=False)
        embed.add_field(name="2. phot (Thuê KOL bóc phốt)", value="Tỉ lệ thắng: **50%**\nPhần thưởng: Cướp **5%** quỹ đối thủ.\nThất bại: Đền bù **2%** quỹ của mình.", inline=False)
        embed.add_field(name="3. giangho (Vũ lực)", value="Tỉ lệ thắng: **70%**\nPhần thưởng: Cướp **2%** quỹ đối thủ.\nThất bại: Đền bù **1%** quỹ của mình.", inline=False)
        return await ctx.send(embed=embed)
        
    u2 = str(member.id); c2_id = load_user(u2).get("company")
    if u1 == u2 or member.bot: return await ctx.send("⚠️ Đánh với ai chứ đừng tự kỷ hoặc đánh Bot.")
    if not c1_id or not c2_id: return await ctx.send("⚠️ Cả 2 đều phải có công ty mới được PK!")
    if c1_id == c2_id: return await ctx.send("⚠️ Cùng một công ty, anh em tương tàn làm gì!")
    
    now = datetime.now()
    if c1_id in cty_cooldowns and (now - cty_cooldowns[c1_id]).total_seconds() < 3600:
        return await ctx.send("⏳ Công ty bạn vừa xuất quân rồi! Đợi 1 tiếng để hồi phục binh lực.")
    
    comp1 = load_company(c1_id); comp2 = load_company(c2_id)
    if comp2["treasury"] < 10000: return await ctx.send("⚠️ Quỹ công ty đối thủ nghèo quá (<10k), không đáng để đánh!")
    
    cty_cooldowns[c1_id] = now
    tactic = tactic.lower()
    
    if tactic == "hack": win_rate = 30; win_pct = 0.10; lose_pct = 0.05; name = "TẤN CÔNG MẠNG MÁY CHỦ"
    elif tactic == "phot": win_rate = 50; win_pct = 0.05; lose_pct = 0.02; name = "THUÊ BÁO CHÍ BÓC PHỐT"
    else: win_rate = 70; win_pct = 0.02; lose_pct = 0.01; name = "ĐƯA GIANG HỒ ĐẾN ĐẬP PHÁ"
    
    msg = await ctx.send(f"⚔️ **{comp1['name']}** đang dùng chiến thuật **{name}** lên **{comp2['name']}**..."); await asyncio.sleep(2)
    
    roll = random.randint(1, 100)
    if roll <= win_rate:
        steal = int(comp2["treasury"] * win_pct)
        comp1["treasury"] += steal; comp2["treasury"] -= steal
        save_company(c1_id); save_company(c2_id)
        await msg.edit(content=f"🔥 **ĐẠI THẮNG!** Binh pháp quá đỉnh!\n💰 Cướp được **{steal:,} 💰** mang về quỹ công ty!")
    else:
        fine = int(comp1["treasury"] * lose_pct)
        comp1["treasury"] -= fine; comp2["treasury"] += fine
        save_company(c1_id); save_company(c2_id)
        await msg.edit(content=f"💀 **THẤT BẠI!** Đối thủ đã phòng bị!\nBạn bị kiện ngược và phải đền bù **{fine:,} 💰** cho quỹ đối thủ.")


# =====================================================================
# SÀN CHỨNG KHOÁN & CƯỚP BANK & SỰ KIỆN CHÍNH
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    embed = discord.Embed(title="📈 SÀN CHỨNG KHOÁN (Cập nhật mỗi giờ)", description="Mua rẻ bán đắt để làm giàu!\n`k ck buy <MÃ> <Số lượng>`\n`k ck sell <MÃ> <Số lượng>`", color=discord.Color.brand_green())
    
    for code, name in STOCKS.items():
        price_now = get_stock_price(code, 0)
        price_old = get_stock_price(code, -1)
        trend = "📈 Lên" if price_now > price_old else "📉 Xuống"
        diff = abs(price_now - price_old)
        embed.add_field(name=f"{code} - {name}", value=f"Giá: **{price_now:,} 💰**\n*(Biến động: {trend} {diff:,})*", inline=False)
        
    user_data = load_user(ctx.author.id)
    my_stocks = user_data.get("stocks", {})
    inventory = "\n".join([f"{k}: {v} cổ phiếu" for k, v in my_stocks.items() if v > 0])
    if not inventory: inventory = "Bạn chưa mua mã nào."
    embed.add_field(name="🎒 Cổ phiếu của bạn", value=inventory, inline=False)
    await ctx.send(embed=embed)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    if code not in STOCKS: return await ctx.send("⚠️ Mã cổ phiếu không tồn tại!")
    if qty <= 0: return await ctx.send("Số lượng phải > 0")
    
    price = get_stock_price(code, 0)
    total_cost = price * qty
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    
    if user_data.get("money", 0) < total_cost: return await ctx.send(f"⚠️ Bạn không đủ tiền! Cần **{total_cost:,} 💰**.")
    
    user_data["money"] -= total_cost
    user_data["stocks"][code] = user_data.get("stocks", {}).get(code, 0) + qty
    save_user(user_id)
    await ctx.send(f"✅ Đã mua **{qty} {code}** với giá {total_cost:,} 💰! Chờ giá lên rồi `sell` nhé.")

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper()
    if code not in STOCKS: return await ctx.send("⚠️ Mã cổ phiếu không tồn tại!")
    if qty <= 0: return await ctx.send("Số lượng phải > 0")
    
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    my_qty = user_data.get("stocks", {}).get(code, 0)
    
    if my_qty < qty: return await ctx.send(f"⚠️ Bạn chỉ có {my_qty} cổ phiếu {code}, lấy đâu ra mà bán!")
    
    price = get_stock_price(code, 0)
    total_gain = price * qty
    
    user_data["stocks"][code] -= qty
    if user_data["stocks"][code] == 0: del user_data["stocks"][code]
    user_data["money"] += total_gain
    save_user(user_id)
    await ctx.send(f"✅ Đã chốt lời **{qty} {code}** thu về {total_gain:,} 💰!")

@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id)
    if user_data.get("money", 0) < 50000: return await ctx.send("⚠️ Bạn cần tối thiểu 50,000 💰 làm vốn mua súng mới đi cướp được!")
    
    now = datetime.now()
    if user_id in cty_cooldowns and (now - cty_cooldowns[user_id]).total_seconds() < 3600:
        return await ctx.send("⏳ Đang bị truy nã gắt gao! Trốn 1 tiếng nữa rồi hẵng đi cướp tiếp.")
    
    cty_cooldowns[user_id] = now
    msg = await ctx.send("🔫 Bạn đang đeo mặt nạ xông vào ngân hàng nhà nước..."); await asyncio.sleep(2)
    
    roll = random.randint(1, 100)
    if roll <= 20: 
        loot = random.randint(100000, 500000)
        user_data["money"] += loot; save_user(user_id)
        await msg.edit(content=f"🎉 **TRÓT LỌT!** Bạn hốt sạch tiền trong két và tẩu thoát.\n💰 Cướp được: **{loot:,} 💰**!")
    else: 
        user_data["money"] -= 50000 
        user_data["jail_time"] = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        save_user(user_id)
        await msg.edit(content=f"🚨 **WEE WOO WEE WOO!** Cảnh sát ập tới!\nBạn bị bắt vào tù. Bị cấm dùng mọi lệnh bot trong **10 phút** tới!")

@bot.event
async def on_message(message):
    if message.author.bot: return
    u_id = str(message.author.id)
    user_data = load_user(u_id)
    
    # Đang đi tù thì không cho chat kiếm tiền (chỉ thực hiện dòng này, lệnh sẽ bị chặn bởi @bot.check bên trên)
    if user_data.get("jail_time"):
        jail_end = datetime.strptime(user_data["jail_time"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            return await bot.process_commands(message)

    user_data["xp"] += random.randint(5, 15)
    max_xp = user_data["level"] * 100

    if user_data["xp"] >= max_xp:
        user_data["xp"] -= max_xp
        user_data["level"] += 1
        thuong = user_data["level"] * 150
        user_data["money"] += thuong
        
        embed = discord.Embed(title="🎉 THĂNG CẤP!", description=f"Chúc mừng {message.author.mention} đã tu luyện đạt **Cấp {user_data['level']}**!\nPhần thưởng: **{thuong:,} 💰**", color=discord.Color.gold())
        if message.author.avatar: embed.set_thumbnail(url=message.author.avatar.url)
        
        config = load_server_config(message.guild.id)
        kenh_id = config.get("channel_id")
        k = bot.get_channel(kenh_id) if kenh_id else message.channel
        if k: await k.send(embed=embed)

    save_user(u_id)
    await bot.process_commands(message)

@bot.event
async def on_ready(): print(f'{bot.user} đã lên mạng và sẵn sàng phục vụ!')

keep_alive() 

# === HAI NỬA MÃ TOKEN ===
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
nua_sau = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'
bot.run(nua_dau + nua_sau)
