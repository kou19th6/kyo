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
# HỆ THỐNG DATA: TỈ LỆ VŨ KHÍ & 50 KỊCH BẢN THÁM HIỂM
# =====================================================================

# Tỉ lệ % tương ứng với giá tiền vũ khí
WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "Gậy Gỗ Mục", "terrible": 20, "bad": 40, "neutral": 20, "good": 15, "great": 5, "jackpot": 0},
    "kiem_sat": {"price": 200, "name": "Kiếm Sắt Thường", "terrible": 10, "bad": 25, "neutral": 20, "good": 30, "great": 12, "jackpot": 3},
    "kiem_hiep_si": {"price": 500, "name": "Kiếm Hiệp Sĩ", "terrible": 5, "bad": 15, "neutral": 15, "good": 35, "great": 20, "jackpot": 10},
    "thanh_kiem": {"price": 1500, "name": "Thánh Kiếm Truyền Thuyết", "terrible": 0, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 20}
}

# TỔNG CỘNG 50 TRƯỜNG HỢP NGẪU NHIÊN
SCENARIOS = {
    "terrible": [ # Trừ siêu nặng (8 trường hợp)
        {"tien": -800, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức một con rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt sạch tiền bạc khi bỏ chạy!"},
        {"tien": -600, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!**\nGặp ngay băng thổ phỉ khét tiếng. Chúng trói bạn vào gốc cây và lột sạch sành sanh không chừa 1 đồng."},
        {"tien": -700, "msg": "💥 **ĐẠP TRÚNG MÌN GOBLIN!**\nBÙM! Bạn đạp trúng mìn tự chế của bọn Goblin. Tiền túi bay mất để trả phí cấp cứu bệnh viện."},
        {"tien": -500, "msg": "📉 **LỪA ĐẢO ĐA CẤP!**\nBạn bị một tay thương nhân lừa mua 'Bình thuốc trường sinh' giả. Nhận ra thì hắn đã tẩu thoát, tiền mất tật mang."},
        {"tien": -1000, "msg": "🦇 **MA CÀ RỒNG!**\nBị một con ma cà rồng cắn. Trốn thoát được nhưng phải tốn một đống tiền mua máu nhân tạo để hồi sức."},
        {"tien": -900, "msg": "🕳️ **RỚT XUỐNG VỰC THẲM!**\nTrượt chân rớt xuống cái hố không đáy. Bạn phải tốn tiền thuê trực thăng cứu hộ kéo lên."},
        {"tien": -650, "msg": "👮 **KIỂM LÂM BẮT QUẢ TANG!**\nBạn bị phạt nặng vì vi phạm luật bảo vệ rừng, tội tàng trữ vũ khí trái phép."},
        {"tien": -850, "msg": "🐅 **LẠC VÀO HANG CỌP!**\nVừa thò đầu vào lùm cây thì thấy mẹ con nhà cọp đang lườm bạn. Phải quăng luôn cái ví tiền để đánh lạc hướng trốn thoát!"}
    ],
    "bad": [ # Trừ nhẹ & vừa (12 trường hợp)
        {"tien": -150, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"tien": -200, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi mua bông băng thuốc đỏ."},
        {"tien": -100, "msg": "🦟 **MUỖI KHỔNG LỒ!**\nBị bầy muỗi rừng khổng lồ chích sưng vù, phải đi mua thuốc mỡ bôi."},
        {"tien": -250, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước tăng lực hết hạn từ máy bán hàng tự động trong rừng. Vừa mất tiền vừa đau bụng."},
        {"tien": -300, "msg": "🐗 **LỢN RỪNG HÚC!**\nCon lợn rừng to đùng lao tới húc bạn văng vào vách đá. Rớt mấy đồng xu khỏi túi."},
        {"tien": -120, "msg": "🍜 **ĐÓI BỤNG QUÁ!**\nLạc đường đói lả, bạn đành mua gói mì tôm chém giá gấp 10 lần của ông chú bán dạo."},
        {"tien": -80, "msg": "👖 **RÁCH QUẦN!**\nMóc vào bụi gai sắc nhọn làm rách toạc cái quần. Tốn tiền đi tiệm may vá lại."},
        {"tien": -180, "msg": "🌊 **TRƯỢT CHÂN XUỐNG SUỐI!**\nBạn ngã tùm xuống suối, nước cuốn trôi đi một vài đồng tiền lấp lánh."},
        {"tien": -90, "msg": "🦅 **QUẠ CẮP ĐỒ!**\nCon quạ đen nhầm đồng xu của bạn là đồ trang sức, nó quắp bay lên trời mất tiêu."},
        {"tien": -220, "msg": "💩 **RỚT XUỐNG ĐẦM LẦY!**\nĐạp nhầm hố bùn bốc mùi hôi thối. Tốn đống tiền đi tiệm giặt sấy cao cấp mới hết mùi."},
        {"tien": -200, "msg": "🗺️ **BẢN ĐỒ FAKE!**\nMua phải bản đồ kho báu giả mạo. Đào nửa ngày trời toàn rác, tiền ngu không lấy lại được."},
        {"tien": -150, "msg": "👻 **MA NHÁT!**\nMột bóng trắng bay xẹt qua làm bạn giật mình đánh rơi một nắm tiền."}
    ],
    "neutral": [ # Không mất không được (5 trường hợp)
        {"tien": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"tien": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."},
        {"tien": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."},
        {"tien": 0, "msg": "🍃 **GIÓ THỔI HIU HIU...**\nKhông có biến gì xảy ra. Có vẻ bạn đã chọn nhầm lùm cây an toàn."},
        {"tien": 0, "msg": "🐜 **TỔ KIẾN!**\nChỉ là một tổ kiến khổng lồ. Tốt nhất là không nên đụng vào."}
    ],
    "good": [ # Được ít tiền (15 trường hợp)
        {"tien": 150, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"tien": 200, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá kha khá!"},
        {"tien": 250, "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc Bắc trả cho bạn một khoản khá hời."},
        {"tien": 120, "msg": "⚙️ **ĐỒNG NÁT!**\nĐào được đống bánh răng bằng đồng cũ rích, đem bán ve chai cũng được chút đỉnh."},
        {"tien": 300, "msg": "🙏 **NGƯỜI TỐT VIỆC TỐT!**\nNhặt được ví của một hiệp sĩ, bạn trả lại và được anh ta hậu tạ một khoản tiền."},
        {"tien": 180, "msg": "👵 **BÀ LÃO ĐI LẠC!**\nGiúp một bà cụ xách đồ ra khỏi rừng, bà cho bạn tiền tiêu vặt."},
        {"tien": 100, "msg": "🌳 **DƯỚI GỐC CÂY!**\nTình cờ đá chân dưới gốc cây cổ thụ, phát hiện vài đồng tiền bị vùi lấp."},
        {"tien": 220, "msg": "🦋 **BƯỚM PHÁT SÁNG!**\nBắt được một con bướm dạ quang quý hiếm, bán cho nhà côn trùng học."},
        {"tien": 350, "msg": "🍯 **TỔ ONG MẬT!**\nLiều mạng hun khói lấy được tảng mật ong rừng cực ngon. Đem bán cháy hàng!"},
        {"tien": 160, "msg": "🗡️ **KIẾM GỈ!**\nThấy một thanh kiếm gãy bỏ hoang, đem bán cân ký sắt vụn cho lò rèn."},
        {"tien": 400, "msg": "🐕 **CỨU CÚN CON!**\nGiải cứu chú chó đi lạc của phú ông khỏi bẫy thú. Phú ông thưởng hậu hĩnh!"},
        {"tien": 280, "msg": "🍓 **QUẢ NGỌT!**\nHái được một chùm quả dại thơm lừng. Chủ nhà hàng 5 sao mua lại để làm món tráng miệng."},
        {"tien": 320, "msg": "🛒 **THƯƠNG NHÂN GẶP NẠN!**\nGiúp một thương nhân đẩy chiếc xe bò bị sa lầy, ông ấy trả công bạn sòng phẳng."},
        {"tien": 450, "msg": "💍 **NHẪN BẠC!**\nPhát hiện một chiếc nhẫn bạc nhỏ xíu mắc trên cành cây. Đem bán tiệm vàng cũng được giá."},
        {"tien": 500, "msg": "📚 **SÁCH KỸ NĂNG CŨ!**\nTìm thấy bí kíp võ công cũ rách bươm, bán lại cho lính đánh thuê được một món!"}
    ],
    "great": [ # Được nhiều tiền (8 trường hợp)
        {"tien": 1000, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp nhỏ và tịch thu kho báu của chúng!"},
        {"tien": 1200, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, ai ngờ đào trúng viên ngọc lục bảo thô to bằng nắm tay!"},
        {"tien": 1500, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nBạn phát hiện ra một rương kho báu vàng chóe bị chôn vùi nửa mét dưới đất. Mở ra toàn tiền!"},
        {"tien": 1800, "msg": "🤵 **ĐẠI GIA ĐI LẠC!**\nGặp một gã quý tộc đi săn bị lạc đường. Dẫn hắn ra khỏi rừng và nhận được phong bì dày cộp!"},
        {"tien": 1300, "msg": "⛏️ **MỎ QUẶNG HIẾM!**\nPhát hiện ra hang động chứa đầy quặng tinh thể. Kịp đập vài cục đem về thành phố bán giá cao."},
        {"tien": 2000, "msg": "💍 **KIM CƯƠNG RỚT!**\nÁnh sáng lấp lánh đập vào mắt! Hóa ra là một viên kim cương tinh khiết ai đó đánh rơi trên thảm cỏ."},
        {"tien": 1600, "msg": "🦄 **SỪNG KỲ LÂN!**\nBạn tình cờ nhặt được chiếc sừng gãy của một sinh vật huyền bí. Giới pháp sư tranh nhau mua giá trên trời!"},
        {"tien": 2500, "msg": "👸 **GIẢI CỨU CÔNG CHÚA!**\nĐuổi được bầy sói đang tấn công cỗ xe ngựa của vương quốc. Nhà vua phái người mang vàng đến tạ ơn!"}
    ],
    "jackpot": [ # Nổ hũ siêu to (2 trường hợp)
        {"tien": 5000, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số của ai đó đánh rơi, đem dò thì trúng giải đặc biệt! Thần tài độ rồi!!!"},
        {"tien": 10000, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Sau lớp sương mù, bạn tìm thấy hang động cất giấu kho báu huyền thoại ngàn năm. Một núi Vàng hiện ra trước mắt! Bạn thành đại gia rồi!!!"}
    ]
}

# =====================================================================
# GIAO DIỆN NÚT BẤM VÀ DROP-DOWN (SHOP VÀ CHƠI)
# =====================================================================

class BushButton(discord.ui.Button):
    def __init__(self, label, style, custom_id):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        weapon_id = view.weapon_val
        weapon_info = WEAPON_ODDS[weapon_id]
        
        # Vô hiệu hoá tất cả nút bấm để khỏi ai spam
        for child in view.children:
            child.disabled = True

        await interaction.response.edit_message(content=f"🗡️ {interaction.user.mention} cầm **{weapon_info['name']}** vạch {self.label} ra...\nĐợi một chút...", view=view)
        await asyncio.sleep(2)

        data = load_data()
        user_id = str(interaction.user.id)

        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [weapon_info["terrible"], weapon_info["bad"], weapon_info["neutral"], 
                   weapon_info["good"], weapon_info["great"], weapon_info["jackpot"]]
        
        category = random.choices(choices, weights=weights, k=1)[0]
        scenario = random.choice(SCENARIOS[category])
        thuong_phat = scenario["tien"]
        
        if thuong_phat < 0:
            data[user_id]["money"] = max(0, data[user_id]["money"] - abs(thuong_phat))
        else:
            data[user_id]["money"] += thuong_phat
            
        save_data(data)
        ket_qua_text = f"{scenario['msg']}\n\n💸 **Số dư hiện tại:** **{data[user_id]['money']} 💰**"
        
        msg = await interaction.original_response()
        await msg.edit(content=ket_qua_text, view=view)

class BushView(discord.ui.View):
    def __init__(self, author, weapon_val):
        super().__init__(timeout=60)
        self.author = author
        self.weapon_val = weapon_val
        for i in range(1, 6):
            self.add_item(BushButton(label=f"Lùm Cây {i}", style=discord.ButtonStyle.success, custom_id=f"bush_{i}"))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Tránh ra, lùm cây này tôi giành rồi!", ephemeral=True)
            return False
        return True

class WeaponSelect(discord.ui.Select):
    def __init__(self):
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
        save_data(data)
        
        view = BushView(interaction.user, weapon_id)
        text = f"🌲 **KHU RỪNG KỲ BÍ ĐÃ MỞ** 🌲\n\n*Trạng thái: Đã tốn {price} 💰 trang bị {weapon_name}*\n\nSương mù rạp xuống... Bạn thấy **5 Lùm Cây** đang rung rinh. Bạn linh cảm kho báu (hay xui xẻo) nằm ở đâu? Bấm chọn đi!"
        await interaction.response.edit_message(content=text, embed=None, view=view)

class ShopView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(WeaponSelect())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Ai gọi lệnh thì người đó mua, đừng có giành!", ephemeral=True)
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
    bang_help.add_field(name="🌲 `k thiemhiem`", value="Mở cửa hàng vũ khí & đi thám hiểm rừng rậm nhặt tiền.", inline=False)
    bang_help.add_field(name="💸 `k give @người-nhận <số tiền>`", value="Chuyển khoản.", inline=False)
    bang_help.add_field(name="⚙️ `k setkenh #tên-kênh`", value="(Quản trị viên) Chỉnh kênh thông báo lên cấp.", inline=False)
    await ctx.send(embed=bang_help)

@bot.command(aliases=['sansoi']) # Vẫn nhận k sansoi hoặc k thamhiem
async def thamhiem(ctx):
    shop_embed = discord.Embed(
        title="🛒 TRẠM TẾP TẾ THÁM HIỂM 🛒",
        description="Chào mừng đến với hội Thám Hiểm! Để vào Khu Rừng Kỳ Bí, bạn cần vũ khí. Chơi đồ xịn thì trúng mánh lớn, cầm cành cây thì dễ ăn đòn.\n\n👇 **HÃY CLICK VÀO THANH MENU BÊN DƯỚI ĐỂ CHỌN MUA** 👇",
        color=discord.Color.dark_red()
    )
    view = ShopView(ctx.author)
    await ctx.send(embed=shop_embed, view=view)

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
    await ctx.send(f"🎁 Bạn nhận được **1000 💰** tiền công! (Số dư: **{data[user_id]['money']} 💰**)")

@bot.command()
async def top(ctx):
    data = load_data()
    danh_sach_dai_gia = [(u_id, thong_tin.get("money", 0)) for u_id, thong_tin in data.items()]
    danh_sach_dai_gia.sort(key=lambda x: x[1], reverse=True)
    
    bang_xep_hang = discord.Embed(title="🏆 TOP ĐẠI GIA SERVER 🏆", color=discord.Color.gold())
    thu_hang = 1
    for user_id, tien in danh_sach_dai_gia[:10]:
        user = bot.get_user(int(user_id))
        ten = user.name if user else f"Ẩn danh ({user_id})"
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
        embed = discord.Embed(title=f"Hồ sơ của {ctx.author.name}", color=discord.Color.green())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Cấp độ", value=f"**{lv}**", inline=True)
        embed.add_field(name="Kinh nghiệm", value=f"**{xp}/{lv*100} XP**", inline=True)
        embed.add_field(name="Tài sản", value=f"**{tien} 💰**", inline=False)
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
