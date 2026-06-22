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
# KẾT NỐI MONGODB (ĐÃ TỐI ƯU HÓA SIÊU TỐC)
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]
users_col = db["users"]   
config_col = db["config"] 

# BỘ ĐỆM RAM (Tránh lag bot khi nhiều người chơi)
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
    if ctx.author.guild_permissions.administrator:
        return True
    if not ctx.guild:
        return True
    config = load_server_config(ctx.guild.id)
    allowed_channels = config.get("allowed_channels", [])
    if allowed_channels and ctx.channel.id not in allowed_channels:
        return False
    return True


# =====================================================================
# KHO TÀNG CÂU HỎI NHÂN SINH THEO CHỈ SỐ
# =====================================================================
EVENTS_P1 = [
    {
        "q": "Bạn được chọn làm lớp trưởng nhưng lũ bạn cá biệt chống đối.",
        "a": "Dùng cái uy răn đe (Cần Nhan Sắc)",
        "b": "Lập mưu thu phục (Cần Trí Tuệ)",
        "stat_a": "nhan_sac", "diff_a": 12,
        "win_a": "Bạn lườm một cái, lũ bạn sợ vẻ đẹp sắc sảo nên ngoan ngoãn. [+2 Nhan sắc, +500💰]",
        "lose_a": "Bọn nó chê bạn chảnh, cô lập bạn. [-1 Nhan sắc, -200💰]",
        "eff_wa": {"tt":0, "ns":2, "mm":0, "t":500}, "eff_la": {"tt":0, "ns":-1, "mm":0, "t":-200},
        "stat_b": "tri_tue", "diff_b": 13,
        "win_b": "Bạn nắm thóp điểm yếu từng đứa, bắt chúng phục tùng. [+3 Trí tuệ, +800💰]",
        "lose_b": "Kế hoạch thất bại, bạn bị chúng lừa lại sấp mặt. [-1 Trí tuệ, -300💰]",
        "eff_wb": {"tt":3, "ns":0, "mm":0, "t":800}, "eff_lb": {"tt":-1, "ns":0, "mm":0, "t":-300}
    },
    {
        "q": "Kiểm tra học kỳ môn Toán cực khó, bạn quên chưa học bài.",
        "a": "Quay cóp thần sầu (Cần May Mắn)",
        "b": "Tự suy luận logic (Cần Trí Tuệ)",
        "stat_a": "may_man", "diff_a": 14,
        "win_a": "Giám thị ngáp ngủ, bạn chép full phao được 9 điểm! [+2 May mắn, +300💰]",
        "lose_a": "Bị bắt quả tang, đình chỉ thi, gọi phụ huynh. [-3 May mắn, -500💰]",
        "eff_wa": {"tt":0, "ns":0, "mm":2, "t":300}, "eff_la": {"tt":0, "ns":0, "mm":-3, "t":-500},
        "stat_b": "tri_tue", "diff_b": 15,
        "win_b": "IQ bùng nổ, bạn giải được cả câu chốt lấy 10 điểm tuyệt đối! [+4 Trí tuệ, +1000💰]",
        "lose_b": "Nặn óc không ra chữ nào, nộp giấy trắng. [-2 Trí tuệ, 0💰]",
        "eff_wb": {"tt":4, "ns":0, "mm":0, "t":1000}, "eff_lb": {"tt":-2, "ns":0, "mm":0, "t":0}
    },
    {
        "q": "Trường tổ chức cuộc thi Gương mặt Đại sứ.",
        "a": "Đăng ký thi ngay (Cần Nhan Sắc)",
        "b": "Bốc thăm trúng thưởng (Cần May Mắn)",
        "stat_a": "nhan_sac", "diff_a": 13,
        "win_a": "Hào quang rực rỡ, bạn ẵm giải Nhất kèm hợp đồng quảng cáo! [+3 Nhan sắc, +1500💰]",
        "lose_a": "Vấp ngã trên sân khấu, thành meme chế giễu toàn trường. [-2 Nhan sắc, -200💰]",
        "eff_wa": {"tt":0, "ns":3, "mm":0, "t":1500}, "eff_la": {"tt":0, "ns":-2, "mm":0, "t":-200},
        "stat_b": "may_man", "diff_b": 12,
        "win_b": "Dù không thi nhưng bạn bốc trúng giải Đặc biệt của nhà tài trợ! [+3 May mắn, +2000💰]",
        "lose_b": "Bốc trúng cái nịt, chả được gì. [0💰]",
        "eff_wb": {"tt":0, "ns":0, "mm":3, "t":2000}, "eff_lb": {"tt":0, "ns":0, "mm":0, "t":0}
    },
    {
        "q": "Bạn tìm thấy một con chó hoang đang sủa người đi đường.",
        "a": "Dùng ánh mắt thuần phục (Cần Nhan Sắc)",
        "b": "Đoán tâm lý để vuốt ve (Cần Trí Tuệ)",
        "stat_a": "nhan_sac", "diff_a": 11,
        "win_a": "Chú chó mê mẩn vẻ đẹp của bạn, cọ đầu vào chân. Bạn nhặt được ví tiền nó ngậm! [+1 Nhan sắc, +800💰]",
        "lose_a": "Nó không quan tâm bạn đẹp cỡ nào, táp cho một phát vào bắp chân! [-1 Nhan sắc, -400💰]",
        "eff_wa": {"tt":0, "ns":1, "mm":0, "t":800}, "eff_la": {"tt":0, "ns":-1, "mm":0, "t":-400},
        "stat_b": "tri_tue", "diff_b": 12,
        "win_b": "Bạn biết nó bị gai đâm, nhổ gai ra. Chú chó dẫn bạn đến một cái hố giấu vàng! [+2 Trí tuệ, +1200💰]",
        "lose_b": "Đoán sai, nó giật mình cắn rách áo bạn. [-1 Trí tuệ, -200💰]",
        "eff_wb": {"tt":2, "ns":0, "mm":0, "t":1200}, "eff_lb": {"tt":-1, "ns":0, "mm":0, "t":-200}
    }
]

EVENTS_P2 = [
    {
        "q": "Bạn muốn khởi nghiệp nhưng thiếu vốn trầm trọng.",
        "a": "Đi gọi vốn Shark Tank (Cần Trí Tuệ)",
        "b": "Mua xổ số đổi đời (Cần May Mắn)",
        "stat_a": "tri_tue", "diff_a": 15,
        "win_a": "Pitching chấn động, Shark rót vốn triệu đô! Công ty phất lên như diều. [+4 Trí tuệ, +5000💰]",
        "lose_a": "Bị các Shark chửi cho tơi bời, xấu hổ đóng cửa dự án. [-2 Trí tuệ, -1000💰]",
        "eff_wa": {"tt":4, "ns":0, "mm":0, "t":5000}, "eff_la": {"tt":-2, "ns":0, "mm":0, "t":-1000},
        "stat_b": "may_man", "diff_b": 16,
        "win_b": "TRÚNG ĐỘC ĐẮC! Không cần làm gì vẫn có tiền khởi nghiệp ngập mặt! [+5 May mắn, +10000💰]",
        "lose_b": "Nướng sạch tiền ăn sáng vào vé số, chết đói. [-2 May mắn, -800💰]",
        "eff_wb": {"tt":0, "ns":0, "mm":5, "t":10000}, "eff_lb": {"tt":0, "ns":0, "mm":-2, "t":-800}
    },
    {
        "q": "Một đại gia già ngỏ ý muốn bao nuôi bạn, cho bạn mọi thứ.",
        "a": "Dùng Nhan sắc thao túng (Cần Nhan Sắc)",
        "b": "Lập mưu cuỗm tài sản (Cần Trí Tuệ)",
        "stat_a": "nhan_sac", "diff_a": 14,
        "win_a": "Đại gia mê đắm, sang tên cho bạn 3 căn biệt thự rồi quy tiên. [+2 Nhan sắc, +8000💰]",
        "lose_a": "Đại gia tìm được 'đồ chơi' mới trẻ hơn, đá bạn ra rìa tay trắng. [-2 Nhan sắc, -2000💰]",
        "eff_wa": {"tt":0, "ns":2, "mm":0, "t":8000}, "eff_la": {"tt":0, "ns":-2, "mm":0, "t":-2000},
        "stat_b": "tri_tue", "diff_b": 15,
        "win_b": "Bạn tìm ra sổ đen trốn thuế của hắn, uy hiếp lấy một nửa gia tài! [+4 Trí tuệ, +6000💰]",
        "lose_b": "Bị hắn phát hiện, sai giang hồ truy sát. Bạn mất trắng. [-2 Trí tuệ, -3000💰]",
        "eff_wb": {"tt":4, "ns":0, "mm":0, "t":6000}, "eff_lb": {"tt":-2, "ns":0, "mm":0, "t":-3000}
    },
    {
        "q": "Công ty bạn có một đợt cắt giảm nhân sự quy mô lớn.",
        "a": "Tranh công của đồng nghiệp (Cần Trí Tuệ)",
        "b": "Tỏ ra vô hại chờ thời (Cần May Mắn)",
        "stat_a": "tri_tue", "diff_a": 13,
        "win_a": "Kế hoạch hoàn hảo, đồng nghiệp bay màu, bạn được thăng chức! [+2 Trí tuệ, +3000💰]",
        "lose_a": "Bị sếp nhìn thấu dã tâm, đuổi việc ngay lập tức. [-2 Trí tuệ, -2000💰]",
        "eff_wa": {"tt":2, "ns":0, "mm":0, "t":3000}, "eff_la": {"tt":-2, "ns":0, "mm":0, "t":-2000},
        "stat_b": "may_man", "diff_b": 12,
        "win_b": "Những đứa giỏi bị đuổi hết vì sếp sợ ghế, bạn lù đù lại lên làm quản lý! [+3 May mắn, +2500💰]",
        "lose_b": "Xui xẻo bị gạch tên ngay vòng gửi xe. Thất nghiệp. [-1 May mắn, -1000💰]",
        "eff_wb": {"tt":0, "ns":0, "mm":3, "t":2500}, "eff_lb": {"tt":0, "ns":0, "mm":-1, "t":-1000}
    },
    {
        "q": "Bạn được mời làm KOL đại diện cho một nhãn hàng tranh cãi.",
        "a": "Bán khuôn mặt lấy tiền (Cần Nhan Sắc)",
        "b": "Tẩy trắng thương hiệu (Cần Trí Tuệ)",
        "stat_a": "nhan_sac", "diff_a": 15,
        "win_a": "Cộng đồng mạng mê mẩn nhan sắc bạn, quên luôn phốt của nhãn hàng! [+3 Nhan sắc, +5000💰]",
        "lose_a": "Bị tế sống trên mọi mặt trận, sự nghiệp KOL tan tành. [-3 Nhan sắc, -4000💰]",
        "eff_wa": {"tt":0, "ns":3, "mm":0, "t":5000}, "eff_la": {"tt":0, "ns":-3, "mm":0, "t":-4000},
        "stat_b": "tri_tue", "diff_b": 14,
        "win_b": "Làm một chiến dịch PR đỉnh cao, lật ngược thế cờ hoàn hảo! [+4 Trí tuệ, +6000💰]",
        "lose_b": "Khủng hoảng truyền thông kép, bạn đền hợp đồng sập nguồn. [-2 Trí tuệ, -5000💰]",
        "eff_wb": {"tt":4, "ns":0, "mm":0, "t":6000}, "eff_lb": {"tt":-2, "ns":0, "mm":0, "t":-5000}
    }
]

EVENTS_P3 = [
    {
        "q": "Bạn rảnh rỗi sinh nông nổi, xách vali bước vào Casino.",
        "a": "Chơi Poker trí tuệ (Cần Trí Tuệ)",
        "b": "Quay Slot Machine (Cần May Mắn)",
        "stat_a": "tri_tue", "diff_a": 16,
        "win_a": "Đọc vị mọi đối thủ, bạn càn quét bàn Poker gom về một gia tài! [+3 Trí tuệ, +12000💰]",
        "lose_a": "Gặp phải cao thủ thế giới, bạn thua cắm luôn cái sổ đỏ. [-3 Trí tuệ, -8000💰]",
        "eff_wa": {"tt":3, "ns":0, "mm":0, "t":12000}, "eff_la": {"tt":-3, "ns":0, "mm":0, "t":-8000},
        "stat_b": "may_man", "diff_b": 17,
        "win_b": "JACKPOT!!! Cả sòng bài chấn động vì bạn nổ hũ vĩ đại! [+5 May mắn, +20000💰]",
        "lose_b": "Máy nuốt sạch tiền, bạn lết bộ về nhà trong đêm mưa. [-4 May mắn, -5000💰]",
        "eff_wb": {"tt":0, "ns":0, "mm":5, "t":20000}, "eff_lb": {"tt":0, "ns":0, "mm":-4, "t":-5000}
    },
    {
        "q": "Cơ thể bạn có dấu hiệu suy nhược nghiêm trọng tuổi trung niên.",
        "a": "Mua thuốc bí truyền (Cần May Mắn)",
        "b": "Phẫu thuật tân trang (Cần Nhan Sắc)",
        "stat_a": "may_man", "diff_a": 14,
        "win_a": "Thuốc tiên! Bạn khỏe như trâu, thọ thêm chục tuổi. [+3 May mắn, -1000💰]",
        "lose_a": "Uống nhằm thuốc giả, suy gan suy thận, tốn bộn tiền cấp cứu. [-3 May mắn, -6000💰]",
        "eff_wa": {"tt":0, "ns":0, "mm":3, "t":-1000}, "eff_la": {"tt":0, "ns":0, "mm":-3, "t":-6000},
        "stat_b": "nhan_sac", "diff_b": 13,
        "win_b": "Phẫu thuật thành công, bạn hồi xuân như trai/gái 18, chốt được đại gia. [+4 Nhan sắc, +5000💰]",
        "lose_b": "Biến chứng thẩm mỹ, mặt sưng vù, tiền mất tật mang. [-4 Nhan sắc, -5000💰]",
        "eff_wb": {"tt":0, "ns":4, "mm":0, "t":5000}, "eff_lb": {"tt":0, "ns":-4, "mm":0, "t":-5000}
    },
    {
        "q": "Thị trường Bất Động Sản đang đóng băng, cò đất xúi bạn bắt đáy.",
        "a": "Phân tích quy hoạch (Cần Trí Tuệ)",
        "b": "Nhắm mắt mua bừa (Cần May Mắn)",
        "stat_a": "tri_tue", "diff_a": 15,
        "win_a": "Đánh hơi được siêu dự án sắp xây, lô đất bạn mua tăng giá x5! [+4 Trí tuệ, +15000💰]",
        "lose_a": "Phân tích sai bét, vướng quy hoạch treo, ôm nợ ngân hàng. [-2 Trí tuệ, -8000💰]",
        "eff_wa": {"tt":4, "ns":0, "mm":0, "t":15000}, "eff_la": {"tt":-2, "ns":0, "mm":0, "t":-8000},
        "stat_b": "may_man", "diff_b": 15,
        "win_b": "Chỉ tay đại một mảnh, ai ngờ trúng ngay mỏ dầu! Giàu to! [+4 May mắn, +18000💰]",
        "lose_b": "Đất dính mồ mả, không ai thèm mua, bán lỗ cũng không xong. [-2 May mắn, -6000💰]",
        "eff_wb": {"tt":0, "ns":0, "mm":4, "t":18000}, "eff_lb": {"tt":0, "ns":0, "mm":-2, "t":-6000}
    }
]

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
        {"mult": -1.0, "msg": "💥 **ĐẠP TRÚNG MÌN GOBLIN!**\nBÙM! Bạn đạp trúng mìn tự chế của bọn Goblin. Tốn một mớ tiền để trả phí cấp cứu."},
        {"mult": -0.8, "msg": "📉 **LỪA ĐẢO ĐA CẤP!**\nBạn bị thương nhân lừa mua 'Thuốc trường sinh' giả. Tiền mất tật mang."},
        {"mult": -1.5, "msg": "🦇 **MA CÀ RỒNG!**\nBị một con ma cà rồng cắn. Trốn thoát được nhưng tốn một đống tiền viện phí."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"mult": -0.4, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi mua bông băng thuốc đỏ."},
        {"mult": -0.3, "msg": "🦟 **MUỖI KHỔNG LỒ!**\nBị bầy muỗi rừng khổng lồ chích sưng vù, phải đi mua thuốc mỡ bôi."},
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước tăng lực hết hạn từ máy bán hàng tự động trong rừng."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"mult": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."},
        {"mult": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"mult": 0.6, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá kha khá!"},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc trả cho bạn một khoản khá hời."},
        {"mult": 1.0, "msg": "🙏 **NGƯỜI TỐT VIỆC TỐT!**\nNhặt được ví của một hiệp sĩ, bạn trả lại và được anh ta hậu tạ một khoản tiền."}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp nhỏ và tịch thu kho báu của chúng!"},
        {"mult": 2.0, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, ai ngờ đào trúng viên ngọc lục bảo thô to bằng nắm tay!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nBạn phát hiện ra một rương kho báu vàng chóe bị chôn vùi nửa mét dưới đất. Mở ra toàn tiền!"},
        {"mult": 3.0, "msg": "💍 **KIM CƯƠNG RỚT!**\nÁnh sáng lấp lánh đập vào mắt! Hóa ra là một viên kim cương tinh khiết rớt trên thảm cỏ."}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng giải đặc biệt!"},
        {"mult": 10.0, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Bạn tìm thấy hang động cất giấu kho báu huyền thoại. Một núi Vàng hiện ra trước mắt!"}
    ]
}


# =====================================================================
# GIAO DIỆN GAME NHÂN SINH RPG TƯƠNG TÁC
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

        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, bố mẹ là tỷ phú. Chạy quanh nhà bằng siêu xe.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài chợ từ nhỏ.")

        self.btn_a = discord.ui.Button(label=f"A. {self.ev['a']}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_a.callback = self.choice_a
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['b']}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_b.callback = self.choice_b

        self.add_item(self.btn_a)
        self.add_item(self.btn_b)

    async def on_timeout(self):
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng bấm lung tung!", ephemeral=True)
            return False
        return True

    async def process_choice(self, interaction: discord.Interaction, choice: str):
        # Xác định stat cần roll
        stat_key = self.ev["stat_a"] if choice == "A" else self.ev["stat_b"]
        diff = self.ev["diff_a"] if choice == "A" else self.ev["diff_b"]
        
        roll = random.randint(1, 10)
        total = roll + self.stats[stat_key]
        is_win = total >= diff
        
        if choice == "A":
            eff = self.ev["eff_wa"] if is_win else self.ev["eff_la"]
            res = self.ev["win_a"] if is_win else self.ev["lose_a"]
        else:
            eff = self.ev["eff_wb"] if is_win else self.ev["eff_lb"]
            res = self.ev["win_b"] if is_win else self.ev["lose_b"]

        self.stats["tri_tue"] += eff["tt"]
        self.stats["nhan_sac"] += eff["ns"]
        self.stats["may_man"] += eff["mm"]
        self.tien_an += eff["t"]

        # FIX LỖI TẠI ĐÂY: Dùng biến short_key để tra cứu đúng từ khóa trong dictionary eff
        short_key = "tt" if stat_key == "tri_tue" else "ns" if stat_key == "nhan_sac" else "mm"
        stat_name = "Trí tuệ" if stat_key == "tri_tue" else "Nhan sắc" if stat_key == "nhan_sac" else "May mắn"
        kq_thung = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        
        log_entry = f"🎲 **Đổ xúc xắc:** Lăn được {roll} + {stat_name} ({self.stats[stat_key] - eff[short_key]}) = **{total}** (Cần {diff})\n{kq_thung}: {res}"
        
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

        await self.update_ui(interaction)

    async def choice_a(self, interaction: discord.Interaction): await self.process_choice(interaction, "A")
    async def choice_b(self, interaction: discord.Interaction): await self.process_choice(interaction, "B")

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH TƯƠNG TÁC 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.purple())

        stats_text = f"Trí tuệ: **{self.stats['tri_tue']}** | Nhan sắc: **{self.stats['nhan_sac']}** | May mắn: **{self.stats['may_man']}**"
        embed.add_field(name="📊 Chỉ số linh hồn (Hiện tại)", value=stats_text, inline=False)

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

            total_reward = self.tien_an + (self.stats['tri_tue'] + self.stats['nhan_sac'] + self.stats['may_man']) * 50
            
            user_data = load_user(user_id)
            user_data["money"] += total_reward
            save_user(user_id)

            if total_reward < 0:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Sống lay lắt qua ngày, cuối đời bệnh tật không tiền chữa.\n❌ **BÁO NHÀ!** Bạn để lại khoản nợ: **{total_reward} 💰**\n*(Hệ thống đã trừ nợ vào sổ, đi cày `k daily` mà trả nhé!)*", inline=False)
            elif total_reward >= 10000:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Hưởng thọ trong biệt thự cao cấp. Tang lễ hoành tráng.\n👑 **ĐẠI PHÚ HÀO!** Di sản kiếp sau: **+{total_reward} 💰**", inline=False)
            else:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Cuộc đời bình dị, thanh thản ra đi bên con cháu.\n💼 **DƯ DẢ!** Di sản kiếp sau: **+{total_reward} 💰**", inline=False)

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{user_data['money']} 💰**", inline=False)

        if interaction.response.is_done(): await interaction.message.edit(embed=embed, view=self)
        else: await interaction.response.edit_message(embed=embed, view=self)

# =====================================================================
# GIAO DIỆN NÚT BẤM VÀ DROP-DOWN (SHOP & EXPLORE & AFK)
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
        
        # Sửa lỗi reference SCENARIOS bằng cách import từ global scope
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
    bang_help.add_field(name="🌀 `k nhansinh`", value="Game Tương Tác RPG (Phí: 100 💰). Coi chừng nợ!", inline=False)
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
        "tri_tue": random.randint(1, 10),
        "nhan_sac": random.randint(1, 10),
        "may_man": random.randint(1, 10)
    }

    view = NhanSinhGameView(ctx.author, stats)
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.purple())
    embed.add_field(name="📊 Chỉ số ban đầu", value=f"Trí tuệ: **{stats['tri_tue']}** | Nhan sắc: **{stats['nhan_sac']}** | May mắn: **{stats['may_man']}**", inline=False)
    
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
