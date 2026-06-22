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

# Biến lưu trữ thời gian chờ 3 giây của lệnh coin
coin_cooldowns = {}

# --- CÁC HÀM XỬ LÝ SỔ TAY LEVEL ---
def load_data():
    if not os.path.exists('users.json'):
        return {}
    with open('users.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('users.json', 'w') as f:
        json.dump(data, f, indent=4)

def load_config():
    if not os.path.exists('config.json'):
        return {}
    with open('config.json', 'r') as f:
        return json.load(f)

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

# --- LỆNH: BẢNG HƯỚNG DẪN (HELP) ---
@bot.command()
async def help(ctx):
    bang_help = discord.Embed(
        title="📚 BẢNG LỆNH CỦA BOT 📚",
        description="Dưới đây là danh sách các lệnh bạn có thể sử dụng. Nhớ thêm chữ **k** ở đằng trước nhé.",
        color=discord.Color.blue()
    )
    bang_help.add_field(name="✨ `k rank`", value="Xem hồ sơ: Cấp độ, XP và số TIỀN 💰 hiện tại.", inline=False)
    bang_help.add_field(name="🏆 `k top`", value="Xem bảng xếp hạng Top 10 đại gia giàu nhất server.", inline=False)
    bang_help.add_field(name="📅 `k daily`", value="Hoàn thành ủy thác hằng ngày để nhận lương.", inline=False)
    bang_help.add_field(name="🪙 `k coin <số tiền>` hoặc `k coin all`", value="Tung đồng xu sấp ngửa. Hồi hộp tới giây cuối cùng!", inline=False)
    bang_help.add_field(name="💸 `k give @người-nhận <số tiền>`", value="Chuyển tiền của bạn cho một người khác.", inline=False)
    bang_help.add_field(name="⚙️ `k setkenh #tên-kênh`", value="(Quản trị viên) Cài đặt kênh thông báo lên cấp.", inline=False)
    
    bang_help.set_footer(text="Hãy chăm chỉ chat để leo rank và kiếm tiền nhé! :))")
    
    await ctx.send(embed=bang_help)

# --- LỆNH: ỦY THÁC HẰNG NGÀY (DAILY) ---
@bot.command()
async def daily(ctx):
    data = load_data()
    user_id = str(ctx.author.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1, "money": 0}
    if "money" not in data[user_id]:
        data[user_id]["money"] = 0

    now = datetime.now()

    # Kiểm tra cooldown daily
    last_daily_str = data[user_id].get("last_daily")
    if last_daily_str:
        last_daily = datetime.strptime(last_daily_str, "%Y-%m-%d %H:%M:%S")
        if now - last_daily < timedelta(days=1):
            time_left = timedelta(days=1) - (now - last_daily)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await ctx.send(f"⏳ Bạn đã nhận ủy thác hôm nay rồi! Hãy quay lại sau **{hours} giờ {minutes} phút** nữa nhé.")
            return

    thuong_daily = 1000
    data[user_id]["money"] += thuong_daily
    data[user_id]["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    save_data(data)
    
    await ctx.send(f"🎁 Ủy thác hoàn tất! {ctx.author.mention} nhận được **{thuong_daily} 💰**. (Số dư: **{data[user_id]['money']} 💰**)")

# --- LỆNH: BẢNG XẾP HẠNG ĐẠI GIA (TOP) ---
@bot.command()
async def top(ctx):
    data = load_data()
    
    danh_sach_dai_gia = []
    for user_id, thong_tin in data.items():
        tien = thong_tin.get("money", 0)
        danh_sach_dai_gia.append((user_id, tien))
        
    danh_sach_dai_gia.sort(key=lambda x: x[1], reverse=True)
    top_10 = danh_sach_dai_gia[:10]
    
    bang_xep_hang = discord.Embed(
        title="🏆 BẢNG XẾP HẠNG TÀI PHÚ 🏆",
        description="Top 10 đại gia nắm giữ nhiều tài sản nhất!",
        color=discord.Color.gold()
    )
    
    thu_hang = 1
    for user_id, tien in top_10:
        user = bot.get_user(int(user_id))
        ten_nguoi_choi = user.name if user else f"Người chơi ẩn ({user_id})"
        
        if thu_hang == 1:
            icon = "🥇"
        elif thu_hang == 2:
            icon = "🥈"
        elif thu_hang == 3:
            icon = "🥉"
        else:
            icon = f"#{thu_hang}"
            
        bang_xep_hang.add_field(name=f"{icon} {ten_nguoi_choi}", value=f"**{tien} 💰**", inline=False)
        thu_hang += 1
        
    await ctx.send(embed=bang_xep_hang)

# --- LỆNH: CHƠI ĐỒNG XU (SẤP NGỬA) ---
@bot.command()
async def coin(ctx, amount: str):
    data = load_data()
    user_id = str(ctx.author.id)
    now = datetime.now()

    # Kiểm tra thời gian chờ 3 giây
    if user_id in coin_cooldowns:
        thoi_gian_truoc = coin_cooldowns[user_id]
        if (now - thoi_gian_truoc).total_seconds() < 3:
            giay_con_lai = int(3 - (now - thoi_gian_truoc).total_seconds())
            await ctx.send(f"⏳ Khí huyết đang sục sôi, hãy bình tĩnh lại! Bạn cần chờ **{giay_con_lai} giây** nữa mới được tung xu tiếp.")
            return

    if user_id not in data or data[user_id].get("money", 0) <= 0:
        await ctx.send("Bạn không có đồng nào trong túi để cược cả. Hãy làm ủy thác hằng ngày để kiếm tiền nhé!")
        return

    tien_hien_tai = data[user_id]["money"]

    if amount.lower() == "all":
        bet = tien_hien_tai
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("Số tiền cược không hợp lệ! Vui lòng nhập một số hoặc chữ `all`.")
            return

    if bet <= 0:
        await ctx.send("Số tiền cược phải lớn hơn 0!")
        return

    if bet > tien_hien_tai:
        await ctx.send(f"Bạn không đủ tiền để cược! Bạn chỉ có **{tien_hien_tai} 💰** trong túi.")
        return

    data[user_id]["money"] -= bet
    save_data(data)

    coin_cooldowns[user_id] = now

    # HIỆU ỨNG TUNG XU 3 GIÂY
    msg = await ctx.send(f"🪙 {ctx.author.mention} đã ném **{bet} 💰** vào không trung...")
    await asyncio.sleep(1.0) 
    
    await msg.edit(content=f"🪙 {ctx.author.mention} đã ném **{bet} 💰** vào không trung...\n🔄 Đồng xu đang xoay tít trên không...")
    await asyncio.sleep(1.0) 
    
    await msg.edit(content=f"🪙 {ctx.author.mention} đã ném **{bet} 💰** vào không trung...\n🔄 Đồng xu đang xoay tít trên không...\n💥 Keng! Đồng xu rơi xuống đất và đang lăn...")
    await asyncio.sleep(1.0) 

    ket_qua = random.choice(["thắng", "thua"])

    data = load_data() 

    if ket_qua == "thắng":
        data[user_id]["money"] += (bet * 2)
        save_data(data)
        await msg.edit(content=f"🪙 **KẾT QUẢ: MẶT NGỬA!**\n🎉 Chúc mừng {ctx.author.mention}! Cờ bạc đãi tay mới, bạn đã thắng lớn và thu về **{bet * 2} 💰**! (Số dư: **{data[user_id]['money']} 💰**)")
    else:
        await msg.edit(content=f"🪙 **KẾT QUẢ: MẶT SẤP!**\n💀 Rất tiếc {ctx.author.mention}... Ra đê mà ở nhé! Bạn đã bay màu mất **{bet} 💰**. (Số dư: **{data[user_id]['money']} 💰**)")

# --- LỆNH: CHUYỂN TIỀN (GIVE) ---
@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    data = load_data()
    nguoi_gui = str(ctx.author.id)
    nguoi_nhan = str(member.id)

    if amount <= 0:
        await ctx.send("Số tiền chuyển phải lớn hơn 0!")
        return

    if nguoi_gui not in data or data[nguoi_gui].get("money", 0) < amount:
        await ctx.send("Bạn không có đủ tiền để chuyển số lượng này!")
        return

    if nguoi_gui == nguoi_nhan:
        await ctx.send("Bạn không thể tự chuyển tiền cho chính mình được =))")
        return

    if nguoi_nhan not in data:
        data[nguoi_nhan] = {"xp": 0, "level": 1, "money": 0}
    if "money" not in data[nguoi_nhan]:
        data[nguoi_nhan]["money"] = 0

    data[nguoi_gui]["money"] -= amount
    data[nguoi_nhan]["money"] += amount
    save_data(data)

    await ctx.send(f"💸 Giao dịch thành công! {ctx.author.mention} đã chuyển **{amount} 💰** cho {member.mention}.")

# --- LỆNH: TỰ CHỌN KÊNH THÔNG BÁO ---
@bot.command()
@commands.has_permissions(administrator=True) 
async def setkenh(ctx, kenh: discord.TextChannel):
    config = load_config()
    server_id = str(ctx.guild.id)
    
    config[server_id] = kenh.id
    save_config(config)
    
    await ctx.send(f'✅ Tuyệt vời! Từ giờ bot sẽ gửi thông báo lên cấp vào kênh {kenh.mention}!')

# --- LỆNH: KIỂM TRA RANK VÀ TIỀN ---
@bot.command()
async def rank(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id in data:
        xp = data[user_id].get("xp", 0)
        level = data[user_id].get("level", 1)
        tien = data[user_id].get("money", 0) 
        xp_tiep_theo = level * 100
        
        khung_rank = discord.Embed(title=f"Hồ sơ của {ctx.author.name}", color=discord.Color.green())
        khung_rank.set_thumbnail(url=ctx.author.display_avatar.url)
        khung_rank.add_field(name="Cấp độ", value=f"**{level}**", inline=True)
        khung_rank.add_field(name="Kinh nghiệm", value=f"**{xp}/{xp_tiep_theo} XP**", inline=True)
        khung_rank.add_field(name="Tài sản", value=f"**{tien} 💰**", inline=False)
        
        await ctx.send(embed=khung_rank)
    else:
        await ctx.send("Bạn chưa có dữ liệu. Hãy chăm chỉ chat để mở khóa hồ sơ nhé!")

# --- SỰ KIỆN: KHI CÓ NGƯỜI CHAT ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_data()
    user_id = str(message.author.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1, "money": 0}

    if "money" not in data[user_id]:
        data[user_id]["money"] = 0

    data[user_id]["xp"] += random.randint(5, 15)
    
    xp_hien_tai = data[user_id]["xp"]
    cap_hien_tai = data[user_id]["level"]
    xp_can_thiet = cap_hien_tai * 100

    if xp_hien_tai >= xp_can_thiet:
        data[user_id]["level"] += 1
        data[user_id]["xp"] -= xp_can_thiet 
        
        tien_thuong = data[user_id]["level"] * 500
        data[user_id]["money"] += tien_thuong
        
        config = load_config()
        server_id = str(message.guild.id)
        
        thong_bao = discord.Embed(
            title="🎉 LÊN CẤP THÀNH CÔNG! 🎉",
            description=f'Chúc mừng {message.author.mention} đã vươn lên **Cấp {data[user_id]["level"]}**!\n\n🎁 Phần thưởng của bạn là: **{tien_thuong} 💰**',
            color=discord.Color.gold()
        )
        thong_bao.set_thumbnail(url=message.author.display_avatar.url)

        if server_id in config:
            kenh_id = config[server_id]
            kenh_thong_bao = bot.get_channel(kenh_id)
            if kenh_thong_bao:
                await kenh_thong_bao.send(embed=thong_bao)
            else:
                await message.channel.send(embed=thong_bao)
        else:
            await message.channel.send(embed=thong_bao)

    save_data(data)
    await bot.process_commands(message)

# --- KHỞI ĐỘNG ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng!')

keep_alive() 

# Hai nửa mã Token của bạn
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GVIyrV.'
nua_sau = 'j8oLKlNxSTcHIDBFjQ_yjQtlJADTrzn4abcKds'

bot.run(nua_dau + nua_sau)
