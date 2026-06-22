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
            DB_CACHE[user_id] = {"xp": 0, "level": 1, "money": 0}
    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE:
        users_col.update_one(
            {"_id": user_id},
            {"$set": DB_CACHE[user_id]},
            upsert=True
        )

def load_server_config(server_id):
    server_id = str(server_id)
    if server_id not in CONFIG_CACHE:
        doc = config_col.find_one({"_id": server_id})
        if doc:
            CONFIG_CACHE[server_id] = doc
        else:
            CONFIG_CACHE[server_id] = {}
    return CONFIG_CACHE[server_id]

@bot.check
async def channel_restriction_check(ctx):
    if ctx.author.guild_permissions.administrator: return True
    if not ctx.guild: return True
    config = load_server_config(ctx.guild.id)
    allowed_channels = config.get("allowed_channels", [])
    if allowed_channels and ctx.channel.id not in allowed_channels: return False
    return True

# Hàm tạo thanh tiến trình siêu ngầu
def make_progress_bar(current, total, length=10):
    progress = int((current / total) * length)
    return "█" * progress + "░" * (length - progress)

# =====================================================================
# KHO SỰ KIỆN NHÂN SINH (HARDCORE)
# =====================================================================

EVENTS_P1 = [
    {
        "q": "Tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.",
        "choices": [
            {"text": "Đem nộp lên công an", "rate": 80, "win": "Chủ ví là tổng tài, hậu tạ bạn món tiền lớn.", "lose": "Bị giam ở phường viết bản tường trình 3 ngày.", "tien_w": 2500, "tien_l": -100},
            {"text": "Bỏ túi xài luôn", "rate": 20, "win": "Không ai biết, bạn bao lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường gấp đôi và bị đuổi học.", "tien_w": 3000, "tien_l": -8000},
            {"text": "Lấy tờ 500k rồi vứt lại ví", "rate": 40, "win": "Trót lọt, bạn nạp game lên VIP.", "lose": "Chủ nhân báo mất, bị tra hỏi phạt nặng.", "tien_w": 1000, "tien_l": -4000},
            {"text": "Giả vờ không thấy", "rate": 95, "win": "Thong thả đi học tiếp, chẳng rước họa vào thân.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn.", "tien_w": 0, "tien_l": -500}
        ]
    },
    {
        "q": "Kỳ thi cuối cấp cận kề, bạn bè rủ cúp học đi net.",
        "choices": [
            {"text": "Ở nhà ôn bài kỹ", "rate": 85, "win": "Đỗ thủ khoa, được họ hàng thưởng nóng.", "lose": "Học tài thi phận, trượt vỏ chuối.", "tien_w": 2500, "tien_l": -500},
            {"text": "Đi net cày rank", "rate": 10, "win": "Gặp idol ở quán net, được kéo lên Thách Đấu và cho tiền.", "lose": "Ngủ gục trên xe tông cột điện thăng thiên.", "tien_w": 3500, "tien_l": -10000, "die_l": True},
            {"text": "Làm phao mang vào", "rate": 35, "win": "Mở phao mượt mà, điểm cao chót vót.", "lose": "Giám thị bắt quả tang, đình chỉ thi 0 điểm.", "tien_w": 2000, "tien_l": -5000},
            {"text": "Ngủ cho khỏe", "rate": 50, "win": "Tinh thần sảng khoái, làm bài vừa đủ đậu.", "lose": "Ngủ nhiều lú não, làm sai phép tính cơ bản 1+1=3.", "tien_w": 800, "tien_l": -1000}
        ]
    }
]

EVENTS_P2 = [
    {
        "q": "Tích cóp được chút vốn, bạn muốn làm giàu nhanh.",
        "choices": [
            {"text": "Bắt đáy chứng khoán", "rate": 30, "win": "Cổ phiếu tím lịm! Tiền lãi mua được cả căn nhà.", "lose": "Bị chủ tịch úp bô, cổ phiếu rác hủy niêm yết.", "tien_w": 15000, "tien_l": -25000},
            {"text": "Cắm sổ đỏ đánh xóc đĩa", "rate": 5, "win": "Ăn thông 10 ván! Bạn mua hẳn siêu xe Mẹc-xê-đét.", "lose": "Cháy túi, nhảy cầu kết thúc cuộc đời.", "tien_w": 80000, "tien_l": -50000, "die_l": True},
            {"text": "Khởi nghiệp bún đậu mắm tôm", "rate": 60, "win": "Đông khách nườm nượp, mở 5 chi nhánh.", "lose": "Bị phốt mắm tôm có giòi, sập tiệm đền tiền.", "tien_w": 12000, "tien_l": -8000},
            {"text": "Gửi tiết kiệm ngân hàng", "rate": 95, "win": "Cuộc sống bình yên, có lãi ra tiêu vặt.", "lose": "Lạm phát phi mã, tiền bốc hơi từ từ.", "tien_w": 2000, "tien_l": -1500}
        ]
    }
]

EVENTS_P3 = [
    {
        "q": "Bất Động Sản đang sốt, cò đất rủ bạn lướt sóng phân lô bán nền.",
        "choices": [
            {"text": "Cầm nhà ngân hàng quất liền", "rate": 20, "win": "Giá đất x5 trong một đêm! Bạn thành đại gia nghìn tỷ.", "lose": "Dính bẫy lừa đảo dự án ma, ra đê ở, treo cổ tự tử.", "tien_w": 60000, "tien_l": -70000, "die_l": True},
            {"text": "Mua miếng đất nhỏ vùng ven", "rate": 55, "win": "Chính phủ mở đường qua, đất nhân 3 giá trị.", "lose": "Đất dính quy hoạch mỏ đá, bán không ai mua.", "tien_w": 15000, "tien_l": -10000},
            {"text": "Mở lớp dạy làm giàu từ BĐS", "rate": 40, "win": "Lùa được đàn gà đông đảo, thu học phí ngập mồm.", "lose": "Bị học viên bóc phốt úp sọt, đánh nhập viện.", "tien_w": 12000, "tien_l": -15000},
            {"text": "Không quan tâm, lo giữ gia đình", "rate": 95, "win": "Nhà cửa êm ấm, vợ/chồng con cái hạnh phúc.", "lose": "Kinh tế khó khăn, đôi lúc cãi nhau vì tiền điện nước.", "tien_w": 3000, "tien_l": -1500}
        ]
    }
]

EVENTS_P4 = [
    {
        "q": "Bước vào tuổi 50, bạn rơi vào khủng hoảng tuổi trung niên trầm trọng.",
        "choices": [
            {"text": "Bán nhà mua siêu xe Mẹc G63", "rate": 15, "win": "Chiến thắng giải đua không chuyên, nổi đình đám ăn quảng cáo.", "lose": "Đạp nhầm chân ga tông xe tải, thăng thiên tại chỗ.", "tien_w": 35000, "tien_l": -40000, "die_l": True},
            {"text": "Sưu tầm Lan Đột Biến", "rate": 35, "win": "Bán chậu lan giá trên trời cho tỷ phú.", "lose": "Thị trường sập, ôm nhánh cỏ khô lỗ chổng vó.", "tien_w": 25000, "tien_l": -20000},
            {"text": "Cặp Sugar Baby cho hồi xuân", "rate": 25, "win": "Nuôi êm thấm, tâm hồn trẻ lại phơi phới.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, mất sạch tài sản.", "tien_w": 2000, "tien_l": -50000},
            {"text": "Tập Thiền, dọn về quê nuôi cá", "rate": 90, "win": "Tâm hồn thanh tịnh, khí huyết lưu thông.", "lose": "Về quê bị muỗi vằn chích sốt xuất huyết.", "tien_w": 5000, "tien_l": -3000}
        ]
    }
]

EVENTS_P5 = [
    {
        "q": "Chạm mốc 70 tuổi, một nhà sư bảo bạn sắp tới số.",
        "choices": [
            {"text": "Vung tiền mua Linh Đan Tu Tiên", "rate": 5, "win": "Kỳ tích! Bạn cải lão hoàn đồng thành thanh niên 20 tuổi!", "lose": "Uống nhầm thủy ngân, nội tạng nát vụn thăng thiên sớm.", "tien_w": 200000, "tien_l": -20000, "die_l": True},
            {"text": "Lập di chúc chia đều tài sản", "rate": 75, "win": "Con cháu hòa thuận, tổ chức mừng thọ linh đình.", "lose": "Con cháu chê ít, đánh nhau mẻ đầu, bạn tức quá đột tử.", "tien_w": 5000, "tien_l": -15000, "die_l": True},
            {"text": "Quyên góp 100% làm từ thiện", "rate": 90, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền bốc hơi, bạn trầm cảm đi luôn.", "tien_w": 15000, "tien_l": -50000, "die_l": True},
            {"text": "Lên Las Vegas đánh Casino lần cuối", "rate": 20, "win": "Thắng Jackpot 50 triệu đô! Lên báo quốc tế rình rang.", "lose": "Thua sạch bong, lên cơn nhồi máu cơ tim gục tại bàn.", "tien_w": 100000, "tien_l": -40000, "die_l": True}
        ]
    }
]


# =====================================================================
# DATA THÁM HIỂM KHU RỪNG (MỞ RỘNG VŨ KHÍ & CÂN BẰNG TỈ LỆ)
# =====================================================================
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
        {"mult": -1.2, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!**\nGặp ngay băng thổ phỉ khét tiếng. Chúng lột sạch đồ đạc."},
        {"mult": -1.8, "msg": "👻 **TRÚNG NGẢI HEO!**\nĐi nhầm vào bản làng ma ám. Tiền tài không cánh mà bay."},
        {"mult": -1.3, "msg": "🕳️ **SỤP HỐ CHÔNG!**\nRơi thẳng xuống hố chông của thợ săn. Gãy 2 cái sườn, nôn hết tiền mặt ra."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"mult": -0.4, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi viện."},
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước hết hạn từ máy bán hàng tự động trong rừng."},
        {"mult": -0.8, "msg": "💩 **TRƯỢT CHÂN VÀO BÃI KÌN!**\nBạn dẫm trúng bãi mìn khổng lồ của voi rừng. Tốn tiền mua bộ đồ mới."},
        {"mult": -0.7, "msg": "📱 **RỚT ĐIỆN THOẠI!**\nMải selfie sống ảo, rơi điện thoại xuống suối mất hút."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"mult": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."},
        {"mult": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."},
        {"mult": 0, "msg": "🌬️ **GIÓ THỔI LẠNH LẼO...**\nChỉ có gió thổi hiu hiu, khung cảnh yên bình không có biến động gì."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"mult": 0.6, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá!"},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được cây nấm linh chi đỏ rực. Tiệm thuốc trả cho bạn một khoản hời."},
        {"mult": 1.0, "msg": "🙏 **NGƯỜI TỐT VIỆC TỐT!**\nNhặt được ví của một hiệp sĩ, bạn trả lại và được hậu tạ."}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp và tịch thu kho báu của chúng!"},
        {"mult": 2.0, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, đào trúng viên ngọc lục bảo thô to bằng nắm tay!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nPhát hiện ra một rương kho báu vàng chóe bị chôn vùi. Mở ra toàn tiền!"},
        {"mult": 2.8, "msg": "⛏️ **PHÁT HIỆN MỎ VÀNG MINI!**\nNhặt được một cục vàng cục bự chà bá ẩn dưới lớp rêu xanh. Phát tài rồi!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng ĐẶC BIỆT!"},
        {"mult": 8.0, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Bạn tìm thấy hang động cất giấu kho báu huyền thoại. Một núi Vàng!"},
        {"mult": 12.0, "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR! (ULTRAPOT)**\nDưới đáy đầm, bạn vớt được Vương miện nạm 100 viên kim cương. Bạn thành tỷ phú!!"}
    ]
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

        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, chạy quanh nhà bằng siêu xe.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài chợ từ nhỏ.")

        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text']}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_a.callback = self.choice_a
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text']}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_b.callback = self.choice_b
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text']}", style=discord.ButtonStyle.success, custom_id="btn_c")
        self.btn_c.callback = self.choice_c
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text']}", style=discord.ButtonStyle.danger, custom_id="btn_d")
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
            self.btn_a.label = f"A. {self.ev['choices'][0]['text']}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text']}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text']}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text']}"
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
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại đống nợ khổng lồ, chủ nợ siết sạch tài sản.\n❌ **BÁO NHÀ!** Khoản nợ: **{total_reward} 💰**\n*(Hệ thống trừ thẳng vào ví, cày `k daily` mà trả nhé!)*", inline=False)
            elif total_reward >= 30000:
                embed.color = discord.Color.gold()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa, làm đại gia trên đỉnh thế giới.\n👑 **ĐẠI PHÚ HÀO!** Di sản để lại: **+{total_reward} 💰**", inline=False)
            else:
                embed.color = discord.Color.blue()
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Cuộc đời êm ấm, thanh thản ra đi.\n💼 **DƯ DẢ!** Di sản để lại: **+{total_reward} 💰**", inline=False)

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{user_data['money']} 💰**", inline=False)

        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)


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
        
        if "mult" in scenario:
            thuong_phat = int(weapon_info['price'] * scenario["mult"])
        else:
            thuong_phat = scenario.get("tien", 0)
        
        user_data["money"] += thuong_phat
        actual_change = user_data["money"] - old_money
        new_session_profit = view.session_profit + actual_change
        save_user(user_id)
        
        profit_text = f"LÃI +{new_session_profit} 💰" if new_session_profit > 0 else f"LỖ {new_session_profit} 💰" if new_session_profit < 0 else "HUỀ VỐN"
        
        # Tạo Embed Kết quả tuyệt đẹp
        embed_color = discord.Color.green() if thuong_phat > 0 else discord.Color.red() if thuong_phat < 0 else discord.Color.light_gray()
        res_embed = discord.Embed(title="MỞ LÙM CÂY...", description=f"**{scenario['msg']}**", color=embed_color)
        
        if thuong_phat > 0:
            res_embed.add_field(name="Thu Hoạch", value=f"📈 **+{thuong_phat} 💰**", inline=True)
        elif thuong_phat < 0:
            res_embed.add_field(name="Thua Lỗ", value=f"📉 **{thuong_phat} 💰**", inline=True)
        else:
            res_embed.add_field(name="Kết Quả", value="➖ **Trắng tay**", inline=True)
            
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
        if interaction.user != self.author:
            await interaction.response.send_message("Hàng của người ta, cấm nhặt hôi!", ephemeral=True)
            return False
        return True

    async def continue_explore(self, interaction: discord.Interaction):
        shop_embed = discord.Embed(
            title="🛒 TRẠM TIẾP TẾ THÁM HIỂM 🛒",
            description="Chào mừng quay lại! Hãy chọn vũ khí để bắt đầu chuyến đi mới.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA** 👇",
            color=discord.Color.orange()
        )
        if self.session_profit > 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LÃI +{self.session_profit} 💰")
        elif self.session_profit < 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LỖ {self.session_profit} 💰")
        else: shop_embed.set_footer(text="📊 Kỷ lục phiên này: Đang HUỀ VỐN")

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
            discord.SelectOption(label="Găng Tay Vô Cực", description="Giá: 5000 💰 | Búng tay hủy diệt (Trúng khủng, Lỗ đau)", emoji="🧤", value="gang_tay")
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
            description=f"Sương mù rạp xuống... Bạn hiện đang cầm **{weapon_name}**.\nPhía trước có 5 lùm cây đang rung rinh. Hãy chọn 1 lùm cây để khám phá!",
            color=discord.Color.dark_green()
        )
        embed.set_footer(text=f"Đã tốn {price} 💰 để mua trang bị.")
        
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class ShopView(discord.ui.View):
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

# TRẠM AFK
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


# =====================================================================
# CÁC LỆNH CHÍNH CỦA BOT ĐÃ LÀM ĐẸP GIAO DIỆN
# =====================================================================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 HỆ THỐNG LỆNH CỦA BOT", 
        description="Chào mừng bạn đến với thiên đường giải trí. Tiền tố lệnh là `k` hoặc `K`.",
        color=discord.Color.blurple()
    )
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(name="💳 CƠ BẢN", value="`k rank` • Xem hồ sơ & Số dư\n`k top` • Bảng xếp hạng\n`k daily` • Nhận lương\n`k give @user <số tiền>` • Chuyển khoản", inline=False)
    embed.add_field(name="🎮 MINI GAMES CÁ CƯỢC", value="`k coin <số tiền/all>` • Xóc đồng xu\n`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu\n`k duathu <heo/cho/ngua/chuot> <tiền>` • Đua thú ảo\n`k ott <bua/bao/keo> <tiền>` • Oẳn tù tì", inline=False)
    embed.add_field(name="🌲 KHÁM PHÁ & NHẬP VAI", value="`k thamhiem` • Đi rừng nhân phẩm\n`k phai` • Treo máy AFK kiếm tiền\n`k nhansinh` • Game mô phỏng luân hồi cực gắt", inline=False)
    
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="⚙️ QUẢN TRỊ VIÊN", value="`k setup #kênh`, `k setkenh #kênh`\n`k themtien @user <tiền>`, `k trutien @user <tiền>`", inline=False)
    
    embed.set_footer(text="Chúc bạn chơi game vui vẻ không quạu!", icon_url=ctx.author.display_avatar.url)
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
        await ctx.send("⚠️ Vui lòng tag các kênh bạn muốn cho phép bot nhận lệnh.\nVí dụ: `k setup #kenh-1 #kenh-2`\nĐể gỡ giới hạn, gõ: `k setup clear`.")
        return

    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    
    if server_id not in CONFIG_CACHE:
        CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids

    channels_str = ", ".join(c.mention for c in mentions)
    await ctx.send(f"✅ Đã cài đặt! Bot từ nay **CHỈ** nhận lệnh tại: {channels_str}\n*(Quản trị viên vẫn có thể dùng lệnh ở mọi kênh)*")

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền phải lớn hơn 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] += amount
    save_user(user_id)
    
    embed = discord.Embed(title="BƠM VỐN THÀNH CÔNG", color=discord.Color.green())
    embed.description = f"👑 Admin {ctx.author.mention} vừa buff nóng cho {member.mention} **{amount:,} 💰**!\n💳 Số dư mới: **{user_data['money']:,} 💰**"
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền trừ đi phải lớn hơn 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] -= amount
    save_user(user_id)

    embed = discord.Embed(title="THIÊN PHẠT GIÁNG XUỐNG", color=discord.Color.red())
    embed.description = f"⚖️ Admin đã tước đoạt **{amount:,} 💰** từ tài khoản của {member.mention}!\n💳 Số dư mới: **{user_data['money']:,} 💰**"
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
            embed.description = f"{ctx.author.mention} đã mở túi hành lý và thu hoạch được **{reward:,} 💰**!\n💳 Số dư hiện tại: **{user_data['money']:,} 💰**"
            await ctx.send(embed=embed)
        else:
            time_left = exp_end - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"⏳ Đang cày cuốc sấp mặt! Hãy kiên nhẫn chờ thêm **{hours} giờ {minutes} phút** nữa nhé.")
        return

    embed = discord.Embed(
        title="⛺ TRẠM THÁM HIỂM AFK", 
        description="Gửi nhân vật đi treo máy và nhặt tiền lúc trở về!\n\n👇 **MỞ MENU ĐỂ CHỌN KHU VỰC** 👇", 
        color=discord.Color.dark_green()
    )
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    view = ExpView(ctx.author)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    shop_embed = discord.Embed(
        title="🛒 TRẠM TIẾP TẾ THÁM HIỂM",
        description="Rừng rậm đầy nguy hiểm nhưng cũng đầy kho báu. Vũ khí xịn thì nổ hũ to, vũ khí cùi thì nhặt bạc lẻ.\n\n👇 **MỞ MENU BÊN DƯỚI ĐỂ MUA ĐỒ** 👇",
        color=discord.Color.orange()
    )
    if bot.user.avatar: shop_embed.set_thumbnail(url=bot.user.avatar.url)
    view = ShopView(ctx.author, session_profit=0)
    await ctx.send(embed=shop_embed, view=view)

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id)
    phi = 100
    now = datetime.now()

    if user_id in dang_choi_nhansinh:
        await ctx.send(f"⏳ {ctx.author.mention}, bạn đang luân hồi dở dang rồi! Hoàn thành kiếp trước đi đã.")
        return

    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5:
        giay_con_lai = int(5 - (now - nhansinh_cooldowns[user_id]).total_seconds())
        await ctx.send(f"⏳ Linh hồn cần nghỉ ngơi! Đợi **{giay_con_lai} giây** nữa mới được đầu thai.")
        return

    user_data = load_user(user_id)
    if user_data.get("money", 0) < phi:
        await ctx.send(f"⚠️ Vé luân hồi giá **{phi} 💰**. Túi rỗng thì không có cửa đầu thai đâu!")
        return

    user_data["money"] -= phi
    nhansinh_cooldowns[user_id] = now
    dang_choi_nhansinh.append(user_id)
    save_user(user_id)

    stats = {
        "may_man": random.randint(1, 10)
    }

    view = NhanSinhGameView(ctx.author, stats)
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.purple())
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{stats['may_man']}/10** *(+ {stats['may_man']*2}% Tỉ lệ)*", inline=False)
    
    story = "\n\n".join(view.logs)
    embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)
    embed.add_field(name="❓ Ngã rẽ tuổi học trò (15 tuổi)", value=f"**{view.ev['q']}**", inline=False)

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
            await ctx.send(f"⏳ Tham lam vậy! Quay lại sau **{hours} giờ {minutes} phút** nữa nhé.")
            return

    user_data["money"] += 500
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    embed = discord.Embed(title="QUÀ ĐIỂM DANH 🎁", color=discord.Color.blue())
    if user_data["money"] < 0:
        embed.description = f"Bạn nhận được **500 💰** tiền công!\n⚠️ Hệ thống đã siết nợ tự động! Bạn vẫn còn đang nợ **{user_data['money']} 💰**."
        embed.color = discord.Color.red()
    else:
        embed.description = f"Bạn nhận được **500 💰** tiền công!\n💳 Số dư mới: **{user_data['money']:,} 💰**"
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    danh_sach_dai_gia = [(doc["_id"], doc.get("money", 0)) for doc in all_users]
    danh_sach_dai_gia.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA SERVER", color=discord.Color.gold())
    
    desc = ""
    thu_hang = 1
    for user_id, tien in danh_sach_dai_gia[:10]:
        user = bot.get_user(int(user_id))
        if user is None:
            try: user = await bot.fetch_user(int(user_id))
            except: pass
                
        ten = user.name if user else f"Người chơi {user_id[-4:]}"
        icon = "🥇" if thu_hang == 1 else "🥈" if thu_hang == 2 else "🥉" if thu_hang == 3 else f"**#{thu_hang}**"
        
        tien_format = f"{tien:,} 💰"
        desc += f"{icon} **{ten}** ━ {tien_format}\n\n"
        thu_hang += 1
        
    embed.description = desc
    await ctx.send(embed=embed)

# Tích hợp hàm kiểm tra Gamble Cooldown
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
        bet = tien_hien_tai if amount_str.lower() == "all" else int(amount_str)
    except: 
        await ctx.send("Số cược không hợp lệ!")
        return None, None

    if bet <= 0 or bet > tien_hien_tai:
        await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai:,} 💰**.")
        return None, None
        
    return user_data, bet

@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🪙 {ctx.author.mention} ném **{bet:,} 💰** lên trời...")
    await asyncio.sleep(1) 
    await msg.edit(content=f"🪙 {ctx.author.mention} ném **{bet:,} 💰** lên trời...\n🔄 Đồng xu lộn nhào...")
    await asyncio.sleep(1) 
    await msg.edit(content=f"🪙 {ctx.author.mention} ném **{bet:,} 💰** lên trời...\n🔄 Đồng xu lộn nhào...\n💥 Rơi rầm xuống đất...")
    await asyncio.sleep(1) 

    user_data = load_user(user_id)
    if random.choice(["thắng", "thua"]) == "thắng":
        win_amt = bet * 2
        user_data["money"] += win_amt
        save_user(user_id)
        await msg.edit(content=f"🪙 **MẶT NGỬA!**\n🎉 {ctx.author.mention} húp trọn **{win_amt:,} 💰**! (Dư: **{user_data['money']:,} 💰**)")
    else:
        await msg.edit(content=f"🪙 **MẶT SẤP!**\n💀 Nhờn! Mất **{bet:,} 💰**. (Dư: **{user_data['money']:,} 💰**)")

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    choice = choice.lower()
    if choice not in ["tai", "tài", "xiu", "xỉu"]:
        return await ctx.send("⚠️ Bạn phải chọn `tài` hoặc `xỉu`. VD: `k taixiu tai 100`")
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🎲 {ctx.author.mention} cược **{bet:,} 💰** vào cửa **{choice.upper()}**.\nĐang lắc xí ngầu... 🫨")
    await asyncio.sleep(1)
    await msg.edit(content=f"🎲 {ctx.author.mention} cược **{bet:,} 💰** vào cửa **{choice.upper()}**.\nĐang lắc xí ngầu... 🫨\nLạch cạch lạch cạch...")
    await asyncio.sleep(1.5)

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    is_bao = (d1 == d2 == d3)
    
    if total <= 10: res_str = "xỉu"
    else: res_str = "tài"
    
    user_data = load_user(user_id)
    
    if choice.replace("à", "a").replace("ỉ", "i") == res_str.replace("à", "a").replace("ỉ", "i"):
        if is_bao:
            win_amount = bet * 5
            user_data["money"] += win_amount
            result_msg = f"🔥 **BÃO {d1}-{d2}-{d3} TỚI RỒI!!! ĐẠI THẮNG x5!**\n🎉 Húp trọn **{win_amount:,} 💰**!"
        else:
            win_amount = bet * 2
            user_data["money"] += win_amount
            result_msg = f"✅ **THẮNG RỒI!**\n🎉 Húp trọn **{win_amount:,} 💰**!"
    else:
        result_msg = f"💀 **THUA CẮNG RĂNG!** Bạn mất **{bet:,} 💰**."

    save_user(user_id)
    final_text = f"🎲 KẾT QUẢ: **{d1} - {d2} - {d3}** (Tổng: {total} - **{res_str.upper()}**)\n" + result_msg + f"\n💳 Số dư: **{user_data['money']:,} 💰**"
    await msg.edit(content=final_text)

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    choice = choice.lower()
    
    if choice not in animals:
        return await ctx.send("⚠️ Chọn sai con vật! Có 4 con: `heo`, `cho`, `ngua`, `chuot`.")
        
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
        win_amount = bet * 3
        user_data["money"] += win_amount
        res_txt = f"\n🏆 **{winner} ĐÃ VỀ NHẤT!** Quá đỉnh, ăn được **x3 tiền ({win_amount:,} 💰)**!"
    else:
        res_txt = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} của bạn xịt rồi. Mất sạch **{bet:,} 💰**."
        
    save_user(user_id)
    await msg.edit(content=get_track() + res_txt + f"\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command(aliases=['ott'])
async def oantuti(ctx, choice: str, amount: str):
    valid_choices = {"bua": "🪨", "búa": "🪨", "bao": "📄", "giay": "📄", "giấy": "📄", "keo": "✂️", "kéo": "✂️"}
    choice = choice.lower()
    if choice not in valid_choices:
        return await ctx.send("⚠️ Phải ra `bua`, `bao` hoặc `keo`!")

    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    bot_options = ["🪨", "📄", "✂️"]
    bot_choice = random.choice(bot_options)
    user_choice = valid_choices[choice]
    
    msg = await ctx.send(f"🤔 Bạn ra {user_choice}. Bot đang suy nghĩ...")
    await asyncio.sleep(1)
    await msg.edit(content=f"🤔 Bạn ra {user_choice}. Bot đang suy nghĩ...\n💥 Oẳn... tù... tì... RA CÁI GÌ RA CÁI NÀY!!")
    await asyncio.sleep(1)

    user_data = load_user(user_id)
    
    if user_choice == bot_choice:
        user_data["money"] += bet
        res = "🤝 **HÒA NHAU!** Trả lại tiền cược."
    elif (user_choice == "🪨" and bot_choice == "✂️") or (user_choice == "📄" and bot_choice == "🪨") or (user_choice == "✂️" and bot_choice == "📄"):
        win_amount = bet * 2
        user_data["money"] += win_amount
        res = f"🎉 **BẠN THẮNG RỒI!** Húp trọn **{win_amount:,} 💰**."
    else:
        res = f"💀 **BOT THẮNG!** Mất **{bet:,} 💰**."

    save_user(user_id)
    await msg.edit(content=f"💥 Bot ra: **{bot_choice}** | Bạn ra: **{user_choice}**\n{res}\n💳 Số dư: **{user_data['money']:,} 💰**")

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

@bot.command()
async def rank(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    lv, xp, tien = user_data.get("level", 1), user_data.get("xp", 0), user_data.get("money", 0)
    max_xp = lv * 100
    
    khung_mau = discord.Color.red() if tien < 0 else discord.Color.teal()
    embed = discord.Embed(title=f"💳 Thẻ Căn Cước của {ctx.author.name}", color=khung_mau)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    embed.add_field(name="Cấp độ", value=f"🌟 **LV {lv}**", inline=True)
    
    tien_text = f"**{tien:,} 💰**\n*(ĐANG NỢ)*" if tien < 0 else f"**{tien:,} 💰**"
    embed.add_field(name="Tài sản", value=tien_text, inline=True)
    
    # Thanh tiến trình XP
    bar = make_progress_bar(xp, max_xp)
    embed.add_field(name="Kinh nghiệm", value=f"`{bar}`\n**{xp}/{max_xp} XP**", inline=False)
    
    await ctx.send(embed=embed)

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
        
        embed = discord.Embed(title="🎉 THĂNG CẤP!", color=discord.Color.gold())
        embed.description = f"Chúc mừng {message.author.mention} đã tu luyện đạt **Cấp {user_data['level']}**!\nPhần thưởng: **{thuong:,} 💰**"
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
