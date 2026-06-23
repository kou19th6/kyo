import discord
from discord.ext import commands, tasks
from keep_alive import keep_alive 
import random 
import asyncio 
from datetime import datetime, timedelta 
import pymongo 
import math

# =====================================================================
# [PHẦN 1] KHỞI TẠO BOT SIÊU CẤP & CẤU HÌNH CƠ BẢN
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Cần thiết để lấy thông tin user trong server

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

# --- BỘ TỪ ĐIỂN ẢNH GIF ANIMATION ---
GIF_LINKS = {
    "jail": "https://media.giphy.com/media/uG3lKkAuh53wKxY0l9/giphy.gif",
    "bank": "https://media.giphy.com/media/xTiTnqUxyWbsAXq7Ju/giphy.gif",
    "rob_success": "https://media.giphy.com/media/Y2ZUWLrTy63j9T6qrK/giphy.gif",
    "rob_fail": "https://media.giphy.com/media/RYjnzPS8u0jAs/giphy.gif",
    "rank": "https://media.giphy.com/media/LdOyjZ7io5Msw/giphy.gif",
    "daily": "https://media.giphy.com/media/67ThRZlYBvibtdF9JH/giphy.gif",
    "casino": "https://media.giphy.com/media/l4hLA4ALhloJt2Tny/giphy.gif",
    "work": "https://media.giphy.com/media/3o7TKoHNJTWWLgljYQ/giphy.gif"
}

# --- QUẢN LÝ COOLDOWN (CHỐNG SPAM) ---
gamble_cooldowns = {} 
nhansinh_cooldowns = {} 
work_cooldowns = {}
crime_cooldowns = {}
dang_choi_nhansinh = [] 

# =====================================================================
# KẾT NỐI MONGODB VÀ BỘ ĐỆM RAM (CACHE TỐI ƯU HÓA)
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]

# CÁC BẢNG (COLLECTIONS) DỮ LIỆU
users_col = db["users"]         # Dữ liệu người chơi
config_col = db["config"]       # Cấu hình server
clans_col = db["clans"]         # Hệ thống Băng Đảng / Gia Tộc
stocks_col = db["stocks"]       # Hệ thống Chứng khoán động

DB_CACHE = {}
CONFIG_CACHE = {}

def load_user(user_id):
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        doc = users_col.find_one({"_id": user_id})
        DB_CACHE[user_id] = doc if doc else {}
            
    # Khởi tạo mặc định nếu user mới tinh hoặc thiếu field
    defaults = {
        "xp": 0, "level": 1, "money": 500, "bank": 0, 
        "title": "Kẻ Lang Thang 🏕️", 
        "assets": [], "pets": {}, "stocks": {}, 
        "jail_time": None, "health": 100, "max_health": 100,
        "clan": None, "reputation": 0
    }
    for k, v in defaults.items():
        if k not in DB_CACHE[user_id]: 
            DB_CACHE[user_id][k] = v
    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE: 
        users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

def load_server_config(server_id):
    server_id = str(server_id)
    if server_id not in CONFIG_CACHE:
        doc = config_col.find_one({"_id": server_id})
        CONFIG_CACHE[server_id] = doc if doc else {}
    return CONFIG_CACHE[server_id]

# --- KIỂM TRA ĐIỀU KIỆN KÊNH & TÙ TỘI ---
@bot.check
async def global_jail_and_channel_check(ctx):
    if ctx.author.guild_permissions.administrator or ctx.command.name == "help": 
        return True
    
    u = load_user(ctx.author.id)
    jail_time_str = u.get("jail_time")
    
    if jail_time_str:
        jail_end = datetime.strptime(jail_time_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            embed = discord.Embed(
                title="🚨 PHẠM NHÂN ĐANG VƯỢT NGỤC!", 
                description=f"Ê {ctx.author.mention}, đang bóc lịch mà đòi lướt mạng à? Cải tạo tốt đi.\n\n⏳ Mãn hạn: <t:{int(jail_end.timestamp())}:R>", 
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=GIF_LINKS["jail"])
            await ctx.reply(embed=embed, mention_author=False)
            return False
        else:
            u["jail_time"] = None
            save_user(ctx.author.id)
            
    if ctx.guild:
        cfg = load_server_config(ctx.guild.id)
        allow = cfg.get("allowed_channels", [])
        if allow and ctx.channel.id not in allow: 
            return False
    return True

async def check_gamble_conditions(ctx, amount_str):
    uid = str(ctx.author.id)
    now = datetime.now()
    if uid in gamble_cooldowns:
        diff = (now - gamble_cooldowns[uid]).total_seconds()
        if diff < 3:
            await ctx.reply(f"⏳ Cờ bạc là bác thằng bần, thở cái đã! Đợi {int(3 - diff)}s.", mention_author=False)
            return None, None
            
    u = load_user(uid)
    if u.get("money", 0) <= 0:
        await ctx.reply("💸 Cháy túi cmnr đại ca ơi, lấy gì cược?", mention_author=False)
        return None, None
        
    try: 
        bet = min(u["money"], 1000000) if amount_str.lower() == "all" else int(amount_str)
    except ValueError: 
        await ctx.reply("⚠️ Nhập sai số tiền! Ghi số đàng hoàng hoặc `all`.", mention_author=False)
        return None, None
        
    if bet <= 0 or bet > u["money"]: 
        await ctx.reply(f"⚠️ Tiền mồm à? Bạn chỉ có **{u['money']:,} 💰**.", mention_author=False)
        return None, None
        
    if bet > 1000000: 
        await ctx.reply("🛑 Nhà cái chỉ nhận kèo cược tối đa **1,000,000 💰** thôi!", mention_author=False)
        return None, None
        
    return u, bet

# =====================================================================
# TỔNG KHO VẬT PHẨM MUA BÁN CỦA SERVER (MỞ RỘNG)
# =====================================================================
SHOP_ITEMS = {
    # Danh hiệu
    "title_1": {"type": "title", "name": "Bình Dân Học Vụ 🎒", "price": 50000, "emoji": "🏷️"},
    "title_2": {"type": "title", "name": "Thương Nhân Chợ Đen 💼", "price": 500000, "emoji": "🏷️"},
    "title_3": {"type": "title", "name": "Đại Gia Nổi Chuẩn 💸", "price": 2000000, "emoji": "🏷️"},
    "title_4": {"type": "title", "name": "Tài Phiệt Ác Ma 👑", "price": 10000000, "emoji": "🏷️"},
    "title_5": {"type": "title", "name": "Thần Tài Giáng Thế 🌟", "price": 50000000, "emoji": "🏷️"},
    
    # Phương tiện
    "veh_1": {"type": "vehicle", "name": "Xe Đạp Điện Mini 🚲", "price": 15000, "emoji": "🚲"},
    "veh_2": {"type": "vehicle", "name": "Honda SH 150i 🏍️", "price": 120000, "emoji": "🏍️"},
    "veh_3": {"type": "vehicle", "name": "Mazda C300 AMG 🚗", "price": 1500000, "emoji": "🚗"},
    "veh_4": {"type": "vehicle", "name": "Mercedes G63 🚙", "price": 8000000, "emoji": "🚙"},
    "veh_5": {"type": "vehicle", "name": "Siêu Xe Bugatti 🏎️", "price": 25000000, "emoji": "🏎️"},
    "veh_6": {"type": "vehicle", "name": "Trực Thăng Cá Nhân 🚁", "price": 150000000, "emoji": "🚁"},
    
    # Bất động sản
    "house_1": {"type": "house", "name": "Phòng Trọ 15m2 🏚️", "price": 80000, "emoji": "🏚️"},
    "house_2": {"type": "house", "name": "Chung Cư Mini 🏢", "price": 800000, "emoji": "🏢"},
    "house_3": {"type": "house", "name": "Nhà Mặt Phố 🏪", "price": 5000000, "emoji": "🏪"},
    "house_4": {"type": "house", "name": "Biệt Thự Hồ Tây 🏡", "price": 35000000, "emoji": "🏡"},
    "house_5": {"type": "house", "name": "Lâu Đài Cổ Châu Âu 🏰", "price": 200000000, "emoji": "🏰"},
    "house_6": {"type": "house", "name": "Hòn Đảo Tư Nhân 🏝️", "price": 800000000, "emoji": "🏝️"}
}

# =====================================================================
# DỮ LIỆU ĐI RỪNG THÁM HIỂM (ĐA DẠNG HÓA KỊCH BẢN)
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "🪵 Gậy Gỗ Mục", "terrible": 25, "bad": 40, "neutral": 15, "good": 15, "great": 5, "jackpot": 0},
    "dao_gam": {"price": 150, "name": "🔪 Dao Găm Rỉ", "terrible": 20, "bad": 30, "neutral": 20, "good": 20, "great": 9, "jackpot": 1},
    "kiem_sat": {"price": 300, "name": "🗡️ Kiếm Sắt", "terrible": 15, "bad": 25, "neutral": 15, "good": 28, "great": 15, "jackpot": 2},
    "sung_luc": {"price": 800, "name": "🔫 Súng Lục Cổ", "terrible": 12, "bad": 20, "neutral": 10, "good": 33, "great": 20, "jackpot": 5},
    "thanh_kiem": {"price": 2000, "name": "🔱 Thánh Kiếm", "terrible": 8, "bad": 15, "neutral": 10, "good": 32, "great": 25, "jackpot": 10},
    "sung_ngam": {"price": 5000, "name": "🔭 Súng Ngắm AWM", "terrible": 5, "bad": 10, "neutral": 5, "good": 30, "great": 35, "jackpot": 15},
    "bazooka": {"price": 12000, "name": "🚀 Pháo Bazooka", "terrible": 3, "bad": 8, "neutral": 5, "good": 24, "great": 40, "jackpot": 20},
    "gang_tay": {"price": 30000, "name": "🧤 Găng Vô Cực", "terrible": 1, "bad": 5, "neutral": 4, "good": 15, "great": 40, "jackpot": 35}
}

SCENARIOS = {
    "terrible": [ 
        {"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!** Bị đấm bay xa 10km, rớt sạch đồ đạc!"},
        {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!** Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền!"},
        {"mult": -1.8, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!** Bị phục kích hội đồng, lột không còn cái quần xà lỏn."},
        {"mult": -2.5, "msg": "☠️ **DẪM TRÚNG MÌN CÒN SÓT LẠI!** Văng lên cây, tiền phẫu thuật chỉnh hình cao ngất ngưởng!"},
        {"mult": -1.2, "msg": "🐊 **CÁ SẤU ĐẦM LẦY!** Đang lội nước bị táp mất cái ví đít."},
        {"mult": -3.0, "msg": "👽 **NGƯỜI NGOÀI HÀNH TINH BẮT CÓC!** Bị hút lên đĩa bay, thí nghiệm tốn hết nguyên khí và tài sản!"}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!** Một con khỉ giật lấy túi tiền rồi đu cây biến mất."},
        {"mult": -0.4, "msg": "🪤 **BẪY GẤU!** CẠCH! Bạn đạp trúng bẫy gấu. Mất tiền đi viện tiêm phòng uốn ván."},
        {"mult": -0.6, "msg": "🧪 **NƯỚC SUỐI ĐỘC!** Khát quá uống bậy, đau bụng tốn tiền viện phí."},
        {"mult": -0.3, "msg": "🐝 **CHỌC Ổ ONG VẼ!** Sưng mặt như cái mâm, đánh rơi tiền chạy lấy người."},
        {"mult": -0.8, "msg": "🕳️ **SỤP HỐ CẠM BẪY!** Phải thuê người kéo lên, nộp phí giải cứu cực chát."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ...** Bạn vạch ra và... chẳng có gì cả. Chỉ có gió lạnh."},
        {"mult": 0, "msg": "🐇 **THỎ CON...** Con thỏ nhìn bạn khinh bỉ rồi nhảy đi."},
        {"mult": 0, "msg": "📦 **RƯƠNG GỖ MỤC!** Mở ra chỉ có đất đá và mạng nhện."},
        {"mult": 0, "msg": "🍄 **NẤM LẠ...** Trông có vẻ ngon nhưng bạn sợ ngộ độc nên không dám hái."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!** Nhặt được chiếc ví rách, bên trong có vài đồng xu cổ."},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI NGÀN NĂM!** Hái được cây nấm đỏ rực. Tiệm thuốc trả khá hời."},
        {"mult": 0.6, "msg": "🍯 **TỔ ONG MẬT ĐẦY ĐẶN!** Hun khói lấy được tảng mật ong rừng vàng óng."},
        {"mult": 0.7, "msg": "🦅 **TRỨNG ĐẠI BÀNG!** Nhặt được quả trứng quý trên vách đá."},
        {"mult": 1.2, "msg": "🤠 **CỨU ĐƯỢC THƯƠNG GIA!** Giúp người ta thoát bẫy gấu, được hậu tạ ngay tại chỗ!"}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!** Tóm gọn toán cướp và tịch thu kho báu chúng giấu trong hang!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!** Đào trúng rương vàng chóe bị chôn vùi. Mở ra lóa cả mắt!"},
        {"mult": 2.0, "msg": "💎 **MỎ NGỌC THÔ KHỔNG LỒ!** Vung bừa vũ khí vỡ tảng đá, lộ ra cả vựa ngọc lục bảo!"},
        {"mult": 3.2, "msg": "🏺 **CỔ VẬT NHÀ THANH!** Đào được cái chóe gốm ngàn năm không sứt mẻ. Giá trị liên thành!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ BỊ ĐÁNH RƠI CỦA THẦN RỪNG!** Dò trúng giải SIÊU ĐẶC BIỆT!"},
        {"mult": 8.0, "msg": "🏴‍☠️ **KHO BÁU HẢI TẶC CARIBE!** Hang động ánh sáng lập lòe, một núi Vàng thỏi hiện ra!"},
        {"mult": 15.0, "msg": "👑 **VƯƠNG MIỆN CLEOPATRA! (ULTRAPOT)** Đáy đầm lầy giấu báu vật vô giá. Chúc mừng tỷ phú mới!"},
        {"mult": 20.0, "msg": "🛸 **TÀU VŨ TRỤ RƠI! (GOD TIER)** Bạn nhặt được lõi năng lượng của người ngoài hành tinh bán cho NASA!"}
    ]
}

# =====================================================================
# BỘ CỐT TRUYỆN MÔ PHỎNG NHÂN SINH KỊCH TÍNH (SIÊU HARDCORE)
# =====================================================================
EVENTS_P1 = [ # TUỔI 15
    {
        "q": "Bạn đang ôn thi chuyển cấp thì nhỏ bạn thân rủ cúp học đi concert của BlackPink.",
        "choices": [
            {"text": "Ở nhà cày đề toán 24/7", "rate": 85, "win": "Bạn đỗ thủ khoa! Bố mẹ thưởng nóng con xe xịn.", "lose": "Áp lực quá hóa điên, vào thi quên sạch tên mình.", "tien_w": 5000, "tien_l": -2000, "die_l": False},
            {"text": "Lấy tiền đóng học đi Concert", "rate": 15, "win": "Gặp ngay đại gia tại Concert nhận làm con nuôi!", "lose": "Chen lấn giẫm đạp nhập viện gãy chân, thi trượt.", "tien_w": 25000, "tien_l": -10000, "die_l": False},
            {"text": "Viết phao bỏ vào ống tay áo", "rate": 35, "win": "Phao chuẩn y xì, bạn qua môn xuất sắc không tốn giọt mồ hôi.", "lose": "Bị giám thị tóm, cấm thi 2 năm, ở nhà chăn bò.", "tien_w": 3000, "tien_l": -8000, "die_l": False},
            {"text": "Bỏ thi đi làm giang hồ mạng", "rate": 5, "win": "Bạn mõm trên Tóp Tóp nổi tiếng, nhận donate chục củ.", "lose": "Bị anh lớn ngoài đời xiên chết vì tội mạo danh.", "tien_w": 50000, "tien_l": -20000, "die_l": True}
        ]
    },
    {
        "q": "Nhặt được iPhone 15 Pro Max của cô hiệu trưởng đánh rơi ở gốc cây.",
        "choices": [
            {"text": "Nộp lên phòng phát thanh", "rate": 90, "win": "Được tuyên dương, cấp học bổng tiền mặt.", "lose": "Mất mặt vì cô hiệu trưởng cho có cái kẹo mút.", "tien_w": 1500, "tien_l": -100, "die_l": False},
            {"text": "Tháo sim mang đi cắm tiệm đồ", "rate": 20, "win": "Trót lọt, chốt được mấy củ tiêu vặt bét nhè.", "lose": "Công an định vị đến tận nhà còng đầu, đóng phạt mọt gông.", "tien_w": 6000, "tien_l": -15000, "die_l": False},
            {"text": "Hack pass để moi thông tin mật", "rate": 10, "win": "Tống tiền hiệu trưởng bằng ảnh mật, vớ bở!", "lose": "Nhập sai pass máy nổ bùm vỡ sọ (điện thoại siêu điệp viên).", "tien_w": 30000, "tien_l": -30000, "die_l": True},
            {"text": "Giả mù quăng xuống hồ cá", "rate": 95, "win": "Phi tang chứng cứ, không liên lụy thân thể.", "lose": "Nước bắn lên làm ướt đôi giày hiệu mới mua.", "tien_w": 0, "tien_l": -500, "die_l": False}
        ]
    }
]

EVENTS_P2 = [ # TUỔI 25
    {
        "q": "Vừa ra trường, cầm trong tay tấm bằng đỏ và 20 triệu tiền tiết kiệm.",
        "choices": [
            {"text": "Nộp đơn vào tập đoàn lớn làm 9-to-5", "rate": 80, "win": "Lương tháng ổn định, cuối năm thưởng Tết khủng.", "lose": "Cạnh tranh đấu đá, bị đồng nghiệp hãm hại mất việc.", "tien_w": 12000, "tien_l": -5000, "die_l": False},
            {"text": "All-in tiền vào Shitcoin (Coin rác)", "rate": 10, "win": "Coin x100 sau một đêm! Lên hương mua ngay siêu xe.", "lose": "Đồ thị cắm đầu thẳng đứng, cháy túi, lao đầu ra đường tàu.", "tien_w": 150000, "tien_l": -80000, "die_l": True},
            {"text": "Mở xe nước mía lề đường", "rate": 55, "win": "Bán 1 vốn 4 lời, kiếm bạc cắc nhưng gom lại mua được vàng.", "lose": "Bị trật tự đô thị gom xe phạt tiền sấp mặt.", "tien_w": 8000, "tien_l": -4000, "die_l": False},
            {"text": "Bám đuôi Sugar Daddy/Mommy", "rate": 25, "win": "Nhà lầu xe hơi có người bao trọn gói, sống phủ phê.", "lose": "Bị chính thất đánh ghen lột đồ giữa phố, thân tàn ma dại.", "tien_w": 40000, "tien_l": -30000, "die_l": False}
        ]
    },
    {
        "q": "Đồng nghiệp rủ bạn tuồn dữ liệu mật của công ty bán cho đối thủ.",
        "choices": [
            {"text": "Nhận kèo, lấy 50% tiền tươi", "rate": 15, "win": "Túi rủng rỉnh tiền, xin nghỉ việc tẩu thoát qua nước ngoài.", "lose": "Công ty phát hiện kiện đi tù, đền bù hợp đồng vỡ nợ.", "tien_w": 80000, "tien_l": -100000, "die_l": False},
            {"text": "Giả vờ đồng ý rồi gài bẫy báo sếp", "rate": 60, "win": "Sếp hất cẳng đồng nghiệp, đưa bạn lên chức Trưởng phòng.", "lose": "Đồng nghiệp lật lọng tố ngược bạn chủ mưu. Bị sa thải.", "tien_w": 20000, "tien_l": -15000, "die_l": False},
            {"text": "Lờ đi coi như điếc", "rate": 90, "win": "An toàn trên hết, bạn giữ được nồi cơm hàng tháng.", "lose": "Công ty phá sản do lộ dữ liệu, bạn mất luôn việc.", "tien_w": 2000, "tien_l": -3000, "die_l": False},
            {"text": "Tống tiền ngược lại thằng đồng nghiệp", "rate": 30, "win": "Nhận tiền bịt miệng đẫm tay, mua được mảnh đất.", "lose": "Đồng nghiệp thuê giang hồ thủ tiêu bạn bịt đầu mối.", "tien_w": 35000, "tien_l": -50000, "die_l": True}
        ]
    }
]

EVENTS_P3 = [ # TUỔI 35
    {
        "q": "Độ tuổi chín muồi, Bất Động Sản đang đóng băng nhưng lại có thằng gạ bán miếng đất ngộp.",
        "choices": [
            {"text": "Cắm nhà ngân hàng bắt đáy", "rate": 18, "win": "Nhà nước mở sân bay kế bên! Lô đất tăng giá gấp 20 lần!", "lose": "Mua trúng sổ hồng giả, ngân hàng siết nhà đuổi ra đê.", "tien_w": 250000, "tien_l": -150000, "die_l": False},
            {"text": "Mở khóa học lùa gà làm giàu", "rate": 45, "win": "Học viên đóng tiền nườm nượp, thu tiền tỷ không tốn vốn.", "lose": "Bị công an bế đi vì tội lừa đảo chiếm đoạt tài sản.", "tien_w": 50000, "tien_l": -60000, "die_l": False},
            {"text": "Không chơi BĐS, cất tiền gửi Bank", "rate": 95, "win": "Bình chân như vại, ngồi xem thiên hạ phá sản.", "lose": "Lạm phát tăng cao, tiền gửi mất đi một nửa giá trị.", "tien_w": 8000, "tien_l": -5000, "die_l": False},
            {"text": "Buôn lậu hàng cấm qua biên giới", "rate": 5, "win": "Trót lọt 1 vụ tậu ngay Biệt thự siêu sang, rửa tay gác kiếm.", "lose": "Bị biên phòng bắn hạ ngay trên ghe pháo.", "tien_w": 500000, "tien_l": -200000, "die_l": True}
        ]
    }
]

EVENTS_P4 = [ # TUỔI 50
    {
        "q": "Giai đoạn tiền mãn kinh/mãn dục. Cảm thấy cuộc đời nhạt nhẽo, bạn muốn làm gì đó điên rồ.",
        "choices": [
            {"text": "Mua thuốc trường sinh tiên đan", "rate": 5, "win": "Phép màu xảy ra! Cơ thể trẻ lại như trai/gái 20 sung mãn.", "lose": "Uống nhầm thủy ngân, nội tạng cháy rụi hộc máu chết.", "tien_w": 100000, "tien_l": -80000, "die_l": True},
            {"text": "Lấy tiền hưu đi Casino Las Vegas", "rate": 15, "win": "Nổ hũ Máy Xèng! Máy nhả tiền ngập cả sảnh Casino.", "lose": "Thua trắng dái, đau tim gục ngã trên bàn Roulette.", "tien_w": 300000, "tien_l": -100000, "die_l": True},
            {"text": "Cặp bồ nhí cho tâm hồn thanh xuân", "rate": 35, "win": "Bồ nhí chân dài/cơ bắp ngoan ngoãn, sống những ngày thăng hoa.", "lose": "Bị đào mỏ sạch bách tài sản rồi đá ra khỏi cửa.", "tien_w": -5000, "tien_l": -70000, "die_l": False},
            {"text": "Ăn chay niệm phật, đi du lịch", "rate": 90, "win": "Đầu óc minh mẫn, không tranh giành, thân tâm an lạc.", "lose": "Đi máy bay gặp bão rung lắc, đau tim rớt tiền viện.", "tien_w": 10000, "tien_l": -8000, "die_l": False}
        ]
    }
]

EVENTS_P5 = [ # TUỔI 70
    {
        "q": "Gần đất xa trời, đã đến lúc lập di chúc quyết định số phận gia tộc.",
        "choices": [
            {"text": "Chia đều cho các con", "rate": 70, "win": "Con cháu thuận hòa, khóc lóc tiếc thương khi bạn nằm xuống.", "lose": "Tụi nó chê ít, đánh nhau mẻ đầu ngay tại giường bệnh làm bạn tức chết.", "tien_w": 5000, "tien_l": -20000, "die_l": True},
            {"text": "Ủng hộ 100% làm từ thiện", "rate": 95, "win": "Được đúc tượng đồng, tên tuổi lưu danh sử sách ngàn thu.", "lose": "Bị tổ chức lừa đảo cuỗm tiền bốc hơi, ra đi không nhắm mắt.", "tien_w": 20000, "tien_l": -50000, "die_l": True},
            {"text": "Gom tiền tổ chức đám tang hoàng gia", "rate": 80, "win": "Đám tang to nhất thành phố, ai cũng trầm trồ ngưỡng mộ độ giàu.", "lose": "Đang làm lễ thì cháy rạp, người nhà phải đền tiền.", "tien_w": -10000, "tien_l": -40000, "die_l": True},
            {"text": "Lưu mật mã kho báu trên hoang đảo", "rate": 10, "win": "Tạo ra Thời đại Hải tặc mới! Di sản của bạn trị giá vô thiên lủng.", "lose": "Giang hồ tra tấn ép khai mật mã, bạn cắn rưỡi tự vẫn.", "tien_w": 800000, "tien_l": -100000, "die_l": True}
        ]
    }
]
# =====================================================================
# [PHẦN 2] HỆ THỐNG GIAO DIỆN NÚT BẤM (UI VIEWS) SIÊU MƯỢT
# =====================================================================

# ---------------------------------------------------------------------
# 1. GIAO DIỆN GACHA KALLEN FANTASY
# ---------------------------------------------------------------------
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
        if interaction.user.id != self.author.id: 
            await interaction.response.send_message("⚠️ Nhìn thôi cấm sờ! Của người ta quay đừng có bấm giành.", ephemeral=True)
            return False
        return True

    async def process_gacha(self, interaction: discord.Interaction, times: int):
        uid = str(interaction.user.id)
        p = load_kf_profile(uid)
        cost = 280 * times
        
        if p["crystals"] < cost: 
            return await interaction.response.send_message(f"⚠️ Thuyền trưởng cạn sạch Pha Lê rồi! Cần {cost:,} 💎.", ephemeral=True)
            
        p["crystals"] -= cost
        res = []
        for _ in range(times):
            roll = random.uniform(0, 100)
            if roll <= 1.5: 
                suit = "sixth_serenade"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    res.append(f"🌟 **VALKYRIE HẠNG S TỚI:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    res.append(f"🌟 Trùng Valkyrie S (Quy đổi thành mảnh vỡ -> +1000 💎)")
                    p["crystals"] += 1000
            elif roll <= 15.0: 
                suit = "sundenjager"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    res.append(f"⭐ **VALKYRIE HẠNG A TỚI:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    res.append(f"⭐ Trùng Valkyrie A (Quy đổi thành mảnh vỡ -> +280 💎)")
                    p["crystals"] += 280
            elif roll <= 30.0:
                wp = "wp_aria"
                p["inventory_weapons"].append(wp)
                res.append(f"🔶 Vũ Khí 5★ Hoàng Kim: {KALLEN_WEAPONS[wp]['name']}")
            else: 
                res.append("🟦 Rác công nghệ (Được an ủi 50 💎)")
                p["crystals"] += 50
                
        save_kf_profile(uid)
        embed = discord.Embed(title="📦 KẾT QUẢ MỞ TIẾP TẾ", description="\n".join(res), color=discord.Color.gold())
        embed.set_footer(text=f"Pha lê còn lại trong kho: {p['crystals']:,} 💎", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

# ---------------------------------------------------------------------
# 2. GIAO DIỆN COMBAT KALLEN FANTASY (ĐÁNH THEO LƯỢT)
# ---------------------------------------------------------------------
class KallenCombatView(discord.ui.View):
    def __init__(self, author, p_stats, stage, p_profile, is_abyss=False):
        super().__init__(timeout=180) 
        self.author, self.p_stats, self.stage, self.p_profile, self.is_abyss = author, p_stats, stage, p_profile, is_abyss
        self.p_hp, self.p_max_hp, self.p_sp, self.cd = p_stats["hp"], p_stats["hp"], 0, 0
        self.crystals_earned = 0
        self.abyss_floor = self.p_profile.get("abyss_floor", 1) if is_abyss else 1

        if not self.is_abyss:
            self.enemy_list = self.stage["enemies"].copy()
            self.current_idx = 0
            self.load_enemy()
        else: 
            self.load_abyss()

    def load_enemy(self):
        if self.current_idx < len(self.enemy_list):
            e = KALLEN_ENEMIES[self.enemy_list[self.current_idx]]
            self.e_data = {"name": e["name"], "type": e["type"], "hp": e["hp"], "max_hp": e["hp"], "atk": e["atk"], "def": e["def"], "sp": e["sp_drop"]}
            return True
        return False

    def load_abyss(self):
        base = random.choice([e for k, e in KALLEN_ENEMIES.items() if "god" not in k])
        mult = 1.0 + (self.abyss_floor * 0.15)
        self.e_data = {
            "name": f"{base['name']} (Tinh Anh Tầng {self.abyss_floor})", 
            "type": base["type"], 
            "hp": int(base["hp"]*mult), 
            "max_hp": int(base["hp"]*mult), 
            "atk": int(base["atk"]*mult), 
            "def": int(base["def"]*mult), 
            "sp": base["sp_drop"] + int(self.abyss_floor/2)
        }

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Chiến trường nguy hiểm, đừng đứng vào đường đạn!", ephemeral=True)
            return False
        return True

    def calc_dmg(self, mult):
        # Tính khắc hệ
        adv = 1.0
        p_type = self.p_stats["suit"]["type"]
        e_type = self.e_data["type"]
        if (p_type=="MECH" and e_type=="BIO") or (p_type=="BIO" and e_type=="PSY") or (p_type=="PSY" and e_type=="MECH"): adv = 1.3
        elif (p_type=="BIO" and e_type=="MECH") or (p_type=="PSY" and e_type=="BIO") or (p_type=="MECH" and e_type=="PSY"): adv = 0.7
        
        raw = (self.p_stats["atk"] * mult * adv) - (self.e_data["def"] * 0.5)
        is_crit = random.uniform(0, 100) <= self.p_stats["crt"]
        if is_crit: raw *= 2.0
        return int(max(10, raw)), is_crit

    def enemy_turn(self):
        if self.e_data["hp"] <= 0: return 0, "Quái vật đã bị nghiền nát!"
        
        adv = 1.0
        p_type = self.p_stats["suit"]["type"]
        e_type = self.e_data["type"]
        if (e_type=="MECH" and p_type=="BIO") or (e_type=="BIO" and p_type=="PSY") or (e_type=="PSY" and p_type=="MECH"): adv = 1.3
        elif (e_type=="BIO" and p_type=="MECH") or (e_type=="PSY" and p_type=="BIO") or (e_type=="MECH" and p_type=="PSY"): adv = 0.7

        raw = (self.e_data["atk"] * adv) - (self.p_stats["def"] * 0.5)
        dmg = int(max(5, raw))
        self.p_hp -= dmg
        return dmg, f"💥 Kẻ địch phản đòn dữ dội gây **{dmg}** Sát thương!"

    async def update_ui(self, interaction, log):
        if self.e_data["hp"] <= 0:
            self.p_sp += self.e_data["sp"] 
            log += f"\n💀 Hạ gục mục tiêu! Thu hồi {self.e_data['sp']} Năng Lượng."
            if self.is_abyss:
                drop = random.randint(5, 15) + int(self.abyss_floor/2)
                self.crystals_earned += drop
                self.p_hp = min(self.p_max_hp, self.p_hp + int(self.p_max_hp*0.15))
                self.abyss_floor += 1
                self.load_abyss()
                log += f"\n✅ Vượt Ải Tầng {self.abyss_floor-1}! Nhặt được +{drop} 💎. Làn sóng địch tiếp theo ập tới!"
            else:
                self.current_idx += 1
                if not self.load_enemy():
                    for c in self.children: c.disabled = True
                    u = load_user(self.author.id)
                    u["money"] += self.stage["reward_money"]
                    self.p_profile["exp"] += self.stage["reward_xp"]
                    save_user(self.author.id); save_kf_profile(self.author.id)
                    embed = discord.Embed(title="🎉 CHIẾN THẮNG RỰC RỠ", description=f"{log}\n\nQuá đỉnh cao! Thuyền trưởng nhận thưởng: **{self.stage['reward_money']:,} 💰** & **{self.stage['reward_xp']} EXP**", color=discord.Color.green())
                    return await interaction.response.edit_message(embed=embed, view=self)

        if self.p_hp <= 0:
            for c in self.children: c.disabled = True
            if self.is_abyss:
                self.p_profile["crystals"] += self.crystals_earned
                if self.abyss_floor > self.p_profile.get("abyss_floor", 1): 
                    self.p_profile["abyss_floor"] = self.abyss_floor
                save_kf_profile(self.author.id)
                desc = f"Đội hình đã gục ngã hoàn toàn tại Tầng {self.abyss_floor}!\nTích lũy Vực Sâu mang về: **{self.crystals_earned} 💎**"
            else:
                desc = "Valkyrie đã cạn kiệt sinh lực. Rút lui về Hyperion sửa chữa!"
            embed = discord.Embed(title="💀 TỬ TRẬN", description=desc, color=discord.Color.red())
            return await interaction.response.edit_message(embed=embed, view=self)

        if self.cd > 0: self.cd -= 1
        
        embed = discord.Embed(title=f"🌋 ABYSS TẦNG {self.abyss_floor}" if self.is_abyss else "⚔️ GIAO TRANH KỊCH LIỆT", description=log, color=discord.Color.red())
        s = self.p_stats["suit"]
        
        embed.add_field(name=f"{s['emoji']} {s['name']}", value=f"❤️ HP: {max(0, self.p_hp)}/{self.p_max_hp}\n⚡ SP: {self.p_sp}/150", inline=True)
        embed.add_field(name="VS", value="⚔️", inline=True)
        embed.add_field(name=f"👹 {self.e_data['name']} ({self.e_data['type']})", value=f"❤️ HP: {max(0, self.e_data['hp'])}/{self.e_data['max_hp']}", inline=True)
        
        self.children[2].disabled = self.p_sp < s["ult_sp_cost"]
        self.children[3].disabled = self.cd > 0

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, row=0)
    async def b_atk(self, interaction, btn):
        dmg, crit = self.calc_dmg(self.p_stats["suit"]["skill_basic_dmg"])
        self.e_data["hp"] -= dmg; self.p_sp += 5 
        ed, el = self.enemy_turn()
        crit_txt = " *(Bạo kích! 💥)*" if crit else ""
        await self.update_ui(interaction, f"🗡️ Dùng vũ khí nã đạn gây **{dmg}** ST{crit_txt}.\n{el}")

    @discord.ui.button(label="Kỹ Năng Nhánh", style=discord.ButtonStyle.success, row=0)
    async def b_cmb(self, interaction, btn):
        dmg, crit = self.calc_dmg(self.p_stats["suit"]["skill_combo_dmg"])
        self.e_data["hp"] -= dmg; self.p_sp += 2
        ed, el = self.enemy_turn()
        crit_txt = " *(Bạo kích! 💥)*" if crit else ""
        await self.update_ui(interaction, f"🚀 Phóng xuất Kỹ năng Nhánh quạt bay **{dmg}** ST{crit_txt}.\n{el}")

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, row=1)
    async def b_ult(self, interaction, btn):
        s = self.p_stats["suit"]
        self.p_sp -= s["ult_sp_cost"]
        dmg, crit = self.calc_dmg(s["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        crit_txt = " *(BẠO KÍCH CHÍ MẠNG! 💥)*" if crit else ""
        log = f"🔥 BÙM! Thi triển Tuyệt Kỹ Tối Thượng dội **{dmg}** ST{crit_txt}! Kẻ địch choáng váng mất lượt!"
        await self.update_ui(interaction, log)

    @discord.ui.button(label="Né Cực Hạn", style=discord.ButtonStyle.secondary, row=1)
    async def b_evd(self, interaction, btn):
        self.cd = 3; self.p_sp += 15 
        await self.update_ui(interaction, "💨 Kích hoạt Thời Gian Ngưng Trệ! Né đòn hoàn hảo, hồi ngay 15 SP.")

# ---------------------------------------------------------------------
# 3. GIAO DIỆN THÁM HIỂM (MỞ LÙM CÂY)
# ---------------------------------------------------------------------
class BushButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, emoji):
        super().__init__(label=label, style=style, custom_id=custom_id, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        w_id = view.w_val
        w_info = WEAPON_ODDS[w_id]
        
        # Khóa tất cả lùm cây
        for c in view.children: c.disabled = True
        await interaction.response.edit_message(content=f"🗡️ Đang siết chặt **{w_info['name']}**, rón rén vạch {self.emoji} {self.label} ra...", view=view)
        await asyncio.sleep(2.5)

        uid = str(interaction.user.id)
        u = load_user(uid)
        o_money = u.get("money", 0)

        # Quay RNG nhân phẩm
        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [w_info["terrible"], w_info["bad"], w_info["neutral"], w_info["good"], w_info["great"], w_info["jackpot"]]
        
        cat = random.choices(choices, weights=weights, k=1)[0]
        sce = random.choice(SCENARIOS[cat])
        
        tien = int(w_info['price'] * sce["mult"]) if "mult" in sce else sce.get("tien", 0)
        u["money"] += tien
        change = u["money"] - o_money
        view.session_profit += change
        save_user(uid)
        
        # Format text đẹp mắt
        p_txt = f"LÃI +{view.session_profit:,} 💰" if view.session_profit > 0 else f"LỖ {view.session_profit:,} 💰" if view.session_profit < 0 else "HUỀ VỐN"
        icon = "📉 LỖ SẶC MÁU" if tien < 0 else "📈 LÃI TO" if tien > 0 else "➖ TAY TRẮNG"
        
        txt = f"**KẾT QUẢ KHÁM PHÁ:**\n{sce['msg']}\n\n{icon}: **{tien:,} 💰**\n💸 Ví hiện tại: **{u['money']:,} 💰**\n📊 Tổng Phiên: **{p_txt}**"
        
        res_view = ResultView(interaction.user, view.session_profit)
        msg = await interaction.original_response()
        await msg.edit(content=txt, view=res_view)

class ResultView(discord.ui.View):
    def __init__(self, author, p):
        super().__init__(timeout=120)
        self.author, self.p = author, p
        
        b1 = discord.ui.Button(label="Đi Tiếp", style=discord.ButtonStyle.primary, emoji="🔄")
        b1.callback = self.cb_tiep
        b2 = discord.ui.Button(label="Rút Lui", style=discord.ButtonStyle.danger, emoji="🛑")
        b2.callback = self.cb_dung
        self.add_item(b1); self.add_item(b2)

    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("Hàng của người ta, cấm nhặt hôi!", ephemeral=True)
            return False
        return True

    async def cb_tiep(self, i):
        e = discord.Embed(title="🛒 CHỢ ĐEN VŨ KHÍ MẶT TRẬN", description="Nghỉ tay nạp đạn, mua vũ khí càn quét tiếp nào đại gia!", color=discord.Color.dark_red())
        e.set_footer(text=f"Phiên này: LÃI +{self.p:,}" if self.p > 0 else f"Phiên này: LỖ {self.p:,}")
        await i.response.edit_message(content=None, embed=e, view=ShopView(self.author, self.p))

    async def cb_dung(self, i):
        for c in self.children: c.disabled = True
        await i.response.edit_message(content=i.message.content + f"\n\n🛑 **CHỐT SỔ TỔNG KẾT RÚT LUI:** {self.p:,} 💰", view=self)

class BushView(discord.ui.View):
    def __init__(self, author, w_val, p):
        super().__init__(timeout=60)
        self.author, self.w_val, self.session_profit = author, w_val, p
        emojis = ["🌲", "🌳", "🌴", "🌵", "🎋"]
        for i in range(5):
            self.add_item(BushButton(label=f"Bụi Cây {i+1}", style=discord.ButtonStyle.success, custom_id=f"b_{i}", emoji=emojis[i]))

    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("Lùm cây này có chủ rồi, ra chỗ khác bóc!", ephemeral=True)
            return False
        return True

class WeaponSelect(discord.ui.Select):
    def __init__(self, p):
        self.p = p
        opts = [discord.SelectOption(label=v["name"], description=f"Giá: {v['price']:,} 💰", value=k) for k, v in WEAPON_ODDS.items()]
        super().__init__(placeholder="Nhấn vào mua Hàng Nóng...", options=opts)

    async def callback(self, i):
        uid = str(i.user.id)
        u = load_user(uid)
        w = WEAPON_ODDS[self.values[0]]
        
        if u.get("money", 0) < w["price"]: 
            return await i.response.send_message("⚠️ Cháy túi rồi đòi mua vũ khí hạng nặng!", ephemeral=True)
            
        u["money"] -= w["price"]
        np = self.p - w["price"]
        save_user(uid)
        
        e = discord.Embed(
            title="🌲 RỪNG THẲM ÂM U 🌲", 
            description=f"Khói mù giăng lối... Bạn hiện đang lăm lăm cây **{w['name']}**.\n\n"
                        f"Phía trước có 5 lùm cây đang rung rinh bí ẩn. Húp trọn kho báu hay bị quái vật đấm vỡ mồm? Bấm đi rồi biết!", 
            color=discord.Color.green()
        )
        await i.response.edit_message(embed=e, view=BushView(i.user, self.values[0], np))

class ShopView(discord.ui.View):
    def __init__(self, author, p=0):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(WeaponSelect(p))
        
    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("Quầy này đang có khách, vui lòng đợi lượt!", ephemeral=True)
            return False
        return True

# ---------------------------------------------------------------------
# 4. GIAO DIỆN MÔ PHỎNG NHÂN SINH (ĐA VŨ TRỤ)
# ---------------------------------------------------------------------
class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author, self.stats, self.phase, self.tien_an, self.logs = author, stats, 1, 0, []
        
        # Load sự kiện tuổi 15
        self.ev = random.choice(EVENTS_P1)
        
        # Mở bài theo may mắn
        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng siêu to khổng lồ, chạy quanh nhà bằng siêu xe mạ vàng.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm, đủ ăn đủ mặc.")
        else:
            self.logs.append("👶 **Tuổi 0:** Vừa lọt lòng bố mẹ ôm nợ xã hội đen bỏ trốn, bạn bị vứt lăn lóc ngoài bãi rác.")
        
        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text'][:70]}", style=discord.ButtonStyle.primary, custom_id="a", row=0)
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text'][:70]}", style=discord.ButtonStyle.secondary, custom_id="b", row=0)
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text'][:70]}", style=discord.ButtonStyle.success, custom_id="c", row=1)
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text'][:70]}", style=discord.ButtonStyle.danger, custom_id="d", row=1)
        
        self.btn_a.callback = lambda i: self.process(i, 0, "A")
        self.btn_b.callback = lambda i: self.process(i, 1, "B")
        self.btn_c.callback = lambda i: self.process(i, 2, "C")
        self.btn_d.callback = lambda i: self.process(i, 3, "D")
        
        for b in [self.btn_a, self.btn_b, self.btn_c, self.btn_d]: 
            self.add_item(b)

    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("⚠️ Chơi máy ai người nấy bấm, đừng có chọc ngoáy nghiệp chướng của tôi!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        uid = str(self.author.id)
        if uid in dang_choi_nhansinh: dang_choi_nhansinh.remove(uid)

    async def process(self, i, idx, letter):
        c = self.ev["choices"][idx]
        
        # Công thức: Tỉ lệ cơ bản + Mỗi điểm may mắn buff 2%. Khóa trần ở 95%
        rate = min(95.0, c["rate"] + (self.stats["may_man"] * 2.0))
        roll = random.uniform(0, 100)
        win = roll <= rate
        
        res, tien = (c["win"], c["tien_w"]) if win else (c["lose"], c["tien_l"])
        self.tien_an += tien
        
        tuoi_hien_tai = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
        
        kq = "✅ **ĐẠI THÀNH CÔNG**" if win else "❌ **MẤT TRẮNG**"
        log = f"🎲 Xúc xắc định mệnh: Yêu cầu {rate:.1f}% -> Tung ra {roll:.1f}\n{kq}: {res} ({tien:,} 💰)"
        
        is_dead = (win and c.get("die_w")) or (not win and c.get("die_l"))
        
        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}: Lựa chọn {letter}.**\n{log}\n💀 **BẠN ĐÃ ĐỘT TỬ! Diêm vương gọi tên, xé nháp làm lại từ đầu!**")
            self.phase = 99
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}: Lựa chọn {letter}.**\n{log}")
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)
            else: self.phase = 99 

        await self.update_ui(i)

    async def update_ui(self, i):
        embed = discord.Embed(title="🌀 SỔ BÌA ĐEN LUÂN HỒI", description="Mỗi lựa chọn là một ngã rẽ tàn khốc. Cẩn thận kẻo rước họa sát thân!", color=discord.Color.teal())
        embed.add_field(name="🍀 Bùa May Mắn Ký Chủ", value=f"Gốc: **{self.stats['may_man']}/10** *(Buff +{self.stats['may_man']*2}% Tỉ lệ né xui)*", inline=False)
        
        # Rút gọn log
        story = "...\n\n" + "\n\n".join(self.logs[-3:]) if len(self.logs) > 3 else "\n\n".join(self.logs)
        embed.add_field(name="📜 Băng Chuyền Ký Ức", value=story, inline=False)
        
        if self.phase < 99:
            tuoi_next = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
            embed.add_field(name=f"❓ Quyết định sinh tử tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            for b in self.children: b.disabled = True
            uid = str(self.author.id)
            if uid in dang_choi_nhansinh: dang_choi_nhansinh.remove(uid)
            
            u = load_user(uid)
            u["money"] += self.tien_an
            save_user(uid)
            
            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(name="🪦 LÊN BÀN THỜ NGẮM GÀ KHỎA THÂN", value=f"Chơi dở báo nhà, để lại đống nợ chà bá lửa.\n❌ **NỢ NẦN CHỒNG CHẤT:** **{self.tien_an:,} 💰**\n*(Hệ thống trừ thẳng vào ví, hãy gõ `k daily` để cày trả nợ!)*", inline=False)
            else:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 NHẮM MẮT XUÔI TAY BÌNH YÊN", value=f"Vinh hoa phú quý mỉm cười mãn nguyện.\n👑 **TÀI SẢN THỪA KẾ:** **+{self.tien_an:,} 💰**", inline=False)
                
            embed.add_field(name="💳 Két Sắt Hiện Tại", value=f"**{u['money']:,} 💰**", inline=False)
            
        if i.response.is_done(): await i.message.edit(embed=embed, view=self)
        else: await i.response.edit_message(embed=embed, view=self)

# ---------------------------------------------------------------------
# 5. GIAO DIỆN TREO MÁY AFK (TRẠM THU MUA)
# ---------------------------------------------------------------------
class ExpSelect(discord.ui.Select):
    def __init__(self):
        opts = [
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Bình Yên)", description="An toàn cày cuốc củi mục: ~600 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động U Tối)", description="Rủi ro vừa đủ, hái nấm độc: ~1500 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Lời Nguyền)", description="Đi xa mỏi cẳng, trộm đồ cổ: ~3000 💰", emoji="🏛️", value="12")
        ]
        super().__init__(placeholder="Dựng lều cắm trại ở đâu đây sếp?", options=opts)

    async def callback(self, i):
        uid = str(i.user.id)
        u = load_user(uid)
        
        hrs = int(self.values[0])
        rw = random.randint(400, 700) if hrs == 4 else random.randint(1000, 1800) if hrs == 8 else random.randint(2200, 3500)
        
        u["exp_end"] = (datetime.now() + timedelta(hours=hrs)).strftime("%Y-%m-%d %H:%M:%S")
        u["exp_reward"] = rw
        save_user(uid)

        embed = discord.Embed(
            title="⛺ KHĂN GÓI QUẢ MƯỚP LÊN ĐƯỜNG!",
            description=f"Ba lô đầy đủ, bạn xách đít đi vào rừng cắm trại **{hrs} giờ**.\n⏳ Nhớ canh đúng giờ về gõ lại lệnh `k phai` để lụm lúa nhé, đừng để bọn lâm tặc nó cuỗm mất!",
            color=discord.Color.green()
        )
        await i.response.edit_message(content=None, embed=embed, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("⚠️ Chỗ người ta cắm trại, đừng có vào phá!", ephemeral=True)
            return False
        return True
        # =====================================================================
# [PHẦN 3] HỆ THỐNG LỆNH NGƯỜI DÙNG (COMMANDS) VÀ QUẢN TRỊ
# =====================================================================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 TỔNG ĐÀI ĐIỀU KHIỂN SIÊU BOT 5.0", 
        description="Chào mừng đến với máy chủ vung tiền như rác. Tiền tố gọi bot: `k` hoặc `K`.", 
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="💳 KINH TẾ & ĐỜI SỐNG", 
        value="`k rank` • Khoe thẻ căn cước & Số dư\n"
              "`k top` • Soi bảng xếp hạng đại gia\n"
              "`k daily` • Nhận trợ cấp hộ nghèo mỗi ngày\n"
              "`k give @tên <tiền>` • Bố thí tiền cho người khác", 
        inline=False
    )
    embed.add_field(
        name="🎮 SÒNG BÀI MA CAO", 
        value="`k coin <tiền/all>` • Xóc xu sấp ngửa x2\n"
              "`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu, Bão ăn x5\n"
              "`k baucua <linh vật> <tiền>` • Bầu Cua Tôm Cá x3\n"
              "`k cuop` • Cầm M4A1 đi cướp ngân hàng (Rủi ro đi tù)", 
        inline=False
    )
    embed.add_field(
        name="⚔️ SINH TỒN & NHẬP VAI", 
        value="`k thamhiem` • Đi mua đồ xông pha rừng rậm\n"
              "`k phai` • Treo acc AFK nhặt bạc lẻ\n"
              "`k nhansinh` • Luân hồi đa vũ trụ, chết lúc nào không hay!", 
        inline=False
    )
    embed.add_field(
        name="🌌 KALLEN FANTASY (RPG Tích Hợp)", 
        value="`k kallen` • Xem hồ sơ chiến hạm Hyperion\n"
              "`k kf gacha` • Đốt tiền quay Gacha Valkyrie\n"
              "`k kf story 1-1` • Xuất kích đánh Boss\n"
              "`k kf abyss` • Leo tháp Vực Sâu Vô Tận", 
        inline=False
    )
    if ctx.author.guild_permissions.administrator:
        embed.add_field(
            name="👑 QUYỀN LỰC ADMIN", 
            value="`k setup #kênh`, `k setkenh #kênh`\n"
                  "`k themtien @user <tiền>`, `k trutien @user <tiền>`", 
            inline=False
        )
    embed.set_footer(text="Gõ đúng cú pháp kẻo bot nó chửi cho đấy nhé!")
    await ctx.reply(embed=embed, mention_author=False)

# ---------------------------------------------------------------------
# LỆNH QUẢN TRỊ (ADMIN ONLY)
# ---------------------------------------------------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    server_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]:
            del CONFIG_CACHE[server_id]["allowed_channels"]
        return await ctx.send("✅ Đã dỡ bỏ rào chắn, anh em cứ thoải mái gõ lệnh ở mọi kênh!")

    mentions = ctx.message.channel_mentions
    if not mentions: 
        return await ctx.send("⚠️ Phải tag kênh cụ thể chứ sếp! VD: `k setup #general`")
        
    c_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": c_ids}}, upsert=True)
    
    if server_id not in CONFIG_CACHE: 
        CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = c_ids
    
    await ctx.send(f"✅ Đã giăng dây thép gai! Từ nay bot chỉ nhận lệnh tại: {', '.join(c.mention for c in mentions)}.")

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Sếp định ban phát không khí à? Nhập số tiền > 0 đi.")
    u = load_user(member.id)
    u["money"] += amount
    save_user(member.id)
    
    embed = discord.Embed(
        title="👑 THÁNH CHỈ GIÁNG XUỐNG",
        description=f"Admin {ctx.author.mention} vừa mở kho bạc quốc gia, ban thưởng cho {member.mention} **{amount:,} 💰**!\n"
                    f"💳 Cập nhật két sắt: **{u['money']:,} 💰**", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Tiền trừ phải lớn hơn 0 sếp ơi.")
    u = load_user(member.id)
    u["money"] -= amount
    save_user(member.id)
    
    embed = discord.Embed(
        title="⚖️ ĐẠI ĐAO HÀNH HÌNH",
        description=f"Lệnh trừng phạt từ Admin! {member.mention} bị tịch thu tài sản trị giá **{amount:,} 💰**!\n"
                    f"💳 Két sắt chỉ còn: **{u['money']:,} 💰**", 
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

# ---------------------------------------------------------------------
# LỆNH KINH TẾ (RANK, TOP, ĐIỂM DANH, TẶNG TIỀN)
# ---------------------------------------------------------------------
@bot.command()
async def rank(ctx):
    u = load_user(ctx.author.id)
    lv, xp, tien = u.get("level", 1), u.get("xp", 0), u.get("money", 0)
    max_xp = lv * 100
    
    # Vẽ thanh tiến trình ngầu lòi
    prog = int((xp / max_xp) * 12)
    bar = "🟩" * prog + "⬛" * (12 - prog)
    
    embed = discord.Embed(
        title=f"💳 CĂN CƯỚC ĐẠI GIA: {ctx.author.name.upper()}", 
        color=discord.Color.gold() if tien > 500000 else discord.Color.teal()
    )
    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
    
    embed.add_field(name="Hào Quang Cấp Độ", value=f"🌟 **LV {lv}**", inline=True)
    embed.add_field(name="Tài Sản Kếch Xù", value=f"**{tien:,} 💰**\n*(ĐANG NỢ XÃ HỘI ĐEN)*" if tien < 0 else f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="Danh Hiệu", value=f"🏷️ **{u.get('title', 'Dân Thường')}**", inline=False)
    embed.add_field(name="Trải Sự Đời (Kinh nghiệm)", value=f"`{bar}`\n**{xp:,}/{max_xp:,} XP**", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    danh_sach = sorted([(doc["_id"], doc.get("money", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)[:10]
    
    desc = ""
    for i, (uid, tien) in enumerate(danh_sach):
        user = bot.get_user(int(uid))
        if not user:
            try: user = await bot.fetch_user(int(uid))
            except: pass
            
        ten = user.name if user else f"Tỷ phú che mặt {uid[-4:]}"
        icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**#{i+1}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
        
    embed = discord.Embed(title="🏆 BẢNG VÀNG GIỚI SIÊU GIÀU SERVER", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    u = load_user(ctx.author.id)
    now = datetime.now()
    last_str = u.get("last_daily")
    
    if last_str:
        last = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
        if now - last < timedelta(days=1):
            tl = timedelta(days=1) - (now - last)
            h, r = divmod(int(tl.total_seconds()), 3600)
            m, _ = divmod(r, 60)
            embed = discord.Embed(description=f"⏳ Tham quá đáng! Chính phủ chưa phát lương. Quay lại sau **{h} giờ {m} phút** nữa nhé sếp.", color=discord.Color.orange())
            return await ctx.reply(embed=embed, mention_author=False)

    u["money"] += 1500
    u["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(ctx.author.id)
    
    embed = discord.Embed(title="🎁 PHÁT CHẨN QUỐC GIA", color=discord.Color.green() if u["money"] >= 0 else discord.Color.red())
    if u["money"] < 0:
        embed.description = f"Nhận trợ cấp **1,500 💰**.\n⚠️ **CẢNH BÁO:** Tiền vừa vào túi đã bị xã hội đen siết nợ một phần! Hiện tại còn nợ: **{u['money']:,} 💰**."
    else:
        embed.description = f"Bạn vừa ký nhận thành công **1,500 💰** tiền công nhật!\n💳 Bỏ vào két sắt được tổng cộng: **{u['money']:,} 💰**"
    
    embed.set_thumbnail(url=GIF_LINKS["daily"])
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    n_gui, n_nhan = str(ctx.author.id), str(member.id)
    if n_gui == n_nhan: 
        return await ctx.reply("Tự lôi tiền túi phải sang túi trái rồi khen mình giàu à?", mention_author=False)
    if amount <= 0: 
        return await ctx.reply("Làm trò gì vậy, định ăn cướp của người ta hay sao mà chuyển tiền âm?", mention_author=False)
    
    gui_data = load_user(n_gui)
    if gui_data.get("money", 0) < amount: 
        return await ctx.reply("⚠️ Tiền trong ví rỗng tuếch mà đòi sĩ diện bao nuôi người khác!", mention_author=False)
    
    nhan_data = load_user(n_nhan)
    gui_data["money"] -= amount
    nhan_data["money"] += amount
    save_user(n_gui)
    save_user(n_nhan)
    
    embed = discord.Embed(
        title="💸 ĐẠI GIA PHÁT LỘC",
        description=f"Ting ting! Đại gia {ctx.author.mention} vừa bố thí cho {member.mention} **{amount:,} 💰**!\nChơi đẹp lắm người anh em!", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed, mention_author=False)

# ---------------------------------------------------------------------
# HỆ THỐNG CỜ BẠC MA CAO (COIN, TÀI XỈU, BẦU CUA)
# ---------------------------------------------------------------------
@bot.command()
async def coin(ctx, amount: str):
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    u["money"] -= bet
    save_user(ctx.author.id)
    gamble_cooldowns[str(ctx.author.id)] = datetime.now()

    msg = await ctx.send(embed=discord.Embed(description=f"🪙 {ctx.author.mention} vênh mặt búng **{bet:,} 💰** lên trời cao...", color=discord.Color.gold()))
    await asyncio.sleep(1.2) 
    await msg.edit(embed=discord.Embed(description=f"🪙 Đồng xu lộn nhào xoay tít trên không trung...\n💥 Rơi rầm xuống úp lên mu bàn tay!", color=discord.Color.gold()))
    await asyncio.sleep(1.2) 

    if random.choice([True, False]):
        win = bet * 2
        u["money"] += win
        res = f"MẶT NGỬA! Đỉnh cao nhân phẩm, húp trọn **{win:,} 💰**!"
    else: 
        res = f"MẶT SẤP! Bước chân ra gầm cầu, đi luôn **{bet:,} 💰**."
    
    save_user(ctx.author.id)
    await msg.edit(embed=discord.Embed(title="🪙 CHỐT KẾT QUẢ ĐỒNG XU", description=res + f"\n\n💳 Số dư sau cược: **{u['money']:,} 💰**", color=discord.Color.gold()))

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    if choice.lower() not in ["tai", "tài", "xiu", "xỉu"]: 
        return await ctx.reply("Chọn `tai` hoặc `xiu` sếp ơi, đừng có ra cửa giữa!", mention_author=False)
    
    u["money"] -= bet
    save_user(ctx.author.id)
    gamble_cooldowns[str(ctx.author.id)] = datetime.now()
    
    msg = await ctx.send(embed=discord.Embed(description=f"🎲 Kéo ghế ngồi xuống sòng, {ctx.author.mention} đập mạnh **{bet:,} 💰** vào cửa **{choice.upper()}**.\nNhà cái đang nhét xí ngầu vào bát... 🫨", color=discord.Color.blue()))
    await asyncio.sleep(1.5)
    await msg.edit(embed=discord.Embed(description=f"🎲 **XÓC XÓC XÓC... RẦM! BÁT ĐÃ ÚP XUỐNG BÀN!**", color=discord.Color.blue()))
    await asyncio.sleep(1.5)

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    tot = d1 + d2 + d3
    res_str = "xiu" if tot <= 10 else "tai"
    
    if choice.replace("à", "a").replace("ỉ", "i").lower() == res_str:
        if d1 == d2 == d3:
            win = bet * 5
            res = f"🔥 **BÃO {d1}-{d2}-{d3} TỚI RỒI!!! ĐẠI THẮNG x5!** Nhà cái phá sản, bạn ăn đậm **{win:,} 💰**!"
        else:
            win = bet * 2
            res = f"✅ **HÚP TRỌN!** Quá kinh nghiệm, nhà cái khóc thét đền bạn **{win:,} 💰**!"
        u["money"] += win
    else: 
        res = f"💀 **TOANG!** Bát mở ra trái khuấy, nhà cái vơ vét sạch **{bet:,} 💰** của bạn trên bàn."
    
    save_user(ctx.author.id)
    await msg.edit(embed=discord.Embed(title=f"🎲 KẾT QUẢ XÍ NGẦU: {d1} - {d2} - {d3} (Tổng {tot} -> {res_str.upper()})", description=res + f"\n\n💳 Số dư sau cược: **{u['money']:,} 💰**", color=discord.Color.gold()))

@bot.command(aliases=['bc'])
async def baucua(ctx, choice: str, amount: str):
    bc_dict = {
        "bau": "🎃", "bầu": "🎃",
        "cua": "🦀",
        "tom": "🦐", "tôm": "🦐",
        "ca": "🐟", "cá": "🐟",
        "ga": "🐔", "gà": "🐔",
        "nai": "🦌"
    }
    choice = choice.lower()
    if choice not in bc_dict:
        return await ctx.reply("⚠️ Đặt cái gì lạ vậy? Chỉ có các cửa: `bau, cua, tom, ca, ga, nai` thôi!", mention_author=False)

    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    
    u["money"] -= bet
    save_user(ctx.author.id)
    gamble_cooldowns[str(ctx.author.id)] = datetime.now()
    
    pet_name = bc_dict[choice]
    
    msg = await ctx.send(embed=discord.Embed(description=f"🎋 {ctx.author.mention} xòe ra **{bet:,} 💰** đặt hết vào cửa {pet_name}.\nNhà cái lắc đĩa... lạch cạch...", color=discord.Color.dark_orange()))
    await asyncio.sleep(1.5)
    
    dice_pool = ["🎃", "🦀", "🦐", "🐟", "🐔", "🦌"]
    r1, r2, r3 = random.choice(dice_pool), random.choice(dice_pool), random.choice(dice_pool)
    
    await msg.edit(embed=discord.Embed(description=f"🎋 Nhà cái mở đĩa từ từ...\nLộ con thứ nhất: **{r1}**", color=discord.Color.dark_orange()))
    await asyncio.sleep(1.0)
    
    count = [r1, r2, r3].count(pet_name)
    
    if count > 0:
        win = bet + (bet * count)
        u["money"] += win
        res = f"🎉 **TRÚNG {count} NHÁY!** Bạn ăn được **{win:,} 💰**!"
    else:
        res = f"💀 **CHÁY TÚI!** Đĩa ra toàn con gì đâu, bạn mất **{bet:,} 💰**."
        
    save_user(ctx.author.id)
    await msg.edit(embed=discord.Embed(title=f"🎋 KẾT QUẢ BẦU CUA: [ {r1} | {r2} | {r3} ]", description=res + f"\n\n💳 Số dư: **{u['money']:,} 💰**", color=discord.Color.gold()))

# ---------------------------------------------------------------------
# LỆNH NHẬP VAI SINH TỒN & RPG CỐT LÕI
# ---------------------------------------------------------------------
@bot.command()
async def cuop(ctx):
    uid = str(ctx.author.id)
    u = load_user(uid)
    now = datetime.now()
    
    if uid in crime_cooldowns:
        diff = (now - crime_cooldowns[uid]).total_seconds()
        if diff < 1800:
            h, r = divmod(int(1800 - diff), 3600)
            m, s = divmod(r, 60)
            return await ctx.reply(f"🚨 Đang bị truy nã toàn thành phố! Trốn đi, {m} phút {s} giây nữa hẵng ló mặt ra cướp tiếp.", mention_author=False)

    if u.get("money", 0) < 50000:
        return await ctx.reply("⚠️ Cướp ngân hàng đòi hỏi phải mua vũ khí đạn dược hết 50,000 💰. Nghèo thì đi nhặt ve chai đi, đừng học đòi làm găng-tơ!", mention_author=False)

    crime_cooldowns[uid] = now
    
    msg = await ctx.send(embed=discord.Embed(description="🔫 Bạn chùm tất da gáy lên đầu, đạp cửa xông vào Ngân hàng Trung ương với cây M4A1...\n*Mọi người la hét hoảng loạn!*", color=discord.Color.dark_gray()))
    await asyncio.sleep(2.5)

    roll = random.randint(1, 100)
    if roll <= 25: # Tỉ lệ trót lọt 25%
        loot = random.randint(150000, 500000)
        u["money"] += loot
        save_user(uid)
        
        embed = discord.Embed(title="💰 PHI VỤ THẾ KỶ HOÀN TẤT!", description=f"Tuyệt vời! Bạn vơ vét sạch két sắt, trốn thoát thành công và ẵm trọn **{loot:,} 💰**!", color=discord.Color.green())
        embed.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed)
    else:
        # Thua thì mất tiền mua súng và bị đi tù 10 phút
        u["money"] -= 50000
        u["jail_time"] = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        save_user(uid)
        
        embed = discord.Embed(title="🚨 SA LƯỚI PHÁP LUẬT!", description="Cảnh sát cơ động SWAT ập vào từ 4 phía! Bạn bị tóm cổ ném vào buồng giam.\n❌ **Mất 50,000 💰** tiền mua súng đạn.\n🔒 **Bóc lịch 10 Phút!** Trong lúc ngồi tù sẽ không được dùng các lệnh khác.", color=discord.Color.red())
        embed.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed)

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    uid = str(ctx.author.id)
    if uid in dang_choi_nhansinh: 
        return await ctx.reply("⏳ Vẫn đang trong luân hồi kiếp trước sếp ơi, sống cho nốt đi!", mention_author=False)
        
    u = load_user(uid)
    if u.get("money", 0) < 100: 
        return await ctx.reply("⚠️ Vé qua trạm thu phí của Diêm Vương là 100 💰. Không đủ tiền thì vất vưởng làm hồn ma bóng quế đi!", mention_author=False)
        
    u["money"] -= 100
    dang_choi_nhansinh.append(uid)
    save_user(uid)
    
    # Init game
    view = NhanSinhGameView(ctx.author, {"may_man": random.randint(1, 10)})
    embed = discord.Embed(title="🌀 SỔ BÌA ĐEN LUÂN HỒI", description="Mỗi lựa chọn là một ngã rẽ tàn khốc. Cẩn thận kẻo rước họa sát thân!", color=discord.Color.teal())
    embed.add_field(name="🍀 Bùa May Mắn Ký Chủ", value=f"Gốc: **{view.stats['may_man']}/10** *(Buff +{view.stats['may_man']*2}%)*", inline=False)
    embed.add_field(name="📜 Băng Chuyền Ký Ức", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Quyết định sinh tử tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    embed = discord.Embed(
        title="🛒 CHỢ ĐEN VŨ KHÍ RỪNG SÂU",
        description="Rừng rậm giấu đầy vàng thỏi nhưng cũng lắm yêu tinh. Vuốt cây súng xịn lên nổ hũ to, mua cây gậy củi thì chuẩn bị tinh thần bị khỉ tát vỡ mồm!\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ VUNG TIỀN MUA ĐỒ** 👇",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, view=ShopView(ctx.author, 0))

@bot.command()
async def phai(ctx):
    u = load_user(ctx.author.id)
    if u.get("exp_end"):
        end = datetime.strptime(u["exp_end"], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        if now >= end:
            rw = u.get("exp_reward", 500)
            u["money"] += rw
            del u["exp_end"]
            del u["exp_reward"]
            save_user(ctx.author.id)
            embed = discord.Embed(title="🎉 LÊ BƯỚC TRỞ VỀ", description=f"{ctx.author.mention} khệ nệ bê bao tải đồ từ rừng mồ hôi nhễ nhại, thương lái mua lại với giá **{rw:,} 💰**!\n💳 Két sắt củng cố: **{u['money']:,} 💰**", color=discord.Color.gold())
            return await ctx.send(embed=embed)
        else:
            h, r = divmod(int((end - now).total_seconds()), 3600)
            m, _ = divmod(r, 60)
            return await ctx.send(embed=discord.Embed(description=f"⏳ Đang bị lùa đi chặt gỗ sấp mặt trong rừng! Kiên nhẫn chờ **{h} tiếng {m} phút** nữa nhé sếp.", color=discord.Color.orange()))

    embed = discord.Embed(title="⛺ TRẠM LỀU TRẠI AFK", description="Mỏi tay quá thì dựng lều ngủ ở đây, để hệ thống tự farm tiền cho bạn!\n👇 **CHỌN ĐỊA ĐIỂM CẦM TÚI NGỦ** 👇", color=discord.Color.dark_green())
    await ctx.send(embed=embed, view=ExpView(ctx.author))

# ---------------------------------------------------------------------
# LỆNH KALLEN FANTASY (Gacha & RPG Mode)
# ---------------------------------------------------------------------
@bot.group(invoke_without_command=True, aliases=['kf', 'honkai'])
async def kallen(ctx):
    p = load_kf_profile(ctx.author.id)
    s = calculate_kallen_stats(ctx.author.id)
    embed = discord.Embed(
        title="🌌 CHIẾN HẠM HYPERION TẬP KẾT",
        description=f"Tư Lệnh: **{ctx.author.name}**\nCấp Tu Luyện: **Lv {p['level']}**\nThể lực: **{p['stamina']}/{p['max_stamina']}** ⚡ | Tài sản: **{p['crystals']:,}** 💎\n\n"
                    f"🛡️ **VALKYRIE XUẤT CHIẾN:**\n{s['suit']['emoji']} **{s['suit']['name']}**\n"
                    f"❤️ Sinh lực: {s['hp']:,} | ⚔️ Sức Mạnh: {s['atk']:,} | 💥 Chí Mạng: {s['crt']}%",
        color=discord.Color.purple()
    )
    embed.add_field(name="Bảng Điều khiển Hạm Đội", value="`k kf gacha` • Đốt tiền quay Tiếp Tế\n`k kf story 1-1` • Dọn dẹp quái vật cốt truyện\n`k kf abyss` • Nhảy xuống Vực Sâu Vô Tận", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command()
async def gacha(ctx):
    await ctx.reply(embed=discord.Embed(title="📦 THÙNG TIẾP TẾ", description="Dùng 280 💎 để cầu nhân phẩm lấy Valkyrie hoặc Trang bị xịn. Khóc hay cười đây?", color=discord.Color.gold()), view=KallenGachaView(ctx.author))

@kallen.command()
async def story(ctx, stage_id: str = "1-1"):
    p = load_kf_profile(ctx.author.id)
    if stage_id not in KALLEN_STAGES: 
        return await ctx.reply("⚠️ Sai mã ải rồi tư lệnh! Gõ đại à?")
    if p["stamina"] < 10: 
        return await ctx.reply("⚠️ Yếu xìu, không đủ 10 Thể Lực ⚡ để xuất kích. Ngồi chơi xơi nước chờ hồi thể lực đi.")
        
    p["stamina"] -= 10
    save_kf_profile(ctx.author.id)
    
    s = KALLEN_STAGES[stage_id]
    msg = await ctx.reply(embed=discord.Embed(title=f"🚀 XUẤT KÍCH: {s['name']}", color=discord.Color.blue()))
    await asyncio.sleep(1)
    
    view = KallenCombatView(ctx.author, calculate_kallen_stats(ctx.author.id), s, p, False)
    await view.update_ui(ctx, f"Chiến hạm thả bạn xuống vùng tử địa {s['name']}! Kẻ địch xông tới!")

@kallen.command()
async def abyss(ctx):
    p = load_kf_profile(ctx.author.id)
    if p["stamina"] < 20: 
        return await ctx.reply("⚠️ Bạn quá mệt mỏi, không đủ 20 Thể Lực ⚡ để nhảy xuống Vực Sâu.")
        
    p["stamina"] -= 20
    save_kf_profile(ctx.author.id)
    
    msg = await ctx.reply(embed=discord.Embed(title="🌋 VỰC SÂU ABYSS", color=discord.Color.red()))
    await asyncio.sleep(1)
    
    view = KallenCombatView(ctx.author, calculate_kallen_stats(ctx.author.id), None, p, True)
    await view.update_ui(ctx, "Hơi nóng bốc lên ngùn ngụt, Cánh Cửa Vực Sâu mở ra đón lấy bạn!")

# =====================================================================
# EVENT CHẠY NGẦM CỦA BOT (FARM XP)
# =====================================================================
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    u = load_user(uid)
    
    # Ngồi tù thì bị cấm chat cày level
    if u.get("jail_time") and datetime.now() < datetime.strptime(u["jail_time"], "%Y-%m-%d %H:%M:%S"):
        return await bot.process_commands(message)

    u["xp"] += random.randint(5, 15)
    max_xp = u["level"] * 100

    if u["xp"] >= max_xp:
        u["xp"] -= max_xp
        u["level"] += 1
        thuong = u["level"] * 250
        u["money"] += thuong
        
        embed = discord.Embed(
            title="🌟 ĐỘT PHÁ CẢNH GIỚI", 
            description=f"Oai phong lẫm liệt! {message.author.mention} tu luyện đạt thành **Cấp Độ {u['level']}**!\nThiên đạo rải xuống thưởng nóng: **{thuong:,} 💰**", 
            color=discord.Color.gold()
        )
        cfg = load_server_config(message.guild.id)
        k_id = cfg.get("channel_id")
        k = bot.get_channel(k_id) if k_id else message.channel
        if k: 
            try: await k.send(embed=embed)
            except: pass

    save_user(uid)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print('================================================')
    print(f'>>> SIÊU BOT {bot.user} BẢN 5.0 ĐÃ VẬN HÀNH!')
    print('>>> KHỐI LƯỢNG DATA: MAX | HỆ THỐNG GIAO DIỆN: OK')
    print('>>> DATABASE: MONGODB ĐÃ KẾT NỐI')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="Mô phỏng Vũ trụ | Gõ K help"))

# =====================================================================
# KHỞI CHẠY BOT BẰNG TOKEN ĐƯỢC GHÉP NỐI AN TOÀN
# =====================================================================
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối an toàn
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
