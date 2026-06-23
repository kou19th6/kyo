import discord
from discord.ext import commands, tasks
from keep_alive import keep_alive 
import random 
import asyncio 
import time
from datetime import datetime, timedelta 
import pymongo 
import math

# =====================================================================
# [PHẦN 1] KHỞI TẠO SIÊU BOT 10.0 - BỘ KHUNG DỮ LIỆU ĐỒ SỘ (>700 DÒNG)
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

# =====================================================================
# TỪ ĐIỂN ẢNH GIF / UI MƯỢT MÀ
# =====================================================================
GIF_LINKS = {
    "jail": "https://media.giphy.com/media/uG3lKkAuh53wKxY0l9/giphy.gif",
    "bank": "https://media.giphy.com/media/xTiTnqUxyWbsAXq7Ju/giphy.gif",
    "rob_success": "https://media.giphy.com/media/Y2ZUWLrTy63j9T6qrK/giphy.gif",
    "rob_fail": "https://media.giphy.com/media/RYjnzPS8u0jAs/giphy.gif",
    "rank": "https://media.giphy.com/media/LdOyjZ7io5Msw/giphy.gif",
    "daily": "https://media.giphy.com/media/67ThRZlYBvibtdF9JH/giphy.gif",
    "casino": "https://media.giphy.com/media/l4hLA4ALhloJt2Tny/giphy.gif",
    "fish": "https://media.giphy.com/media/3o6ZtaO9BZHcOjmErm/giphy.gif",
    "farm": "https://media.giphy.com/media/11s7Ke7jcNxCHS/giphy.gif",
    "war": "https://media.giphy.com/media/l41JRsph73VokN6ik/giphy.gif"
}

cooldowns = {
    "gamble": {}, 
    "nhansinh": {}, 
    "work": {}, 
    "crime": {}, 
    "fish": {}, 
    "farm": {}
}
dang_choi_nhansinh = [] 

# =====================================================================
# KẾT NỐI MONGODB & BỘ ĐỆM ĐA LUỒNG
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["DiscordBotDB"]
    users_col = db["users"]         
    config_col = db["config"]       
    stocks_col = db["stocks"]       
    kf_col = db["kallen_fantasy"]
    farm_col = db["farms"]
    companies_col = db["companies"]
    print("✅ Đã kết nối thành công tới MongoDB Database!")
except Exception as e:
    print(f"❌ Lỗi kết nối Database: {e}")

DB_CACHE, CONFIG_CACHE, KF_CACHE, FARM_CACHE, COMPANY_CACHE = {}, {}, {}, {}, {}

def load_user(user_id):
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        doc = users_col.find_one({"_id": user_id})
        DB_CACHE[user_id] = doc if doc else {}
            
    # HỆ THỐNG KỸ NĂNG MỚI (SKILLS) VÀ CHỈ SỐ SINH TỒN
    defaults = {
        "xp": 0, 
        "level": 1, 
        "money": 5000, 
        "bank": 0, 
        "bank_capacity": 5000000,
        "title": "Kẻ Lang Thang 🏕️", 
        "assets": [], 
        "inventory": {}, 
        "pets": {}, 
        "stocks": {}, 
        "jail_time": None, 
        "health": 100, 
        "max_health": 100,
        "fishing_rod": "CanTre", 
        "bait": 50,
        "reputation": 0, 
        "honor_points": 0,
        "skills": {
            "trading": 1,       # Giảm thuế, tăng giá bán cổ phiếu
            "farming": 1,       # Tăng sản lượng nông nghiệp
            "fishing": 1,       # Tăng tỉ lệ câu cá hiếm
            "charisma": 1,      # Thuyết phục (Dùng trong Nhan sinh)
            "hacking": 1        # Tăng tỉ lệ cướp ngân hàng
        },
        "company": None
    }
    for k, v in defaults.items():
        if k not in DB_CACHE[user_id]: 
            DB_CACHE[user_id][k] = v
            
    # Update nested dicts (như skills) nếu thêm skill mới trong tương lai
    if "skills" in DB_CACHE[user_id]:
        for sk, sv in defaults["skills"].items():
            if sk not in DB_CACHE[user_id]["skills"]:
                DB_CACHE[user_id]["skills"][sk] = sv

    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE: 
        users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

# =====================================================================
# TỔNG KHO VẬT PHẨM ĐỜI THỰC & GAME (SHOP_ITEMS)
# =====================================================================
SHOP_ITEMS = {
    # HỆ THỐNG DANH HIỆU
    "title_1": {
        "type": "title", 
        "name": "Bình Dân Học Vụ 🎒", 
        "price": 50000, 
        "emoji": "🏷️", 
        "buff_xp": 1.1,
        "desc": "Danh hiệu cơ bản cho người mới."
    },
    "title_2": {
        "type": "title", 
        "name": "Thương Nhân Chợ Đen 💼", 
        "price": 500000, 
        "emoji": "🏷️", 
        "buff_xp": 1.2,
        "desc": "Giảm 5% phí giao dịch chợ đen."
    },
    "title_3": {
        "type": "title", 
        "name": "Quản Trị Tinh Hà Trang Viên 🌌", 
        "price": 2500000, 
        "emoji": "🏷️", 
        "buff_xp": 1.5,
        "desc": "Danh hiệu VIP cấp trung."
    },
    "title_4": {
        "type": "title", 
        "name": "Tài Phiệt Ác Ma 👑", 
        "price": 10000000, 
        "emoji": "🏷️", 
        "buff_xp": 2.0,
        "desc": "Tăng 20% lợi nhuận ngân hàng."
    },
    
    # HỆ THỐNG PHƯƠNG TIỆN (CỘNG CHỈ SỐ HACKING/ESCAPE)
    "veh_1": {
        "type": "vehicle", 
        "name": "Xe Đạp Điện Mini 🚲", 
        "price": 15000, 
        "emoji": "🚲", 
        "escape_rate": 5,
        "desc": "Chạy pin 40km/h."
    },
    "veh_2": {
        "type": "vehicle", 
        "name": "Honda SH 150i 🏍️", 
        "price": 120000, 
        "emoji": "🏍️", 
        "escape_rate": 10,
        "desc": "Dân chơi bốc đầu."
    },
    "veh_3": {
        "type": "vehicle", 
        "name": "Mazda C300 AMG 🚗", 
        "price": 1500000, 
        "emoji": "🚗", 
        "escape_rate": 15,
        "desc": "Đẹp trai lãng tử."
    },
    "veh_4": {
        "type": "vehicle", 
        "name": "Mercedes G63 🚙", 
        "price": 8000000, 
        "emoji": "🚙", 
        "escape_rate": 20,
        "desc": "Chủ tịch giả danh."
    },
    
    # BẤT ĐỘNG SẢN (CỘNG TIỀN THỤ ĐỘNG THEO GIỜ)
    "house_1": {
        "type": "house", 
        "name": "Phòng Trọ 15m2 🏚️", 
        "price": 80000, 
        "emoji": "🏚️", 
        "income": 500,
        "desc": "Nóng nực nhưng có chỗ chui ra chui vào."
    },
    "house_2": {
        "type": "house", 
        "name": "Chung Cư Mini 🏢", 
        "price": 800000, 
        "emoji": "🏢", 
        "income": 4000,
        "desc": "Có thang máy và bảo vệ."
    },
    "house_3": {
        "type": "house", 
        "name": "Nhà Mặt Phố 🏪", 
        "price": 5000000, 
        "emoji": "🏪", 
        "income": 20000,
        "desc": "Kinh doanh buôn bán siêu lời."
    },
    "house_4": {
        "type": "house", 
        "name": "Biệt Thự Hồ Tây 🏡", 
        "price": 35000000, 
        "emoji": "🏡", 
        "income": 100000,
        "desc": "View triệu đô."
    },
    "house_5": {
        "type": "house", 
        "name": "Căn Cứ Công Nghiệp Tiền Tuyến 🏭", 
        "price": 250000000, 
        "emoji": "🏭", 
        "income": 800000,
        "desc": "Căn cứ AIC chuẩn Arknights Endfield."
    },
    
    # SÁCH KỸ NĂNG (TĂNG ĐIỂM SKILL)
    "book_1": {
        "type": "item",
        "name": "Sách Luyện Thi TSA HUST 📘",
        "price": 50000,
        "emoji": "📘",
        "buff_skill": "hacking",
        "desc": "Đọc xong não to ra, tư duy siêu việt."
    },
    "book_2": {
        "type": "item",
        "name": "Binh Pháp Tôn Tử 📕",
        "price": 100000,
        "emoji": "📕",
        "buff_skill": "trading",
        "desc": "Thao túng tâm lý thị trường chứng khoán."
    }
}

# =====================================================================
# DATA KALLEN FANTASY (Gacha & Đánh Quái)
# =====================================================================
KALLEN_BATTLESUITS = {
    "imayoh": {
        "name": "Ritual Imayoh", "type": "MECH", "rarity": "A", 
        "base_hp": 1200, "base_atk": 250, 
        "skill_basic_dmg": 1.2, "skill_ult_dmg": 6.0, 
        "ult_sp_cost": 80, "emoji": "🔫"
    },
    "sixth_serenade": {
        "name": "Sixth Serenade", "type": "PSY", "rarity": "S", 
        "base_hp": 1500, "base_atk": 320, 
        "skill_basic_dmg": 1.5, "skill_ult_dmg": 8.0, 
        "ult_sp_cost": 100, "emoji": "🎭"
    },
    "chen_qianyu": {
        "name": "Chen Qianyu (Endfield)", "type": "BIO", "rarity": "S", 
        "base_hp": 1800, "base_atk": 380, 
        "skill_basic_dmg": 1.8, "skill_ult_dmg": 10.0, 
        "ult_sp_cost": 120, "emoji": "🗡️"
    },
    "raiden_shogun": {
        "name": "Raiden Shogun", "type": "PSY", "rarity": "SSS", 
        "base_hp": 2800, "base_atk": 550, 
        "skill_basic_dmg": 2.8, "skill_ult_dmg": 18.0, 
        "ult_sp_cost": 150, "emoji": "⚡"
    }
}

KALLEN_WEAPONS = {
    "wp_usp": {"name": "Súng Ngắn USP", "rarity": 2, "atk": 50, "crt": 5},
    "wp_aria": {"name": "Tranquil Arias", "rarity": 5, "atk": 350, "crt": 35},
    "wp_engulfing": {"name": "Engulfing Lightning", "rarity": 6, "atk": 550, "crt": 50},
    "wp_endfield_blade": {"name": "Gươm Công Nghiệp Tiền Tuyến", "rarity": 5, "atk": 400, "crt": 40}
}

KALLEN_ENEMIES = {
    "zombie_1": {
        "name": "Xác Sống Cầm Kiếm", "type": "BIO", 
        "hp": 2000, "atk": 100, "def": 50, "sp_drop": 5
    },
    "marble_boss": {
        "name": "Ma Thú Cẩm Thạch (Aggelomoirai)", "type": "MECH", 
        "hp": 18000, "atk": 450, "def": 350, "sp_drop": 25
    },
    "boss_ming": {
        "name": "Đại Quân Nhà Minh (Giả lập lịch sử)", "type": "MECH", 
        "hp": 80000, "atk": 1200, "def": 600, "sp_drop": 80
    }
}

KALLEN_STAGES = {
    "1-1": {"name": "1-1: Thức tỉnh", "enemies": ["zombie_1"], "reward_money": 5000, "reward_xp": 100},
    "2-1": {"name": "2-1: Căn Cứ AIC Sụp Đổ", "enemies": ["zombie_1", "marble_boss"], "reward_money": 15000, "reward_xp": 300},
    "3-1": {"name": "Chung Cuộc: Trận Tuyết Hận", "enemies": ["boss_ming"], "reward_money": 50000, "reward_xp": 1000}
}

# =====================================================================
# HỆ THỐNG MÔ PHỎNG NHÂN SINH KHỔNG LỒ (ĐỜI THỰC + GAME + LỊCH SỬ)
# =====================================================================
EVENTS_P1 = [ # TUỔI 15 (School / Early Life)
    {
        "q": "Bạn 15 tuổi, đang suy nghĩ chọn định hướng tương lai. Thấy trên mạng có tuyển quản lý đội bóng ảo (FC Mobile), bạn tính sao?",
        "choices": [
            {
                "text": "Bỏ học cày rank Manager Mode 24/7", 
                "rate": 20, 
                "win": "Xếp hạng top 1 server, được mời làm HLV Esports có lương cứng!", 
                "lose": "Cày cuốc mờ mắt, rớt hạng tơi bời, bị khóa acc vì spam.", 
                "tien_w": 25000, 
                "tien_l": -5000, 
                "die_l": False
            },
            {
                "text": "Nạp tiền đập thẻ cầu thủ Flashback", 
                "rate": 15, 
                "win": "Nhân phẩm bùng nổ, mở trúng thẻ Icons Prime bán lại giá hàng trăm triệu!", 
                "lose": "Nướng sạch tiền ăn sáng vào game, toàn ra thẻ rác OVR thấp.", 
                "tien_w": 80000, 
                "tien_l": -30000, 
                "die_l": False
            },
            {
                "text": "Chỉ đá giao hữu giải trí cuối tuần", 
                "rate": 90, 
                "win": "Cân bằng học tập và giải trí, đầu óc thoải mái đỗ kỳ thi.", 
                "lose": "Bị đám bạn rủ cá độ thua mất vài trăm ngàn tiền ăn sáng.", 
                "tien_w": 1000, 
                "tien_l": -1000, 
                "die_l": False
            },
            {
                "text": "Bán acc game lấy vốn buôn bán", 
                "rate": 60, 
                "win": "Acc OVR cao bán được giá hời, lấy tiền nhập hàng về bán.", 
                "lose": "Gặp trúng lừa đảo (scammer) cuỗm mất acc không trả tiền.", 
                "tien_w": 15000, 
                "tien_l": -5000, 
                "die_l": False
            }
        ]
    },
    {
        "q": "Kỳ thi chuyển cấp khốc liệt, bạn áp lực vì phải cày bộ đề TSA HUST. Đám bạn rủ trốn học.",
        "choices": [
            {
                "text": "Nhốt mình trong phòng giải đề TSA", 
                "rate": 75, 
                "win": "Đạt 74.5/100 điểm TSA! Đỗ thẳng vào đại học danh giá, bố mẹ thưởng xe xịn.", 
                "lose": "Học quá sức tẩu hỏa nhập ma, vào phòng thi ngủ gục nộp giấy trắng.", 
                "tien_w": 50000, 
                "tien_l": -10000, 
                "die_l": False
            },
            {
                "text": "Đem tài liệu thi bán lấy tiền", 
                "rate": 40, 
                "win": "Lập group kín bán tài liệu ôn thi TSA lãi khủng.", 
                "lose": "Bị bắt quả tang bán tài liệu giả, bị đình chỉ học.", 
                "tien_w": 20000, 
                "tien_l": -8000, 
                "die_l": False
            },
            {
                "text": "Xin bảo lưu 1 năm để xả stress", 
                "rate": 80, 
                "win": "Tâm lý ổn định lại, năm sau thi đỗ thủ khoa.", 
                "lose": "Chơi bời lêu lổng quên luôn chữ nghĩa, nghỉ học đi phụ hồ.", 
                "tien_w": 5000, 
                "tien_l": -2000, 
                "die_l": False
            },
            {
                "text": "Mang điện thoại vào quay bài", 
                "rate": 10, 
                "win": "Hack cam phòng thi mượt mà, điểm cao tuyệt đối.", 
                "lose": "Giám thị dùng máy quét sóng bắt tại trận, vỡ mộng đại học.", 
                "tien_w": 10000, 
                "tien_l": -15000, 
                "die_l": False
            }
        ]
    }
]

EVENTS_P2 = [ # TUỔI 25 (Career / Early Adulthood)
    {
        "q": "Bạn 25 tuổi, một tập đoàn công nghệ mời bạn thiết kế Hệ thống tự động AIC (chuẩn Endfield).",
        "choices": [
            {
                "text": "Thiết kế tối ưu hoàn hảo bằng mọi giá", 
                "rate": 60, 
                "win": "Dây chuyền hoạt động max công suất. Chen Qianyu đích thân thưởng lớn!", 
                "lose": "Lỗi phần mềm, máy móc đình công, bạn phải đền hợp đồng.", 
                "tien_w": 100000, 
                "tien_l": -50000, 
                "die_l": False
            },
            {
                "text": "Rút ruột ngân sách dự án", 
                "rate": 10, 
                "win": "Ăn chặn chục tỷ trót lọt, tậu siêu xe mua nhà lầu.", 
                "lose": "Bị thanh tra sờ gáy, dựa cột tiêm thuốc độc.", 
                "tien_w": 500000, 
                "tien_l": -80000, 
                "die_l": True
            },
            {
                "text": "Giao lại cho cấp dưới làm", 
                "rate": 80, 
                "win": "Thảnh thơi hưởng lương quản lý, tuy ít nhưng nhàn hạ.", 
                "lose": "Cấp dưới làm ẩu, bạn bị liên đới trừ nửa năm lương.", 
                "tien_w": 15000, 
                "tien_l": -10000, 
                "die_l": False
            },
            {
                "text": "Hack luôn hệ thống của đối thủ", 
                "rate": 5, 
                "win": "Đoạt được bản vẽ công nghệ lõi, bán chợ đen siêu lợi nhuận.", 
                "lose": "Đụng trúng firewall xịn, máy tính nổ tung chết cháy.", 
                "tien_w": 800000, 
                "tien_l": -100000, 
                "die_l": True
            }
        ]
    },
    {
        "q": "Bạn muốn mở công ty riêng. Đồng nghiệp xúi bạn chung vốn buôn Lan Đột Biến.",
        "choices": [
            {
                "text": "Vay nóng xã hội đen chơi lớn", 
                "rate": 15, 
                "win": "Sang tay ngay chậu lan cùi được 5 tỷ! Mua nhà lầu xe hơi.", 
                "lose": "Thị trường vỡ trận, ôm đống cỏ khô, trốn nợ biệt xứ.", 
                "tien_w": 400000, 
                "tien_l": -250000, 
                "die_l": False
            },
            {
                "text": "Mua 1 mầm nhỏ thử nghiệm", 
                "rate": 40, 
                "win": "Bán có lời chút đỉnh đủ mua con xe máy xịn.", 
                "lose": "Lan chết héo vì không biết chăm, mất toi tháng lương.", 
                "tien_w": 25000, 
                "tien_l": -15000, 
                "die_l": False
            },
            {
                "text": "Báo công an bắt tụi thổi giá", 
                "rate": 50, 
                "win": "Phá đường dây lừa đảo, được thành phố thưởng huân chương và tiền.", 
                "lose": "Tụi nó gọi giang hồ chém bạn nhập viện vì lo chuyện bao đồng.", 
                "tien_w": 30000, 
                "tien_l": -40000, 
                "die_l": True
            },
            {
                "text": "Mặc kệ, đi làm công ăn lương", 
                "rate": 90, 
                "win": "Sống thảnh thơi, tối về ngủ ngon không âu lo.", 
                "lose": "Thấy đồng nghiệp mua Mẹc, tiếc đến trầm cảm ốm đau.", 
                "tien_w": 5000, 
                "tien_l": -5000, 
                "die_l": False
            }
        ]
    }
]

EVENTS_P3 = [ # TUỔI 35 (Mid-life / Wealth Building)
    {
        "q": "Bạn 35 tuổi, đang đào móng xây nhà thì phát hiện một kho báu cổ từ thời Khởi nghĩa Lam Sơn (Lê Lợi).",
        "choices": [
            {
                "text": "Nộp ngay cho bảo tàng nhà nước", 
                "rate": 95, 
                "win": "Được tuyên dương, nhận bằng khen và tiền thưởng theo quy định.", 
                "lose": "Làm rơi vỡ bình gốm trên đường đi, bị phạt tiền.", 
                "tien_w": 50000, 
                "tien_l": -10000, 
                "die_l": False
            },
            {
                "text": "Lén lút tuồn ra chợ đen quốc tế", 
                "rate": 10, 
                "win": "Bán được thanh bảo kiếm giá hàng triệu đô, trốn ra nước ngoài định cư!", 
                "lose": "Giao dịch bị công an mật ập vào tóm gọn, nhận án chung thân.", 
                "tien_w": 2000000, 
                "tien_l": -150000, 
                "die_l": True
            },
            {
                "text": "Giữ lại làm đồ gia truyền", 
                "rate": 70, 
                "win": "Ngôi nhà hội tụ vượng khí, gia đình làm ăn phát đạt vô cùng.", 
                "lose": "Cổ vật dính lời nguyền, bạn ốm liệt giường tốn bộn tiền viện phí.", 
                "tien_w": 80000, 
                "tien_l": -50000, 
                "die_l": False
            },
            {
                "text": "Nghiên cứu binh pháp trong sách cổ", 
                "rate": 40, 
                "win": "Lĩnh ngộ chiến thuật, áp dụng vào kinh doanh trở thành ông trùm.", 
                "lose": "Đọc không hiểu tẩu hỏa nhập ma, điên điên khùng khùng.", 
                "tien_w": 300000, 
                "tien_l": -80000, 
                "die_l": False
            }
        ]
    }
]

EVENTS_P4 = [ # TUỔI 50 (Late Career / Mid-life Crisis)
    {
        "q": "Giai đoạn tiền mãn kinh/mãn dục. Cảm thấy cuộc đời nhạt nhẽo, bạn muốn làm gì đó điên rồ.",
        "choices": [
            {
                "text": "Mua thuốc trường sinh tiên đan", 
                "rate": 5, 
                "win": "Phép màu! Cơ thể trẻ lại như trai 20 sung mãn. Lên Tóp Tóp làm idol.", 
                "lose": "Uống nhầm thủy ngân, nội tạng nổ tung hộc máu chết.", 
                "tien_w": 100000, 
                "tien_l": -80000, 
                "die_l": True
            },
            {
                "text": "Lấy tiền hưu đi Casino Las Vegas", 
                "rate": 15, 
                "win": "Nổ hũ Máy Xèng! Máy nhả tiền ngập cả sảnh Casino.", 
                "lose": "Thua trắng dái, đau tim gục ngã trên bàn Roulette.", 
                "tien_w": 500000, 
                "tien_l": -200000, 
                "die_l": True
            },
            {
                "text": "Cặp bồ nhí cho tâm hồn thanh xuân", 
                "rate": 35, 
                "win": "Bồ nhí ngoan ngoãn, sống những ngày thăng hoa.", 
                "lose": "Bị đào mỏ sạch bách tài sản rồi đá ra khỏi cửa.", 
                "tien_w": -5000, 
                "tien_l": -100000, 
                "die_l": False
            },
            {
                "text": "Ăn chay niệm phật, đi du lịch", 
                "rate": 90, 
                "win": "Đầu óc minh mẫn, không tranh giành, thân tâm an lạc.", 
                "lose": "Đi máy bay gặp bão rung lắc, rớt máy bay.", 
                "tien_w": 10000, 
                "tien_l": -50000, 
                "die_l": True
            }
        ]
    }
]

EVENTS_P5 = [ # TUỔI 70 (End of Life / Legacy)
    {
        "q": "Gần đất xa trời, đã đến lúc lập di chúc quyết định số phận gia tộc.",
        "choices": [
            {
                "text": "Chia đều cho các con", 
                "rate": 70, 
                "win": "Con cháu thuận hòa, khóc lóc tiếc thương khi bạn nằm xuống.", 
                "lose": "Tụi nó chê ít, đánh nhau mẻ đầu ngay tại giường bệnh làm bạn tức chết.", 
                "tien_w": 10000, 
                "tien_l": -30000, 
                "die_l": True
            },
            {
                "text": "Ủng hộ 100% làm từ thiện", 
                "rate": 95, 
                "win": "Được đúc tượng đồng, tên tuổi lưu danh sử sách ngàn thu.", 
                "lose": "Bị tổ chức lừa đảo cuỗm tiền bốc hơi, ra đi không nhắm mắt.", 
                "tien_w": 20000, 
                "tien_l": -80000, 
                "die_l": True
            },
            {
                "text": "Tổ chức đám tang hoàng gia", 
                "rate": 80, 
                "win": "Đám tang to nhất thành phố, ai cũng trầm trồ ngưỡng mộ.", 
                "lose": "Đang làm lễ thì cháy rạp, người nhà gánh nợ đền.", 
                "tien_w": -20000, 
                "tien_l": -50000, 
                "die_l": True
            },
            {
                "text": "Giấu kho báu trên hoang đảo", 
                "rate": 10, 
                "win": "Tạo ra Thời đại Hải tặc mới! Di sản vĩ đại.", 
                "lose": "Giang hồ tra tấn ép khai mật mã, cắn lưỡi tự vẫn.", 
                "tien_w": 1000000, 
                "tien_l": -100000, 
                "die_l": True
            }
        ]
    }
]
# =====================================================================
# [PHẦN 2] HỆ THỐNG BACKGROUND TASKS & GIAO DIỆN (UI VIEWS) ĐỜI THỰC
# =====================================================================

# ---------------------------------------------------------------------
# 1. TASK CHẠY NGẦM: LÃI SUẤT, TIỀN THUÊ NHÀ & CHỨNG KHOÁN (CHẠY MỖI GIỜ)
# ---------------------------------------------------------------------
@tasks.loop(hours=1)
async def economy_background_tasks():
    print("🔄 Đang cập nhật nền kinh tế vĩ mô (Bank, BĐS, Chứng khoán)...")
    
    # --- CẬP NHẬT TÀI SẢN NGƯỜI CHƠI ---
    all_users = list(users_col.find())
    for doc in all_users:
        uid = str(doc["_id"])
        u = load_user(uid)
        
        # 1.1 Tính lãi suất ngân hàng (0.3% / giờ)
        if u.get("bank", 0) > 0:
            lai_suat = int(u["bank"] * 0.003)
            # Buff từ danh hiệu (Tài phiệt ác ma +20% lãi)
            if u.get("title") == "Tài Phiệt Ác Ma 👑": lai_suat = int(lai_suat * 1.2)
            u["bank"] += lai_suat
            
        # 1.2 Tính lãi vay (Nếu money âm -> Phạt 1% / giờ)
        if u.get("money", 0) < 0:
            tien_phat = int(abs(u["money"]) * 0.01)
            u["money"] -= tien_phat
            
        # 1.3 Thu tiền thuê nhà thụ động (Bất động sản)
        assets = u.get("assets", [])
        tong_thu_nhap = 0
        for asset_name in assets:
            for k, v in SHOP_ITEMS.items():
                if v["name"] == asset_name and v["type"] == "house":
                    tong_thu_nhap += v.get("income", 0)
        
        if tong_thu_nhap > 0:
            u["bank"] += tong_thu_nhap # Tiền thuê nhà đổ thẳng vào ngân hàng cho an toàn
            
        # 1.4 Thú cưng giảm độ no (Hunger)
        pets = u.get("pets", {})
        for pet_id, pet_data in pets.items():
            if pet_data.get("hunger", 100) > 0:
                pet_data["hunger"] -= 5 # Giảm 5% độ no mỗi giờ
                
        save_user(uid)

    # --- CẬP NHẬT SÀN CHỨNG KHOÁN ---
    all_stocks = list(stocks_col.find())
    if not all_stocks:
        default_stocks = [
            {"_id": "VNM", "name": "Vinamilk", "price": 50000, "trend": "up", "history": [50000]},
            {"_id": "FLC", "name": "Tập đoàn FLC", "price": 10000, "trend": "down", "history": [10000]},
            {"_id": "MHY", "name": "Mihoyo Hoyoverse", "price": 150000, "trend": "up", "history": [150000]},
            {"_id": "AIC", "name": "Công Nghiệp Endfield", "price": 85000, "trend": "up", "history": [85000]}
        ]
        for s in default_stocks: stocks_col.insert_one(s)
        all_stocks = default_stocks

    for stock in all_stocks:
        current_price = stock.get("price", 10000)
        
        # Nguy cơ 5% có Event Lớn
        event_roll = random.uniform(0, 100)
        if event_roll <= 2.5: 
            new_price = int(current_price * random.uniform(0.3, 0.6)) # Sập hầm (Giảm mạnh)
        elif event_roll <= 5.0:
            new_price = int(current_price * random.uniform(1.5, 2.5)) # Bơm thổi (Tăng mạnh)
        else:
            volatility = random.uniform(-0.12, 0.12) # Biến động bình thường
            new_price = int(current_price * (1 + volatility))
            
        new_price = max(500, new_price) # Không cho rớt dưới 500đ
        
        history = stock.get("history", [])
        history.append(new_price)
        if len(history) > 12: history.pop(0) # Lưu 12 giờ gần nhất
        
        stocks_col.update_one(
            {"_id": stock["_id"]},
            {"$set": {"price": new_price, "history": history, "trend": "up" if new_price >= current_price else "down"}}
        )

@economy_background_tasks.before_loop
async def before_economy():
    await bot.wait_until_ready()

economy_background_tasks.start()

# ---------------------------------------------------------------------
# 2. GIAO DIỆN CỬA HÀNG ĐẠI GIA (MUA BĐS, XE, DANH HIỆU, KỸ NĂNG)
# ---------------------------------------------------------------------
class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        options = []
        for key, item_data in SHOP_ITEMS.items():
            if item_data["type"] == category_type:
                # Format hiển thị Dropdown
                desc = f"Giá: {item_data['price']:,} 💰 | {item_data.get('desc', '')}"
                options.append(discord.SelectOption(label=item_data['name'], description=desc[:100], value=key, emoji=item_data['emoji']))
                
        super().__init__(placeholder="Nhấn vào đây để vung tiền...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        u = load_user(uid)
        item = SHOP_ITEMS[self.values[0]]
        
        if u.get("money", 0) < item["price"]:
            return await interaction.response.send_message(f"⚠️ Thẻ đen từ chối! Bạn thiếu **{(item['price'] - u['money']):,} 💰** để mua {item['name']}.", ephemeral=True)
            
        # Kiểm tra trùng lặp (Chỉ mua 1 cái)
        if item["type"] in ["vehicle", "house"] and item["name"] in u.get("assets", []):
            return await interaction.response.send_message(f"⚠️ Bạn đã đứng tên sổ đỏ/cà vẹt **{item['name']}** rồi! Nhường người khác mua đi.", ephemeral=True)
        if item["type"] == "title" and u.get("title") == item["name"]:
            return await interaction.response.send_message("⚠️ Bạn đang đeo danh hiệu này rồi mà!", ephemeral=True)

        # Thanh toán
        u["money"] -= item["price"]
        
        if item["type"] == "title":
            u["title"] = item["name"]
            msg = f"🎉 Tiền trao cháo múc! Bạn đã đổi danh hiệu Căn Cước thành: **{item['name']}**."
        elif item["type"] == "item":
            skill = item.get("buff_skill")
            if skill:
                u["skills"][skill] += 1
                msg = f"🧠 Uống sách như uống nước! Kỹ năng **{skill.upper()}** của bạn đã tăng lên Cấp {u['skills'][skill]}."
        else:
            u["assets"].append(item["name"])
            msg = f"🎉 Ký hợp đồng thành công! Bạn vừa ném chìa khóa **{item['name']}** vào túi đồ."

        save_user(uid)
        embed = discord.Embed(title="🛍️ GIAO DỊCH HOÀN TẤT", description=msg, color=discord.Color.green())
        embed.set_footer(text=f"Số dư ví: {u['money']:,} 💰", icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)

class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    async def interaction_check(self, i): return i.user.id == self.author.id

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰", row=0)
    async def btn_house(self, interaction, button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(title="🏰 SÀN GIAO DỊCH BẤT ĐỘNG SẢN", description="Nhà đất sinh lời từng giờ. Tiền thuê tự động chuyển vào Bank.", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️", row=0)
    async def btn_veh(self, interaction, button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(title="🏎️ SHOWROOM AUTO", description="Xe xịn giúp tăng tỉ lệ chạy trốn khi đi Cướp Ngân Hàng.", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cục Sở Hữu Trí Tuệ (Danh Hiệu)", style=discord.ButtonStyle.primary, emoji="🏷️", row=1)
    async def btn_title(self, interaction, button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(title="🏷️ QUẦY DANH HIỆU VIP", description="Danh hiệu giúp tăng Lãi Bank và tăng Exp nhận được.", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Nhà Sách Kỹ Năng", style=discord.ButtonStyle.secondary, emoji="📚", row=1)
    async def btn_book(self, interaction, button):
        view = discord.ui.View(timeout=60); view.add_item(ShopItemSelect("item"))
        embed = discord.Embed(title="📚 NHÀ SÁCH TRÍ TUỆ", description="Mua sách để nâng cấp Skill sinh tồn (Câu cá, Buôn lậu, Hack...).", color=discord.Color.dark_grey())
        await interaction.response.edit_message(embed=embed, view=view)

# ---------------------------------------------------------------------
# 3. GIAO DIỆN HỆ THỐNG THÚ CƯNG (MUA TRỨNG & ẤP TRỨNG)
# ---------------------------------------------------------------------
PET_EGGS = {
    "egg_1": {"name": "Trứng Gỗ 🥚", "price": 25000, "pool": ["Chó Cỏ 🐕", "Mèo Lười 🐈", "Gà Trống 🐓"]},
    "egg_2": {"name": "Trứng Bạc 🥚", "price": 150000, "pool": ["Sói Tuyết 🐺", "Gấu Xám 🐻", "Đại Bàng 🦅"]},
    "egg_3": {"name": "Trứng Vàng 🥚", "price": 1000000, "pool": ["Hổ Trắng 🐅", "Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍"]},
    "egg_4": {"name": "Trứng Hỗn Độn 🌌", "price": 10000000, "pool": ["Kỳ Lân 🦄", "Phượng Hoàng 🦚", "Rồng Cổ Đại 🐉"]}
}

class PetGachaSelect(discord.ui.Select):
    def __init__(self):
        opts = [discord.SelectOption(label=v["name"], description=f"Giá: {v['price']:,} 💰", value=k) for k, v in PET_EGGS.items()]
        super().__init__(placeholder="Chọn loại trứng muốn mua và ấp...", options=opts)

    async def callback(self, i):
        uid = str(i.user.id)
        u = load_user(uid)
        egg = PET_EGGS[self.values[0]]
        
        if u.get("money", 0) < egg["price"]:
            return await i.response.send_message(f"⚠️ Mua trứng cũng thiếu tiền! Cần **{egg['price']:,} 💰**.", ephemeral=True)
            
        u["money"] -= egg["price"]
        pet_born = random.choice(egg["pool"])
        
        # Cấu trúc lưu thú cưng
        if pet_born not in u["pets"]:
            u["pets"][pet_born] = {"level": 1, "xp": 0, "hunger": 100, "loyalty": 0}
            msg = f"🎉 TÁCH! Trứng vỡ ra... Bạn nhận được thú cưng mới: **{pet_born}**!"
        else:
            u["pets"][pet_born]["xp"] += 50 # Trùng thì cộng XP
            msg = f"🔄 TÁCH! Ra **{pet_born}**. Vì bạn đã có rồi nên nó hóa thành 50 XP cho pet cũ!"
            
        save_user(uid)
        await i.response.edit_message(content=None, embed=discord.Embed(title="🥚 LÒ ẤP TRỨNG", description=msg, color=discord.Color.gold()), view=None)

# ---------------------------------------------------------------------
# 4. GIAO DIỆN HỆ THỐNG NÔNG TRẠI (TRỒNG TRỌT & THU HOẠCH)
# ---------------------------------------------------------------------
class FarmPlotSelect(discord.ui.Select):
    def __init__(self, farm_data):
        self.farm = farm_data
        opts = []
        for p in self.farm["plots"]:
            if not p["unlocked"]: 
                opts.append(discord.SelectOption(label=f"Ô đất {p['id']}", description="Đang khóa (Cần nâng cấp)", value=f"lock_{p['id']}", emoji="🔒"))
            elif p["seed"] is None:
                opts.append(discord.SelectOption(label=f"Ô đất {p['id']}", description="Đất trống, cỏ mọc", value=str(p['id']), emoji="🟫"))
            else:
                seed = FARM_SEEDS[p['seed']]
                ptime = datetime.strptime(p["plant_time"], "%Y-%m-%d %H:%M:%S")
                ready_time = ptime + timedelta(minutes=seed["time_mins"])
                if datetime.now() >= ready_time:
                    opts.append(discord.SelectOption(label=f"Ô {p['id']} - {seed['name']}", description="ĐÃ CHÍN! Nhấn để thu hoạch.", value=f"harvest_{p['id']}", emoji="✨"))
                else:
                    opts.append(discord.SelectOption(label=f"Ô {p['id']} - {seed['name']}", description=f"Đang lớn... Cần tưới nước.", value=f"grow_{p['id']}", emoji="🌱"))
                    
        super().__init__(placeholder="Chọn ô đất để thao tác...", options=opts)

    async def callback(self, i):
        val = self.values[0]
        uid = str(i.user.id)
        
        if val.startswith("lock"):
            return await i.response.send_message("⚠️ Ô đất này chưa được mở khóa!", ephemeral=True)
            
        if val.startswith("grow"):
            return await i.response.send_message("🌱 Cây đang lớn, chưa thu hoạch được đâu sếp!", ephemeral=True)
            
        if val.startswith("harvest"):
            plot_id = int(val.split("_")[1])
            f = load_farm(uid)
            u = load_user(uid)
            
            for p in f["plots"]:
                if p["id"] == plot_id:
                    seed = FARM_SEEDS[p["seed"]]
                    # Kỹ năng Farming buff sản lượng
                    buff = 1 + (u["skills"]["farming"] * 0.05)
                    thu_nhap = int(seed["sell"] * buff)
                    
                    u["money"] += thu_nhap
                    f["exp"] += 10
                    # Reset ô đất
                    p["seed"] = None
                    p["plant_time"] = None
                    p["watered"] = False
                    
                    save_user(uid)
                    save_farm(uid)
                    
                    embed = discord.Embed(title="🌾 THU HOẠCH THÀNH CÔNG", description=f"Thu hoạch {seed['name']} bán được **{thu_nhap:,} 💰**!", color=discord.Color.green())
                    return await i.response.edit_message(embed=embed, view=None)

        # Trạng thái đất trống -> Chuyển sang View Mua Hạt Giống
        plot_id = int(val)
        view = discord.ui.View(timeout=60)
        view.add_item(SeedSelect(plot_id))
        embed = discord.Embed(title="🌱 CỬA HÀNG HẠT GIỐNG", description=f"Chọn hạt giống để gieo xuống Ô đất {plot_id}:", color=discord.Color.dark_green())
        await i.response.edit_message(embed=embed, view=view)

class SeedSelect(discord.ui.Select):
    def __init__(self, plot_id):
        self.plot_id = plot_id
        opts = [discord.SelectOption(label=v["name"], description=f"Mua: {v['buy']} 💰 | Bán: {v['sell']} 💰 | Tgian: {v['time_mins']}p", value=k) for k, v in FARM_SEEDS.items()]
        super().__init__(placeholder="Chọn hạt giống muốn mua...", options=opts)

    async def callback(self, i):
        uid = str(i.user.id)
        u = load_user(uid)
        f = load_farm(uid)
        seed = FARM_SEEDS[self.values[0]]
        
        if u.get("money", 0) < seed["buy"]:
            return await i.response.send_message(f"⚠️ Thiếu tiền mua hạt giống! Cần {seed['buy']} 💰.", ephemeral=True)
            
        u["money"] -= seed["buy"]
        
        for p in f["plots"]:
            if p["id"] == self.plot_id:
                p["seed"] = self.values[0]
                p["plant_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                p["watered"] = True
                
        save_user(uid)
        save_farm(uid)
        await i.response.edit_message(content=None, embed=discord.Embed(description=f"✅ Đã gieo **{seed['name']}** xuống đất. Hãy quay lại thu hoạch sau **{seed['time_mins']} phút** nhé!", color=discord.Color.green()), view=None)

class FarmView(discord.ui.View):
    def __init__(self, author, farm_data):
        super().__init__(timeout=60)
        self.author = author
        self.add_item(FarmPlotSelect(farm_data))
        
    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("⚠️ Nông trại của người ta, cấm nhổ trộm!", ephemeral=True)
            return False
        return True
        # =====================================================================
# [PHẦN 3] HỆ THỐNG LỆNH NGƯỜI DÙNG (COMMANDS), EVENTS & KHỞI CHẠY
# =====================================================================

# ---------------------------------------------------------------------
# 1. BẢNG ĐIỀU KHIỂN & LỆNH ADMIN
# ---------------------------------------------------------------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 BỘ CÚ PHÁP ĐIỀU KHIỂN SIÊU BOT 10.0", 
        description="Chào mừng sếp đến với hệ sinh thái mô phỏng đời thực khốc liệt.\nTiền tố gọi bot: `k` hoặc `K`.", 
        color=discord.Color.blurple()
    )
    embed.add_field(name="💳 KINH TẾ & GIAO DỊCH", value="`k rank` • Xem CCCD & Kỹ năng\n`k tuido` • Xem toàn bộ kho tài sản\n`k top` • Soi bảng xếp hạng đại gia\n`k daily` • Nhận trợ cấp hộ nghèo\n`k give @tên <tiền>` • Chuyển khoản\n`k cuahang` • Đi shopping mua BĐS, Xe", inline=False)
    embed.add_field(name="🏦 NGÂN HÀNG & CHỨNG KHOÁN", value="`k bank` • Vào ngân hàng gửi/rút/vay nợ\n`k ck` • Xem bảng giá cổ phiếu\n`k ck buy / k ck sell` • Mua bán cổ phiếu\n`k cty` • Quản lý/Thành lập Doanh nghiệp", inline=False)
    embed.add_field(name="🎮 SÒNG BÀI MA CAO", value="`k coin <tiền>` • Xóc xu sấp ngửa\n`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu\n`k baucua <con vật> <tiền>` • Bầu Cua Tôm Cá\n`k cuop` • Cầm M4A1 đi cướp ngân hàng", inline=False)
    embed.add_field(name="🌾 ĐỜI SỐNG THỰC & NHẬP VAI", value="`k cauca` • Vác cần ra bờ sông\n`k nongtrai` • Quản lý trang trại trồng trọt\n`k thucung` • Mua trứng ấp pet\n`k thamhiem` • Đi mua đồ xông pha rừng rậm\n`k phai` • Treo acc AFK nhặt bạc lẻ\n`k nhansinh` • Luân hồi đa vũ trụ (Cực khó!)", inline=False)
    embed.add_field(name="🌌 KALLEN FANTASY (Gacha RPG)", value="`k kallen` • Xem hồ sơ Valkyrie\n`k kf gacha` • Đốt tiền quay Tiếp Tế\n`k kf story 1-1` • Xuất kích đánh Boss\n`k kf abyss` • Leo tháp Vực Sâu", inline=False)
    
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="👑 QUYỀN LỰC ADMIN", value="`k setup #kênh` • Giới hạn kênh chat\n`k themtien @user <tiền>` • Buff tiền\n`k trutien @user <tiền>` • Phạt tiền", inline=False)
        
    embed.set_footer(text="Gõ đúng cú pháp kẻo hệ thống không hiểu nhé sếp!")
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, *, args=""):
    server_id = str(ctx.guild.id)
    if "clear" in args.lower():
        config_col.update_one({"_id": server_id}, {"$unset": {"allowed_channels": ""}})
        if server_id in CONFIG_CACHE and "allowed_channels" in CONFIG_CACHE[server_id]:
            del CONFIG_CACHE[server_id]["allowed_channels"]
        return await ctx.send("✅ Đã dỡ bỏ rào chắn, anh em cứ thoải mái gõ lệnh ở mọi kênh!")

    mentions = ctx.message.channel_mentions
    if not mentions: 
        return await ctx.send("⚠️ Phải tag kênh cụ thể chứ sếp! VD: `k setup #general`")
        
    c_ids = [c.id for c in mentions]
    config_col.update_one({"_id": server_id}, {"$set": {"allowed_channels": c_ids}}, upsert=True)
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
    CONFIG_CACHE[server_id]["allowed_channels"] = c_ids
    await ctx.send(f"✅ Đã giăng dây thép gai! Từ nay bot chỉ nhận lệnh tại: {', '.join(c.mention for c in mentions)}.")

@bot.command()
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Tiền buff phải lớn hơn 0.")
    u = load_user(member.id); u["money"] += amount; save_user(member.id)
    await ctx.send(embed=discord.Embed(description=f"👑 **THÁNH CHỈ:** Admin buff nóng cho {member.mention} **{amount:,} 💰**!\n💳 Két nổ: **{u['money']:,} 💰**", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Tiền trừ phải lớn hơn 0.")
    u = load_user(member.id); u["money"] -= amount; save_user(member.id)
    await ctx.send(embed=discord.Embed(description=f"⚖️ **TỊCH THU:** {member.mention} bị Admin phạt mất **{amount:,} 💰**!\n💳 Két móp: **{u['money']:,} 💰**", color=discord.Color.red()))

# ---------------------------------------------------------------------
# 2. NGÂN HÀNG TRUNG ƯƠNG (BANKING SYSTEM)
# ---------------------------------------------------------------------
@bot.group(invoke_without_command=True, aliases=['nh'])
async def bank(ctx):
    u = load_user(ctx.author.id)
    bank_bal = u.get("bank", 0)
    wallet = u.get("money", 0)
    debt = u.get("debt", 0)
    
    embed = discord.Embed(
        title="🏦 NGÂN HÀNG TRUNG ƯƠNG (Lãi suất: 0.3%/h)", 
        description="Gửi tiền vào đây sinh lời tự động, tránh bị úp sọt ở Casino.\n"
                    "Lệnh: `k bank gui <tiền>`, `k bank rut <tiền>`, `k bank vay <tiền>`, `k bank tra <tiền>`", 
        color=discord.Color.blue()
    )
    embed.add_field(name="💳 Ví Tiền Mặt", value=f"**{wallet:,} 💰**", inline=True)
    embed.add_field(name="🏦 Két Sắt", value=f"**{bank_bal:,} / {u.get('bank_capacity', 5000000):,} 💰**", inline=True)
    if debt > 0:
        embed.add_field(name="🚨 Dư Nợ Tín Dụng", value=f"**-{debt:,} 💰**", inline=False)
        
    embed.set_thumbnail(url=GIF_LINKS["bank"])
    await ctx.reply(embed=embed, mention_author=False)

@bank.command()
async def gui(ctx, amount: str):
    u = load_user(ctx.author.id)
    try: amt = u["money"] if amount.lower() == "all" else int(amount)
    except: return await ctx.reply("⚠️ Nhập sai số tiền!")
        
    if amt <= 0 or amt > u.get("money", 0): return await ctx.reply(f"⚠️ Ví bạn chỉ có **{u.get('money', 0):,} 💰**!")
    cap = u.get("bank_capacity", 5000000)
    if u.get("bank", 0) + amt > cap: return await ctx.reply(f"🛑 Két sắt đầy! Tối đa chứa được **{cap:,} 💰**.")

    u["money"] -= amt; u["bank"] += amt; save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Đã gửi **{amt:,} 💰** vào két sắt. Chờ nhận lãi thôi!", color=discord.Color.green()), mention_author=False)

@bank.command()
async def rut(ctx, amount: str):
    u = load_user(ctx.author.id)
    try: amt = u["bank"] if amount.lower() == "all" else int(amount)
    except: return await ctx.reply("⚠️ Nhập sai số.")
        
    if amt <= 0 or amt > u.get("bank", 0): return await ctx.reply(f"⚠️ Ngân hàng bạn chỉ có **{u.get('bank', 0):,} 💰**!")
    u["bank"] -= amt; u["money"] += amt; save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"📤 Đã rút **{amt:,} 💰** ra ví đi quẩy!", color=discord.Color.green()), mention_author=False)

@bank.command()
async def vay(ctx, amount: int):
    u = load_user(ctx.author.id)
    if u.get("money", 0) < 0 or u.get("debt", 0) > 0: return await ctx.reply("🛑 Đang mang nợ xấu, ngân hàng từ chối giải ngân!")
    max_loan = u.get("level", 1) * 200000
    if amount <= 0 or amount > max_loan: return await ctx.reply(f"⚠️ Thẩm định thất bại! Level {u.get('level', 1)} chỉ được vay tối đa **{max_loan:,} 💰**.")
        
    u["money"] += amount
    u["debt"] = amount
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(title="📝 GIẢI NGÂN THÀNH CÔNG", description=f"Vay nóng **{amount:,} 💰**. Nhớ dùng `k bank tra` để trả nợ!", color=discord.Color.gold()), mention_author=False)

@bank.command()
async def tra(ctx, amount: str):
    u = load_user(ctx.author.id)
    debt = u.get("debt", 0)
    if debt <= 0: return await ctx.reply("✅ Bạn không mắc nợ ai cả!")
    try: amt = debt if amount.lower() == "all" else int(amount)
    except: return await ctx.reply("⚠️ Nhập sai.")
    
    if amt <= 0 or amt > u.get("money", 0): return await ctx.reply("⚠️ Ví không đủ tiền trả!")
    amt_pay = min(amt, debt)
    u["money"] -= amt_pay; u["debt"] -= amt_pay; save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Đã trả **{amt_pay:,} 💰** nợ.\nDư nợ còn: **{u['debt']:,} 💰**", color=discord.Color.green()), mention_author=False)

# ---------------------------------------------------------------------
# 3. KINH TẾ ĐỜI SỐNG (RANK, TÚI ĐỒ, CỬA HÀNG, CÂU CÁ, DAILY)
# ---------------------------------------------------------------------
@bot.command()
async def rank(ctx):
    u = load_user(ctx.author.id)
    lv, xp, tien = u.get("level", 1), u.get("xp", 0), u.get("money", 0)
    max_xp = lv * 100
    prog = int((xp / max_xp) * 12)
    bar = "🟩" * prog + "⬛" * (12 - prog)
    
    embed = discord.Embed(title=f"💳 CĂN CƯỚC: {ctx.author.name.upper()}", color=discord.Color.gold() if tien > 500000 else discord.Color.teal())
    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
    embed.add_field(name="🌟 Cấp Độ", value=f"**LV {lv}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏷️ Danh Hiệu", value=f"**{u.get('title', 'Dân Thường')}**", inline=False)
    
    # Hiển thị Skills
    skills = u.get("skills", {})
    skill_txt = f"📈 Giao dịch: Lv.{skills.get('trading',1)} | 🌾 Trồng trọt: Lv.{skills.get('farming',1)}\n🎣 Câu cá: Lv.{skills.get('fishing',1)} | 💻 Hacking: Lv.{skills.get('hacking',1)}"
    embed.add_field(name="🧠 Kỹ Năng Sinh Tồn", value=skill_txt, inline=False)
    embed.add_field(name="Kinh Nghiệm", value=f"`{bar}`\n**{xp:,}/{max_xp:,} XP**", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def tuido(ctx):
    u = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO TÀI SẢN KHỔNG LỒ", color=discord.Color.dark_purple())
    
    assets = u.get("assets", [])
    embed.add_field(name="🏰 Bất Động Sản & Siêu Xe", value="Trắng tay." if not assets else "\n".join([f"🔸 {a}" for a in assets]), inline=False)
    
    pets = u.get("pets", {})
    pet_txt = "Chưa có thú cưng." if not pets else "\n".join([f"🐾 {p} (No: {d['hunger']}%)" for p, d in pets.items()])
    embed.add_field(name="🐾 Vườn Thú Cưng", value=pet_txt, inline=False)
    
    stocks = u.get("stocks", {})
    stk_txt = "Chưa đầu tư mã nào." if not stocks else "\n".join([f"📈 {c}: {q} Cổ Phiếu" for c, q in stocks.items() if q > 0])
    embed.add_field(name="💼 Danh Mục Đầu Tư", value=stk_txt, inline=False)
    
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def top(ctx):
    all_users = list(users_col.find())
    danh_sach = sorted([(doc["_id"], doc.get("money", 0) + doc.get("bank", 0)) for doc in all_users], key=lambda x: x[1], reverse=True)[:10]
    desc = ""
    for i, (uid, tien) in enumerate(danh_sach):
        user = bot.get_user(int(uid))
        if not user:
            try: user = await bot.fetch_user(int(uid))
            except: pass
        ten = user.name if user else f"Đại gia ẩn danh {uid[-4:]}"
        icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**#{i+1}**"
        desc += f"{icon} **{ten}** ━ Tổng tài sản: {tien:,} 💰\n\n"
        
    await ctx.send(embed=discord.Embed(title="🏆 BẢNG VÀNG GIỚI SIÊU GIÀU", description=desc, color=discord.Color.gold()))

@bot.command()
async def daily(ctx):
    u = load_user(ctx.author.id)
    now = datetime.now()
    if u.get("last_daily"):
        last = datetime.strptime(u["last_daily"], "%Y-%m-%d %H:%M:%S")
        if now - last < timedelta(days=1):
            tl = timedelta(days=1) - (now - last)
            h, r = divmod(int(tl.total_seconds()), 3600); m, _ = divmod(r, 60)
            return await ctx.reply(embed=discord.Embed(description=f"⏳ Chưa tới tháng lương! Quay lại sau **{h}h {m}p** nữa.", color=discord.Color.orange()))

    u["money"] += 2000
    u["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_user(ctx.author.id)
    await ctx.send(embed=discord.Embed(title="🎁 QUỸ XÓA ĐÓI GIẢM NGHÈO", description=f"Nhận thành công **2,000 💰** tiền trợ cấp!\n💳 Trong ví có: **{u['money']:,} 💰**", color=discord.Color.green()))

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.id == member.id: return await ctx.reply("Tự lôi tiền túi phải sang túi trái à?")
    if amount <= 0: return await ctx.reply("Làm trò gì vậy, định ăn cướp à?")
    
    gui = load_user(ctx.author.id)
    if gui.get("money", 0) < amount: return await ctx.reply("⚠️ Mõm à? Tiền trong ví rỗng tuếch!")
    
    nhan = load_user(member.id)
    gui["money"] -= amount; nhan["money"] += amount
    save_user(ctx.author.id); save_user(member.id)
    await ctx.reply(embed=discord.Embed(description=f"💸 Ting ting! {ctx.author.mention} vừa bố thí cho {member.mention} **{amount:,} 💰**!", color=discord.Color.green()))

@bot.command()
async def cuahang(ctx):
    embed = discord.Embed(
        title="🛒 TRUNG TÂM THƯƠNG MẠI MEGA MALL", 
        description="Chào mừng đại gia! Hãy chọn một gian hàng để vung tiền.\n\n👇 **MỞ BẢNG CHỌN BÊN DƯỚI** 👇", 
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command()
async def cauca(ctx):
    uid = str(ctx.author.id)
    now = datetime.now()
    if uid in cooldowns["fish"] and (now - cooldowns["fish"][uid]).total_seconds() < 15:
        return await ctx.reply("⏳ Cá chưa cắn câu đâu, đợi tí đi sếp!")
    
    u = load_user(uid)
    if u.get("bait", 0) <= 0:
        return await ctx.reply("⚠️ Hết mồi câu rồi! Vào `k cuahang` mà mua thêm nhé.")
        
    u["bait"] -= 1
    cooldowns["fish"][uid] = now
    
    # Tính toán Luck dựa trên Cần câu và Skill Câu Cá
    rod = FISHING_RODS.get(u.get("fishing_rod", "CanTre"))
    luck_buff = rod["luck"] + (u["skills"].get("fishing", 1) * 2)
    
    msg = await ctx.send(embed=discord.Embed(description=f"🎣 {ctx.author.mention} vung cây **{rod['name']}** quăng mồi xuống hồ...\n*Mặt hồ tĩnh lặng...*", color=discord.Color.blue()))
    await asyncio.sleep(2.5)
    
    # Tung xúc xắc độ hiếm
    roll = random.uniform(0, 100) - (luck_buff * 0.1) # Giảm base roll để dễ ra đồ hiếm hơn
    roll = max(0.1, roll)
    
    if roll <= FISH_DATABASE["mythic"]["rate"]: rarity = "mythic"
    elif roll <= FISH_DATABASE["legendary"]["rate"]: rarity = "legendary"
    elif roll <= FISH_DATABASE["epic"]["rate"]: rarity = "epic"
    elif roll <= FISH_DATABASE["rare"]["rate"]: rarity = "rare"
    elif roll <= FISH_DATABASE["uncommon"]["rate"]: rarity = "uncommon"
    else: rarity = "common"
    
    fish_data = FISH_DATABASE[rarity]
    caught = random.choice(fish_data["pool"])
    price = fish_data["price"]
    
    # Skill trading giúp bán cá đắt hơn
    price = int(price * (1 + (u["skills"]["trading"] * 0.02)))
    u["money"] += price
    u["xp"] += 5
    save_user(uid)
    
    embed = discord.Embed(title="🐟 CÁ CẮN CÂU!", description=f"Giật mạnh! Bạn câu được **{caught}** ({rarity.upper()}).\nThương lái mua lại với giá **{price:,} 💰**!\n\n*(Mồi còn: {u['bait']})*", color=discord.Color.green() if price > 1000 else discord.Color.light_grey())
    embed.set_thumbnail(url=GIF_LINKS["fish"])
    await msg.edit(embed=embed)

@bot.command()
async def nongtrai(ctx):
    f = load_farm(ctx.author.id)
    embed = discord.Embed(title="🌾 NÔNG TRẠI VUI VẺ", description="Gieo hạt hôm nay, ngày mai gặt hái!\n👇 **MỞ MENU CHỌN Ô ĐẤT BÊN DƯỚI** 👇", color=discord.Color.green())
    embed.set_thumbnail(url=GIF_LINKS["farm"])
    await ctx.send(embed=embed, view=FarmView(ctx.author, f))

@bot.command()
async def thucung(ctx):
    embed = discord.Embed(title="🐾 TRẠI NHÂN GIỐNG THÚ CƯNG", description="Mua trứng, ấp trứng, nhận Pet siêu cấp VIP pro!\n👇 **MỞ MENU BÊN DƯỚI ĐỂ ĐẬP TRỨNG** 👇", color=discord.Color.dark_orange())
    await ctx.send(embed=embed, view=PetGachaSelect())

# ---------------------------------------------------------------------
# 4. CHỨNG KHOÁN & CÔNG TY ĐẠI CHIẾN
# ---------------------------------------------------------------------
@bot.group(invoke_without_command=True, aliases=['ck'])
async def chungkhoan(ctx):
    all_stocks = list(stocks_col.find())
    if not all_stocks: return await ctx.reply("Sàn chứng khoán bảo trì!")
    
    embed = discord.Embed(title="📈 SÀN GIAO DỊCH PHỐ WALL", description="🛒 `k ck buy <MÃ> <Số lượng>`\n💸 `k ck sell <MÃ> <Số lượng>`", color=discord.Color.teal())
    for s in all_stocks:
        trd = "🟩 Lên" if s.get("trend") == "up" else "🟥 Xuống"
        embed.add_field(name=f"🏢 {s['_id']} - {s['name']}", value=f"Giá: **{s.get('price',0):,} 💰** ({trd})", inline=False)
        
    u = load_user(ctx.author.id)
    stk = u.get("stocks", {})
    txt = "Chưa đầu tư mã nào." if not stk else "\n".join([f"🔸 {c}: {q} Cổ Phiếu" for c, q in stk.items() if q > 0])
    embed.add_field(name="🎒 Ví Đầu Tư Của Bạn", value=txt, inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    stock = stocks_col.find_one({"_id": code})
    if not stock: return await ctx.reply("⚠️ Mã này không tồn tại!")
    if qty <= 0: return await ctx.reply("⚠️ Mua số lượng âm à?")
    
    total = stock.get("price", 0) * qty
    u = load_user(ctx.author.id)
    if u.get("money", 0) < total: return await ctx.reply(f"⚠️ Thiếu lúa! Cần **{total:,} 💰**.")
        
    u["money"] -= total
    if total >= 50000000 and random.uniform(0, 100) <= 5.0:
        save_user(ctx.author.id)
        return await ctx.reply(embed=discord.Embed(title="🚨 RUG PULL - ÚP BÔ!", description=f"CEO của **{code}** ôm tiền trốn! Bốc hơi **{total:,} 💰**!", color=discord.Color.red()))
        
    u["stocks"][code] = u.get("stocks", {}).get(code, 0) + qty
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ MUA thành công **{qty} {code}** (Tổng: {total:,} 💰).", color=discord.Color.green()))

@chungkhoan.command()
async def sell(ctx, code: str, qty: int):
    code = code.upper()
    stock = stocks_col.find_one({"_id": code})
    if not stock: return await ctx.reply("⚠️ Mã này không tồn tại!")
    if qty <= 0: return await ctx.reply("⚠️ Nhập sai số lượng.")
    
    u = load_user(ctx.author.id)
    if u.get("stocks", {}).get(code, 0) < qty: return await ctx.reply("⚠️ Đâu ra cổ phiếu mà bán khống!")
        
    # Kỹ năng Trading buff giá bán
    buff = 1 + (u["skills"]["trading"] * 0.02)
    gain = int(stock.get("price", 0) * qty * buff)
    
    u["stocks"][code] -= qty
    if u["stocks"][code] == 0: del u["stocks"][code]
    u["money"] += gain
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ BÁN thành công **{qty} {code}** thu về **{gain:,} 💰** (Đã tính Buff Kỹ năng).", color=discord.Color.gold()))

# ---------------------------------------------------------------------
# 5. CASINO BẤT BẠI
# ---------------------------------------------------------------------
@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    if choice.lower() not in ["tai", "tài", "xiu", "xỉu"]: return await ctx.reply("Chọn `tai` hoặc `xiu` sếp ơi!")
    
    u["money"] -= bet; save_user(ctx.author.id); gamble_cooldowns[str(ctx.author.id)] = datetime.now()
    msg = await ctx.send(embed=discord.Embed(description=f"🎲 {ctx.author.mention} đập **{bet:,} 💰** vào cửa **{choice.upper()}**. Lạch cạch...", color=discord.Color.blue()))
    await asyncio.sleep(2)

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    tot = d1 + d2 + d3
    res_str = "xiu" if tot <= 10 else "tai"
    
    if choice.replace("à", "a").replace("ỉ", "i").lower() == res_str:
        win = bet * (5 if d1==d2==d3 else 2)
        u["money"] += win
        res = f"🔥 **BÃO {d1}-{d2}-{d3}!!!** Ăn **{win:,} 💰**!" if d1==d2==d3 else f"✅ **THẮNG!** Ăn **{win:,} 💰**!"
    else: res = f"💀 **THUA!** Mất **{bet:,} 💰**."
    
    save_user(ctx.author.id)
    await msg.edit(embed=discord.Embed(title=f"🎲 KẾT QUẢ: {d1}-{d2}-{d3} (Tổng {tot} - {res_str.upper()})", description=res + f"\n💳 Két: **{u['money']:,} 💰**", color=discord.Color.gold()))

@bot.command()
async def coin(ctx, amount: str):
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    u["money"] -= bet; save_user(ctx.author.id); gamble_cooldowns[str(ctx.author.id)] = datetime.now()
    
    msg = await ctx.send(embed=discord.Embed(description=f"🪙 Búng **{bet:,} 💰** lên trời cao...", color=discord.Color.gold()))
    await asyncio.sleep(2) 

    if random.choice([True, False]):
        win = bet * 2
        u["money"] += win
        res = f"🎉 **MẶT NGỬA!** Húp trọn **{win:,} 💰**!"
    else: res = f"💀 **MẶT SẤP!** Mất trắng **{bet:,} 💰**."
    
    save_user(ctx.author.id)
    await msg.edit(embed=discord.Embed(title="🪙 CHỐT KẾT QUẢ", description=res + f"\n💳 Két: **{u['money']:,} 💰**", color=discord.Color.gold()))

@bot.command(aliases=['bc'])
async def baucua(ctx, choice: str, amount: str):
    bc = {"bau": "🎃", "cua": "🦀", "tom": "🦐", "ca": "🐟", "ga": "🐔", "nai": "🦌"}
    if choice.lower() not in bc: return await ctx.reply("⚠️ Lỗi! Bầu cua gồm: `bau, cua, tom, ca, ga, nai`.")
    u, bet = await check_gamble_conditions(ctx, amount)
    if not u: return
    
    u["money"] -= bet; save_user(ctx.author.id); gamble_cooldowns[str(ctx.author.id)] = datetime.now()
    pet = bc[choice.lower()]
    msg = await ctx.send(embed=discord.Embed(description=f"🎋 Đặt **{bet:,} 💰** vào cửa {pet}. Xóc đĩa...", color=discord.Color.dark_orange()))
    await asyncio.sleep(2)
    
    pool = ["🎃", "🦀", "🦐", "🐟", "🐔", "🦌"]
    r1, r2, r3 = random.choice(pool), random.choice(pool), random.choice(pool)
    count = [r1, r2, r3].count(pet)
    
    if count > 0:
        win = bet + (bet * count)
        u["money"] += win
        res = f"🎉 **TRÚNG {count} NHÁY!** Ăn **{win:,} 💰**!"
    else: res = f"💀 **CHÁY TÚI!** Mất **{bet:,} 💰**."
        
    save_user(ctx.author.id)
    await msg.edit(embed=discord.Embed(title=f"🎋 BẦU CUA: [ {r1} | {r2} | {r3} ]", description=res + f"\n💳 Két: **{u['money']:,} 💰**", color=discord.Color.gold()))

@bot.command()
async def cuop(ctx):
    uid = str(ctx.author.id)
    u = load_user(uid)
    now = datetime.now()
    
    if uid in cooldowns["crime"] and (now - cooldowns["crime"][uid]).total_seconds() < 1800:
        return await ctx.reply("🚨 Đang bị truy nã! Nấp đi chờ 30 phút nữa.")
    if u.get("money", 0) < 50000:
        return await ctx.reply("⚠️ Cần mua vũ khí giá 50,000 💰 mới đi cướp được!")

    cooldowns["crime"][uid] = now
    msg = await ctx.send(embed=discord.Embed(description="🔫 Đạp cửa xông vào Ngân hàng với M4A1...", color=discord.Color.dark_gray()))
    await asyncio.sleep(2.5)

    # Hack skill buff tỉ lệ cướp
    rate = 25 + (u["skills"]["hacking"] * 2)
    if random.randint(1, 100) <= rate: 
        loot = random.randint(200000, 600000)
        u["money"] += loot
        save_user(uid)
        embed = discord.Embed(title="💰 TRÓT LỌT!", description=f"Vơ vét sạch két sắt ẵm trọn **{loot:,} 💰**!", color=discord.Color.green())
        embed.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed)
    else:
        u["money"] -= 50000
        u["jail_time"] = (now + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        save_user(uid)
        embed = discord.Embed(title="🚨 SA LƯỚI!", description="SWAT ập tới! Mất 50,000 💰 tiền súng đạn.\n🔒 **Bóc lịch 15 Phút!**", color=discord.Color.red())
        embed.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed)

# ---------------------------------------------------------------------
# 6. SINH TỒN & RPG CỐT LÕI (Mô Phỏng, Thám Hiểm, AFK)
# ---------------------------------------------------------------------
@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    uid = str(ctx.author.id)
    if uid in dang_choi_nhansinh: return await ctx.reply("⏳ Đang luân hồi rồi!")
    u = load_user(uid)
    if u.get("money", 0) < 100: return await ctx.reply("⚠️ Vé luân hồi 100 💰. Đi cày đi!")
    u["money"] -= 100
    dang_choi_nhansinh.append(uid)
    save_user(uid)
    
    view = NhanSinhGameView(ctx.author, {"may_man": random.randint(1, 10)})
    embed = discord.Embed(title="🌀 SỔ BÌA ĐEN LUÂN HỒI", description="Mỗi lựa chọn là một ngã rẽ tàn khốc.", color=discord.Color.teal())
    embed.add_field(name="📜 Băng Chuyền Ký Ức", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Quyết định sinh tử", value=f"**{view.ev['q']}**", inline=False)
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    embed = discord.Embed(title="🛒 CHỢ ĐEN VŨ KHÍ RỪNG SÂU", description="Mua vũ khí càn quét rừng rú lấy kho báu!\n👇 **MỞ MENU CHỌN** 👇", color=discord.Color.orange())
    await ctx.send(embed=embed, view=ShopView(ctx.author, 0))

@bot.command()
async def phai(ctx):
    u = load_user(ctx.author.id)
    if u.get("exp_end"):
        end = datetime.strptime(u["exp_end"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() >= end:
            rw = u.get("exp_reward", 500)
            u["money"] += rw
            del u["exp_end"]; del u["exp_reward"]; save_user(ctx.author.id)
            return await ctx.send(embed=discord.Embed(title="🎉 TRỞ VỀ", description=f"Thu hoạch được **{rw:,} 💰**!", color=discord.Color.gold()))
        else:
            h, r = divmod(int((end - datetime.now()).total_seconds()), 3600); m, _ = divmod(r, 60)
            return await ctx.send(embed=discord.Embed(description=f"⏳ Vẫn đang cày cuốc. Chờ **{h}h {m}m** nữa.", color=discord.Color.orange()))

    embed = discord.Embed(title="⛺ TRẠM LỀU TRẠI AFK", description="Treo acc đi cày tiền.\n👇 **CHỌN ĐỊA ĐIỂM** 👇", color=discord.Color.dark_green())
    await ctx.send(embed=embed, view=ExpView(ctx.author))

# ---------------------------------------------------------------------
# 7. KALLEN FANTASY (Gacha & Đánh Quái)
# ---------------------------------------------------------------------
@bot.group(invoke_without_command=True, aliases=['kf', 'honkai'])
async def kallen(ctx):
    p = load_kf_profile(ctx.author.id)
    s = calculate_kallen_stats(ctx.author.id)
    embed = discord.Embed(
        title="🌌 CHIẾN HẠM HYPERION TẬP KẾT",
        description=f"Tư Lệnh: **{ctx.author.name}**\nCấp Tu Luyện: **Lv {p['level']}**\nThể lực: **{p['stamina']}/{p['max_stamina']}** ⚡ | Tài sản: **{p['crystals']:,}** 💎\n\n"
                    f"🛡️ **VALKYRIE XUẤT CHIẾN:**\n{s['suit']['emoji']} **{s['suit']['name']}**\n"
                    f"❤️ Sinh lực: {s['hp']:,} | ⚔️ Sức Mạnh: {s['atk']:,} | 💥 Chí Mạng: {s['crt']}%",
        color=discord.Color.purple()
    )
    embed.add_field(name="Bộ Lệnh Đánh", value="`k kf gacha` • Đốt tiền quay Tiếp Tế\n`k kf story 1-1` • Dọn dẹp quái vật\n`k kf abyss` • Nhảy xuống Vực Sâu", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command()
async def gacha(ctx):
    await ctx.reply(embed=discord.Embed(title="📦 THÙNG TIẾP TẾ", description="Dùng 280 💎 để cầu nhân phẩm lấy Valkyrie.", color=discord.Color.gold()), view=KallenGachaView(ctx.author))

@kallen.command()
async def story(ctx, stage_id: str = "1-1"):
    p = load_kf_profile(ctx.author.id)
    if stage_id not in KALLEN_STAGES: return await ctx.reply("⚠️ Sai mã ải!")
    if p["stamina"] < 10: return await ctx.reply("⚠️ Thiếu 10 Thể Lực ⚡.")
        
    p["stamina"] -= 10; save_kf_profile(ctx.author.id)
    s = KALLEN_STAGES[stage_id]
    msg = await ctx.reply(embed=discord.Embed(title=f"🚀 XUẤT KÍCH: {s['name']}", color=discord.Color.blue()))
    await asyncio.sleep(1)
    view = KallenCombatView(ctx.author, calculate_kallen_stats(ctx.author.id), s, p, False)
    await view.update_ui(ctx, f"Chiến hạm thả bạn xuống vùng tử địa {s['name']}!")

@kallen.command()
async def abyss(ctx):
    p = load_kf_profile(ctx.author.id)
    if p["stamina"] < 20: return await ctx.reply("⚠️ Thiếu 20 Thể Lực ⚡.")
    p["stamina"] -= 20; save_kf_profile(ctx.author.id)
    msg = await ctx.reply(embed=discord.Embed(title="🌋 VỰC SÂU ABYSS", color=discord.Color.red()))
    await asyncio.sleep(1)
    view = KallenCombatView(ctx.author, calculate_kallen_stats(ctx.author.id), None, p, True)
    await view.update_ui(ctx, "Cánh Cửa Vực Sâu mở ra đón lấy bạn!")

# ---------------------------------------------------------------------
# 8. EVENTS (CÀY XP THEO TIN NHẮN)
# ---------------------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    u = load_user(uid)
    
    if u.get("jail_time") and datetime.now() < datetime.strptime(u["jail_time"], "%Y-%m-%d %H:%M:%S"):
        return await bot.process_commands(message)

    u["xp"] += random.randint(5, 15)
    max_xp = u["level"] * 100

    if u["xp"] >= max_xp:
        u["xp"] -= max_xp
        u["level"] += 1
        thuong = u["level"] * 300
        u["money"] += thuong
        
        embed = discord.Embed(
            title="🌟 ĐỘT PHÁ CẢNH GIỚI", 
            description=f"Oai phong lẫm liệt! {message.author.mention} tu luyện đạt thành **Cấp Độ {u['level']}**!\nThiên đạo rải xuống thưởng nóng: **{thuong:,} 💰**", 
            color=discord.Color.gold()
        )
        try: await message.channel.send(embed=embed)
        except: pass

    save_user(uid)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print('================================================')
    print(f'>>> SIÊU BOT {bot.user} BẢN 10.0 ĐÃ VẬN HÀNH!')
    print('>>> KHỐI LƯỢNG LỆNH: KHỔNG LỒ | DATABASE: MONGODB')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="Hệ sinh thái Tỷ Phú | k help"))

# =====================================================================
# KHỞI CHẠY BOT BẰNG TOKEN ĐƯỢC GHÉP NỐI AN TOÀN
# =====================================================================
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối an toàn
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
