import discord
from discord.ext import commands
from keep_alive import keep_alive 
import json 
import os
import random 
import asyncio 
from datetime import datetime, timedelta 

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

coin_cooldowns = {}
nhansinh_cooldowns = {} # Thêm biến lưu thời gian chờ của Nhân Sinh

# --- CÁC HÀM XỬ LÝ SỔ TAY LEVEL ---
def load_data():
    if not os.path.exists('users.json'): return {}
    with open('users.json', 'r') as f: return json.load(f)

def save_data(data):
    with open('users.json', 'w') as f: json.dump(data, f, indent=4)

def load_config():
    if not os.path.exists('config.json'): return {}
    with open('config.json', 'r') as f: return json.load(f)

def save_config(config):
    with open('config.json', 'w') as f: json.dump(config, f, indent=4)


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
        {"tien": -800, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức một con rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt sạch tiền bạc khi bỏ chạy!"},
        {"tien": -600, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!**\nGặp ngay băng thổ phỉ khét tiếng. Chúng trói bạn vào gốc cây và lột sạch sành sanh không chừa 1 đồng."},
        {"tien": -700, "msg": "💥 **ĐẠP TRÚNG MÌN GOBLIN!**\nBÙM! Bạn đạp trúng mìn tự chế của bọn Goblin. Tiền túi bay mất để trả phí cấp cứu bệnh viện."},
        {"tien": -500, "msg": "📉 **LỪA ĐẢO ĐA CẤP!**\nBạn bị một tay thương nhân lừa mua 'Bình thuốc trường sinh' giả. Nhận ra thì hắn đã tẩu thoát, tiền mất tật mang."},
        {"tien": -1000, "msg": "🦇 **MA CÀ RỒNG!**\nBị một con ma cà rồng cắn. Trốn thoát được nhưng phải tốn một đống tiền mua máu nhân tạo để hồi sức."}
    ],
    "bad": [ 
        {"tien": -150, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"tien": -200, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi mua bông băng thuốc đỏ."},
        {"tien": -100, "msg": "🦟 **MUỖI KHỔNG LỒ!**\nBị bầy muỗi rừng khổng lồ chích sưng vù, phải đi mua thuốc mỡ bôi."},
        {"tien": -250, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước tăng lực hết hạn từ máy bán hàng tự động trong rừng. Vừa mất tiền vừa đau bụng."}
    ],
    "neutral": [ 
        {"tien": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"tien": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."},
        {"tien": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."}
    ],
    "good": [ 
        {"tien": 150, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"tien": 200, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá kha khá!"},
        {"tien": 250, "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc Bắc trả cho bạn một khoản khá hời."},
        {"tien": 300, "msg": "🙏 **NGƯỜI TỐT VIỆC TỐT!**\nNhặt được ví của một hiệp sĩ, bạn trả lại và được anh ta hậu tạ một khoản tiền."}
    ],
    "great": [ 
        {"tien": 1000, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp nhỏ và tịch thu kho báu của chúng!"},
        {"tien": 1200, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, ai ngờ đào trúng viên ngọc lục bảo thô to bằng nắm tay!"},
        {"tien": 1500, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nBạn phát hiện ra một rương kho báu vàng chóe bị chôn vùi nửa mét dưới đất. Mở ra toàn tiền!"},
        {"tien": 2000, "msg": "💍 **KIM CƯƠNG RỚT!**\nÁnh sáng lấp lánh đập vào mắt! Hóa ra là một viên kim cương tinh khiết ai đó đánh rơi trên thảm cỏ."}
    ],
    "jackpot": [ 
        {"tien": 5000, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số của ai đó đánh rơi, đem dò thì trúng giải đặc biệt! Thần tài độ rồi!!!"},
        {"tien": 10000, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Sau lớp sương mù, bạn tìm thấy hang động cất giấu kho báu huyền thoại ngàn năm. Một núi Vàng hiện ra trước mắt! Bạn thành đại gia rồi!!!"}
    ]
}


# =====================================================================
# GIAO DIỆN NHÂN SINH (PAGINATION)
# =====================================================================

class NhanSinhView(discord.ui.View):
    def __init__(self, author, embeds):
        super().__init__(timeout=180)
        self.author = author
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.btn_prev.disabled = self.current_page == 0
        self.btn_next.disabled = self.current_page == len(self.embeds) - 1

    @discord.ui.button(label="◀ Ký ức trước", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Tiếp tục sống ▶", style=discord.ButtonStyle.primary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Cuộc đời của ai người nấy tự lo đi!", ephemeral=True)
            return False
        return True


# =====================================================================
# GIAO DIỆN NÚT BẤM VÀ DROP-DOWN (SHOP & EXPLORE & AFK)
# =====================================================================

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

        data = load_data()
        user_id = str(interaction.user.id)
        old_money = data[user_id].get("money", 0)

        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [weapon_info["terrible"], weapon_info["bad"], weapon_info["neutral"], weapon_info["good"], weapon_info["great"], weapon_info["jackpot"]]
        
        category = random.choices(choices, weights=weights, k=1)[0]
        scenario = random.choice(SCENARIOS[category])
        thuong_phat = scenario["tien"]
        
        if thuong_phat < 0: data[user_id]["money"] = max(0, data[user_id]["money"] - abs(thuong_phat))
        else: data[user_id]["money"] += thuong_phat
            
        actual_change = data[user_id]["money"] - old_money
        new_session_profit = view.session_profit + actual_change
        save_data(data)
        
        profit_text = f"LÃI +{new_session_profit}" if new_session_profit > 0 else f"LỖ {new_session_profit}" if new_session_profit < 0 else "HUỀ VỐN"
        ket_qua_text = f"{scenario['msg']}\n\n💸 **Số dư hiện tại:** **{data[user_id]['money']} 💰**\n📊 **Tổng kết phiên:** **{profit_text}**"
        
        res_view = ResultView(interaction.user, new_session_profit)
        msg = await interaction.original_response()
        await msg.edit(content=ket_qua_text, view=res_view)

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
            discord.SelectOption(label="Gậy Gỗ Mục", description="Giá: 50 💰 | Tỉ lệ hên: Cực thấp (Dễ bị đấm)", emoji="🪵", value="gay_go"),
            discord.SelectOption(label="Kiếm Sắt Thường", description="Giá: 200 💰 | Tỉ lệ hên: Bình thường", emoji="🗡️", value="kiem_sat"),
            discord.SelectOption(label="Kiếm Hiệp Sĩ", description="Giá: 500 💰 | Tỉ lệ hên: Khá Cao (Dễ ăn lãi)", emoji="⚔️", value="kiem_hiep_si"),
            discord.SelectOption(label="Thánh Kiếm Mạ Vàng", description="Giá: 1500 💰 | Tỉ lệ hên: Tuyệt đỉnh (Dễ nổ hũ)", emoji="🔱", value="thanh_kiem")
        ]
        super().__init__(placeholder="Nhấp vào để mua vũ khí...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_data()
        user_id = str(interaction.user.id)
        
        weapon_id = self.values[0]
        price = WEAPON_ODDS[weapon_id]["price"]
        weapon_name = WEAPON_ODDS[weapon_id]["name"]
        
        if user_id not in data or data[user_id].get("money", 0) < price:
            await interaction.response.send_message(f"Nghèo quá! Bạn không đủ **{price} 💰** để mua {weapon_name}!", ephemeral=True)
            return
            
        data[user_id]["money"] -= price
        new_profit = self.session_profit - price 
        save_data(data)
        
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

class ExpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Phần thưởng: ~1500 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Phần thưởng: ~3500 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Phần thưởng: ~6000 💰", emoji="🏛️", value="12")
        ]
        super().__init__(placeholder="Chọn khu vực phái đi...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_data()
        user_id = str(interaction.user.id)
        
        hours = int(self.values[0])
        reward = 0
        if hours == 4: reward = random.randint(1200, 1800)
        elif hours == 8: reward = random.randint(3000, 4000)
        elif hours == 12: reward = random.randint(5500, 6500)

        end_time = datetime.now() + timedelta(hours=hours)
        
        if user_id not in data: data[user_id] = {"xp": 0, "level": 1, "money": 0}
        data[user_id]["exp_end"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        data[user_id]["exp_reward"] = reward
        save_data(data)

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
# CÁC LỆNH CƠ BẢN CỦA BOT
# =====================================================================

@bot.command()
async def help(ctx):
    bang_help = discord.Embed(
        title="📚 BẢNG LỆNH CỦA BOT 📚",
        description="Danh sách các lệnh thần thánh. Nhớ thêm chữ **k** ở đằng trước nhé.",
        color=discord.Color.blue()
    )
    bang_help.add_field(name="✨ `k rank`", value="Xem hồ sơ và số Tiền 💰 hiện tại.", inline=False)
    bang_help.add_field(name="🏆 `k top`", value="Bảng xếp hạng đại gia.", inline=False)
    bang_help.add_field(name="📅 `k daily`", value="Nhận lương hằng ngày (1000 💰).", inline=False)
    bang_help.add_field(name="🪙 `k coin <số tiền/all>`", value="Cờ bạc tung xu hồi hộp (Chờ 3s).", inline=False)
    bang_help.add_field(name="🌲 `k thamhiem`", value="Mở cửa hàng vũ khí & đi thám hiểm rừng rậm nhặt tiền.", inline=False)
    bang_help.add_field(name="⛺ `k phai`", value="Phái đi thám hiểm (Treo máy AFK kiếm tiền).", inline=False)
    bang_help.add_field(name="🌀 `k nhansinh`", value="Mô phỏng nhân sinh luân hồi (Phí vé: 100 💰). Coi chừng kiếp sau gánh nợ!", inline=False)
    bang_help.add_field(name="💸 `k give @người-nhận <số tiền>`", value="Chuyển khoản.", inline=False)
    await ctx.send(embed=bang_help)

@bot.command()
async def phai(ctx):
    data = load_data()
    user_id = str(ctx.author.id)

    if user_id not in data: data[user_id] = {"xp": 0, "level": 1, "money": 0}
    
    exp_end_str = data[user_id].get("exp_end")
    if exp_end_str:
        exp_end = datetime.strptime(exp_end_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        if now >= exp_end:
            reward = data[user_id].get("exp_reward", 1000)
            data[user_id]["money"] = data[user_id].get("money", 0) + reward
            del data[user_id]["exp_end"]
            del data[user_id]["exp_reward"]
            save_data(data)
            await ctx.send(f"🎉 {ctx.author.mention} đã vác ba lô trở về an toàn! Bạn mở túi ra và thu hoạch được **{reward} 💰**. (Số dư: **{data[user_id]['money']} 💰**)")
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

# --- MÔ PHỎNG NHÂN SINH ---
@bot.command()
async def nhansinh(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    phi = 100
    now = datetime.now()

    # Kiểm tra thời gian chờ 5 giây
    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5:
        giay_con_lai = int(5 - (now - nhansinh_cooldowns[user_id]).total_seconds())
        await ctx.send(f"⏳ Linh hồn bạn vừa mới luân hồi, cần nghỉ ngơi! Đợi **{giay_con_lai} giây** nữa mới được đầu thai tiếp.")
        return

    if user_id not in data: data[user_id] = {"xp": 0, "level": 1, "money": 0}
    if data[user_id].get("money", 0) < phi:
        await ctx.send(f"Phí cấp thẻ lên Tàu Astral luân hồi là **{phi} 💰**. Nợ nần hay nghèo rớt mồng tơi thì không có cửa đi đầu thai đâu!")
        return

    # Trừ phí vé và đặt lại thời gian chờ
    data[user_id]["money"] -= phi
    nhansinh_cooldowns[user_id] = now

    # Tạo chỉ số ngẫu nhiên
    gia_the = random.randint(1, 10)
    tri_tue = random.randint(1, 10)
    nhan_sac = random.randint(1, 10)
    may_man = random.randint(1, 10)

    # PAGE 1: KHỞI ĐẦU (0 - 15 TUỔI)
    tuoi_0 = random.choice(["Sinh ra ngậm thìa vàng ở Belobog khu Tầng Trên, có quản gia chăm bẵm.", "Sinh ra là thiếu gia tài phiệt, ngày thôi nôi bố mẹ tặng luôn một tinh cầu."]) if gia_the >= 8 else random.choice(["Sinh ra trong gia đình bình thường, sống êm ấm qua ngày.", "Tuổi thơ êm đềm ở một làng quê hẻo lánh."]) if gia_the >= 4 else random.choice(["Sinh ra dưới gầm cầu, tuổi thơ cơ cực đi nhặt ve chai.", "Ký ức đầu đời là bị bỏ rơi trước cửa Ngân Hàng Bắc Quốc."])
    tuoi_10 = "Được cử đi du học nước ngoài từ nhỏ, học đánh đàn piano." if gia_the >= 8 else "Hay trốn mẹ ra quán net chơi điện tử bị đánh đòn." if tri_tue < 5 else "Là lớp trưởng gương mẫu, học đều các môn."
    tuoi_15 = "Dậy thì thành công, nhan sắc nở rộ làm bao người xao xuyến." if nhan_sac >= 8 else "Mặt mọc đầy mụn, thân hình cò hương, đi học hay bị trêu chọc." if nhan_sac <= 3 else "Phát triển bình thường, không có gì nổi bật."

    # PAGE 2: THANH XUÂN (16 - 25 TUỔI)
    tuoi_18 = "Đậu thủ khoa kỳ thi Học Viện Giáo Viện, được vinh danh toàn cõi." if tri_tue >= 8 else "Vừa đủ điểm đậu vào một trường đại học tầm trung." if tri_tue >= 5 else "Trượt đại học, cất bước đi làm công nhân vệ sinh."
    tuoi_22 = "Bắt đầu làm KOL Tóp Tóp, nổi tiếng nhờ gương mặt không góc chết." if nhan_sac >= 8 else "Cắm mặt vào code rụng hết cả tóc, lấy được cái bằng xuất sắc nhưng ế chỏng vó." if tri_tue >= 7 else "Tốt nghiệp với tấm bằng trung bình, rải CV 50 công ty không ai nhận."
    tuoi_25 = "Trúng tuyển làm nhân viên chính thức của Công ty Hành Tinh Hòa Bình (IPC)." if may_man >= 8 else "Khởi nghiệp bán trà đá vỉa hè, thu nhập bấp bênh." if tri_tue < 5 else "Làm nhân viên văn phòng 9-to-5, ngày nào cũng chạy deadline sấp mặt."

    # PAGE 3: LẬP NGHIỆP & BIẾN CỐ (26 - 40 TUỔI)
    tuoi_28 = "Đầu tư vào cổ phiếu IPC trúng mánh, tài sản nhân 10 lần!" if may_man >= 8 else "Dính bẫy gacha, nạp sạch tiền tiết kiệm để quay Nón Ánh Sáng nhưng toàn rớt đồ 3 sao." if may_man <= 3 else "Kết hôn với thanh mai trúc mã, mua được căn chung cư trả góp."
    tuoi_35 = "Được thăng chức làm Giám Đốc Khu Vực, thâu tóm nhiều bất động sản." if tri_tue >= 8 else "Công việc ổn định, bắt đầu có bụng bia và đau mỏi vai gáy." if tri_tue >= 5 else "Tin bạn thân hùn vốn mở quán cafe chó mèo, dẹp tiệm sau 3 tháng."
    
    if may_man <= 2:
        tuoi_40 = "🚨 Lòng tham trỗi dậy, bạn vay nóng tín dụng đen đu đỉnh coin. Thị trường sập, bạn vỡ nợ, giang hồ siết nhà!"
        tien_thuong = random.randint(-50000, -20000) 
    elif gia_the >= 8 and tri_tue <= 4:
        tuoi_40 = "🚨 Phá gia chi tử! Bạn ăn chơi trác táng, đốt sạch gia tài bố mẹ để lại vào sòng bài tại Penacony."
        tien_thuong = random.randint(-10000, -5000) 
    elif tri_tue >= 8 and may_man >= 8:
        tuoi_40 = "🌟 Sáng lập kỳ lân công nghệ mới. Tập đoàn được định giá hàng tỷ USD. Bạn lọt top Forbes!"
        tien_thuong = random.randint(20000, 50000) 
    else:
        tuoi_40 = "Vẫn tiếp tục guồng quay cuộc sống, đi làm rước con, tằn tiện chi tiêu qua ngày."
        tien_thuong = random.randint(500, 3000) 

    # PAGE 4: TRUNG NIÊN (41 - 60 TUỔI)
    tuoi_50 = "Chuyển nhượng công ty, xách vali lên đi du lịch vòng quanh Teyvat." if tien_thuong > 10000 else "Trốn chui trốn lủi vì chủ nợ tìm đến tận nhà đòi mạng." if tien_thuong < 0 else "Được con cái mua tặng cái máy massage lưng, cuộc sống bình lặng."
    tuoi_60 = "Nằm võng uống trà chiều, thỉnh thoảng đi đánh golf cùng giới thượng lưu." if tien_thuong > 10000 else "Còng lưng đi nhặt ve chai trả nợ lãi ngày." if tien_thuong < 0 else "Tổ chức tiệc mừng thọ 60 tuổi, quây quần bên cháu chắt."

    # PAGE 5: TỔNG KẾT
    if tien_thuong < 0:
        cuoi_doi = "Oanh liệt một thời, cuối đời làm bạn với vỉa hè và đống giấy nợ bủa vây."
        ket_qua_chot = f"❌ **BÁO NHÀ!** Bạn để lại khoản nợ khổng lồ: **{tien_thuong} 💰**\n*(Lưu ý: Hệ thống đã trừ thẳng vào số dư của bạn. Đời này ăn chơi, kiếp sau đi làm `k daily` mà trả nợ nha!)*"
    elif tien_thuong > 10000:
        cuoi_doi = "Hưởng thọ trong biệt thự dát vàng. Bạn mỉm cười nhắm mắt, viên mãn trọn kiếp người."
        ket_qua_chot = f"👑 **ĐẠI PHÚ HÀO!** Con cháu nhận được gia tài: **+{tien_thuong} 💰**"
    else:
        cuoi_doi = "Sinh lão bệnh tử là lẽ thường. Bạn nhắm mắt xuôi tay trên chiếc giường quen thuộc."
        ket_qua_chot = f"💼 **DƯ DẢ!** Di chúc để lại cho kiếp sau: **+{tien_thuong} 💰**"

    # ÁP DỤNG TIỀN / NỢ CHO NGƯỜI CHƠI (Cho phép âm tiền)
    data[user_id]["money"] += tien_thuong
    save_data(data)

    embeds = []
    e1 = discord.Embed(title="[Trang 1/5] Khởi Đầu Nhân Sinh 🌱", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.purple())
    e1.add_field(name="📊 Chỉ số linh hồn", value=f"Gia thế: **{gia_the}/10** | Trí tuệ: **{tri_tue}/10**\nNhan sắc: **{nhan_sac}/10** | May mắn: **{may_man}/10**", inline=False)
    e1.add_field(name="👶 Tuổi 0", value=tuoi_0, inline=False)
    e1.add_field(name="🏃 Tuổi 10", value=tuoi_10, inline=False)
    e1.add_field(name="🏫 Tuổi 15", value=tuoi_15, inline=False)
    embeds.append(e1)

    e2 = discord.Embed(title="[Trang 2/5] Thời Thanh Xuân 🎓", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.blue())
    e2.add_field(name="🎓 Tuổi 18", value=tuoi_18, inline=False)
    e2.add_field(name="💼 Tuổi 22", value=tuoi_22, inline=False)
    e2.add_field(name="🏢 Tuổi 25", value=tuoi_25, inline=False)
    embeds.append(e2)

    e3 = discord.Embed(title="[Trang 3/5] Lập Nghiệp & Biến Cố 🌪️", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.orange())
    e3.add_field(name="💍 Tuổi 28", value=tuoi_28, inline=False)
    e3.add_field(name="👔 Tuổi 35", value=tuoi_35, inline=False)
    e3.add_field(name="⚠️ Tuổi 40", value=tuoi_40, inline=False)
    embeds.append(e3)

    e4 = discord.Embed(title="[Trang 4/5] Tuổi Xế Chiều ☕", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.dark_gray())
    e4.add_field(name="🩺 Tuổi 50", value=tuoi_50, inline=False)
    e4.add_field(name="🦯 Tuổi 60", value=tuoi_60, inline=False)
    embeds.append(e4)

    e5 = discord.Embed(title="[Trang 5/5] Về Cát Bụi 🪦", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.red())
    e5.add_field(name="🪦 Cuối đời", value=cuoi_doi, inline=False)
    e5.add_field(name="💸 TỔNG KẾT LUÂN HỒI", value=f"{ket_qua_chot}\n\n💳 Số dư thực tế hiện tại của bạn: **{data[user_id]['money']} 💰**", inline=False)
    embeds.append(e5)

    view = NhanSinhView(ctx.author, embeds)
    await ctx.send(embed=embeds[0], view=view)


@bot.command()
async def daily(ctx):
    data = load_data()
    user_id = str(ctx.author.id)

    if user_id not in data: data[user_id] = {"xp": 0, "level": 1, "money": 0}
    if "money" not in data[user_id]: data[user_id]["money"] = 0

    now = datetime.now()
    last_daily_str = data[user_id].get("last_daily")
    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            time_left = timedelta(days=1) - (now - last_daily)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"⏳ Tham lam vậy! Trở lại sau **{hours} giờ {minutes} phút** nữa để nhận lương tiếp nhé.")
            return

    data[user_id]["money"] += 1000
    data[user_id]["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    if data[user_id]["money"] < 0:
        await ctx.send(f"🎁 Bạn nhận được **1000 💰** tiền công!\n⚠️ Hệ thống đã siết nợ tự động! Bạn vẫn còn đang nợ **{data[user_id]['money']} 💰**.")
    else:
        await ctx.send(f"🎁 Bạn nhận được **1000 💰** tiền công! (Số dư: **{data[user_id]['money']} 💰**)")

@bot.command()
async def top(ctx):
    data = load_data()
    danh_sach_dai_gia = [(u_id, thong_tin.get("money", 0)) for u_id, thong_tin in data.items()]
    danh_sach_dai_gia.sort(key=lambda x: x[1], reverse=True)
    
    bang_xep_hang = discord.Embed(title="🏆 TOP ĐẠI GIA SERVER 🏆", color=discord.Color.gold())
    thu_hang = 1
    
    top_10 = danh_sach_dai_gia[:10]
    
    for user_id, tien in top_10:
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
    data = load_data()
    user_id = str(ctx.author.id)
    now = datetime.now()

    if user_id in coin_cooldowns and (now - coin_cooldowns[user_id]).total_seconds() < 3:
        await ctx.send(f"⏳ Máu cờ bạc nổi lên à? Đợi {int(3 - (now - coin_cooldowns[user_id]).total_seconds())}s nữa nhé!")
        return

    if user_id not in data or data[user_id].get("money", 0) <= 0:
        if data.get(user_id, {}).get("money", 0) < 0:
            await ctx.send("Tài khoản đang **nợ nần chồng chất** mà dám vào casino à? Đi cày `k daily` hoặc `k phai` trả nợ ngay!")
        else:
            await ctx.send("Túi rỗng tếch mà đòi cá cược! Chạy `k daily` đi.")
        return

    tien_hien_tai = data[user_id]["money"]
    try: bet = tien_hien_tai if amount.lower() == "all" else int(amount)
    except: return await ctx.send("Số cược không hợp lệ!")

    if bet <= 0 or bet > tien_hien_tai:
        return await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai} 💰**.")

    data[user_id]["money"] -= bet
    save_data(data)
    coin_cooldowns[user_id] = now

    msg = await ctx.send(f"🪙 {ctx.author.mention} ném **{bet} 💰** lên trời...")
    await asyncio.sleep(1) 
    await msg.edit(content=f"🪙 {ctx.author.mention} ném **{bet} 💰** lên trời...\n🔄 Đồng xu lộn nhào...")
    await asyncio.sleep(1) 
    await msg.edit(content=f"🪙 {ctx.author.mention} ném **{bet} 💰** lên trời...\n🔄 Đồng xu lộn nhào...\n💥 Rơi rầm xuống đất...")
    await asyncio.sleep(1) 

    data = load_data() 
    if random.choice(["thắng", "thua"]) == "thắng":
        data[user_id]["money"] += (bet * 2)
        save_data(data)
        await msg.edit(content=f"🪙 **MẶT NGỬA!**\n🎉 {ctx.author.mention} húp trọn **{bet * 2} 💰**! (Dư: **{data[user_id]['money']} 💰**)")
    else:
        await msg.edit(content=f"🪙 **MẶT SẤP!**\n💀 Nhờn! {ctx.author.mention} ra gầm cầu ngủ! Mất **{bet} 💰**. (Dư: **{data[user_id]['money']} 💰**)")

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    data = load_data()
    n_gui, n_nhan = str(ctx.author.id), str(member.id)
    if amount <= 0 or data.get(n_gui, {}).get("money", 0) < amount or n_gui == n_nhan:
        return await ctx.send("Giao dịch lỗi (Tiền âm, không đủ tiền hoặc tự chuyển cho mình).")

    if n_nhan not in data: data[n_nhan] = {"xp": 0, "level": 1, "money": 0}
    data[n_gui]["money"] -= amount
    data[n_nhan]["money"] += amount
    save_data(data)
    await ctx.send(f"💸 {ctx.author.mention} đã chuyển {member.mention} **{amount} 💰**.")

@bot.command()
@commands.has_permissions(administrator=True) 
async def setkenh(ctx, kenh: discord.TextChannel):
    config = load_config()
    config[str(ctx.guild.id)] = kenh.id
    save_config(config)
    await ctx.send(f'✅ Đã lưu kênh báo lên cấp: {kenh.mention}!')

@bot.command()
async def rank(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    if user_id in data:
        lv, xp, tien = data[user_id].get("level", 1), data[user_id].get("xp", 0), data[user_id].get("money", 0)
        
        khung_mau = discord.Color.red() if tien < 0 else discord.Color.green()
        
        embed = discord.Embed(title=f"Hồ sơ của {ctx.author.name}", color=khung_mau)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Cấp độ", value=f"**{lv}**", inline=True)
        embed.add_field(name="Kinh nghiệm", value=f"**{xp}/{lv*100} XP**", inline=True)
        
        tien_text = f"**{tien} 💰** (ĐANG MANG NỢ)" if tien < 0 else f"**{tien} 💰**"
        embed.add_field(name="Tài sản", value=tien_text, inline=False)
        await ctx.send(embed=embed)
    else: await ctx.send("Chưa có hồ sơ!")

@bot.event
async def on_message(message):
    if message.author.bot: return
    data = load_data()
    u_id = str(message.author.id)

    if u_id not in data: data[u_id] = {"xp": 0, "level": 1, "money": 0}
    data[u_id]["xp"] += random.randint(5, 15)

    if data[u_id]["xp"] >= data[u_id]["level"] * 100:
        data[u_id]["xp"] -= data[u_id]["level"] * 100
        data[u_id]["level"] += 1
        thuong = data[u_id]["level"] * 500
        data[u_id]["money"] += thuong
        
        tb = discord.Embed(title="🎉 LÊN CẤP! 🎉", description=f'{message.author.mention} đạt Cấp {data[u_id]["level"]}!\nThưởng: **{thuong} 💰**', color=discord.Color.gold())
        kenh_id = load_config().get(str(message.guild.id))
        k = bot.get_channel(kenh_id) if kenh_id else message.channel
        if k: await k.send(embed=tb)

    save_data(data)
    await bot.process_commands(message)

@bot.event
async def on_ready(): print(f'{bot.user} đã lên mạng và sẵn sàng!')

keep_alive() 

# Hai nửa mã Token của bạn
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GVIyrV.'
nua_sau = 'j8oLKlNxSTcHIDBFjQ_yjQtlJADTrzn4abcKds'
bot.run(nua_dau + nua_sau)
