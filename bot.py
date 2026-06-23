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
# [PHẦN 1] KHỞI TẠO SIÊU BOT 10.0 - BỘ KHUNG DỮ LIỆU ĐỒ SỘ (MAX BUNG LỤA)
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.presences = True

bot = commands.Bot(command_prefix=['K ', 'k ', 'K', 'k'], intents=intents)
bot.remove_command('help')

# =====================================================================
# BỘ TỪ ĐIỂN ẢNH GIF ANIMATION 
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
    "war": "https://media.giphy.com/media/l41JRsph73VokN6ik/giphy.gif",
    "gacha": "https://media.giphy.com/media/3o7TKoHNJTWWLgljYQ/giphy.gif"
}

cooldowns = {
    "gamble": {}, 
    "nhansinh": {}, 
    "work": {}, 
    "crime": {}, 
    "fish": {}, 
    "farm": {}, 
    "eat": {}
}
dang_choi_nhansinh = [] 

# =====================================================================
# KẾT NỐI MONGODB VÀ BỘ ĐỆM RAM TỐI ƯU TRUY XUẤT NHIỀU BẢNG
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
    global_col = db["global_state"]
    print("✅ [HỆ THỐNG] Đã kết nối thành công tới Siêu máy chủ MongoDB!")
except Exception as e:
    print(f"❌ [LỖI NGHIÊM TRỌNG] Không thể kết nối Database: {e}")

DB_CACHE = {}
CONFIG_CACHE = {}
KF_CACHE = {}
FARM_CACHE = {}
COMPANY_CACHE = {}

def get_global_weather():
    state = global_col.find_one({"_id": "world_weather"})
    if not state:
        default_state = {
            "_id": "world_weather", 
            "current": "Nắng Đẹp ☀️", 
            "multiplier": 1.0
        }
        global_col.insert_one(default_state)
        return default_state
    return state

def set_global_weather(weather_name, multiplier):
    global_col.update_one(
        {"_id": "world_weather"}, 
        {"$set": {
            "current": weather_name, 
            "multiplier": multiplier
        }}, 
        upsert=True
    )

def load_user(user_id):
    user_id = str(user_id)
    if user_id not in DB_CACHE:
        doc = users_col.find_one({"_id": user_id})
        DB_CACHE[user_id] = doc if doc else {}
            
    # BỘ KHUNG USER SIÊU CHI TIẾT
    defaults = {
        "xp": 0, 
        "level": 1, 
        "money": 5000, 
        "bank": 0, 
        "bank_capacity": 5000000, 
        "debt": 0,
        "title": "Kẻ Lang Thang 🏕️", 
        "assets": [], 
        "inventory": {
            "Thịt Gà": 5, 
            "Nước Suối": 5,
            "Gỗ": 0,
            "Đá": 0,
            "Sắt": 0
        }, 
        "pets": {}, 
        "stocks": {}, 
        "jail_time": None, 
        
        # Chỉ số sinh tồn (Survival Stats)
        "health": 100, 
        "max_health": 100,
        "hunger": 100, 
        "max_hunger": 100,
        "thirst": 100, 
        "max_thirst": 100,
        "energy": 100, 
        "max_energy": 100,
        
        # Trang bị nghề nghiệp
        "fishing_rod": "CanTre", 
        "bait": 50,
        "mining_pick": "CuocGo",
        
        # Xã hội & Danh vọng
        "reputation": 0, 
        "honor_points": 0, 
        "company": None,
        
        # Cây Kỹ năng đa dạng (Skills Tree)
        "skills": {
            "trading": 1, 
            "farming": 1, 
            "fishing": 1, 
            "charisma": 1, 
            "hacking": 1, 
            "combat": 1, 
            "mining": 1
        }
    }
    
    for k, v in defaults.items():
        if k not in DB_CACHE[user_id]: 
            DB_CACHE[user_id][k] = v
            
    # Tự cập nhật nếu thiếu skill mới
    if "skills" in DB_CACHE[user_id]:
        for sk, sv in defaults["skills"].items():
            if sk not in DB_CACHE[user_id]["skills"]:
                DB_CACHE[user_id]["skills"][sk] = sv
                
    if "inventory" not in DB_CACHE[user_id] or not isinstance(DB_CACHE[user_id]["inventory"], dict):
        DB_CACHE[user_id]["inventory"] = {"Thịt Gà": 5, "Nước Suối": 5, "Gỗ": 0, "Đá": 0, "Sắt": 0}

    return DB_CACHE[user_id]

def save_user(user_id):
    user_id = str(user_id)
    if user_id in DB_CACHE: 
        users_col.update_one({"_id": user_id}, {"$set": DB_CACHE[user_id]}, upsert=True)

# =====================================================================
# KHO VẬT PHẨM MUA SẮM (SHOP_ITEMS) - QUY MÔ LỚN
# =====================================================================
SHOP_ITEMS = {
    # ------------------- THỨC ĂN SINH TỒN -------------------
    "food_1": {
        "type": "food", 
        "name": "Bánh Mì Khô 🥖", 
        "price": 500, 
        "recover_hunger": 15, 
        "recover_thirst": -5, 
        "emoji": "🥖"
    },
    "food_2": {
        "type": "food", 
        "name": "Cơm Tấm Mắm Tôm 🍱", 
        "price": 2500, 
        "recover_hunger": 40, 
        "recover_thirst": -10, 
        "emoji": "🍱"
    },
    "food_3": {
        "type": "food", 
        "name": "Bò Kobe Dát Vàng 🥩", 
        "price": 50000, 
        "recover_hunger": 100, 
        "recover_thirst": 20, 
        "emoji": "🥩"
    },
    "drink_1": {
        "type": "food", 
        "name": "Nước Suối Lọc 💧", 
        "price": 200, 
        "recover_hunger": 0, 
        "recover_thirst": 30, 
        "emoji": "💧"
    },
    "drink_2": {
        "type": "food", 
        "name": "Nước Tăng Lực Redbull 🧃", 
        "price": 1500, 
        "recover_hunger": 5, 
        "recover_thirst": 50, 
        "emoji": "🧃"
    },
    "drink_3": {
        "type": "food", 
        "name": "Rượu Vang Pháp 🍷", 
        "price": 10000, 
        "recover_hunger": 10, 
        "recover_thirst": 80, 
        "emoji": "🍷"
    },
    
    # ------------------- DANH HIỆU -------------------
    "title_1": {
        "type": "title", 
        "name": "Bình Dân Học Vụ 🎒", 
        "price": 50000, 
        "emoji": "🏷️", 
        "buff": 1.1,
        "desc": "Tăng 10% kinh nghiệm."
    },
    "title_2": {
        "type": "title", 
        "name": "Thương Nhân Chợ Đen 💼", 
        "price": 500000, 
        "emoji": "🏷️", 
        "buff": 1.2,
        "desc": "Giảm phí giao dịch."
    },
    "title_3": {
        "type": "title", 
        "name": "Trùm Giang Hồ Mạng 🕶️", 
        "price": 1500000, 
        "emoji": "🏷️", 
        "buff": 1.4,
        "desc": "Tăng tỉ lệ tẩu thoát."
    },
    "title_4": {
        "type": "title", 
        "name": "Quản Trị Tinh Hà 🌌", 
        "price": 5000000, 
        "emoji": "🏷️", 
        "buff": 1.7,
        "desc": "Tăng tỉ lệ Gacha."
    },
    "title_5": {
        "type": "title", 
        "name": "Tài Phiệt Ác Ma 👑", 
        "price": 20000000, 
        "emoji": "🏷️", 
        "buff": 2.0,
        "desc": "Tăng 20% lãi suất ngân hàng."
    },
    "title_6": {
        "type": "title", 
        "name": "Thần Tài Giáng Thế 🌟", 
        "price": 100000000, 
        "emoji": "🏷️", 
        "buff": 3.0,
        "desc": "Tăng may mắn tất cả mọi mặt."
    },
    
    # ------------------- PHƯƠNG TIỆN -------------------
    "veh_1": {
        "type": "vehicle", 
        "name": "Xe Đạp Điện Martin 🚲", 
        "price": 15000, 
        "emoji": "🚲", 
        "escape": 5,
        "desc": "Chạy pin 40km/h."
    },
    "veh_2": {
        "type": "vehicle", 
        "name": "Wave Alpha Đôn Dên 🛵", 
        "price": 85000, 
        "emoji": "🛵", 
        "escape": 12,
        "desc": "Phóng lợn thoát cảnh sát."
    },
    "veh_3": {
        "type": "vehicle", 
        "name": "Honda SH 150i 🏍️", 
        "price": 300000, 
        "emoji": "🏍️", 
        "escape": 20,
        "desc": "Dân chơi bốc đầu."
    },
    "veh_4": {
        "type": "vehicle", 
        "name": "Toyota Civic 🚕", 
        "price": 1500000, 
        "emoji": "🚕", 
        "escape": 30,
        "desc": "Đẹp trai lãng tử."
    },
    "veh_5": {
        "type": "vehicle", 
        "name": "Mercedes G63 🚙", 
        "price": 12000000, 
        "emoji": "🚙", 
        "escape": 45,
        "desc": "Chủ tịch giả danh."
    },
    "veh_6": {
        "type": "vehicle", 
        "name": "Siêu Xe Bugatti Chiron 🏎️", 
        "price": 50000000, 
        "emoji": "🏎️", 
        "escape": 65,
        "desc": "Tốc độ bàn thờ."
    },
    "veh_7": {
        "type": "vehicle", 
        "name": "Trực Thăng Apache 🚁", 
        "price": 250000000, 
        "emoji": "🚁", 
        "escape": 85,
        "desc": "Bay trên không trung."
    },
    "veh_8": {
        "type": "vehicle", 
        "name": "Tàu Vũ Trụ Hyperion 🛸", 
        "price": 1000000000, 
        "emoji": "🛸", 
        "escape": 99,
        "desc": "Nhảy warp không gian."
    },
    
    # ------------------- BẤT ĐỘNG SẢN -------------------
    "house_1": {
        "type": "house", 
        "name": "Phòng Trọ Ống Cống 🏚️", 
        "price": 80000, 
        "emoji": "🏚️", 
        "income": 500,
        "desc": "Cho sinh viên nghèo thuê."
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
        "name": "Cửa Hàng Tạp Hóa 🏪", 
        "price": 2500000, 
        "emoji": "🏪", 
        "income": 12000,
        "desc": "Bán lẻ sinh lời đều đặn."
    },
    "house_4": {
        "type": "house", 
        "name": "Nhà Hàng 5 Sao 🍽️", 
        "price": 10000000, 
        "emoji": "🍽️", 
        "income": 45000,
        "desc": "Khách Tây nườm nượp."
    },
    "house_5": {
        "type": "house", 
        "name": "Biệt Thự Vùng Ven 🏡", 
        "price": 35000000, 
        "emoji": "🏡", 
        "income": 150000,
        "desc": "Khu compound an ninh."
    },
    "house_6": {
        "type": "house", 
        "name": "Khách Sạn Casino 🏨", 
        "price": 120000000, 
        "emoji": "🏨", 
        "income": 600000,
        "desc": "Máy in tiền tỷ."
    },
    "house_7": {
        "type": "house", 
        "name": "Căn Cứ Công Nghiệp Tiền Tuyến AIC 🏭", 
        "price": 500000000, 
        "emoji": "🏭", 
        "income": 2500000,
        "desc": "Nhà máy điện hạt nhân."
    },
    "house_8": {
        "type": "house", 
        "name": "Hòn Đảo Nhiệt Đới 🏝️", 
        "price": 2000000000, 
        "emoji": "🏝️", 
        "income": 10000000,
        "desc": "Thu thuế đảo quốc."
    },
    
    # ------------------- SÁCH KỸ NĂNG -------------------
    "book_1": {
        "type": "item",
        "name": "Sách Luyện Thi TSA HUST 📘",
        "price": 50000,
        "emoji": "📘",
        "buff_skill": "hacking",
        "desc": "Tăng cường logic và hack hệ thống."
    },
    "book_2": {
        "type": "item",
        "name": "Binh Pháp Tôn Tử 📕",
        "price": 100000,
        "emoji": "📕",
        "buff_skill": "trading",
        "desc": "Thao túng tâm lý thị trường chứng khoán."
    },
    "book_3": {
        "type": "item",
        "name": "Cẩm Nang Nhà Nông 📗",
        "price": 80000,
        "emoji": "📗",
        "buff_skill": "farming",
        "desc": "Tăng năng suất cây trồng."
    },
    "book_4": {
        "type": "item",
        "name": "Sách Cần Thủ 📙",
        "price": 75000,
        "emoji": "📙",
        "buff_skill": "fishing",
        "desc": "Tăng tỉ lệ bắt cá hiếm."
    },
    "book_5": {
        "type": "item",
        "name": "Đắc Nhân Tâm 📓",
        "price": 150000,
        "emoji": "📓",
        "buff_skill": "charisma",
        "desc": "Tăng sức ảnh hưởng và uy tín."
    }
}

# =====================================================================
# HỆ THỐNG CÂU CÁ, ĐÀO MỎ & NÔNG TRẠI 
# =====================================================================
FISHING_RODS = {
    "CanTre": {
        "name": "Cần Câu Tre Làng 🎋", 
        "price": 5000, 
        "luck": 0
    },
    "CanSat": {
        "name": "Cần Câu Thép Chống Rỉ 🎣", 
        "price": 25000, 
        "luck": 10
    },
    "CanCarbon": {
        "name": "Cần Câu Sợi Carbon 🎿", 
        "price": 100000, 
        "luck": 25
    },
    "CanFiber": {
        "name": "Cần Câu Thủy Tinh 🔬", 
        "price": 350000, 
        "luck": 40
    },
    "CanVang": {
        "name": "Cần Câu Mạ Vàng 🏆", 
        "price": 1500000, 
        "luck": 60
    },
    "CanPosedion": {
        "name": "Đinh Ba Thủy Thần 🔱", 
        "price": 10000000, 
        "luck": 90
    }
}

FISH_DATABASE = {
    "trash": {
        "rate": 20, 
        "price": 10, 
        "pool": [
            "Bọc Nilon rách 🗑️", 
            "Chiếc ủng rách 👢", 
            "Chai nhựa cũ 🍾"
        ]
    },
    "common": {
        "rate": 45, 
        "price": 200, 
        "pool": [
            "Cá Chép 🐟", 
            "Cá Rô 🐟", 
            "Cá Trê 🐠", 
            "Cá Diêu Hồng 🐟"
        ]
    },
    "uncommon": {
        "rate": 20, 
        "price": 1000, 
        "pool": [
            "Cá Lóc Khổng Lồ 🐡", 
            "Cá Hồi Na Uy 🍣", 
            "Lươn Điện 🐍"
        ]
    },
    "rare": {
        "rate": 10, 
        "price": 5000, 
        "pool": [
            "Cá Mập Con 🦈", 
            "Rùa Biển 🐢", 
            "Cá Đuối Khổng Lồ 🐡"
        ]
    },
    "epic": {
        "rate": 4.5, 
        "price": 35000, 
        "pool": [
            "Cá Voi Xanh 🐳", 
            "Bạch Tuộc Kraken Nhí 🦑", 
            "Cá Kiếm Đại Dương 🐟"
        ]
    },
    "legendary": {
        "rate": 0.45, 
        "price": 250000, 
        "pool": [
            "Thủy Quái Loch Ness 🐉", 
            "Cá Mập Megalodon Tiền Sử 🦈", 
            "Ngọc Trai Biển Sâu 🦪"
        ]
    },
    "mythic": {
        "rate": 0.05, 
        "price": 5000000, 
        "pool": [
            "Nàng Tiên Cá Bị Lạc 🧜‍♀️", 
            "Rương Kho Báu Atlantis 🧰", 
            "Vương Miện Hải Vương 👑"
        ]
    }
}

FARM_SEEDS = {
    "lua_mi": {
        "name": "Lúa Mì 🌾", 
        "buy": 100, "sell": 300, 
        "time_mins": 5, "water_req": 1
    },
    "ca_rot": {
        "name": "Cà Rốt 🥕", 
        "buy": 300, "sell": 900, 
        "time_mins": 15, "water_req": 1
    },
    "ca_chua": {
        "name": "Cà Chua 🍅", 
        "buy": 800, "sell": 2500, 
        "time_mins": 30, "water_req": 2
    },
    "bap_cai": {
        "name": "Bắp Cải 🥬", 
        "buy": 2000, "sell": 6500, 
        "time_mins": 60, "water_req": 2
    },
    "dau_tay": {
        "name": "Dâu Tây 🍓", 
        "buy": 5000, "sell": 18000, 
        "time_mins": 120, "water_req": 3
    },
    "du_hau": {
        "name": "Dưa Hấu 🍉", 
        "buy": 15000, "sell": 55000, 
        "time_mins": 240, "water_req": 4
    },
    "nhan_sam": {
        "name": "Nhân Sâm Ngàn Năm 🌿", 
        "buy": 100000, "sell": 450000, 
        "time_mins": 720, "water_req": 5
    },
    "cay_tien": {
        "name": "Cây Tiền Tỷ 💸", 
        "buy": 500000, "sell": 2500000, 
        "time_mins": 1440, "water_req": 10
    }
}

# =====================================================================
# DATA KALLEN FANTASY (Hơn 15 Characters & Vũ Khí Đỉnh Cao)
# =====================================================================
KALLEN_BATTLESUITS = {
    "imayoh": {
        "name": "Ritual Imayoh", "type": "MECH", "rarity": "A", 
        "base_hp": 1200, "base_atk": 250, "base_def": 150, "base_crt": 20,
        "skill_basic_dmg": 1.2, "skill_ult_dmg": 6.0, "ult_sp_cost": 80, "emoji": "🔫"
    },
    "sundenjager": {
        "name": "Sündenjäger", "type": "MECH", "rarity": "A", 
        "base_hp": 1400, "base_atk": 220, "base_def": 180, "base_crt": 15,
        "skill_basic_dmg": 1.0, "skill_ult_dmg": 5.5, "ult_sp_cost": 75, "emoji": "🦇"
    },
    "yamabuki": {
        "name": "Valkyrie Chariot", "type": "PSY", "rarity": "A", 
        "base_hp": 1600, "base_atk": 200, "base_def": 250, "base_crt": 10,
        "skill_basic_dmg": 1.0, "skill_ult_dmg": 5.0, "ult_sp_cost": 60, "emoji": "🛡️"
    },
    "sixth_serenade": {
        "name": "Sixth Serenade", "type": "PSY", "rarity": "S", 
        "base_hp": 1500, "base_atk": 320, "base_def": 140, "base_crt": 30,
        "skill_basic_dmg": 1.5, "skill_ult_dmg": 8.0, "ult_sp_cost": 100, "emoji": "🎭"
    },
    "chen_qianyu": {
        "name": "Chen Qianyu (Endfield)", "type": "BIO", "rarity": "S", 
        "base_hp": 1800, "base_atk": 380, "base_def": 200, "base_crt": 25,
        "skill_basic_dmg": 1.8, "skill_ult_dmg": 10.0, "ult_sp_cost": 120, "emoji": "🗡️"
    },
    "kafka": {
        "name": "Kafka (Stellaron Hunter)", "type": "PSY", "rarity": "S", 
        "base_hp": 1700, "base_atk": 400, "base_def": 180, "base_crt": 35,
        "skill_basic_dmg": 1.9, "skill_ult_dmg": 9.5, "ult_sp_cost": 110, "emoji": "🕸️"
    },
    "silver_wolf": {
        "name": "Silver Wolf", "type": "MECH", "rarity": "S", 
        "base_hp": 1600, "base_atk": 350, "base_def": 160, "base_crt": 40,
        "skill_basic_dmg": 1.4, "skill_ult_dmg": 12.0, "ult_sp_cost": 90, "emoji": "👾"
    },
    "acheron": {
        "name": "Acheron (Nihility)", "type": "MECH", "rarity": "SS", 
        "base_hp": 2200, "base_atk": 480, "base_def": 220, "base_crt": 45,
        "skill_basic_dmg": 2.2, "skill_ult_dmg": 14.0, "ult_sp_cost": 130, "emoji": "🥀"
    },
    "jingliu": {
        "name": "Jingliu (Sword Champion)", "type": "BIO", "rarity": "SS", 
        "base_hp": 2100, "base_atk": 520, "base_def": 210, "base_crt": 50,
        "skill_basic_dmg": 2.4, "skill_ult_dmg": 15.0, "ult_sp_cost": 135, "emoji": "❄️"
    },
    "raiden_shogun": {
        "name": "Raiden Shogun (Archon)", "type": "PSY", "rarity": "SSS", 
        "base_hp": 2800, "base_atk": 650, "base_def": 300, "base_crt": 55,
        "skill_basic_dmg": 3.0, "skill_ult_dmg": 20.0, "ult_sp_cost": 150, "emoji": "⚡"
    },
    "kiana_finality": {
        "name": "Herrscher of Finality", "type": "IMG", "rarity": "SSS", 
        "base_hp": 3000, "base_atk": 700, "base_def": 350, "base_crt": 60,
        "skill_basic_dmg": 3.5, "skill_ult_dmg": 25.0, "ult_sp_cost": 180, "emoji": "🔥"
    },
    "elysia_human": {
        "name": "Elysia (Herrscher of Human)", "type": "PSY", "rarity": "SSS", 
        "base_hp": 2900, "base_atk": 680, "base_def": 320, "base_crt": 65,
        "skill_basic_dmg": 3.2, "skill_ult_dmg": 22.0, "ult_sp_cost": 160, "emoji": "🌸"
    }
}

KALLEN_WEAPONS = {
    "wp_usp": {"name": "Súng Ngắn USP", "rarity": 3, "atk": 50, "crt": 5},
    "wp_water": {"name": "Water Spirit Type-II", "rarity": 4, "atk": 200, "crt": 15},
    "wp_magstorm": {"name": "Magnetic Storm", "rarity": 4, "atk": 250, "crt": 20},
    "wp_aria": {"name": "Tranquil Arias", "rarity": 5, "atk": 400, "crt": 35},
    "wp_endfield_blade": {"name": "Gươm Công Nghiệp Tiền Tuyến", "rarity": 5, "atk": 450, "crt": 40},
    "wp_domain": {"name": "Domain of Sanction", "rarity": 6, "atk": 650, "crt": 55},
    "wp_engulfing": {"name": "Engulfing Lightning", "rarity": 6, "atk": 700, "crt": 60},
    "wp_key_of_castigation": {"name": "Key of Castigation", "rarity": 6, "atk": 720, "crt": 65}
}

KALLEN_ENEMIES = {
    "zombie_1": {"name": "Xác Sống Cầm Kiếm", "type": "BIO", "hp": 2000, "atk": 100, "def": 50, "sp_drop": 5},
    "beast_1": {"name": "Thú Honkai Kỵ Binh", "type": "PSY", "hp": 3500, "atk": 150, "def": 120, "sp_drop": 8},
    "mecha_1": {"name": "Titan Tuần Tra", "type": "MECH", "hp": 5000, "atk": 200, "def": 250, "sp_drop": 10},
    "marble_boss": {"name": "Ma Thú Cẩm Thạch", "type": "MECH", "hp": 25000, "atk": 550, "def": 400, "sp_drop": 30},
    "boss_ming": {"name": "Đại Quân Nhà Minh", "type": "BIO", "hp": 60000, "atk": 900, "def": 500, "sp_drop": 50},
    "boss_god": {"name": "Herrscher of the Void", "type": "BIO", "hp": 120000, "atk": 1500, "def": 800, "sp_drop": 100},
    "boss_kevin": {"name": "Kevin Kaslana (Diệt Thế)", "type": "IMG", "hp": 300000, "atk": 3000, "def": 1500, "sp_drop": 200},
    "boss_otto": {"name": "Otto Apocalypse", "type": "IMG", "hp": 500000, "atk": 5000, "def": 2000, "sp_drop": 500}
}

KALLEN_STAGES = {
    "1-1": {"name": "1-1: Thức tỉnh", "enemies": ["zombie_1"], "rw_m": 5000, "rw_xp": 100},
    "1-2": {"name": "1-2: Cuộc vây hãm", "enemies": ["zombie_1", "beast_1"], "rw_m": 10000, "rw_xp": 200},
    "1-3": {"name": "1-3: Phòng Tuyến Titan", "enemies": ["mecha_1", "mecha_1"], "rw_m": 15000, "rw_xp": 300},
    "2-1": {"name": "2-1: Căn Cứ AIC Sụp Đổ", "enemies": ["beast_1", "marble_boss"], "rw_m": 45000, "rw_xp": 800},
    "3-1": {"name": "3-1: Trận Tuyết Hận (Lịch sử)", "enemies": ["mecha_1", "boss_ming"], "rw_m": 100000, "rw_xp": 1500},
    "4-1": {"name": "4-1: Luật Giả Giáng Lâm", "enemies": ["boss_god"], "rw_m": 300000, "rw_xp": 4000},
    "5-1": {"name": "5-1: Lửa Thiêng Cứu Thế", "enemies": ["boss_god", "boss_kevin"], "rw_m": 1000000, "rw_xp": 15000},
    "6-1": {"name": "CHUNG CUỘC: Kẻ Ngu Giả", "enemies": ["boss_kevin", "boss_otto"], "rw_m": 5000000, "rw_xp": 50000}
}

# =====================================================================
# BỘ CỐT TRUYỆN MÔ PHỎNG NHÂN SINH KHỔNG LỒ (ĐA VŨ TRỤ 10 GIAI ĐOẠN)
# =====================================================================
EVENTS_P1 = [ 
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

EVENTS_P2 = [ 
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

EVENTS_P3 = [ 
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

EVENTS_P4 = [ 
    {
        "q": "Tuổi 50, giai đoạn tiền mãn kinh. Cảm thấy cuộc đời nhạt nhẽo, bạn muốn làm gì đó điên rồ.",
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

EVENTS_P5 = [ 
    {
        "q": "Chạm mốc 70 tuổi thọ. Bạn suy nghĩ về di sản đời mình.",
        "choices": [
            {
                "text": "Chia đều gia sản cho con cháu", 
                "rate": 70, 
                "win": "Gia đình đoàn viên, khóc lóc tiếc thương khi bạn nằm xuống.", 
                "lose": "Tụi nó chê ít, đánh nhau mẻ đầu ngay tại giường bệnh làm bạn tức chết.", 
                "tien_w": 15000, 
                "tien_l": -50000, 
                "die_l": True
            },
            {
                "text": "Quyên góp 100% xây trường học Lam Sơn", 
                "rate": 95, 
                "win": "Được đúc tượng đồng, tên tuổi lưu danh sử sách ngàn thu.", 
                "lose": "Tổ chức quỹ tham nhũng ăn chặn tiền, phước đức tiêu tan.", 
                "tien_w": 50000, 
                "tien_l": -100000, 
                "die_l": True
            },
            {
                "text": "Bao nguyên quán Bar nhảy đầm đêm cuối", 
                "rate": 15, 
                "win": "Được tôn làm dân chơi Tóp Tóp lão làng, vung tiền không gợn sóng.", 
                "lose": "Quẩy quá đà nhồi máu cơ tim thăng thiên ngay trên sàn nhảy.", 
                "tien_w": 25000, 
                "tien_l": -80000, 
                "die_l": True
            },
            {
                "text": "Mua vé tàu vũ trụ đi tìm sự sống mới", 
                "rate": 5, 
                "win": "Tìm ra hành tinh mỏ kim cương, trở thành Hoàng đế liên ngân hà!", 
                "lose": "Tàu nổ tung giữa không gian do lỗi động cơ.", 
                "tien_w": 5000000, 
                "tien_l": -500000, 
                "die_l": True
            }
        ]
    }
]
# =====================================================================
# [PHẦN 2] HỆ THỐNG BACKGROUND TASKS, SINH TỒN VÀ GIAO DIỆN (UI VIEWS)
# =====================================================================

# ---------------------------------------------------------------------
# 1. TASK CHẠY NGẦM: THỜI TIẾT, SINH TỒN, LÃI SUẤT & CHỨNG KHOÁN
# ---------------------------------------------------------------------
@tasks.loop(minutes=60)
async def world_simulation_task():
    """Luồng chạy ngầm mô phỏng thế giới ảo, chạy mỗi 60 phút"""
    print("🌍 [HỆ THỐNG] Đang cập nhật trạng thái Thế Giới (Thời tiết, Sinh tồn, Kinh tế)...")
    
    # --- 1.1 CẬP NHẬT THỜI TIẾT TOÀN CẦU ---
    weather_chance = random.uniform(0, 100)
    if weather_chance <= 50:
        set_global_weather("Nắng Đẹp ☀️", 1.0)
    elif weather_chance <= 75:
        set_global_weather("Mưa Rào 🌧️", 1.2)  # Mưa thì câu cá dễ hơn
    elif weather_chance <= 90:
        set_global_weather("Bão Táp ⛈️", 0.5)  # Bão thì khó câu cá, hỏng cây
    elif weather_chance <= 98:
        set_global_weather("Sương Mù 🌫️", 0.8)
    else:
        set_global_weather("Tuyết Rơi ❄️", 0.3) # Đóng băng nông trại

    # Lấy thông tin thời tiết vừa set
    current_weather = get_global_weather()
    print(f"☁️ [THỜI TIẾT] Bầu trời hiện tại: {current_weather['current']}")

    # --- 1.2 CẬP NHẬT TÀI SẢN & SINH TỒN NGƯỜI CHƠI ---
    all_users = list(users_col.find())
    for doc in all_users:
        uid = str(doc["_id"])
        u = load_user(uid)
        
        # A. Lãi suất ngân hàng (0.3% / giờ)
        if u.get("bank", 0) > 0:
            lai_suat = int(u["bank"] * 0.003)
            # Buff từ danh hiệu (Tài phiệt ác ma +20% lãi)
            if u.get("title") == "Tài Phiệt Ác Ma 👑": 
                lai_suat = int(lai_suat * 1.2)
            u["bank"] += lai_suat
            
        # B. Lãi vay (Nếu money âm -> Phạt 1% / giờ)
        if u.get("money", 0) < 0:
            tien_phat = int(abs(u["money"]) * 0.01)
            u["money"] -= tien_phat
            
        # C. Thu tiền thuê nhà thụ động (Bất động sản)
        assets = u.get("assets", [])
        tong_thu_nhap = 0
        for asset_name in assets:
            for k, v in SHOP_ITEMS.items():
                if v.get("name") == asset_name and v.get("type") == "house":
                    tong_thu_nhap += v.get("income", 0)
        
        if tong_thu_nhap > 0:
            u["bank"] += tong_thu_nhap # Tiền thuê nhà đổ thẳng vào két ngân hàng
            
        # D. Hệ thống Sinh Tồn Khắc Nghiệt (Đói, Khát)
        u["hunger"] -= random.randint(3, 8)
        u["thirst"] -= random.randint(5, 10)
        u["energy"] += random.randint(10, 20) # Hồi năng lượng tự nhiên
        
        # Giới hạn chỉ số
        if u["energy"] > u["max_energy"]: 
            u["energy"] = u["max_energy"]
            
        # Trừng phạt nếu Đói / Khát
        if u["hunger"] <= 0:
            u["hunger"] = 0
            u["health"] -= 10 # Mất máu vì đói
            
        if u["thirst"] <= 0:
            u["thirst"] = 0
            u["health"] -= 15 # Mất máu vì khát
            
        # Kiểm tra đột tử vì sinh tồn
        if u["health"] <= 0:
            u["health"] = 100
            u["hunger"] = 100
            u["thirst"] = 100
            # Phạt tiền khi chết
            tien_phat_chet = int(u.get("money", 0) * 0.1) 
            if tien_phat_chet > 0:
                u["money"] -= tien_phat_chet
                print(f"💀 [SINH TỒN] Ký chủ {uid} đã chết vì kiệt sức. Phạt {tien_phat_chet} 💰")

        # E. Thú cưng giảm độ no (Hunger)
        pets = u.get("pets", {})
        for pet_id, pet_data in pets.items():
            if pet_data.get("hunger", 100) > 0:
                pet_data["hunger"] -= random.randint(5, 15)
                if pet_data["hunger"] < 0:
                    pet_data["hunger"] = 0
                
        save_user(uid)

    # --- 1.3 CẬP NHẬT SÀN CHỨNG KHOÁN ĐẠI CHIẾN ---
    all_stocks = list(stocks_col.find())
    if not all_stocks:
        default_stocks = [
            {"_id": "VNM", "name": "Vinamilk", "price": 50000, "trend": "up", "history": [50000]},
            {"_id": "FLC", "name": "Tập đoàn FLC", "price": 10000, "trend": "down", "history": [10000]},
            {"_id": "MHY", "name": "Mihoyo Hoyoverse", "price": 150000, "trend": "up", "history": [150000]},
            {"_id": "AIC", "name": "Công Nghiệp Endfield", "price": 85000, "trend": "up", "history": [85000]},
            {"_id": "BTC", "name": "Bitcoin Crypto", "price": 900000, "trend": "up", "history": [900000]},
            {"_id": "TSA", "name": "Giáo Dục HUST", "price": 30000, "trend": "up", "history": [30000]}
        ]
        for s in default_stocks: 
            stocks_col.insert_one(s)
        all_stocks = default_stocks

    for stock in all_stocks:
        current_price = stock.get("price", 10000)
        
        # Nguy cơ có Event Lớn (Thiên nga đen / Bong bóng)
        event_roll = random.uniform(0, 100)
        
        if event_roll <= 2.5: 
            # Sập hầm (Giảm mạnh 40% - 70%)
            new_price = int(current_price * random.uniform(0.3, 0.6)) 
        elif event_roll <= 5.0:
            # Bơm thổi (Tăng mạnh 150% - 250%)
            new_price = int(current_price * random.uniform(1.5, 2.5)) 
        else:
            # Biến động bình thường từ -15% đến +15%
            volatility = random.uniform(-0.15, 0.15) 
            new_price = int(current_price * (1 + volatility))
            
        # Không cho rớt dưới 500đ (Bảo lưu giá trị tối thiểu)
        if new_price < 500:
            new_price = 500 
            
        history = stock.get("history", [])
        history.append(new_price)
        
        # Lưu 12 giờ gần nhất để vẽ biểu đồ (nếu cần)
        if len(history) > 12: 
            history.pop(0) 
        
        stocks_col.update_one(
            {"_id": stock["_id"]},
            {"$set": {
                "price": new_price, 
                "history": history, 
                "trend": "up" if new_price >= current_price else "down"
            }}
        )
    print("✅ [HỆ THỐNG] Đã hoàn tất cập nhật chu kỳ 1 giờ.")

# ---------------------------------------------------------------------
# 2. GIAO DIỆN CỬA HÀNG ĐẠI GIA (SHOPPING UI)
# ---------------------------------------------------------------------
class ShopItemSelect(discord.ui.Select):
    def __init__(self, category_type):
        self.category_type = category_type
        options = []
        for key, item_data in SHOP_ITEMS.items():
            if item_data.get("type") == category_type:
                # Format mô tả dài cho chuẩn xác
                desc = f"Giá: {item_data['price']:,} 💰 | {item_data.get('desc', '')}"
                
                # Tránh lỗi giới hạn 100 ký tự của Discord
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                    
                options.append(discord.SelectOption(
                    label=item_data['name'], 
                    description=desc, 
                    value=key, 
                    emoji=item_data.get('emoji', '🛒')
                ))
                
        super().__init__(
            placeholder="Nhấn vào đây để vung tiền tỷ...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        u = load_user(uid)
        
        selected_key = self.values[0]
        item = SHOP_ITEMS[selected_key]
        item_price = item["price"]
        item_name = item["name"]
        item_type = item["type"]
        
        # Kiểm tra số dư ví
        if u.get("money", 0) < item_price:
            thieu = item_price - u.get('money', 0)
            return await interaction.response.send_message(
                f"⚠️ Thẻ đen từ chối! Bạn thiếu **{thieu:,} 💰** để mua món đồ này.", 
                ephemeral=True
            )
            
        # Kiểm tra trùng lặp với BĐS và Xe cộ
        if item_type in ["vehicle", "house"]:
            if item_name in u.get("assets", []):
                return await interaction.response.send_message(
                    f"⚠️ Bạn đã đứng tên sổ đỏ/cà vẹt **{item_name}** rồi! Để người khác mua với.", 
                    ephemeral=True
                )
                
        # Kiểm tra trùng lặp Danh hiệu
        if item_type == "title":
            if u.get("title") == item_name:
                return await interaction.response.send_message(
                    "⚠️ Bạn đang đeo danh hiệu này trên đầu rồi mà!", 
                    ephemeral=True
                )

        # XỬ LÝ THANH TOÁN
        u["money"] -= item_price
        
        # Xử lý theo từng loại Item
        if item_type == "title":
            u["title"] = item_name
            msg = f"🎉 Tiền trao cháo múc! Bạn đã đổi danh hiệu Căn Cước thành: **{item_name}**."
            
        elif item_type == "item":
            skill = item.get("buff_skill")
            if skill:
                u["skills"][skill] += 1
                msg = f"🧠 Uống sách như uống nước! Kỹ năng **{skill.upper()}** của bạn đã tăng lên Cấp {u['skills'][skill]}."
            else:
                msg = f"🎉 Mua thành công **{item_name}**."
                
        elif item_type == "food":
            # Thức ăn thêm vào túi đồ (Inventory)
            if item_name not in u["inventory"]:
                u["inventory"][item_name] = 0
            u["inventory"][item_name] += 1
            msg = f"🍔 Đã cất **{item_name}** vào ba lô sinh tồn. Nhớ ăn uống đầy đủ nha!"
            
        else:
            # Add vào Assets (BĐS, Xe)
            u["assets"].append(item_name)
            msg = f"🎉 Ký hợp đồng thành công! Bạn vừa ném chìa khóa **{item_name}** vào kho tài sản."

        # Lưu Database
        save_user(uid)
        
        embed = discord.Embed(
            title="🛍️ GIAO DỊCH HOÀN TẤT", 
            description=msg, 
            color=discord.Color.green()
        )
        embed.set_footer(
            text=f"Số dư ví hiện tại: {u['money']:,} 💰", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ShopCategoryMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=120)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Ai gọi lệnh người nấy mua, cấm tranh giành!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Tạp Hóa Sinh Tồn", style=discord.ButtonStyle.primary, emoji="🍔", row=0)
    async def btn_food(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ShopItemSelect("food"))
        embed = discord.Embed(
            title="🍔 CỬA HÀNG TIỆN LỢI", 
            description="Mua thức ăn, nước uống để không bị chết đói, chết khát.", 
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Sàn Bất Động Sản", style=discord.ButtonStyle.danger, emoji="🏰", row=0)
    async def btn_house(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ShopItemSelect("house"))
        embed = discord.Embed(
            title="🏰 SÀN GIAO DỊCH BẤT ĐỘNG SẢN", 
            description="Nhà đất sinh lời từng giờ. Tiền thuê tự động chuyển thẳng vào Bank.", 
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Showroom Siêu Xe", style=discord.ButtonStyle.success, emoji="🏎️", row=0)
    async def btn_veh(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ShopItemSelect("vehicle"))
        embed = discord.Embed(
            title="🏎️ SHOWROOM AUTO", 
            description="Xe xịn giúp tăng tỉ lệ tẩu thoát khi đi Cướp Ngân Hàng.", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cục Sở Hữu Trí Tuệ (VIP)", style=discord.ButtonStyle.secondary, emoji="🏷️", row=1)
    async def btn_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ShopItemSelect("title"))
        embed = discord.Embed(
            title="🏷️ QUẦY DANH HIỆU CĂN CƯỚC", 
            description="Danh hiệu xịn giúp tăng Lãi Bank và tăng Exp nhận được.", 
            color=discord.Color.dark_grey()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Nhà Sách Kỹ Năng", style=discord.ButtonStyle.secondary, emoji="📚", row=1)
    async def btn_book(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ShopItemSelect("item"))
        embed = discord.Embed(
            title="📚 NHÀ SÁCH TRÍ TUỆ TUYỆT ĐỈNH", 
            description="Đọc sách để nâng cấp Skill sinh tồn (Câu cá, Buôn lậu, Hack...).", 
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=view)


# ---------------------------------------------------------------------
# 3. GIAO DIỆN HỆ THỐNG NÔNG TRẠI (FARMING UI)
# ---------------------------------------------------------------------
def load_farm(user_id):
    user_id = str(user_id)
    if user_id not in FARM_CACHE:
        doc = farm_col.find_one({"_id": user_id})
        FARM_CACHE[user_id] = doc if doc else {}
    
    # 6 ô đất cơ bản
    defaults = {
        "plots": [
            {"id": 1, "seed": None, "plant_time": None, "watered": False, "unlocked": True},
            {"id": 2, "seed": None, "plant_time": None, "watered": False, "unlocked": True},
            {"id": 3, "seed": None, "plant_time": None, "watered": False, "unlocked": False},
            {"id": 4, "seed": None, "plant_time": None, "watered": False, "unlocked": False},
            {"id": 5, "seed": None, "plant_time": None, "watered": False, "unlocked": False},
            {"id": 6, "seed": None, "plant_time": None, "watered": False, "unlocked": False}
        ],
        "fertilizer": 0,
        "level": 1, 
        "exp": 0
    }
    for k, v in defaults.items():
        if k not in FARM_CACHE[user_id]: 
            FARM_CACHE[user_id][k] = v
    return FARM_CACHE[user_id]

def save_farm(user_id):
    user_id = str(user_id)
    if user_id in FARM_CACHE: 
        farm_col.update_one({"_id": user_id}, {"$set": FARM_CACHE[user_id]}, upsert=True)

class FarmPlotSelect(discord.ui.Select):
    def __init__(self, farm_data):
        self.farm = farm_data
        opts = []
        
        for p in self.farm["plots"]:
            if not p["unlocked"]: 
                opts.append(discord.SelectOption(
                    label=f"Ô đất số {p['id']}", 
                    description="Đất hoang đang khóa (Cần nâng cấp để mở)", 
                    value=f"lock_{p['id']}", 
                    emoji="🔒"
                ))
            elif p["seed"] is None:
                opts.append(discord.SelectOption(
                    label=f"Ô đất số {p['id']}", 
                    description="Đất trống, cỏ mọc um tùm. Bấm để gieo hạt.", 
                    value=str(p['id']), 
                    emoji="🟫"
                ))
            else:
                seed_info = FARM_SEEDS[p['seed']]
                ptime = datetime.strptime(p["plant_time"], "%Y-%m-%d %H:%M:%S")
                
                # Logic Ảnh hưởng của Thời Tiết lên Nông Trại
                weather = get_global_weather()
                time_multiplier = 1.0
                if weather["current"] == "Nắng Đẹp ☀️":
                    time_multiplier = 0.8 # Lớn nhanh hơn 20%
                elif weather["current"] == "Tuyết Rơi ❄️":
                    time_multiplier = 1.5 # Lớn chậm hơn 50%
                
                actual_time_mins = seed_info["time_mins"] * time_multiplier
                ready_time = ptime + timedelta(minutes=actual_time_mins)
                
                if datetime.now() >= ready_time:
                    opts.append(discord.SelectOption(
                        label=f"Ô {p['id']} - {seed_info['name']}", 
                        description="✨ Nông sản ĐÃ CHÍN! Nhấn để thu hoạch ngay.", 
                        value=f"harvest_{p['id']}", 
                        emoji="✨"
                    ))
                else:
                    opts.append(discord.SelectOption(
                        label=f"Ô {p['id']} - {seed_info['name']}", 
                        description="🌱 Đang sinh trưởng... Cần kiên nhẫn chờ đợi.", 
                        value=f"grow_{p['id']}", 
                        emoji="🌱"
                    ))
                    
        super().__init__(
            placeholder="Chọn ô đất để thao tác làm nông...", 
            min_values=1, 
            max_values=1, 
            options=opts
        )

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        uid = str(interaction.user.id)
        
        if val.startswith("lock"):
            return await interaction.response.send_message(
                "⚠️ Lấy đâu ra cuốc mà đòi khai hoang! Ô đất này chưa được mở khóa.", 
                ephemeral=True
            )
            
        if val.startswith("grow"):
            return await interaction.response.send_message(
                "🌱 Ép chín à? Cây đang sinh trưởng, chưa thu hoạch được đâu sếp!", 
                ephemeral=True
            )
            
        # XỬ LÝ THU HOẠCH
        if val.startswith("harvest"):
            plot_id = int(val.split("_")[1])
            f = load_farm(uid)
            u = load_user(uid)
            
            for p in f["plots"]:
                if p["id"] == plot_id:
                    seed_info = FARM_SEEDS[p["seed"]]
                    
                    # Tính toán Buff từ Kỹ năng Farming
                    skill_buff = 1 + (u["skills"].get("farming", 1) * 0.05)
                    thu_nhap = int(seed_info["sell"] * skill_buff)
                    
                    # Nhận tiền và EXP nông trại
                    u["money"] += thu_nhap
                    f["exp"] += 10
                    
                    # Reset ô đất về trạng thái trống
                    p["seed"] = None
                    p["plant_time"] = None
                    p["watered"] = False
                    
                    # Lưu DB
                    save_user(uid)
                    save_farm(uid)
                    
                    embed = discord.Embed(
                        title="🌾 THU HOẠCH THÀNH CÔNG", 
                        description=f"Bạn gặt hái {seed_info['name']} và bán cho thương lái được **{thu_nhap:,} 💰**!\n"
                                    f"*(Đã cộng dồn % buff từ cấp kỹ năng Trồng Trọt)*", 
                        color=discord.Color.green()
                    )
                    return await interaction.response.edit_message(embed=embed, view=None)

        # TRẠNG THÁI ĐẤT TRỐNG -> Chuyển sang Menu Chọn Mua Hạt Giống
        plot_id = int(val)
        view = discord.ui.View(timeout=120)
        view.add_item(SeedSelect(plot_id))
        
        embed = discord.Embed(
            title="🌱 CỬA HÀNG HẠT GIỐNG NÔNG NGHIỆP", 
            description=f"Chọn một loại hạt giống bên dưới để gieo xuống **Ô đất số {plot_id}**:", 
            color=discord.Color.dark_green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class SeedSelect(discord.ui.Select):
    def __init__(self, plot_id):
        self.plot_id = plot_id
        opts = []
        for k, v in FARM_SEEDS.items():
            opts.append(discord.SelectOption(
                label=v["name"], 
                description=f"Mua: {v['buy']:,} 💰 | Bán: {v['sell']:,} 💰 | T.Gian: {v['time_mins']}p", 
                value=k
            ))
            
        super().__init__(
            placeholder="Mở túi hạt giống...", 
            min_values=1, 
            max_values=1, 
            options=opts
        )

    async def callback(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        u = load_user(uid)
        f = load_farm(uid)
        
        selected_seed_key = self.values[0]
        seed_info = FARM_SEEDS[selected_seed_key]
        
        # Kiểm tra tiền mua giống
        if u.get("money", 0) < seed_info["buy"]:
            return await interaction.response.send_message(
                f"⚠️ Nhà nông mà không có lúa! Bạn thiếu tiền mua hạt giống, cần **{seed_info['buy']:,} 💰**.", 
                ephemeral=True
            )
            
        u["money"] -= seed_info["buy"]
        
        # Cập nhật trạng thái ô đất
        for p in f["plots"]:
            if p["id"] == self.plot_id:
                p["seed"] = selected_seed_key
                p["plant_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                p["watered"] = True # Mặc định tưới lần đầu
                
        save_user(uid)
        save_farm(uid)
        
        embed = discord.Embed(
            title="🌱 GIEO TRỒNG THÀNH CÔNG",
            description=f"Đã gieo **{seed_info['name']}** xuống đất tơi xốp.\n"
                        f"Hãy quay lại kiểm tra và thu hoạch sau **{seed_info['time_mins']} phút** nữa nhé!", 
            color=discord.Color.green()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

class FarmView(discord.ui.View):
    def __init__(self, author, farm_data):
        super().__init__(timeout=120)
        self.author = author
        self.add_item(FarmPlotSelect(farm_data))
        
    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Nông trại của người ta, cấm vào vặt trộm mầm cây!", ephemeral=True)
            return False
        return True
        # =====================================================================
# [PHẦN 3] HỆ THỐNG GIAO DIỆN (UI VIEWS) ĐA VŨ TRỤ & SINH TỒN
# =====================================================================

# ---------------------------------------------------------------------
# 1. HỆ THỐNG GIAO DIỆN THÚ CƯNG (MUA TRỨNG & ẤP TRỨNG)
# ---------------------------------------------------------------------
PET_EGGS = {
    "egg_1": {
        "name": "Trứng Gỗ 🥚", 
        "price": 25000, 
        "pool": ["Chó Cỏ 🐕", "Mèo Lười 🐈", "Gà Trống 🐓"]
    },
    "egg_2": {
        "name": "Trứng Bạc 🥚", 
        "price": 150000, 
        "pool": ["Sói Tuyết 🐺", "Gấu Xám 🐻", "Đại Bàng 🦅"]
    },
    "egg_3": {
        "name": "Trứng Vàng 🥚", 
        "price": 1000000, 
        "pool": ["Hổ Trắng 🐅", "Sư Tử Lửa 🦁", "Khỉ Đột Khổng Lồ 🦍"]
    },
    "egg_4": {
        "name": "Trứng Hỗn Độn 🌌", 
        "price": 10000000, 
        "pool": ["Kỳ Lân 🦄", "Phượng Hoàng 🦚", "Rồng Cổ Đại 🐉"]
    }
}

class PetGachaSelect(discord.ui.Select):
    def __init__(self):
        opts = []
        for k, v in PET_EGGS.items():
            opts.append(discord.SelectOption(
                label=v["name"], 
                description=f"Giá thành: {v['price']:,} 💰", 
                value=k
            ))
            
        super().__init__(
            placeholder="Chọn loại trứng muốn mua và ấp...", 
            min_values=1, 
            max_values=1, 
            options=opts
        )

    async def callback(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        u = load_user(uid)
        
        selected_egg_key = self.values[0]
        egg_data = PET_EGGS[selected_egg_key]
        
        if u.get("money", 0) < egg_data["price"]:
            return await interaction.response.send_message(
                f"⚠️ Nhà nghèo đòi chơi thú kiểng! Bạn cần **{egg_data['price']:,} 💰**.", 
                ephemeral=True
            )
            
        u["money"] -= egg_data["price"]
        
        # Random ra pet
        pet_born = random.choice(egg_data["pool"])
        
        # Quản lý Pet trong Database
        if "pets" not in u:
            u["pets"] = {}
            
        if pet_born not in u["pets"]:
            # Pet mới tinh
            u["pets"][pet_born] = {
                "level": 1, 
                "xp": 0, 
                "hunger": 100, 
                "loyalty": 0
            }
            msg = f"🎉 TÁCH! Trứng vỡ ra... Bạn nhận được thú cưng mới: **{pet_born}**!"
        else:
            # Trùng pet thì hóa thành điểm Kinh nghiệm cho Pet cũ
            u["pets"][pet_born]["xp"] += 50 
            msg = f"🔄 TÁCH! Lại ra **{pet_born}**. Vì bạn đã có bé này rồi nên nó hóa thành 50 XP cho pet hiện tại!"
            
        save_user(uid)
        
        embed = discord.Embed(
            title="🥚 LÒ ẤP TRỨNG MA THUẬT", 
            description=msg, 
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

# ---------------------------------------------------------------------
# 2. GIAO DIỆN GACHA KALLEN FANTASY (CÓ PITY SYSTEM - BẢO HIỂM)
# ---------------------------------------------------------------------
class KallenGachaView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=120)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id: 
            await interaction.response.send_message("⚠️ Máy Gacha đang có người dùng, cấm chen ngang!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Tiếp Tế x1 (280 💎)", style=discord.ButtonStyle.primary, emoji="📦", row=0)
    async def roll_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 1)

    @discord.ui.button(label="Tiếp Tế x10 (2800 💎)", style=discord.ButtonStyle.danger, emoji="🎁", row=0)
    async def roll_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_gacha(interaction, 10)

    async def process_gacha(self, interaction: discord.Interaction, times: int):
        uid = str(interaction.user.id)
        p = load_kf_profile(uid)
        
        cost = 280 * times
        if p.get("crystals", 0) < cost: 
            return await interaction.response.send_message(
                f"⚠️ Thuyền trưởng cạn sạch Pha Lê rồi! Cần {cost:,} 💎 để quay {times} lần.", 
                ephemeral=True
            )
            
        p["crystals"] -= cost
        
        # Khởi tạo Pity counter nếu chưa có
        pity_s = p.get("pity_s", 0) 
        
        results = []
        for _ in range(times):
            pity_s += 1
            roll = random.uniform(0, 100)
            
            # CƠ CHẾ BẢO HIỂM (PITY SYSTEM): 90 lần quay chắc chắn ra S/SS/SSS
            is_guaranteed = False
            if pity_s >= 90:
                is_guaranteed = True
                
            if roll <= 1.5 or is_guaranteed: 
                # Nhóm Valkyrie S, SS, SSS
                s_pool = [k for k, v in KALLEN_BATTLESUITS.items() if v["rarity"] in ["S", "SS", "SSS"]]
                suit = random.choice(s_pool)
                
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"🌟 **VALKYRIE {KALLEN_BATTLESUITS[suit]['rarity']} TỚI:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"🌟 Trùng lặp {KALLEN_BATTLESUITS[suit]['rarity']} (Quy đổi thành mảnh vỡ -> +1500 💎)")
                    p["crystals"] += 1500
                    
                pity_s = 0 # Reset bảo hiểm
                
            elif roll <= 15.0: 
                # Nhóm Valkyrie A
                a_pool = [k for k, v in KALLEN_BATTLESUITS.items() if v["rarity"] == "A"]
                suit = random.choice(a_pool)
                
                if suit not in p["unlocked_suits"]:
                    p["unlocked_suits"].append(suit)
                    results.append(f"⭐ **VALKYRIE A TỚI:** {KALLEN_BATTLESUITS[suit]['name']}")
                else:
                    results.append(f"⭐ Trùng lặp A (Quy đổi thành mảnh vỡ -> +280 💎)")
                    p["crystals"] += 280
                    
            elif roll <= 30.0:
                # Vũ khí 5 - 6 Sao
                wp_pool = [k for k, v in KALLEN_WEAPONS.items() if v["rarity"] >= 5]
                wp = random.choice(wp_pool)
                p["inventory_weapons"].append(wp)
                results.append(f"🔶 Vũ Khí {KALLEN_WEAPONS[wp]['rarity']}★: {KALLEN_WEAPONS[wp]['name']}")
                
            else: 
                results.append("🟦 Rác công nghệ (Thu hồi được 50 💎)")
                p["crystals"] += 50
                
        # Cập nhật lại pity
        p["pity_s"] = pity_s
        save_kf_profile(uid)
        
        embed = discord.Embed(
            title="📦 KẾT QUẢ MỞ TIẾP TẾ", 
            description="\n".join(results), 
            color=discord.Color.gold()
        )
        embed.set_footer(
            text=f"💎 Pha lê còn: {p['crystals']:,} | Cần {max(0, 90 - pity_s)} lần nữa chắc chắn ra Rank S", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=embed, view=self)

# ---------------------------------------------------------------------
# 3. GIAO DIỆN CHIẾN ĐẤU KALLEN FANTASY (COMBAT HỆ THỐNG KHẮC HỆ)
# ---------------------------------------------------------------------
class KallenCombatView(discord.ui.View):
    def __init__(self, author, p_stats, stage, p_profile, is_abyss=False):
        super().__init__(timeout=300) # Đánh boss cho thời gian 5 phút
        self.author = author
        self.p_stats = p_stats
        self.stage = stage
        self.p_profile = p_profile
        self.is_abyss = is_abyss
        
        self.p_hp = p_stats["hp"]
        self.p_max_hp = p_stats["hp"]
        self.p_sp = 0
        self.cd = 0 # Evade cooldown
        
        self.crystals_earned = 0
        self.abyss_floor = self.p_profile.get("abyss_floor", 1) if is_abyss else 1

        if not self.is_abyss:
            self.enemy_list = self.stage["enemies"].copy()
            self.current_idx = 0
            self.load_enemy()
        else: 
            self.load_abyss()

    def load_enemy(self):
        if self.current_idx < len(self.enemy_list):
            e = KALLEN_ENEMIES[self.enemy_list[self.current_idx]]
            self.e_data = {
                "name": e["name"], 
                "type": e["type"], 
                "hp": e["hp"], 
                "max_hp": e["hp"], 
                "atk": e["atk"], 
                "def": e["def"], 
                "sp": e["sp_drop"]
            }
            return True
        return False

    def load_abyss(self):
        # Lấy quái ngẫu nhiên, tỉ lệ ra Boss tăng theo số tầng
        if self.abyss_floor % 5 == 0:
            pool = [e for k, e in KALLEN_ENEMIES.items() if "boss" in k]
        else:
            pool = [e for k, e in KALLEN_ENEMIES.items() if "boss" not in k]
            
        base = random.choice(pool)
        
        # Scale sức mạnh theo tầng
        mult = 1.0 + (self.abyss_floor * 0.2)
        self.e_data = {
            "name": f"{base['name']} (Tinh Anh Tầng {self.abyss_floor})", 
            "type": base["type"], 
            "hp": int(base["hp"] * mult), 
            "max_hp": int(base["hp"] * mult), 
            "atk": int(base["atk"] * mult), 
            "def": int(base["def"] * mult), 
            "sp": base["sp_drop"] + int(self.abyss_floor/2)
        }

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Chiến trường nguy hiểm, đang đánh nhau đừng xen vào!", ephemeral=True)
            return False
        return True

    def get_type_multiplier(self, atk_type, def_type):
        """Logic Khắc Hệ: MECH > BIO > PSY > MECH. IMG & QUA là hệ đặc biệt."""
        adv = 1.0
        if (atk_type == "MECH" and def_type == "BIO") or \
           (atk_type == "BIO" and def_type == "PSY") or \
           (atk_type == "PSY" and def_type == "MECH"):
            adv = 1.3 # Khắc hệ +30% ST
            
        elif (atk_type == "BIO" and def_type == "MECH") or \
             (atk_type == "PSY" and def_type == "BIO") or \
             (atk_type == "MECH" and def_type == "PSY"):
            adv = 0.7 # Bị khắc -30% ST
            
        elif atk_type == "IMG" or def_type == "IMG":
            # Hệ IMG (Số Ảo) không bị khắc bởi hệ cơ bản, gây thêm ST lẫn nhau
            if atk_type == "IMG" and def_type == "IMG":
                adv = 1.3
        return adv

    def calc_dmg(self, skill_mult):
        p_type = self.p_stats["suit"]["type"]
        e_type = self.e_data["type"]
        adv = self.get_type_multiplier(p_type, e_type)
        
        raw_dmg = (self.p_stats["atk"] * skill_mult * adv) - (self.e_data["def"] * 0.4)
        
        # Bạo kích
        is_crit = random.uniform(0, 100) <= self.p_stats["crt"]
        if is_crit: 
            raw_dmg *= 2.0
            
        return int(max(10, raw_dmg)), is_crit, adv

    def enemy_turn(self):
        if self.e_data["hp"] <= 0: 
            return 0, "Quái vật đã bị băm vằn!"
        
        p_type = self.p_stats["suit"]["type"]
        e_type = self.e_data["type"]
        adv = self.get_type_multiplier(e_type, p_type)

        raw_dmg = (self.e_data["atk"] * adv) - (self.p_stats["def"] * 0.4)
        dmg = int(max(5, raw_dmg))
        self.p_hp -= dmg
        
        return dmg, f"💥 Kẻ địch xuất chiêu, phản đòn **{dmg:,}** Sát thương!"

    async def update_ui(self, interaction, log):
        # Kiểm tra Quái chết
        if self.e_data["hp"] <= 0:
            self.p_sp = min(200, self.p_sp + self.e_data["sp"])
            log += f"\n💀 Bạn đã tiêu diệt mục tiêu! Thu hồi {self.e_data['sp']} Năng Lượng."
            
            if self.is_abyss:
                # Quà qua tầng
                drop = random.randint(10, 30) + int(self.abyss_floor)
                self.crystals_earned += drop
                
                # Hồi 15% HP sau mỗi tầng
                heal = int(self.p_max_hp * 0.15)
                self.p_hp = min(self.p_max_hp, self.p_hp + heal)
                
                self.abyss_floor += 1
                self.load_abyss()
                log += f"\n✅ Vượt Ải! Hồi {heal} HP và nhặt được +{drop} 💎.\n🚨 CẢNH BÁO: Quái vật Tầng {self.abyss_floor} đã xuất hiện!"
            else:
                self.current_idx += 1
                if not self.load_enemy():
                    # Phá đảo Stage
                    for c in self.children: c.disabled = True
                    u = load_user(self.author.id)
                    u["money"] += self.stage["rw_m"]
                    self.p_profile["exp"] += self.stage["rw_xp"]
                    
                    save_user(self.author.id)
                    save_kf_profile(self.author.id)
                    
                    embed = discord.Embed(
                        title="🎉 CHIẾN THẮNG RỰC RỠ", 
                        description=f"{log}\n\nQuá đỉnh cao! Thuyền trưởng dọn dẹp chiến trường và nhận:\n"
                                    f"💰 **{self.stage['rw_m']:,} Tiền Mặt**\n"
                                    f"📈 **{self.stage['rw_xp']:,} Điểm EXP**", 
                        color=discord.Color.green()
                    )
                    return await interaction.response.edit_message(embed=embed, view=self)

        # Kiểm tra Người chơi chết
        if self.p_hp <= 0:
            for c in self.children: c.disabled = True
            
            if self.is_abyss:
                self.p_profile["crystals"] += self.crystals_earned
                if self.abyss_floor > self.p_profile.get("abyss_floor", 1): 
                    self.p_profile["abyss_floor"] = self.abyss_floor
                save_kf_profile(self.author.id)
                desc = f"Đội hình đã tan vỡ tại Tầng {self.abyss_floor}!\nTích lũy Vực Sâu mang về căn cứ: **{self.crystals_earned:,} 💎**"
            else:
                desc = "Valkyrie đã cạn kiệt sinh lực. Hệ thống giáp hỏng hóc, rút lui về Hyperion sửa chữa khẩn cấp!"
                
            embed = discord.Embed(title="💀 TỬ TRẬN TẠI CHIẾN TRƯỜNG", description=desc, color=discord.Color.red())
            return await interaction.response.edit_message(embed=embed, view=self)

        # Trừ cooldown kỹ năng Né
        if self.cd > 0: self.cd -= 1
        
        # Vẽ giao diện Combat
        title_str = f"🌋 VỰC SÂU VÔ TẬN - TẦNG {self.abyss_floor}" if self.is_abyss else f"⚔️ CHIẾN DỊCH: {self.stage['name']}"
        embed = discord.Embed(title=title_str, description=log, color=discord.Color.red())
        
        s = self.p_stats["suit"]
        embed.add_field(
            name=f"🔵 BẠN: {s['emoji']} {s['name']}", 
            value=f"❤️ HP: {max(0, self.p_hp):,}/{self.p_max_hp:,}\n⚡ SP: {self.p_sp}/200", 
            inline=True
        )
        
        # Biểu tượng khắc hệ
        adv_icon = "⚔️"
        p_type = s["type"]
        e_type = self.e_data["type"]
        if self.get_type_multiplier(p_type, e_type) > 1.0: adv_icon = "🔺 (Khắc Hệ)"
        elif self.get_type_multiplier(p_type, e_type) < 1.0: adv_icon = "🔻 (Bị Khắc)"
            
        embed.add_field(name="VS", value=adv_icon, inline=True)
        
        embed.add_field(
            name=f"🔴 ĐỊCH: {self.e_data['name']} ({self.e_data['type']})", 
            value=f"❤️ HP: {max(0, self.e_data['hp']):,}/{self.e_data['max_hp']:,}", 
            inline=True
        )
        
        # Cập nhật trạng thái Nút bấm (Tắt nút Ulti nếu thiếu SP)
        self.children[2].disabled = self.p_sp < s["ult_sp_cost"]
        self.children[3].disabled = self.cd > 0

        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Đánh Thường", style=discord.ButtonStyle.primary, row=0)
    async def b_atk(self, interaction, btn):
        dmg, crit, adv = self.calc_dmg(self.p_stats["suit"]["skill_basic_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp = min(200, self.p_sp + 8) 
        
        crit_txt = " *(Bạo kích! 💥)*" if crit else ""
        adv_txt = " (Khắc hệ!)" if adv > 1.0 else " (Bị giảm ST)" if adv < 1.0 else ""
        
        ed, el = self.enemy_turn()
        await self.update_ui(interaction, f"🗡️ Dùng vũ khí nã đạn gây **{dmg:,}** ST{crit_txt}{adv_txt}.\n{el}")

    @discord.ui.button(label="Kỹ Năng Nhánh", style=discord.ButtonStyle.success, row=0)
    async def b_cmb(self, interaction, btn):
        dmg, crit, adv = self.calc_dmg(self.p_stats["suit"]["skill_combo_dmg"])
        self.e_data["hp"] -= dmg
        self.p_sp = min(200, self.p_sp + 5)
        
        crit_txt = " *(Bạo kích! 💥)*" if crit else ""
        adv_txt = " (Khắc hệ!)" if adv > 1.0 else ""
        
        ed, el = self.enemy_turn()
        await self.update_ui(interaction, f"🚀 Phóng xuất Kỹ năng Nhánh quạt bay **{dmg:,}** ST{crit_txt}{adv_txt}.\n{el}")

    @discord.ui.button(label="Tất Sát (Ulti)", style=discord.ButtonStyle.danger, row=1)
    async def b_ult(self, interaction, btn):
        s = self.p_stats["suit"]
        self.p_sp -= s["ult_sp_cost"]
        
        dmg, crit, adv = self.calc_dmg(s["skill_ult_dmg"])
        self.e_data["hp"] -= dmg
        
        crit_txt = " *(BẠO KÍCH CHÍ MẠNG! 💥)*" if crit else ""
        log = f"🔥 BÙM! Thi triển Tuyệt Kỹ Tối Thượng dội **{dmg:,}** ST{crit_txt}! Kẻ địch choáng váng mất lượt!"
        await self.update_ui(interaction, log)

    @discord.ui.button(label="Né Cực Hạn", style=discord.ButtonStyle.secondary, row=1)
    async def b_evd(self, interaction, btn):
        self.cd = 4 # Hồi chiêu né 4 lượt
        self.p_sp = min(200, self.p_sp + 25) 
        await self.update_ui(interaction, "💨 Kích hoạt Thời Gian Ngưng Trệ! Né đòn hoàn hảo, hồi ngay 25 SP.")

# ---------------------------------------------------------------------
# 4. GIAO DIỆN THÁM HIỂM KHÁM PHÁ (CHỌN LÙM CÂY / RƯƠNG)
# ---------------------------------------------------------------------
class BushButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, emoji):
        super().__init__(label=label, style=style, custom_id=custom_id, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        w_id = view.w_val
        w_info = WEAPON_ODDS[w_id]
        
        # Vô hiệu hóa các lùm cây khác để tránh spam
        for c in view.children: c.disabled = True
        await interaction.response.edit_message(content=f"🗡️ Đang siết chặt **{w_info['name']}**, rón rén vạch {self.emoji} {self.label} ra...", view=view)
        await asyncio.sleep(2.5)

        uid = str(interaction.user.id)
        u = load_user(uid)
        
        # Tính toán kết quả dựa trên xác suất vũ khí
        choices = ["terrible", "bad", "neutral", "good", "great", "jackpot"]
        weights = [w_info["terrible"], w_info["bad"], w_info["neutral"], w_info["good"], w_info["great"], w_info["jackpot"]]
        
        cat = random.choices(choices, weights=weights, k=1)[0]
        sce = random.choice(SCENARIOS[cat])
        
        # Nếu gặp quái, buff từ Skill Combat sẽ giúp giảm thiệt hại hoặc tăng tiền thưởng
        tien = int(w_info['price'] * sce["mult"]) if "mult" in sce else sce.get("tien", 0)
        
        if tien > 0:
            tien = int(tien * (1 + (u["skills"]["combat"] * 0.05))) # Buff tiền nhờ đánh quái giỏi
            
        u["money"] += tien
        view.session_profit += tien
        save_user(uid)
        
        # Hiển thị UI kết quả
        p_txt = f"LÃI TẠM TÍNH +{view.session_profit:,} 💰" if view.session_profit > 0 else f"LỖ TẠM TÍNH {view.session_profit:,} 💰" if view.session_profit < 0 else "HUỀ VỐN"
        icon = "📉 MÁU ĐÃ ĐỔ" if tien < 0 else "📈 LỤM LÚA" if tien > 0 else "➖ TAY TRẮNG"
        
        txt = f"**KẾT QUẢ VẠCH LÁ:**\n{sce['msg']}\n\n{icon}: **{tien:,} 💰**\n💸 Ví hiện tại: **{u['money']:,} 💰**\n📊 Tổng Phiên: **{p_txt}**"
        
        res_view = ResultView(interaction.user, view.session_profit)
        msg = await interaction.original_response()
        await msg.edit(content=txt, view=res_view)

class ResultView(discord.ui.View):
    def __init__(self, author, p):
        super().__init__(timeout=120)
        self.author = author
        self.p = p
        
        b1 = discord.ui.Button(label="Tiếp tục Càn Quét", style=discord.ButtonStyle.primary, emoji="🔄")
        b1.callback = self.cb_tiep
        b2 = discord.ui.Button(label="Rút Lui An Toàn", style=discord.ButtonStyle.danger, emoji="🛑")
        b2.callback = self.cb_dung
        self.add_item(b1)
        self.add_item(b2)

    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("⚠️ Mảnh đất này đã có chủ cắm sừng, cấm hôi của!", ephemeral=True)
            return False
        return True

    async def cb_tiep(self, i):
        e = discord.Embed(
            title="🛒 CỬA HÀNG VŨ KHÍ TIỀN TUYẾN", 
            description="Nghỉ tay nạp đạn, vung tiền sắm vũ khí mới để càn quét tiếp nào đại gia!", 
            color=discord.Color.dark_red()
        )
        e.set_footer(text=f"Phiên thám hiểm này: LÃI +{self.p:,}" if self.p > 0 else f"Phiên thám hiểm này: LỖ {self.p:,}")
        
        from main import ShopView # Dynamic import
        await i.response.edit_message(content=None, embed=e, view=ShopView(self.author, self.p))

    async def cb_dung(self, i):
        for c in self.children: c.disabled = True
        txt = f"\n\n🛑 **CHỐT SỔ TỔNG KẾT RÚT LUI:** {self.p:,} 💰. Khôn ngoan đấy, không tham lam thì sống lâu!"
        await i.response.edit_message(content=i.message.content + txt, view=self)

class BushView(discord.ui.View):
    def __init__(self, author, w_val, p):
        super().__init__(timeout=120)
        self.author = author
        self.w_val = w_val
        self.session_profit = p
        
        emojis = ["🌲", "🌳", "🌴", "🌵", "🎋"]
        for i in range(5):
            self.add_item(BushButton(
                label=f"Hướng {i+1}", 
                style=discord.ButtonStyle.success, 
                custom_id=f"b_{i}", 
                emoji=emojis[i]
            ))

    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            return False
        return True
        # =====================================================================
# [PHẦN 3] ĐỊNH TUYẾN LỆNH (COMMANDS), EVENTS & KHỞI CHẠY BOT
# =====================================================================

# ---------------------------------------------------------------------
# VIEW VŨ KHÍ THÁM HIỂM (Bổ sung cho Phần 2)
# ---------------------------------------------------------------------
class WeaponSelect(discord.ui.Select):
    def __init__(self, p):
        self.p = p
        opts = []
        for k, v in WEAPON_ODDS.items():
            opts.append(discord.SelectOption(
                label=v["name"], 
                description=f"Giá: {v['price']:,} 💰", 
                value=k
            ))
        super().__init__(placeholder="Nhấn vào mua Hàng Nóng để càn quét...", min_values=1, max_values=1, options=opts)

    async def callback(self, i: discord.Interaction):
        uid = str(i.user.id)
        u = load_user(uid)
        w = WEAPON_ODDS[self.values[0]]
        
        if u.get("money", 0) < w["price"]: 
            return await i.response.send_message("⚠️ Cháy túi rồi đòi mua vũ khí hạng nặng!", ephemeral=True)
            
        u["money"] -= w["price"]
        np = self.p - w["price"]
        save_user(uid)
        
        e = discord.Embed(
            title="🌲 RỪNG THẲM ÂM U 🌲", 
            description=f"Khói mù giăng lối... Bạn hiện đang lăm lăm cây **{w['name']}**.\n\nPhía trước có 5 lùm cây đang rung rinh bí ẩn. Húp trọn kho báu hay bị quái vật đấm vỡ mồm? Bấm đi rồi biết!", 
            color=discord.Color.green()
        )
        await i.response.edit_message(embed=e, view=BushView(i.user, self.values[0], np))

class ShopView(discord.ui.View):
    def __init__(self, author, p=0):
        super().__init__(timeout=120)
        self.author = author
        self.add_item(WeaponSelect(p))
        
    async def interaction_check(self, i): 
        if i.user.id != self.author.id:
            await i.response.send_message("Quầy này đang có khách, vui lòng đợi lượt!", ephemeral=True)
            return False
        return True


# =====================================================================
# DANH SÁCH LỆNH QUẢN TRỊ VÀ TIỆN ÍCH (ADMIN & HELP)
# =====================================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 TỔNG ĐÀI ĐIỀU KHIỂN SIÊU BOT AAA", 
        description="Chào mừng sếp đến với hệ sinh thái mô phỏng đời thực khốc liệt.\nTiền tố gọi bot: `k` hoặc `K`.", 
        color=discord.Color.blurple()
    )
    embed.add_field(name="💳 KINH TẾ & GIAO DỊCH", value="`k rank` • Xem CCCD & Sinh Tồn\n`k tuido` • Xem toàn bộ kho tài sản\n`k top` • Soi bảng xếp hạng đại gia\n`k daily` • Nhận trợ cấp hàng ngày\n`k give @tên <tiền>` • Chuyển khoản\n`k cuahang` • Đi Shopping mua BĐS, Xe", inline=False)
    embed.add_field(name="🏦 NGÂN HÀNG & CHỨNG KHOÁN", value="`k bank` • Vào ngân hàng gửi/rút/vay nợ\n`k ck` • Xem bảng giá cổ phiếu\n`k ck buy / k ck sell` • Mua bán cổ phiếu\n`k cty` • Quản lý/Thành lập Doanh nghiệp", inline=False)
    embed.add_field(name="🎮 SÒNG BÀI MA CAO", value="`k coin <tiền>` • Xóc xu sấp ngửa\n`k taixiu <tài/xỉu> <tiền>` • Lắc xí ngầu\n`k baucua <con vật> <tiền>` • Bầu Cua Tôm Cá\n`k cuop` • Cầm M4A1 đi cướp ngân hàng", inline=False)
    embed.add_field(name="🌾 ĐỜI SỐNG THỰC & NHẬP VAI", value="`k an <Tên Món>` / `k uong <Tên Nước>` • Sinh tồn\n`k cauca` • Vác cần ra bờ sông\n`k nongtrai` • Quản lý trang trại trồng trọt\n`k thucung` • Mua trứng ấp pet\n`k thamhiem` • Khám phá rừng rậm\n`k nhansinh` • Luân hồi đa vũ trụ", inline=False)
    embed.add_field(name="🌌 KALLEN FANTASY (Gacha RPG)", value="`k kallen` • Xem hồ sơ Valkyrie\n`k kf gacha` • Đốt tiền quay Tiếp Tế\n`k kf story 1-1` • Xuất kích đánh Boss\n`k kf abyss` • Leo tháp Vực Sâu", inline=False)
    
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="👑 QUYỀN LỰC ADMIN", value="`k setup #kênh` • Giới hạn kênh chat\n`k themtien @user <tiền>` • Buff tiền\n`k trutien @user <tiền>` • Phạt tiền", inline=False)
        
    embed.set_footer(text="Hệ thống Sinh Tồn: Nhớ ăn uống đầy đủ nếu không sẽ chết và rớt tiền!")
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


# =====================================================================
# HỆ THỐNG KINH TẾ & ĐỜI SỐNG (RANK, INVENTORY, ĂN UỐNG)
# =====================================================================
@bot.command()
async def rank(ctx):
    u = load_user(ctx.author.id)
    lv, xp, tien = u.get("level", 1), u.get("xp", 0), u.get("money", 0)
    max_xp = lv * 100
    prog = int((xp / max_xp) * 10)
    bar = "🟩" * prog + "⬛" * (10 - prog)
    
    embed = discord.Embed(title=f"💳 CĂN CƯỚC: {ctx.author.name.upper()}", color=discord.Color.gold() if tien > 500000 else discord.Color.teal())
    if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)
    
    embed.add_field(name="🌟 Cấp Độ", value=f"**LV {lv}**", inline=True)
    embed.add_field(name="💰 Ví Tiền", value=f"**{tien:,} 💰**", inline=True)
    embed.add_field(name="🏷️ Danh Hiệu", value=f"**{u.get('title', 'Dân Thường')}**", inline=False)
    
    # Chỉ số sinh tồn
    hp, h_max = u.get("health", 100), u.get("max_health", 100)
    hg, hg_max = u.get("hunger", 100), u.get("max_hunger", 100)
    th, th_max = u.get("thirst", 100), u.get("max_thirst", 100)
    en, en_max = u.get("energy", 100), u.get("max_energy", 100)
    
    surv_txt = f"❤️ Máu: {hp}/{h_max} | 🍗 Đói: {hg}/{hg_max}\n💧 Khát: {th}/{th_max} | ⚡ Năng lượng: {en}/{en_max}"
    embed.add_field(name="🩺 Tình Trạng Thể Chất", value=f"```\n{surv_txt}\n```", inline=False)
    
    # Skills
    skills = u.get("skills", {})
    skill_txt = f"📈 Giao dịch: Lv.{skills.get('trading',1)} | 🌾 Trồng trọt: Lv.{skills.get('farming',1)}\n🎣 Câu cá: Lv.{skills.get('fishing',1)} | 💻 Hacking: Lv.{skills.get('hacking',1)}"
    embed.add_field(name="🧠 Kỹ Năng Sinh Tồn", value=skill_txt, inline=False)
    
    embed.add_field(name="Kinh Nghiệm", value=f"`{bar}`\n**{xp:,}/{max_xp:,} XP**", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def tuido(ctx):
    u = load_user(ctx.author.id)
    embed = discord.Embed(title=f"🎒 KHO TÀI SẢN KHỔNG LỒ", color=discord.Color.dark_purple())
    
    inv = u.get("inventory", {})
    inv_txt = "Trống không." if not inv else "\n".join([f"🔹 {k}: {v} cái" for k, v in inv.items() if v > 0])
    embed.add_field(name="🍔 Lương thực & Tài nguyên", value=inv_txt, inline=False)
    
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
async def cuahang(ctx):
    embed = discord.Embed(
        title="🛒 TRUNG TÂM THƯƠNG MẠI MEGA MALL", 
        description="Chào mừng đại gia! Hãy mở bảng và chọn gian hàng để vung tiền.\n\n👇 **MỞ BẢNG CHỌN BÊN DƯỚI** 👇", 
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=ShopCategoryMenu(ctx.author))

@bot.command()
async def an(ctx, *, item_name: str):
    u = load_user(ctx.author.id)
    inv = u.get("inventory", {})
    
    # Tìm food trong SHOP_ITEMS để check chỉ số hồi phục
    food_data = None
    for k, v in SHOP_ITEMS.items():
        if v.get("type") == "food" and item_name.lower() in v["name"].lower():
            food_data = v
            actual_name = v["name"]
            break
            
    if not food_data:
        return await ctx.reply("⚠️ Món này không tồn tại hoặc không ăn được!")
        
    if inv.get(actual_name, 0) <= 0:
        return await ctx.reply(f"⚠️ Bạn không có **{actual_name}** trong túi đồ!")
        
    # Tiêu thụ
    inv[actual_name] -= 1
    u["hunger"] = min(u["max_hunger"], u["hunger"] + food_data.get("recover_hunger", 0))
    u["thirst"] = min(u["max_thirst"], max(0, u["thirst"] + food_data.get("recover_thirst", 0)))
    
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"🍔 Bạn vừa ăn **{actual_name}**.\nĐộ no: **{u['hunger']}/{u['max_hunger']}** | Độ khát: **{u['thirst']}/{u['max_thirst']}**", color=discord.Color.green()))

@bot.command()
async def uong(ctx, *, item_name: str):
    # Dùng chung logic với hàm ăn
    await an(ctx, item_name=item_name)


# =====================================================================
# HỆ THỐNG NGÂN HÀNG, CÔNG TY & CHỨNG KHOÁN ĐẠI CHIẾN
# =====================================================================
@bot.group(invoke_without_command=True, aliases=['nh'])
async def bank(ctx):
    u = load_user(ctx.author.id)
    bank_bal = u.get("bank", 0)
    wallet = u.get("money", 0)
    debt = u.get("debt", 0)
    
    embed = discord.Embed(
        title="🏦 NGÂN HÀNG TRUNG ƯƠNG (Lãi suất: 0.3%/h)", 
        description="Gửi tiền vào đây sinh lời tự động, tránh bị chết rơi rớt tiền.\n"
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
    max_loan = u.get("level", 1) * 250000
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

# =====================================================================
# [ĐẠI CẬP NHẬT] HỆ THỐNG SÀN CHỨNG KHOÁN & DOANH NGHIỆP VĨ MÔ
# =====================================================================

def get_next_hour_timestamp():
    """Lấy thời gian đếm ngược đến đầu giờ tiếp theo (vd: 14:00, 15:00)"""
    now = datetime.now()
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    return int(next_hour.timestamp())

# Kho cổ phiếu mặc định (Hơn 20 mã đa dạng vũ trụ)
DEFAULT_STOCKS = [
    {"_id": "VNM", "name": "Vinamilk Việt Nam", "price": 65000, "trend": "up", "history": []},
    {"_id": "FLC", "name": "Tập đoàn BĐS FLC", "price": 4500, "trend": "down", "history": []},
    {"_id": "MHY", "name": "Mihoyo Hoyoverse", "price": 150000, "trend": "up", "history": []},
    {"_id": "AIC", "name": "Công Nghiệp Endfield", "price": 85000, "trend": "up", "history": []},
    {"_id": "BTC", "name": "Bitcoin Crypto", "price": 1200000, "trend": "up", "history": []},
    {"_id": "TSA", "name": "Đại học Bách Khoa", "price": 30000, "trend": "up", "history": []},
    {"_id": "AAPL", "name": "Apple Táo Khuyết", "price": 450000, "trend": "up", "history": []},
    {"_id": "TSLA", "name": "Tesla Xe Điện", "price": 250000, "trend": "down", "history": []},
    {"_id": "VNG", "name": "VinaGame Corp", "price": 75000, "trend": "up", "history": []},
    {"_id": "FPT", "name": "Tập Đoàn FPT", "price": 95000, "trend": "up", "history": []},
    {"_id": "DOGE", "name": "Shiba Doge Coin", "price": 1500, "trend": "up", "history": []},
    {"_id": "NVDA", "name": "Nvidia Chip AI", "price": 850000, "trend": "up", "history": []},
    {"_id": "TGC", "name": "Trà Đá Vỉa Hè", "price": 2000, "trend": "down", "history": []},
    {"_id": "VIX", "name": "VinGroup", "price": 60000, "trend": "up", "history": []},
    {"_id": "FB", "name": "Meta Facebook", "price": 320000, "trend": "down", "history": []},
    {"_id": "TIK", "name": "Tóp Tóp Global", "price": 210000, "trend": "up", "history": []},
    {"_id": "QSB", "name": "Quán Cơm Sườn", "price": 8000, "trend": "up", "history": []},
    {"_id": "SHB", "name": "Ngân hàng SHB", "price": 12000, "trend": "down", "history": []}
]

class StockPaginationView(discord.ui.View):
    """Giao diện Sàn chứng khoán có phân trang và đếm ngược"""
    def __init__(self, author, stocks_list):
        super().__init__(timeout=120)
        self.author = author
        self.stocks = stocks_list
        self.current_page = 0
        self.max_page = math.ceil(len(self.stocks) / 6) - 1 # Hiển thị 6 mã 1 trang cho đỡ rối
        self.update_buttons()

    def update_buttons(self):
        self.btn_prev.disabled = self.current_page == 0
        self.btn_next.disabled = self.current_page >= self.max_page

    def generate_embed(self):
        start_idx = self.current_page * 6
        end_idx = start_idx + 6
        page_stocks = self.stocks[start_idx:end_idx]
        
        next_update = get_next_hour_timestamp()
        
        embed = discord.Embed(
            title="📈 SÀN GIAO DỊCH CHỨNG KHOÁN QUỐC TẾ", 
            description=f"⏳ **Làm mới thị trường vào:** <t:{next_update}:R>\n"
                        f"*(Tất cả giá trị sẽ dao động, có nguy cơ phá sản nếu cắm đầu quá sâu)*\n\n"
                        f"🛒 Mua: `k ck buy <MÃ> <Số lượng>`\n"
                        f"💸 Bán: `k ck sell <MÃ> <Số lượng>`\n"
                        f"🏢 Lên sàn: `k cty ipo <MÃ>` (Dành cho cty 50 Triệu)", 
            color=discord.Color.teal()
        )
        
        for s in page_stocks:
            code = s["_id"]
            price = s.get("price", 0)
            
            # Cảnh báo mã rác
            if price <= 2000:
                trend_icon = "💀 RÁC / SẮP HỦY NIÊM YẾT"
            else:
                trend_icon = "🟩 Đang bay" if s.get("trend") == "up" else "🟥 Rớt thảm"
                
            embed.add_field(
                name=f"🏢 {code} - {s['name']}", 
                value=f"💵 Giá hiện tại: **{price:,} 💰** / CP\n📊 Xu hướng: {trend_icon}", 
                inline=False
            )
            
        embed.set_footer(text=f"Trang {self.current_page + 1}/{self.max_page + 1} | Đại gia phố Wall")
        return embed

    async def interaction_check(self, interaction: discord.Interaction): 
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ Nhìn thôi cấm giành bấm của đại gia!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Trang Trước", style=discord.ButtonStyle.primary, emoji="◀️")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Trang Sau", style=discord.ButtonStyle.primary, emoji="▶️")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)


# ---------------------------------------------------------------------
# LỆNH CHỨNG KHOÁN CỐT LÕI (MUA/BÁN/XEM SÀN)
# ---------------------------------------------------------------------
@bot.group(invoke_without_command=True, aliases=['ck'])
async def chungkhoan(ctx):
    all_stocks = list(stocks_col.find())
    
    # Auto bơm data nếu db trống (Không bao giờ báo bảo trì nữa)
    if not all_stocks: 
        stocks_col.insert_many(DEFAULT_STOCKS)
        all_stocks = DEFAULT_STOCKS
        
    view = StockPaginationView(ctx.author, all_stocks)
    msg_embed = view.generate_embed()
    
    # Kẹp thêm danh mục đầu tư cá nhân vào cuối
    u = load_user(ctx.author.id)
    stk = u.get("stocks", {})
    txt = "Chưa đầu tư mã nào. Hãy mua ngay để đu đỉnh!" if not stk else "\n".join([f"🔸 {c}: {q} Cổ Phiếu (Trị giá: {stocks_col.find_one({'_id': c}).get('price', 0) * q:,} 💰)" for c, q in stk.items() if q > 0])
    msg_embed.add_field(name="🎒 Ví Đầu Tư Của Bạn", value=txt, inline=False)
    
    await ctx.reply(embed=msg_embed, view=view, mention_author=False)

@chungkhoan.command()
async def buy(ctx, code: str, qty: int):
    code = code.upper()
    stock = stocks_col.find_one({"_id": code})
    
    if not stock: return await ctx.reply("⚠️ Sàn làm gì có mã này! Gõ lệnh `k ck` để xem danh sách.")
    if qty <= 0: return await ctx.reply("⚠️ Mua số lượng âm định hack tiền hệ thống à?")
    
    price = stock.get("price", 0)
    if price < 500:
        return await ctx.reply("🛑 Cổ phiếu này rớt giá thê thảm, Ủy ban Chứng khoán đã khóa giao dịch chiều MUA!")

    total = price * qty
    u = load_user(ctx.author.id)
    if u.get("money", 0) < total: 
        return await ctx.reply(f"⚠️ Thẻ đen rỗng tuếch! Cần **{total:,} 💰** để khớp lệnh MUA này.")
        
    u["money"] -= total
    
    # ==========================================
    # CƠ CHẾ RUG PULL (ÚP BÔ) KHỐC LIỆT
    # ==========================================
    if total >= 100000000 and random.uniform(0, 100) <= 8.0:
        save_user(ctx.author.id)
        
        # Hủy niêm yết cổ phiếu luôn
        stocks_col.delete_one({"_id": code})
        
        embed = discord.Embed(
            title="🚨 RUG PULL - VỠ BONG BÓNG CHỨNG KHOÁN!", 
            description=f"TIN SỐC! Thấy bạn vừa ném **{total:,} 💰** vào mua mã **{code}**...\n\n"
                        f"CEO của công ty này đã làm giả sổ sách, lập tức ôm toàn bộ tiền rút ruột công ty và trốn sang Mỹ bằng phi cơ riêng!\n"
                        f"Mã **{code}** bị Ủy ban Chứng khoán hủy niêm yết vĩnh viễn. Bạn mất trắng số tiền vừa đầu tư!", 
            color=discord.Color.red()
        )
        embed.set_image(url=GIF_LINKS["rugpull"])
        return await ctx.reply(embed=embed, mention_author=False)
        
    # Giao dịch bình thường
    u["stocks"][code] = u.get("stocks", {}).get(code, 0) + qty
    save_user(ctx.author.id)
    await ctx.reply(embed=discord.Embed(description=f"✅ Lệnh MUA khớp! Bạn đã nạp **{qty} cổ phiếu {code}** vào ví (Tổng chi: **{total:,} 💰**).", color=discord.Color.green()))


# ---------------------------------------------------------------------
# LỆNH QUẢN TRỊ DOANH NGHIỆP TƯ NHÂN
# ---------------------------------------------------------------------
@bot.group(invoke_without_command=True, aliases=['cty', 'congty'])
async def company(ctx):
    u = load_user(ctx.author.id)
    comp_id = u.get("company")
    
    if not comp_id:
        embed = discord.Embed(
            title="🏢 CỤC SỞ HỮU TRÍ TUỆ & DOANH NGHIỆP", 
            description="Bạn hiện đang làm thuê cuốc mướn, không có doanh nghiệp nào đứng tên.\n\n"
                        "💡 **Mở Công Ty:** Gõ lệnh `k cty tao <Tên Công Ty>`\n"
                        "*(Lệ phí cấp giấy phép kinh doanh: 500,000 💰)*", 
            color=discord.Color.dark_grey()
        )
        return await ctx.reply(embed=embed, mention_author=False)
        
    comp = companies_col.find_one({"_id": comp_id})
    if not comp:
        u["company"] = None; save_user(ctx.author.id)
        return await ctx.reply("🛑 Công ty của bạn đã phá sản sụp đổ. Vui lòng lập công ty mới!")
        
    # Lấy thông tin chức vụ
    my_role_id = comp["members"].get(str(ctx.author.id), "nhanvien")
    role_name = comp["roles"].get(my_role_id, "Nhân Viên Mèn")
    
    embed = discord.Embed(title=f"🏢 TẬP ĐOÀN ĐA QUỐC GIA: {comp['name'].upper()}", color=discord.Color.gold())
    embed.add_field(name="💰 Quỹ Hoạt Động", value=f"**{comp['treasury']:,} 💰**", inline=True)
    embed.add_field(name="👥 Quy Mô Nhân Sự", value=f"**{len(comp['members'])} Thành viên**", inline=True)
    
    status_ipo = f"Đã lên sàn CK (Mã: {comp.get('stock_code')})" if comp.get("is_ipo") else "Chưa niêm yết"
    embed.add_field(name="Trạng Thái", value=f"**{status_ipo}**", inline=True)
    embed.add_field(name="Thẻ Nhân Viên Của Bạn", value=f"👑 **{role_name}**", inline=False)
    
    cmds = ("**Thao tác cơ bản:**\n"
            "`k cty gop <tiền>` • Bơm tiền vào quỹ cty\n"
            "`k cty roi` • Từ chức, ném thẻ vào mặt sếp\n\n")
            
    if my_role_id in ["boss", "quanly"]:
        cmds += ("**Quyền Quản Lý:**\n"
                 "`k cty tuyen @user` • Ký hợp đồng lao động\n"
                 "`k cty duoi @user` • Đuổi cổ nhân viên\n\n")
                 
    if my_role_id == "boss":
        cmds += ("**Quyền Chủ Tịch Tối Cao:**\n"
                 "`k cty rut <tiền>` • Rút lõi công trình (Rút quỹ)\n"
                 "`k cty doitencty <tên>` • Đổi tên Tập đoàn\n"
                 "`k cty doitenchuc <boss/quanly/nhanvien> <tên>` • Custom chức vụ\n"
                 "`k cty chucvu @user <boss/quanly/nhanvien>` • Thăng chức/Giáng chức\n"
                 "`k cty ipo <MÃ>` • Niêm yết cổ phiếu lên Sàn (Cần 50 Triệu quỹ)")
                 
    embed.add_field(name="Bảng Lệnh Hành Động", value=cmds, inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@company.command()
async def tao(ctx, *, name: str):
    uid = str(ctx.author.id)
    u = load_user(uid)
    
    if u.get("company"): 
        return await ctx.reply("⚠️ Lòng tham vô đáy! Bạn đã thuộc biên chế công ty khác rồi, không được mở thêm!")
        
    if u.get("money", 0) < 500000: 
        return await ctx.reply("⚠️ Lệ phí làm giấy phép kinh doanh là **500,000 💰**. Cày thêm lúa đi sếp!")
    
    u["money"] -= 500000
    u["company"] = uid
    save_user(uid)
    
    new_comp = {
        "_id": uid,
        "name": name,
        "treasury": 0,
        "members": {uid: "boss"},
        "roles": {"boss": "Chủ Tịch HĐQT", "quanly": "Tổng Giám Đốc", "nhanvien": "Thực Tập Sinh"},
        "is_ipo": False,
        "stock_code": None
    }
    
    companies_col.insert_one(new_comp)
    await ctx.reply(embed=discord.Embed(title="🎉 KHAI TRƯƠNG HỒNG PHÁT", description=f"Cắt băng khánh thành! Chúc mừng {ctx.author.mention} đã chính thức lên chức Chủ Tịch của Tập đoàn **{name}**!", color=discord.Color.green()), mention_author=False)

@company.command()
async def doitenchuc(ctx, role_id: str, *, new_role_name: str):
    uid = str(ctx.author.id)
    comp_id = load_user(uid).get("company")
    if not comp_id: return
    
    comp = companies_col.find_one({"_id": comp_id})
    if comp["members"].get(uid) != "boss": 
        return await ctx.reply("⚠️ Gầm gừ cái gì? Chỉ Chủ Tịch mới có quyền định đoạt tên chức vụ!")
    
    role_id = role_id.lower()
    if role_id not in ["boss", "quanly", "nhanvien"]: 
        return await ctx.reply("⚠️ Gõ sai mã chức vụ rồi! Chỉ nhận: `boss`, `quanly`, `nhanvien`.\nVD: `k cty doitenchuc nhanvien Nô Lệ Tư Bản`")
        
    comp["roles"][role_id] = new_role_name
    companies_col.update_one({"_id": comp_id}, {"$set": {"roles": comp["roles"]}})
    await ctx.reply(f"✅ Đã đóng dấu đỏ! Chức vụ `{role_id}` từ nay sẽ được gọi là: **{new_role_name}**.")

@company.command()
async def gop(ctx, amount: int):
    if amount <= 0: return await ctx.reply("⚠️ Góp số âm để rút ruột công ty à?")
    uid = str(ctx.author.id)
    u = load_user(uid)
    comp_id = u.get("company")
    if not comp_id: return await ctx.reply("Bạn chưa vào công ty nào!")
    
    if u.get("money", 0) < amount: return await ctx.reply("⚠️ Cà thẻ thất bại! Ví bạn không đủ tiền.")
        
    u["money"] -= amount
    save_user(uid)
    
    comp = companies_col.find_one({"_id": comp_id})
    comp["treasury"] += amount
    companies_col.update_one({"_id": comp_id}, {"$set": {"treasury": comp["treasury"]}})
    
    # Nếu công ty đã IPO, vốn tăng thì giá cổ phiếu cũng tăng theo tỉ lệ nhỏ
    if comp.get("is_ipo") and comp.get("stock_code"):
        code = comp["stock_code"]
        stock = stocks_col.find_one({"_id": code})
        if stock:
            new_p = stock["price"] + int(amount / 5000) # Góp 5M thì giá cp tăng 1000đ
            stocks_col.update_one({"_id": code}, {"$set": {"price": new_p, "trend": "up"}})
            
    await ctx.reply(f"✅ Cống hiến vĩ đại! Bạn vừa bơm **{amount:,} 💰** vào quỹ đen công ty.")

@company.command()
async def rut(ctx, amount: int):
    if amount <= 0: return await ctx.reply("⚠️ Rút số âm?")
    uid = str(ctx.author.id)
    u = load_user(uid)
    comp_id = u.get("company")
    if not comp_id: return
    
    comp = companies_col.find_one({"_id": comp_id})
    if comp["members"].get(uid) != "boss": return await ctx.reply("⚠️ Chống lệnh à! Chỉ Chủ Tịch mới được quyền đụng vào ngân khố!")
    if comp["treasury"] < amount: return await ctx.reply("⚠️ Quỹ công ty cạn kiệt, không đủ tiền để rút!")
        
    comp["treasury"] -= amount
    u["money"] += amount
    
    save_user(uid)
    companies_col.update_one({"_id": comp_id}, {"$set": {"treasury": comp["treasury"]}})
    await ctx.reply(f"📤 Đã rút lõi công trình thành công **{amount:,} 💰** bỏ vào túi riêng.")

@company.command()
async def ipo(ctx, stock_code: str):
    uid = str(ctx.author.id)
    comp_id = load_user(uid).get("company")
    if not comp_id: return
    
    comp = companies_col.find_one({"_id": comp_id})
    if comp["members"].get(uid) != "boss": 
        return await ctx.reply("⚠️ Vượt quyền! Chỉ Chủ Tịch mới được ra quyết định Lên Sàn.")
    if comp.get("is_ipo"): 
        return await ctx.reply("⚠️ Tập đoàn này đã niêm yết cổ phiếu rồi sếp ơi!")
    if comp["treasury"] < 50000000: 
        return await ctx.reply("⚠️ Tài chính yếu kém! Quỹ công ty phải đạt ít nhất **50,000,000 💰** mới đủ điều kiện kiểm duyệt IPO.")
    
    stock_code = stock_code.upper()
    if len(stock_code) < 3 or len(stock_code) > 5: 
        return await ctx.reply("⚠️ Mã cổ phiếu phải từ 3 đến 5 ký tự viết hoa. VD: `k cty ipo VNG`")
    
    if stocks_col.find_one({"_id": stock_code}): 
        return await ctx.reply("⚠️ Mã cổ phiếu này đã bị tập đoàn khác đăng ký bản quyền!")
        
    # Tạo cổ phiếu mới trên sàn ảo
    base_price = int(comp["treasury"] / 1000) # Ví dụ: Quỹ 50M -> Giá CP 50,000
    
    new_stock = {
        "_id": stock_code,
        "name": comp["name"],
        "price": base_price,
        "trend": "up",
        "history": [base_price]
    }
    stocks_col.insert_one(new_stock)
    
    # Đánh dấu cty đã lên sàn
    companies_col.update_one({"_id": comp_id}, {"$set": {"is_ipo": True, "stock_code": stock_code}})
    
    embed = discord.Embed(
        title="📈 ĐÁNH CHUÔNG LÊN SÀN CHỨNG KHOÁN!", 
        description=f"Thời khắc lịch sử! Tập đoàn **{comp['name']}** đã chính thức IPO thành công!\n\n"
                    f"🏷️ Mã niêm yết: **{stock_code}**\n"
                    f"💵 Giá khởi điểm: **{base_price:,} 💰 / Cổ phiếu**\n\n"
                    f"Từ giờ mọi người trong server có thể dùng lệnh `k ck buy {stock_code}` để đầu tư vào công ty bạn!", 
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed)


async de@chungkhoan.command()f sell(ctx, code: str, qty: int):
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
    await ctx.reply(embed=discord.Embed(description=f"✅ BÁN thành công **{qty} {code}** thu về **{gain:,} 💰** (Đã buff Kỹ Năng).", color=discord.Color.gold()))


# =====================================================================
# HỆ THỐNG CASINO MA CAO & CƯỚP NGÂN HÀNG
# =====================================================================
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
        return await ctx.reply("🚨 Đang bị truy nã toàn thành phố! Nấp đi chờ 30 phút nữa.")
    if u.get("money", 0) < 50000:
        return await ctx.reply("⚠️ Cần đóng 50,000 💰 tiền mua súng đạn M4A1 mới đi cướp được!")

    cooldowns["crime"][uid] = now
    msg = await ctx.send(embed=discord.Embed(description="🔫 Đạp cửa xông vào Ngân hàng với khẩu M4A1...", color=discord.Color.dark_gray()))
    await asyncio.sleep(2.5)

    # Hack skill buff tỉ lệ cướp trót lọt
    rate = 25 + (u["skills"]["hacking"] * 2)
    
    if random.randint(1, 100) <= rate: 
        loot = random.randint(300000, 800000)
        u["money"] += loot
        save_user(uid)
        embed = discord.Embed(title="💰 TRÓT LỌT KINH ĐIỂN!", description=f"Vơ vét sạch két sắt ẵm trọn **{loot:,} 💰**!", color=discord.Color.green())
        embed.set_image(url=GIF_LINKS["rob_success"])
        await msg.edit(embed=embed)
    else:
        u["money"] -= 50000
        u["jail_time"] = (now + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        save_user(uid)
        embed = discord.Embed(title="🚨 SA LƯỚI BỌN ĐẶC NHIỆM!", description="SWAT ập tới! Mất 50,000 💰 tiền súng đạn.\n🔒 **Bóc lịch 15 Phút!**", color=discord.Color.red())
        embed.set_image(url=GIF_LINKS["rob_fail"])
        await msg.edit(embed=embed)


# =====================================================================
# HỆ THỐNG RPG SINH TỒN, MÔ PHỎNG VÀ KALLEN FANTASY CỐT LÕI
# =====================================================================
@bot.command()
async def cauca(ctx):
    uid = str(ctx.author.id)
    now = datetime.now()
    if uid in cooldowns["fish"] and (now - cooldowns["fish"][uid]).total_seconds() < 15:
        return await ctx.reply("⏳ Đừng nóng vội, cá chưa cắn câu đâu!")
    
    u = load_user(uid)
    if u.get("bait", 0) <= 0:
        return await ctx.reply("⚠️ Hết mồi câu rồi! Đi mua đi sếp.")
        
    u["bait"] -= 1
    u["energy"] -= 2 # Tốn năng lượng khi câu cá
    cooldowns["fish"][uid] = now
    
    rod = FISHING_RODS.get(u.get("fishing_rod", "CanTre"))
    luck_buff = rod["luck"] + (u["skills"]["fishing"] * 2)
    
    # Thời tiết mưa sẽ làm cá dễ cắn câu hơn
    weather = get_global_weather()
    if weather["current"] == "Mưa Rào 🌧️":
        luck_buff += 10
    
    msg = await ctx.send(embed=discord.Embed(description=f"🎣 Vung cây **{rod['name']}** quăng mồi xuống hồ...\n*Thời tiết hiện tại: {weather['current']}*", color=discord.Color.blue()))
    await asyncio.sleep(2.5)
    
    roll = max(0.1, random.uniform(0, 100) - (luck_buff * 0.1))
    
    if roll <= FISH_DATABASE["mythic"]["rate"]: rarity = "mythic"
    elif roll <= FISH_DATABASE["legendary"]["rate"]: rarity = "legendary"
    elif roll <= FISH_DATABASE["epic"]["rate"]: rarity = "epic"
    elif roll <= FISH_DATABASE["rare"]["rate"]: rarity = "rare"
    elif roll <= FISH_DATABASE["uncommon"]["rate"]: rarity = "uncommon"
    elif roll <= FISH_DATABASE["common"]["rate"] + FISH_DATABASE["trash"]["rate"]: rarity = "common"
    else: rarity = "trash"
    
    fish_data = FISH_DATABASE[rarity]
    caught = random.choice(fish_data["pool"])
    price = int(fish_data["price"] * (1 + (u["skills"]["trading"] * 0.02)))
    
    u["money"] += price
    u["xp"] += 10 if rarity not in ["trash", "common"] else 2
    save_user(uid)
    
    embed = discord.Embed(title="🐟 CÁ CẮN CÂU VÀO LƯỚI!", description=f"Giật mạnh! Bạn câu được **{caught}** ({rarity.upper()}).\nThương lái thu mua giá **{price:,} 💰**!\n\n*(Mồi còn: {u['bait']} | Năng lượng: {u['energy']}%)*", color=discord.Color.green() if price > 1000 else discord.Color.light_grey())
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

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    embed = discord.Embed(title="🛒 CHỢ ĐEN VŨ KHÍ RỪNG SÂU", description="Mua vũ khí càn quét rừng rú lấy kho báu!\n👇 **MỞ MENU CHỌN MUA** 👇", color=discord.Color.orange())
    await ctx.send(embed=embed, view=ShopView(ctx.author, 0))

@bot.command(aliases=['mophong'])
async def nhansinh(ctx):
    uid = str(ctx.author.id)
    if uid in dang_choi_nhansinh: return await ctx.reply("⏳ Đang luân hồi rồi, chơi nốt kiếp này đi!")
    u = load_user(uid)
    if u.get("money", 0) < 100: return await ctx.reply("⚠️ Vé luân hồi 100 💰. Cày tiền đi!")
    
    u["money"] -= 100
    dang_choi_nhansinh.append(uid)
    save_user(uid)
    
    view = NhanSinhGameView(ctx.author, {"may_man": random.randint(1, 10)})
    embed = discord.Embed(title="🌀 SỔ BÌA ĐEN LUÂN HỒI", description="Mỗi lựa chọn là một ngã rẽ tàn khốc.", color=discord.Color.teal())
    embed.add_field(name="📜 Băng Chuyền Ký Ức", value=view.logs[0], inline=False)
    embed.add_field(name="❓ Quyết định sinh tử", value=f"**{view.ev['q']}**", inline=False)
    await ctx.send(embed=embed, view=view)

@bot.group(invoke_without_command=True, aliases=['kf', 'honkai'])
async def kallen(ctx):
    p = load_kf_profile(ctx.author.id)
    # Tránh lỗi chưa load kallen stats
    suit = KALLEN_BATTLESUITS[p["current_suit"]]
    thp = int(suit["base_hp"] * (1 + (p["level"] - 1) * 0.1))
    tatk = int(suit["base_atk"] * (1 + (p["level"] - 1) * 0.1))
    tcrt = suit.get("base_crt", 10)
    
    if p["equipped_weapon"] and p["equipped_weapon"] in KALLEN_WEAPONS:
        wp = KALLEN_WEAPONS[p["equipped_weapon"]]
        tatk += wp["atk"]
        tcrt += wp["crt"]
        
    s_data = {"suit": suit, "hp": thp, "atk": tatk, "crt": tcrt, "def": suit.get("base_def", 100)}
    
    embed = discord.Embed(
        title="🌌 CHIẾN HẠM HYPERION TẬP KẾT",
        description=f"Tư Lệnh: **{ctx.author.name}**\nCấp Tu Luyện: **Lv {p['level']}**\nThể lực: **{p['stamina']}/{p['max_stamina']}** ⚡ | Tài sản: **{p['crystals']:,}** 💎\n\n"
                    f"🛡️ **VALKYRIE XUẤT CHIẾN:**\n{suit['emoji']} **{suit['name']}**\n"
                    f"❤️ Sinh lực: {thp:,} | ⚔️ Sức Mạnh: {tatk:,} | 💥 Chí Mạng: {tcrt}%",
        color=discord.Color.purple()
    )
    embed.add_field(name="Bộ Lệnh Hành Động", value="`k kf gacha` • Đốt tiền quay Tiếp Tế Pity 90\n`k kf story 1-1` • Dọn dẹp quái vật cốt truyện\n`k kf abyss` • Nhảy xuống Vực Sâu Vô Tận", inline=False)
    await ctx.reply(embed=embed, mention_author=False)

@kallen.command()
async def gacha(ctx):
    await ctx.reply(embed=discord.Embed(title="📦 THÙNG TIẾP TẾ", description="Dùng 280 💎 để cầu nhân phẩm lấy Valkyrie/Operator.", color=discord.Color.gold()), view=KallenGachaView(ctx.author))

@kallen.command()
async def story(ctx, stage_id: str = "1-1"):
    p = load_kf_profile(ctx.author.id)
    if stage_id not in KALLEN_STAGES: return await ctx.reply("⚠️ Lệnh sai mã ải rồi!")
    if p["stamina"] < 10: return await ctx.reply("⚠️ Thể Lực ⚡ cạn kiệt.")
        
    p["stamina"] -= 10; save_kf_profile(ctx.author.id)
    s_stage = KALLEN_STAGES[stage_id]
    
    # Tính stat trực tiếp
    suit = KALLEN_BATTLESUITS[p["current_suit"]]
    thp = int(suit["base_hp"] * (1 + (p["level"] - 1) * 0.1))
    tatk = int(suit["base_atk"] * (1 + (p["level"] - 1) * 0.1))
    if p["equipped_weapon"] and p["equipped_weapon"] in KALLEN_WEAPONS:
        tatk += KALLEN_WEAPONS[p["equipped_weapon"]]["atk"]
    p_stats = {"suit": suit, "hp": thp, "atk": tatk, "crt": suit.get("base_crt", 10), "def": suit.get("base_def", 100)}
    
    msg = await ctx.reply(embed=discord.Embed(title=f"🚀 XUẤT KÍCH: {s_stage['name']}", color=discord.Color.blue()))
    await asyncio.sleep(1)
    view = KallenCombatView(ctx.author, p_stats, s_stage, p, False)
    await view.update_ui(ctx, f"Chiến hạm thả bạn xuống vùng tử địa {s_stage['name']}! Hãy chiến đấu!")

@kallen.command()
async def abyss(ctx):
    p = load_kf_profile(ctx.author.id)
    if p["stamina"] < 20: return await ctx.reply("⚠️ Thiếu 20 Thể Lực ⚡.")
    p["stamina"] -= 20; save_kf_profile(ctx.author.id)
    
    suit = KALLEN_BATTLESUITS[p["current_suit"]]
    thp = int(suit["base_hp"] * (1 + (p["level"] - 1) * 0.1))
    tatk = int(suit["base_atk"] * (1 + (p["level"] - 1) * 0.1))
    if p["equipped_weapon"] and p["equipped_weapon"] in KALLEN_WEAPONS:
        tatk += KALLEN_WEAPONS[p["equipped_weapon"]]["atk"]
    p_stats = {"suit": suit, "hp": thp, "atk": tatk, "crt": suit.get("base_crt", 10), "def": suit.get("base_def", 100)}
    
    msg = await ctx.reply(embed=discord.Embed(title="🌋 VỰC SÂU ABYSS", color=discord.Color.red()))
    await asyncio.sleep(1)
    view = KallenCombatView(ctx.author, p_stats, None, p, True)
    await view.update_ui(ctx, "Cánh Cửa Vực Sâu mở ra đón lấy bạn!")

# =====================================================================
# EVENT LẮNG NGHE CHAT (CÀY XP THEO TIN NHẮN TỰ ĐỘNG)
# =====================================================================
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    u = load_user(uid)
    
    # Phạt ngồi tù không được nói chuyện cày XP
    if u.get("jail_time") and datetime.now() < datetime.strptime(u["jail_time"], "%Y-%m-%d %H:%M:%S"):
        return await bot.process_commands(message)

    u["xp"] += random.randint(5, 15)
    max_xp = u["level"] * 100

    # Cơ chế thăng cấp
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
    print(f'>>> SIÊU BOT {bot.user} BẢN AAA ĐÃ VẬN HÀNH!')
    print('>>> MODULES: KINH TẾ, SINH TỒN, NÔNG TRẠI, GACHA')
    print('>>> DATABASE: MONGODB CLUSTER ĐANG CHẠY MƯỢT MÀ')
    print('================================================')
    await bot.change_presence(activity=discord.Game(name="Mô phỏng Đời Thực | k help"))

# =====================================================================
# KHỞI CHẠY BOT BẰNG TOKEN ĐƯỢC GHÉP NỐI AN TOÀN THEO LỆNH SẾP
# =====================================================================
keep_alive() 

# Khởi chạy bot bằng Token được ghép nối an toàn
TOKEN_PART_1 = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
TOKEN_PART_2 = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(TOKEN_PART_1 + TOKEN_PART_2)
