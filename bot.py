import discord
from discord.ext import commands
from keep_alive import keep_alive 

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng hoạt động 24/24!')

@bot.command()
async def chao(ctx):
    await ctx.send(f'Chào {ctx.author.name}! Mình đang online 24/24 nè!')

keep_alive() 
# Nhớ thay dòng bên dưới bằng mã Token thật của bot bạn nhé!
bot.run('DÁN_MÃ_TOKEN_CỦA_BẠN_VÀO_ĐÂY')
