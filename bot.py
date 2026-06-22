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
            DB_CACHE[user_id] = {"xp": 0, "level": 1, "money": 0, "title": "Dân Nghèo 🚶", "assets": [], "pets": {}}
    if "title" not in DB_CACHE[user_id]: DB_CACHE[user_id]["title"] = "Dân Nghèo 🚶"
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

async def check_gamble_conditions(ctx, amount_str):
    user_id = str(ctx.author.id)
    now = datetime.now()
    if user_id in gamble_cooldowns and (now - gamble_cooldowns[user_id]).total_seconds() < 4:
        await ctx.send(f"⏳ Cờ bạc từ từ thôi! Đợi {int(4 - (now - gamble_cooldowns[user_id]).total_seconds())}s nữa nhé!")
        return None, None
    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        if user_data.get("money", 0) < 0: return await ctx.send("Tài khoản đang **NỢ** mà dám vào casino à? Cày `k daily` trả nợ ngay!")
        else: return await ctx.send("Túi rỗng tếch mà đòi cá cược! Điểm danh đi.")
    tien_hien_tai = user_data["money"]
    try: 
        if amount_str.lower() == "all": bet = tien_hien_tai if tien_hien_tai <= 500000 else 500000
        else: bet = int(amount_str)
    except: 
        await ctx.send("Số cược không hợp lệ!")
        return None, None
    if bet <= 0 or bet > tien_hien_tai:
        await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai:,} 💰**.")
        return None, None
    if bet > 500000:
        await ctx.send("⚠️ Sòng bài quy định mỗi ván chỉ được cược tối đa **500,000 💰** thôi nhé.")
        return None, None
    return user_data, bet

# =====================================================================
# DỮ LIỆU GAME NHÂN SINH & RỪNG
# =====================================================================
EVENTS_P1 = [{"q": "Tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.", "choices": [{"text": "Đem nộp lên công an", "rate": 80, "win": "Chủ ví là tổng tài, hậu tạ bạn món tiền lớn.", "lose": "Bị giam ở phường viết bản tường trình 3 ngày.", "tien_w": 2500, "tien_l": -100}, {"text": "Bỏ túi xài luôn", "rate": 20, "win": "Không ai biết, bạn bao lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường gấp đôi và bị đuổi học.", "tien_w": 3000, "tien_l": -8000}, {"text": "Lấy tờ 500k rồi vứt lại ví", "rate": 40, "win": "Trót lọt, bạn nạp game lên VIP.", "lose": "Chủ nhân báo mất, bị tra hỏi phạt nặng.", "tien_w": 1000, "tien_l": -4000}, {"text": "Giả vờ không thấy", "rate": 95, "win": "Thong thả đi học tiếp, chẳng rước họa vào thân.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn.", "tien_w": 0, "tien_l": -500}]}, {"q": "Kỳ thi cuối cấp cận kề, bạn bè rủ cúp học đi net.", "choices": [{"text": "Ở nhà ôn bài kỹ", "rate": 85, "win": "Đỗ thủ khoa, được họ hàng thưởng nóng.", "lose": "Học tài thi phận, trượt vỏ chuối.", "tien_w": 2500, "tien_l": -500}, {"text": "Đi net cày rank", "rate": 10, "win": "Gặp idol ở quán net, được kéo lên Thách Đấu và cho tiền.", "lose": "Ngủ gục trên xe tông cột điện thăng thiên.", "tien_w": 3500, "tien_l": -10000, "die_l": True}, {"text": "Làm phao mang vào", "rate": 35, "win": "Mở phao mượt mà, điểm cao chót vót.", "lose": "Giám thị bắt quả tang, đình chỉ thi 0 điểm.", "tien_w": 2000, "tien_l": -5000}, {"text": "Ngủ cho khỏe", "rate": 50, "win": "Tinh thần sảng khoái, làm bài vừa đủ đậu.", "lose": "Ngủ nhiều lú não, làm sai phép tính cơ bản 1+1=3.", "tien_w": 800, "tien_l": -1000}]}]
EVENTS_P2 = [{"q": "Tích cóp được chút vốn, bạn muốn làm giàu nhanh.", "choices": [{"text": "Bắt đáy chứng khoán", "rate": 30, "win": "Cổ phiếu tím lịm! Tiền lãi mua được cả căn nhà.", "lose": "Bị chủ tịch úp bô, cổ phiếu rác hủy niêm yết.", "tien_w": 15000, "tien_l": -25000}, {"text": "Cắm sổ đỏ đánh xóc đĩa", "rate": 5, "win": "Ăn thông 10 ván! Bạn mua hẳn siêu xe Mẹc-xê-đét.", "lose": "Cháy túi, nhảy cầu kết thúc cuộc đời.", "tien_w": 80000, "tien_l": -50000, "die_l": True}, {"text": "Khởi nghiệp bún đậu mắm tôm", "rate": 60, "win": "Đông khách nườm nượp, mở 5 chi nhánh.", "lose": "Bị phốt mắm tôm có giòi, sập tiệm đền tiền.", "tien_w": 12000, "tien_l": -8000}, {"text": "Gửi tiết kiệm ngân hàng", "rate": 95, "win": "Cuộc sống bình yên, có lãi ra tiêu vặt.", "lose": "Lạm phát phi mã, tiền bốc hơi từ từ.", "tien_w": 2000, "tien_l": -1500}]}]
EVENTS_P3 = [{"q": "Bất Động Sản đang sốt, cò đất rủ bạn lướt sóng phân lô bán nền.", "choices": [{"text": "Cầm nhà ngân hàng quất liền", "rate": 20, "win": "Giá đất x5 trong một đêm! Bạn thành đại gia nghìn tỷ.", "lose": "Dính bẫy lừa đảo dự án ma, ra đê ở, treo cổ tự tử.", "tien_w": 60000, "tien_l": -70000, "die_l": True}, {"text": "Mua miếng đất nhỏ vùng ven", "rate": 55, "win": "Chính phủ mở đường qua, đất nhân 3 giá trị.", "lose": "Đất dính quy hoạch mỏ đá, bán không ai mua.", "tien_w": 15000, "tien_l": -10000}, {"text": "Mở lớp dạy làm giàu từ BĐS", "rate": 40, "win": "Lùa được đàn gà đông đảo, thu học phí ngập mồm.", "lose": "Bị học viên bóc phốt úp sọt, đánh nhập viện.", "tien_w": 12000, "tien_l": -15000}, {"text": "Không quan tâm, lo giữ gia đình", "rate": 95, "win": "Nhà cửa êm ấm, vợ/chồng con cái hạnh phúc.", "lose": "Kinh tế khó khăn, đôi lúc cãi nhau vì tiền điện nước.", "tien_w": 3000, "tien_l": -1500}]}]
EVENTS_P4 = [{"q": "Bước vào tuổi 50, bạn rơi vào khủng hoảng tuổi trung niên trầm trọng.", "choices": [{"text": "Bán nhà mua siêu xe Mẹc G63", "rate": 15, "win": "Chiến thắng giải đua không chuyên, nổi đình đám ăn quảng cáo.", "lose": "Đạp nhầm chân ga tông xe tải, thăng thiên tại chỗ.", "tien_w": 35000, "tien_l": -40000, "die_l": True}, {"text": "Sưu tầm Lan Đột Biến", "rate": 35, "win": "Bán chậu lan giá trên trời cho tỷ phú.", "lose": "Thị trường sập, ôm nhánh cỏ khô lỗ chổng vó.", "tien_w": 25000, "tien_l": -20000}, {"text": "Cặp Sugar Baby cho hồi xuân", "rate": 25, "win": "Nuôi êm thấm, tâm hồn trẻ lại phơi phới.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, mất sạch tài sản.", "tien_w": 2000, "tien_l": -50000}, {"text": "Tập Thiền, dọn về quê nuôi cá", "rate": 90, "win": "Tâm hồn thanh tịnh, khí huyết lưu thông.", "lose": "Về quê bị muỗi vằn chích sốt xuất huyết.", "tien_w": 5000, "tien_l": -3000}]}]
EVENTS_P5 = [{"q": "Chạm mốc 70 tuổi, một nhà sư bảo bạn sắp tới số.", "choices": [{"text": "Vung tiền mua Linh Đan Tu Tiên", "rate": 5, "win": "Kỳ tích! Bạn cải lão hoàn đồng thành thanh niên 20 tuổi!", "lose": "Uống nhầm thủy ngân, nội tạng nát vụn thăng thiên sớm.", "tien_w": 200000, "tien_l": -20000, "die_l": True}, {"text": "Lập di chúc chia đều tài sản", "rate": 75, "win": "Con cháu hòa thuận, tổ chức mừng thọ linh đình.", "lose": "Con cháu chê ít, đánh nhau mẻ đầu, bạn tức quá đột tử.", "tien_w": 5000, "tien_l": -15000, "die_l": True}, {"text": "Quyên góp 100% làm từ thiện", "rate": 90, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền bốc hơi, bạn trầm cảm đi luôn.", "tien_w": 15000, "tien_l": -50000, "die_l": True}, {"text": "Lên Las Vegas đánh Casino lần cuối", "rate": 20, "win": "Thắng Jackpot 50 triệu đô! Lên báo quốc tế rình rang.", "lose": "Thua sạch bong, lên cơn nhồi máu cơ tim gục tại bàn.", "tien_w": 100000, "tien_l": -40000, "die_l": True}]}]

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
    "terrible": [{"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!**\nBạn chọc tức chúa tể rừng xanh. Bị đấm bay rớt đồ!"}, {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại. Cháy trụi quần áo!"}, {"mult": -1.3, "msg": "🕳️ **SỤP HỐ CHÔNG!**\nRơi thẳng xuống hố chông thợ săn. Gãy sườn nôn tiền."}],
    "bad": [{"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nKhỉ nhảy ra giật túi tiền rồi đu cây mất."}, {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm nước hết hạn trong rừng."}, {"mult": -0.8, "msg": "💩 **BÃI MÌN!**\nDẫm trúng phân voi. Tốn tiền giặt đồ."}],
    "neutral": [{"mult": 0, "msg": "🍂 **LÁ KHÔ...**\nVạch ra chẳng có gì, chỉ có lá khô xào xạc."}, {"mult": 0, "msg": "📦 **RƯƠNG RỖNG!**\nMở rương cũ nhưng bên trong toàn mạng nhện."}],
    "good": [{"mult": 0.5, "msg": "💰 **TIỀN LẺ!**\nNhặt được chiếc ví nhỏ rơi rớt vài đồng."}, {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được linh chi đỏ. Tiệm thuốc trả hời lớn."}],
    "great": [{"mult": 1.5, "msg": "⚔️ **DIỆT THỔ PHỈ!**\nTóm gọn toán cướp tịch thu kho báu của chúng!"}, {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nĐào được rương vàng chóe mở ra toàn tiền!"}],
    "jackpot": [{"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC!**\nNhặt được vé số đem dò trúng ĐẶC BIỆT!"}, {"mult": 12.0, "msg": "👑 **VƯƠNG MIỆN VUA ARTHUR!**\nVớt được vương miện nạm kim cương. Tỷ phú rồi!!"}]
}

# --- CỬA HÀNG VÀ PET ---
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
    "common": {"rate": 60.0, "pool": ["Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈", "Lợn Đất 🐖", "Cá Chép 🐟", "Ếch Xanh 🐸", "Chuột Đồng 🐁", "Bò Sữa 🐄"]},
    "rare": {"rate": 25.0, "pool": ["Sói Tuyết 🐺", "Gấu Bự 🐻", "Cáo Chín Đuôi 🦊", "Đại Bàng 🦅", "Báo Gấm 🐆", "Hươu Sao 🦌"]},
    "epic": {"rate": 10.0, "pool": ["Sư Tử Lửa 🦁", "Khỉ Đột 🦍", "Bạch Hổ 🐅", "Cá Mập Megalodon 🦈", "Tê Giác Đất 🦏"]},
    "legendary": {"rate": 4.9, "pool": ["Rồng Đỏ Hủy Diệt 🐉", "Kỳ Lân Ánh Sáng 🦄", "Phượng Hoàng Lửa 🦚", "Thủy Quái Leviathan 🐙"]},
    "mythic": {"rate": 0.1, "pool": ["Thần Long Hoàng Kim 🐲", "Hắc Ám Cự Thú 🦇", "Mèo Thần Tài Vô Cực 😻"]}
}

def get_asset_price(asset_name):
    for v in SHOP_ITEMS.values():
        if v["name"] == asset_name: return int(v["price"] * 0.7)
    return 1000

def get_pet_sell_price(pet_name):
    for rarity, data in PET_RATES.items():
        if pet_name in data["pool"]:
            if rarity == "common": return 10000
            if rarity == "rare": return 30000
            if rarity == "epic": return 150000
            if rarity == "legendary": return 1000000
            if rarity == "mythic": return 10000000
    return 1000

# =====================================================================
# GIAO DIỆN GAME NHÂN SINH
# =====================================================================
class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180); self.author = author; self.stats = stats; self.phase = 1; self.tien_an = 0; self.logs = []
        self.ev = random.choice(EVENTS_P1)
        if self.stats["may_man"] >= 8: self.logs.append("👶 **Tuổi 0:** Sinh ra ngậm thìa vàng.")
        elif self.stats["may_man"] >= 4: self.logs.append("👶 **Tuổi 0:** Sinh ra trong gia đình ấm êm.")
        else: self.logs.append("👶 **Tuổi 0:** Bị vứt lăn lóc ngoài chợ từ nhỏ.")
        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text'][:70]}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text'][:70]}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text'][:70]}", style=discord.ButtonStyle.success, custom_id="btn_c")
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text'][:70]}", style=discord.ButtonStyle.danger, custom_id="btn_d")
        self.btn_a.callback = self.choice_a; self.btn_b.callback = self.choice_b; self.btn_c.callback = self.choice_c; self.btn_d.callback = self.choice_d
        self.add_item(self.btn_a); self.add_item(self.btn_b); self.add_item(self.btn_c); self.add_item(self.btn_d)
    async def on_timeout(self):
        if str(self.author.id) in dang_choi_nhansinh: dang_choi_nhansinh.remove(str(self.author.id))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author
    async def choice_a(self, interaction: discord.Interaction): await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): await self.process_choice(interaction, 3, "D")
    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        choice_data = self.ev["choices"][choice_idx]
        final_rate = min(95, choice_data["rate"] + (self.stats["may_man"] * 2)); roll = random.randint(1, 100); is_win = roll <= final_rate
        res = choice_data["win"] if is_win else choice_data["lose"]; tien = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        is_dead = True if (is_win and choice_data.get("die_w")) or (not is_win and choice_data.get("die_l")) else False
        self.tien_an += tien
        log_entry = f"🎲 Tỉ lệ: **{final_rate}%** (Ra {roll})\n{'✅' if is_win else '❌'}: {res} ({tien} 💰)"
        tuoi = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
        if is_dead: self.logs.append(f"👻 **Tuổi {tuoi}:** Chọn {letter}.\n{log_entry}\n💀 **ĐỘT TỬ!**"); self.phase = 99 
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi}:** Chọn {letter}.\n{log_entry}"); self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)
        await self.update_ui(interaction)
    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.teal())
        embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn: **{self.stats['may_man']}/10** *(+ {self.stats['may_man']*2}% Tỉ lệ)*", inline=False)
        story = "...\n\n" + "\n\n".join(self.logs[-4:]) if len(self.logs) > 4 else "\n\n".join(self.logs)
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)
        if self.phase <= 5:
            tuoi = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
            embed.add_field(name=f"❓ Quyết định tuổi {tuoi}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label, self.btn_b.label, self.btn_c.label, self.btn_d.label = f"A. {self.ev['choices'][0]['text'][:70]}", f"B. {self.ev['choices'][1]['text'][:70]}", f"C. {self.ev['choices'][2]['text'][:70]}", f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.clear_items(); user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)
            user_data = load_user(user_id); user_data["money"] += self.tien_an; save_user(user_id)
            if self.tien_an < 0: embed.color = discord.Color.red(); embed.add_field(name="🪦 Về với Cát Bụi", value=f"❌ **BÁO NHÀ!** Nợ: **{self.tien_an} 💰**", inline=False)
            elif self.tien_an >= 30000: embed.color = discord.Color.gold(); embed.add_field(name="🪦 Về với Cát Bụi", value=f"👑 **ĐẠI PHÚ HÀO!** Di sản: **+{self.tien_an} 💰**", inline=False)
            else: embed.color = discord.Color.blue(); embed.add_field(name="🪦 Về với Cát Bụi", value=f"💼 **DƯ DẢ!** Di sản: **+{self.tien_an} 💰**", inline=False)
        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

# =====================================================================
# GIAO DIỆN KHU RỪNG THÁM HIỂM (ĐÃ SỬA LỖI TÊN)
# =====================================================================
class BushButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, emoji): super().__init__(label=label, style=style, custom_id=custom_id, emoji=emoji)
    async def callback(self, interaction: discord.Interaction):
        view = self.view; weapon_id = view.weapon_val; weapon_info = WEAPON_ODDS[weapon_id]
        for child in view.children: child.disabled = True
        await interaction.response.edit_message(content=f"🌲 {interaction.user.mention} cầm **{weapon_info['name']}** tiến vào bụi rậm...", view=view); await asyncio.sleep(2)
        user_id = str(interaction.user.id); user_data = load_user(user_id); old_money = user_data.get("money", 0)
        category = random.choices(["terrible", "bad", "neutral", "good", "great", "jackpot"], weights=[weapon_info["terrible"], weapon_info["bad"], weapon_info["neutral"], weapon_info["good"], weapon_info["great"], weapon_info["jackpot"]], k=1)[0]
        scenario = random.choice(SCENARIOS[category])
        thuong_phat = int(weapon_info['price'] * scenario["mult"]) if "mult" in scenario else scenario.get("tien", 0)
        user_data["money"] += thuong_phat; new_session_profit = view.session_profit + (user_data["money"] - old_money); save_user(user_id)
        profit_text = f"LÃI +{new_session_profit} 💰" if new_session_profit > 0 else f"LỖ {new_session_profit} 💰" if new_session_profit < 0 else "HUỀ VỐN"
        embed_color = discord.Color.green() if thuong_phat > 0 else discord.Color.red() if thuong_phat < 0 else discord.Color.light_gray()
        res_embed = discord.Embed(title="MỞ LÙM CÂY...", description=f"**{scenario['msg']}**", color=embed_color)
        if thuong_phat > 0: res_embed.add_field(name="Thu Hoạch", value=f"📈 **+{thuong_phat} 💰**", inline=True)
        elif thuong_phat < 0: res_embed.add_field(name="Thua Lỗ", value=f"📉 **{thuong_phat} 💰**", inline=True)
        res_embed.add_field(name="Tổng Kết Phiên", value=f"📊 **{profit_text}**", inline=True)
        res_embed.set_footer(text=f"Số dư: {user_data['money']} 💰")
        await (await interaction.original_response()).edit(content=None, embed=res_embed, view=ResultView(interaction.user, new_session_profit))

class ResultView(discord.ui.View):
    def __init__(self, author, session_profit):
        super().__init__(timeout=120); self.author = author; self.session_profit = session_profit
        btn_tiep = discord.ui.Button(label="Tiếp tục", style=discord.ButtonStyle.primary, emoji="🔄"); btn_tiep.callback = self.continue_explore; self.add_item(btn_tiep)
        btn_dung = discord.ui.Button(label="Dừng lại", style=discord.ButtonStyle.danger, emoji="🛑"); btn_dung.callback = self.stop_explore; self.add_item(btn_dung)
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author
    async def continue_explore(self, interaction: discord.Interaction):
        shop_embed = discord.Embed(title="🛒 TRẠM TIẾP TẾ 🛒", description="Chọn vũ khí để đi tiếp.\n👇 **MỞ MENU MUA** 👇", color=discord.Color.orange())
        await interaction.response.edit_message(content=None, embed=shop_embed, view=KhungRungShopView(self.author, self.session_profit))
    async def stop_explore(self, interaction: discord.Interaction):
        for child in self.children: child.disabled = True
        end_embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        end_embed.add_field(name="🛑 KẾT THÚC CHUYẾN ĐI", value=f"Tổng kết phiên: **{'LÃI +' if self.session_profit > 0 else 'LỖ ' if self.session_profit < 0 else ''}{self.session_profit} 💰**", inline=False)
        await interaction.response.edit_message(embed=end_embed, view=self)

class BushView(discord.ui.View):
    def __init__(self, author, weapon_val, session_profit):
        super().__init__(timeout=60); self.author = author; self.weapon_val = weapon_val; self.session_profit = session_profit
        emojis = ["🌲", "🌳", "🌴", "🌵", "🎋"]
        for i in range(5): self.add_item(BushButton(label=f"Lùm Cây {i+1}", style=discord.ButtonStyle.success, custom_id=f"bush_{i}", emoji=emojis[i]))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class WeaponSelect(discord.ui.Select):
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = [discord.SelectOption(label=v['name'], description=f"Giá: {v['price']} 💰", emoji=v['name'][0], value=k) for k, v in WEAPON_ODDS.items()]
        super().__init__(placeholder="Nhấp vào để mua trang bị...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); price = WEAPON_ODDS[self.values[0]]["price"]
        if user_data.get("money", 0) < price: return await interaction.response.send_message(f"Nghèo quá! Không đủ **{price} 💰**.", ephemeral=True)
        user_data["money"] -= price; new_profit = self.session_profit - price; save_user(user_id)
        embed = discord.Embed(title="🌲 KHU RỪNG KỲ BÍ 🌲", description=f"Cầm **{WEAPON_ODDS[self.values[0]]['name']}**.\nPhía trước có 5 lùm cây. Chọn 1 lùm!", color=discord.Color.dark_green())
        await interaction.response.edit_message(content=None, embed=embed, view=BushView(interaction.user, self.values[0], new_profit))

class KhungRungShopView(discord.ui.View):
    def __init__(self, author, session_profit=0):
        super().__init__(timeout=60); self.author = author; self.add_item(WeaponSelect(session_profit))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author


# =====================================================================
# GIAO DIỆN TRẠM AFK & CỬA HÀNG ĐẠI GIA
# =====================================================================
class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Phần thưởng: ~450 💰", emoji="🌿", value="4"), discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Phần thưởng: ~1000 💰", emoji="🦇", value="8"), discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Phần thưởng: ~2000 💰", emoji="🏛️", value="12")]
        super().__init__(placeholder="Chọn khu vực cắm trại...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); hours = int(self.values[0])
        user_data["exp_end"] = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = random.randint(300, 600) if hours == 4 else random.randint(700, 1200) if hours == 8 else random.randint(1500, 2500)
        save_user(user_id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(title="⛺ LÊN ĐƯỜNG!", description=f"Bạn bắt đầu cắm trại **{hours} giờ**.\nDùng lệnh `k phai` khi hết thời gian để nhận.", color=discord.Color.green()), view=None)

class ExpView(discord.ui.View):
    def __init__(self, author): super().__init__(timeout=60); self.author = author; self.add_item(ExpSelect())
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        options = [discord.SelectOption(label=v['name'], description=f"Giá: {v['price']:,} 💰", value=k, emoji=v['emoji']) for k, v in SHOP_ITEMS.items() if v["type"] == category_type]
        super().__init__(placeholder="Nhấn vào đây để chọn mua...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); item_info = SHOP_ITEMS[self.values[0]]
        if user_data.get("money", 0) < item_info["price"]: return await interaction.response.send_message(f"⚠️ Cần **{item_info['price']:,} 💰** để mua.", ephemeral=True)
        user_data["money"] -= item_info["price"]
        if item_info["type"] == "title": user_data["title"] = item_info["name"]; msg = f"🎉 Đã trang bị danh hiệu **{item_info['name']}**."
        else:
            if item_info["name"] in user_data["assets"]: user_data["money"] += item_info["price"]; return await interaction.response.send_message(f"⚠️ Bạn đã có **{item_info['name']}** rồi!", ephemeral=True)
            user_data["assets"].append(item_info["name"]); msg = f"🎉 Vừa tậu siêu phẩm **{item_info['name']}**."
        save_user(user_id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(title="🛍️ GIAO DỊCH THÀNH CÔNG!", description=msg, color=discord.Color.green()).set_footer(text=f"Số dư: {user_data['money']:,} 💰"), view=None)

class ShopDetailView(discord.ui.View):
    def __init__(self, author, category_type): super().__init__(timeout=60); self.author = author; self.add_item(ShopItemSelect(category_type))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author): super().__init__(timeout=60); self.author = author
    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button): await interaction.response.edit_message(content="**🛍️ QUẦY BÁN DANH HIỆU:**", embed=None, view=ShopDetailView(self.author, "title"))
    @discord.ui.button(label="Showroom Xe Cộ", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button): await interaction.response.edit_message(content="**🛍️ SHOWROOM XE CỘ:**", embed=None, view=ShopDetailView(self.author, "vehicle"))
    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button): await interaction.response.edit_message(content="**🛍️ BẤT ĐỘNG SẢN:**", embed=None, view=ShopDetailView(self.author, "house"))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author


# =====================================================================
# GIAO DIỆN CHỢ ĐEN (BÁN ĐỒ)
# =====================================================================
class SellAssetSelect(discord.ui.Select):
    def __init__(self, assets):
        options = [discord.SelectOption(label=asset, description=f"Số lượng: {assets.count(asset)} | Thu mua: {get_asset_price(asset):,} 💰", value=asset) for asset in list(set(assets))[:25]]
        super().__init__(placeholder="Chọn tài sản để bán (Lỗ 30%)...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); asset_name = self.values[0]
        if asset_name not in user_data.get("assets", []): return await interaction.response.send_message("Lỗi: Không còn tài sản này!", ephemeral=True)
        sell_price = get_asset_price(asset_name)
        user_data["assets"].remove(asset_name); user_data["money"] += sell_price; save_user(user_id)
        await interaction.response.edit_message(content=f"✅ Bạn đã bán **{asset_name}** và vớt vát được **{sell_price:,} 💰**!", embed=None, view=None)

class SellPetSelect(discord.ui.Select):
    def __init__(self, pets):
        options = []; count = 0
        for pet, qty in pets.items():
            if count >= 25: break
            if qty > 0: options.append(discord.SelectOption(label=pet, description=f"Đang có: {qty} | Giá bán: {get_pet_sell_price(pet):,} 💰", value=pet)); count += 1
        super().__init__(placeholder="Chọn thú cưng để bán...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); pet_name = self.values[0]
        if user_data.get("pets", {}).get(pet_name, 0) <= 0: return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này!", ephemeral=True)
        sell_price = get_pet_sell_price(pet_name)
        user_data["pets"][pet_name] -= 1
        if user_data["pets"][pet_name] == 0: del user_data["pets"][pet_name]
        user_data["money"] += sell_price; save_user(user_id)
        await interaction.response.edit_message(content=f"✅ Đã bán 1 con **{pet_name}** thu về **{sell_price:,} 💰**!", embed=None, view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author): super().__init__(timeout=60); self.author = author
    @discord.ui.button(label="Bán Tài Sản (Nhà/Xe)", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: return await interaction.response.send_message("Làm gì có tài sản nào mà bán!", ephemeral=True)
        view = discord.ui.View(timeout=60); view.add_item(SellAssetSelect(assets))
        await interaction.response.edit_message(content="**🏷️ CHỢ ĐEN BẤT ĐỘNG SẢN & XE CỘ:**\n*(Lưu ý: Khấu hao mất 30% giá trị gốc)*", embed=None, view=view)
    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(v == 0 for v in pets.values()): return await interaction.response.send_message("Chưa có thú cưng nào để bán!", ephemeral=True)
        view = discord.ui.View(timeout=60); view.add_item(SellPetSelect(pets))
        await interaction.response.edit_message(content="**🏷️ TRẠM THU MUA THÚ CƯNG:**", embed=None, view=view)
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author


# =====================================================================
# TÍNH NĂNG ĐẤU TRƯỜNG: SOLO OẲN TÙ TÌ (ĐÃ SỬA LỖI INTERACTION)
# =====================================================================
class SoloOTTGame(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60); self.p1, self.p2, self.bet = p1, p2, bet
        self.msg = None; self.choices = {str(p1.id): None, str(p2.id): None}
    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "🪨")
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "📄")
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, interaction: discord.Interaction, button: discord.ui.Button): await self.handle_choice(interaction, "✂️")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = str(interaction.user.id)
        if user_id not in self.choices: return await interaction.response.send_message("Tránh ra chỗ khác!", ephemeral=True)
        if self.choices[user_id] is not None: return await interaction.response.send_message("Ông đã ra chiêu rồi!", ephemeral=True)
        
        self.choices[user_id] = choice
        await interaction.response.send_message(f"🤫 Bạn đã giấu tay chọn **{choice}**. Chờ đối thủ...", ephemeral=True)

        if self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]:
            for child in self.children: child.disabled = True
            c1, c2 = self.choices[str(self.p1.id)], self.choices[str(self.p2.id)]
            u1_data, u2_data = load_user(self.p1.id), load_user(self.p2.id)
            tong_thuong = self.bet * 2
            
            if c1 == c2:
                res = "🤝 **HÒA NHAU!** Tiền cược được trả lại."
                u1_data["money"] += self.bet; u2_data["money"] += self.bet
            elif (c1 == "🪨" and c2 == "✂️") or (c1 == "📄" and c2 == "🪨") or (c1 == "✂️" and c2 == "📄"):
                res = f"🎉 **{self.p1.name} THẮNG!** Húp **{tong_thuong:,} 💰**."
                u1_data["money"] += tong_thuong
            else:
                res = f"🎉 **{self.p2.name} THẮNG!** Húp **{tong_thuong:,} 💰**."
                u2_data["money"] += tong_thuong
                
            save_user(self.p1.id); save_user(self.p2.id)
            embed = discord.Embed(title="⚔️ KẾT QUẢ ĐẠI CHIẾN", color=discord.Color.gold())
            embed.add_field(name=self.p1.name, value=f"Ra {c1}", inline=True); embed.add_field(name="VS", value="⚡", inline=True); embed.add_field(name=self.p2.name, value=f"Ra {c2}", inline=True)
            embed.add_field(name="KẾT QUẢ", value=res, inline=False)
            await self.msg.edit(embed=embed, view=self)
            self.stop()
            
    async def on_timeout(self):
        if not (self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]):
            u1_data, u2_data = load_user(self.p1.id), load_user(self.p2.id)
            u1_data["money"] += self.bet; u2_data["money"] += self.bet
            save_user(self.p1.id); save_user(self.p2.id)
            try: await self.msg.edit(embed=discord.Embed(title="⏳ HẾT GIỜ", description="Trận đấu bị hủy, tiền cược đã hoàn trả!"), view=None)
            except: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60); self.p1, self.p2, self.bet = p1, p2, bet
    @discord.ui.button(label="Nhận Kèo Ngay!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.p2.id: return await interaction.response.send_message("Không phận sự miễn vào!", ephemeral=True)
        u1_data, u2_data = load_user(self.p1.id), load_user(self.p2.id)
        if u1_data.get("money",0) < self.bet or u2_data.get("money",0) < self.bet: return await interaction.response.send_message("⚠️ Thiếu lúa để chơi!", ephemeral=True)
        
        u1_data["money"] -= self.bet; u2_data["money"] -= self.bet
        save_user(self.p1.id); save_user(self.p2.id)
        
        game_view = SoloOTTGame(self.p1, self.p2, self.bet)
        embed = discord.Embed(title="⚔️ QUYẾT CHIẾN", description=f"{self.p1.mention} 🆚 {self.p2.mention}\nCược: **{self.bet:,} 💰**\n👇 **CHỌN ĐI (Bị giấu kín)**")
        # SỬA LỖI Ở ĐÂY: Dùng response.edit_message thay vì message.edit
        await interaction.response.edit_message(embed=embed, view=game_view)
        game_view.msg = interaction.message
        self.stop()


# =====================================================================
# CÁC LỆNH CHÍNH CỦA BOT
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH CỦA BOT", description="Tiền tố lệnh là `k` hoặc `K`.", color=discord.Color.blurple())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    embed.add_field(name="💳 KINH TẾ & TÀI SẢN", value="`k rank` • Xem thẻ căn cước\n`k daily` • Nhận lương\n`k lixi` • Bốc phong bao\n`k cuahang` • TTTM Bán nhà, bán xe\n`k sell` (`k ban`) • Bán đồ cho Cầm đồ\n`k tuido` • Xem tài sản\n`k top` • BXH Đại gia\n`k give @user <tiền>`", inline=False)
    embed.add_field(name="🎮 CÁ CƯỢC (MAX 500K)", value="`k coin <tiền/all>` • Xóc xu\n`k taixiu <t/x> <tiền>`\n`k duathu <heo/cho/ngua/chuot> <tiền>`\n`k baucua <con vật> <tiền>`\n`k nohu <tiền>` • Quay xèng\n`k soloott @user <tiền>` • PK Oẳn tù tì", inline=False)
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
    embed = discord.Embed(title="🏪 TRUNG TÂM THƯƠNG MẠI", description="Tiền nhiều để làm gì? Để mua danh hiệu khè nhau và tậu nhà lầu xe hơi chứ còn gì nữa!\n\n👇 **MỞ DANH SÁCH ĐỂ MUA SẮM** 👇", color=discord.Color.brand_green())
    if bot.user.avatar: embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command()
async def gacha(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); cost = 30000
    if user_data.get("money", 0) < cost: return await ctx.send(f"⚠️ Trứng Gacha giá **{cost:,} 💰**! Ví bạn chỉ có {user_data.get('money', 0):,} 💰.")
    user_data["money"] -= cost; save_user(user_id)

    msg = await ctx.send(f"🥚 {ctx.author.mention} ném **30,000 💰** để đập trứng...\n🔨 Đang gõ..."); await asyncio.sleep(1.5)
    await msg.edit(content=f"🥚 Vỏ trứng bắt đầu nứt rạn...\n⚡ Ánh sáng chói lóa phát ra từ bên trong!"); await asyncio.sleep(1.5)

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

    await msg.edit(content=ctx.author.mention, embed=discord.Embed(title=f"🎉 NỔ TRỨNG: {text}!", description=f"Tuyệt vời! Bạn vừa nở ra **{pet_name}**!\n*(Gõ `k tuido` để ngắm, gõ `k sell` để bán)*", color=color))

@bot.command()
async def tuido(ctx):
    user_data = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 Kho Báu của {ctx.author.name}", color=discord.Color.dark_theme())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    assets = user_data.get("assets", [])
    embed.add_field(name="🏠 Tài Sản", value="Trắng tay, Khố rách." if len(assets) == 0 else "\n".join([f"🔸 {a}" for a in assets]), inline=False)
    
    pets = user_data.get("pets", {})
    embed.add_field(name="🐾 Thú Cưng", value="Chưa có. Gõ `k gacha` ngay!" if len(pets) == 0 else "\n".join([f"{pet} (x{count})" for pet, count in pets.items()]), inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def rank(ctx):
    user_data = load_user(ctx.author.id)
    lv, xp, tien = user_data.get("level", 1), user_data.get("xp", 0), user_data.get("money", 0)
    embed = discord.Embed(title=f"💳 Thẻ Căn Cước của {ctx.author.name}", color=discord.Color.red() if tien < 0 else discord.Color.teal())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.add_field(name="Danh hiệu", value=f"**{user_data.get('title', 'Dân Nghèo 🚶')}**", inline=False)
    embed.add_field(name="Cấp độ", value=f"🌟 **LV {lv}**", inline=True)
    embed.add_field(name="Tài sản", value=f"**{tien:,} 💰**\n*(ĐANG NỢ)*" if tien < 0 else f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="Kinh nghiệm", value=f"`{make_progress_bar(xp, lv * 100)}`\n**{xp}/{lv * 100} XP**", inline=False)
    
    assets = user_data.get("assets", [])
    embed.set_footer(text=f"Đang sở hữu: {', '.join(assets[:3])}{'...' if len(assets)>3 else ''}" if assets else "Gia cảnh: Vô Gia Cư")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    server_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]: del CONFIG_CACHE[server_id]["allowed_channels"]
        return await ctx.send("✅ Đã gỡ bỏ giới hạn. Bot sẽ nhận lệnh ở **mọi kênh**.")

    mentions = ctx.message.channel_mentions
    if not mentions: return await ctx.send("⚠️ Vui lòng tag các kênh. VD: `k setup #kenh-1`")
    channel_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": channel_ids}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = channel_ids
    await ctx.send(f"✅ Đã cài đặt! Bot từ nay **CHỈ** nhận lệnh tại: {', '.join(c.mention for c in mentions)}")

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền phải > 0.")
    user_id = str(member.id); user_data = load_user(user_id); user_data["money"] += amount; save_user(user_id)
    await ctx.send(embed=discord.Embed(title="BƠM VỐN", description=f"👑 Admin buff cho {member.mention} **{amount:,} 💰**!\n💳 Dư: **{user_data['money']:,} 💰**", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền trừ phải > 0.")
    user_id = str(member.id); user_data = load_user(user_id); user_data["money"] -= amount; save_user(user_id)
    await ctx.send(embed=discord.Embed(title="THIÊN PHẠT", description=f"⚖️ Tước đoạt **{amount:,} 💰** của {member.mention}!\n💳 Dư: **{user_data['money']:,} 💰**", color=discord.Color.red()))

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_daily") and now - datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S") < timedelta(days=1):
        h, r = divmod(int((timedelta(days=1) - (now - datetime.strptime(user_data["last_daily"], "%Y-%m-%d %H:%M:%S"))).total_seconds()), 3600)
        return await ctx.send(f"⏳ Quay lại sau **{h} giờ {r//60} phút** nữa nhé.")

    user_data["money"] += 500; user_data["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    embed = discord.Embed(title="QUÀ ĐIỂM DANH 🎁", color=discord.Color.blue())
    if user_data["money"] < 0: embed.description = f"Nhận **500 💰**!\n⚠️ Hệ thống siết nợ! Nợ: **{user_data['money']} 💰**."; embed.color = discord.Color.red()
    else: embed.description = f"Nhận **500 💰**!\n💳 Số dư mới: **{user_data['money']:,} 💰**"
    await ctx.send(embed=embed)

@bot.command()
async def lixi(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); now = datetime.now()
    if user_data.get("last_lixi") and now - datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S") < timedelta(hours=12):
        h, r = divmod(int((timedelta(hours=12) - (now - datetime.strptime(user_data["last_lixi"], "%Y-%m-%d %H:%M:%S"))).total_seconds()), 3600)
        return await ctx.send(f"🧧 Đã bốc lì xì! Hẹn sau **{h} giờ {r//60} phút**.")

    tien_lixi = random.randint(1000, 8000) 
    user_data["money"] += tien_lixi; user_data["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(user_id)
    await ctx.send(embed=discord.Embed(title="🧧 TING TING! CÓ LÌ XÌ!", description=f"Chúc mừng nhận được **{tien_lixi:,} 💰**!\n💳 Dư: **{user_data['money']:,} 💰**", color=discord.Color.red()))

@bot.command()
async def top(ctx):
    danh_sach = sorted([(d["_id"], d.get("money", 0)) for d in list(users_col.find())], key=lambda x: x[1], reverse=True)
    desc = ""
    for i, (uid, tien) in enumerate(danh_sach[:10]):
        user = bot.get_user(int(uid))
        try: 
            if not user: user = await bot.fetch_user(int(uid))
        except: pass
        icon = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"**#{i+1}**"
        desc += f"{icon} **{user.name if user else f'Người chơi {uid[-4:]}'}** ━ {tien:,} 💰\n\n"
    await ctx.send(embed=discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA", description=desc, color=discord.Color.gold()))

@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🪙 {ctx.author.mention} tung **{bet:,} 💰**...\n🔄 Đồng xu xoay tít..."); await asyncio.sleep(2) 
    if random.choice(["thắng", "thua"]) == "thắng":
        user_data = load_user(user_id); user_data["money"] += bet * 2; save_user(user_id)
        await msg.edit(content=f"🪙 **MẶT NGỬA!**\n🎉 Húp trọn **{bet * 2:,} 💰**! (Dư: {user_data['money']:,})")
    else: await msg.edit(content=f"🪙 **MẶT SẤP!**\n💀 Mất **{bet:,} 💰**.")

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    if choice.lower() not in ["tai", "tài", "xiu", "xỉu"]: return await ctx.send("⚠️ Bạn phải chọn `tài` hoặc `xỉu`.")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🎲 {ctx.author.mention} cược **{bet:,} 💰** cửa **{choice.upper()}**.\nLạch cạch... 🫨"); await asyncio.sleep(2)
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6); total = d1 + d2 + d3
    res_str = "xỉu" if total <= 10 else "tài"; user_data = load_user(user_id)
    
    if choice.replace("à", "a").replace("ỉ", "i").lower() == res_str:
        if d1 == d2 == d3: user_data["money"] += bet * 5; r = f"🔥 **BÃO {d1}-{d2}-{d3}!!! ĐẠI THẮNG x5!**\n🎉 Húp **{bet * 5:,} 💰**!"
        else: user_data["money"] += bet * 2; r = f"✅ **THẮNG RỒI!** Húp **{bet * 2:,} 💰**!"
    else: r = f"💀 **THUA CẮNG RĂNG!** Mất **{bet:,} 💰**."

    save_user(user_id)
    await msg.edit(content=f"🎲 KẾT QUẢ: **{d1}-{d2}-{d3}** (Tổng: {total} - **{res_str.upper()}**)\n{r}\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    valid = {"bau":"🥒", "bầu":"🥒", "cua":"🦀", "tom":"🦐", "tôm":"🦐", "ca":"🐟", "cá":"🐟", "ga":"🐓", "gà":"🐓", "huou":"🦌", "hươu":"🦌"}
    if choice.lower() not in valid: return await ctx.send("⚠️ Sai tên! Gồm: `bau`, `cua`, `tom`, `ca`, `ga`, `huou`.")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    uc = valid[choice.lower()]; faces = ["🥒", "🦀", "🦐", "🐟", "🐓", "🦌"]; d1, d2, d3 = random.choice(faces), random.choice(faces), random.choice(faces)
    msg = await ctx.send(f"🎲 {ctx.author.mention} đặt **{bet:,} 💰** vào **{uc}**.\nNhà cái xóc đĩa... 🫨"); await asyncio.sleep(2)
    
    count = [d1, d2, d3].count(uc); user_data = load_user(user_id)
    if count > 0: user_data["money"] += bet + (bet * count); r = f"🎉 **TRÚNG {count} Ô!** Lấy về **{bet + (bet * count):,} 💰**."
    else: r = f"💀 **TRẬT LẤT!** Mất trắng **{bet:,} 💰**."
    save_user(user_id)
    await msg.edit(content=f"🎲 MỞ BÁT: **[ {d1} | {d2} | {d3} ]**\n{r}\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command(aliases=['slot', 'nohu', 'slots'])
async def mayxeng(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    s1, s2, s3 = random.choice(items), random.choice(items), random.choice(items)
    embed = discord.Embed(title="🎰 MÁY XÈNG CASINO 🎰", color=discord.Color.gold())
    msg = await ctx.send(embed=embed)
    
    for _ in range(3): embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đang quay..."; await msg.edit(embed=embed); await asyncio.sleep(1)
    for _ in range(2): embed.description = f"**[ {s1} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Chốt ô đầu..."; await msg.edit(embed=embed); await asyncio.sleep(1)
    for _ in range(2): embed.description = f"**[ {s1} | {s2} | {random.choice(items)} ]**\n\n🔄 Nín thở..."; await msg.edit(embed=embed); await asyncio.sleep(1)
        
    user_data = load_user(user_id)
    if s1 == s2 == s3:
        w = bet * 50 if s1 == "👑" else bet * 20 if s1 == "💎" else bet * 10
        r = f"🔥 **JACKPOT NỔ HŨ!** Trúng 3 ô {s1}\nHúp **{w:,} 💰**!"; user_data["money"] += w
    elif s1 == s2 or s2 == s3 or s1 == s3: w = bet * 2; r = f"🎉 **THẮNG NHỎ!** Trúng 2 ô.\nNhận **{w:,} 💰**."; user_data["money"] += w
    else: r = f"💀 **TOANG!** Mất **{bet:,} 💰**."
        
    save_user(user_id); embed.description = f"**[ {s1} | {s2} | {s3} ]**\n\n{r}\n💳 Số dư: **{user_data['money']:,} 💰**"; await msg.edit(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    n_gui, n_nhan = str(ctx.author.id), str(member.id); gui_data, nhan_data = load_user(n_gui), load_user(n_nhan)
    if amount <= 0 or gui_data.get("money", 0) < amount or n_gui == n_nhan: return await ctx.send("Lỗi: Không đủ tiền hoặc tự gửi.")
    gui_data["money"] -= amount; nhan_data["money"] += amount; save_user(n_gui); save_user(n_nhan)
    await ctx.send(embed=discord.Embed(title="💸 CHUYỂN KHOẢN", description=f"{ctx.author.mention} chuyển cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green()))

@bot.command()
async def phai(ctx):
    user_id = str(ctx.author.id); user_data = load_user(user_id); exp_end_str = user_data.get("exp_end")
    if exp_end_str:
        now = datetime.now()
        if now >= datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S"):
            reward = user_data.get("exp_reward", 500); user_data["money"] += reward; del user_data["exp_end"]; del user_data["exp_reward"]; save_user(user_id)
            return await ctx.send(embed=discord.Embed(title="🎉 TRỞ VỀ!", description=f"{ctx.author.mention} thu hoạch được **{reward:,} 💰**!", color=discord.Color.gold()))
        else:
            h, r = divmod(int((datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S") - now).total_seconds()), 3600)
            return await ctx.send(f"⏳ Cố đợi thêm **{h} giờ {r//60} phút** nữa nhé.")
    await ctx.send(embed=discord.Embed(title="⛺ TRẠM AFK", description="Gửi nhân vật đi treo máy.\n👇 **CHỌN KHU VỰC** 👇", color=discord.Color.dark_green()), view=ExpView(ctx.author))

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx): 
    # ĐÃ FIX: Dùng đúng KhungRungShopView
    await ctx.send(embed=discord.Embed(title="🛒 TRẠM TIẾP TẾ", description="👇 **MỞ MENU MUA VŨ KHÍ** 👇", color=discord.Color.orange()), view=KhungRungShopView(ctx.author, 0))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    user_id = str(ctx.author.id); phi = 100; now = datetime.now()
    if user_id in dang_choi_nhansinh: return await ctx.send(f"⏳ Bạn đang luân hồi dở!")
    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5: return await ctx.send(f"⏳ Đợi chút đi!")
    user_data = load_user(user_id)
    if user_data.get("money", 0) < phi: return await ctx.send(f"⚠️ Vé luân hồi **{phi} 💰**. Không đủ lúa!")
    user_data["money"] -= phi; nhansinh_cooldowns[user_id] = now; dang_choi_nhansinh.append(user_id); save_user(user_id)
    stats = {"may_man": random.randint(1, 10)}; view = NhanSinhGameView(ctx.author, stats)
    embed = discord.Embed(title="🌀 NHÂN SINH", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.purple())
    embed.add_field(name="🍀 Tâm linh", value=f"May mắn: **{stats['may_man']}/10**", inline=False); embed.add_field(name="📜 Hành trình", value="\n\n".join(view.logs), inline=False); embed.add_field(name="❓ Tuổi 15", value=f"**{view.ev['q']}**", inline=False)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['ott'])
async def oantuti(ctx, choice: str, amount: str):
    valid = {"bua": "🪨", "búa": "🪨", "bao": "📄", "giay": "📄", "giấy": "📄", "keo": "✂️", "kéo": "✂️"}
    if choice.lower() not in valid: return await ctx.send("⚠️ Ra `bua`, `bao` hoặc `keo`!")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()
    
    bot_c, user_c = random.choice(["🪨", "📄", "✂️"]), valid[choice.lower()]
    msg = await ctx.send(f"🤔 Bạn ra {user_c}. Bot suy nghĩ...\n💥 Oẳn tù tì... RA CÁI NÀY!"); await asyncio.sleep(1.5)

    user_data = load_user(user_id)
    if user_c == bot_c: user_data["money"] += bet; r = "🤝 **HÒA!**"
    elif (user_c == "🪨" and bot_c == "✂️") or (user_c == "📄" and bot_c == "🪨") or (user_c == "✂️" and bot_c == "📄"): user_data["money"] += bet * 2; r = f"🎉 **THẮNG!** Húp **{bet * 2:,} 💰**."
    else: r = f"💀 **THUA!** Mất **{bet:,} 💰**."
    save_user(user_id); await msg.edit(content=f"💥 Bot: **{bot_c}** | Bạn: **{user_c}**\n{r}\n💳 Số dư: **{user_data['money']:,} 💰**")

@bot.command()
async def soloott(ctx, member: discord.Member, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    if member.id == ctx.author.id or member.bot: return await ctx.send("⚠️ Lỗi: Không thể thách đấu chính mình hoặc Bot.")
    if load_user(member.id).get("money", 0) < bet: return await ctx.send(f"⚠️ {member.mention} không đủ lúa nhận kèo!")
    await ctx.send(embed=discord.Embed(title="🔥 THÁCH ĐẬU", description=f"{ctx.author.mention} cược **{bet:,} 💰** solo với {member.mention}!\nBấm **Nhận Kèo** trong 60s!", color=discord.Color.red()), view=SoloOTTAccept(ctx.author, member, bet))

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    if choice.lower() not in animals: return await ctx.send("⚠️ Chọn: `heo`, `cho`, `ngua`, `chuot`.")
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return
    user_id = str(ctx.author.id); user_data["money"] -= bet; save_user(user_id); gamble_cooldowns[user_id] = datetime.now()

    t_len = 20; p = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    def gt(): return f"🏇 **ĐUA THÚ!** ({ctx.author.name} cược {bet:,} 💰 vào {animals[choice.lower()]})\n🏁{'='*t_len}⛩️\n" + "".join([f"🏁{'~'*min(x, t_len)}{k}{' '*(t_len - min(x, t_len))}⛩️\n" for k, x in p.items()])
    msg = await ctx.send(gt()); w = None
    for _ in range(4):
        await asyncio.sleep(1.2)
        for k in p: p[k] += random.randint(2, 6); w = k if p[k] >= t_len and not w else w
        await msg.edit(content=gt())
        if w: break
    if not w: w = max(p, key=p.get); p[w] = t_len; await msg.edit(content=gt())
        
    user_data = load_user(user_id)
    if animals[choice.lower()] == w: user_data["money"] += bet * 3; r = f"\n🏆 **{w} VỀ NHẤT!** Ăn **x3 ({bet * 3:,} 💰)**!"
    else: r = f"\n💀 **{w} VỀ NHẤT!** Xịt. Mất **{bet:,} 💰**."
    save_user(user_id); await msg.edit(content=gt() + r)

@bot.event
async def on_message(message):
    if message.author.bot: return
    u_id = str(message.author.id); user_data = load_user(u_id)
    user_data["xp"] += random.randint(5, 15); max_xp = user_data["level"] * 100

    if user_data["xp"] >= max_xp:
        user_data["xp"] -= max_xp; user_data["level"] += 1; thuong = user_data["level"] * 150; user_data["money"] += thuong
        embed = discord.Embed(title="🎉 THĂNG CẤP!", description=f"{message.author.mention} đạt **Cấp {user_data['level']}**!\nThưởng: **{thuong:,} 💰**", color=discord.Color.gold())
        if message.author.avatar: embed.set_thumbnail(url=message.author.avatar.url)
        c_id = load_server_config(message.guild.id).get("channel_id"); k = bot.get_channel(c_id) if c_id else message.channel
        if k: await k.send(embed=embed)
    save_user(u_id); await bot.process_commands(message)

@bot.event
async def on_ready(): print(f'{bot.user} online!')

keep_alive() 
bot.run('MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.' + 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0')
