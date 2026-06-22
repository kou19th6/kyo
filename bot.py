import discord
from discord.ext import commands
from keep_alive import keep_alive 
import json 
import os
import random 

intents = discord.Intents.default()
intents.message_content = True

# --- ĐÃ ĐỔI PREFIX THÀNH Ky ---
# Bot sẽ nhận diện được cả: 'Ky rank', 'ky rank', 'Kyrank', 'kyrank'
bot = commands.Bot(command_prefix=['Ky ', 'ky ', 'Ky', 'ky'], intents=intents)

# --- CÁC HÀM XỬ LÝ SỔ TAY LEVEL ---
def load_data():
    if not os.path.exists('users.json'):
        return {}
    with open('users.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('users.json', 'w') as f:
        json.dump(data, f, indent=4)

# --- CÁC HÀM CẤT GIỮ CẤU HÌNH SERVER ---
def load_config():
    if not os.path.exists('config.json'):
        return {}
    with open('config.json', 'r') as f:
        return json.load(f)

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

# --- LỆNH: TỰ CHỌN KÊNH THÔNG BÁO ---
@bot.command()
@commands.has_permissions(administrator=True) 
async def setkenh(ctx, kenh: discord.TextChannel):
    config = load_config()
    server_id = str(ctx.guild.id)
    
    config[server_id] = kenh.id
    save_config(config)
    
    await ctx.send(f'✅ Tuyệt vời! Từ giờ bot sẽ gửi thông báo lên cấp vào kênh {kenh.mention}!')

# --- LỆNH: KIỂM TRA RANK ---
@bot.command()
async def rank(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id in data:
        xp = data[user_id]["xp"]
        level = data[user_id]["level"]
        xp_tiep_theo = level * 100
        await ctx.send(f'📊 {ctx.author.name}, bạn đang ở **Cấp {level}** với **{xp}/{xp_tiep_theo} XP**.')
    else:
        await ctx.send("Bạn chưa có điểm kinh nghiệm nào. Hãy chăm chỉ tương tác nhé!")

# --- SỰ KIỆN: KHI CÓ NGƯỜI CHAT ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_data()
    user_id = str(message.author.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1}

    data[user_id]["xp"] += random.randint(5, 15)
    
    xp_hien_tai = data[user_id]["xp"]
    cap_hien_tai = data[user_id]["level"]
    xp_can_thiet = cap_hien_tai * 100

    if xp_hien_tai >= xp_can_thiet:
        data[user_id]["level"] += 1
        data[user_id]["xp"] = 0 
        
        config = load_config()
        server_id = str(message.guild.id)
        
        thong_bao = discord.Embed(
            title="🎉 LÊN CẤP THÀNH CÔNG! 🎉",
            description=f'Chúc mừng {message.author.mention} đã chăm chỉ tương tác và vươn lên **Cấp {data[user_id]["level"]}**!',
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
    print(f'Bot {bot.user} đã sẵn sàng với lệnh gọi mới!')

keep_alive() 

# Hai nửa mã Token của bạn
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GVIyrV.'
nua_sau = 'j8oLKlNxSTcHIDBFjQ_yjQtlJADTrzn4abcKds'

bot.run(nua_dau + nua_sau)
