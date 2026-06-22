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
    
    # Khởi tạo mặc định
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
            await ctx.send(f"🚨 **BÁO ĐỘNG!** Đang bóc lịch trong tù do cướp nhà băng! Cải tạo thêm **{m} phút {s} giây** nữa mới được dùng lệnh.")
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
        if user_data.get("money", 0) < 0: return await ctx.send("Đang **NỢ** mà dám vào casino? Cày `k daily` trả nợ ngay!"), None
        else: return await ctx.send("Túi rỗng tếch mà đòi cá cược! Điểm danh đi."), None
    tien_hien_tai = user_data["money"]
    try: bet = tien_hien_tai if amount_str.lower() == "all" else int(amount_str)
    except: await ctx.send("Số cược không hợp lệ!"); return None, None
    if bet <= 0 or bet > tien_hien_tai: await ctx.send(f"Cược sai! Có: **{tien_hien_tai:,} 💰**."); return None, None
    if bet > 500000: await ctx.send("⚠️ Sòng bài quy định cược tối đa **500,000 💰**."); return None, None
    return user_data, bet

# =====================================================================
# DỮ LIỆU DATA (Đã nén gọn)
# =====================================================================
EVENTS_P1 = [{"q": "Nhặt được ví rơi.", "choices": [{"text": "Nộp công an", "rate": 80, "win": "Hậu tạ tiền.", "lose": "Bị giam.", "tien_w": 2500, "tien_l": -100}, {"text": "Bỏ túi", "rate": 20, "win": "Bao lớp.", "lose": "Bị đuổi học.", "tien_w": 3000, "tien_l": -8000}, {"text": "Lấy tiền", "rate": 40, "win": "Nạp VIP.", "lose": "Phạt nặng.", "tien_w": 1000, "tien_l": -4000}, {"text": "Lơ đi", "rate": 95, "win": "Bình yên.", "lose": "Đổ oan.", "tien_w": 0, "tien_l": -500}]}]
EVENTS_P2 = [{"q": "Cúp học đi net.", "choices": [{"text": "Ôn bài", "rate": 85, "win": "Thủ khoa.", "lose": "Trượt.", "tien_w": 2500, "tien_l": -500}, {"text": "Đi net", "rate": 10, "win": "Gặp Idol.", "lose": "Tai nạn.", "tien_w": 3500, "tien_l": -10000, "die_l": True}, {"text": "Làm phao", "rate": 35, "win": "Điểm cao.", "lose": "Đình chỉ.", "tien_w": 2000, "tien_l": -5000}, {"text": "Ngủ", "rate": 50, "win": "Qua môn.", "lose": "Lú não.", "tien_w": 800, "tien_l": -1000}]}]
EVENTS_P3 = [{"q": "Cò đất rủ mua.", "choices": [{"text": "Cầm nhà", "rate": 20, "win": "X5 tiền.", "lose": "Dự án ma.", "tien_w": 60000, "tien_l": -70000, "die_l": True}, {"text": "Mua vùng ven", "rate": 55, "win": "Lãi to.", "lose": "Quy hoạch.", "tien_w": 15000, "tien_l": -10000}, {"text": "Mở lớp dạy", "rate": 40, "win": "Lùa gà.", "lose": "Bị phốt.", "tien_w": 12000, "tien_l": -15000}, {"text": "Mặc kệ", "rate": 95, "win": "Gia đình vui.", "lose": "Kinh tế buồn.", "tien_w": 3000, "tien_l": -1500}]}]
EVENTS_P4 = [{"q": "Khủng hoảng tuổi 50.", "choices": [{"text": "Mua G63", "rate": 15, "win": "Nổi tiếng.", "lose": "Tai nạn.", "tien_w": 35000, "tien_l": -40000, "die_l": True}, {"text": "Chơi Lan", "rate": 35, "win": "Bán tỷ phú.", "lose": "Sập sàn.", "tien_w": 25000, "tien_l": -20000}, {"text": "Cặp Baby", "rate": 25, "win": "Hồi xuân.", "lose": "Đánh ghen.", "tien_w": 2000, "tien_l": -50000}, {"text": "Tập thiền", "rate": 90, "win": "Khỏe mạnh.", "lose": "Sốt.", "tien_w": 5000, "tien_l": -3000}]}]
EVENTS_P5 = [{"q": "Thầy bói phán tới số.", "choices": [{"text": "Mua linh đan", "rate": 5, "win": "Hoàn đồng!", "lose": "Uống thủy ngân.", "tien_w": 200000, "tien_l": -20000, "die_l": True}, {"text": "Lập di chúc", "rate": 75, "win": "Con hòa thuận.", "lose": "Đánh nhau.", "tien_w": 5000, "tien_l": -15000, "die_l": True}, {"text": "Từ thiện", "rate": 90, "win": "Đúc tượng.", "lose": "Bị lừa.", "tien_w": 15000, "tien_l": -50000, "die_l": True}, {"text": "Đánh bạc", "rate": 20, "win": "Jackpot!", "lose": "Đột quỵ.", "tien_w": 100000, "tien_l": -40000, "die_l": True}]}]

WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "🪵 Gậy", "terrible": 25, "bad": 40, "neutral": 15, "good": 15, "great": 5, "jackpot": 0},
    "sung_cao_su": {"price": 100, "name": "🪀 Súng CS", "terrible": 20, "bad": 35, "neutral": 20, "good": 20, "great": 5, "jackpot": 0},
    "kiem_sat": {"price": 200, "name": "🗡️ Kiếm Sắt", "terrible": 15, "bad": 25, "neutral": 20, "good": 25, "great": 13, "jackpot": 2},
    "kiem_hiep_si": {"price": 500, "name": "⚔️ Kiếm HS", "terrible": 10, "bad": 20, "neutral": 15, "good": 30, "great": 20, "jackpot": 5},
    "riu_chien": {"price": 1000, "name": "🪓 Rìu", "terrible": 10, "bad": 15, "neutral": 15, "good": 30, "great": 25, "jackpot": 5},
    "thanh_kiem": {"price": 1500, "name": "🔱 Thánh Kiếm", "terrible": 5, "bad": 10, "neutral": 10, "good": 35, "great": 30, "jackpot": 10},
    "sung_phong_luu": {"price": 3000, "name": "🚀 RPG", "terrible": 5, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 15},
    "gang_tay": {"price": 5000, "name": "🧤 Găng Infinity", "terrible": 2, "bad": 5, "neutral": 5, "good": 20, "great": 40, "jackpot": 28}
}

SCENARIOS = {
    "terrible": [{"mult": -2.0, "msg": "🐘 KING KONG ĐẤM! Bay màu!"}, {"mult": -1.5, "msg": "🐉 RỒNG PHUN LỬA! Cháy đồ!"}],
    "bad": [{"mult": -0.5, "msg": "🐒 KHỈ TRỘM! Mất tiền!"}, {"mult": -0.8, "msg": "💩 BÃI MÌN! Dẫm trúng phân voi."}],
    "neutral": [{"mult": 0, "msg": "🍂 LÁ KHÔ..."}, {"mult": 0, "msg": "📦 RƯƠNG RỖNG! Toàn mạng nhện."}],
    "good": [{"mult": 0.5, "msg": "💰 TIỀN LẺ! Nhặt được xu."}, {"mult": 0.8, "msg": "🍄 NẤM LINH CHI! Bán có tiền."}],
    "great": [{"mult": 1.5, "msg": "⚔️ DIỆT CƯỚP! Lấy kho báu!"}, {"mult": 2.5, "msg": "🏆 RƯƠNG VÀNG! Mở ra tiền!"}],
    "jackpot": [{"mult": 5.0, "msg": "🎫 VÉ SỐ ĐỘC ĐẮC!"}, {"mult": 12.0, "msg": "👑 VƯƠNG MIỆN VUA! Tỷ phú!!"}]
}

SHOP_ITEMS = {
    "t1": {"type": "title", "name": "Tiểu Thương 🏪", "price": 50000, "emoji": "🏷️"},
    "t2": {"type": "title", "name": "Phú Nông 🌾", "price": 200000, "emoji": "🏷️"},
    "t3": {"type": "title", "name": "Đại Gia 💸", "price": 1000000, "emoji": "🏷️"},
    "t4": {"type": "title", "name": "Tỷ Phú 💎", "price": 5000000, "emoji": "🏷️"},
    "t5": {"type": "title", "name": "Thần Tài 🧧", "price": 20000000, "emoji": "🏷️"},
    "v1": {"type": "vehicle", "name": "Xe Đạp 🚲", "price": 15000, "emoji": "🚲"},
    "v2": {"type": "vehicle", "name": "Honda SH 🏍️", "price": 300000, "emoji": "🏍️"},
    "v3": {"type": "vehicle", "name": "Mẹc G63 🚙", "price": 8000000, "emoji": "🚙"},
    "v4": {"type": "vehicle", "name": "Lamborghini 🏎️", "price": 25000000, "emoji": "🏎️"},
    "v5": {"type": "vehicle", "name": "Phi Cơ 🛩️", "price": 80000000, "emoji": "🛩️"},
    "h1": {"type": "house", "name": "Chung Cư 🏢", "price": 250000, "emoji": "🏢"},
    "h2": {"type": "house", "name": "Nhà Phố 🏘️", "price": 5000000, "emoji": "🏘️"},
    "h3": {"type": "house", "name": "Biệt Thự 🏡", "price": 20000000, "emoji": "🏡"},
    "h4": {"type": "house", "name": "Đảo Tư Nhân 🏝️", "price": 500000000, "emoji": "🏝️"}
}

PET_RATES = {
    "common": {"rate": 80.0, "pool": ["Gà Con 🐥", "Chó 🐕", "Mèo 🐈", "Heo 🐖"]},
    "rare": {"rate": 15.0, "pool": ["Sói 🐺", "Gấu 🐻", "Đại Bàng 🦅"]},
    "epic": {"rate": 4.0, "pool": ["Sư Tử 🦁", "Khỉ Đột 🦍", "Hổ 🐅"]},
    "legendary": {"rate": 0.9, "pool": ["Rồng Đỏ 🐉", "Kỳ Lân 🦄", "Phượng 🦚"]},
    "mythic": {"rate": 0.1, "pool": ["Thần Long 🐲", "Hắc Cẩu 🐺", "Mèo VIP 😻"]}
}

STOCKS = {"VIN": "Tập Đoàn VIN", "FLC": "Hàng Không FLC", "VNZ": "Công Nghệ VNZ", "DOGE": "Doge Coin"}

def get_asset_price(asset_name):
    for v in SHOP_ITEMS.values():
        if v["name"] == asset_name: return int(v["price"] * 0.7)
    return 1000

def get_pet_sell_price(pet_name):
    for r, d in PET_RATES.items():
        if pet_name in d["pool"]:
            return 5000 if r=="common" else 15000 if r=="rare" else 100000 if r=="epic" else 500000 if r=="legendary" else 5000000
    return 1000

def get_stock_price(stock_code, hour_offset=0):
    t = datetime.now() + timedelta(hours=hour_offset)
    seed = int(t.strftime("%Y%m%d%H")) + sum(ord(c) for c in stock_code)
    return random.Random(seed).randint(10, 300) * 1000

# =====================================================================
# CÁC CLASS UI GIAO DIỆN (NÚT BẤM)
# =====================================================================
class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180); self.author = author; self.stats = stats; self.phase = 1; self.tien_an = 0; self.logs = []
        self.ev = random.choice(EVENTS_P1)
        self.logs.append("👶 **Tuổi 0:** Sinh ra bình an.")
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
        embed = discord.Embed(title="🌀 NHÂN SINH", description=f"Ký chủ: {self.author.mention}", color=discord.Color.teal())
        embed.add_field(name="📜 Hành trình", value="...\n\n" + "\n\n".join(self.logs[-4:]) if len(self.logs)>4 else "\n\n".join(self.logs), inline=False)
        if self.phase <= 5:
            tuoi = 15 if self.phase==1 else 25 if self.phase==2 else 35 if self.phase==3 else 50 if self.phase==4 else 70
            embed.add_field(name=f"❓ Quyết định tuổi {tuoi}", value=f"**{self.ev['q']}**", inline=False)
            self.btn_a.label, self.btn_b.label, self.btn_c.label, self.btn_d.label = f"A. {self.ev['choices'][0]['text'][:70]}", f"B. {self.ev['choices'][1]['text'][:70]}", f"C. {self.ev['choices'][2]['text'][:70]}", f"D. {self.ev['choices'][3]['text'][:70]}"
        else:
            self.clear_items(); user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)
            user_data = load_user(user_id); user_data["money"] += self.tien_an; save_user(user_id)
            embed.color = discord.Color.gold(); embed.add_field(name="🪦 Về Cát Bụi", value=f"Di sản: **{self.tien_an:,} 💰**", inline=False)
        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

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
        profit_text = f"LÃI +{new_session_profit:,} 💰" if new_session_profit > 0 else f"LỖ {new_session_profit:,} 💰" if new_session_profit < 0 else "HUỀ VỐN"
        res_embed = discord.Embed(title="MỞ LÙM CÂY...", description=f"**{scenario['msg']}**", color=discord.Color.green() if thuong_phat > 0 else discord.Color.red())
        res_embed.add_field(name="Thu/Lỗ", value=f"**{thuong_phat:,} 💰**", inline=True); res_embed.add_field(name="Tổng Phiên", value=f"**{profit_text}**", inline=True)
        await (await interaction.original_response()).edit(content=None, embed=res_embed, view=ResultView(interaction.user, new_session_profit))

class ResultView(discord.ui.View):
    def __init__(self, author, session_profit):
        super().__init__(timeout=120); self.author = author; self.session_profit = session_profit
        btn_tiep = discord.ui.Button(label="Tiếp tục", style=discord.ButtonStyle.primary, emoji="🔄"); btn_tiep.callback = self.continue_explore; self.add_item(btn_tiep)
        btn_dung = discord.ui.Button(label="Dừng lại", style=discord.ButtonStyle.danger, emoji="🛑"); btn_dung.callback = self.stop_explore; self.add_item(btn_dung)
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author
    async def continue_explore(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=None, embed=discord.Embed(title="🛒 TRẠM TIẾP TẾ", description="Chọn vũ khí.", color=discord.Color.orange()), view=KhungRungShopView(self.author, self.session_profit))
    async def stop_explore(self, interaction: discord.Interaction):
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🛑 KẾT THÚC CHUYẾN ĐI", description=f"Tổng kết phiên: **{self.session_profit:,} 💰**"), view=self)

class BushView(discord.ui.View):
    def __init__(self, author, weapon_val, session_profit):
        super().__init__(timeout=60); self.author = author; self.weapon_val = weapon_val; self.session_profit = session_profit
        for i in range(5): self.add_item(BushButton(label=f"Lùm Cây {i+1}", style=discord.ButtonStyle.success, custom_id=f"bush_{i}", emoji="🌲"))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class WeaponSelect(discord.ui.Select):
    def __init__(self, session_profit):
        self.session_profit = session_profit
        options = [discord.SelectOption(label=v['name'], description=f"Giá: {v['price']} 💰", value=k) for k, v in WEAPON_ODDS.items()]
        super().__init__(placeholder="Nhấp vào để mua trang bị...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); price = WEAPON_ODDS[self.values[0]]["price"]
        if user_data.get("money", 0) < price: return await interaction.response.send_message(f"Không đủ **{price} 💰**.", ephemeral=True)
        user_data["money"] -= price; save_user(user_id)
        embed = discord.Embed(title="🌲 KHU RỪNG KỲ BÍ", description=f"Cầm **{WEAPON_ODDS[self.values[0]]['name']}**. Chọn 1 lùm!", color=discord.Color.dark_green())
        await interaction.response.edit_message(content=None, embed=embed, view=BushView(interaction.user, self.values[0], self.session_profit - price))

class KhungRungShopView(discord.ui.View):
    def __init__(self, author, session_profit=0): super().__init__(timeout=60); self.author = author; self.add_item(WeaponSelect(session_profit))
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="4 Giờ", value="4"), discord.SelectOption(label="8 Giờ", value="8"), discord.SelectOption(label="12 Giờ", value="12")]
        super().__init__(placeholder="Chọn khu vực cắm trại...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id); user_data = load_user(user_id); h = int(self.values[0])
        user_data["exp_end"] = (datetime.now() + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = random.randint(300,600) if h==4 else random.randint(700,1200) if h==8 else random.randint(1500,2500)
        save_user(user_id)
        await interaction.response.edit_message(content=f"⛺ Bắt đầu cắm trại **{h} giờ**. Xong gõ `k phai`.", embed=None, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author): super().__init__(timeout=60); self.author = author; self.add_item(ExpSelect())
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class ShopItemSelect(discord.ui.Select):
    def __init__(self, c_type):
        options = [discord.SelectOption(label=v['name'], description=f"Giá: {v['price']:,} 💰", value=k) for k, v in SHOP_ITEMS.items() if v["type"] == c_type]
        super().__init__(placeholder="Chọn mua...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        u_id = str(interaction.user.id); u_data = load_user(u_id); item = SHOP_ITEMS[self.values[0]]
        if u_data.get("money", 0) < item["price"]: return await interaction.response.send_message(f"⚠️ Cần {item['price']:,} 💰.", ephemeral=True)
        u_data["money"] -= item["price"]
        if item["type"] == "title": u_data["title"] = item["name"]; msg = f"Trang bị danh hiệu **{item['name']}**."
        else:
            if item["name"] in u_data["assets"]: u_data["money"] += item["price"]; return await interaction.response.send_message("Đã sở hữu!", ephemeral=True)
            u_data["assets"].append(item["name"]); msg = f"Đã mua **{item['name']}**."
        save_user(u_id); await interaction.response.edit_message(content=f"✅ {msg} (Dư: {u_data['money']:,} 💰)", embed=None, view=None)

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author): super().__init__(timeout=60); self.author = author
    @discord.ui.button(label="Danh Hiệu", style=discord.ButtonStyle.primary)
    async def btn_t(self, inter: discord.Interaction, btn: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("title")); await inter.response.edit_message(content="**🛍️ DANH HIỆU:**", embed=None, view=view)
    @discord.ui.button(label="Xe Cộ", style=discord.ButtonStyle.success)
    async def btn_v(self, inter: discord.Interaction, btn: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("vehicle")); await inter.response.edit_message(content="**🛍️ XE CỘ:**", embed=None, view=view)
    @discord.ui.button(label="BĐS", style=discord.ButtonStyle.danger)
    async def btn_h(self, inter: discord.Interaction, btn: discord.ui.Button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("house")); await inter.response.edit_message(content="**🛍️ BĐS:**", embed=None, view=view)
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class SellAssetSelect(discord.ui.Select):
    def __init__(self, assets):
        options = [discord.SelectOption(label=a, description=f"Thu mua: {get_asset_price(a):,} 💰", value=a) for a in list(set(assets))[:25]]
        super().__init__(placeholder="Chọn tài sản để bán...", min_values=1, max_values=1, options=options)
    async def callback(self, inter: discord.Interaction):
        u_id = str(inter.user.id); u_data = load_user(u_id); a = self.values[0]
        if a not in u_data.get("assets", []): return await inter.response.send_message("Lỗi!", ephemeral=True)
        sp = get_asset_price(a); u_data["assets"].remove(a); u_data["money"] += sp; save_user(u_id)
        await inter.response.edit_message(content=f"✅ Đã bán **{a}** vớt vát được **{sp:,} 💰**!", view=None)

class SellPetSelect(discord.ui.Select):
    def __init__(self, pets):
        options = [discord.SelectOption(label=p, description=f"Giá: {get_pet_sell_price(p):,} 💰", value=p) for p, c in list(pets.items())[:25] if c > 0]
        super().__init__(placeholder="Chọn pet để bán...", min_values=1, max_values=1, options=options)
    async def callback(self, inter: discord.Interaction):
        u_id = str(inter.user.id); u_data = load_user(u_id); p = self.values[0]
        if u_data.get("pets", {}).get(p, 0) <= 0: return await inter.response.send_message("Lỗi!", ephemeral=True)
        sp = get_pet_sell_price(p); u_data["pets"][p] -= 1
        if u_data["pets"][p] == 0: del u_data["pets"][p]
        u_data["money"] += sp; save_user(u_id)
        await inter.response.edit_message(content=f"✅ Đã bán **{p}** lấy **{sp:,} 💰**!", view=None)

class SellCategoryMenu(discord.ui.View):
    def __init__(self, author): super().__init__(timeout=60); self.author = author
    @discord.ui.button(label="Bán Tài Sản", style=discord.ButtonStyle.primary)
    async def btn_a(self, inter: discord.Interaction, btn: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: return await inter.response.send_message("Không có tài sản!", ephemeral=True)
        view = discord.ui.View(timeout=60); view.add_item(SellAssetSelect(assets))
        await inter.response.edit_message(content="**🏷️ CHỢ ĐEN (Lỗ 30%):**", embed=None, view=view)
    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success)
    async def btn_p(self, inter: discord.Interaction, btn: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets: return await inter.response.send_message("Không có thú cưng!", ephemeral=True)
        view = discord.ui.View(timeout=60); view.add_item(SellPetSelect(pets))
        await inter.response.edit_message(content="**🏷️ BÁN THÚ CƯNG:**", embed=None, view=view)
    async def interaction_check(self, interaction: discord.Interaction): return interaction.user == self.author

class SoloOTTGame(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60); self.p1, self.p2, self.bet = p1, p2, bet
        self.msg = None; self.choices = {str(p1.id): None, str(p2.id): None}
    @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.secondary)
    async def btn_bua(self, inter: discord.Interaction, btn: discord.ui.Button): await self.handle_choice(inter, "🪨")
    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary)
    async def btn_bao(self, inter: discord.Interaction, btn: discord.ui.Button): await self.handle_choice(inter, "📄")
    @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.secondary)
    async def btn_keo(self, inter: discord.Interaction, btn: discord.ui.Button): await self.handle_choice(inter, "✂️")

    async def handle_choice(self, inter: discord.Interaction, choice: str):
        uid = str(inter.user.id)
        if uid not in self.choices: return await inter.response.send_message("Ra chỗ khác!", ephemeral=True)
        if self.choices[uid] is not None: return await inter.response.send_message("Đã chọn rồi!", ephemeral=True)
        self.choices[uid] = choice; await inter.response.send_message(f"🤫 Bạn chọn **{choice}**.", ephemeral=True)

        if self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]:
            for c in self.children: c.disabled = True
            c1, c2 = self.choices[str(self.p1.id)], self.choices[str(self.p2.id)]
            u1, u2 = load_user(self.p1.id), load_user(self.p2.id); tt = self.bet * 2
            
            if c1 == c2: r = "🤝 **HÒA!**"; u1["money"] += self.bet; u2["money"] += self.bet
            elif (c1=="🪨" and c2=="✂️") or (c1=="📄" and c2=="🪨") or (c1=="✂️" and c2=="📄"): r = f"🎉 **{self.p1.name} THẮNG!** Húp {tt:,} 💰"; u1["money"] += tt
            else: r = f"🎉 **{self.p2.name} THẮNG!** Húp {tt:,} 💰"; u2["money"] += tt
                
            save_user(self.p1.id); save_user(self.p2.id)
            await self.msg.edit(embed=discord.Embed(title="⚔️ KẾT QUẢ", description=f"{self.p1.name} ({c1}) VS ({c2}) {self.p2.name}\n\n{r}", color=discord.Color.gold()), view=self); self.stop()
            
    async def on_timeout(self):
        if not (self.choices[str(self.p1.id)] and self.choices[str(self.p2.id)]):
            u1, u2 = load_user(self.p1.id), load_user(self.p2.id)
            u1["money"] += self.bet; u2["money"] += self.bet; save_user(self.p1.id); save_user(self.p2.id)
            try: await self.msg.edit(content="⏳ **Hết giờ, hòa tiền!**", view=None)
            except: pass

class SoloOTTAccept(discord.ui.View):
    def __init__(self, p1, p2, bet):
        super().__init__(timeout=60); self.p1, self.p2, self.bet = p1, p2, bet
    @discord.ui.button(label="Nhận Kèo!", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def accept(self, inter: discord.Interaction, btn: discord.ui.Button):
        if inter.user.id != self.p2.id: return await inter.response.send_message("Không phận sự miễn vào!", ephemeral=True)
        u1, u2 = load_user(self.p1.id), load_user(self.p2.id)
        if u1.get("money",0) < self.bet or u2.get("money",0) < self.bet: return await inter.response.send_message("⚠️ Thiếu lúa!", ephemeral=True)
        u1["money"] -= self.bet; u2["money"] -= self.bet; save_user(self.p1.id); save_user(self.p2.id)
        game_view = SoloOTTGame(self.p1, self.p2, self.bet)
        await inter.response.edit_message(content=f"⚔️ {self.p1.mention} 🆚 {self.p2.mention} ({self.bet:,} 💰)\n👇 Chọn đi!", embed=None, view=game_view)
        game_view.msg = inter.message; self.stop()

class CompanyInviteView(discord.ui.View):
    def __init__(self, comp_id, comp_name, target_user):
        super().__init__(timeout=60); self.comp_id = comp_id; self.comp_name = comp_name; self.target_user = target_user
    @discord.ui.button(label="Gia nhập", style=discord.ButtonStyle.success)
    async def acc(self, inter: discord.Interaction, btn: discord.ui.Button):
        if inter.user.id != self.target_user.id: return await inter.response.send_message("Lỗi!", ephemeral=True)
        tid = str(self.target_user.id); tdata = load_user(tid)
        if tdata.get("company"): return await inter.response.send_message("Đã có công ty!", ephemeral=True)
        comp = load_company(self.comp_id)
        if not comp: return await inter.response.send_message("Công ty phá sản rồi!", ephemeral=True)
        comp["members"][tid] = "nhanvien"; tdata["company"] = self.comp_id; save_company(self.comp_id); save_user(tid)
        await inter.response.edit_message(content=f"🎉 {self.target_user.mention} đã vào **{self.comp_name}**!", view=None)


# =====================================================================
# CHỨNG KHOÁN & CÔNG TY
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    embed = discord.Embed(title="📈 SÀN CHỨNG KHOÁN (Cập nhật mỗi giờ)", description="`k ck buy <MÃ> <SL>`\n`k ck sell <MÃ> <SL>`", color=discord.Color.brand_green())
    for code, name in STOCKS.items():
        p_now = get_stock_price(code, 0); p_old = get_stock_price(code, -1)
        embed.add_field(name=f"{code} - {name}", value=f"Giá: **{p_now:,} 💰**\n*(Biến động: {'📈' if p_now > p_old else '📉'} {abs(p_now - p_old):,})*", inline=False)
    inv = "\n".join([f"{k}: {v} CP" for k, v in load_user(ctx.author.id).get("stocks", {}).items() if v > 0])
    embed.add_field(name="🎒 Cổ phiếu của bạn", value=inv if inv else "Trống không.", inline=False)
    await ctx.send(embed=embed)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    if code not in STOCKS or qty <= 0: return await ctx.send("Lỗi mã hoặc số lượng!")
    cost = get_stock_price(code, 0) * qty; uid = str(ctx.author.id); udata = load_user(uid)
    if udata.get("money", 0) < cost: return await ctx.send(f"⚠️ Cần **{cost:,} 💰**.")
    udata["money"] -= cost; udata["stocks"][code] = udata.get("stocks", {}).get(code, 0) + qty; save_user(uid)
    await ctx.send(f"✅ Mua **{qty} {code}** mất {cost:,} 💰!")

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper(); uid = str(ctx.author.id); udata = load_user(uid); my_q = udata.get("stocks", {}).get(code, 0)
    if code not in STOCKS or qty <= 0 or my_q < qty: return await ctx.send("Lỗi: Không đủ cổ phiếu!")
    gain = get_stock_price(code, 0) * qty; udata["stocks"][code] -= qty; udata["money"] += gain; save_user(uid)
    await ctx.send(f"✅ Bán **{qty} {code}** thu về {gain:,} 💰!")

@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    uid = str(ctx.author.id); udata = load_user(uid); cid = udata.get("company")
    if not cid: return await ctx.send(embed=discord.Embed(description="🏢 Thất nghiệp. `k cty tao <tên>` (500k 💰)", color=discord.Color.red()))
    c = load_company(cid)
    if not c: udata["company"] = None; save_user(uid); return await ctx.send("Công ty đã phá sản!")
    mr = c["members"].get(uid, "nhanvien"); rn = c["roles"].get(mr, mr)
    embed = discord.Embed(title=f"🏢 CTY: {c['name']}", color=discord.Color.gold())
    embed.add_field(name="Quỹ", value=f"{c['treasury']:,} 💰"); embed.add_field(name="NS", value=f"{len(c['members'])} người")
    embed.add_field(name="Chức vụ", value=f"{rn}", inline=False)
    cmds = "`k cty gop <tiền>`\n`k cty thulai` (nhận lãi ngày)\n`k cty roi`"
    if mr in ["boss", "quanly"]: cmds += "\n`k cty tuyen @user`\n`k cty duoi @user`"
    if mr == "boss": cmds += "\n`k cty luong <tiền>`\n`k cty chucvu @user <quanly/nhanvien>`"
    embed.add_field(name="Lệnh", value=cmds, inline=False); await ctx.send(embed=embed)

@cty.command()
async def tao(ctx, *, name: str):
    uid = str(ctx.author.id); udata = load_user(uid)
    if udata.get("company"): return await ctx.send("Thoát cty cũ trước!")
    if udata.get("money", 0) < 500000: return await ctx.send("⚠️ Cần **500,000 💰**.")
    udata["money"] -= 500000; udata["company"] = uid
    COMPANY_CACHE[uid] = {"_id": uid, "name": name, "treasury": 0, "members": {uid: "boss"}, "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, "last_interest": "2000-01-01 00:00:00"}
    save_company(uid); save_user(uid); await ctx.send(f"🏢 Sếp {ctx.author.mention} lập cty **{name}**!")

@cty.command()
async def tuyen(ctx, member: discord.Member):
    uid = str(ctx.author.id); cid = load_user(uid).get("company"); c = load_company(cid) if cid else None
    if not c or c["members"].get(uid) not in ["boss", "quanly"]: return await ctx.send("Lỗi quyền!")
    if load_user(member.id).get("company"): return await ctx.send("Người này đã có việc.")
    await ctx.send(f"🏢 {member.mention}, mời vào cty **{c['name']}**!", view=CompanyInviteView(cid, c["name"], member))

@cty.command()
async def duoi(ctx, member: discord.Member):
    uid = str(ctx.author.id); cid = load_user(uid).get("company"); c = load_company(cid) if cid else None
    if not c or c["members"].get(uid) not in ["boss", "quanly"]: return
    tid = str(member.id)
    if tid not in c["members"] or c["members"][tid] == "boss": return await ctx.send("Lỗi!")
    del c["members"][tid]; td = load_user(tid); td["company"] = None; save_company(cid); save_user(tid)
    await ctx.send(f"👢 Đã đuổi {member.mention}!")

@cty.command()
async def gop(ctx, amount: int):
    if amount <= 0: return
    uid = str(ctx.author.id); udata = load_user(uid); cid = udata.get("company"); c = load_company(cid) if cid else None
    if not c or udata.get("money", 0) < amount: return await ctx.send("Lỗi!")
    udata["money"] -= amount; c["treasury"] += amount; save_user(uid); save_company(cid)
    await ctx.send(f"💰 Góp **{amount:,} 💰**. Quỹ: **{c['treasury']:,} 💰**.")

@cty.command()
async def thulai(ctx):
    uid = str(ctx.author.id); cid = load_user(uid).get("company"); c = load_company(cid) if cid else None
    if not c or c["members"].get(uid) != "boss": return await ctx.send("Chỉ sếp!")
    now = datetime.now()
    if now - datetime.strptime(c.get("last_interest", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") < timedelta(days=1): return await ctx.send("⏳ Mai quay lại.")
    lai = min(int(c["treasury"] * 0.05), 100000); c["treasury"] += lai; c["last_interest"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_company(cid)
    await ctx.send(f"📈 Lãi: **{lai:,} 💰**. Quỹ: **{c['treasury']:,} 💰**.")

@cty.command()
async def luong(ctx, amount: int):
    uid = str(ctx.author.id); cid = load_user(uid).get("company"); c = load_company(cid) if cid else None
    if not c or c["members"].get(uid) != "boss": return await ctx.send("Chỉ sếp!")
    mc = len(c["members"])
    if amount * mc > c["treasury"]: return await ctx.send("Quỹ cạn!")
    c["treasury"] -= (amount * mc)
    for m in c["members"]: d = load_user(m); d["money"] += amount; save_user(m)
    save_company(cid); await ctx.send(f"💸 Đã phát **{amount:,} 💰** cho mỗi nhân viên!")

@cty.command()
async def chucvu(ctx, member: discord.Member, role: str):
    uid = str(ctx.author.id); cid = load_user(uid).get("company"); c = load_company(cid) if cid else None
    if not c or c["members"].get(uid) != "boss": return
    tid = str(member.id)
    if tid not in c["members"] or role not in ["quanly", "nhanvien"]: return await ctx.send("Lỗi!")
    c["members"][tid] = role; save_company(cid); await ctx.send(f"✅ Xong!")

@cty.command()
async def roi(ctx):
    uid = str(ctx.author.id); ud = load_user(uid); cid = ud.get("company"); c = load_company(cid) if cid else None
    if not c: return
    if c["members"][uid] == "boss":
        del COMPANY_CACHE[cid]; companies_col.delete_one({"_id": cid})
        for m in c["members"]: md = load_user(m); md["company"] = None; save_user(m)
        await ctx.send("🏢 Cty PHÁ SẢN!")
    else:
        del c["members"][uid]; ud["company"] = None; save_user(uid); save_company(cid)
        await ctx.send("🎒 Bạn đã nghỉ việc.")

@bot.command()
async def daichien(ctx, member: discord.Member = None, tactic: str = None):
    u1 = str(ctx.author.id); c1 = load_user(u1).get("company")
    if not member or tactic not in ["hack", "phot", "giangho"]:
        return await ctx.send(embed=discord.Embed(title="⚔️ ĐẠI CHIẾN", description="`k daichien @user <chiến_thuật>`\n1. `hack`: Tỉ lệ 30% | Ăn 10% | Phạt 5%\n2. `phot`: Tỉ lệ 50% | Ăn 5% | Phạt 2%\n3. `giangho`: Tỉ lệ 70% | Ăn 2% | Phạt 1%", color=discord.Color.red()))
    u2 = str(member.id); c2 = load_user(u2).get("company")
    if u1 == u2 or member.bot or not c1 or not c2 or c1 == c2: return await ctx.send("⚠️ Lỗi mục tiêu.")
    now = datetime.now()
    if c1 in cty_cooldowns and (now - cty_cooldowns[c1]).total_seconds() < 3600: return await ctx.send("⏳ Đợi 1 tiếng!")
    cp1, cp2 = load_company(c1), load_company(c2)
    if cp2["treasury"] < 10000: return await ctx.send("⚠️ Đối thủ quá nghèo!")
    cty_cooldowns[c1] = now
    
    wr, wp, lp = (30, 0.1, 0.05) if tactic == "hack" else (50, 0.05, 0.02) if tactic == "phot" else (70, 0.02, 0.01)
    msg = await ctx.send(f"⚔️ **{cp1['name']}** đang dùng **{tactic}** lên **{cp2['name']}**..."); await asyncio.sleep(2)
    if random.randint(1, 100) <= wr:
        st = int(cp2["treasury"] * wp); cp1["treasury"] += st; cp2["treasury"] -= st
        save_company(c1); save_company(c2); await msg.edit(content=f"🔥 **ĐẠI THẮNG!** Cướp được **{st:,} 💰**!")
    else:
        fn = int(cp1["treasury"] * lp); cp1["treasury"] -= fn; cp2["treasury"] += fn
        save_company(c1); save_company(c2); await msg.edit(content=f"💀 **THẤT BẠI!** Đền bù **{fn:,} 💰**.")


# =====================================================================
# LỆNH CƠ BẢN & CASINO
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📚 HỆ THỐNG LỆNH CỦA BOT", color=discord.Color.blurple())
    embed.add_field(name="🏢 THƯƠNG TRƯỜNG & CHỨNG KHOÁN", value="`k cty tao <tên>` • Lập cty 500k\n`k cty` • Mở Dashboard Cty\n`k daichien` • Cướp cty khác\n`k ck` • Chứng khoán", inline=False)
    embed.add_field(name="💳 KINH TẾ", value="`k rank`, `k tuido`\n`k cuahang`, `k ban`\n`k cuopnganhang` • Liều ăn nhiều\n`k daily`, `k lixi`, `k give`", inline=False)
    embed.add_field(name="🎮 CASINO (MAX 500K)", value="`k coin`, `k taixiu`, `k duathu`, `k baucua`, `k nohu`, `k soloott`", inline=False)
    embed.add_field(name="🌲 NHẬP VAI", value="`k gacha` (30k)\n`k thamhiem`, `k phai`, `k nhansinh`", inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=['ban'])
async def sell(ctx): await ctx.send(embed=discord.Embed(title="⚖️ CHỢ ĐEN", description="Cầm đồ uy tín!", color=discord.Color.dark_orange()), view=SellCategoryMenu(ctx.author))
@bot.command()
async def cuahang(ctx): await ctx.send(embed=discord.Embed(title="🏪 TTTM", description="Mua đồ khè nhau!", color=discord.Color.brand_green()), view=ShopCategoryMenu(ctx.author))

@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    u_id = str(ctx.author.id); u_data = load_user(u_id); now = datetime.now()
    if u_data.get("money", 0) < 50000: return await ctx.send("⚠️ Cần tối thiểu 50,000 💰 mua súng!")
    msg = await ctx.send("🔫 Đang xông vào ngân hàng..."); await asyncio.sleep(2)
    if random.randint(1, 100) <= 20:
        loot = random.randint(100000, 500000); u_data["money"] += loot; save_user(u_id)
        await msg.edit(content=f"🎉 **TRÓT LỌT!** Cướp được: **{loot:,} 💰**!")
    else:
        u_data["money"] -= 50000; u_data["jail_time"] = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"); save_user(u_id)
        await msg.edit(content=f"🚨 **BỊ BẮT!** Vào tù 10 phút!")

@bot.command()
async def gacha(ctx):
    u_id = str(ctx.author.id); u_data = load_user(u_id); cost = 30000
    if u_data.get("money", 0) < cost: return await ctx.send("⚠️ Cần 30k 💰.")
    u_data["money"] -= cost; save_user(u_id)
    msg = await ctx.send(f"🥚 {ctx.author.mention} đang đập trứng..."); await asyncio.sleep(2)
    r = random.uniform(0, 100)
    if r<=0.1: ra, t = "mythic", "🌌 THẦN THOẠI"
    elif r<=1.0: ra, t = "legendary", "👑 HUYỀN THOẠI"
    elif r<=5.0: ra, t = "epic", "🔮 SỬ THI"
    elif r<=20.0: ra, t = "rare", "💎 HIẾM"
    else: ra, t = "common", "🪵 PHỔ THÔNG"
    p = random.choice(PET_RATES[ra]["pool"]); u_data["pets"][p] = u_data["pets"].get(p, 0) + 1; save_user(u_id)
    await msg.edit(content=f"{ctx.author.mention} nổ trứng {t}: **{p}**!")

@bot.command()
async def rank(ctx):
    d = load_user(ctx.author.id); lv, xp, m = d.get("level", 1), d.get("xp", 0), d.get("money", 0)
    embed = discord.Embed(title=f"💳 Căn Cước: {ctx.author.name}", color=discord.Color.teal())
    embed.add_field(name="Danh hiệu", value=f"**{d.get('title')}**", inline=False)
    embed.add_field(name="Cấp độ", value=f"🌟 **LV {lv}**", inline=True); embed.add_field(name="Tài sản", value=f"**{m:,} 💰**", inline=True)
    if d.get("company"):
        comp = load_company(d["company"])
        if comp: embed.add_field(name="Công ty", value=f"🏢 {comp['name']}", inline=False)
    if d.get("jail_time"): embed.add_field(name="Trạng thái", value="🚨 **Đang bóc lịch!**", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def tuido(ctx):
    d = load_user(ctx.author.id); embed = discord.Embed(title=f"🎒 Kho của {ctx.author.name}", color=discord.Color.dark_theme())
    embed.add_field(name="🏠 Tài Sản", value="Trống." if not d.get("assets") else "\n".join([f"🔸 {a}" for a in d["assets"]]), inline=False)
    embed.add_field(name="🐾 Thú Cưng", value="Trống." if not d.get("pets") else "\n".join([f"{p} (x{c})" for p, c in d["pets"].items()]))
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    s_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": s_id}, {"$unset": {"allowed_channels": ""}})
        if s_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[s_id]: del CONFIG_CACHE[s_id]["allowed_channels"]
        return await ctx.send("✅ Đã gỡ bỏ giới hạn kênh.")
    mentions = ctx.message.channel_mentions
    if not mentions: return await ctx.send("⚠️ Tag các kênh: `k setup #kenh`")
    c_ids = [c.id for c in mentions]
    config_col.update_one({"_id": s_id}, {"$set": {"allowed_channels": c_ids}}, upsert=True); CONFIG_CACHE.setdefault(s_id, {})["allowed_channels"] = c_ids
    await ctx.send(f"✅ Bot CHỈ nhận lệnh tại: {', '.join(c.mention for c in mentions)}")

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount > 0: uid = str(member.id); ud = load_user(uid); ud["money"] += amount; save_user(uid); await ctx.send(f"✅ Đã bơm {amount:,} 💰 cho {member.mention}.")

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount > 0: uid = str(member.id); ud = load_user(uid); ud["money"] -= amount; save_user(uid); await ctx.send(f"✅ Đã trừ {amount:,} 💰 của {member.mention}.")

@bot.command()
async def daily(ctx):
    uid = str(ctx.author.id); ud = load_user(uid); now = datetime.now()
    if ud.get("last_daily") and now - datetime.strptime(ud["last_daily"], "%Y-%m-%d %H:%M:%S") < timedelta(days=1): return await ctx.send("⏳ Mai quay lại.")
    ud["money"] += 500; ud["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(uid); await ctx.send(f"✅ Nhận 500 💰! Dư: {ud['money']:,} 💰")

@bot.command()
async def lixi(ctx):
    uid = str(ctx.author.id); ud = load_user(uid); now = datetime.now()
    if ud.get("last_lixi") and now - datetime.strptime(ud["last_lixi"], "%Y-%m-%d %H:%M:%S") < timedelta(hours=12): return await ctx.send("🧧 Đợi 12 tiếng.")
    t = random.randint(1000, 8000); ud["money"] += t; ud["last_lixi"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_user(uid); await ctx.send(f"🧧 Lì xì: **{t:,} 💰**!")

@bot.command()
async def top(ctx):
    l = sorted([(d["_id"], d.get("money", 0)) for d in list(users_col.find())], key=lambda x: x[1], reverse=True)
    s = ""
    for i, (u, t) in enumerate(l[:10]):
        user = bot.get_user(int(u)); un = user.name if user else f"User {u[-4:]}"
        s += f"**#{i+1}** {un}: {t:,} 💰\n"
    await ctx.send(embed=discord.Embed(title="🏆 BẢNG VÀNG", description=s, color=discord.Color.gold()))

@bot.command()
async def coin(ctx, amount: str):
    ud, b = await check_gamble_conditions(ctx, amount)
    if not ud: return
    uid = str(ctx.author.id); ud["money"] -= b; save_user(uid); gamble_cooldowns[uid] = datetime.now()
    msg = await ctx.send(f"🪙 Tung xu..."); await asyncio.sleep(2) 
    if random.choice([True, False]): ud["money"] += b*2; save_user(uid); await msg.edit(content=f"🪙 **NGỬA!** Húp {b*2:,} 💰")
    else: await msg.edit(content=f"🪙 **SẤP!** Mất {b:,} 💰")

@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    if choice.lower() not in ["tai", "xiu"]: return await ctx.send("⚠️ `tai` hoặc `xiu`.")
    ud, b = await check_gamble_conditions(ctx, amount)
    if not ud: return
    uid = str(ctx.author.id); ud["money"] -= b; save_user(uid); gamble_cooldowns[uid] = datetime.now()
    msg = await ctx.send(f"🎲 Đang lắc..."); await asyncio.sleep(2)
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6); t = d1+d2+d3; res = "xiu" if t<=10 else "tai"
    if choice.lower() == res: 
        w = b*5 if d1==d2==d3 else b*2; ud["money"] += w; await msg.edit(content=f"🎲 {d1}-{d2}-{d3} ({res.upper()})! Thắng {w:,} 💰")
    else: await msg.edit(content=f"🎲 {d1}-{d2}-{d3} ({res.upper()})! Thua {b:,} 💰")
    save_user(uid)

@bot.command()
async def baucua(ctx, choice: str, amount: str):
    v = {"bau":"🥒", "cua":"🦀", "tom":"🦐", "ca":"🐟", "ga":"🐓", "huou":"🦌"}
    if choice.lower() not in v: return await ctx.send("⚠️ bau, cua, tom, ca, ga, huou.")
    ud, b = await check_gamble_conditions(ctx, amount)
    if not ud: return
    uid = str(ctx.author.id); ud["money"] -= b; save_user(uid); gamble_cooldowns[uid] = datetime.now()
    uc = v[choice.lower()]; msg = await ctx.send("🎲 Đang xóc..."); await asyncio.sleep(2)
    d = [random.choice(list(v.values())) for _ in range(3)]; c = d.count(uc)
    if c > 0: ud["money"] += b + (b*c); r = f"🎉 TRÚNG {c} Ô! Đền {b*c:,} 💰."
    else: r = f"💀 Trật! Mất {b:,} 💰."
    save_user(uid); await msg.edit(content=f"🎲 {'|'.join(d)}\n{r}")

@bot.command()
async def duathu(ctx, choice: str, amount: str):
    v = {"heo":"🐖", "cho":"🐕", "ngua":"🐎", "chuot":"🐀"}
    if choice.lower() not in v: return await ctx.send("⚠️ heo, cho, ngua, chuot.")
    ud, b = await check_gamble_conditions(ctx, amount)
    if not ud: return
    uid = str(ctx.author.id); ud["money"] -= b; save_user(uid); gamble_cooldowns[uid] = datetime.now()
    tl = 20; p = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    def gt(): return "🏇 **ĐUA THÚ!**\n" + "".join([f"🏁{'~'*min(x, tl)}{k}{' '*(tl - min(x, tl))}⛩️\n" for k, x in p.items()])
    msg = await ctx.send(gt()); w = None
    for _ in range(4):
        await asyncio.sleep(1.2)
        for k in p: p[k] += random.randint(2, 6); w = k if p[k] >= tl and not w else w
        await msg.edit(content=gt())
        if w: break
    if not w: w = max(p, key=p.get); p[w] = tl; await msg.edit(content=gt())
    if v[choice.lower()] == w: ud["money"] += b*3; r = f"\n🏆 **{w} VỀ NHẤT!** Ăn {b*3:,} 💰"
    else: r = f"\n💀 **{w} VỀ NHẤT!** Mất {b:,} 💰"
    save_user(uid); await msg.edit(content=gt() + r)

@bot.command(aliases=['nohu'])
async def mayxeng(ctx, amount: str):
    ud, b = await check_gamble_conditions(ctx, amount)
    if not ud: return
    uid = str(ctx.author.id); ud["money"] -= b; save_user(uid); gamble_cooldowns[uid] = datetime.now()
    i = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]; s = [random.choice(i) for _ in range(3)]
    msg = await ctx.send("🎰 Đang quay..."); await asyncio.sleep(2)
    if s[0]==s[1]==s[2]: w = b*50 if s[0]=="👑" else b*20 if s[0]=="💎" else b*10; ud["money"] += w; r = f"🔥 JACKPOT! Húp {w:,} 💰"
    elif s[0]==s[1] or s[1]==s[2] or s[0]==s[2]: w = b*2; ud["money"] += w; r = f"🎉 THẮNG NHỎ! Nhận {w:,} 💰"
    else: r = f"💀 Xịt! Mất {b:,} 💰"
    save_user(uid); await msg.edit(content=f"🎰 [ {s[0]} | {s[1]} | {s[2]} ]\n{r}")

@bot.command()
async def soloott(ctx, member: discord.Member, amount: str):
    ud, b = await check_gamble_conditions(ctx, amount)
    if not ud: return
    if member.id == ctx.author.id or member.bot: return await ctx.send("⚠️ Lỗi mục tiêu.")
    if load_user(member.id).get("money", 0) < b: return await ctx.send(f"⚠️ {member.mention} thiếu lúa!")
    await ctx.send(embed=discord.Embed(description=f"🔥 {ctx.author.mention} cược **{b:,} 💰** solo với {member.mention}!", color=discord.Color.red()), view=SoloOTTAccept(ctx.author, member, b))

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    ng, nn = str(ctx.author.id), str(member.id); dg, dn = load_user(ng), load_user(nn)
    if amount <= 0 or dg.get("money", 0) < amount or ng == nn: return await ctx.send("Lỗi!")
    dg["money"] -= amount; dn["money"] += amount; save_user(ng); save_user(nn)
    await ctx.send(f"💸 Đã chuyển {amount:,} 💰 cho {member.mention}!")

@bot.command()
async def phai(ctx):
    uid = str(ctx.author.id); ud = load_user(uid); end = ud.get("exp_end")
    if end:
        if datetime.now() >= datetime.strptime(end, "%Y-%m-%d %H:%M:%S"):
            rw = ud.get("exp_reward", 500); ud["money"] += rw; del ud["exp_end"]; del ud["exp_reward"]; save_user(uid)
            return await ctx.send(f"🎉 Thu hoạch được **{rw:,} 💰**!")
        h, r = divmod(int((datetime.strptime(end, "%Y-%m-%d %H:%M:%S") - datetime.now()).total_seconds()), 3600)
        return await ctx.send(f"⏳ Cố đợi thêm **{h} giờ {r//60} phút**.")
    await ctx.send(embed=discord.Embed(title="⛺ TRẠM AFK", color=discord.Color.dark_green()), view=ExpView(ctx.author))

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx): await ctx.send(embed=discord.Embed(title="🛒 TRẠM TIẾP TẾ", color=discord.Color.orange()), view=KhungRungShopView(ctx.author, 0))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    uid = str(ctx.author.id); now = datetime.now()
    if uid in dang_choi_nhansinh or (uid in nhansinh_cooldowns and (now - nhansinh_cooldowns[uid]).total_seconds() < 5): return await ctx.send(f"⏳ Từ từ!")
    ud = load_user(uid)
    if ud.get("money", 0) < 100: return await ctx.send("⚠️ Vé luân hồi 100 💰.")
    ud["money"] -= 100; nhansinh_cooldowns[uid] = now; dang_choi_nhansinh.append(uid); save_user(uid)
    await ctx.send(embed=discord.Embed(title="🌀 NHÂN SINH"), view=NhanSinhGameView(ctx.author, {"may_man": random.randint(1, 10)}))

@bot.event
async def on_message(message):
    if message.author.bot: return
    u_id = str(message.author.id); user_data = load_user(u_id)
    if user_data.get("jail_time") and datetime.now() < datetime.strptime(user_data["jail_time"], "%Y-%m-%d %H:%M:%S"): return
    user_data["xp"] += random.randint(5, 15); max_xp = user_data["level"] * 100
    if user_data["xp"] >= max_xp:
        user_data["xp"] -= max_xp; user_data["level"] += 1; thuong = user_data["level"] * 150; user_data["money"] += thuong
        try: await message.channel.send(f"🎉 {message.author.mention} lên cấp **{user_data['level']}**! Thưởng: **{thuong:,} 💰**")
        except: pass
    save_user(u_id); await bot.process_commands(message)

@bot.event
async def on_ready(): print(f'{bot.user} online!')

keep_alive() 
bot.run('MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.' + 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0')
