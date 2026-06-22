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
gamble_cooldowns = {} 
nhansinh_cooldowns = {} 
dang_choi_nhansinh = [] 

# =====================================================================
# KẾT NỐI MONGODB VÀ BỘ ĐỆM
# =====================================================================
MONGO_URI = "mongodb+srv://jakinat101084_db_user:Lam17722@cluster0.y6jqmz8.mongodb.net/?appName=Cluster0"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["DiscordBotDB"]
users_col = db["users"]   
config_col = db["config"] 

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
    if ctx.author.guild_permissions.administrator: return True
    if not ctx.guild: return True
    config = load_server_config(ctx.guild.id)
    allowed_channels = config.get("allowed_channels", [])
    if allowed_channels and ctx.channel.id not in allowed_channels: return False
    return True

# =====================================================================
# KHO SỰ KIỆN NHÂN SINH (MỞ RỘNG HÀNG TRĂM KỊCH BẢN)
# =====================================================================

EVENTS_P1 = [ # TUỔI 15
    {
        "q": "Tình cờ nhặt được một chiếc ví rơi ngoài cổng trường.",
        "choices": [
            {"text": "Đem nộp lên công an", "rate": 80, "win": "Chủ ví là tổng tài, hậu tạ bạn món tiền lớn.", "lose": "Bị giam ở phường viết bản tường trình 3 ngày.", "tien_w": 2500, "tien_l": -100},
            {"text": "Bỏ túi xài luôn", "rate": 20, "win": "Không ai biết, bạn bao lớp ăn chè thỏa thích.", "lose": "Bị check camera, bồi thường gấp đôi và bị đuổi học.", "tien_w": 3000, "tien_l": -8000},
            {"text": "Lấy tờ 500k rồi vứt lại ví", "rate": 40, "win": "Trót lọt, bạn nạp game lên VIP.", "lose": "Chủ nhân báo mất, bị tra hỏi phạt nặng.", "tien_w": 1000, "tien_l": -4000},
            {"text": "Giả vờ không thấy", "rate": 95, "win": "Thong thả đi học tiếp, chẳng rước họa vào thân.", "lose": "Đứa đi sau nhặt được đổ oan cho bạn.", "tien_w": 0, "tien_l": -500}
        ]
    },
    {
        "q": "Kỳ thi cuối cấp cận kề, bạn bè rủ cúp học đi net.",
        "choices": [
            {"text": "Ở nhà ôn bài kỹ", "rate": 85, "win": "Đỗ thủ khoa, được họ hàng thưởng nóng.", "lose": "Học tài thi phận, trượt vỏ chuối.", "tien_w": 2500, "tien_l": -500},
            {"text": "Đi net cày rank", "rate": 10, "win": "Gặp idol ở quán net, được kéo lên Thách Đấu và cho tiền.", "lose": "Ngủ gục trên xe tông cột điện thăng thiên.", "tien_w": 3500, "tien_l": -10000, "die_l": True},
            {"text": "Làm phao mang vào", "rate": 35, "win": "Mở phao mượt mà, điểm cao chót vót.", "lose": "Giám thị bắt quả tang, đình chỉ thi 0 điểm.", "tien_w": 2000, "tien_l": -5000},
            {"text": "Ngủ cho khỏe", "rate": 50, "win": "Tinh thần sảng khoái, làm bài vừa đủ đậu.", "lose": "Ngủ nhiều lú não, làm sai phép tính cơ bản 1+1=3.", "tien_w": 800, "tien_l": -1000}
        ]
    },
    {
        "q": "Đang đi học về thì bị chặn đánh xin đểu.",
        "choices": [
            {"text": "Ngoan ngoãn nộp tiền", "rate": 90, "win": "Giữ được mạng sống, chạy về nhà an toàn.", "lose": "Nó chê ít, lột luôn đôi giày real của bạn.", "tien_w": -200, "tien_l": -2000},
            {"text": "Bộc phát Haki đấm lại", "rate": 15, "win": "Đấm gục đại ca, thu sạch tiền bảo kê của bọn chúng!", "lose": "Bị đánh hội đồng chấn thương sọ não, đi luôn.", "tien_w": 5000, "tien_l": -15000, "die_l": True},
            {"text": "Bỏ chạy tốc biến", "rate": 60, "win": "Lẻn vào nhà dân thoát thân thành công.", "lose": "Vấp ổ gà ngã gãy răng, vừa đau vừa mất tiền.", "tien_w": 0, "tien_l": -3000},
            {"text": "Bảo 'Anh tao là trùm khu này'", "rate": 45, "win": "Bọn nó rén, xin lỗi rối rít rồi chuồn.", "lose": "Nó gọi thẳng cho anh bạn ra đối chứng, ăn đập x2.", "tien_w": 0, "tien_l": -4500}
        ]
    },
    {
        "q": "Bạn muốn nổi tiếng trên mạng xã hội từ sớm.",
        "choices": [
            {"text": "Nhảy cover Tóp Tóp", "rate": 55, "win": "Video viral 10 triệu view, nhận booking mỏi tay.", "lose": "Nhảy rách đũng quần, bị thành trò cười cho thiên hạ.", "tien_w": 4000, "tien_l": -1000},
            {"text": "Bóc phốt giang hồ mạng", "rate": 5, "win": "Trở thành chiến thần công lý, nhận donate donate khủng.", "lose": "Bị truy sát tới tận nhà, bay màu trong đêm.", "tien_w": 15000, "tien_l": -20000, "die_l": True},
            {"text": "Livestream chơi game", "rate": 40, "win": "Kỹ năng đỉnh, có người donate cái thẻ 10 triệu.", "lose": "Chửi bậy trên stream bị khóa kênh, trầm cảm.", "tien_w": 2500, "tien_l": -500},
            {"text": "Không chơi mạng xã hội", "rate": 95, "win": "Tâm hồn trong sáng, không bị drama toxic.", "lose": "Bị bạn bè chê là đồ tối cổ.", "tien_w": 0, "tien_l": -100}
        ]
    }
]

EVENTS_P2 = [ # TUỔI 25
    {
        "q": "Tích cóp được chút vốn, bạn muốn làm giàu nhanh.",
        "choices": [
            {"text": "Bắt đáy chứng khoán", "rate": 30, "win": "Cổ phiếu tím lịm! Tiền lãi mua được cả căn nhà.", "lose": "Bị chủ tịch úp bô, cổ phiếu rác hủy niêm yết.", "tien_w": 15000, "tien_l": -25000},
            {"text": "Cắm sổ đỏ đánh xóc đĩa", "rate": 5, "win": "Ăn thông 10 ván! Bạn mua hẳn siêu xe Mẹc-xê-đét.", "lose": "Cháy túi, nhảy cầu kết thúc cuộc đời.", "tien_w": 80000, "tien_l": -50000, "die_l": True},
            {"text": "Khởi nghiệp bún đậu mắm tôm", "rate": 60, "win": "Đông khách nườm nượp, mở 5 chi nhánh.", "lose": "Bị phốt mắm tôm có giòi, sập tiệm đền tiền.", "tien_w": 12000, "tien_l": -8000},
            {"text": "Gửi tiết kiệm ngân hàng", "rate": 95, "win": "Cuộc sống bình yên, có lãi ra tiêu vặt.", "lose": "Lạm phát phi mã, tiền bốc hơi từ từ.", "tien_w": 2000, "tien_l": -1500}
        ]
    },
    {
        "q": "Đồng nghiệp xúi bạn chung vốn buôn Lan Đột Biến.",
        "choices": [
            {"text": "Vay nóng chơi lớn", "rate": 15, "win": "Sang tay ngay chậu lan cùi được 5 tỷ!", "lose": "Thị trường vỡ trận, ôm đống cỏ khô, trốn nợ biệt xứ.", "tien_w": 40000, "tien_l": -45000},
            {"text": "Mua 1 mầm nhỏ thử", "rate": 40, "win": "Bán có lời chút đỉnh đủ mua con SH.", "lose": "Lan chết héo, mất toi vài tháng lương.", "tien_w": 6000, "tien_l": -5000},
            {"text": "Báo công an bắt tụi thổi giá", "rate": 50, "win": "Phá đường dây lừa đảo, được thành phố thưởng lớn.", "lose": "Tụi nó mua chuộc công an, quay lại kiện bạn tội vu khống.", "tien_w": 8000, "tien_l": -12000},
            {"text": "Mặc kệ, đi làm công ăn lương", "rate": 90, "win": "Sống thảnh thơi, tối về ngủ ngon.", "lose": "Thấy đồng nghiệp mua Mẹc, tiếc đến ốm.", "tien_w": 1000, "tien_l": -500}
        ]
    },
    {
        "q": "Bạn được sếp đề bạt lên vị trí Trưởng phòng, nhưng phải đi nhậu chốt hợp đồng liên tục.",
        "choices": [
            {"text": "Nhậu xả láng tới bến", "rate": 45, "win": "Hợp đồng ký ầm ầm, tiền thưởng doanh thu ngập mặt.", "lose": "Thủng dạ dày, xơ gan, nằm viện cấp cứu.", "tien_w": 18000, "tien_l": -15000},
            {"text": "Uống trà đá bàn chuyện làm ăn", "rate": 20, "win": "Gặp đối tác cũng hệ mọt sách, chốt deal triệu đô nhẹ nhàng.", "lose": "Đối tác tự ái chê khinh người, hủy kèo, sếp đuổi việc.", "tien_w": 25000, "tien_l": -8000},
            {"text": "Cho nhân viên cấp dưới đi nhậu thay", "rate": 65, "win": "Bạn thảnh thơi ngồi đếm tiền hoa hồng.", "lose": "Nhân viên nhậu xỉn cướp luôn hợp đồng rồi nghỉ việc.", "tien_w": 8000, "tien_l": -6000},
            {"text": "Từ chối thăng chức", "rate": 85, "win": "Làm nhân viên quèn, sống dai sống thọ.", "lose": "Bị sếp ghim, đày ải làm đủ thứ việc lặt vặt.", "tien_w": 1500, "tien_l": -2000}
        ]
    }
]

EVENTS_P3 = [ # TUỔI 35
    {
        "q": "Bất Động Sản đang sốt, cò đất rủ bạn lướt sóng phân lô bán nền.",
        "choices": [
            {"text": "Cầm nhà ngân hàng quất liền", "rate": 20, "win": "Giá đất x5 trong một đêm! Bạn thành đại gia nghìn tỷ.", "lose": "Dính bẫy lừa đảo dự án ma, ra đê ở, treo cổ tự tử.", "tien_w": 60000, "tien_l": -70000, "die_l": True},
            {"text": "Mua miếng đất nhỏ vùng ven", "rate": 55, "win": "Chính phủ mở đường qua, đất nhân 3 giá trị.", "lose": "Đất dính quy hoạch mỏ đá, bán không ai mua.", "tien_w": 15000, "tien_l": -10000},
            {"text": "Mở lớp dạy làm giàu từ BĐS", "rate": 40, "win": "Lùa được đàn gà đông đảo, thu học phí ngập mồm.", "lose": "Bị học viên bóc phốt úp sọt, đánh nhập viện.", "tien_w": 12000, "tien_l": -15000},
            {"text": "Không quan tâm, lo giữ gia đình", "rate": 95, "win": "Nhà cửa êm ấm, vợ/chồng con cái hạnh phúc.", "lose": "Kinh tế khó khăn, đôi lúc cãi nhau vì tiền điện nước.", "tien_w": 3000, "tien_l": -1500}
        ]
    },
    {
        "q": "Có người gạ bạn vào đường dây buôn lậu hàng cấm.",
        "choices": [
            {"text": "Làm 1 chuyến rồi nghỉ", "rate": 10, "win": "Trót lọt! Ôm mớ tiền trốn ra nước ngoài sống sung tướng.", "lose": "Công an ập vào bắt tại trận, dựa cột tiêm thuốc độc tử hình.", "tien_w": 100000, "tien_l": -100000, "die_l": True},
            {"text": "Làm chỉ điểm cho công an", "rate": 60, "win": "Phá án thành công, được cấp huân chương và thưởng lớn.", "lose": "Bị lộ thân phận, giang hồ thủ tiêu trong hẻm vắng.", "tien_w": 20000, "tien_l": -50000, "die_l": True},
            {"text": "Từ chối nhưng bị uy hiếp", "rate": 50, "win": "Nhờ giang hồ quen biết dàn xếp êm xuôi.", "lose": "Phải cống nạp tiền bảo kê hàng tháng để yên thân.", "tien_w": -1000, "tien_l": -12000},
            {"text": "Chuyển nhà lánh nạn", "rate": 80, "win": "Thoát khỏi vòng xoáy tội lỗi, làm lại từ đầu.", "lose": "Tốn bộn tiền chuyển nhà và thất nghiệp vài tháng.", "tien_w": 0, "tien_l": -4000}
        ]
    },
    {
        "q": "Cuộc hôn nhân của bạn đang có dấu hiệu rạn nứt.",
        "choices": [
            {"text": "Thuê thám tử điều tra", "rate": 50, "win": "Bắt quả tang ngoại tình, ly hôn chia 70% tài sản cho bạn.", "lose": "Phát hiện vợ/chồng bạn là trùm mafia ngầm, bạn bị thủ tiêu.", "tien_w": 15000, "tien_l": -30000, "die_l": True},
            {"text": "Đi du lịch hâm nóng tình cảm", "rate": 70, "win": "Tình yêu quay lại như thuở ban đầu.", "lose": "Đi du lịch cãi nhau to hơn, ly hôn chia đôi tài sản.", "tien_w": 2000, "tien_l": -10000},
            {"text": "Mặc kệ, đi nhậu nhẹt gái gú/trai đẹp", "rate": 30, "win": "Sống sướng bản thân, bung xõa tuổi trẻ.", "lose": "Bị tống cổ ra khỏi nhà với hai bàn tay trắng.", "tien_w": 1000, "tien_l": -25000},
            {"text": "Đăng ký khóa học tâm lý gia đình", "rate": 85, "win": "Hòa giải thành công, gia đình lại hạnh phúc bách niên.", "lose": "Tốn tiền học mà chuyên gia tâm lý lại tư vấn xui ly dị.", "tien_w": 5000, "tien_l": -3000}
        ]
    }
]

EVENTS_P4 = [ # TUỔI 50
    {
        "q": "Bước vào tuổi 50, bạn rơi vào khủng hoảng tuổi trung niên trầm trọng.",
        "choices": [
            {"text": "Bán nhà mua siêu xe Mẹc G63 đua tốc độ", "rate": 15, "win": "Chiến thắng giải đua không chuyên, nổi đình đám ăn quảng cáo.", "lose": "Đạp nhầm chân ga tông xe tải, thăng thiên tại chỗ.", "tien_w": 35000, "tien_l": -40000, "die_l": True},
            {"text": "Chơi đồ cổ, mua Lan Đột Biến", "rate": 35, "win": "Sưu tầm trúng bình gốm đời nhà Thanh, bán đấu giá giàu to.", "lose": "Mua phải bình gốm mẻ Bát Tràng fake, lỗ chổng vó.", "tien_w": 25000, "tien_l": -20000},
            {"text": "Cặp bồ nhí cho hồi xuân", "rate": 25, "win": "Nuôi Sugar Baby/Boy êm thấm, tâm hồn trẻ lại.", "lose": "Bị vợ/chồng bắt ghen tung lên mạng, nhục nhã mất mặt và mất sạch tiền.", "tien_w": 2000, "tien_l": -50000},
            {"text": "Tập Thiền, dọn về quê nuôi cá trồng rau", "rate": 90, "win": "Tâm hồn thanh tịnh, khí huyết lưu thông sống thọ.", "lose": "Về quê bị muỗi vằn chích sốt xuất huyết mém chết.", "tien_w": 5000, "tien_l": -3000}
        ]
    },
    {
        "q": "Con cái phá gia chi tử, báo nợ 10 tỷ.",
        "choices": [
            {"text": "Bán hết gia tài cứu con", "rate": 40, "win": "Con cái tỉnh ngộ, tu chí làm ăn sau này phụng dưỡng bạn.", "lose": "Cứu xong nó lại cờ bạc báo thêm 20 tỷ, bạn tăng xông chết.", "tien_w": 10000, "tien_l": -60000, "die_l": True},
            {"text": "Từ mặt con, báo công an", "rate": 60, "win": "Giữ được tài sản dưỡng già, cắt đứt ung nhọt.", "lose": "Bọn xã hội đen tới đốt nhà bạn để xiết nợ thay con.", "tien_w": 8000, "tien_l": -30000},
            {"text": "Thuê giang hồ xử bọn chủ nợ", "rate": 15, "win": "Giang hồ dẹp yên, con bạn trốn ra nước ngoài an toàn.", "lose": "Hai băng đảng thanh toán nhau, bạn ăn đạn lạc bay màu.", "tien_w": 5000, "tien_l": -50000, "die_l": True},
            {"text": "Lên chùa nương tựa", "rate": 85, "win": "Né tránh bụi trần, ngày gõ mõ tụng kinh bình yên.", "lose": "Vẫn bị bọn đòi nợ lên chùa phá phách, mất tiền bồi thường chùa.", "tien_w": 2000, "tien_l": -8000}
        ]
    }
]

EVENTS_P5 = [ # TUỔI 70
    {
        "q": "Chạm mốc 70 tuổi, một nhà sư bảo bạn sắp tới số.",
        "choices": [
            {"text": "Vung tiền mua Linh Đan Tu Tiên", "rate": 5, "win": "Kỳ tích! Bạn cải lão hoàn đồng thành thanh niên 20 tuổi!", "lose": "Uống nhầm thủy ngân, nội tạng nát vụn thăng thiên sớm.", "tien_w": 200000, "tien_l": -20000, "die_l": True},
            {"text": "Lập di chúc chia đều tài sản", "rate": 75, "win": "Con cháu hòa thuận, tổ chức mừng thọ linh đình.", "lose": "Con cháu chê ít, đánh nhau mẻ đầu mẻ trán, bạn tức quá đột tử.", "tien_w": 5000, "tien_l": -15000, "die_l": True},
            {"text": "Quyên góp 100% tài sản làm từ thiện", "rate": 90, "win": "Được nhà nước tạc tượng vinh danh công đức vô lượng.", "lose": "Tổ chức từ thiện cuỗm tiền bốc hơi, bạn trầm cảm mà đi.", "tien_w": 15000, "tien_l": -50000, "die_l": True},
            {"text": "Lôi hết tiền đi Las Vegas chơi một đêm cuối", "rate": 20, "win": "Thắng Jackpot 50 triệu đô! Lên báo quốc tế rình rang.", "lose": "Thua sạch bong, lên cơn nhồi máu cơ tim gục tại bàn Roulette.", "tien_w": 100000, "tien_l": -40000, "die_l": True}
        ]
    },
    {
        "q": "Bỗng dưng có một cô gái trẻ 20 tuổi đến nhận làm vợ bé.",
        "choices": [
            {"text": "Rước nàng về rinh", "rate": 10, "win": "Nàng chăm sóc bạn chu đáo, bạn sống thọ thêm 20 năm.", "lose": "Mã thượng phong! Đột tử ngay đêm tân hôn.", "tien_w": -5000, "tien_l": -30000, "die_l": True},
            {"text": "Chắc chắn lừa đảo, đuổi đi", "rate": 85, "win": "Bảo vệ được két sắt an toàn.", "lose": "Cô ta gọi đồng bọn tới dàn cảnh cướp giật tài sản.", "tien_w": 2000, "tien_l": -15000},
            {"text": "Cho tiền rồi bảo đi đi", "rate": 60, "win": "Hóa giải nghiệp chướng, tích đức về sau.", "lose": "Bị tống tiền đòi thêm, nợ nần chồng chất.", "tien_w": -2000, "tien_l": -25000},
            {"text": "Giả vờ mất trí nhớ lẩm cẩm", "rate": 95, "win": "Cô ta thấy thế chán nản bỏ đi.", "lose": "Bị đưa vào trại tâm thần nhốt.", "tien_w": 1000, "tien_l": -5000}
        ]
    }
]


# =====================================================================
# DATA THÁM HIỂM KHU RỪNG (HÀNG TÁ BIẾN THỂ MỚI)
# =====================================================================
WEAPON_ODDS = {
    "gay_go": {"price": 50, "name": "Gậy Gỗ Mục", "terrible": 20, "bad": 40, "neutral": 20, "good": 15, "great": 5, "jackpot": 0},
    "kiem_sat": {"price": 200, "name": "Kiếm Sắt Thường", "terrible": 10, "bad": 25, "neutral": 20, "good": 30, "great": 12, "jackpot": 3},
    "kiem_hiep_si": {"price": 500, "name": "Kiếm Hiệp Sĩ", "terrible": 5, "bad": 15, "neutral": 15, "good": 35, "great": 20, "jackpot": 10},
    "thanh_kiem": {"price": 1500, "name": "Thánh Kiếm Truyền Thuyết", "terrible": 0, "bad": 5, "neutral": 10, "good": 30, "great": 35, "jackpot": 20}
}

SCENARIOS = {
    "terrible": [ 
        {"mult": -2.0, "msg": "🐘 **KING KONG NỔI GIẬN!**\nBạn chọc tức chúa tể rừng xanh. Bị đấm bay xa 10km, rớt sạch đồ đạc!"},
        {"mult": -1.5, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt bộn tiền khi bỏ chạy!"},
        {"mult": -1.2, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!**\nGặp ngay băng thổ phỉ khét tiếng. Chúng trói bạn vào gốc cây và lột sạch đồ đạc."},
        {"mult": -1.5, "msg": "💥 **ĐẠP TRÚNG MÌN GOBLIN!**\nBÙM! Bạn đạp trúng mìn tự chế của bọn Goblin. Tốn một mớ tiền để trả phí cấp cứu."},
        {"mult": -1.8, "msg": "👻 **TRÚNG NGẢI HEO!**\nĐi nhầm vào bản làng ma ám. Tiền tài không cánh mà bay, bụng to như mang bầu."},
        {"mult": -2.5, "msg": "🚔 **BỊ KIỂM LÂM BẾ LÊN PHƯỜNG!**\nVô tình chặt nhầm cây cổ thụ ngàn năm. Đóng phạt nứt ví!"},
        {"mult": -1.0, "msg": "🦇 **MA CÀ RỒNG!**\nBị một con ma cà rồng cắn. Trốn thoát được nhưng tốn một đống tiền truyền máu."},
        {"mult": -1.3, "msg": "🕳️ **SỤP HỐ CHÔNG!**\nÁ a a a a! Rơi thẳng xuống hố chông của thợ săn. Gãy 2 cái sườn, nôn hết tiền mặt ra."}
    ],
    "bad": [ 
        {"mult": -0.5, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"mult": -0.4, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi mua bông băng thuốc đỏ."},
        {"mult": -0.3, "msg": "🦟 **MUỖI KHỔNG LỒ!**\nBị bầy muỗi rừng khổng lồ chích sưng vù, phải đi mua thuốc mỡ bôi."},
        {"mult": -0.6, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước tăng lực hết hạn từ máy bán hàng tự động trong rừng."},
        {"mult": -0.8, "msg": "💩 **TRƯỢT CHÂN VÀO BÃI KÍM!**\nBạn dẫm trúng bãi mìn khổng lồ của voi rừng. Tốn tiền mua bộ đồ mới xịt nước hoa."},
        {"mult": -0.2, "msg": "🦅 **BỊ QUẠ ĐỊNH VỊ!**\nMột đàn quạ bay ngang qua và 'bổ sung canxi' lên đầu bạn. Xui xẻo mất tiền sửa vận."},
        {"mult": -0.7, "msg": "📱 **RỚT ĐIỆN THOẠI XUỐNG SUỐI!**\nMải selfie sống ảo, rơi cmn cái iPhone 15 Pro Max xuống nước."},
        {"mult": -0.5, "msg": "🍄 **ĂN NHẦM NẤM CƯỜI!**\nBốc nhầm nấm độc ăn, bạn cười điên dại nửa ngày trời rơi hết cả tiền lẻ trong túi."}
    ],
    "neutral": [ 
        {"mult": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"mult": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."},
        {"mult": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."},
        {"mult": 0, "msg": "🌬️ **GIÓ THỔI LẠNH BẼO...**\nChỉ có gió thổi hiu hiu, khung cảnh yên bình không có biến động gì."},
        {"mult": 0, "msg": "🪨 **MỘT CỤC ĐÁ TO!**\nBạn cố cạy nó lên xem có vàng không, kết quả là... nó chỉ là cục đá."},
        {"mult": 0, "msg": "🐾 **VẾT CHÂN LỢN RỪNG!**\nBạn lần theo dấu vết hy vọng săn được thịt lợn rưng, nhưng mất dấu."}
    ],
    "good": [ 
        {"mult": 0.5, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"mult": 0.6, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá kha khá!"},
        {"mult": 0.8, "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc trả cho bạn một khoản khá hời."},
        {"mult": 1.0, "msg": "🙏 **NGƯỜI TỐT VIỆC TỐT!**\nNhặt được ví của một hiệp sĩ, bạn trả lại và được anh ta hậu tạ một khoản tiền."},
        {"mult": 0.7, "msg": "🍯 **TỔ ONG MẬT KHỔNG LỒ!**\nBạn hun khói lấy được tảng mật ong rừng vàng óng. Thương lái mua với giá rất tốt!"},
        {"mult": 0.4, "msg": "⌚ **ĐỒNG HỒ CŨ!**\nĐào sương sương thấy cái đồng hồ bị gỉ, đem ra tiệm cầm đồ vớt vát được vài đồng."},
        {"mult": 0.9, "msg": "🐕 **CỨU ĐƯỢC CHÓ SĂN!**\nBạn giải cứu một chú chó bị mắc bẫy, chủ của nó thưởng bạn nóng một khoản tiền lớn!"}
    ],
    "great": [ 
        {"mult": 1.5, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp nhỏ và tịch thu kho báu của chúng!"},
        {"mult": 2.0, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, ai ngờ đào trúng viên ngọc lục bảo thô to bằng nắm tay!"},
        {"mult": 2.5, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nBạn phát hiện ra một rương kho báu vàng chóe bị chôn vùi nửa mét dưới đất. Mở ra toàn tiền!"},
        {"mult": 3.0, "msg": "💍 **KIM CƯƠNG RỚT!**\nÁnh sáng lấp lánh đập vào mắt! Hóa ra là một viên kim cương tinh khiết rớt trên thảm cỏ."},
        {"mult": 2.2, "msg": "🏺 **ĐÀO TRÚNG ĐỒ CỔ NHÀ TỐNG!**\nBình gốm ngàn năm không sứt mẻ. Giới siêu giàu vung tiền mua ngay lập tức!"},
        {"mult": 2.8, "msg": "⛏️ **PHÁT HIỆN MỎ VÀNG MINI!**\nNhặt được một cục vàng cục bự chà bá ẩn dưới lớp rêu xanh. Phát tài rồi!"}
    ],
    "jackpot": [ 
        {"mult": 5.0, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số đánh rơi, đem dò trúng giải đặc biệt!"},
        {"mult": 8.0, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Bạn tìm thấy hang động cất giấu kho báu huyền thoại. Một núi Vàng hiện ra trước mắt!"},
        {"mult": 10.0, "msg": "👑 **VƯƠNG MIỆN CỦA VUA ARTHUR! (ULTRAPOT)**\nDưới đáy đầm lầy, bạn vớt được Vương miện nạm 100 viên kim cương đỏ. Bạn trở thành tỷ phú đô la!!"},
        {"mult": 7.5, "msg": "🧚 **CỨU ĐƯỢC THẦN RỪNG! (MEGAPOT)**\nBạn vô tình giải ấn cho vị thần cai quản khu rừng. Ngài ban cho bạn một rương ngập tràn vàng thỏi!"}
    ]
}


# =====================================================================
# GIAO DIỆN GAME NHÂN SINH TƯƠNG TÁC
# =====================================================================

class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        self.ev = random.choice(EVENTS_P1)

        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, chạy quanh nhà bằng siêu xe.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình công chức ấm êm.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn bị vứt lăn lóc ngoài chợ từ nhỏ.")

        self.btn_a = discord.ui.Button(label=f"A. {self.ev['choices'][0]['text']}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_a.callback = self.choice_a
        self.btn_b = discord.ui.Button(label=f"B. {self.ev['choices'][1]['text']}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_b.callback = self.choice_b
        self.btn_c = discord.ui.Button(label=f"C. {self.ev['choices'][2]['text']}", style=discord.ButtonStyle.success, custom_id="btn_c")
        self.btn_c.callback = self.choice_c
        self.btn_d = discord.ui.Button(label=f"D. {self.ev['choices'][3]['text']}", style=discord.ButtonStyle.danger, custom_id="btn_d")
        self.btn_d.callback = self.choice_d

        self.add_item(self.btn_a)
        self.add_item(self.btn_b)
        self.add_item(self.btn_c)
        self.add_item(self.btn_d)

    async def on_timeout(self):
        user_id = str(self.author.id)
        if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng bấm lung tung!", ephemeral=True)
            return False
        return True

    async def choice_a(self, interaction: discord.Interaction): await self.process_choice(interaction, 0, "A")
    async def choice_b(self, interaction: discord.Interaction): await self.process_choice(interaction, 1, "B")
    async def choice_c(self, interaction: discord.Interaction): await self.process_choice(interaction, 2, "C")
    async def choice_d(self, interaction: discord.Interaction): await self.process_choice(interaction, 3, "D")

    async def process_choice(self, interaction: discord.Interaction, choice_idx: int, letter: str):
        choice_data = self.ev["choices"][choice_idx]
        base_rate = choice_data["rate"]
        
        final_rate = min(95, base_rate + (self.stats["may_man"] * 2))
        roll = random.randint(1, 100)
        is_win = roll <= final_rate
        
        res = choice_data["win"] if is_win else choice_data["lose"]
        tien = choice_data["tien_w"] if is_win else choice_data["tien_l"]
        
        is_dead = False
        if is_win and choice_data.get("die_w", False): is_dead = True
        if not is_win and choice_data.get("die_l", False): is_dead = True

        self.tien_an += tien
        
        kq_thung = "✅ **THÀNH CÔNG**" if is_win else "❌ **THẤT BẠI**"
        log_entry = f"🎲 Tỉ lệ: **{final_rate}%** (Đổ ra: {roll})\n{kq_thung}: {res} ({tien} 💰)"
        
        tuoi_hien_tai = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70

        if is_dead:
            self.logs.append(f"👻 **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}\n💀 **BẠN ĐÃ ĐỘT TỬ! Cuộc đời khép lại sớm.**")
            self.phase = 99 
        else:
            self.logs.append(f"🗓️ **Tuổi {tuoi_hien_tai}:** Chọn {letter}.\n{log_entry}")
            self.phase += 1
            if self.phase == 2: self.ev = random.choice(EVENTS_P2)
            elif self.phase == 3: self.ev = random.choice(EVENTS_P3)
            elif self.phase == 4: self.ev = random.choice(EVENTS_P4)
            elif self.phase == 5: self.ev = random.choice(EVENTS_P5)

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.purple())

        stats_text = f"May mắn ban đầu: **{self.stats['may_man']}/10** *(+ {self.stats['may_man']*2}% Tỉ lệ)*"
        embed.add_field(name="🍀 Chỉ số tâm linh", value=stats_text, inline=False)

        if len(self.logs) > 4:
            story = "...\n\n" + "\n\n".join(self.logs[-4:])
        else:
            story = "\n\n".join(self.logs)
            
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase <= 5:
            tuoi_next = 15 if self.phase == 1 else 25 if self.phase == 2 else 35 if self.phase == 3 else 50 if self.phase == 4 else 70
            embed.add_field(name=f"❓ Quyết định tuổi {tuoi_next}", value=self.ev['q'], inline=False)
            self.btn_a.label = f"A. {self.ev['choices'][0]['text']}"
            self.btn_b.label = f"B. {self.ev['choices'][1]['text']}"
            self.btn_c.label = f"C. {self.ev['choices'][2]['text']}"
            self.btn_d.label = f"D. {self.ev['choices'][3]['text']}"
        else:
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.btn_c.disabled = True
            self.btn_d.disabled = True
            self.clear_items() 

            user_id = str(self.author.id)
            if user_id in dang_choi_nhansinh: dang_choi_nhansinh.remove(user_id)

            total_reward = self.tien_an 
            
            user_data = load_user(user_id)
            user_data["money"] += total_reward
            save_user(user_id)

            if total_reward < 0:
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Sống lỗi để lại đống nợ khổng lồ, chủ nợ siết sạch tài sản.\n❌ **BÁO NHÀ!** Khoản nợ: **{total_reward} 💰**\n*(Hệ thống trừ thẳng vào ví, cày `k daily` mà trả nhé!)*", inline=False)
            elif total_reward >= 30000:
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Hưởng thọ trong nhung lụa, làm đại gia trên đỉnh thế giới.\n👑 **ĐẠI PHÚ HÀO!** Di sản để lại: **+{total_reward} 💰**", inline=False)
            else:
                embed.add_field(name="🪦 Về với Cát Bụi", value=f"Cuộc đời êm ấm, thanh thản ra đi.\n💼 **DƯ DẢ!** Di sản để lại: **+{total_reward} 💰**", inline=False)

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{user_data['money']} 💰**", inline=False)

        if interaction.response.is_done(): 
            await interaction.message.edit(embed=embed, view=self)
        else: 
            await interaction.response.edit_message(embed=embed, view=self)


# =====================================================================
# GIAO DIỆN NÚT BẤM KHU RỪNG
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
# CÁC LỆNH CHÍNH CỦA BOT VÀ CÁC MINI-GAMES MỚI
# =====================================================================

@bot.command()
async def help(ctx):
    bang_help = discord.Embed(title="📚 BẢNG LỆNH CỦA BOT 📚", color=discord.Color.blue())
    bang_help.add_field(name="✨ `k rank` / `k top` / `k daily`", value="Xem hồ sơ, bảng xếp hạng và nhận lương.", inline=False)
    bang_help.add_field(name="💸 `k give @user <số tiền>`", value="Chuyển tiền cho người khác.", inline=False)
    bang_help.add_field(name="🎮 CÁC TRÒ CHƠI CÁ CƯỢC:", value="━━━━━━━━━━━━━━", inline=False)
    bang_help.add_field(name="🪙 `k coin <số tiền/all>`", value="Tung đồng xu sấp ngửa (Tỉ lệ 50/50, x2 tiền).", inline=False)
    bang_help.add_field(name="🎲 `k taixiu <tài/xỉu> <số tiền>`", value="Lắc 3 xí ngầu. Trúng Bão ăn x5!", inline=False)
    bang_help.add_field(name="🏇 `k duathu <heo/cho/ngua/chuot> <số tiền>`", value="Đặt cược xem thú nào về đích trước. Ăn x3 tiền!", inline=False)
    bang_help.add_field(name="🪨 `k ott <bua/bao/keo> <số tiền>`", value="Oẳn tù tì với bot. Thắng ăn x2, hòa trả lại tiền.", inline=False)
    bang_help.add_field(name="🌲 `k sansoi` (hoặc `k thamhiem`)", value="Khám phá rừng rậm nhân phẩm.", inline=False)
    bang_help.add_field(name="⛺ `k phai`", value="Phái đi thám hiểm (Treo máy AFK kiếm tiền).", inline=False)
    bang_help.add_field(name="🌀 `k nhansinh` (hoặc `k mophong`)", value="Game Tương Tác RPG siêu hardcore, coi chừng ĐỘT TỬ!", inline=False)
    bang_help.add_field(name="⚙️ QUẢN TRỊ VIÊN:", value="`k setup #kênh`, `k setkenh #kênh`, `k themtien`, `k trutien`", inline=False)
    await ctx.send(embed=bang_help)

# --- KIỂM TRA ĐIỀU KIỆN TRƯỚC KHI CÁ CƯỢC ---
async def check_gamble_conditions(ctx, amount_str):
    user_id = str(ctx.author.id)
    now = datetime.now()

    if user_id in gamble_cooldowns and (now - gamble_cooldowns[user_id]).total_seconds() < 4:
        await ctx.send(f"⏳ Cờ bạc từ từ thôi! Đợi {int(4 - (now - gamble_cooldowns[user_id]).total_seconds())}s nữa nhé!")
        return None, None

    user_data = load_user(user_id)
    if user_data.get("money", 0) <= 0:
        if user_data.get("money", 0) < 0:
            await ctx.send("Tài khoản đang **nợ nần chồng chất** mà dám vào casino à? Đi cày `k daily` hoặc `k phai` trả nợ ngay!")
        else:
            await ctx.send("Túi rỗng tếch mà đòi cá cược! Chạy `k daily` đi.")
        return None, None

    tien_hien_tai = user_data["money"]
    try: 
        bet = tien_hien_tai if amount_str.lower() == "all" else int(amount_str)
    except: 
        await ctx.send("Số cược không hợp lệ!")
        return None, None

    if bet <= 0 or bet > tien_hien_tai:
        await ctx.send(f"Cược sai! Bạn đang có: **{tien_hien_tai} 💰**.")
        return None, None
        
    return user_data, bet

# ----------------- GAME 1: TÀI XỈU -----------------
@bot.command()
async def taixiu(ctx, choice: str, amount: str):
    choice = choice.lower()
    if choice not in ["tai", "tài", "xiu", "xỉu"]:
        return await ctx.send("⚠️ Bạn phải chọn `tài` hoặc `xỉu`. VD: `k taixiu tai 100`")
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    msg = await ctx.send(f"🎲 {ctx.author.mention} cược **{bet} 💰** vào cửa **{choice.upper()}**.\nĐang lắc xí ngầu... 🫨")
    await asyncio.sleep(1)
    await msg.edit(content=f"🎲 {ctx.author.mention} cược **{bet} 💰** vào cửa **{choice.upper()}**.\nĐang lắc xí ngầu... 🫨\nLạch cạch lạch cạch...")
    await asyncio.sleep(1.5)

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    is_bao = (d1 == d2 == d3)
    
    if total <= 10: res_str = "xỉu"
    else: res_str = "tài"
    
    user_data = load_user(user_id)
    
    if choice.replace("à", "a").replace("ỉ", "i") == res_str.replace("à", "a").replace("ỉ", "i"):
        if is_bao:
            win_amount = bet * 5
            user_data["money"] += win_amount
            result_msg = f"🔥 **BÃO {d1}-{d2}-{d3} TỚI RỒI!!! ĐẠI THẮNG x5!**\n🎉 Húp trọn **{win_amount} 💰**!"
        else:
            win_amount = bet * 2
            user_data["money"] += win_amount
            result_msg = f"✅ **THẮNG RỒI!**\n🎉 Húp trọn **{win_amount} 💰**!"
    else:
        result_msg = f"💀 **THUA CẮNG RĂNG!** Bạn mất **{bet} 💰**."

    save_user(user_id)
    final_text = f"🎲 KẾT QUẢ: **{d1} - {d2} - {d3}** (Tổng: {total} - **{res_str.upper()}**)\n" + result_msg + f"\n💳 Số dư: **{user_data['money']} 💰**"
    await msg.edit(content=final_text)

# ----------------- GAME 2: ĐUA THÚ -----------------
@bot.command()
async def duathu(ctx, choice: str, amount: str):
    animals = {"heo": "🐖", "cho": "🐕", "chó": "🐕", "ngua": "🐎", "ngựa": "🐎", "chuot": "🐀", "chuột": "🐀"}
    choice = choice.lower()
    
    if choice not in animals:
        return await ctx.send("⚠️ Chọn sai con vật! Có 4 con: `heo`, `cho`, `ngua`, `chuot`.")
        
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

    track_length = 20
    positions = {"🐖": 0, "🐕": 0, "🐎": 0, "🐀": 0}
    
    def get_track():
        txt = f"🏇 **ĐUA THÚ MỞ BÁT!** ({ctx.author.name} cược {bet} 💰 vào {animals[choice]})\n"
        txt += "🏁" + "="*track_length + "⛩️\n"
        for pet, pos in positions.items():
            dash_count = min(pos, track_length)
            space_count = track_length - dash_count
            txt += f"🏁{'~'*dash_count}{pet}{' '*space_count}⛩️\n"
        return txt

    msg = await ctx.send(get_track())
    winner = None
    for _ in range(4):
        await asyncio.sleep(1.2)
        for pet in positions:
            positions[pet] += random.randint(2, 6) 
            if positions[pet] >= track_length and winner is None:
                winner = pet
        
        await msg.edit(content=get_track())
        if winner: break
        
    if not winner:
        winner = max(positions, key=positions.get)
        positions[winner] = track_length
        await msg.edit(content=get_track())
        
    user_data = load_user(user_id)
    if animals[choice] == winner:
        win_amount = bet * 3
        user_data["money"] += win_amount
        res_txt = f"\n🏆 **{winner} ĐÃ VỀ NHẤT!** Quá đỉnh, ăn được **x3 tiền ({win_amount} 💰)**!"
    else:
        res_txt = f"\n💀 **{winner} VỀ NHẤT!** Con {animals[choice]} của bạn xịt rồi. Mất sạch **{bet} 💰**."
        
    save_user(user_id)
    await msg.edit(content=get_track() + res_txt + f"\n💳 Số dư: **{user_data['money']} 💰**")

# ----------------- GAME 3: OẲN TÙ TÌ -----------------
@bot.command(aliases=['ott', 'oantuti'])
async def oantuti(ctx, choice: str, amount: str):
    valid_choices = {
        "bua": "🪨", "búa": "🪨", 
        "bao": "📄", "giay": "📄", "giấy": "📄",
        "keo": "✂️", "kéo": "✂️"
    }
    choice = choice.lower()
    if choice not in valid_choices:
        return await ctx.send("⚠️ Phải ra `bua`, `bao` hoặc `keo`!")

    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()
    
    bot_options = ["🪨", "📄", "✂️"]
    bot_choice = random.choice(bot_options)
    user_choice = valid_choices[choice]
    
    msg = await ctx.send(f"🤔 Bạn ra {user_choice}. Bot đang suy nghĩ...")
    await asyncio.sleep(1)
    await msg.edit(content=f"🤔 Bạn ra {user_choice}. Bot đang suy nghĩ...\n💥 Oẳn... tù... tì... RA CÁI GÌ RA CÁI NÀY!!")
    await asyncio.sleep(1)

    user_data = load_user(user_id)
    
    if user_choice == bot_choice:
        user_data["money"] += bet
        res = "🤝 **HÒA NHAU!** Trả lại tiền cược."
    elif (user_choice == "🪨" and bot_choice == "✂️") or \
         (user_choice == "📄" and bot_choice == "🪨") or \
         (user_choice == "✂️" and bot_choice == "📄"):
        win_amount = bet * 2
        user_data["money"] += win_amount
        res = f"🎉 **BẠN THẮNG RỒI!** Húp trọn **{win_amount} 💰**."
    else:
        res = f"💀 **BOT THẮNG!** Mất **{bet} 💰**."

    save_user(user_id)
    await msg.edit(content=f"💥 Bot ra: **{bot_choice}** | Bạn ra: **{user_choice}**\n{res}\n💳 Số dư: **{user_data['money']} 💰**")

# ----------------- TUNG ĐỒNG XU -----------------
@bot.command()
async def coin(ctx, amount: str):
    user_data, bet = await check_gamble_conditions(ctx, amount)
    if not user_data: return

    user_id = str(ctx.author.id)
    user_data["money"] -= bet
    save_user(user_id)
    gamble_cooldowns[user_id] = datetime.now()

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

# =====================================================================
# LỆNH ADMIN VÀ CÁC LỆNH KHÁC
# =====================================================================

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
@commands.has_permissions(administrator=True) 
async def themtien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền phải lớn hơn 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] += amount
    save_user(user_id)
    await ctx.send(f"👑 **QUYỀN TỐI THƯỢNG:** Admin {ctx.author.mention} buff cho {member.mention} **{amount} 💰**!\n💳 (Dư: **{user_data['money']} 💰**)")

@bot.command()
@commands.has_permissions(administrator=True) 
async def trutien(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Số tiền trừ đi phải lớn hơn 0.")
    user_id = str(member.id)
    user_data = load_user(user_id)
    user_data["money"] -= amount
    save_user(user_id)
    await ctx.send(f"⚖️ **THIÊN PHẠT:** Admin tước đoạt **{amount} 💰** từ {member.mention}!\n💳 (Dư: **{user_data['money']} 💰**)")

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
    if server_id not in CONFIG_CACHE: CONFIG_CACHE[server_id] = {}
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

@bot.command(aliases=['mophong'])
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
        await ctx.send(f"Phí mua vé luân hồi là **{phi} 💰**. Nghèo quá thì đi cày rank kiếm tiền đi đã!")
        return

    user_data["money"] -= phi
    nhansinh_cooldowns[user_id] = now
    dang_choi_nhansinh.append(user_id)
    save_user(user_id)

    stats = {
        "may_man": random.randint(1, 10)
    }

    view = NhanSinhGameView(ctx.author, stats)
    embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {ctx.author.mention}", color=discord.Color.purple())
    embed.add_field(name="🍀 Chỉ số tâm linh", value=f"May mắn ban đầu: **{stats['may_man']}/10** *(+ {stats['may_man']*2}% Tỉ lệ)*", inline=False)
    
    story = "\n\n".join(view.logs)
    embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)
    embed.add_field(name="❓ Ngã rẽ tuổi học trò (15 tuổi)", value=view.ev['q'], inline=False)

    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['sansoi']) 
async def thamhiem(ctx):
    shop_embed = discord.Embed(
        title="🛒 TRẠM TIẾP TẾ THÁM HIỂM 🛒",
        description="Chào mừng đến với hội Thám Hiểm! Chọn vũ khí để bắt đầu. Chơi đồ xịn dễ nổ hũ to, nhưng lỡ xịt thì đền ốm.\n\n👇 **HÃY CLICK VÀO THANH MENU BÊN DƯỚI ĐỂ CHỌN MUA** 👇",
        color=discord.Color.dark_red()
    )
    view = ShopView(ctx.author, session_profit=0)
    await ctx.send(embed=shop_embed, view=view)

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
async def on_ready(): print(f'{bot.user} đã lên mạng và sẵn sàng càn quét server!')

keep_alive() 

# === HAI NỬA MÃ TOKEN ===
nua_dau = 'MTUxODUwMzkzNDIyNDg5NjAwMA.GyKHSc.'
nua_sau = 'WCjwsbS87_itRFAJxPTpDOCbFcmmjhQdcDSDU0'

bot.run(nua_dau + nua_sau)
