import discord
from discord.ext import commands
from keep_alive import keep_alive 
import json 
import os
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

# =====================================================================
# KẾT NỐI MONGODB VÀ BỘ ĐỆM
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]
users_col = db["users"]   
config_col = db["config"] 

DB_CACHE = {}
CONFIG_CACHE = {}

def load_user(user_id):
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        doc = users_col.find_one({"_id": user_id})
        if doc:
            DB_CACHE[user_id] = doc
        else:
            DB_CACHE[user_id] = {
                "xp": 0, "level": 1, "money": 0, 
                "title": "Dân Thường 🚶", "assets": [], "pets": {}
            }
    # Khởi tạo mặc định nếu data cũ bị thiếu
    if "title" not in DB_CACHE[user_id]: DB_CACHE[user_id]["title"] = "Dân Thường 🚶"
    if "assets" not in DB_CACHE[user_id]: DB_CACHE[user_id]["assets"] = []
    if "pets" not in DB_CACHE[user_id]: DB_CACHE[user_id]["pets"] = {}
    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE:
        users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

def load_server_config(server_id):
    server_id = str(server_id)
    if server_id not in CONFIG_CACHE:
        doc = config_col.find_one({"_id": server_id})
        if doc: CONFIG_CACHE[server_id] = doc
        else: CONFIG_CACHE[server_id] = {}
    return CONFIG_CACHE[server_id]

@bot.check
async def channel_restriction_check(ctx):
    if ctx.author.guild_permissions.administrator: return True
    if not ctx.guild: return True
    config = load_server_config(ctx.guild.id)
    allowed_channels = config.get("allowed_channels", [])
    if allowed_channels and ctx.channel.id not in allowed_channels: return False
    return True

def make_progress_bar(current, total, length=10):
    progress = int((current / total) * length)
    return "█" * progress + "░" * (length - progress)


# =====================================================================
# HÀM KIỂM TRA ĐIỀU KIỆN CÁ CƯỢC (GIỚI HẠN MAX 500K)
# =====================================================================
async def check_gamble_conditions(ctx, amount_str):
    user_id = str(ctx.author.id)
    now = datetime.now()

    if user_id in gamble_cooldowns and (now - gamble_cooldowns[user_id]).total_seconds() < 4:
        await ctx.send(f"⏳ Cờ bạc từ từ thôi! Đợi {int(4 - (now - gamble_cooldowns[user_id]).total_seconds())}s nữa nhé!")
        return None, None

    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        if user_data.get("money", 0) < 0:
            await ctx.send("Tài khoản đang **NỢ** mà dám vào casino à? Đi cày `k daily` trả nợ ngay!")
        else:
            await ctx.send("Túi rỗng tếch mà đòi cá cược! Điểm danh đi.")
        return None, None

    tien_hien_tai = user_data["money"]
    try: 
        if amount_str.lower() == "all":
            bet = tien_hien_tai if tien_hien_tai <= 500000 else 500000
        else:
            bet = int(amount_str)
    except: 
        await ctx.send("Số cược không hợp lệ!")
        return None, None

    if bet <= 0 or bet > tien_hien_tai:
        await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai:,} 💰**.")
        return None, None
        
    if bet > 500000:
        await ctx.send("⚠️ Đại gia bình tĩnh! Sòng bài quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé.")
        return None, None
        
    return user_data, bet

# =====================================================================
# DỮ LIỆU GAME (NHÂN SINH, KHU RỪNG, SHOP, GACHA)
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
        {"mult": -0.8, "msg": "💩 **TRƯỢT CHÂN VÀO BÃI KÌN!**\nBạn dẫm trúng bãi mìn khổng lồ của voi rừng. Tốn tiền mua bộ đồ mới."}
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

# --- DỮ LIỆU CỬA HÀNG VÀ PET ---
SHOP_ITEMS = {
    "t_1": {"type": "title", "name": "Nông Dân Chăm Chỉ 🌾", "price": 50000},
    "t_2": {"type": "title", "name": "Đại Gia Mới Nổi 💸", "price": 500000},
    "t_3": {"type": "title", "name": "Chúa Tể Sòng Bài 🎰", "price": 2000000},
    "t_4": {"type": "title", "name": "Thiên Hạ Đệ Nhất 👑", "price": 10000000},
    "a_1": {"type": "asset", "name": "Xe Đạp Thống Nhất 🚲", "price": 10000},
    "a_2": {"type": "asset", "name": "Honda SH 🛵", "price": 50000},
    "a_3": {"type": "asset", "name": "Mẹc G63 🚙", "price": 500000},
    "a_4": {"type": "asset", "name": "Biệt Thự Ven Biển 🏡", "price": 10000000},
    "a_5": {"type": "asset", "name": "Đảo Tư Nhân 🏝️", "price": 50000000}
}

PET_RATES = {
    "common": {"rate": 70, "pool": ["Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", "Lợn Đất 🐖", "Cá Chép 🐟", "Ếch Xanh 🐸"]},
    "rare": {"rate": 25, "pool": ["Sói Tuyết 🐺", "Gấu Bự 🐻", "Cáo Chín Đuôi 🦊", "Đại Bàng 🦅", "Báo Gấm 🐆"]},
    "epic": {"rate": 4, "pool": ["Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍", "Bạch Hổ 🐅", "Cá Mập Megalodon 🦈"]},
    "legendary": {"rate": 1, "pool": ["Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", "Phượng Hoàng Lửa 🦚"]}
}


# =====================================================================
# GIAO DIỆN GAME NHÂN SINH
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

        if self.stats["may_man"] >= 8: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, chạy quanh nhà bằng siêu xe.")
        elif self.stats["may_man"] >= 4: self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm.")
        else: self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài chợ từ nhỏ.")

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

        if len(self.logs) > 4: story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else: story = "\n\n".join(self.logs)
            
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

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{user_data['money']} 💰**", inline=False)

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

# =====================================================================
# GIAO DIỆN KHU RỪNG
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
        
        global SCENARIOS
        scenario = random.choice(SCENARIOS[category])
        
        if "mult" in scenario: thuong_phat = int(weapon_info['price'] * scenario["mult"])
        else: thuong_phat = scenario.get("tien", 0)
        
        user_data["money"] += thuong_phat
        actual_change = user_data["money"] - old_money
        new_session_profit = view.session_profit + actual_change
        save_user(user_id)
        
        profit_text = f"LÃI +{new_session_profit} 💰" if new_session_profit > 0 else f"LỖ {new_session_profit} 💰" if new_session_profit < 0 else "HUỀ VỐN"
        
        embed_color = discord.Color.green() if thuong_phat > 0 else discord.Color.red() if thuong_phat < 0 else discord.Color.light_gray()
        res_embed = discord.Embed(title="MỞ LÙM CÂY...", description=f"**{scenario['msg']}**", color=embed_color)
        
        if thuong_phat > 0: res_embed.add_field(name="Thu Hoạch", value=f"📈 **+{thuong_phat} 💰**", inline=True)
        elif thuong_phat < 0: res_embed.add_field(name="Thua Lỗ", value=f"📉 **{thuong_phat} 💰**", inline=True)
        else: res_embed.add_field(name="Kết Quả", value="➖ **Trắng tay**", inline=True)
            
        res_embed.add_field(name="Tổng Kết Phiên", value=f"📊 **{profit_text}**", inline=True)
        res_embed.set_footer(text=f"Số dư: {user_data['money']} 💰", icon_url=interaction.user.display_avatar.url)
        
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
        if interaction.user != self.author: return False
        return True

    async def continue_explore(self, interaction: discord.Interaction):
        shop_embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ THÁM HIỂM 🛒", description="Chọn vũ khí để bắt đầu chuyến đi mới.\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA** 👇", color=discord.Color.orange())
        if self.session_profit > 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LÃI +{self.session_profit} 💰")
        elif self.session_profit < 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LỖ {self.session_profit} 💰")
        
        view = ShopView(self.author, self.session_profit)
        await interaction.response.edit_message(content=None, embed=shop_embed, view=view)

    async def stop_explore(self, interaction: discord.Interaction):
        for child in self.children: child.disabled = True
        profit_text = f"LÃI +{self.session_profit} 💰" if self.session_profit > 0 else f"LỖ {self.session_profit} 💰" if self.session_profit < 0 else "HUỀ VỐN"
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
        if interaction.user != self.author: return False
        return True

class WeaponSelect(discord.ui.Select):
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = [
            discord.SelectOption(label="Gậy Gỗ Mục", description="Giá: 50 💰", emoji="🪵", value="gay_go"),
            discord.SelectOption(label="Súng Cao Su", description="Giá: 100 💰", emoji="🪀", value="sung_cao_su"),
            discord.SelectOption(label="Kiếm Sắt Thường", description="Giá: 200 💰", emoji="🗡️", value="kiem_sat"),
            discord.SelectOption(label="Kiếm Hiệp Sĩ", description="Giá: 500 💰", emoji="⚔️", value="kiem_hiep_si"),
            discord.SelectOption(label="Rìu Phá Giáp", description="Giá: 1000 💰", emoji="🪓", value="riu_chien"),
            discord.SelectOption(label="Thánh Kiếm Mạ Vàng", description="Giá: 1500 💰", emoji="🔱", value="thanh_kiem"),
            discord.SelectOption(label="Súng Phóng Lựu", description="Giá: 3000 💰", emoji="🚀", value="sung_phong_luu"),
            discord.SelectOption(label="Găng Tay Vô Cực", description="Giá: 5000 💰", emoji="🧤", value="gang_tay")
        ]
        super().__init__(placeholder="Nhấp vào để mua trang bị...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        weapon_id = self.values[0]
        price = WEAPON_ODDS[weapon_id]["price"]
        weapon_name = WEAPON_ODDS[weapon_id]["name"]
        
        if user_data.get("money", 0) < price:
            return await interaction.response.send_message(f"Nghèo quá! Bạn không đủ **{price} 💰** để mua {weapon_name}!", ephemeral=True)
            
        user_data["money"] -= price
        new_profit = self.session_profit - price 
        save_user(user_id)
        
        view = BushView(interaction.user, weapon_id, new_profit)
        embed = discord.Embed(title="🌲 KHU RỪNG KỲ BÍ 🌲", description=f"Bạn hiện đang cầm **{weapon_name}**.\nPhía trước có 5 lùm cây. Hãy chọn 1 lùm cây để khám phá!", color=discord.Color.dark_green())
        embed.set_footer(text=f"Đã tốn {price} 💰 để mua trang bị.")
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class ShopView(discord.ui.View):
    def __init__(self, author, session_profit=0):
        super().__init__(timeout=60)
        self.author = author
        self.session_profit = session_profit
        self.add_item(WeaponSelect(self.session_profit))
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author: return False
        return True


# =====================================================================
# GIAO DIỆN TRẠM AFK
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

        embed = discord.Embed(title="⛺ LÊN ĐƯỜNG!", description=f"Hành lý đã chuẩn bị xong. Bạn bắt đầu hành trình **{hours} giờ**.\nHãy dùng lại lệnh `k phai` khi hết thời gian để nhận thưởng.", color=discord.Color.green())
        await interaction.response.edit_message(content=None, embed=embed, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author: return False
        return True

# =====================================================================
# GIAO DIỆN CỬA HÀNG (SHOP & BĐS)
# =====================================================================
class CuaHangSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Danh hiệu: Nông Dân Chăm Chỉ", description="50,000 💰", emoji="🌾", value="t_1"),
            discord.SelectOption(label="Danh hiệu: Đại Gia Mới Nổi", description="500,000 💰", emoji="💸", value="t_2"),
            discord.SelectOption(label="Danh hiệu: Chúa Tể Sòng Bài", description="2,000,000 💰", emoji="🎰", value="t_3"),
            discord.SelectOption(label="Danh hiệu: Thiên Hạ Đệ Nhất", description="10,000,000 💰", emoji="👑", value="t_4"),
            discord.SelectOption(label="Tài sản: Xe Đạp Thống Nhất", description="10,000 💰", emoji="🚲", value="a_1"),
            discord.SelectOption(label="Tài sản: Honda SH", description="50,000 💰", emoji="🛵", value="a_2"),
            discord.SelectOption(label="Tài sản: Mẹc G63", description="500,000 💰", emoji="🚙", value="a_3"),
            discord.SelectOption(label="Tài sản: Biệt Thự Ven Biển", description="10,000,000 💰", emoji="🏡", value="a_4"),
            discord.SelectOption(label="Tài sản: Đảo Tư Nhân", description="50,000,000 💰", emoji="🏝️", value="a_5")
        ]
        super().__init__(placeholder="Mở danh sách để mua sắm...", min_values=1, max_values=1, options=options)

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
                user_data["money"] += item_info["price"] # Hoàn tiền
                return await interaction.response.send_message(f"⚠️ Bạn đã sở hữu **{item_info['name']}** rồi, không cần mua nữa đâu đại gia!", ephemeral=True)
            
            user_data["assets"].append(item_info["name"])
            msg = f"🎉 Chúc mừng! Bạn vừa tậu thành công **{item_info['name']}**."
            
        save_user(user_id)
        
        embed = discord.Embed(title="🛍️ GIAO DỊCH THÀNH CÔNG!", description=msg, color=discord.Color.green())
        embed.set_footer(text=f"Số dư còn lại: {user_data['money']:,} 💰")
        await interaction.response.edit_message(content=None, embed=embed, view=None)

class CuaHangView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(CuaHangSelect())
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author: return False
        return True


# =====================================================================
# TÍNH NĂNG ĐẤU TRƯỜNG: SOLO OẲN TÙ TÌ
# =====================================================================
class SoloOTTGame(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60)
        self.p1, self.p2, self.bet = p1, p2, bet
        self.msg = None
        self.choices = {str(p1.id): None, str(p2.id): None}

    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "🪨")

    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "📄")

    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "✂️")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = str(interaction.user.id)
        if user_id not in self.choices: return await interaction.response.send_message("Tránh ra chỗ khác, đây là trận chiến riêng tư!", ephemeral=True)
        if self.choices[user_id] is not None: return await interaction.response.send_message("Ông đã ra chiêu rồi, không được đổi!", ephemeral=True)
            
        self.choices[user_id] = choice
        await interaction.response.send_message(f"🤫 Bạn đã giấu tay chọn **{choice}**. Chờ đối thủ...", ephemeral=True)

        if self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]:
            for child in self.children: child.disabled = True
            c1, c2 = self.choices[str(self.p1.id)], self.choices[str(self.p2.id)]
            u1_data, u2_data = load_user(self.p1.id), load_user(self.p2.id)
            tong_thuong = self.bet * 2
            
            if c1 == c2:
                res = "🤝 **HÒA NHAU!** Tiền cược được trả lại cho cả hai."
                u1_data["money"] += self.bet; u2_data["money"] += self.bet
            elif (c1 == "🪨" and c2 == "✂️") or (c1 == "📄" and c2 == "🪨") or (c1 == "✂️" and c2 == "📄"):
                res = f"🎉 **{self.p1.name} CHIẾN THẮNG!**\nHúp trọn nồi lẩu **{tong_thuong:,} 💰**."
                u1_data["money"] += tong_thuong
            else:
                res = f"🎉 **{self.p2.name} CHIẾN THẮNG!**\nHúp trọn nồi lẩu **{tong_thuong:,} 💰**."
                u2_data["money"] += tong_thuong
                
            save_user(self.p1.id); save_user(self.p2.id)
            embed = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed.add_field(name=self.p1.name, value=f"Ra {c1}", inline=True)
            embed.add_field(name="VS", value="⚡", inline=True)
            embed.add_field(name=self.p2.name, value=f"Ra {c2}", inline=True)
            embed.add_field(name="KẾT QUẢ", value=res, inline=False)
            await self.msg.edit(embed=embed, view=self)
            self.stop()

    async def on_timeout(self):
        if not (self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]):
            u1_data, u2_data = load_user(self.p1.id), load_user(self.p2.id)
            u1_data["money"] += self.bet; u2_data["money"] += self.bet
            save_user(self.p1.id); save_user(self.p2.id)
            embed = discord.Embed(title="⏳ HẾT GIỜ KHIẾP SỢ", description="Có người nhát gan. Trận đấu bị hủy, tiền cược đã hoàn trả!", color=discord.Color.dark_gray())
            try: await self.msg.edit(embed=embed, view=None)
            except: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60)
        self.p1, self.p2, self.bet = p1, p2, bet

    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.p2.id: return await interaction.response.send_message("Không phận sự miễn vào!", ephemeral=True)
        
        u1_data, u2_data = load_user(self.p1.id), load_user(self.p2.id)
        if u1_data.get("money",0) < self.bet or u2_data.get("money",0) < self.bet:
            return await interaction.response.send_message("⚠️ Một trong hai người đã tiêu cạn tiền, không đủ lúa để chơi!", ephemeral=True)
        
        u1_data["money"] -= self.bet; u2_data["money"] -= self.bet
        save_user(self.p1.id); save_user(self.p2.id)

        game_view = SoloOTTGame(self.p1, self.p2, self.bet)
        embed = discord.Embed(title="⚔️ QUYẾT CHIẾN OẲN TÙ TÌ", description=f"{self.p1.mention} 🆚 {self.p2.mention}\nTiền cược: **{self.bet:,} 💰**\n\n👇 **HÃY BẤM NÚT ĐỂ CHỌN! (Lựa chọn bị giấu kín)**")
        await interaction.message.edit(embed=embed, view=game_view)
        game_view.msg = interaction.message
        self.stop()


# =====================================================================
# CÁC LỆNH CHÍNH CỦA BOT
# =====================================================================

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH CỦA BOT", description="Tiền tố lệnh là `k` hoặc `K`.", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(name="💳 KINH TẾ & TÀI SẢN", value="`k rank` • Xem hồ sơ\n`k daily` • Nhận lương\n`k lixi` • Bốc phong bao\n`k cuahang` • Mua Danh hiệu & BĐS\n`k tuido` • Xem tài sản & thú cưng\n`k top` • BXH\n`k give @user <tiền>` • Chuyển tiền", inline=False)
    embed.add_field(name="🎮 CÁ CƯỢC (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu\n`k duathu <heo/cho/ngua/chuot> <tiền>`\n`k baucua <con vật> <tiền>` • Lắc bầu cua\n`k nohu <tiền>` • Quay xèng\n`k soloott @user <tiền>` • PK Oẳn tù tì", inline=False)
    embed.add_field(name="🌲 NHẬP VAI & CÀY CUỐC", value="`k gacha` • Đập trứng thú cưng (30k)\n`k thamhiem` • Đi rừng\n`k phai` • Treo máy AFK\n`k nhansinh` • Mô phỏng cuộc đời", inline=False)
    
    embed.set_footer(text="Chúc bạn cày cuốc vui vẻ không quạu!", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def cuahang(ctx):
    embed = discord.Embed(title="🏪 CỬA HÀNG ĐẠI GIA 🏪", description="Tiền nhiều để làm gì? Để mua danh hiệu khè nhau và tậu nhà lầu xe hơi chứ còn gì nữa!\n\n👇 **MỞ DANH SÁCH BÊN DƯỚI ĐỂ MUA SẮM** 👇", color=discord.Color.brand_green())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    view = CuaHangView(ctx.author)
    await ctx.send(embed=embed, view=view)

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

    roll = random.randint(1, 100)
    if roll <= PET_RATES["legendary"]["rate"]: rarity, color, text = "legendary", discord.Color.gold(), "👑 HUYỀN THOẠI"
    elif roll <= PET_RATES["legendary"]["rate"] + PET_RATES["epic"]["rate"]: rarity, color, text = "epic", discord.Color.purple(), "🔮 SỬ THI"
    elif roll <= PET_RATES["legendary"]["rate"] + PET_RATES["epic"]["rate"] + PET_RATES["rare"]["rate"]: rarity, color, text = "rare", discord.Color.blue(), "💎 HIẾM"
    else: rarity, color, text = "common", discord.Color.light_grey(), "🪵 PHỔ THÔNG"

    pet_name = random.choice(PET_RATES[rarity]["pool"])
    
    # Lưu Pet vào túi
    if pet_name in user_data["pets"]: user_data["pets"][pet_name] += 1
    else: user_data["pets"][pet_name] = 1
    save_user(user_id)

    embed = discord.Embed(title=f"🎉 NỔ TRỨNG: {text}!", description=f"Tuyệt vời! Bạn vừa nở ra một bé **{pet_name}**!\n*(Gõ `k tuido` để xem bộ sưu tập của bạn)*", color=color)
    await msg.edit(content=ctx.author.mention, embed=embed)

@bot.command()
async def tuido(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    embed = discord.Embed(title=f"🎒 Kho Báu của {ctx.author.name}", color=discord.Color.dark_theme())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    # Tài sản
    assets = user_data.get("assets", [])
    if len(assets) == 0: assets_str = "Trắng tay, Khố rách áo ôm."
    else: assets_str = "\n".join([f"🔸 {a}" for a in assets])
    embed.add_field(name="🏠 Bất Động Sản & Phương Tiện", value=assets_str, inline=False)
    
    # Thú cưng
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
    title = user_data.get("title", "Dân Thường 🚶")
    max_xp = lv * 100
    
    khung_mau = discord.Color.red() if tien < 0 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 Thẻ Căn Cước của {ctx.author.name}", color=khung_mau)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    embed.add_field(name="Danh hiệu", value=f"**{title}**", inline=False)
    embed.add_field(name="Cấp độ", value=f"🌟 **LV {lv}**", inline=True)
    
    tien_text = f"**{tien:,} 💰**\n*(ĐANG NỢ)*" if tien < 0 else f"**{tien:,} 💰**"
    embed.add_field(name="Tài sản", value=tien_text, inline=True)
    
    bar = make_progress_bar(xp, max_xp)
    embed.add_field(name="Kinh nghiệm", value=f"`{bar}`\n**{xp}/{max_xp} XP**", inline=False)
    
    # Trích xuất bđs để khoe sương sương trên căn cước
    assets = user_data.get("assets", [])
    if assets: embed.set_footer(text=f"Đang sở hữu: {', '.join(assets[:2])}{'...' if len(assets)>2 else ''}")
    else: embed.set_footer(text="Gia cảnh: Vô Gia Cư")
        
    await ctx.send(embed=embed)


# --- CÁC LỆNH ADMIN, GAME, AFK GIỮ NGUYÊN HOÀN TOÀN GIỐNG BẢN TRƯỚC BÊN DƯỚI NÀY ---
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
    if not mentions: return await ctx.send("⚠️ Vui lòng tag các kênh. VD: `k setup #kenh-1`")
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
    embed = discord.Embed(title="BƠM VỐN THÀNH CÔNG", description=f"👑 Admin {ctx.author.mention} buff cho {member.mention} **{amount:,} 💰**!\n💳 Số dư mới: **{user_data['money']:,} 💰**", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền trừ đi phải > 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] -= amount
    save_user(user_id)
    embed = discord.Embed(title="THIÊN PHẠT GIÁNG XUỐNG", description=f"⚖️ Admin đã tước đoạt **{amount:,} 💰** của {member.mention}!\n💳 Số dư mới: **{user_data['money']:,} 💰**", color=discord.Color.red())
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
            embed = discord.Embed(title="🎉 TRỞ VỀ AN TOÀN!", description=f"{ctx.author.mention} đã thu hoạch được **{reward:,} 💰**!\n💳 Số dư hiện tại: **{user_data['money']:,} 💰**", color=discord.Color.gold())
            await ctx.send(embed=embed)
        else:
            time_left = exp_end - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"⏳ Đang cày cuốc sấp mặt! Hãy kiên nhẫn chờ thêm **{hours} giờ {minutes} phút** nữa.")
        return

    embed = discord.Embed(title="⛺ TRẠM THÁM HIỂM AFK", description="Gửi nhân vật đi treo máy và nhặt tiền lúc trở về!\n\n👇 **MỞ MENU ĐỂ CHỌN KHU VỰC** 👇", color=discord.Color.dark_green())
    view = ExpView(ctx.author)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    shop_embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ THÁM HIỂM", description="Rừng rậm đầy nguy hiểm nhưng cũng đầy kho báu.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA ĐỒ** 👇", color=discord.Color.orange())
    view = ShopView(ctx.author, session_profit=0)
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
    
    for _ in range(4):
        embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Máy đang quay tít mù..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1.2)
        
    for _ in range(2):
        embed.description = f"**[ {s1} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đã chốt ô đầu tiên..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1.2)
        
    for _ in range(2):
        embed.description = f"**[ {s1} | {s2} | {random.choice(items)} ]**\n\n🔄 Nín thở chờ ô cuối..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1.2)
        
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
@commands.has_permissions(administrator=True) 
async def setkenh(ctx, kenh: discord.TextChannel):
    server_id = str(ctx.guild.id)
    config_col.update_one({"_id": server_id}, {"$set": {"channel_id": kenh.id}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["channel_id"] = kenh.id
    await ctx.send(f'✅ Đã lưu kênh báo lên cấp: {kenh.mention}!')

@bot.event
async def on_message(message):
    if message.author.bot: return
    u_id = str(message.author.id)
    user_data = load_user(u_id)

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
