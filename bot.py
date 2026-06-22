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
# KHO SỰ KIỆN NHÂN SINH (5 GIAI ĐOẠN - CÓ ĐỘT TỬ)
# =====================================================================
# Thêm cờ "die_l": True nếu nhánh thua dẫn đến cái chết.

EVENTS_P1 = [ # TUỔI 15
    {
        "q": "Tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.",
        "choices": [
            {"text": "Đem nộp lên công an", "rate": 80, "win": "Chủ ví là người tốt, hậu tạ bạn một ít tiền.", "lose": "Công an giữ lại điều tra lâu lắc, tốn công vô ích.", "tien_w": 500, "tien_l": -100},
            {"text": "Bỏ túi xài luôn", "rate": 20, "win": "Không ai biết, bạn bao lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường gấp đôi và bị đuổi học.", "tien_w": 3000, "tien_l": -8000},
            {"text": "Lấy tờ 500k rồi vứt lại ví", "rate": 40, "win": "Trót lọt, bạn mua được món đồ chơi yêu thích.", "lose": "Chủ nhân báo mất, bạn bị tra hỏi và phạt nặng.", "tien_w": 1000, "tien_l": -4000},
            {"text": "Giả vờ không thấy", "rate": 95, "win": "Bạn thong thả đi học tiếp, chẳng rước họa vào thân.", "lose": "Đứa đi sau nhặt được quay ra đổ oan cho bạn.", "tien_w": 0, "tien_l": -500}
        ]
    },
    {
        "q": "Kỳ thi cuối cấp cận kề, bạn bè rủ cúp học đi chơi net xuyên đêm.",
        "choices": [
            {"text": "Ở nhà ôn bài kỹ", "rate": 85, "win": "Bạn đỗ thủ khoa, được họ hàng thưởng tiền.", "lose": "Học tài thi phận, bạn vẫn trượt vỏ chuối.", "tien_w": 1500, "tien_l": -500},
            {"text": "Đi net cày rank", "rate": 10, "win": "Đi thi trúng phóc tủ mảng vừa đọc lướt ở net!", "lose": "Mắt nhắm mắt mở chạy xe về, tai nạn thăng thiên.", "tien_w": 2500, "tien_l": -10000, "die_l": True},
            {"text": "Làm phao mang vào", "rate": 35, "win": "Mở phao mượt mà, điểm cao chót vót.", "lose": "Giám thị bắt quả tang, đánh dấu bài 0 điểm.", "tien_w": 2000, "tien_l": -5000},
            {"text": "Ngủ cho khỏe", "rate": 50, "win": "Tinh thần sảng khoái, làm bài vừa đủ đậu.", "lose": "Ngủ nhiều lú não, làm sai hết phép tính cơ bản.", "tien_w": 800, "tien_l": -1000}
        ]
    }
]

EVENTS_P2 = [ # TUỔI 25
    {
        "q": "Bạn tích cóp được một số vốn nhỏ và muốn làm giàu nhanh.",
        "choices": [
            {"text": "Đầu tư Coin rác (Shitcoin)", "rate": 10, "win": "Coin x100, bạn đổi đời thành đại gia sau 1 đêm!", "lose": "Cháy tài khoản, nhảy cầu tự vẫn bỏ lại gia đình.", "tien_w": 60000, "tien_l": -50000, "die_l": True},
            {"text": "Mua vàng tích trữ", "rate": 85, "win": "Vàng nhích lên từ từ, bạn an tâm sống qua ngày.", "lose": "Giá vàng sập ngắn hạn, lỗ nhẹ phí chênh lệch.", "tien_w": 2500, "tien_l": -1500},
            {"text": "Mở quán cafe vỉa hè", "rate": 45, "win": "Quán đông khách nhờ review Tóp Tóp, mở chuỗi chi nhánh.", "lose": "Ế ẩm, dẹp tiệm sau 3 tháng, tiền thuê mặt bằng cắn đứt ví.", "tien_w": 12000, "tien_l": -15000},
            {"text": "Cho vay nặng lãi", "rate": 15, "win": "Lãi mẹ đẻ lãi con, tiền thu về đếm mỏi tay.", "lose": "Bị con nợ xiên chết để xù nợ.", "tien_w": 25000, "tien_l": -40000, "die_l": True}
        ]
    },
    {
        "q": "Công ty bạn có đợt cắt giảm nhân sự mạnh.",
        "choices": [
            {"text": "Xin nghỉ việc lấy trợ cấp", "rate": 70, "win": "Cầm cục tiền đi du lịch rồi kiếm việc khác.", "lose": "Tiêu lố tay, thất nghiệp 6 tháng rỗng túi.", "tien_w": 5000, "tien_l": -4000},
            {"text": "Đổ lỗi cho đồng nghiệp", "rate": 30, "win": "Sếp tin bạn, đuổi đồng nghiệp, bạn được thăng chức.", "lose": "Bị đồng nghiệp phát hiện, úp sọt hội đồng vỡ sọ tử vong.", "tien_w": 15000, "tien_l": -20000, "die_l": True},
            {"text": "Cày cuốc OT mù quáng", "rate": 55, "win": "Ghi điểm với cấp trên, giữ lại được ghế lương cao.", "lose": "Đột quỵ trên bàn làm việc vì kiệt sức.", "tien_w": 6000, "tien_l": -15000, "die_l": True},
            {"text": "Thả virus phá sập data công ty", "rate": 5, "win": "Hệ thống sập, bạn cứu nguy đòi tăng lương khủng.", "lose": "Bị điều tra ra IP, kiện bắt đền cả gia tài.", "tien_w": 50000, "tien_l": -80000}
        ]
    }
]

EVENTS_P3 = [ # TUỔI 35
    {
        "q": "Đứng trước sòng bài lớn nhất thành phố, bạn rảnh rỗi sinh nông nổi.",
        "choices": [
            {"text": "Vào chơi vui 100 đô", "rate": 60, "win": "Hên tay ăn được chuỗi thắng nhỏ, ra về đi ăn nhà hàng.", "lose": "Thua sạch 100 đô, đi bộ về nhà.", "tien_w": 2000, "tien_l": -500},
            {"text": "All-in tiền mặt vào Tài Xỉu", "rate": 20, "win": "Bát mở ra đúng cửa! Tiền nhân đôi nhét không vừa ví.", "lose": "Vay nóng giang hồ gỡ gạc, bị chém đứt lìa bay màu.", "tien_w": 30000, "tien_l": -50000, "die_l": True},
            {"text": "Cầm cố sổ đỏ chơi Poker", "rate": 10, "win": "Bạn úp sọt cả bàn bài, thu về số tiền bằng 5 căn nhà!", "lose": "Bay luôn sổ đỏ, lang thang gầm cầu.", "tien_w": 100000, "tien_l": -80000},
            {"text": "Đi làm bảo vệ Casino", "rate": 90, "win": "Làm công ăn lương, thỉnh thoảng được khách tip.", "lose": "Khách quỵt tiền làm loạn, bạn bị đánh oan.", "tien_w": 3000, "tien_l": -1000}
        ]
    },
    {
        "q": "Thị trường BĐS đóng băng, cò đất gạ bạn mua rẻ mảnh đất trên núi.",
        "choices": [
            {"text": "Bỏ qua mua chung cư ở", "rate": 75, "win": "Chung cư lên giá đều đều, gia đình sống thoải mái.", "lose": "Chủ đầu tư bỏ trốn, chờ mỏi mòn không có sổ hồng.", "tien_w": 8000, "tien_l": -6000},
            {"text": "Vay nóng mua mảnh đất hoang", "rate": 15, "win": "Chính phủ làm cao tốc qua núi! Đất nhân 20 lần giá!", "lose": "Bị lừa giấy tờ giả, tức tưởi đột quỵ chết tại chỗ.", "tien_w": 80000, "tien_l": -55000, "die_l": True},
            {"text": "Góp vốn cùng cò đất", "rate": 35, "win": "Cò bán lại lời chia đôi, làm ăn êm xuôi.", "lose": "Cò lừa bạn ôm giấy tờ giả chạy mất tăm.", "tien_w": 15000, "tien_l": -25000},
            {"text": "Để tiền gửi tiết kiệm", "rate": 95, "win": "Tiền đẻ ra tiền nhè nhẹ, an toàn tuyệt đối.", "lose": "Lạm phát tăng cao, tiền mất giá từ từ.", "tien_w": 2500, "tien_l": -1500}
        ]
    }
]

EVENTS_P4 = [ # TUỔI 50
    {
        "q": "Bước vào tuổi 50, bạn rơi vào khủng hoảng tuổi trung niên.",
        "choices": [
            {"text": "Cầm cố nhà mua siêu xe đua", "rate": 20, "win": "Giành giải đua xe lão tướng, tiền thưởng ngập mặt.", "lose": "Đạp nhầm chân ga đâm vách núi, nổ tung chết cháy.", "tien_w": 25000, "tien_l": -30000, "die_l": True},
            {"text": "Đi thám hiểm rừng Amazon", "rate": 15, "win": "Đào được kho báu của người Inca, thành huyền thoại.", "lose": "Bị rắn độc cắn giữa rừng sâu, bỏ mạng.", "tien_w": 50000, "tien_l": -15000, "die_l": True},
            {"text": "Cặp bồ nhí đáng tuổi con mình", "rate": 30, "win": "Tâm hồn hồi xuân phơi phới, vui vẻ hưởng thụ.", "lose": "Bị vợ/chồng đánh ghen giữa đường, nhục nhã mất sạch tài sản.", "tien_w": 5000, "tien_l": -45000},
            {"text": "Đi du lịch tĩnh tâm dưỡng lão", "rate": 85, "win": "Tâm hồn thư thái, huyết áp ổn định.", "lose": "Bị công ty tour lừa đảo, mang cục tức vào người.", "tien_w": 3000, "tien_l": -2000}
        ]
    },
    {
        "q": "Bạn phát hiện một khối u lạ trong cơ thể.",
        "choices": [
            {"text": "Không chữa, đi chu du thế giới", "rate": 15, "win": "Khối u tự tiêu tan, bạn ngộ ra chân lý nhân sinh.", "lose": "Gục chết lạnh lẽo trên đỉnh núi Alpes băng giá.", "tien_w": 20000, "tien_l": -5000, "die_l": True},
            {"text": "Sang Mỹ phẫu thuật", "rate": 60, "win": "Cắt bỏ thành công, khỏe mạnh đón tuổi già.", "lose": "Tai biến y khoa ngay trên bàn mổ, ra đi mãi mãi.", "tien_w": 10000, "tien_l": -60000, "die_l": True},
            {"text": "Mua thuốc thầy lang trên mạng", "rate": 10, "win": "Kỳ tích y học! Lá cây rừng chữa bách bệnh.", "lose": "Ngộ độc thạch tín cấp tính, tử vong tức tưởi.", "tien_w": 5000, "tien_l": -15000, "die_l": True},
            {"text": "Chữa trị theo phác đồ bệnh viện", "rate": 85, "win": "Căn bệnh bị đẩy lùi sau thời gian dài điều trị.", "lose": "Bệnh biến chứng mãn tính, tốn tiền thuốc dai dẳng.", "tien_w": 2000, "tien_l": -12000}
        ]
    }
]

EVENTS_P5 = [ # TUỔI 70
    {
        "q": "Chạm mốc 70 tuổi, bạn nghĩ về cái chết và di sản của mình.",
        "choices": [
            {"text": "Mua thuốc trường sinh bất lão", "rate": 5, "win": "Bạn hóa tiên! Sống thọ thêm 100 tuổi với cơ thể sung mãn.", "lose": "Uống nhầm thủy ngân, nội tạng nát vụn thăng thiên.", "tien_w": 150000, "tien_l": -20000, "die_l": True},
            {"text": "Chia đều tài sản cho con cháu", "rate": 70, "win": "Gia đình êm ấm, ai cũng vui vẻ phụng dưỡng bạn.", "lose": "Con cái đánh nhau mẻ đầu mẻ trán, bạn lên cơn đau tim gục chết.", "tien_w": 5000, "tien_l": -15000, "die_l": True},
            {"text": "Quyên góp toàn bộ làm từ thiện", "rate": 90, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền bốc hơi, bạn tức hộc máu chết.", "tien_w": 10000, "tien_l": -50000, "die_l": True},
            {"text": "Gom tiền đi quẩy Bar, nhảy đầm", "rate": 40, "win": "Trở thành dân chơi lão làng, idol của giới trẻ Tóp Tóp.", "lose": "Lắc hông quá đà gãy xương chậu, nằm liệt giường bón cháo.", "tien_w": 15000, "tien_l": -20000}
        ]
    }
]


# =====================================================================
# GIAO DIỆN GAME NHÂN SINH RPG TƯƠNG TÁC (ĐÃ XỬ LÝ LỖI VÀ ĐỘT TỬ)
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
        
        # May mắn buff % thành công (Mỗi điểm MM buff 2%)
        final_rate = min(95, base_rate + (self.stats["may_man"] * 2))
        
        roll = random.randint(1, 100)
        is_win = roll <= final_rate
        
        res = choice_data["win"] if is_win else choice_data["lose"]
        tien = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        # Kiểm tra đột tử (chết bất đắc kỳ tử)
        is_dead = False
        if is_win and choice_data.get("die_w", False): is_dead = True
        if not is_win and choice_data.get("die_l", False): is_dead = True

        self.tien_an += tien
        
        kq_thung = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ: **{final_rate}%** (Đổ ra: {roll})\n{kq_thung}: {res} ({tien} 💰)"
        
        # Lấy mốc tuổi hiện tại để in Log
        tuoi_hien_tai = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời khép lại sớm.**")
            self.phase = 99 # Chuyển ngay sang màn hình kết thúc
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}")
            # Chuyển Phase
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.purple())

        stats_text = f"May mắn ban đầu: **{self.stats['may_man']}/10** *(+ {self.stats['may_man']*2}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số tâm linh", value=stats_text, inline=False)

        # Chống trôi dòng Discord (Chỉ nối 4 dòng log cuối nếu quá dài)
        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase <= 5:
            tuoi_next = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
            embed.add_field(name=f"❓ Quyết định tuổi {tuoi_next}", value=self.ev['q'], inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text']}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text']}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text']}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text']}"
        else:
            # End Game (Chết hoặc Tới 70 tuổi thành công)
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
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại đống nợ khổng lồ, chủ nợ siết sạch tài sản.\n❌ **BÁO NHÀ!** Khoản nợ: **{total_reward} 💰**\n*(Hệ thống trừ thẳng vào ví, cày `k daily` mà trả nhé!)*", inline=False)
            elif total_reward >= 30000:
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa, làm đại gia trên đỉnh thế giới.\n👑 **ĐẠI PHÚ HÀO!** Di sản để lại: **+{total_reward} 💰**", inline=False)
            else:
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Cuộc đời êm ấm, thanh thản ra đi.\n💼 **DƯ DẢ!** Di sản để lại: **+{total_reward} 💰**", inline=False)

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
    bang_help.add_field(name="🌀 `k nhansinh`", value="Game Tương Tác RPG 5 Giai Đoạn (Phí: 100 💰). Coi chừng ĐỘT TỬ!", inline=False)
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
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{stats['may_man']}/10** *(+ {stats['may_man']*2}% Tỉ lệ)*", inline=False)
    
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
