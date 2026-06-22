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
coin_cooldowns = {}
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


# =====================================================================
# KHO SỰ KIỆN NHÂN SINH (CÓ XÁC SUẤT % THÀNH CÔNG)
# =====================================================================
# rate_a, rate_b là tỉ lệ % thành công cơ bản. 
# win_a: Lời thoại thắng A | lose_a: Lời thoại thua A
# tien_wa: Tiền nhận khi thắng A | tien_la: Tiền bị trừ khi thua A

EVENTS_P1 = [
    {"q": "Lớp trưởng xúi bạn trốn học đi net.", 
     "a": "Đi luôn sợ gì", "rate_a": 40, "win_a": "Thầy cô không điểm danh, bạn leo rank vù vù.", "tien_wa": 200, "lose_a": "Bị giám thị bắt tại trận, mời phụ huynh.", "tien_la": -300,
     "b": "Ở lại học bài", "rate_b": 70, "win_b": "Cô giáo điểm danh đột xuất, bạn an toàn tuyệt đối.", "tien_wb": 100, "lose_b": "Ngồi trong lớp nhưng ngủ gật, vẫn bị chép phạt.", "tien_lb": -50},
    
    {"q": "Bạn nhặt được ví tiền của thầy Hiệu trưởng.",
     "a": "Tiêu xài đập phá", "rate_a": 30, "win_a": "Không ai phát hiện, bạn bao bạn bè một chầu linh đình.", "tien_wa": 800, "lose_a": "Bị check camera, bêu tên trước cờ.", "tien_la": -500,
     "b": "Trả lại phòng giám thị", "rate_b": 80, "win_b": "Được tuyên dương và thưởng nóng.", "tien_wb": 300, "lose_b": "Giám thị tưởng bạn là người ăn cắp, bị nghi ngờ.", "tien_lb": 0},
    
    {"q": "Crush bất ngờ tỏ tình ngay sát ngày thi.",
     "a": "Đồng ý yêu luôn", "rate_a": 45, "win_a": "Tình yêu thăng hoa, cùng nhau thi đỗ.", "tien_wa": 400, "lose_a": "Yêu đương mù quáng, cả hai rớt đại học.", "tien_la": -400,
     "b": "Từ chối khéo", "rate_b": 60, "win_b": "Crush nể phục, bạn tập trung đỗ thủ khoa.", "tien_wb": 600, "lose_b": "Crush ghét bạn, lan truyền tin đồn thất thiệt.", "tien_lb": -200},
     
    {"q": "Nhóm đầu gấu chặn đường xin đểu.",
     "a": "Gồng lên đánh lại", "rate_a": 35, "win_a": "Bộc phát Haki, đánh đuổi được lũ côn đồ.", "tien_wa": 500, "lose_a": "Bị đấm sưng mắt, mất sạch tiền.", "tien_la": -400,
     "b": "Bỏ chạy thục mạng", "rate_b": 65, "win_b": "Chạy nhanh như Flash, thoát nạn.", "tien_wb": 0, "lose_b": "Vấp cục đá ngã sấp mặt, vẫn bị lột tiền.", "tien_lb": -300},
     
    {"q": "Nhặt được tờ vé số cũ trong ngăn bàn.",
     "a": "Mang đi dò", "rate_a": 15, "win_a": "Trúng giải nhất! Bỗng dưng có tiền ăn vặt rủng rỉnh.", "tien_wa": 1500, "lose_a": "Tờ vé số đã hết hạn từ 8 kiếp trước.", "tien_la": 0,
     "b": "Vứt đi cho sạch", "rate_b": 90, "win_b": "Bàn học sạch sẽ gọn gàng.", "tien_wb": 50, "lose_b": "Lỡ tay vứt nhầm luôn tờ tiền 100k kẹp bên trong.", "tien_lb": -100},
     
    {"q": "Tham gia thi năng khiếu cấp trường.",
     "a": "Đăng ký thi hát", "rate_a": 40, "win_a": "Giọng ca vàng, ẵm giải Nhất kèm phong bì.", "tien_wa": 800, "lose_a": "Hát oét nốt, thành meme chế giễu toàn trường.", "tien_la": -200,
     "b": "Ngồi dưới vỗ tay", "rate_b": 85, "win_b": "Nhàn nhã không làm gì vẫn được ăn bánh kẹo.", "tien_wb": 100, "lose_b": "Bị bắt đi dọn rác sau hậu trường.", "tien_lb": -50},
     
    {"q": "Bạn tìm thấy con chó hoang đang đói.",
     "a": "Mang về nuôi", "rate_a": 50, "win_a": "Chó khôn, đi bắt chuột bắt gián giúp bạn.", "tien_wa": 200, "lose_a": "Chó cắn xé đồ đạc trong nhà, đền ốm.", "tien_la": -300,
     "b": "Bỏ đi không quan tâm", "rate_b": 75, "win_b": "Tránh được phiền phức.", "tien_wb": 0, "lose_b": "Bị bạn bè bảo là máu lạnh.", "tien_lb": -50}
]

EVENTS_P2 = [
    {"q": "Vừa ra trường, bạn muốn kiếm tiền nhanh.",
     "a": "Vay nặng lãi Khởi nghiệp", "rate_a": 25, "win_a": "Công ty lên sàn, bạn trở thành CEO tuổi 25!", "tien_wa": 4000, "lose_a": "Phá sản sau 3 tháng, giang hồ đòi nợ.", "tien_la": -3000},
     "b": "Làm văn phòng an toàn", "rate_b": 70, "win_b": "Lương đều đặn, tích cóp được sổ tiết kiệm.", "tien_wb": 800, "lose_b": "Công ty cắt giảm nhân sự, bạn thất nghiệp.", "tien_lb": -500},
    
    {"q": "Thấy người ta trade Coin lãi khủng.",
     "a": "All-in tiền tiết kiệm", "rate_a": 20, "win_a": "Coin x10 tài khoản! Bạn đổi đời chớp nhoáng.", "tien_wa": 5000, "lose_a": "Đu đỉnh đu mát, chia 10 tài khoản, khóc ròng.", "tien_la": -4000,
     "b": "Bỏ qua không chơi", "rate_b": 80, "win_b": "Bảo toàn vốn, thị trường sập bạn ngồi cười.", "tien_wb": 300, "lose_b": "Coin tăng vọt, bạn tiếc đứt ruột sinh bệnh.", "tien_lb": -200},
     
    {"q": "Đồng nghiệp rủ mở quán nhậu chung.",
     "a": "Góp vốn làm ăn", "rate_a": 40, "win_a": "Quán đông nghịt khách, thu hồi vốn sau 2 tháng.", "tien_wa": 2500, "lose_a": "Đồng nghiệp ôm tiền bỏ trốn, bạn è cổ trả nợ.", "tien_la": -2000,
     "b": "Xin từ chối", "rate_b": 75, "win_b": "Tiền vẫn nằm ngoan trong két sắt.", "tien_wb": 200, "lose_b": "Mất tình anh em đồng nghiệp.", "tien_lb": -100},
     
    {"q": "Sếp ép bạn nhận tội thay trong một dự án lỗi.",
     "a": "Đăng bài bóc phốt sếp", "rate_a": 35, "win_a": "Cộng đồng mạng ủng hộ, sếp bị đuổi, bạn lên thay.", "tien_wa": 3000, "lose_a": "Bị kiện ngược tội vu khống, đền tiền ốm.", "tien_la": -2500,
     "b": "Ngậm đắng nuốt cay", "rate_b": 60, "win_b": "Sếp thấy áy náy nên thưởng nóng bù đắp.", "tien_wb": 1000, "lose_b": "Bị đuổi việc để làm dê thế tội.", "tien_lb": -1500},
     
    {"q": "Người yêu cũ giàu có rủ quay lại.",
     "a": "Đồng ý luôn", "rate_a": 30, "win_a": "Cưới nhau, sống sung sướng trong biệt thự.", "tien_wa": 3500, "lose_a": "Bị cắm sừng lần 2, lừa sạch tiền bạc.", "tien_la": -2000,
     "b": "Say No!", "rate_b": 80, "win_b": "Tự trọng dâng cao, dốc lòng làm việc thăng tiến.", "tien_wb": 800, "lose_b": "Cô đơn buồn bã nhậu nhẹt tốn tiền.", "tien_lb": -300},

    {"q": "Nhận được lời mời làm quảng cáo đa cấp.",
     "a": "Nhận làm để kiếm tiền", "rate_a": 40, "win_a": "Lùa được một đống gà, hoa hồng ngập mặt.", "tien_wa": 3000, "lose_a": "Bị bế lên phường vì lừa đảo.", "tien_la": -3500,
     "b": "Từ chối thẳng thừng", "rate_b": 85, "win_b": "Giữ sạch hồ sơ, uy tín cá nhân.", "tien_wb": 200, "lose_b": "Bọn đa cấp ghim hận, report sập Facebook.", "tien_lb": -200},

    {"q": "Đang đi đường thì thấy túi xách nữ rơi.",
     "a": "Mang đến đồn công an", "rate_a": 70, "win_a": "Chủ nhân là nữ đại gia, hậu tạ một món lớn.", "tien_wa": 1500, "lose_a": "Bị hiểu lầm là ăn cắp, vướng vòng lao lý.", "tien_la": -1000,
     "b": "Lấy tiền rồi vứt túi", "rate_b": 30, "win_b": "Tiêu xài tẹt ga số tiền trong ví.", "tien_wa": 2000, "lose_b": "Túi có định vị GPS, bị bắt tại trận.", "tien_lb": -3000}
]

EVENTS_P3 = [
    {"q": "Thị trường đóng băng, có người gạ bán rẻ mảnh đất.",
     "a": "Mua bắt đáy", "rate_a": 30, "win_a": "Đất sốt trở lại, bán sang tay lãi gấp 3!", "tien_wa": 6000, "lose_a": "Đất dính quy hoạch, ôm nợ ngân hàng mọt kiếp.", "tien_la": -5000,
     "b": "Lắc đầu chê xa", "rate_b": 80, "win_b": "Bảo toàn số tiền chắt bóp bao năm.", "tien_wb": 500, "lose_b": "Mảnh đất sau này xây sân bay, tiếc hùi hụi.", "tien_lb": -500},
     
    {"q": "Bước vào Casino lớn nhất nước.",
     "a": "Chơi khô máu Poker", "rate_a": 15, "win_a": "Đánh bại thần bài, ẵm tiền tỉ ra về!", "tien_wa": 10000, "lose_a": "Thua trắng dái, cầm luôn sổ đỏ nhà.", "tien_la": -8000,
     "b": "Chơi cò con 100 đô", "rate_b": 60, "win_b": "Giải trí vui vẻ, hên hên trúng nhỏ.", "tien_wb": 800, "lose_b": "Thua chút tiền, coi như mua vui.", "tien_lb": -300},
     
    {"q": "Sức khỏe xuống cấp, đau nhức liên miên.",
     "a": "Mua thuốc bí truyền mọc tóc", "rate_a": 25, "win_a": "Thuốc tiên! Khỏe như trâu, sinh lực dồi dào.", "tien_wa": 1500, "lose_a": "Suy gan suy thận, viện phí chất đống.", "tien_la": -4000,
     "b": "Đăng ký tập Gym", "rate_b": 75, "win_b": "Khỏe mạnh, body săn chắc tuổi xế chiều.", "tien_wb": 500, "lose_b": "Tập sai tư thế, trật khớp gãy xương.", "tien_lb": -800},
     
    {"q": "Quỹ từ thiện lạ mặt gọi điện xin quyên góp.",
     "a": "Chuyển 50 củ ủng hộ", "rate_a": 30, "win_a": "Quỹ thật, được lên báo tuyên dương, nhận bằng khen.", "tien_wa": 2000, "lose_a": "Bị lừa đảo qua mạng, mất sạch.", "tien_la": -2000,
     "b": "Tắt máy chặn số", "rate_b": 90, "win_b": "Không sợ bị lừa.", "tien_wb": 100, "lose_b": "Bị cộng đồng mạng chửi là kẹt xỉn.", "tien_lb": -200},

    {"q": "Vô tình đào được bình gốm cổ dưới vườn nhà.",
     "a": "Đem đi đấu giá", "rate_a": 35, "win_a": "Đồ cổ đời Tống, đại gia tranh nhau mua giá trên trời!", "tien_wa": 8000, "lose_a": "Hàng fake mua ở chợ đồ sành sứ, mất tiền giám định.", "tien_la": -500,
     "b": "Để làm chậu trồng cây", "rate_b": 85, "win_b": "Cây mọc xanh tốt, thư giãn tinh thần.", "tien_wb": 200, "lose_b": "Lỡ tay làm vỡ đứt tay, tốn tiền khâu.", "tien_lb": -100}
]


# =====================================================================
# DATA THÁM HIỂM (KHU RỪNG)
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "Gậy Gỗ Mục", "terrible": 20, "bad": 40, "neutral": 20, "good": 15, "great": 5, "jackpot": 0},
    "kiem_sat": {"price": 200, "name": "Kiếm Sắt Thường", "terrible": 10, "bad": 25, "neutral": 20, "good": 30, "great": 12, "jackpot": 3},
    "kiem_hiep_si": {"price": 500, "name": "Kiếm Hiệp Sĩ", "terrible": 5, "bad": 15, "neutral": 15, "good": 35, "great": 20, "jackpot": 10},
    "thanh_kiem": {"price": 1500, "name": "Thánh Kiếm Truyền Thuyết", "terrible": 0, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 20}
}

SCENARIOS = {
    "terrible": [ 
        {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền khi bỏ chạy!"},
        {"mult": -1.2, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!**\nGặp ngay băng thổ phỉ khét tiếng. Chúng trói bạn vào gốc cây và lột sạch đồ đạc."},
        {"mult": -1.0, "msg": "💥 **ĐẠP TRÚNG MÌN GOBLIN!**\nBÙM! Bạn đạp trúng mìn tự chế của bọn Goblin. Tốn một mớ tiền để trả phí cấp cứu."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"mult": -0.4, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi mua bông băng thuốc đỏ."},
        {"mult": -0.3, "msg": "🦟 **MUỖI KHỔNG LỒ!**\nBị bầy muỗi rừng khổng lồ chích sưng vù, phải đi mua thuốc mỡ bôi."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"mult": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"mult": 0.6, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá kha khá!"}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp nhỏ và tịch thu kho báu của chúng!"},
        {"mult": 2.0, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, ai ngờ đào trúng viên ngọc lục bảo thô to bằng nắm tay!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng giải đặc biệt!"},
        {"mult": 10.0, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Bạn tìm thấy hang động cất giấu kho báu huyền thoại. Một núi Vàng hiện ra trước mắt!"}
    ]
}


# =====================================================================
# VIEW: MÔ PHỎNG NHÂN SINH (ĐÃ FIX LỖI 100%)
# =====================================================================

class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=120)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        self.ev = random.choice(EVENTS_P1)

        # Lời bình đầu đời
        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, bố mẹ là chủ tịch tập đoàn.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài chợ từ nhỏ.")

        # Nút lựa chọn
        self.btn_a = discord.ui.Button(label=f"A. {self.ev['a']}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_a.callback = self.choice_a
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['b']}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_b.callback = self.choice_b

        self.add_item(self.btn_a)
        self.add_item(self.btn_b)

    async def on_timeout(self):
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: 
            dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng bấm lung tung!", ephemeral=True)
            return False
        return True

    async def choice_a(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, "A")
        
    async def choice_b(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, "B")

    async def process_choice(self, interaction: discord.Interaction, choice: str):
        # 1. Tính toán tỉ lệ thành công cơ bản + buff May Mắn (Mỗi điểm May Mắn + 2% tỉ lệ)
        base_rate = self.ev["rate_a"] if choice == "A" else self.ev["rate_b"]
        final_rate = base_rate + (self.stats["may_man"] * 2)
        if final_rate > 95: final_rate = 95 # Tối đa 95% thành công
        
        # 2. Đổ xúc xắc ngẫu nhiên (1-100)
        roll = random.randint(1, 100)
        is_win = roll <= final_rate
        
        # 3. Lấy kết quả
        if choice == "A":
            res = self.ev["win_a"] if is_win else self.ev["lose_a"]
            tien = self.ev["tien_wa"] if is_win else self.ev["tien_la"]
        else:
            res = self.ev["win_b"] if is_win else self.ev["lose_b"]
            tien = self.ev["tien_wb"] if is_win else self.ev["tien_lb"]

        # 4. Lưu tiền
        self.tien_an += tien
        
        # 5. Ghi Log
        kq_thung = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ thành công: **{final_rate}%** (Xúc xắc đổ ra {roll})\n{kq_thung}: {res} ({tien} 💰)"
        
        if self.phase == 1:
            self.logs.append(f"🎒 **Tuổi 15:** Bạn chọn {choice}.\n{log_entry}")
            self.phase = 2
            self.ev = random.choice(EVENTS_P2)
        elif self.phase == 2:
            self.logs.append(f"💼 **Tuổi 25:** Bạn chọn {choice}.\n{log_entry}")
            self.phase = 3
            self.ev = random.choice(EVENTS_P3)
        elif self.phase == 3:
            self.logs.append(f"🏦 **Tuổi 35:** Bạn chọn {choice}.\n{log_entry}")
            self.phase = 4

        # Cập nhật Giao diện
        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.purple())

        stats_text = f"May mắn ban đầu: **{self.stats['may_man']}/10** *(+ {self.stats['may_man']*2}% thành công)*"
        embed.add_field(name="🍀 Chỉ số tâm linh", value=stats_text, inline=False)

        story = "\n\n".join(self.logs)
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase < 4:
            tuoi = 15 if self.phase == 1 else 25 if self.phase == 2 else 35
            embed.add_field(name=f"❓ Quyết định tuổi {tuoi}", value=self.ev['q'], inline=False)
            self.btn_a.label = f"A. {self.ev['a']}"
            self.btn_b.label = f"B. {self.ev['b']}"
        else:
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.clear_items() 

            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

            total_reward = self.tien_an 
            
            user_data = load_user(user_id)
            user_data["money"] += total_reward
            save_user(user_id)

            if total_reward < 0:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Sống lay lắt qua ngày, cuối đời bệnh tật không tiền chữa.\n❌ **BÁO NHÀ!** Bạn để lại khoản nợ: **{total_reward} 💰**\n*(Hệ thống đã trừ nợ vào sổ, đi cày `k daily` mà trả nhé!)*", inline=False)
            elif total_reward >= 5000:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Hưởng thọ trong biệt thự cao cấp. Tang lễ hoành tráng.\n👑 **ĐẠI PHÚ HÀO!** Di sản kiếp sau: **+{total_reward} 💰**", inline=False)
            else:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Cuộc đời bình dị, thanh thản ra đi bên con cháu.\n💼 **DƯ DẢ!** Di sản kiếp sau: **+{total_reward} 💰**", inline=False)

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{user_data['money']} 💰**", inline=False)

        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)


# =====================================================================
# GIAO DIỆN NÚT BẤM KHU RỪNG
# =====================================================================

class BushButton(discord.ui.Button):
    def __init__(self, label, style, custom_id):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        weapon_id = view.weapon_val
        weapon_info = WEAPON_ODDS[weapon_id]
        
        for child in view.children: child.disabled = True
        await interaction.response.edit_message(content=f"🗡️ {interaction.user.mention} cầm **{weapon_info['name']}** vạch {self.label} ra...\nĐợi một chút...", view=view)
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
        
        profit_text = f"LÃI +{new_session_profit}" if new_session_profit > 0 else f"LỖ {new_session_profit}" if new_session_profit < 0 else "HUỀ VỐN"
        icon_tien = "📉 LỖ" if thuong_phat < 0 else "📈 LÃI" if thuong_phat > 0 else "➖ HUỀ"
        
        ket_qua_text = f"{scenario['msg']}\n\n{icon_tien}: **{thuong_phat} 💰**\n💸 **Số dư hiện tại:** **{user_data['money']} 💰**\n📊 **Tổng kết phiên:** **{profit_text}**"
        
        res_view = ResultView(interaction.user, new_session_profit)
        msg = await interaction.original_response()
        await msg.edit(content=ket_qua_text, view=res_view)

class ResultView(discord.ui.View):
    def __init__(self, author, session_profit):
        super().__init__(timeout=120)
        self.author = author
        self.session_profit = session_profit
        btn_tiep = discord.ui.Button(label="Thám hiểm tiếp", style=discord.ButtonStyle.primary, emoji="🔄")
        btn_tiep.callback = self.continue_explore
        self.add_item(btn_tiep)
        btn_dung = discord.ui.Button(label="Nghỉ ngơi", style=discord.ButtonStyle.danger, emoji="🛑")
        btn_dung.callback = self.stop_explore
        self.add_item(btn_dung)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Đây không phải báo cáo của bạn!", ephemeral=True)
            return False
        return True

    async def continue_explore(self, interaction: discord.Interaction):
        shop_embed = discord.Embed(
            title="🛒 TRẠM TIẾP TẾ THÁM HIỂM 🛒",
            description="Chào mừng quay lại Trạm! Hãy mua vũ khí để bắt đầu chuyến đi mới.\n\n👇 **CLICK VÀO MENU ĐỂ CHỌN MUA** 👇",
            color=discord.Color.dark_red()
        )
        if self.session_profit > 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LÃI +{self.session_profit} 💰")
        elif self.session_profit < 0: shop_embed.set_footer(text=f"📊 Kỷ lục phiên này: Đang LỖ {self.session_profit} 💰")
        else: shop_embed.set_footer(text="📊 Kỷ lục phiên này: Đang HUỀ VỐN")

        view = ShopView(self.author, self.session_profit)
        await interaction.response.edit_message(content=None, embed=shop_embed, view=view)

    async def stop_explore(self, interaction: discord.Interaction):
        for child in self.children: child.disabled = True
        profit_text = f"LÃI +{self.session_profit} 💰" if self.session_profit > 0 else f"LỖ {self.session_profit} 💰" if self.session_profit < 0 else "HUỀ VỐN"
        chot_so_msg = f"\n\n🛑 **ĐÃ KẾT THÚC CHUYẾN THÁM HIỂM.**\nTổng kết cả phiên: **{profit_text}**"
        await interaction.response.edit_message(content=interaction.message.content + chot_so_msg, view=self)

class BushView(discord.ui.View):
    def __init__(self, author, weapon_val, session_profit):
        super().__init__(timeout=60)
        self.author = author
        self.weapon_val = weapon_val
        self.session_profit = session_profit
        for i in range(1, 6):
            self.add_item(BushButton(label=f"Lùm Cây {i}", style=discord.ButtonStyle.success, custom_id=f"bush_{i}"))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Tránh ra, lùm cây này tôi giành rồi!", ephemeral=True)
            return False
        return True

class WeaponSelect(discord.ui.Select):
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = [
            discord.SelectOption(label="Gậy Gỗ Mục", description="Giá: 50 💰 | Tỉ lệ hên: Cực thấp", emoji="🪵", value="gay_go"),
            discord.SelectOption(label="Kiếm Sắt Thường", description="Giá: 200 💰 | Tỉ lệ hên: Bình thường", emoji="🗡️", value="kiem_sat"),
            discord.SelectOption(label="Kiếm Hiệp Sĩ", description="Giá: 500 💰 | Tỉ lệ hên: Khá Cao", emoji="⚔️", value="kiem_hiep_si"),
            discord.SelectOption(label="Thánh Kiếm Mạ Vàng", description="Giá: 1500 💰 | Tỉ lệ hên: Tuyệt đỉnh", emoji="🔱", value="thanh_kiem")
        ]
        super().__init__(placeholder="Nhấp vào để mua vũ khí...", min_values=1, max_values=1, options=options)

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
        text = f"🌲 **KHU RỪNG KỲ BÍ ĐÃ MỞ** 🌲\n\n*Trạng thái: Đã tốn {price} 💰 trang bị {weapon_name}*\n\nSương mù rạp xuống... Bạn thấy **5 Lùm Cây** đang rung rinh. Bấm chọn lùm cây để đào kho báu đi!"
        await interaction.response.edit_message(content=text, embed=None, view=view)

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
        super().__init__(placeholder="Chọn khu vực phái đi...", min_values=1, max_values=1, options=options)

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

        await interaction.response.edit_message(content=f"⛺ {interaction.user.mention} đã thu xếp hành lý và bắt đầu hành trình **{hours} giờ**!\nHãy dùng lại lệnh `k phai` để nhận thưởng khi hết thời gian nhé.", view=None, embed=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Lệnh của ai người nấy bấm nhé!", ephemeral=True)
            return False
        return True


# =====================================================================
# CÁC LỆNH CHÍNH CỦA BOT
# =====================================================================

@bot.command()
async def help(ctx):
    bang_help = discord.Embed(title="📚 BẢNG LỆNH CỦA BOT 📚", color=discord.Color.blue())
    bang_help.add_field(name="✨ `k rank`", value="Xem hồ sơ và số Tiền 💰 hiện tại.", inline=False)
    bang_help.add_field(name="🏆 `k top`", value="Bảng xếp hạng đại gia.", inline=False)
    bang_help.add_field(name="📅 `k daily`", value="Nhận lương hằng ngày (500 💰).", inline=False)
    bang_help.add_field(name="🪙 `k coin <số tiền/all>`", value="Cờ bạc tung xu hồi hộp (Chờ 3s).", inline=False)
    bang_help.add_field(name="🌲 `k thamhiem`", value="Khám phá rừng rậm nhân phẩm.", inline=False)
    bang_help.add_field(name="⛺ `k phai`", value="Phái đi thám hiểm (Treo máy AFK kiếm tiền).", inline=False)
    bang_help.add_field(name="🌀 `k nhansinh`", value="Game Tương Tác Cốt Truyện (Phí: 100 💰).", inline=False)
    bang_help.add_field(name="💸 `k give @người-nhận <số tiền>`", value="Chuyển khoản.", inline=False)
    bang_help.add_field(name="⚙️ `k setup #kênh1 #kênh2`", value="(Quản trị viên) Cài đặt kênh cho phép gõ lệnh.", inline=False)
    bang_help.add_field(name="⚙️ `k setkenh #tên-kênh`", value="(Quản trị viên) Chỉnh kênh thông báo lên cấp.", inline=False)
    await ctx.send(embed=bang_help)

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
            await ctx.send(f"🎉 {ctx.author.mention} đã vác ba lô trở về an toàn! Bạn mở túi ra và thu hoạch được **{reward} 💰**. (Số dư: **{user_data['money']} 💰**)")
        else:
            time_left = exp_end - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"⏳ Đang hì hục cày cuốc trong rừng! Hãy kiên nhẫn chờ thêm **{hours} giờ {minutes} phút** nữa nhé.")
        return

    embed = discord.Embed(title="⛺ TRẠM THÁM HIỂM AFK ⛺", description="Bạn bận rộn không có thời gian cày cuốc? Hãy gửi nhân vật đi treo máy và nhặt tiền lúc trở về!\n\n👇 **CHỌN THỜI GIAN THÁM HIỂM BÊN DƯỚI** 👇", color=discord.Color.green())
    view = ExpView(ctx.author)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    shop_embed = discord.Embed(
        title="🛒 TRẠM TIẾP TẾ THÁM HIỂM 🛒",
        description="Chào mừng đến với hội Thám Hiểm! Để vào Khu Rừng Kỳ Bí, bạn cần vũ khí. Chơi đồ xịn thì trúng mánh lớn, cầm cành cây thì dễ ăn đòn.\n\n👇 **HÃY CLICK VÀO THANH MENU BÊN DƯỚI ĐỂ CHỌN MUA** 👇",
        color=discord.Color.dark_red()
    )
    view = ShopView(ctx.author, session_profit=0)
    await ctx.send(embed=shop_embed, view=view)

@bot.command()
async def nhansinh(ctx):
    user_id = str(ctx.author.id)
    phi = 100
    now = datetime.now()

    if user_id in dang_choi_nhansinh:
        await ctx.send(f"⏳ {ctx.author.mention}, bạn đang luân hồi dở dang rồi! Hoàn thành kiếp trước đi đã.")
        return

    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5:
        giay_con_lai = int(5 - (now - nhansinh_cooldowns[user_id]).total_seconds())
        await ctx.send(f"⏳ Linh hồn bạn vừa mới luân hồi, cần nghỉ ngơi! Đợi **{giay_con_lai} giây** nữa mới được đầu thai tiếp.")
        return

    user_data = load_user(user_id)
    if user_data.get("money", 0) < phi:
        await ctx.send(f"Phí mua vé luân hồi đi đầu thai là **{phi} 💰**. Nợ nần hay nghèo rớt mồng tơi thì không có cửa đi đầu thai đâu!")
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
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{stats['may_man']}/10** *(+ {stats['may_man']*2}% thành công)*", inline=False)
    
    story = "\n\n".join(view.logs)
    embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)
    embed.add_field(name="❓ Ngã rẽ tuổi học trò (15 tuổi)", value=view.ev['q'], inline=False)

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
            await ctx.send(f"⏳ Tham lam vậy! Trở lại sau **{hours} giờ {minutes} phút** nữa để nhận lương tiếp nhé.")
            return

    user_data["money"] += 500
    user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(user_id)
    
    if user_data["money"] < 0:
        await ctx.send(f"🎁 Bạn nhận được **500 💰** tiền công!\n⚠️ Hệ thống đã siết nợ tự động! Bạn vẫn còn đang nợ **{user_data['money']} 💰**.")
    else:
        await ctx.send(f"🎁 Bạn nhận được **500 💰** tiền công! (Số dư: **{user_data['money']} 💰**)")

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    danh_sach_dai_gia = [(doc["_id"], doc.get("money", 0)) for doc in all_users]
    danh_sach_dai_gia.sort(key=lambda x: x[1], reverse=True)
    
    bang_xep_hang = discord.Embed(title="🏆 TOP ĐẠI GIA SERVER 🏆", color=discord.Color.gold())
    thu_hang = 1
    
    for user_id, tien in danh_sach_dai_gia[:10]:
        user = bot.get_user(int(user_id))
        if user is None:
            try: user = await bot.fetch_user(int(user_id))
            except: pass
                
        ten = user.name if user else f"Người chơi {user_id[-4:]}"
        icon = "🥇" if thu_hang == 1 else "🥈" if thu_hang == 2 else "🥉" if thu_hang == 3 else f"#{thu_hang}"
        bang_xep_hang.add_field(name=f"{icon} {ten}", value=f"**{tien} 💰**", inline=False)
        thu_hang += 1
        
    await ctx.send(embed=bang_xep_hang)

@bot.command()
async def coin(ctx, amount: str):
    user_id = str(ctx.author.id)
    now = datetime.now()

    if user_id in coin_cooldowns and (now - coin_cooldowns[user_id]).total_seconds() < 3:
        await ctx.send(f"⏳ Máu cờ bạc nổi lên à? Đợi {int(3 - (now - coin_cooldowns[user_id]).total_seconds())}s nữa nhé!")
        return

    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        if user_data.get("money", 0) < 0:
            await ctx.send("Tài khoản đang **nợ nần chồng chất** mà dám vào casino à? Đi cày `k daily` hoặc `k phai` trả nợ ngay!")
        else:
            await ctx.send("Túi rỗng tếch mà đòi cá cược! Chạy `k daily` đi.")
        return

    tien_hien_tai = user_data["money"]
    try: bet = tien_hien_tai if amount.lower() == "all" else int(amount)
    except: return await ctx.send("Số cược không hợp lệ!")

    if bet <= 0 or bet > tien_hien_tai:
        return await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai} 💰**.")

    user_data["money"] -= bet
    save_user(user_id)
    coin_cooldowns[user_id] = now

    msg = await ctx.send(f"🪙 {ctx.author.mention} ném **{bet} 💰** lên trời...")
    await asyncio.sleep(1) 
    await msg.edit(content=f"🪙 {ctx.author.mention} ném **{bet} 💰** lên trời...\n🔄 Đồng xu lộn nhào...")
    await asyncio.sleep(1) 
    await msg.edit(content=f"🪙 {ctx.author.mention} ném **{bet} 💰** lên trời...\n🔄 Đồng xu lộn nhào...\n💥 Rơi rầm xuống đất...")
    await asyncio.sleep(1) 

    user_data = load_user(user_id)
    if random.choice(["thắng", "thua"]) == "thắng":
        user_data["money"] += (bet * 2)
        save_user(user_id)
        await msg.edit(content=f"🪙 **MẶT NGỬA!**\n🎉 {ctx.author.mention} húp trọn **{bet * 2} 💰**! (Dư: **{user_data['money']} 💰**)")
    else:
        await msg.edit(content=f"🪙 **MẶT SẤP!**\n💀 Nhờn! {ctx.author.mention} ra gầm cầu ngủ! Mất **{bet} 💰**. (Dư: **{user_data['money']} 💰**)")

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
    
    await ctx.send(f"💸 {ctx.author.mention} đã chuyển {member.mention} **{amount} 💰**.")

@bot.command()
@commands.has_permissions(administrator=True) 
async def setkenh(ctx, kenh: discord.TextChannel):
    server_id = str(ctx.guild.id)
    config_col.update_one({"_id": server_id}, {"$set": {"channel_id": kenh.id}}, upsert=True)
    if server_id not in CONFIG_CACHE:
        CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["channel_id"] = kenh.id
    await ctx.send(f'✅ Đã lưu kênh báo lên cấp: {kenh.mention}!')

@bot.command()
async def rank(ctx):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    lv, xp, tien = user_data.get("level", 1), user_data.get("xp", 0), user_data.get("money", 0)
    
    khung_mau = discord.Color.red() if tien < 0 else discord.Color.green()
    embed = discord.Embed(title=f"Hồ sơ của {ctx.author.name}", color=khung_mau)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.add_field(name="Cấp độ", value=f"**{lv}**", inline=True)
    embed.add_field(name="Kinh nghiệm", value=f"**{xp}/{lv*100} XP**", inline=True)
    
    tien_text = f"**{tien} 💰** (ĐANG MANG NỢ)" if tien < 0 else f"**{tien} 💰**"
    embed.add_field(name="Tài sản", value=tien_text, inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    u_id = str(message.author.id)
    user_data = load_user(u_id)

    user_data["xp"] += random.randint(5, 15)

    if user_data["xp"] >= user_data["level"] * 100:
        user_data["xp"] -= user_data["level"] * 100
        user_data["level"] += 1
        thuong = user_data["level"] * 150
        user_data["money"] += thuong
        
        tb = discord.Embed(title="🎉 LÊN CẤP! 🎉", description=f'{message.author.mention} đạt Cấp {user_data["level"]}!\nThưởng: **{thuong} 💰**', color=discord.Color.gold())
        
        config = load_server_config(message.guild.id)
        kenh_id = config.get("channel_id")
        k = bot.get_channel(kenh_id) if kenh_id else message.channel
        if k: await k.send(embed=tb)

    save_user(u_id)
    await bot.process_commands(message)

@bot.event
async def on_ready(): print(f'{bot.user} đã lên mạng và sẵn sàng!')

keep_alive() 

# === HAI NỬA MÃ TOKEN ===
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
nua_sau = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(nua_dau + nua_sau)
