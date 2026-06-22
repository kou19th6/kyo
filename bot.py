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
nhansinh_cooldowns = {} 

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
        {"tien": -400, "msg": "🐉 **RỒNG PHUN LỬA!**\nBạn đánh thức một con rồng cổ đại. Bị nó khè lửa cháy trụi quần áo, rớt sạch tiền bạc khi bỏ chạy!"},
        {"tien": -300, "msg": "🥷 **BĂNG CƯỚP HẮC ÁM!**\nGặp ngay băng thổ phỉ khét tiếng. Chúng trói bạn vào gốc cây và lột sạch sành sanh không chừa 1 đồng."},
        {"tien": -350, "msg": "💥 **ĐẠP TRÚNG MÌN GOBLIN!**\nBÙM! Bạn đạp trúng mìn tự chế của bọn Goblin. Tiền túi bay mất để trả phí cấp cứu bệnh viện."},
        {"tien": -250, "msg": "📉 **LỪA ĐẢO ĐA CẤP!**\nBạn bị một tay thương nhân lừa mua 'Bình thuốc trường sinh' giả. Nhận ra thì hắn đã tẩu thoát, tiền mất tật mang."},
        {"tien": -500, "msg": "🦇 **MA CÀ RỒNG!**\nBị một con ma cà rồng cắn. Trốn thoát được nhưng phải tốn một đống tiền mua máu nhân tạo để hồi sức."}
    ],
    "bad": [ 
        {"tien": -75, "msg": "🐒 **KHỈ ĂN TRỘM!**\nMột con khỉ nhảy ra giật lấy túi tiền của bạn rồi đu cây biến mất."},
        {"tien": -100, "msg": "🪤 **BẪY GẤU!**\nCẠCH! Bạn đạp trúng bẫy gấu. Mất một khoản tiền đi mua bông băng thuốc đỏ."},
        {"tien": -50, "msg": "🦟 **MUỖI KHỔNG LỒ!**\nBị bầy muỗi rừng khổng lồ chích sưng vù, phải đi mua thuốc mỡ bôi."},
        {"tien": -125, "msg": "🧪 **THUỐC QUÁ HẠN!**\nMua nhầm bình nước tăng lực hết hạn từ máy bán hàng tự động trong rừng. Vừa mất tiền vừa đau bụng."}
    ],
    "neutral": [ 
        {"tien": 0, "msg": "🍂 **LÁ KHÔ...**\nBạn vạch ra và... chẳng có gì cả, chỉ là một đống lá khô xào xạc."},
        {"tien": 0, "msg": "🐇 **THỎ CON...**\nMột chú thỏ trắng nhìn bạn chằm chằm vài giây rồi quay đít chạy mất."},
        {"tien": 0, "msg": "📦 **RƯƠNG RỖNG!**\nHáo hức mở một cái rương cũ, nhưng bên trong chả có gì ngoài mạng nhện."}
    ],
    "good": [ 
        {"tien": 75, "msg": "💰 **TIỀN LẺ RỚT!**\nBạn nhặt được một chiếc ví nhỏ ai đó đánh rơi, bên trong có vài đồng xu."},
        {"tien": 100, "msg": "🐟 **CÁ HIẾM!**\nBắt được một con cá có vảy lấp lánh dưới suối. Đem ra chợ bán được giá kha khá!"},
        {"tien": 125, "msg": "🍄 **NẤM LINH CHI!**\nHái được một cây nấm linh chi đỏ rực. Tiệm thuốc Bắc trả cho bạn một khoản khá hời."},
        {"tien": 150, "msg": "🙏 **NGƯỜI TỐT VIỆC TỐT!**\nNhặt được ví của một hiệp sĩ, bạn trả lại và được anh ta hậu tạ một khoản tiền."}
    ],
    "great": [ 
        {"tien": 500, "msg": "⚔️ **TIÊU DIỆT THỔ PHỈ!**\nBằng sức mạnh áp đảo, bạn tóm gọn toán cướp nhỏ và tịch thu kho báu của chúng!"},
        {"tien": 600, "msg": "💎 **NGỌC THÔ!**\nCầm cuốc gõ bừa vào đá, ai ngờ đào trúng viên ngọc lục bảo thô to bằng nắm tay!"},
        {"tien": 750, "msg": "🏆 **RƯƠNG HOÀNG KIM!**\nBạn phát hiện ra một rương kho báu vàng chóe bị chôn vùi nửa mét dưới đất. Mở ra toàn tiền!"},
        {"tien": 1000, "msg": "💍 **KIM CƯƠNG RỚT!**\nÁnh sáng lấp lánh đập vào mắt! Hóa ra là một viên kim cương tinh khiết ai đó đánh rơi trên thảm cỏ."}
    ],
    "jackpot": [ 
        {"tien": 2500, "msg": "🎫 **VÉ SỐ ĐỘC ĐẮC! (JACKPOT)**\nTrời ơi tin được không!? Bạn nhặt được tấm vé số của ai đó đánh rơi, đem dò thì trúng giải đặc biệt! Thần tài độ rồi!!!"},
        {"tien": 5000, "msg": "🏴‍☠️ **KHO BÁU VUA HẢI TẶC! (MEGAPOT)**\nCHẤN ĐỘNG!!! Sau lớp sương mù, bạn tìm thấy hang động cất giấu kho báu huyền thoại ngàn năm. Một núi Vàng hiện ra trước mắt! Bạn đổi đời rồi!!!"}
    ]
}


# =====================================================================
# DATA NGÂN HÀNG CÂU HỎI NHÂN SINH (45 SỰ KIỆN)
# =====================================================================
# tt: Trí tuệ, ns: Nhan sắc, mm: May mắn, t: Tiền
EVENTS_P1 = [
    {"q": "Bạn nhặt được chiếc ví dày cộp của thầy Hiệu trưởng.", "a": "Nộp lên phòng giám thị", "b": "Lấy tiền đi bao bạn bè", "ra": "Thầy khen ngợi trước cờ, tăng uy tín.", "rb": "Tiêu xài sướng tay nhưng bị camera quay lại, hạ kiểm kiểm.", "ea": {"tt": 1, "ns": 0, "mm": 2, "t": 200}, "eb": {"tt": -2, "ns": 0, "mm": -3, "t": 1000}},
    {"q": "Crush tỏ tình với bạn ngay sát kỳ thi quan trọng.", "a": "Từ chối để ôn thi", "b": "Đồng ý hẹn hò luôn", "ra": "Đau lòng nhưng đỗ điểm cao.", "rb": "Tình yêu thăng hoa, học hành đội sổ.", "ea": {"tt": 3, "ns": -1, "mm": 0, "t": 0}, "eb": {"tt": -3, "ns": 2, "mm": 1, "t": -200}},
    {"q": "Bị nhóm đầu gấu trấn lột tiền ăn sáng.", "a": "Gồng lên đấm lại", "b": "Ngoan ngoãn đưa tiền", "ra": "Bị đấm sưng mắt nhưng chúng nể phục.", "rb": "Mất tiền nhưng nhan sắc được bảo toàn.", "ea": {"tt": 0, "ns": -2, "mm": 2, "t": -100}, "eb": {"tt": 1, "ns": 0, "mm": 0, "t": -300}},
    {"q": "Trường tổ chức thi Nam thanh Nữ tú.", "a": "Tham gia thi", "b": "Ngồi dưới làm khán giả", "ra": "Lọt top hoa khôi/nam vương, được nhiều người biết đến.", "rb": "Nhạt nhòa giữa đám đông nhưng đỡ tốn thời gian.", "ea": {"tt": -1, "ns": 3, "mm": 1, "t": -200}, "eb": {"tt": 1, "ns": 0, "mm": 0, "t": 100}},
    {"q": "Bạn tìm thấy một con mèo hoang sắp chết đói.", "a": "Nhặt về nuôi", "b": "Lờ đi vì sợ tốn tiền", "ra": "Tốn tiền mua hạt nhưng mèo mang lại may mắn.", "rb": "Giữ được tiền nhưng lòng áy náy.", "ea": {"tt": 0, "ns": 1, "mm": 2, "t": -300}, "eb": {"tt": 0, "ns": -1, "mm": -1, "t": 100}},
    {"q": "Bạn bè rủ cúp học đi nét chơi game mới ra.", "a": "Đi chơi luôn", "b": "Ở lại lớp làm bài tập", "ra": "Vui vẻ nhưng hổng kiến thức nghiêm trọng.", "rb": "Thầy giáo điểm danh đột xuất, bạn an toàn.", "ea": {"tt": -2, "ns": 0, "mm": 0, "t": -150}, "eb": {"tt": 2, "ns": 0, "mm": 1, "t": 0}},
    {"q": "Kiểm tra 15 phút mà bạn chưa học bài.", "a": "Mở tài liệu quay cóp", "b": "Làm bằng thực lực", "ra": "Được 10 điểm nhưng thấp thỏm lo sợ.", "rb": "Được 3 điểm nhưng lòng thanh thản.", "ea": {"tt": -1, "ns": 0, "mm": 2, "t": 0}, "eb": {"tt": 1, "ns": 0, "mm": 0, "t": 0}},
    {"q": "Quảng cáo mua điện thoại xịn giá rẻ bèo trên mạng.", "a": "Chốt đơn mua ngay", "b": "Biết là lừa đảo, bỏ qua", "ra": "Nhận được cục gạch, mất trắng tiền tiết kiệm.", "rb": "Bảo toàn số tiền, tăng thêm kinh nghiệm sống.", "ea": {"tt": -2, "ns": 0, "mm": -2, "t": -800}, "eb": {"tt": 2, "ns": 0, "mm": 0, "t": 0}},
    {"q": "Thấy người già ăn xin ngoài cổng trường.", "a": "Cho hết tiền ăn sáng", "b": "Đi thẳng vào lớp", "ra": "Bụng đói meo nhưng tích được phước đức.", "rb": "Bụng no nê nhưng bỏ lỡ cơ hội làm việc tốt.", "ea": {"tt": 0, "ns": 0, "mm": 3, "t": -200}, "eb": {"tt": 0, "ns": 0, "mm": -1, "t": 0}},
    {"q": "Giải đấu thể thao cấp trường đang thiếu người.", "a": "Đăng ký thi đấu", "b": "Từ chối vì sợ mệt", "ra": "Mang vinh quang về cho lớp, nhan sắc tỏa sáng.", "rb": "Ngồi chơi xơi nước, người tích mỡ.", "ea": {"tt": -1, "ns": 2, "mm": 1, "t": 0}, "eb": {"tt": 0, "ns": -1, "mm": 0, "t": 0}},
    {"q": "Phát hiện bạn thân nói dối giáo viên.", "a": "Bao che cho bạn", "b": "Nói ra sự thật", "ra": "Tình bạn thêm gắn kết, nhưng bạn trở thành kẻ dối trá.", "rb": "Giáo viên tin tưởng, nhưng bạn thân cạch mặt.", "ea": {"tt": -1, "ns": 0, "mm": 1, "t": 0}, "eb": {"tt": 2, "ns": 0, "mm": -1, "t": 0}},
    {"q": "Nhặt được tờ vé số cũ trong ngăn bàn.", "a": "Đem đi dò thử", "b": "Vứt sọt rác", "ra": "Trúng giải khuyến khích, có tiền ăn vặt!", "rb": "Bỏ lỡ vận may từ trên trời rơi xuống.", "ea": {"tt": 0, "ns": 0, "mm": 2, "t": 500}, "eb": {"tt": 0, "ns": 0, "mm": -1, "t": 0}},
    {"q": "Học lỏm một ngoại ngữ mới.", "a": "Cày cuốc học đêm", "b": "Lười quá đi ngủ", "ra": "Tăng mạnh trí tuệ nhưng mặt mọc mụn vì thức khuya.", "rb": "Ngủ đủ giấc, da dẻ hồng hào nhưng não phẳng.", "ea": {"tt": 3, "ns": -1, "mm": 0, "t": 0}, "eb": {"tt": -1, "ns": 2, "mm": 0, "t": 0}},
    {"q": "Mua sách luyện thi hay nạp tiền chơi game?", "a": "Mua sách", "b": "Nạp game", "ra": "Trở thành mọt sách, kiến thức uyên thâm.", "rb": "Lên rank vù vù nhưng kiến thức trống rỗng.", "ea": {"tt": 2, "ns": -1, "mm": 0, "t": -300}, "eb": {"tt": -2, "ns": 0, "mm": 0, "t": -300}},
    {"q": "Tranh cử chức Bí thư lớp.", "a": "Đứng lên tranh cử", "b": "Để người khác làm", "ra": "Trở thành người lãnh đạo, tăng uy tín.", "rb": "An phận làm học sinh bình thường.", "ea": {"tt": 1, "ns": 1, "mm": 1, "t": 0}, "eb": {"tt": 0, "ns": 0, "mm": 0, "t": 0}}
]

EVENTS_P2 = [
    {"q": "Một người bạn rủ góp vốn mở quán trà chanh.", "a": "Đầu tư ngay", "b": "Từ chối, tiền để ngân hàng", "ra": "Quán đông khách, bạn kiếm được một khoản kha khá.", "rb": "An toàn nhưng không sinh lời nhiều.", "ea": {"tt": 1, "ns": 0, "mm": 1, "t": 1500}, "eb": {"tt": 0, "ns": 0, "mm": 0, "t": 200}},
    {"q": "Sếp cướp công dự án bạn làm đêm ngày.", "a": "Đăng bài bóc phốt sếp", "b": "Nhẫn nhịn chờ thời", "ra": "Bị đuổi việc ngay lập tức, dính nợ thẻ tín dụng.", "rb": "Được thăng chức bù đắp sau này.", "ea": {"tt": -2, "ns": 0, "mm": -2, "t": -2000}, "eb": {"tt": 2, "ns": 0, "mm": 1, "t": 2500}},
    {"q": "Có một đại gia già xấu muốn bao nuôi bạn.", "a": "Gật đầu đồng ý", "b": "Từ chối kiên quyết", "ra": "Có tiền sắm đồ hiệu nhưng danh dự tụt dốc.", "rb": "Nghèo nhưng giữ được cốt cách.", "ea": {"tt": -2, "ns": -2, "mm": 0, "t": 5000}, "eb": {"tt": 1, "ns": 1, "mm": 0, "t": -500}},
    {"q": "Bắt trend tiền ảo đang lên ngôi.", "a": "All-in tiền tiết kiệm", "b": "Đứng ngoài xem", "ra": "Thị trường sập! Bạn chia 10 tài sản, khóc thét.", "rb": "Bạn né được cú sập thế kỷ, bảo toàn vốn.", "ea": {"tt": -3, "ns": 0, "mm": -2, "t": -4000}, "eb": {"tt": 2, "ns": 0, "mm": 1, "t": 0}},
    {"q": "Bạn được mời làm KOL review đồ ăn.", "a": "Nhận lời làm", "b": "Sợ mập, không làm", "ra": "Nổi tiếng mạng xã hội, kiếm nhiều tiền nhưng tăng 10 cân.", "rb": "Giữ được body chuẩn nhưng ví mỏng.", "ea": {"tt": 0, "ns": -2, "mm": 1, "t": 3000}, "eb": {"tt": 0, "ns": 2, "mm": 0, "t": 0}},
    {"q": "Khám phá ra một lỗ hổng phần mềm của công ty.", "a": "Báo cáo nội bộ", "b": "Bán dữ liệu cho hacker", "ra": "Được thưởng nóng vì tính trung thực.", "rb": "Kiếm bộn tiền nhưng bị công an sờ gáy, nộp phạt sấp mặt.", "ea": {"tt": 2, "ns": 0, "mm": 1, "t": 1000}, "eb": {"tt": -3, "ns": 0, "mm": -3, "t": -5000}},
    {"q": "Vay nợ mua xe SH để loè thiên hạ.", "a": "Quất luôn", "b": "Đi xe số cho lành", "ra": "Có le với gái/trai, nhưng cày cuốc trả lãi mệt mỏi.", "rb": "Không ai để ý nhưng tài chính vững vàng.", "ea": {"tt": -2, "ns": 2, "mm": 0, "t": -3000}, "eb": {"tt": 1, "ns": -1, "mm": 1, "t": 1000}},
    {"q": "Khách hàng ngỏ ý đút lót để lách luật.", "a": "Nhận phong bì", "b": "Cự tuyệt thẳng thừng", "ra": "Bị thanh tra phát hiện, mất việc và đền tiền.", "rb": "Giữ sạch hồ sơ, được cấp trên cất nhắc.", "ea": {"tt": -2, "ns": 0, "mm": -2, "t": -2500}, "eb": {"tt": 2, "ns": 0, "mm": 1, "t": 1500}},
    {"q": "Một công ty nước ngoài mời bạn sang làm việc.", "a": "Xuất ngoại", "b": "Ở lại quê hương", "ra": "Lương đô-la nhưng cô đơn nơi xứ người.", "rb": "Thu nhập bình thường nhưng có gia đình kề bên.", "ea": {"tt": 2, "ns": 0, "mm": 0, "t": 4000}, "eb": {"tt": 0, "ns": 0, "mm": 1, "t": 1000}},
    {"q": "Tham gia khóa học kỹ năng mềm 50 củ.", "a": "Đăng ký học", "b": "Tự học trên mạng", "ra": "Mở rộng mối quan hệ VIP, kỹ năng thăng hạng.", "rb": "Tiết kiệm tiền nhưng tiến bộ chậm.", "ea": {"tt": 3, "ns": 0, "mm": 1, "t": -1000}, "eb": {"tt": 1, "ns": 0, "mm": 0, "t": 0}},
    {"q": "Người yêu cũ rủ quay lại.", "a": "Gương vỡ lại lành", "b": "Say No!", "ra": "Tiếp tục cãi vã, stress tột độ ảnh hưởng công việc.", "rb": "Đầu óc thư thái, tập trung kiếm tiền.", "ea": {"tt": -1, "ns": -1, "mm": -1, "t": -500}, "eb": {"tt": 1, "ns": 1, "mm": 1, "t": 1000}},
    {"q": "Thuê chung cư cao cấp hay phòng trọ giá rẻ?", "a": "Chung cư cao cấp", "b": "Phòng trọ sinh viên", "ra": "Sống sướng, sang chảnh nhưng lương tháng nào hết tháng đó.", "rb": "Sống cực khổ nhưng dư dả tiền tiết kiệm.", "ea": {"tt": 0, "ns": 1, "mm": 0, "t": -2000}, "eb": {"tt": 0, "ns": -1, "mm": 0, "t": 2000}},
    {"q": "Có người gạ bán bảo hiểm nhân thọ cho bạn.", "a": "Mua 1 gói", "b": "Từ chối", "ra": "Tháng sau vô tình gãy chân, được đền bù y tế khủng.", "rb": "Bị tai nạn tốn tiền túi tự lo.", "ea": {"tt": 1, "ns": 0, "mm": 3, "t": 2500}, "eb": {"tt": 0, "ns": 0, "mm": -2, "t": -1500}},
    {"q": "Đồng nghiệp nhờ bảo lãnh vay nợ tín chấp.", "a": "Ký giấy giúp", "b": "Nói không", "ra": "Đồng nghiệp bỏ trốn, bạn è cổ trả nợ thay!", "rb": "Mất lòng bạn nhưng an toàn ví tiền.", "ea": {"tt": -3, "ns": 0, "mm": -2, "t": -4000}, "eb": {"tt": 2, "ns": 0, "mm": 0, "t": 0}},
    {"q": "Tham gia gameshow hẹn hò trên tivi.", "a": "Đi thi", "b": "Ngại xuất hiện", "ra": "Trở thành tâm điểm mạng xã hội, kiếm bộn tiền quảng cáo.", "rb": "Cuộc sống trôi qua vô vị.", "ea": {"tt": 0, "ns": 2, "mm": 2, "t": 3500}, "eb": {"tt": 0, "ns": 0, "mm": 0, "t": 0}}
]

EVENTS_P3 = [
    {"q": "Cò đất cò mồi bạn mua mảnh đất ở ngoại ô.", "a": "Chốt cọc mua", "b": "Chê xa không mua", "ra": "Đất dính quy hoạch! Tiền đầu tư biến thành rác.", "rb": "May mắn né được cú lừa thế kỷ.", "ea": {"tt": -2, "ns": 0, "mm": -3, "t": -5000}, "eb": {"tt": 2, "ns": 0, "mm": 1, "t": 1000}},
    {"q": "Cảm thấy cơ thể hay đau nhức.", "a": "Bỏ tiền mua thuốc xịn", "b": "Bỏ qua, cày tiếp", "ra": "Cơ thể khỏe mạnh, trẻ lại chục tuổi.", "rb": "Đột quỵ phải đi cấp cứu, tốn một núi tiền.", "ea": {"tt": 1, "ns": 2, "mm": 0, "t": -1000}, "eb": {"tt": -2, "ns": -3, "mm": -2, "t": -4000}},
    {"q": "Mở rộng kinh doanh ra nước ngoài.", "a": "Vay vốn mở rộng", "b": "Giữ quy mô hiện tại", "ra": "Kinh doanh bùng nổ! Lợi nhuận tăng phi mã.", "rb": "Công ty giậm chân tại chỗ, dần thụt lùi.", "ea": {"tt": 2, "ns": 0, "mm": 2, "t": 6000}, "eb": {"tt": 0, "ns": 0, "mm": -1, "t": -500}},
    {"q": "Con cái muốn đi du học trường đắt đỏ.", "a": "Rút tiết kiệm cho con đi", "b": "Bắt học trường công", "ra": "Con thành tài, sau này gửi tiền báo hiếu.", "rb": "Con bất mãn, quậy phá báo nhà.", "ea": {"tt": 2, "ns": 0, "mm": 1, "t": 4000}, "eb": {"tt": -1, "ns": 0, "mm": -2, "t": -2000}},
    {"q": "Bị giang hồ tông xe trên đường.", "a": "Bắt đền", "b": "Xin lỗi cho qua chuyện", "ra": "Bị chúng đập cho một trận nhừ tử, mất viện phí.", "rb": "Tốn tiền sửa xe nhưng toàn mạng.", "ea": {"tt": -1, "ns": -2, "mm": -2, "t": -3000}, "eb": {"tt": 1, "ns": 0, "mm": 0, "t": -500}},
    {"q": "Được mời làm cố vấn cho một công ty mới nổi.", "a": "Nhận lời", "b": "Từ chối", "ra": "Nhận cổ phần thưởng, công ty lên sàn bạn giàu to.", "rb": "Bỏ lỡ cơ hội đổi đời.", "ea": {"tt": 2, "ns": 0, "mm": 2, "t": 5000}, "eb": {"tt": 0, "ns": 0, "mm": 0, "t": 0}},
    {"q": "Đánh rơi nhẫn kim cương xuống cống.", "a": "Thuê người móc cống", "b": "Bỏ luôn", "ra": "Tìm lại được nhẫn, nhưng người dính đầy bùn đất.", "rb": "Mất trắng tài sản quý giá.", "ea": {"tt": 0, "ns": -2, "mm": 1, "t": 1000}, "eb": {"tt": 0, "ns": 0, "mm": -2, "t": -3000}},
    {"q": "Phát hiện vợ/chồng quỹ đen.", "a": "Tịch thu hết", "b": "Nhắm mắt làm ngơ", "ra": "Ví dày cộp nhưng gia đình lục đục.", "rb": "Gia đình êm ấm, tinh thần thoải mái.", "ea": {"tt": 0, "ns": 0, "mm": -1, "t": 2000}, "eb": {"tt": 1, "ns": 1, "mm": 0, "t": 0}},
    {"q": "Bác sĩ khuyên nên phẫu thuật thẩm mỹ để đổi vận.", "a": "Đập đi xây lại", "b": "Giữ nét tự nhiên", "ra": "Phẫu thuật lỗi! Biến chứng sưng vù, tốn tiền đền bù.", "rb": "Nhan sắc tàn phai theo năm tháng nhưng tiết kiệm.", "ea": {"tt": -2, "ns": -3, "mm": -2, "t": -4000}, "eb": {"tt": 1, "ns": -1, "mm": 0, "t": 1000}},
    {"q": "Tham gia đấu giá một bức tranh cổ.", "a": "Giơ bảng mua", "b": "Ngồi im", "ra": "Trúng mánh! Bức tranh là đồ thật, giá trị tăng gấp 3.", "rb": "Giữ tiền trong thẻ, không mất gì.", "ea": {"tt": 2, "ns": 0, "mm": 2, "t": 7000}, "eb": {"tt": 0, "ns": 0, "mm": 0, "t": 0}},
    {"q": "Bạn được mời đi đánh golf với đối tác lớn.", "a": "Đi ngay", "b": "Ở nhà ngủ", "ra": "Ký được hợp đồng triệu đô, mở ra chân trời mới.", "rb": "Đối tác chọn công ty khác, bạn mất hợp đồng.", "ea": {"tt": 1, "ns": 1, "mm": 2, "t": 5500}, "eb": {"tt": -1, "ns": 0, "mm": -1, "t": -1000}},
    {"q": "Một quỹ từ thiện mạo danh nhờ bạn quyên góp.", "a": "Chuyển khoản ủng hộ", "b": "Điều tra kỹ", "ra": "Mất tiền oan cho bọn lừa đảo.", "rb": "Phanh phui đường dây, được lên báo tuyên dương.", "ea": {"tt": -2, "ns": 0, "mm": -1, "t": -2500}, "eb": {"tt": 2, "ns": 1, "mm": 1, "t": 1500}},
    {"q": "Nổi hứng muốn mua xe hơi thể thao.", "a": "Vay tiền quất luôn", "b": "Mua xe cũ thôi", "ra": "Mua xe trả góp gánh nợ tụt hơi, nhưng oai.", "rb": "Dư dả tiền bạc kinh doanh tiếp.", "ea": {"tt": -2, "ns": 2, "mm": 0, "t": -3500}, "eb": {"tt": 1, "ns": 0, "mm": 1, "t": 2000}},
    {"q": "Sóng thần truyền thông: Bạn bị bóc phốt oan.", "a": "Thuê luật sư kiện", "b": "Im lặng chờ chìm", "ra": "Thắng kiện, lấy lại danh dự và tiền bồi thường.", "rb": "Sự nghiệp tụt dốc, bị đối tác quay lưng.", "ea": {"tt": 2, "ns": 1, "mm": 1, "t": 4500}, "eb": {"tt": -1, "ns": -1, "mm": -2, "t": -3000}},
    {"q": "Rảnh rỗi sinh nông nổi, đi sòng bài Macao.", "a": "Mang sổ đỏ ra chơi", "b": "Đánh vui 100 đô", "ra": "Thua cháy túi, bay luôn căn biệt thự!", "rb": "Ra về vui vẻ, mua được món quà cho gia đình.", "ea": {"tt": -3, "ns": 0, "mm": -3, "t": -8000}, "eb": {"tt": 1, "ns": 0, "mm": 1, "t": 500}}
]


# =====================================================================
# GIAO DIỆN GAME NHÂN SINH TƯƠNG TÁC NGẪU NHIÊN
# =====================================================================

class NhanSinhGameView(discord.ui.View):
    def __init__(self, author, stats):
        super().__init__(timeout=180)
        self.author = author
        self.stats = stats
        self.phase = 1
        self.tien_an = 0
        self.logs = []
        
        # Random pick 3 sự kiện cho 3 giai đoạn
        self.event_p1 = random.choice(EVENTS_P1)
        self.event_p2 = random.choice(EVENTS_P2)
        self.event_p3 = random.choice(EVENTS_P3)

        if self.stats["may_man"] >= 8:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra ngậm thìa vàng, bố làm chủ tịch, sống trong nhung lụa từ bé.")
        elif self.stats["may_man"] >= 4:
            self.logs.append("👶 **Tuổi 0:** Bạn sinh ra trong một gia đình êm ấm, đủ ăn đủ mặc.")
        else:
            self.logs.append("👶 **Tuổi 0:** Bố mẹ ôm nợ bỏ trốn, bạn phải tự thân vận động từ khi còn nhỏ xíu.")

        self.btn_a = discord.ui.Button(label=f"A. {self.event_p1['a']}", style=discord.ButtonStyle.primary, custom_id="btn_a")
        self.btn_a.callback = self.choice_a
        self.btn_b = discord.ui.Button(label=f"B. {self.event_p1['b']}", style=discord.ButtonStyle.secondary, custom_id="btn_b")
        self.btn_b.callback = self.choice_b

        self.add_item(self.btn_a)
        self.add_item(self.btn_b)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Nhân quả của ai người nấy gánh, đừng bấm lung tung!", ephemeral=True)
            return False
        return True

    async def choice_a(self, interaction: discord.Interaction):
        await self.process_choice(interaction, "A")

    async def choice_b(self, interaction: discord.Interaction):
        await self.process_choice(interaction, "B")

    async def process_choice(self, interaction: discord.Interaction, choice: str):
        if self.phase == 1:
            ev = self.event_p1
            eff = ev["ea"] if choice == "A" else ev["eb"]
            res = ev["ra"] if choice == "A" else ev["rb"]
            
            self.stats["tri_tue"] += eff["tt"]
            self.stats["nhan_sac"] += eff["ns"]
            self.stats["may_man"] += eff["mm"]
            self.tien_an += eff["t"]
            
            self.logs.append(f"🎒 **Tuổi 15:** {res}")
            self.phase = 2

        elif self.phase == 2:
            ev = self.event_p2
            eff = ev["ea"] if choice == "A" else ev["eb"]
            res = ev["ra"] if choice == "A" else ev["rb"]
            
            self.stats["tri_tue"] += eff["tt"]
            self.stats["nhan_sac"] += eff["ns"]
            self.stats["may_man"] += eff["mm"]
            self.tien_an += eff["t"]
            
            self.logs.append(f"💼 **Tuổi 25:** {res}")
            self.phase = 3

        elif self.phase == 3:
            ev = self.event_p3
            eff = ev["ea"] if choice == "A" else ev["eb"]
            res = ev["ra"] if choice == "A" else ev["rb"]
            
            self.stats["tri_tue"] += eff["tt"]
            self.stats["nhan_sac"] += eff["ns"]
            self.stats["may_man"] += eff["mm"]
            self.tien_an += eff["t"]
            
            self.logs.append(f"🏦 **Tuổi 35:** {res}")
            self.phase = 4

        await self.update_ui(interaction)

    async def update_ui(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🌀 MÔ PHỎNG NHÂN SINH 🌀", description=f"Ký chủ: {self.author.mention}", color=discord.Color.purple())

        stats_text = f"Trí tuệ: **{self.stats['tri_tue']}** | Nhan sắc: **{self.stats['nhan_sac']}** | May mắn: **{self.stats['may_man']}**"
        embed.add_field(name="📊 Chỉ số linh hồn", value=stats_text, inline=False)

        story = "\n\n".join(self.logs)
        embed.add_field(name="📜 Hành trình cuộc đời", value=story, inline=False)

        if self.phase == 1:
            embed.add_field(name="❓ Ngã rẽ tuổi học trò (15 tuổi)", value=self.event_p1['q'], inline=False)
            self.btn_a.label = f"A. {self.event_p1['a']}"
            self.btn_b.label = f"B. {self.event_p1['b']}"
        elif self.phase == 2:
            embed.add_field(name="❓ Quyết định tuổi 25", value=self.event_p2['q'], inline=False)
            self.btn_a.label = f"A. {self.event_p2['a']}"
            self.btn_b.label = f"B. {self.event_p2['b']}"
        elif self.phase == 3:
            embed.add_field(name="❓ Cám dỗ tuổi 35", value=self.event_p3['q'], inline=False)
            self.btn_a.label = f"A. {self.event_p3['a']}"
            self.btn_b.label = f"B. {self.event_p3['b']}"
        elif self.phase == 4:
            self.btn_a.disabled = True
            self.btn_b.disabled = True
            self.clear_items() 

            # TÍNH TOÁN KẾT QUẢ CUỐI CÙNG 
            total_reward = self.tien_an + (self.stats['tri_tue'] + self.stats['nhan_sac'] + self.stats['may_man']) * 50
            
            data = load_data()
            user_id = str(self.author.id)
            if user_id not in data: data[user_id] = {"xp": 0, "level": 1, "money": 0}
            
            data[user_id]["money"] += total_reward
            save_data(data)

            if total_reward < 0:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Sống lay lắt qua ngày, cuối đời bệnh tật không tiền chữa.\n❌ **BÁO NHÀ!** Bạn để lại khoản nợ: **{total_reward} 💰**\n*(Hệ thống đã trừ nợ vào sổ, đi cày `k daily` mà trả nhé!)*", inline=False)
            elif total_reward >= 5000:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Hưởng thọ trong biệt thự cao cấp. Tang lễ hoành tráng.\n👑 **ĐẠI PHÚ HÀO!** Di sản kiếp sau: **+{total_reward} 💰**", inline=False)
            else:
                embed.add_field(name="🪦 Nhắm mắt xuôi tay", value=f"Cuộc đời bình dị, thanh thản ra đi bên con cháu.\n💼 **DƯ DẢ!** Di sản kiếp sau: **+{total_reward} 💰**", inline=False)

            embed.add_field(name="💳 Tài sản hiện tại", value=f"**{data[user_id]['money']} 💰**", inline=False)

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)


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
        
        data[user_id]["money"] += thuong_phat
            
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
            discord.SelectOption(label="4 Giờ (Bãi Cỏ Yên Bình)", description="Phần thưởng: ~450 💰", emoji="🌿", value="4"),
            discord.SelectOption(label="8 Giờ (Hang Động Tối Tăm)", description="Phần thưởng: ~1000 💰", emoji="🦇", value="8"),
            discord.SelectOption(label="12 Giờ (Di Tích Nguy Hiểm)", description="Phần thưởng: ~2000 💰", emoji="🏛️", value="12")
        ]
        super().__init__(placeholder="Chọn khu vực phái đi...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_data()
        user_id = str(interaction.user.id)
        
        hours = int(self.values[0])
        reward = 0
        if hours == 4: reward = random.randint(300, 600)
        elif hours == 8: reward = random.randint(700, 1200)
        elif hours == 12: reward = random.randint(1500, 2500)

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
    bang_help.add_field(name="📅 `k daily`", value="Nhận lương hằng ngày (500 💰).", inline=False)
    bang_help.add_field(name="🪙 `k coin <số tiền/all>`", value="Cờ bạc tung xu hồi hộp (Chờ 3s).", inline=False)
    bang_help.add_field(name="🌲 `k thamhiem`", value="Mở cửa hàng vũ khí & đi thám hiểm rừng rậm nhặt tiền.", inline=False)
    bang_help.add_field(name="⛺ `k phai`", value="Phái đi thám hiểm (Treo máy AFK kiếm tiền).", inline=False)
    bang_help.add_field(name="🌀 `k nhansinh`", value="Game Tương Tác Nhân Sinh (Phí vé: 100 💰).", inline=False)
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
            reward = data[user_id].get("exp_reward", 500)
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

@bot.command()
async def nhansinh(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    phi = 100
    now = datetime.now()

    if user_id in nhansinh_cooldowns and (now - nhansinh_cooldowns[user_id]).total_seconds() < 5:
        giay_con_lai = int(5 - (now - nhansinh_cooldowns[user_id]).total_seconds())
        await ctx.send(f"⏳ Linh hồn bạn vừa mới luân hồi, cần nghỉ ngơi! Đợi **{giay_con_lai} giây** nữa mới được đầu thai tiếp.")
        return

    if user_id not in data: data[user_id] = {"xp": 0, "level": 1, "money": 0}
    if data[user_id].get("money", 0) < phi:
        await ctx.send(f"Phí mua vé luân hồi đi đầu thai là **{phi} 💰**. Nợ nần hay nghèo rớt mồng tơi thì không có cửa đi đầu thai đâu!")
        return

    data[user_id]["money"] -= phi
    nhansinh_cooldowns[user_id] = now
    save_data(data)

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
    embed.add_field(name="❓ Ngã rẽ tuổi học trò (15 tuổi)", value=view.event_p1['q'], inline=False)

    await ctx.send(embed=embed, view=view)


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

    data[user_id]["money"] += 500
    data[user_id]["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    if data[user_id]["money"] < 0:
        await ctx.send(f"🎁 Bạn nhận được **500 💰** tiền công!\n⚠️ Hệ thống đã siết nợ tự động! Bạn vẫn còn đang nợ **{data[user_id]['money']} 💰**.")
    else:
        await ctx.send(f"🎁 Bạn nhận được **500 💰** tiền công! (Số dư: **{data[user_id]['money']} 💰**)")

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
        thuong = data[u_id]["level"] * 200
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
