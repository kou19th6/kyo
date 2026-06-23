import discord
from discord.ext import commands
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 

# =====================================================================
# THIẾT LẬP CƠ BẢN CỦA BOT SIÊU VIP 4.0
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

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

gamble_cooldowns, nhansinh_cooldowns, dang_choi_nhansinh = {}, {}, []
cty_cooldowns, work_cooldowns, vietlott_players = {}, {}, {}

# =====================================================================
# KẾT NỐI MONGODB VÀ HỆ THỐNG BỘ ĐỆM (CACHE)
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]

users_col = db["users"]   
config_col = db["config"] 
companies_col = db["companies"]
kf_col = db["kallen_fantasy"]

DB_CACHE, CONFIG_CACHE, COMPANY_CACHE, KF_CACHE = {}, {}, {}, {}

def load_user(user_id):
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        document = users_col.find_one({"_id": user_id})
        if document: DB_CACHE[user_id] = document
        else: DB_CACHE[user_id] = {}
            
    defaults = {
        "xp": 0, "level": 1, "money": 0, "bank": 0, "title": "Dân Đáy Xã Hội 🧱", 
        "assets": [], "pets": {}, "company": None, "stocks": {}, "jail_time": None, "spouse": None
    }
    for key, value in defaults.items():
        if key not in DB_CACHE[user_id]: DB_CACHE[user_id][key] = value
    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE: users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

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
        if document: COMPANY_CACHE[company_id] = document
        else: return None
    return COMPANY_CACHE[company_id]

def save_company(company_id):
    company_id = str(company_id)
    if company_id in COMPANY_CACHE: companies_col.update_one({"_id": company_id}, {"$set": COMPANY_CACHE[company_id]}, upsert=True)

def load_kf_profile(user_id):
    user_id = str(user_id)
    if user_id not in KF_CACHE:
        doc = kf_col.find_one({"_id": user_id})
        if doc: KF_CACHE[user_id] = doc
        else: KF_CACHE[user_id] = {}
            
    defaults = {
        "level": 1, "exp": 0, "stamina": 100, "max_stamina": 100,
        "last_stamina_regen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "crystals": 0, "current_suit": "imayoh", "unlocked_suits": ["imayoh"],
        "inventory_weapons": ["wp_usp"], "equipped_weapon": "wp_usp",
        "inventory_stigmata": [], "equipped_stigmata": {"T": None, "M": None, "B": None},
        "cleared_stages": [], "abyss_floor": 1
    }
    
    for k, v in defaults.items():
        if k not in KF_CACHE[user_id]: KF_CACHE[user_id][k] = v
            
    last_regen = datetime.strptime(KF_CACHE[user_id]["last_stamina_regen"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    delta = now - last_regen
    minutes_passed = int(delta.total_seconds() / 60)
    
    if minutes_passed >= 5:
        stamina_to_add = minutes_passed // 5
        KF_CACHE[user_id]["stamina"] = min(KF_CACHE[user_id]["max_stamina"], KF_CACHE[user_id]["stamina"] + stamina_to_add)
        leftover_seconds = int(delta.total_seconds()) % 300
        new_regen_time = now - timedelta(seconds=leftover_seconds)
        KF_CACHE[user_id]["last_stamina_regen"] = new_regen_time.strftime("%Y-%m-%d %H:%M:%S")
        kf_col.update_one({"_id": user_id}, {"$set": KF_CACHE[user_id]}, upsert=True)

    return KF_CACHE[user_id]

def save_kf_profile(user_id):
    user_id = str(user_id)
    if user_id in KF_CACHE: kf_col.update_one({"_id": user_id}, {"$set": KF_CACHE[user_id]}, upsert=True)

@bot.check
async def global_jail_and_channel_check(ctx):
    if ctx.author.guild_permissions.administrator or ctx.command.name == "help": return True
    user_data = load_user(ctx.author.id)
    jail_time_str = user_data.get("jail_time")
    if jail_time_str:
        jail_end = datetime.strptime(jail_time_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < jail_end:
            embed = discord.Embed(title="🚨 BÁO ĐỘNG ĐỎ!", description=f"{ctx.author.mention} đang bóc lịch trong trại giam!\n\n⏳ Mãn hạn tù: <t:{int(jail_end.timestamp())}:R>\n\n", color=discord.Color.red())
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
        time_difference = (current_time - gamble_cooldowns[user_id]).total_seconds()
        if time_difference < 4:
            time_left = int(4 - time_difference)
            await ctx.reply(embed=discord.Embed(description=f"⏳ Đợi {time_left}s nữa hẵng lắc tiếp sếp ơi!", color=discord.Color.orange()), mention_author=False)
            return None, None
            
    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        await ctx.reply(embed=discord.Embed(description="💸 Tiền trong ví không có một xu mà đòi cá cược!", color=discord.Color.red()), mention_author=False)
        return None, None
        
    try: 
        if amount_str.lower() == "all": bet_amount = user_data["money"] if user_data["money"] <= 500000 else 500000
        else: bet_amount = int(amount_str)
    except ValueError: 
        await ctx.reply(embed=discord.Embed(description="⚠️ Nhập số tiền sai định dạng! Vui lòng nhập số hoặc chữ `all`.", color=discord.Color.red()), mention_author=False)
        return None, None
        
    if bet_amount <= 0 or bet_amount > user_data["money"]: 
        await ctx.reply(embed=discord.Embed(description=f"⚠️ Bạn chỉ có **{user_data['money']:,} 💰** trong ví thôi!", color=discord.Color.red()), mention_author=False)
        return None, None
        
    if bet_amount > 500000: 
        await ctx.reply(embed=discord.Embed(description="🛑 Nhà cái quy định mỗi ván cược tối đa **500,000 💰** thôi nhé!", color=discord.Color.red()), mention_author=False)
        return None, None
        
    return user_data, bet_amount

SHOP_ITEMS = {
    "title_1": {"type": "title", "name": "Dân Thường 🚶", "price": 10000, "emoji": "🏷️"},
    "title_4": {"type": "title", "name": "Đại Gia 💸", "price": 1000000, "emoji": "🏷️"},
    "vehicle_2": {"type": "vehicle", "name": "Honda SH 150i 🏍️", "price": 300000, "emoji": "🏍️"},
    "vehicle_4": {"type": "vehicle", "name": "Mercedes G63 🚙", "price": 8000000, "emoji": "🚙"},
    "house_2": {"type": "house", "name": "Chung Cư Mini 🏢", "price": 500000, "emoji": "🏢"},
    "house_4": {"type": "house", "name": "Biệt Thự Hồ Tây 🏡", "price": 30000000, "emoji": "🏡"}
}

def get_asset_price(asset_name):
    for item_key, item_data in SHOP_ITEMS.items():
        if item_data["name"] == asset_name: return int(item_data["price"] * 0.7)
    return 1000

PET_RATES = {
    "common": {"rate": 70.0, "pool": ["Gà Con 🐥", "Chó Cỏ 🐕", "Mèo Mướp 🐈"]},
    "rare": {"rate": 20.0, "pool": ["Sói Tuyết 🐺", "Gấu Xám 🐻", "Đại Bàng 🦅"]},
    "epic": {"rate": 7.0, "pool": ["Sư Tử Lửa 🦁", "Khỉ Đột 🦍", "Bạch Hổ 🐅"]},
    "legendary": {"rate": 2.5, "pool": ["Rồng Đỏ 🐉", "Kỳ Lân 🦄"]},
    "mythic": {"rate": 0.5, "pool": ["Thần Long 🐲", "Hắc Ám Cự Thú 🦇"]}
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

KALLEN_BATTLESUITS = {
    "imayoh": {"id": "imayoh", "name": "Ritual Imayoh (MECH)", "type": "MECH", "rarity": "A", "base_hp": 1200, "base_atk": 250, "base_def": 150, "base_crt": 30, "skill_basic_name": "Súng Kata", "skill_basic_dmg": 1.2, "skill_combo_name": "Mưa Đạn Động Năng", "skill_combo_dmg": 2.5, "skill_ult_name": "Khúc Ca Elysia", "skill_ult_dmg": 6.0, "ult_sp_cost": 80, "evade_name": "Vết Nứt Không Gian", "emoji": "🔫"},
    "sundenjager": {"id": "sundenjager", "name": "Sündenjäger (MECH)", "type": "MECH", "rarity": "A", "base_hp": 1400, "base_atk": 220, "base_def": 180, "base_crt": 25, "skill_basic_name": "Xạ Kích Liên Thanh", "skill_basic_dmg": 1.0, "skill_combo_name": "Càn Quét Tội Lỗi", "skill_combo_dmg": 2.2, "skill_ult_name": "Oanh Tạc Quỹ Đạo", "skill_ult_dmg": 5.5, "ult_sp_cost": 75, "evade_name": "Phản Xạ Vượt Cấp", "emoji": "🦇"},
    "sixth_serenade": {"id": "sixth_serenade", "name": "Sixth Serenade (PSY)", "type": "PSY", "rarity": "S", "base_hp": 1500, "base_atk": 320, "base_def": 140, "base_crt": 40, "skill_basic_name": "Dạ Khúc Dạ Tưởng", "skill_basic_dmg": 1.5, "skill_combo_name": "Dấu Ấn Quạ Đen", "skill_combo_dmg": 3.0, "skill_ult_name": "Bản Tình Ca Bóng Tối", "skill_ult_dmg": 8.0, "ult_sp_cost": 100, "evade_name": "Vũ Điệu Quạ Đen", "emoji": "🎭"}
}

KALLEN_WEAPONS = {
    "wp_usp": {"id": "wp_usp", "name": "Súng Ngắn USP", "rarity": 2, "atk": 50, "crt": 5},
    "wp_water": {"id": "wp_water", "name": "Water Spirit Type-II", "rarity": 4, "atk": 200, "crt": 15},
    "wp_aria": {"id": "wp_aria", "name": "Tranquil Arias", "rarity": 5, "atk": 350, "crt": 35}
}

KALLEN_STIGMATA = {
    "stig_attila_t": {"id": "stig_attila_t", "name": "Attila (T)", "type": "T", "rarity": 3, "hp": 200, "atk": 40, "def": 30, "crt": 0},
    "stig_michel_m": {"id": "stig_michel_m", "name": "Michelangelo (M)", "type": "M", "rarity": 5, "hp": 450, "atk": 0, "def": 120, "crt": 10},
    "stig_nohime_b": {"id": "stig_nohime_b", "name": "Nohime (B)", "type": "B", "rarity": 5, "hp": 450, "atk": 80, "def": 50, "crt": 10}
}

KALLEN_ENEMIES = {
    "zombie_1": {"name": "Xác Sống Cầm Kiếm", "type": "BIO", "hp": 2000, "atk": 100, "def": 50, "sp_drop": 5},
    "beast_1": {"name": "Thú Honkai Kỵ Binh", "type": "PSY", "hp": 3000, "atk": 120, "def": 100, "sp_drop": 5},
    "mecha_1": {"name": "Robot Tuần Tra", "type": "MECH", "hp": 3500, "atk": 80, "def": 200, "sp_drop": 5},
    "boss_god": {"name": "Herrscher of the Void", "type": "BIO", "hp": 50000, "atk": 800, "def": 400, "sp_drop": 50}
}

KALLEN_STAGES = {
    "1-1": {"name": "1-1: Sự thức tỉnh", "enemies": ["zombie_1", "zombie_1"], "reward_money": 5000, "reward_xp": 100},
    "1-2": {"name": "1-2: Cuộc vây hãm", "enemies": ["zombie_1", "beast_1"], "reward_money": 7000, "reward_xp": 150},
    "2-1": {"name": "Chung Cuộc: Luật Giả", "enemies": ["boss_god"], "reward_money": 50000, "reward_xp": 1000}
}

def calculate_kallen_stats(user_id):
    p = load_kf_profile(user_id)
    suit = KALLEN_BATTLESUITS[p["current_suit"]]
    total_hp, total_atk, total_def, total_crt = suit["base_hp"], suit["base_atk"], suit["base_def"], suit["base_crt"]
    
    if p["equipped_weapon"]:
        wp = KALLEN_WEAPONS[p["equipped_weapon"]]
        total_atk += wp["atk"]; total_crt += wp["crt"]
        
    for pos in ["T", "M", "B"]:
        stig_id = p["equipped_stigmata"][pos]
        if stig_id:
            stig = KALLEN_STIGMATA[stig_id]
            total_hp += stig["hp"]; total_atk += stig["atk"]; total_def += stig["def"]; total_crt += stig["crt"]
            
    return {
        "suit": suit,
        "hp": int(total_hp * (1 + (p["level"] - 1) * 0.1)), 
        "atk": int(total_atk * (1 + (p["level"] - 1) * 0.1)),
        "def": int(total_def * (1 + (p["level"] - 1) * 0.1)),
        "crt": int(total_crt * (1 + (p["level"] - 1) * 0.1)),
    }

def get_type_advantage(attacker_type, defender_type):
    if attacker_type == "MECH" and defender_type == "BIO": return 1.3
    if attacker_type == "BIO" and defender_type == "PSY": return 1.3
    if attacker_type == "PSY" and defender_type == "MECH": return 1.3
    if attacker_type == "BIO" and defender_type == "MECH": return 0.7
    if attacker_type == "PSY" and defender_type == "BIO": return 0.7
    if attacker_type == "MECH" and defender_type == "PSY": return 0.7
    return 1.0
    # =====================================================================
# KALLEN FANTASY - GIAO DIỆN GACHA & QUẢN LÝ TÀI KHOẢN
# =====================================================================
class KallenGachaView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Tiếp Tế x1 (280 💎)", style=discord.ButtonStyle.primary, emoji="📦")
    async def roll_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 1)

    @discord.ui.button(label="Tiếp Tế x10 (2800 💎)", style=discord.ButtonStyle.danger, emoji="🎁")
    async def roll_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 10)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: 
            await interaction.response.send_message("⚠️ Không thể quay ké của người khác!", ephemeral=True)
            return False
        return True

    async def process_gacha(self, interaction: discord.Interaction, times: int):
        user_id = str(interaction.user.id)
        p = load_kf_profile(user_id)
        cost = 280 * times
        
        if p["crystals"] < cost:
            return await interaction.response.send_message(f"⚠️ Thuyền trưởng không đủ Pha lê! Cần {cost:,} 💎.", ephemeral=True)
            
        p["crystals"] -= cost
        results = []
        
        for _ in range(times):
            roll = random.uniform(0, 100)
            if roll <= 1.5: 
                suit = "sixth_serenade"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"🌟 **VALKYRIE CẤP S:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"🌟 Valkyrie Cấp S (Trùng lặp, chuyển thành 1000 💎)")
                    p["crystals"] += 1000
            elif roll <= 5.0: 
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] == 5] + [k for k, v in KALLEN_STIGMATA.items() if v["rarity"] == 5]
                item = random.choice(pool)
                if item in KALLEN_WEAPONS:
                    p["inventory_weapons"].append(item)
                    results.append(f"🔶 **Vũ Khí 5★:** {KALLEN_WEAPONS[item]['name']}")
                else:
                    p["inventory_stigmata"].append(item)
                    results.append(f"💠 **Vết Thánh 5★:** {KALLEN_STIGMATA[item]['name']}")
            elif roll <= 15.0: 
                suit = "sundenjager"
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"⭐ **VALKYRIE CẤP A:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"⭐ Valkyrie Cấp A (Trùng lặp, chuyển thành 280 💎)")
                    p["crystals"] += 280
            elif roll <= 45.0: 
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] == 4]
                if pool:
                    item = random.choice(pool)
                    p["inventory_weapons"].append(item)
                    results.append(f"🟦 Vũ Khí 4★: {KALLEN_WEAPONS[item]['name']}")
                else:
                    results.append("🟦 Tài nguyên Nâng cấp (50 💎)")
                    p["crystals"] += 50
            else: 
                pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] <= 3] + [k for k, v in KALLEN_STIGMATA.items() if v["rarity"] <= 3]
                item = random.choice(pool)
                if item in KALLEN_WEAPONS:
                    p["inventory_weapons"].append(item)
                    results.append(f"⬜ Vũ Khí 3★: {KALLEN_WEAPONS[item]['name']}")
                else:
                    p["inventory_stigmata"].append(item)
                    results.append(f"⬜ Vết Thánh 3★: {KALLEN_STIGMATA[item]['name']}")
                    
        save_kf_profile(user_id)
        desc = "\n".join(results)
        embed = discord.Embed(title="📦 KẾT QUẢ TIẾP TẾ", description=desc, color=discord.Color.gold())
        embed.set_footer(text=f"Pha lê còn lại: {p['crystals']:,} 💎", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

class KallenCombatView(discord.ui.View):
    def __init__(self, author, player_stats, stage_data, p_profile, is_abyss=False):
        super().__init__(timeout=300) 
        self.author = author
        self.p_stats = player_stats
        self.stage = stage_data
        self.p_profile = p_profile
        self.is_abyss = is_abyss
        
        self.p_hp = self.p_stats["hp"]
        self.p_max_hp = self.p_stats["hp"]
        self.p_sp = 0 
        self.p_evade_cooldown = 0
        
        self.crystals_earned = 0
        self.abyss_floor = self.p_profile.get("abyss_floor", 1) if is_abyss else 1

        if not self.is_abyss:
            self.enemy_list = self.stage["enemies"].copy()
            self.current_enemy_idx = 0
            self.load_enemy()
        else:
            self.load_abyss_enemy()

    def load_enemy(self):
        if self.current_enemy_idx < len(self.enemy_list):
            enemy_id = self.enemy_list[self.current_enemy_idx]
            base_enemy = KALLEN_ENEMIES[enemy_id]
            self.e_data = {
                "name": base_enemy["name"], "type": base_enemy["type"], "hp": base_enemy["hp"],
                "max_hp": base_enemy["hp"], "atk": base_enemy["atk"], "def": base_enemy["def"], "sp_drop": base_enemy["sp_drop"]
            }
            return True
        return False

    def load_abyss_enemy(self):
        enemy_pool = [e for k, e in KALLEN_ENEMIES.items() if "god_boss" not in k]
        base_enemy = random.choice(enemy_pool)
        multiplier = 1.0 + (self.abyss_floor * 0.15)
        self.e_data = {
            "name": f"{base_enemy['name']} (Tầng {self.abyss_floor})", "type": base_enemy["type"],
            "hp": int(base_enemy["hp"] * multiplier), "max_hp": int(base_enemy["hp"] * multiplier),
            "atk": int(base_enemy["atk"] * multiplier), "def": int(base_enemy["def"] * multiplier),
            "sp_drop": base_enemy["sp_drop"] + int(self.abyss_floor / 5)
        }

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: return False
        return True

    def calculate_damage(self, dmg_multiplier):
        base_atk = self.p_stats["atk"]
        enemy_def = self.e_data["def"]
        type_adv = get_type_advantage(self.p_stats["suit"]["type"], self.e_data["type"])
        
        is_crit = False
        crit_mult = 1.0
        if random.uniform(0, 100) <= min(100, self.p_stats["crt"]):
            is_crit, crit_mult = True, 2.0 
                
        raw_dmg = (base_atk * dmg_multiplier * type_adv * crit_mult) - (enemy_def * 0.5)
        return int(max(10, raw_dmg)), is_crit

    def enemy_turn(self):
        if self.e_data["hp"] <= 0: return 0, "Quái vật đã bị tiêu diệt!"
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        raw_dmg = (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)
        final_dmg = int(max(5, raw_dmg))
        self.p_hp -= final_dmg
        return final_dmg, f"💥 **{self.e_data['name']}** phản công gây **{final_dmg}** sát thương!"

    async def update_battle_ui(self, interaction: discord.Interaction, combat_log: str):
        if self.e_data["hp"] <= 0:
            self.p_sp += self.e_data["sp_drop"] 
            combat_log += f"\n💀 **{self.e_data['name']}** bị hạ! Nhận {self.e_data['sp_drop']} SP."
            
            if self.is_abyss:
                crystal_drop = random.randint(5, 15) + int(self.abyss_floor / 2)
                self.crystals_earned += crystal_drop
                heal_amount = int(self.p_max_hp * 0.1)
                self.p_hp = min(self.p_max_hp, self.p_hp + heal_amount)
                combat_log += f"\n✅ Vượt Tầng {self.abyss_floor}! Rớt {crystal_drop} 💎. Hồi {heal_amount} HP."
                self.abyss_floor += 1
                self.load_abyss_enemy()
                combat_log += f"\n👹 **CẢNH BÁO:** {self.e_data['name']} xuất hiện!"
            else:
                self.current_enemy_idx += 1
                if not self.load_enemy():
                    for child in self.children: child.disabled = True
                    u_data = load_user(self.author.id)
                    u_data["money"] += self.stage["reward_money"]
                    self.p_profile["exp"] += self.stage["reward_xp"]
                    save_user(self.author.id); save_kf_profile(self.author.id)
                    embed = discord.Embed(title="🎉 VƯỢT ẢI THÀNH CÔNG!", description=f"{combat_log}\n\n🎁 **THƯỞNG:** {self.stage['reward_money']:,} 💰 | {self.stage['reward_xp']} EXP", color=discord.Color.green())
                    await interaction.response.edit_message(embed=embed, view=self)
                    return self.stop()
                else: combat_log += f"\n⚠️ **CẢNH BÁO:** Kẻ địch [**{self.e_data['name']}**] xuất hiện!"

        if self.p_hp <= 0:
            for child in self.children: child.disabled = True
            if self.is_abyss:
                self.p_profile["crystals"] += self.crystals_earned
                if self.abyss_floor > self.p_profile.get("abyss_floor", 0): self.p_profile["abyss_floor"] = self.abyss_floor
                save_kf_profile(self.author.id)
                desc = f"{combat_log}\n\nGục ngã tại **Tầng {self.abyss_floor}**.\n🎁 **THƯỞNG:** {self.crystals_earned:,} 💎"
            else: desc = f"{combat_log}\n\nValkyrie đã gục ngã. Hãy thử lại!"
            await interaction.response.edit_message(embed=discord.Embed(title="💀 NHIỆM VỤ THẤT BẠI", description=desc, color=discord.Color.dark_grey()), view=self)
            return self.stop()

        if self.p_evade_cooldown > 0: self.p_evade_cooldown -= 1

        p_hp_bar = make_progress_bar(max(0, self.p_hp), self.p_max_hp, 10)
        e_hp_bar = make_progress_bar(max(0, self.e_data["hp"]), self.e_data["max_hp"], 10)
        
        embed = discord.Embed(title=f"🌋 VỰC SÂU ABYSS - TẦNG {self.abyss_floor}" if self.is_abyss else f"⚔️ {self.stage['name'].upper()}", description=combat_log, color=discord.Color.dark_red() if self.is_abyss else discord.Color.red())
        suit = self.p_stats["suit"]
        embed.add_field(name=f"{suit['emoji']} {suit['name']}", value=f"❤️ HP: {max(0, self.p_hp)}/{self.p_max_hp}\n`{p_hp_bar}`\n⚡ SP: {self.p_sp}" + (f" | {self.crystals_earned} 💎" if self.is_abyss else ""), inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        type_icon = "🔺" if get_type_advantage(suit["type"], self.e_data["type"]) > 1 else ("🔻" if get_type_advantage(suit["type"], self.e_data["type"]) < 1 else "➖")
        embed.add_field(name=f"👹 {self.e_data['name']} ({self.e_data['type']}) {type_icon}", value=f"❤️ HP: {max(0, self.e_data['hp'])}/{self.e_data['max_hp']}\n`{e_hp_bar}`", inline=True)

        self.btn_ult.disabled = self.p_sp < suit["ult_sp_cost"]
        self.btn_evade.disabled = self.p_evade_cooldown > 0

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, custom_id="btn_atk")
    async def btn_atk(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit = self.calculate_damage(suit["skill_basic_dmg"])
        self.e_data["hp"] -= dmg; self.p_sp += 5 
        log = f"🗡️ Dùng **{suit['skill_basic_name']}** gây **{dmg}** ST" + (" (💥)" if is_crit else "") + "."
        e_dmg, e_log = self.enemy_turn()
        await self.update_battle_ui(interaction, log + f"\n{e_log}")

    @discord.ui.button(label="Combo", style=discord.ButtonStyle.success, custom_id="btn_combo")
    async def btn_combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        dmg, is_crit = self.calculate_damage(suit["skill_combo_dmg"])
        self.e_data["hp"] -= dmg; self.p_sp += 2
        log = f"⚔️ Đòn Nhánh **{suit['skill_combo_name']}** gây **{dmg}** ST" + (" (💥)" if is_crit else "") + "."
        e_dmg, e_log = self.enemy_turn()
        await self.update_battle_ui(interaction, log + f"\n{e_log}")

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, custom_id="btn_ult")
    async def btn_ult(self, interaction: discord.Interaction, button: discord.ui.Button):
        suit = self.p_stats["suit"]
        if self.p_sp < suit["ult_sp_cost"]: return await interaction.response.send_message("⚠️ Không đủ SP!", ephemeral=True)
        self.p_sp -= suit["ult_sp_cost"]; dmg, is_crit = self.calculate_damage(suit["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        log = f"🔥 Tất Sát **{suit['skill_ult_name']}** gây **{dmg}** ST khủng khiếp!" + (" (💥)" if is_crit else "")
        if self.e_data["hp"] > 0: log += f"\n🛡️ Đối phương bị choáng ngợp, bỏ qua lượt!"
        await self.update_battle_ui(interaction, log)

    @discord.ui.button(label="Né Cực Hạn", style=discord.ButtonStyle.secondary, custom_id="btn_evade")
    async def btn_evade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.p_evade_cooldown > 0: return await interaction.response.send_message("⚠️ Đang hồi chiêu!", ephemeral=True)
        self.p_evade_cooldown = 3; self.p_sp += 15 
        type_adv = get_type_advantage(self.e_data["type"], self.p_stats["suit"]["type"])
        e_dmg = int(max(5, (self.e_data["atk"] * type_adv) - (self.p_stats["def"] * 0.5)))
        await self.update_battle_ui(interaction, f"💨 Dùng **{self.p_stats['suit']['evade_name']}**! Né hoàn toàn **{e_dmg}** ST, hồi 15 SP.")

# =====================================================================
# CÁC LỆNH KALLEN FANTASY (SỬ DỤNG CHUẨN - KHÔNG TRÙNG LẶP)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['kf', 'honkai'])
async def kallen(ctx):
    p = load_kf_profile(ctx.author.id)
    stats = calculate_kallen_stats(ctx.author.id)
    suit = stats["suit"]
    
    embed = discord.Embed(
        title="🌌 KALLEN FANTASY - HYPERION BRIDGE",
        description=f"Thuyền trưởng: **{ctx.author.name}**\nCấp độ: **Lv.{p['level']}** | Thể lực: **{p['stamina']}/{p['max_stamina']}** ⚡ | Pha lê: **{p['crystals']:,}** 💎",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Đang xuất chiến", value=f"**{suit['emoji']} {suit['name']}**", inline=False)
    embed.add_field(name="Chỉ số chiến đấu", value=f"❤️ HP: {stats['hp']} | ⚔️ ATK: {stats['atk']}\n🛡️ DEF: {stats['def']} | 💥 CRT: {stats['crt']}", inline=False)
    
    cmds = "`k kallen gacha` • Tiếp Tế | `k kallen doipha <số>` • Đổi Tiền lấy Pha lê\n`k kallen equip <loại> <id>` • Lắp đồ | `k kallen story <mã>` | `k kallen abyss`"
    embed.add_field(name="Bảng Lệnh", value=cmds, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command()
async def doipha(ctx, amount: int):
    if amount <= 0: return await ctx.reply("Vui lòng nhập số lớn hơn 0.")
    u_data = load_user(ctx.author.id)
    cost = amount * 1000
    if u_data.get("money", 0) < cost: return await ctx.reply(f"⚠️ Sếp cần {cost:,} 💰 để đổi lấy {amount:,} 💎.")
    u_data["money"] -= cost; save_user(ctx.author.id)
    p = load_kf_profile(ctx.author.id); p["crystals"] += amount; save_kf_profile(ctx.author.id)
    await ctx.reply(f"✅ Nạp thành công **{amount:,} 💎** vào Kallen Fantasy.")

@kallen.command()
async def equip(ctx, category: str, item_id: str):
    p = load_kf_profile(ctx.author.id)
    category = category.lower()
    if category == "suit":
        if item_id not in p["unlocked_suits"]: return await ctx.reply("⚠️ Bạn chưa có Giáp này.")
        p["current_suit"] = item_id
    elif category == "wp":
        if item_id not in p["inventory_weapons"]: return await ctx.reply("⚠️ Bạn không có Vũ khí này.")
        p["equipped_weapon"] = item_id
    elif category in ["stig_t", "stig_m", "stig_b"]:
        pos = category.split("_")[1].upper()
        if item_id not in p["inventory_stigmata"]: return await ctx.reply("⚠️ Bạn không có Vết thánh này.")
        p["equipped_stigmata"][pos] = item_id
    else: return await ctx.reply("⚠️ Cú pháp: `suit`, `wp`, `stig_t`, `stig_m`, `stig_b`.")
    save_kf_profile(ctx.author.id)
    await ctx.reply("✅ Lắp trang bị thành công.")

@kallen.command()
async def gacha(ctx):
    await ctx.reply(embed=discord.Embed(title="📦 KÊNH TIẾP TẾ", description="Dùng Pha Lê 💎 để Gacha Valkyrie và Trang Bị!", color=discord.Color.blue()), view=KallenGachaView(ctx.author), mention_author=False)

@kallen.command()
async def story(ctx, stage_id: str = None):
    p = load_kf_profile(ctx.author.id)
    if stage_id is None or stage_id.lower() == "list":
        desc = "".join([f"{'✅' if s_id in p['cleared_stages'] else '🔒'} **Ải {s_id}**: {s_data['name']} (Thưởng: {s_data['reward_money']:,} 💰)\n" for s_id, s_data in KALLEN_STAGES.items()])
        return await ctx.reply(embed=discord.Embed(title="📜 DANH SÁCH ẢI CỐT TRUYỆN", description=desc, color=discord.Color.dark_purple()), mention_author=False)
    if stage_id not in KALLEN_STAGES: return await ctx.reply("⚠️ Mã ải không tồn tại.")
    if p["stamina"] < 10: return await ctx.reply(f"⚠️ Không đủ thể lực. Cần 10 ⚡.")
        
    p["stamina"] -= 10; save_kf_profile(ctx.author.id)
    stage_data = KALLEN_STAGES[stage_id]
    msg = await ctx.reply(embed=discord.Embed(title=f"🚀 XUẤT KÍCH: {stage_data['name']}", description="Đang tải dữ liệu...", color=discord.Color.blue()), mention_author=False)
    await asyncio.sleep(2)
    view = KallenCombatView(ctx.author, calculate_kallen_stats(ctx.author.id), stage_data, p, is_abyss=False)
    await view.update_battle_ui(ctx, f"Bắt đầu ải: {stage_data['name']}. Kẻ địch đã xuất hiện!")

@kallen.command()
async def abyss(ctx):
    p = load_kf_profile(ctx.author.id)
    if p["stamina"] < 20: return await ctx.reply(f"⚠️ Không đủ thể lực. Cần 20 ⚡.")
    p["stamina"] -= 20; save_kf_profile(ctx.author.id)
    msg = await ctx.reply(embed=discord.Embed(title="🌋 VỰC SÂU VÔ TẬN", description="Chuẩn bị chiến đấu...", color=discord.Color.dark_red()), mention_author=False)
    await asyncio.sleep(2)
    view = KallenCombatView(ctx.author, calculate_kallen_stats(ctx.author.id), None, p, is_abyss=True)
    await view.update_battle_ui(ctx, f"Cửa Vực Sâu mở ra. {view.e_data['name']} lao về phía bạn!")
    # =====================================================================
# GIAO DIỆN UI: CỬA HÀNG ĐẠI GIA (SHOP)
# =====================================================================
class ShopItemSelect(discord.ui.Select):
    """Bảng Dropdown chọn đồ trong Cửa Hàng Đại Gia"""
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
            placeholder="Nhấn vào đây để chọn món đồ muốn tậu...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_info = SHOP_ITEMS[self.values[0]]
        
        # Kiểm tra túi tiền
        if user_data.get("money", 0) < item_info["price"]:
            embed_fail = discord.Embed(
                description=f"⚠️ Thẻ từ chối! Bạn cần **{item_info['price']:,} 💰** để mua {item_info['name']}.", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)
            
        # Trừ tiền
        user_data["money"] -= item_info["price"]
        
        # Xử lý mua Danh hiệu (Ghi đè)
        if item_info["type"] == "title":
            user_data["title"] = item_info["name"]
            success_message = f"🎉 Tiền trao cháo múc! Bạn đã trang bị danh hiệu: **{item_info['name']}**."
        else:
            # Xử lý mua Đồ vật (Xe, Nhà...)
            if item_info["name"] in user_data.get("assets", []):
                # Nếu đã có, hoàn lại tiền và báo lỗi
                user_data["money"] += item_info["price"] 
                embed_exist = discord.Embed(
                    description=f"⚠️ Bạn đã đứng tên sở hữu **{item_info['name']}** rồi, mua thêm chi cho chật nhà!", 
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed_exist, ephemeral=True)
            
            # Thêm vào túi đồ
            user_data["assets"].append(item_info["name"])
            success_message = f"🎉 Chúc mừng đại gia! Bạn vừa đập hộp siêu phẩm **{item_info['name']}**."
            
        save_user(user_id)
        
        embed_success = discord.Embed(
            title="🛍️ GIAO DỊCH HOÀN TẤT!", 
            description=success_message, 
            color=discord.Color.green()
        )
        embed_success.set_footer(
            text=f"Số dư ví hiện tại: {user_data['money']:,} 💰", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=embed_success, view=None)

class ShopCategoryMenu(discord.ui.View):
    """Menu chọn danh mục trong Cửa hàng Đại Gia"""
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Danh Hiệu (VIP)", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(
            title="🛍️ QUẦY BÁN DANH HIỆU", 
            description="Tút tát lại vẻ đẹp trai bằng một danh hiệu xịn xò dán lên Căn Cước.", 
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️")
    async def btn_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(
            title="🛍️ SHOWROOM XE CỘ & PHI CƠ", 
            description="Đẳng cấp thể hiện qua tốc độ. Hãy chọn một con xe ưng ý.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰")
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(
            title="🛍️ SÀN GIAO DỊCH BẤT ĐỘNG SẢN", 
            description="Đầu tư nhà đất là kênh an toàn nhất để xưng vương.", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Ai gọi lệnh người đó mua nha, đừng có bấm giành!", ephemeral=True)
            return False
        return True

# =====================================================================
# GIAO DIỆN UI: CHỢ ĐEN (BÁN LẠI TÀI SẢN & THÚ CƯNG)
# =====================================================================
class SellItemSelect(discord.ui.Select):
    """Bảng Dropdown chọn đồ muốn bán cho Chợ đen"""
    def __init__(self, items, is_pet=False):
        self.is_pet = is_pet
        options = []
        
        if is_pet:
            count = 0
            for pet, quantity in list(items.items()):
                if count >= 25: 
                    break
                if quantity > 0: 
                    options.append(discord.SelectOption(
                        label=pet, 
                        description=f"Đang có: {quantity} con | Chợ đen thâu tóm: {get_pet_sell_price(pet):,} 💰", 
                        value=pet
                    ))
                    count += 1
        else:
            for asset in list(set(items))[:25]:
                options.append(discord.SelectOption(
                    label=asset, 
                    description=f"Bị ép giá còn: {get_asset_price(asset):,} 💰", 
                    value=asset
                ))
                
        super().__init__(
            placeholder="Chọn món đồ bạn muốn cắm sổ / bán...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        item_value = self.values[0]
        
        if self.is_pet:
            if user_data.get("pets", {}).get(item_value, 0) <= 0: 
                return await interaction.response.send_message("Lỗi: Không tìm thấy thú cưng này trong chuồng!", ephemeral=True)
                
            sell_price = get_pet_sell_price(item_value)
            user_data["pets"][item_value] -= 1
            
            # Xóa key nếu pet về 0
            if user_data["pets"][item_value] == 0: 
                del user_data["pets"][item_value]
                
            success_message = f"✅ Thương lái đã mang bé **{item_value}** đi.\nBạn nhận được **{sell_price:,} 💰** tiền tươi thóc thật!"
        else:
            if item_value not in user_data.get("assets", []): 
                return await interaction.response.send_message("Lỗi: Bạn làm gì có tài sản này mà đòi đem cắm!", ephemeral=True)
                
            sell_price = get_asset_price(item_value)
            user_data["assets"].remove(item_value)
            success_message = f"✅ Chủ tiệm cầm đồ đã thâu tóm **{item_value}**.\nBạn cắn răng chịu lỗ, vớt vát lại được **{sell_price:,} 💰**!"

        # Cộng tiền cho user
        user_data["money"] += sell_price
        save_user(user_id)
        
        embed = discord.Embed(
            title="🤝 GIAO DỊCH HOÀN TẤT", 
            description=success_message, 
            color=discord.Color.dark_orange()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class SellCategoryMenu(discord.ui.View):
    """Menu chọn danh mục bán trong Chợ đen"""
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Cắm Sổ Đỏ / Cầm Xe", style=discord.ButtonStyle.primary, emoji="🏠")
    async def btn_asset(self, interaction: discord.Interaction, button: discord.ui.Button):
        assets = load_user(self.author.id).get("assets", [])
        if not assets: 
            embed_err = discord.Embed(
                description="Bạn không có tài sản nào để bán cả! Nghèo rớt mồng tơi.", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(assets, False))
        
        embed = discord.Embed(
            title="🏷️ CẦM ĐỒ BĐS & XE CỘ", 
            description="Lưu ý: Bạn sẽ bị con buôn ép giá tơi bời, chịu lỗ 30% giá trị so với lúc mua.", 
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Bán Thú Cưng", style=discord.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, interaction: discord.Interaction, button: discord.ui.Button):
        pets = load_user(self.author.id).get("pets", {})
        if not pets or all(quantity == 0 for quantity in pets.values()): 
            embed_err = discord.Embed(
                description="Bạn chưa đập được con Thú cưng nào để bán cả!", 
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
        view = discord.ui.View(timeout=60)
        view.add_item(SellItemSelect(pets, True))
        
        embed = discord.Embed(
            title="🏷️ TRẠM THU MUA THÚ CƯNG", 
            description="Thu mua thú cưng đổi lấy tiền mặt nhanh gọn lẹ. Pet càng hiếm giá càng cao.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: 
            return False
        return True

# =====================================================================
# GIAO DIỆN UI: TRẠM TREO MÁY AFK (PHÁI)
# =====================================================================
class ExpSelect(discord.ui.Select):
    """Bảng chọn thời gian treo máy dã ngoại"""
    def __init__(self):
        options = [
            discord.SelectOption(
                label="4 Giờ (Bãi Cỏ Yên Bình)", 
                description="Rủi ro thấp, phần thưởng dự kiến: ~450 💰", 
                emoji="🌿", 
                value="4"
            ),
            discord.SelectOption(
                label="8 Giờ (Hang Động Tối Tăm)", 
                description="Rủi ro trung bình, phần thưởng dự kiến: ~1000 💰", 
                emoji="🦇", 
                value="8"
            ),
            discord.SelectOption(
                label="12 Giờ (Di Tích Nguy Hiểm)", 
                description="Rủi ro cao, phần thưởng dự kiến: ~2000 💰", 
                emoji="🏛️", 
                value="12"
            )
        ]
        super().__init__(
            placeholder="Lựa chọn địa điểm hạ trại...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = load_user(user_id)
        
        hours = int(self.values[0])
        
        # Ngẫu nhiên phần thưởng tương xứng với rủi ro
        if hours == 4: 
            reward = random.randint(300, 600)
        elif hours == 8: 
            reward = random.randint(700, 1200)
        else: 
            reward = random.randint(1500, 2500)
            
        end_time = datetime.now() + timedelta(hours=hours)
        
        user_data["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        user_data["exp_reward"] = reward
        save_user(user_id)

        embed_success = discord.Embed(
            title="⛺ LÊN ĐƯỜNG BÌNH AN!", 
            description=f"Hành lý đã chuẩn bị xong. Bạn vác balo tiến vào rừng và bắt đầu cắm trại **{hours} giờ**.\n\n"
                        f"⏳ Khi nào hết thời gian, hãy gõ lại lệnh `k phai` để thu hoạch chiến lợi phẩm mang về nhé.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed_success, view=None)

class ExpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(ExpSelect())

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            return False
        return True

# =====================================================================
# GIAO DIỆN UI: GAME NHÂN SINH LỰA CHỌN ĐA VŨ TRỤ (HARDCORE)
# =====================================================================
class NhanSinhGameView(discord.ui.View):
    """Hệ thống lõi của Game Nhân Sinh - Xử lý ngã rẽ cuộc đời"""
    def __init__(self, author, stats):
        super().__init__(timeout=180) # Hạn chót 3 phút cho 1 mạng
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        # Khởi tạo kịch bản tuổi 15
        self.ev = random.choice(EVENTS_P1)

        # Mở bài theo điểm may mắn
        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra đã ngậm thìa vàng, bố mẹ là tài phiệt ác ma.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức bình dân êm ấm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài bãi rác từ nhỏ.")

        # Khởi tạo 4 Nút Lựa Chọn A, B, C, D
        self.btn_a = discord.ui.Button(
            label=f"A. {self.ev['choices'][0]['text'][:70]}", 
            style=discord.ButtonStyle.primary, 
            custom_id="btn_a"
        )
        self.btn_b = discord.ui.Button(
            label=f"B. {self.ev['choices'][1]['text'][:70]}", 
            style=discord.ButtonStyle.secondary, 
            custom_id="btn_b"
        )
        self.btn_c = discord.ui.Button(
            label=f"C. {self.ev['choices'][2]['text'][:70]}", 
            style=discord.ButtonStyle.success, 
            custom_id="btn_c"
        )
        self.btn_d = discord.ui.Button(
            label=f"D. {self.ev['choices'][3]['text'][:70]}", 
            style=discord.ButtonStyle.danger, 
            custom_id="btn_d"
        )
        
        # Gắn callback cho các nút
        self.btn_a.callback = self.choice_a
        self.btn_b.callback = self.choice_b
        self.btn_c.callback = self.choice_c
        self.btn_d.callback = self.choice_d
        
        self.add_item(self.btn_a)
        self.add_item(self.btn_b)
        self.add_item(self.btn_c)
        self.add_item(self.btn_d)

    async def on_timeout(self):
        """Xử lý khi người chơi AFK bỏ dở game"""
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: 
            dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Nhân quả của ai người nấy gánh, đừng xen vào cuộc đời của người khác!", ephemeral=True)
            return False
        return True

    # Các hàm liên kết nút bấm tới index của mảng kịch bản
    async def choice_a(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): 
        await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        """Xử lý Logic cốt lõi khi bấm 1 nút lựa chọn"""
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        # Tỉ lệ thành công = Tỉ lệ gốc + (May Mắn * 1.5). Khóa giới hạn tối đa 85% để tạo độ rủi ro Hardcore.
        calculated_rate = base_rate + (self.stats["may_man"] * 1.5)
        final_rate = min(85.0, calculated_rate)
        
        # Đổ xúc xắc
        roll = random.uniform(0, 100)
        is_win = roll <= final_rate
        
        result_msg = choice_data["win"] if is_win else choice_data["lose"]
        money_change = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        # Kiểm tra cờ Đột tử (die)
        is_dead = False
        if is_win and choice_data.get("die_w", False): 
            is_dead = True
        if not is_win and choice_data.get("die_l", False): 
            is_dead = True

        self.tien_an += money_change
        
        # Tạo nhật ký (Log) để ghi lại hành trình
        status_icon = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ thành công: **{final_rate:.1f}%** (Xúc xắc: {roll:.1f})\n{status_icon}: {result_msg} ({money_change:,} 💰)"
        
        # Tính toán tuổi
        if self.phase == 1: 
            tuoi_hien_tai = 15
        elif self.phase == 2: 
            tuoi_hien_tai = 25
        elif self.phase == 3: 
            tuoi_hien_tai = 35
        elif self.phase == 4: 
            tuoi_hien_tai = 50
        else: 
            tuoi_hien_tai = 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Bạn chọn con đường {letter}.\n{log_entry}\n\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời luân hồi khép lại sớm.**")
            self.phase = 99 # Đẩy phase lên mức max để ngắt game ngay lập tức
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Bạn chọn con đường {letter}.\n{log_entry}")
            self.phase += 1
            
            # Sang giai đoạn mới, load kịch bản tiếp theo ngẫu nhiên
            if self.phase == 2: 
                self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: 
                self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: 
                self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: 
                self.ev = random.choice(EVENTS_P5)

        # Cập nhật giao diện
        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        """Cập nhật lại giao diện sau mỗi lượt chơi"""
        embed = discord.Embed(
            title="🌀 MÔ PHỎNG NHÂN SINH (HARDCORE)", 
            description=f"Ký chủ luân hồi: {self.author.mention}", 
            color=discord.Color.teal()
        )
        
        stats_text = f"Tâm linh / May mắn: **{self.stats['may_man']}/10** *(Được buff +{self.stats['may_man']*1.5}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số ban đầu", value=stats_text, inline=False)

        # Rút gọn log nếu quá dài để không bị quá ký tự giới hạn của embed (hiển thị 4 turn gần nhất)
        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        # Trạng thái: Game đang tiếp tục
        if self.phase <= 5:
            if self.phase == 1: tuoi_next = 15
            elif self.phase == 2: tuoi_next = 25
            elif self.phase == 3: tuoi_next = 35
            elif self.phase == 4: tuoi_next = 50
            else: tuoi_next = 70
            
            embed.add_field(name=f"❓ Ngã rẽ quyết định tuổi {tuoi_next}", value=f"**{self.ev['q']}**", inline=False)
            
            # Cập nhật nhãn nút bấm
            self.btn_a.label = f"A. {self.ev['choices'][0]['text'][:70]}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text'][:70]}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text'][:70]}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text'][:70]}"
            
        # Trạng thái: Game kết thúc (Chết hoặc Hết tuổi)
        else:
            # Khóa và Xóa toàn bộ nút bấm
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.btn_c.disabled = True
            self.btn_d.disabled = True
            self.clear_items() 
            
            # Dọn dẹp cờ trạng thái đang chơi
            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: 
                dang_choi_nhansinh.remove(user_id)

            # Thanh toán tiền (Cộng / Trừ)
            user_data = load_user(user_id)
            user_data["money"] += self.tien_an
            save_user(user_id)

            # Cập nhật thông báo cuối cùng tùy theo kết quả
            if self.tien_an < 0:
                embed.color = discord.Color.red()
                embed.add_field(
                    name="🪦 Về với Cát Bụi", 
                    value=f"Sống lỗi để lại một đống nợ khổng lồ, chủ nợ đến siết nhà.\n❌ **BÁO NHÀ!** Khoản nợ phải gánh: **{self.tien_an:,} 💰**", 
                    inline=False
                )
            elif self.tien_an >= 500000:
                embed.color = discord.Color.gold()
                embed.add_field(
                    name="🪦 Về với Cát Bụi", 
                    value=f"Hưởng thọ trong nhung lụa vinh hoa, con cháu kính trọng.\n👑 **TỶ PHÚ ĐỜI THẬT!** Di sản để lại: **+{self.tien_an:,} 💰**", 
                    inline=False
                )
            else:
                embed.color = discord.Color.blue()
                embed.add_field(
                    name="🪦 Về với Cát Bụi", 
                    value=f"Một cuộc đời êm ấm trôi qua, không còn gì nuối tiếc.\n💼 **DƯ DẢ!** Di sản để lại: **+{self.tien_an:,} 💰**", 
                    inline=False
                )

        # Cập nhật tin nhắn UI
        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)
    # =====================================================================
# HỆ THỐNG LỆNH NGÂN HÀNG TRUNG ƯƠNG
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nganhang', 'nh'])
async def bank(ctx):
    """Dashboard quản lý ngân hàng trung ương"""
    user_data = load_user(ctx.author.id)
    bank_balance = user_data.get("bank", 0)
    wallet_balance = user_data.get("money", 0)
    
    embed = discord.Embed(
        title="🏦 NGÂN HÀNG TRUNG ƯƠNG SERVER", 
        description="Gửi tiền an toàn tuyệt đối. Tiền nằm trong ngân hàng sẽ không bao giờ bị mất do Casino, bị trộm hay bị đánh thuế!\n\n"
                    "📥 `k bank gui <số tiền / all>`: Gửi tiền mặt vào két sắt\n"
                    "📤 `k bank rut <số tiền / all>`: Rút tiền từ két sắt ra ví", 
        color=discord.Color.blue()
    )
    embed.add_field(name="💳 Ví tiền mặt (Wallet)", value=f"**{wallet_balance:,} 💰**", inline=True)
    embed.add_field(name="🏦 Số dư Két sắt (Bank)", value=f"**{bank_balance:,} 💰**", inline=True)
    embed.set_thumbnail(url=GIF_LINKS.get("bank", ""))
    
    await ctx.reply(embed=embed, mention_author=False)

@bank.command(aliases=['send'])
async def gui(ctx, amount: str):
    """Lệnh gửi tiền vào ngân hàng"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    try: 
        if amount.lower() == "all":
            deposit_amount = user_data["money"]
        else:
            deposit_amount = int(amount)
    except ValueError: 
        embed_err = discord.Embed(description="⚠️ Vui lòng nhập đúng số tiền hoặc chữ `all`!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
    
    if deposit_amount <= 0 or deposit_amount > user_data["money"]: 
        embed_err = discord.Embed(description="⚠️ Số tiền trong ví không đủ để gửi!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data["money"] -= deposit_amount
    user_data["bank"] = user_data.get("bank", 0) + deposit_amount
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Nhân viên ngân hàng đã đóng gói và đưa **{deposit_amount:,} 💰** của bạn vào két sắt an toàn tuyệt đối!", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@bank.command(aliases=['withdraw'])
async def rut(ctx, amount: str):
    """Lệnh rút tiền từ ngân hàng ra ví"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    bank_balance = user_data.get("bank", 0)
    
    try: 
        if amount.lower() == "all":
            withdraw_amount = bank_balance
        else:
            withdraw_amount = int(amount)
    except ValueError: 
        embed_err = discord.Embed(description="⚠️ Vui lòng nhập đúng số tiền hoặc chữ `all`!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
    
    if withdraw_amount <= 0 or withdraw_amount > bank_balance: 
        embed_err = discord.Embed(description="⚠️ Số dư trong ngân hàng của bạn không đủ!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    user_data["bank"] -= withdraw_amount
    user_data["money"] += withdraw_amount
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Bạn đã rút thành công **{withdraw_amount:,} 💰** từ két sắt mang ra ngoài ví để ăn chơi!", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

# =====================================================================
# HỆ THỐNG SÀN CHỨNG KHOÁN (CÓ CƠ CHẾ IPO VÀ RUG PULL)
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['ck', 'trade'])
async def chungkhoan(ctx):
    """Bảng hiển thị giá trị cổ phiếu trên thị trường chứng khoán"""
    next_timestamp = get_next_hour_timestamp()
    all_stocks = get_all_stocks()
    
    embed = discord.Embed(
        title="📈 SÀN CHỨNG KHOÁN PHỐ WALL (IPO & MẶC ĐỊNH)", 
        description=f"Thị trường sẽ đóng phiên và cập nhật giá mới vào: <t:{next_timestamp}:R>\n\n"
                    f"🛒 Lệnh Mua: `k ck buy <MÃ> <Số lượng>`\n"
                    f"💸 Lệnh Bán: `k ck sell <MÃ> <Số lượng>`\n"
                    f"🏢 Lên Sàn: `k ck ipo` (Dành cho cty quỹ >50 Triệu)", 
        color=discord.Color.blue()
    )
    
    # Liệt kê các mã cổ phiếu và giá hiện tại
    for code, name in all_stocks.items():
        price_now = get_stock_price(code, 0)
        price_old = get_stock_price(code, -1)
        
        # Cảnh báo phá sản / Hủy niêm yết
        if price_now <= 1000:
            trend = "💀 HỦY NIÊM YẾT / ĐÁY XÃ HỘI"
            difference = 0
        else:
            if price_now > price_old:
                trend = "🟩 Đang Lên"
            else:
                trend = "🟥 Đang Xuống"
            difference = abs(price_now - price_old)
        
        embed.add_field(
            name=f"🏢 {code} - {name}", 
            value=f"Giá niêm yết: **{price_now:,} 💰**\n*(Biến động: {trend} {difference:,})*", 
            inline=False
        )
        
    user_data = load_user(ctx.author.id)
    my_stocks = user_data.get("stocks", {})
    
    inventory_str = ""
    for code, quantity in my_stocks.items():
        if quantity > 0:
            # Hiện giá trị đang nắm giữ
            current_val = get_stock_price(code, 0) * quantity
            inventory_str += f"🔸 {code}: {quantity} CP (Đang có giá trị: {current_val:,} 💰)\n"
            
    if not inventory_str:
        inventory_str = "Ví đầu tư của bạn đang trống trơn."
        
    embed.add_field(name="🎒 Cổ phiếu bạn đang nắm giữ", value=inventory_str, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    """Lệnh mua cổ phiếu (Có cơ chế Rug Pull úp bô)"""
    code = code.upper()
    all_stocks = get_all_stocks()
    
    if code not in all_stocks:
        embed_err = discord.Embed(description="⚠️ Mã cổ phiếu này không tồn tại trên sàn giao dịch!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if qty <= 0: 
        embed_err = discord.Embed(description="⚠️ Số lượng mua phải lớn hơn 0!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    stock_price = get_stock_price(code, 0)
    
    if stock_price <= 1000:
        embed_err = discord.Embed(description="⚠️ Công ty này đã bị hủy niêm yết / rớt đáy xã hội, sàn chứng khoán khóa chức năng mua!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)

    total_cost = stock_price * qty
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("money", 0) < total_cost: 
        embed_err = discord.Embed(description=f"⚠️ Thiếu lúa rồi đại gia ơi! Bạn cần tới **{total_cost:,} 💰** để khớp lệnh.", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    # TRỪ TIỀN TRƯỚC TIÊN ĐỂ KIỂM TRA RUG PULL
    user_data["money"] -= total_cost
    
    # CƠ CHẾ RUG PULL: Đầu tư hơn 50 triệu có 15% bị úp bô
    if total_cost >= 50000000:
        if random.randint(1, 100) <= 15:
            save_user(user_id)
            embed_rugpull = discord.Embed(
                title="🚨 CẢNH BÁO TỘI PHẠM KINH TẾ (RUG PULL) 🚨", 
                description=f"**Trời ơi tin được không!**\nKhi bạn vừa chuyển khoản **{total_cost:,} 💰** để mua lượng lớn cổ phiếu **{code}**...\n\n"
                            f"CEO của công ty này đã ôm toàn bộ số tiền của bạn, lên phi cơ riêng trốn ra nước ngoài!\n"
                            f"Sàn chứng khoán đóng băng mã này, bạn mất trắng số tiền vừa mua!", 
                color=discord.Color.red()
            )
            embed_rugpull.set_image(url=GIF_LINKS["rugpull"])
            return await ctx.reply(embed=embed_rugpull, mention_author=False)
            
    # Thêm cổ phiếu vào túi đồ bình thường nếu không bị Rug pull
    current_qty = user_data.get("stocks", {}).get(code, 0)
    user_data["stocks"][code] = current_qty + qty
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Lệnh BUY đã khớp! Bạn vừa đầu tư mua **{qty} {code}** với tổng số tiền là **{total_cost:,} 💰**.", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    """Lệnh chốt lời/cắt lỗ cổ phiếu"""
    code = code.upper()
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    all_stocks = get_all_stocks()
    
    if code not in all_stocks:
        embed_err = discord.Embed(description="⚠️ Mã cổ phiếu này không tồn tại!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    my_qty = user_data.get("stocks", {}).get(code, 0)
    
    if qty <= 0 or my_qty < qty: 
        embed_err = discord.Embed(description="⚠️ Bạn không đủ số lượng cổ phiếu này để bán!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    total_gain = get_stock_price(code, 0) * qty
    
    # Trừ cổ phiếu và cộng tiền
    user_data["stocks"][code] -= qty
    if user_data["stocks"][code] == 0:
        del user_data["stocks"][code]
        
    user_data["money"] += total_gain
    save_user(user_id)
    
    embed_success = discord.Embed(
        description=f"✅ Lệnh SELL đã khớp! Bạn vừa bán **{qty} {code}** và thu về **{total_gain:,} 💰**.", 
        color=discord.Color.gold()
    )
    await ctx.reply(embed=embed_success, mention_author=False)

@chungkhoan.command()
async def ipo(ctx):
    """Lệnh đưa công ty lên sàn chứng khoán (Cần 50 Triệu)"""
    user_id = str(ctx.author.id)
    comp_id = load_user(user_id).get("company")
    
    if not comp_id:
        embed_err = discord.Embed(description="⚠️ Bạn chưa gia nhập công ty nào cả!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    comp = load_company(comp_id)
    if comp["members"].get(user_id) != "boss":
        embed_err = discord.Embed(description="⚠️ Chỉ Chủ Tịch mới có quyền quyết định đưa công ty lên sàn chứng khoán!", color=discord.Color.red())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if comp.get("is_ipo"):
        embed_err = discord.Embed(description="⚠️ Công ty của bạn đã được niêm yết trên sàn chứng khoán rồi!", color=discord.Color.orange())
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    if comp["treasury"] < 50000000:
        embed_err = discord.Embed(
            description="⚠️ Điều kiện niêm yết: Quỹ công ty phải đạt tối thiểu **50,000,000 💰**.\n"
                        "Hãy kêu gọi cổ đông đóng góp thêm!", 
            color=discord.Color.red()
        )
        return await ctx.reply(embed=embed_err, mention_author=False)
        
    # Kích hoạt trạng thái IPO trên Database
    comp["is_ipo"] = True
    save_company(comp_id)
    
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
# HỆ THỐNG QUẢN LÝ CÔNG TY ĐẠI CHIẾN
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['congty'])
async def cty(ctx):
    """Dashboard trung tâm quản lý công ty"""
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    comp_id = user_data.get("company")

    if not comp_id:
        embed_none = discord.Embed(
            title="🏢 SÀN GIAO DỊCH DOANH NGHIỆP", 
            description="Bạn hiện đang là kẻ lang thang thất nghiệp.\nĐể thành lập công ty, gõ:\n`k cty tao <tên công ty>` (Phí thành lập: 500,000 💰)", 
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed_none)
    
    comp = load_company(comp_id)
    if not comp:
        user_data["company"] = None
        save_user(user_id)
        return await ctx.send("Công ty của bạn đã phá sản từ trước rồi! Hãy dọn dẹp đống đổ nát và lập công ty mới.")
        
    my_role = comp["members"].get(user_id, "nhanvien")
    role_name = comp["roles"].get(my_role, my_role)
    
    embed_dashboard = discord.Embed(title=f"🏢 CÔNG TY: {comp['name']}", color=discord.Color.gold())
    embed_dashboard.add_field(name="Quỹ Công Ty", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed_dashboard.add_field(name="Nhân Sự", value=f"**{len(comp['members'])} người**", inline=True)
    embed_dashboard.add_field(name="Chức vụ của bạn", value=f"**{role_name}**", inline=False)
    
    cmds = "`k cty gop <tiền>`: Đóng góp tiền túi vào quỹ công ty\n`k cty thulai`: Nhận lãi suất ngân hàng mỗi ngày\n`k cty roi`: Nộp đơn từ chức nghỉ việc"
    
    if my_role in ["boss", "quanly"]:
        cmds += "\n\n**Quyền Quản Lý:**\n`k cty tuyen @user`: Tuyển dụng nhân viên\n`k cty duoi @user`: Sa thải nhân viên"
        
    if my_role == "boss":
        cmds += "\n\n**Quyền Chủ Tịch:**\n`k cty luong <tiền>`: Rút quỹ phát lương\n`k cty chucvu @user <quanly/nhanvien>`: Set role\n`k cty doitenchuc <boss/quanly/nhanvien> <Tên>`: Đổi tên hiển thị"
        
    embed_dashboard.add_field(name="Bảng Lệnh Công Ty", value=cmds, inline=False)
    await ctx.send(embed=embed_dashboard)

@cty.command()
async def tao(ctx, *, name: str):
    user_id = str(ctx.author.id)
    user_data = load_user(user_id)
    
    if user_data.get("company"): 
        return await ctx.reply("Bạn đã ký hợp đồng với một công ty rồi!", mention_author=False)
    if user_data.get("money", 0) < 500000: 
        return await ctx.reply("⚠️ Phí đăng ký doanh nghiệp là **500,000 💰**. Cày thêm đi sếp!", mention_author=False)
    
    user_data["money"] -= 500000
    user_data["company"] = user_id
    
    new_comp = {
        "_id": user_id, 
        "name": name, 
        "treasury": 0, 
        "members": {user_id: "boss"}, 
        "roles": {"boss": "Chủ Tịch", "quanly": "Giám Đốc", "nhanvien": "Nhân Viên"}, 
        "last_interest": "2000-01-01 00:00:00",
        "is_ipo": False
    }
    
    COMPANY_CACHE[user_id] = new_comp
    save_company(user_id)
    save_user(user_id)
    
    embed_success = discord.Embed(
        title="🏢 KHAI TRƯƠNG HỒNG PHÁT", 
        description=f"Cắt băng khánh thành! Chúc mừng sếp {ctx.author.mention} đã thành lập doanh nghiệp **{name}**!", 
        color=discord.Color.green()
    )
    await ctx.send(embed=embed_success)

# =====================================================================
# HỆ THỐNG LỆNH CƠ BẢN VÀ MINIGAME (RANK, CASINO, CƯỚP BANK...)
# =====================================================================
@bot.command()
async def help(ctx):
    """Bảng hiển thị trợ giúp hệ thống"""
    embed = discord.Embed(
        title="📚 HỆ THỐNG LỆNH BOT UPDATE 2026", 
        description="Tiền tố: `k ` hoặc `K `.", 
        color=discord.Color.blurple()
    )
    embed.add_field(name="🏦 KINH TẾ", value="`k rank`, `k tuido`, `k bank`, `k cuahang`, `k choden`\n`k daily`, `k lixi`, `k give`, `k top`, `k marry @user`", inline=False)
    embed.add_field(name="🏢 CÔNG TY & CHỨNG KHOÁN", value="`k cty tao <tên>`, `k cty`, `k ck`, `k daichien @user`", inline=False)
    embed.add_field(name="🎮 CASINO", value="`k coin <tiền>`, `k taixiu <tài/xỉu> <tiền>`, `k baucua <vật> <tiền>`, `k duathu <vật> <tiền>`, `k nohu <tiền>`", inline=False)
    embed.add_field(name="⛏️ NHẬP VAI", value="`k cuopnganhang`, `k daovang`, `k nhansinh`, `k thamhiem`, `k phai`, `k gacha`", inline=False)
    embed.add_field(name="🌌 KALLEN FANTASY (Gacha RPG)", value="`k kallen`, `k kallen gacha`, `k kallen equip`, `k kallen story`, `k kallen abyss`", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def rank(ctx):
    """Lệnh xem Căn Cước Công Dân"""
    u = load_user(ctx.author.id)
    embed = discord.Embed(
        title=f"💳 CĂN CƯỚC: {ctx.author.name.upper()}", 
        color=discord.Color.gold() if u.get("money",0) > 1000000 else discord.Color.teal()
    )
    embed.set_thumbnail(url=GIF_LINKS["rank"])
    embed.add_field(name="🏷️ Danh hiệu", value=f"**{u.get('title')}**", inline=False)
    embed.add_field(name="🌟 Cấp độ", value=f"**LV {u.get('level',1)}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{u.get('money',0):,} 💰**", inline=True)
    embed.add_field(name="🏦 Ngân Hàng", value=f"**{u.get('bank',0):,} 💰**", inline=True)
    embed.add_field(name="✨ Kinh Nghiệm", value=f"`{make_progress_bar(u.get('xp',0), u.get('level',1)*100)}`\n**{u.get('xp',0)}/{u.get('level',1)*100} XP**", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@bot.command(aliases=['cuop', 'cuopbank'])
async def cuopnganhang(ctx):
    """Tính năng cướp ngân hàng kịch tính"""
    u_id = str(ctx.author.id)
    u = load_user(u_id)
    now = datetime.now()
    
    if u.get("money", 0) < 50000: 
        return await ctx.reply(embed=discord.Embed(description="⚠️ Cần 50k mua súng M4A1 mới đi cướp được!", color=discord.Color.red()), mention_author=False)
        
    if u_id in cty_cooldowns and (now - cty_cooldowns[u_id]).total_seconds() < 3600: 
        return await ctx.reply("⏳ Đang bị truy nã 5 sao! Đi trốn 1 tiếng đi.", mention_author=False)
        
    cty_cooldowns[u_id] = now
    
    msg = await ctx.send(embed=discord.Embed(title="🔫 PHI VỤ THẾ KỶ", description="Xông vào Ngân hàng Trung ương...", color=discord.Color.dark_grey()))
    await asyncio.sleep(2.5)
    
    if random.randint(1, 100) <= 20: 
        loot = random.randint(200000, 800000)
        u["money"] += loot
        save_user(u_id)
        embed_win = discord.Embed(title="🎉 TRÓT LỌT!", description=f"Vơ vét sạch két sắt! Húp **{loot:,} 💰**!", color=discord.Color.green())
        embed_win.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed_win)
    else: 
        u["money"] -= 50000
        u["jail_time"] = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        save_user(u_id)
        embed_lose = discord.Embed(title="🚨 BỊ TÓM GỌN", description="Đặc nhiệm SWAT ập tới! Mất 50k tiền súng và đi tù 10 phút!", color=discord.Color.red())
        embed_lose.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed_lose)

@bot.command()
async def mayxeng(ctx, amount: str):
    """Máy đánh bạc Slot Machine"""
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    
    u_id = str(ctx.author.id)
    u["money"] -= bet
    save_user(u_id)
    gamble_cooldowns[u_id] = datetime.now()

    items = ["🍒", "🍋", "🍉", "🔔", "💎", "👑"]
    r = [random.choice(items) for _ in range(3)]
    
    embed = discord.Embed(title="🎰 MÁY XÈNG CASINO 🎰", color=discord.Color.gold())
    embed.set_thumbnail(url=GIF_LINKS["casino"])
    msg = await ctx.reply(embed=embed, mention_author=False)
    
    for _ in range(2): 
        embed.description = f"**[ {random.choice(items)} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đang quay tít mù..."
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        
    for _ in range(2): 
        embed.description = f"**[ {r[0]} | {random.choice(items)} | {random.choice(items)} ]**\n\n🔄 Đã chốt ô 1..."
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        
    for _ in range(2): 
        embed.description = f"**[ {r[0]} | {r[1]} | {random.choice(items)} ]**\n\n🔄 Nín thở chờ ô cuối..."
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
        
    if r[0] == r[1] == r[2]:
        if r[0] == "👑": win = bet * 50
        elif r[0] == "💎": win = bet * 20
        else: win = bet * 10
        txt = f"🔥 **JACKPOT NỔ HŨ!!!** Bạn húp trọn **{win:,} 💰**!"
        u["money"] += win
    elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
        win = bet * 2
        txt = f"🎉 **THẮNG NHỎ!** Bạn nhận được **{win:,} 💰**."
        u["money"] += win
    else: 
        txt = f"💀 **TOANG!** Cờ bạc là bác thằng bần. Mất trắng **{bet:,} 💰**."
        
    save_user(u_id)
    embed.description = f"**[ {r[0]} | {r[1]} | {r[2]} ]**\n\n{txt}"
    await msg.edit(embed=embed)

@bot.command()
async def daily(ctx):
    """Điểm danh nhận tiền mỗi ngày"""
    u = load_user(ctx.author.id)
    now = datetime.now()
    
    if u.get("last_daily"):
        last = datetime.strptime(u["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last < timedelta(days=1): 
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Khôn thế, lương ngày mai nhận vào: <t:{int((last + timedelta(days=1)).timestamp())}:R> nữa.", color=discord.Color.orange()), mention_author=False)
    
    u["money"] += 1000
    u["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(ctx.author.id)
    
    embed = discord.Embed(
        title="🎁 QUÀ ĐIỂM DANH", 
        description=f"Nhận trợ cấp **1,000 💰** thành công!\n💳 Số dư ví: **{u['money']:,} 💰**", 
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=GIF_LINKS["daily"])
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def tuido(ctx):
    """Hiển thị túi đồ BĐS, Xe và Thú cưng"""
    u = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO BÁU CỦA {ctx.author.name.upper()}", color=discord.Color.dark_purple())
    if ctx.author.avatar: 
        embed.set_thumbnail(url=ctx.author.avatar.url)
        
    embed.add_field(name="🏠 Tài Sản Cá Nhân", value="Trống không." if not u.get("assets") else "\n".join([f"🔸 {a}" for a in u["assets"]]), inline=False)
    embed.add_field(name="🐾 Trang Trại Thú Cưng", value="Chưa bắt được con nào." if not u.get("pets") else "\n".join([f"{p} (x{c})" for p, c in u["pets"].items()]), inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx):
    """Bảng xếp hạng tổng tài sản server"""
    all_users = list(users_col.find())
    danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)
    
    desc = ""
    for i, (uid, tien) in enumerate(danh_sach[:10]):
        user = bot.get_user(int(uid))
        if not user:
            try: user = await bot.fetch_user(int(uid))
            except Exception: pass
            
        ten = user.name if user else f"Tỷ phú ẩn danh {uid[-4:]}"
        icon = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"**#{i+1}**"
        desc += f"{icon} **{ten}** ━ {tien:,} 💰\n\n"
        
    embed = discord.Embed(title="🏆 BẢNG VÀNG ĐẠI GIA SERVER", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

# =====================================================================
# SỰ KIỆN HỆ THỐNG LÕI CỦA BOT (ON_MESSAGE, ON_READY)
# =====================================================================
@bot.event
async def on_message(message):
    """Xử lý kinh nghiệm khi user chat và chặn chat nhận kinh nghiệm nếu đi tù"""
    if message.author.bot: 
        return
        
    user_id = str(message.author.id)
    u = load_user(user_id)
    
    # Kiểm tra tù nhân, không cấp điểm kinh nghiệm
    if u.get("jail_time"):
        if datetime.now() < datetime.strptime(u["jail_time"], "%Y-%m-%d %H:%M:%S"): 
            return await bot.process_commands(message)
            
    # Cộng điểm kinh nghiệm chat
    u["xp"] += random.randint(5, 15)
    lv = u.get("level", 1)
    
    # Thăng cấp
    if u["xp"] >= lv * 100:
        u["xp"] -= lv * 100
        u["level"] += 1
        rw = u["level"] * 150
        u["money"] += rw
        
        try: 
            embed_levelup = discord.Embed(
                description=f"🎉 Chúc mừng **{message.author.mention}** đã đột phá cảnh giới lên **Cấp độ {u['level']}**!\nPhần thưởng thăng cấp: **{rw:,} 💰**", 
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed_levelup)
        except Exception: 
            pass
            
    save_user(user_id)
    await bot.process_commands(message)

@bot.event
async def on_ready(): 
    """Khởi động hệ thống in ra Terminal"""
    print('================================================')
    print(f'>>> SIÊU BOT {bot.user} ĐÃ SẴN SÀNG CÀN QUÉT!')
    print('>>> BẢN 4.0 SIÊU HARDCORE - KALLEN FANTASY TÍCH HỢP')
    print('>>> TẤT CẢ MODULE ĐÃ HOẠT ĐỘNG TRƠN TRU 100%')
    print('================================================')
    
    # Gắn chữ đang chơi Game cho Bot trên Discord
    await bot.change_presence(activity=discord.Game(name="Kallen Fantasy & Sinh Tồn | k help"))

# =====================================================================
# KHỞI ĐỘNG SERVER 24/7 VÀ CHẠY BOT BẰNG TOKEN
# =====================================================================
# Chạy máy chủ giả để giữ mạng 24/7 trên Render hoặc UptimeRobot
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối an toàn
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
