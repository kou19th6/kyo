# =====================================================================
# 🎲 CỜ TỶ PHÚ (MONOPOLY) — MODULE RIÊNG, GHÉP VÀO bot.py
# =====================================================================
# CÁCH CÀI ĐẶT:
# 1) Đặt file này (monopoly.py) cùng thư mục với bot.py.
# 2) Cài thêm thư viện vẽ ảnh (bắt buộc cho bản này):
#        pip install Pillow aiohttp
#    (Nếu muốn đẹp hơn nữa, cài thêm font Poppins:
#        apt-get install fonts-google-noto fonts-open-sans
#     Module tự động dùng Poppins nếu máy có sẵn, nếu không sẽ dùng
#     DejaVu Sans (luôn có sẵn trên hầu hết server Linux) nên KHÔNG BẮT
#     BUỘC phải cài thêm gì, mọi thứ vẫn chạy đẹp bằng font mặc định.)
# 3) Trong bot.py, ngay sau đoạn bạn setup custom_commands (chỗ có dòng
#    `from custom_commands import setup_custom_commands` /
#    `setup_custom_commands(bot, db)`), thêm 2 dòng:
#
#        from monopoly import setup_monopoly
#        setup_monopoly(bot, db, load_user=load_user, save_user=save_user, add_history=add_history)
#
#    (load_user / save_user / add_history là các hàm ĐÃ CÓ SẴN trong bot.py
#     của bạn — truyền vào để khi thắng ván Cờ Tỷ Phú, người chơi được
#     thưởng thêm <:Money_kyo:1528673432613552188> vào ví thật. Nếu không
#     truyền, minigame vẫn chạy bình thường, chỉ là không có thưởng thật.
#     ⚠️ LƯU Ý: nếu hàm save_user(user_id, data) của bạn có tham số khác,
#     hãy sửa lại đúng 1 dòng trong hàm check_winner() bên dưới, tìm
#     chỗ có ghi "SỬA DÒNG NÀY CHO KHỚP VỚI save_user CỦA BẠN".)
#
# ĐẶC ĐIỂM (bản nâng cấp giao diện + tính năng):
# - Mỗi kênh Discord có TỐI ĐA 1 bàn cờ đang hoạt động (lưu trong Mongo,
#   collection "monopoly_games", key = channel_id).
# - Bàn cờ KHÔNG BAO GIỜ HẾT HẠN: dùng discord.ui.View(timeout=None) với
#   custom_id CỐ ĐỊNH, đăng ký 1 lần duy nhất bằng bot.add_view() lúc
#   bot khởi động (on_ready). Nút bấm hoạt động vĩnh viễn kể cả sau khi
#   bot restart.
# - 2 chế độ: `pvp` (chơi với người) và `bot` (chơi với máy).
# - Hỗ trợ tối đa 6 người/bàn.
# - 🖼️ BÀN CỜ ĐƯỢC VẼ LẠI HOÀN TOÀN (v2):
#     • Layout mỗi ô: dải màu (nhóm màu / loại ô) ở trên, tên ô được
#       tự động NGẮT DÒNG & THU NHỎ FONT vừa khít ô (không còn tràn,
#       không còn icon đè chữ), giá tiền rõ ràng ở góc dưới.
#     • Icon từng loại ô (❓ cơ hội, $ thuế, tàu, điện, nước) được vẽ
#       gọn trong dải màu, không chồng lên tên ô.
#     • Khu trung tâm hiển thị danh sách người chơi dạng THẺ BÀI đẹp,
#       có avatar, tiền, trạng thái tù/lượt hiện tại.
#     • Nhà/khách sạn hiển thị icon nhỏ gọn ở góc ô, viền màu quanh ô
#       thể hiện chủ sở hữu.
# - 🔎 TÍNH NĂNG MỚI — "Vị Trí Của Tôi": bấm nút 📍 bất cứ lúc nào để
#   xem ảnh ZOOM cận cảnh vào đúng ô bạn đang đứng, kèm thông tin chi
#   tiết (giá, tiền thuê theo số nhà, chủ sở hữu, số tiền bạn có...).
# - 📋 TÍNH NĂNG MỚI — "Tài Sản Của Tôi": xem danh sách toàn bộ đất bạn
#   đang sở hữu, số nhà đã xây, tiền thuê hiện tại mỗi ô, tổng giá trị.
# - 🏆 TÍNH NĂNG MỚI — "Bảng Xếp Hạng": so tài sản ròng (tiền mặt + giá
#   trị bất động sản) giữa tất cả người chơi trong bàn.
# - Vẫn giữ ảnh bàn cờ RIÊNG (ephemeral) gửi cho người vừa đi mỗi lượt.
# =====================================================================

import discord
from discord.ext import commands, tasks
import random
import asyncio
import io
import os
import re
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[MONO] ⚠️ Chưa cài Pillow! Chạy: pip install Pillow  (ảnh bàn cờ sẽ không hoạt động)")

try:
    import aiohttp
    AIOHTTP_OK = True
except ImportError:
    AIOHTTP_OK = False

MONO_START_MONEY   = 1_500_000
MONO_GO_SALARY     = 200_000
MONO_JAIL_FINE     = 50_000
MONO_MAX_PLAYERS   = 6
MONO_JAIL_IDX      = 10
MONO_GOTOJAIL_IDX  = 30
MONO_FREEPARK_IDX  = 20

MONEY_EMOJI = "<:Money_kyo:1528673432613552188>"

GROUP_COLORS = {
    "brown":     (136, 82, 59),
    "lightblue": (98, 189, 237),
    "pink":      (224, 74, 150),
    "orange":    (245, 141, 51),
    "red":       (224, 63, 63),
    "yellow":    (240, 189, 32),
    "green":     (42, 157, 97),
    "blue":      (42, 99, 199),
    "railroad":  (55, 61, 74),
    "utility":   (108, 123, 140),
}
GROUP_VN_NAMES = {
    "brown": "Nâu", "lightblue": "Xanh Nhạt", "pink": "Hồng", "orange": "Cam",
    "red": "Đỏ", "yellow": "Vàng", "green": "Xanh Lá", "blue": "Xanh Dương",
    "railroad": "Nhà Ga", "utility": "Tiện Ích",
}
BOARD_BG = (238, 231, 214)
CENTER_BG = (252, 249, 242)
PLAYER_COLORS = [
    (230, 66, 92), (44, 130, 201), (35, 158, 112),
    (232, 160, 32), (146, 87, 199), (26, 173, 158),
]
CORNER_STYLES = {
    0:  {"bg": (35, 138, 82),  "label": "XUẤT PHÁT", "sub": "+200.000"},
    10: {"bg": (222, 128, 45), "label": "NHÀ TÙ",     "sub": "Thăm quan"},
    20: {"bg": (44, 122, 194), "label": "CÔNG VIÊN",  "sub": "Tự Do"},
    30: {"bg": (196, 51, 51),  "label": "ĐI TÙ",      "sub": "Bị Bắt!"},
}

_AVATAR_CACHE = {}
_AVATAR_SESSION = None


async def _get_avatar_image(url):
    """Tải avatar Discord về, crop tròn, trả về PIL.Image RGBA 128x128 (có cache)."""
    global _AVATAR_SESSION
    if not PIL_OK or not AIOHTTP_OK or not url:
        return None
    if url in _AVATAR_CACHE:
        return _AVATAR_CACHE[url]
    try:
        if _AVATAR_SESSION is None or _AVATAR_SESSION.closed:
            _AVATAR_SESSION = aiohttp.ClientSession()
        async with _AVATAR_SESSION.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
        raw = Image.open(io.BytesIO(data)).convert("RGBA")
        raw = raw.resize((128, 128), Image.LANCZOS)
        mask = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 128, 128), fill=255)
        raw.putalpha(mask)
        _AVATAR_CACHE[url] = raw
        return raw
    except Exception as e:
        print(f"[MONO] avatar fetch error: {e}")
        return None


def _m(n):
    return f"{n:,}".replace(",", ".")


# ── DỮ LIỆU BÀN CỜ (40 Ô, LẤY THEO TỈ LỆ CỜ TỶ PHÚ CỔ ĐIỂN) ───────────
def _build_board():
    board = [None] * 40
    board[0]  = {"name": "Xuất Phát", "type": "go"}
    board[10] = {"name": "Nhà Tù (Thăm Quan)", "type": "jail"}
    board[20] = {"name": "Công Viên Tự Do", "type": "free_parking"}
    board[30] = {"name": "Đi Tù!", "type": "go_to_jail"}

    for i in (2, 7, 17, 22, 36):
        board[i] = {"name": "Cơ Hội", "type": "chance"}
    board[4]  = {"name": "Thuế Thu Nhập", "type": "tax", "amount": 200_000}
    board[33] = {"name": "Thuế Tài Sản", "type": "tax", "amount": 100_000}
    board[38] = {"name": "Thuế Xa Xỉ", "type": "tax", "amount": 75_000}

    for i, name in [(5, "Ga Sài Gòn"), (15, "Ga Hà Nội"), (25, "Ga Đà Nẵng"), (35, "Ga Nha Trang")]:
        board[i] = {"name": name, "type": "railroad", "price": 200_000, "group": "railroad"}

    for i, name in [(12, "Cty Điện Lực"), (28, "Cty Cấp Nước")]:
        board[i] = {"name": name, "type": "utility", "price": 150_000, "group": "utility"}

    props = [
        # idx, name, group, price, rent[0h,1h,2h,3h,4h,hotel], house_cost
        (1,  "Cần Thơ",       "brown",     60_000,  [2_000, 10_000, 30_000, 90_000, 160_000, 250_000],   50_000),
        (3,  "Sóc Trăng",     "brown",     60_000,  [4_000, 20_000, 60_000, 180_000, 320_000, 450_000],  50_000),
        (6,  "Vĩnh Long",     "lightblue", 100_000, [6_000, 30_000, 90_000, 270_000, 400_000, 550_000],  50_000),
        (8,  "Bến Tre",       "lightblue", 100_000, [6_000, 30_000, 90_000, 270_000, 400_000, 550_000],  50_000),
        (9,  "Tiền Giang",    "lightblue", 120_000, [8_000, 40_000, 100_000, 300_000, 450_000, 600_000], 50_000),
        (11, "Vũng Tàu",      "pink",      140_000, [10_000, 50_000, 150_000, 450_000, 625_000, 750_000], 100_000),
        (13, "Đà Lạt",        "pink",      140_000, [10_000, 50_000, 150_000, 450_000, 625_000, 750_000], 100_000),
        (14, "Phan Thiết",    "pink",      160_000, [12_000, 60_000, 180_000, 500_000, 700_000, 900_000], 100_000),
        (16, "Hải Phòng",     "orange",    180_000, [14_000, 70_000, 200_000, 550_000, 750_000, 950_000], 100_000),
        (18, "Quy Nhơn",      "orange",    180_000, [14_000, 70_000, 200_000, 550_000, 750_000, 950_000], 100_000),
        (19, "Buôn Ma Thuột", "orange",    200_000, [16_000, 80_000, 220_000, 600_000, 800_000, 1_000_000], 100_000),
        (21, "Hà Nội",        "red",       220_000, [18_000, 90_000, 250_000, 700_000, 875_000, 1_050_000], 150_000),
        (23, "Hạ Long",       "red",       220_000, [18_000, 90_000, 250_000, 700_000, 875_000, 1_050_000], 150_000),
        (24, "Sa Pa",         "red",       240_000, [20_000, 100_000, 300_000, 750_000, 925_000, 1_100_000], 150_000),
        (26, "Phú Quốc",      "yellow",    260_000, [22_000, 110_000, 330_000, 800_000, 975_000, 1_150_000], 150_000),
        (27, "Côn Đảo",       "yellow",    260_000, [22_000, 110_000, 330_000, 800_000, 975_000, 1_150_000], 150_000),
        (29, "Mũi Né",        "yellow",    280_000, [24_000, 120_000, 360_000, 850_000, 1_025_000, 1_200_000], 150_000),
        (31, "Ninh Bình",     "green",     300_000, [26_000, 130_000, 390_000, 900_000, 1_100_000, 1_275_000], 200_000),
        (32, "Tam Đảo",       "green",     300_000, [26_000, 130_000, 390_000, 900_000, 1_100_000, 1_275_000], 200_000),
        (34, "Bà Nà Hills",   "green",     320_000, [28_000, 150_000, 450_000, 1_000_000, 1_200_000, 1_400_000], 200_000),
        (37, "Landmark 81",   "blue",      350_000, [35_000, 175_000, 500_000, 1_100_000, 1_300_000, 1_500_000], 200_000),
        (39, "Bitexco Tower", "blue",      400_000, [50_000, 200_000, 600_000, 1_400_000, 1_700_000, 2_000_000], 200_000),
    ]
    for idx, name, group, price, rent, hcost in props:
        board[idx] = {
            "name": name, "type": "property", "group": group,
            "price": price, "rent": rent, "house_cost": hcost,
        }
    return board


BOARD = _build_board()
OWNABLE_TYPES = ("property", "railroad", "utility")
GROUP_INDICES = {}
for _i, _t in enumerate(BOARD):
    if _t and _t["type"] in OWNABLE_TYPES:
        GROUP_INDICES.setdefault(_t["group"], []).append(_i)

CHANCE_CARDS = [
    {"text": "🎉 Trúng số! Nhận **{v}**", "type": "gain", "value": 100_000},
    {"text": "🚓 Bị phạt vi phạm giao thông! Mất **{v}**", "type": "lose", "value": 50_000},
    {"text": "🏁 Quay về Ô Xuất Phát, nhận **{v}**!", "type": "goto_go"},
    {"text": "🚨 Đi tù ngay lập tức!", "type": "gotojail"},
    {"text": "🎂 Sinh nhật bạn! Mỗi người chơi khác tặng bạn **{v}**", "type": "collect_each", "value": 50_000},
    {"text": "🎗️ Làm từ thiện! Bạn trả mỗi người chơi khác **{v}**", "type": "pay_each", "value": 50_000},
    {"text": "👟 Tiến 3 ô về phía trước!", "type": "move", "value": 3},
    {"text": "⏪ Lùi lại 3 ô!", "type": "move", "value": -3},
    {"text": "🎫 Nhận thẻ **Miễn Tù** — giữ để dùng khi cần!", "type": "get_out_card"},
    {"text": "🔧 Bảo trì nhà cửa! Trả **{v}** cho mỗi căn nhà, **x3** cho mỗi khách sạn bạn sở hữu", "type": "house_repair", "value": 20_000},
]


# =====================================================================
# 🖼️ VẼ ẢNH BÀN CỜ (v2 — layout gọn, không chồng chữ/icon, tự co giãn)
# =====================================================================
_FONT_CACHE = {}

# 🇻🇳 FONT ĐI KÈM MODULE — không phụ thuộc font cài sẵn trên server nữa.
# Trước đây module tìm font trong /usr/share/fonts/... — nếu server không
# cài Poppins/Noto (rất hay gặp trên VPS trống), Pillow sẽ âm thầm rơi về
# ImageFont.load_default(), một font bitmap CHỈ CÓ KÝ TỰ ASCII → mọi chữ có
# dấu tiếng Việt (ư, ơ, đ, ệ...) bị vẽ thành ô vuông/lỗi như trong ảnh lỗi.
# Cách khắc phục triệt để: ĐÓNG GÓI SẴN font hỗ trợ đầy đủ tiếng Việt ngay
# cạnh file này, nên chạy trên bất kỳ server nào cũng ra chữ đúng 100%.
#
# → Nhớ copy cả thư mục "mono_fonts/" cùng chỗ với monopoly.py khi deploy!
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mono_fonts")

# Be Vietnam Pro — font chữ hỗ trợ tiếng Việt đầy đủ dấu, rõ ràng, dễ đọc
# ở cỡ nhỏ (dùng cho tên ô, giá tiền, bảng thông tin...).
_BUNDLED_FONTS = {
    "Regular":  os.path.join(FONT_DIR, "BeVietnamPro-Regular.ttf"),
    "Medium":   os.path.join(FONT_DIR, "BeVietnamPro-Medium.ttf"),
    "SemiBold": os.path.join(FONT_DIR, "BeVietnamPro-SemiBold.ttf"),
    "Bold":     os.path.join(FONT_DIR, "BeVietnamPro-Bold.ttf"),
    "ExtraBold": os.path.join(FONT_DIR, "BeVietnamPro-ExtraBold.ttf"),
    # Font chữ to, có cá tính, chỉ dùng riêng cho logo "CỜ TỶ PHÚ" ở giữa bàn.
    "Title":    os.path.join(FONT_DIR, "YoungTypeface-BoldDisplay.otf"),
}

# Nếu vì lý do gì đó thư mục mono_fonts/ bị thiếu, vẫn cố tìm font hệ thống
# hỗ trợ tiếng Việt trước khi chấp nhận rơi về font mặc định (méo chữ).
_SYSTEM_FALLBACKS = {
    "Regular": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "Medium": [
        "/usr/share/fonts/truetype/noto/NotoSans-Medium.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "SemiBold": [
        "/usr/share/fonts/truetype/noto/NotoSans-SemiBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "Bold": [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "ExtraBold": [
        "/usr/share/fonts/truetype/noto/NotoSans-ExtraBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "Title": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}

_font_warned = False


def _load_font(size, weight="Regular"):
    global _font_warned
    size = max(int(size), 8)
    key = (size, weight)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates = [_BUNDLED_FONTS.get(weight, _BUNDLED_FONTS["Regular"])]
    candidates += _SYSTEM_FALLBACKS.get(weight, _SYSTEM_FALLBACKS["Regular"])

    font = None
    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
        if not _font_warned:
            _font_warned = True
            print(
                "[MONO] ⚠️ Không tìm thấy font trong 'mono_fonts/' cạnh monopoly.py! "
                "Chữ tiếng Việt sẽ bị lỗi (ô vuông). Hãy copy thư mục mono_fonts/ "
                "đi kèm cùng chỗ với monopoly.py."
            )
    _FONT_CACHE[key] = font
    return font


def _text_w(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _wrap_px(draw, text, font, max_w, max_lines=3):
    """Ngắt dòng theo ĐỘ RỘNG PIXEL thực tế (không theo số ký tự) để không
    bao giờ bị tràn/chữ dính nhau, kể cả với font có độ rộng ký tự khác nhau."""
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if _text_w(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if lines and _text_w(draw, lines[-1], font) > max_w:
        while lines[-1] and _text_w(draw, lines[-1] + "…", font) > max_w:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1] + "…"
    return lines


def _cell_rect(i, cell):
    """Trả về (x0,y0,x1,y1) của ô thứ i trên lưới 11x11 (layout bàn cờ Tỷ Phú thật)."""
    if i <= 10:
        col, row = 10 - i, 10
    elif i <= 20:
        col, row = 0, 20 - i
    elif i <= 30:
        col, row = i - 20, 0
    else:
        col, row = 10, i - 30
    x0, y0 = col * cell, row * cell
    return x0, y0, x0 + cell, y0 + cell


def _rrect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _draw_tile_icon(draw, cx, cy, r, kind):
    """Icon nhỏ tự vẽ bằng hình học/emoji đơn giản (không sao chép artwork nào),
    luôn nằm gọn trong dải màu phía trên ô, KHÔNG đè lên tên ô bên dưới."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 240))
    if kind == "chance":
        draw.text((cx, cy - r * 0.05), "?", font=_load_font(r * 1.5, "Bold"), fill=(235, 140, 30), anchor="mm")
    elif kind == "tax":
        draw.text((cx, cy - r * 0.05), "$", font=_load_font(r * 1.3, "Bold"), fill=(140, 70, 190), anchor="mm")
    elif kind == "railroad":
        bw, bh = r * 1.15, r * 0.75
        draw.rounded_rectangle([cx - bw / 2, cy - bh / 2 - r * 0.12, cx + bw / 2, cy + bh / 2 - r * 0.12],
                                radius=max(2, r * 0.12), fill=(55, 60, 70))
        wr = max(2, r * 0.18)
        draw.ellipse([cx - bw / 2 + wr, cy + bh / 2 - wr * 1.6 - r * 0.12, cx - bw / 2 + wr * 3, cy + bh / 2 + wr * 0.4 - r * 0.12], fill=(25, 25, 25))
        draw.ellipse([cx + bw / 2 - wr * 3, cy + bh / 2 - wr * 1.6 - r * 0.12, cx + bw / 2 - wr, cy + bh / 2 + wr * 0.4 - r * 0.12], fill=(25, 25, 25))
    elif kind == "utility_power":
        draw.text((cx, cy - r * 0.05), "⚡", font=_load_font(r * 1.3, "Bold"), fill=(230, 180, 20), anchor="mm")
    elif kind == "utility_water":
        draw.ellipse([cx - r * 0.55, cy - r * 0.3, cx + r * 0.55, cy + r * 0.5], fill=(70, 150, 220))
        draw.polygon([(cx - r * 0.32, cy - r * 0.25), (cx + r * 0.32, cy - r * 0.25), (cx, cy - r * 0.75)], fill=(70, 150, 220))


def _draw_token(base_img, draw, cx, cy, r, color, avatar_img, is_current, letter):
    """Vẽ quân cờ (avatar tròn hoặc chấm màu có chữ cái đầu tên)."""
    draw.ellipse([cx - r - 3, cy - r - 1, cx + r + 3, cy + r + 5], fill=(0, 0, 0, 55))  # bóng đổ nhẹ
    ring = (255, 205, 0) if is_current else (255, 255, 255)
    ring_w = max(3, int(r * 0.22))
    if avatar_img is not None:
        size = r * 2
        av = avatar_img.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        base_img.paste(av, (cx - r, cy - r), mask)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring, width=ring_w)
    else:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=ring, width=ring_w)
        draw.text((cx, cy), letter, font=_load_font(max(10, int(r * 0.9)), "Bold"), fill=(255, 255, 255), anchor="mm")


def render_board_image(game, avatars=None, highlight_id=None):
    """Vẽ toàn bộ bàn cờ ra 1 ảnh PNG (BytesIO). Layout được thiết kế lại
    hoàn toàn (v2): mỗi ô có dải màu + icon RIÊNG BIỆT phía trên, tên ô tự
    NGẮT DÒNG & THU NHỎ FONT để luôn vừa khít, giá tiền/nhà cửa không bao
    giờ chồng lên tên ô. avatars: dict {player_id: PIL.Image RGBA}.
    highlight_id: id người chơi cần khoanh viền đỏ nổi bật."""
    if not PIL_OK:
        return None
    avatars = avatars or {}

    SIZE = 1400
    CELL = SIZE // 11
    SIZE = CELL * 11
    img = Image.new("RGB", (SIZE, SIZE), BOARD_BG)
    draw = ImageDraw.Draw(img, "RGBA")

    f_name = _load_font(CELL * 0.115, "SemiBold")
    f_price = _load_font(CELL * 0.11, "Bold")
    f_corner_label = _load_font(CELL * 0.185, "Bold")
    f_corner_sub = _load_font(CELL * 0.115, "Medium")
    f_title = _load_font(CELL * 0.95, "Title")
    f_tagline = _load_font(CELL * 0.16, "Medium")
    f_legend_name = _load_font(CELL * 0.155, "SemiBold")
    f_legend_money = _load_font(CELL * 0.13, "Medium")

    draw.rounded_rectangle([4, 4, SIZE - 4, SIZE - 4], radius=24, outline=(40, 35, 25), width=5, fill=BOARD_BG)
    draw.rounded_rectangle([CELL + 4, CELL + 4, SIZE - CELL - 4, SIZE - CELL - 4],
                            radius=28, fill=CENTER_BG, outline=(220, 208, 180), width=2)

    cur_idx = game["turn_index"] % len(game["players"]) if game.get("players") else -1
    cur_id = game["players"][cur_idx]["id"] if cur_idx >= 0 else None

    BAND_FRAC = 0.30

    for i in range(40):
        tile = BOARD[i]
        x0, y0, x1, y1 = _cell_rect(i, CELL)
        pad = 4
        bx0, by0, bx1, by1 = x0 + pad, y0 + pad, x1 - pad, y1 - pad
        is_corner = i in (0, 10, 20, 30)

        if is_corner:
            style = CORNER_STYLES[i]
            _rrect(draw, [bx0, by0, bx1, by1], 16, fill=style["bg"], outline=(35, 30, 25), width=2)
            cx = (bx0 + bx1) // 2
            icon_r = CELL * 0.16
            icon_cy = by0 + (by1 - by0) * 0.30
            if i == 0:
                w = icon_r * 0.9
                draw.polygon([(cx, icon_cy - w), (cx + w, icon_cy + w * 0.3), (cx + w * 0.4, icon_cy + w * 0.3),
                              (cx + w * 0.4, icon_cy + w), (cx - w * 0.4, icon_cy + w), (cx - w * 0.4, icon_cy + w * 0.3),
                              (cx - w, icon_cy + w * 0.3)], fill=(255, 255, 255))
            elif i == 10:
                draw.rounded_rectangle([cx - icon_r, icon_cy - icon_r * 0.6, cx + icon_r, icon_cy + icon_r * 0.7],
                                        radius=4, fill=(255, 255, 255))
                step = max(4, icon_r * 0.4)
                bxo = cx - icon_r * 0.6
                while bxo <= cx + icon_r * 0.6:
                    draw.line([(bxo, icon_cy - icon_r * 0.5), (bxo, icon_cy + icon_r * 0.6)], fill=style["bg"], width=3)
                    bxo += step
            elif i == 20:
                draw.ellipse([cx - icon_r, icon_cy - icon_r, cx + icon_r, icon_cy + icon_r], fill=(255, 255, 255))
                draw.text((cx, icon_cy), "P", font=_load_font(icon_r * 1.3, "Bold"), fill=style["bg"], anchor="mm")
            elif i == 30:
                draw.ellipse([cx - icon_r, icon_cy - icon_r, cx + icon_r, icon_cy + icon_r], fill=(255, 255, 255))
                draw.text((cx, icon_cy), "!", font=_load_font(icon_r * 1.5, "Bold"), fill=style["bg"], anchor="mm")

            label_y = by0 + (by1 - by0) * 0.62
            sub_y = by0 + (by1 - by0) * 0.85
            lbl_lines = [style["label"]]
            if _text_w(draw, lbl_lines[0], f_corner_label) > (bx1 - bx0 - 10):
                lbl_lines = _wrap_px(draw, lbl_lines[0], f_corner_label, bx1 - bx0 - 10, 2)
            ly = label_y - (len(lbl_lines) - 1) * (f_corner_label.size * 0.55)
            for ln in lbl_lines:
                draw.text((cx, ly), ln, font=f_corner_label, fill=(255, 255, 255), anchor="mm")
                ly += f_corner_label.size * 1.05
            draw.text((cx, sub_y), style["sub"], font=f_corner_sub, fill=(255, 255, 255, 235), anchor="mm")
            continue

        # ô thường: nền trắng bo góc
        _rrect(draw, [bx0, by0, bx1, by1], 10, fill=(255, 255, 255), outline=(70, 65, 60), width=1)

        band_color = None
        icon_kind = None
        if tile["type"] in OWNABLE_TYPES:
            band_color = GROUP_COLORS.get(tile["group"], (150, 150, 150))
            if tile["type"] == "railroad":
                icon_kind = "railroad"
            elif tile["type"] == "utility":
                icon_kind = "utility_power" if "Điện" in tile["name"] else "utility_water"
        elif tile["type"] == "chance":
            band_color = (240, 155, 40)
            icon_kind = "chance"
        elif tile["type"] == "tax":
            band_color = (150, 95, 195)
            icon_kind = "tax"

        band_h = (by1 - by0) * BAND_FRAC
        content_top = by0
        if band_color:
            _rrect(draw, [bx0, by0, bx1, by0 + band_h], 10, fill=band_color)
            draw.rectangle([bx0, by0 + band_h - 10, bx1, by0 + band_h], fill=band_color)
            content_top = by0 + band_h
            if icon_kind:
                _draw_tile_icon(draw, (bx0 + bx1) // 2, by0 + band_h / 2, max(9, band_h * 0.32), icon_kind)

        content_bottom = by1 - (14 if tile["type"] in OWNABLE_TYPES else 6)
        avail_w = (bx1 - bx0) - 10
        name_font = f_name
        lines = _wrap_px(draw, tile["name"], name_font, avail_w, 3)
        line_h = name_font.size * 1.08
        total_h = line_h * len(lines)
        area_h = content_bottom - content_top
        while total_h > area_h and name_font.size > 10:
            name_font = _load_font(name_font.size - 1, "SemiBold")
            lines = _wrap_px(draw, tile["name"], name_font, avail_w, 3)
            line_h = name_font.size * 1.08
            total_h = line_h * len(lines)

        ty = content_top + (area_h - total_h) / 2 + line_h / 2
        cxm = (bx0 + bx1) // 2
        for ln in lines:
            draw.text((cxm, ty), ln, font=name_font, fill=(35, 32, 28), anchor="mm")
            ty += line_h

        if tile["type"] in OWNABLE_TYPES:
            draw.text((bx0 + 8, by1 - 8), f"{tile['price'] // 1000}k", font=f_price, fill=(90, 85, 78), anchor="lm")

        # chủ sở hữu (viền màu quanh ô) + nhà/khách sạn (góc dưới-phải, không đè giá)
        prop = game.get("properties", {}).get(str(i))
        if prop and prop.get("owner"):
            owner_p = next((p for p in game["players"] if p["id"] == prop["owner"]), None)
            if owner_p:
                oc_idx = game["players"].index(owner_p) % len(PLAYER_COLORS)
                oc = PLAYER_COLORS[oc_idx]
                draw.rounded_rectangle([bx0, by0, bx1, by1], radius=10, outline=oc, width=4)
                houses = prop.get("houses", 0)
                if houses == 5:
                    hb_w, hb_h = CELL * 0.19, CELL * 0.115
                    draw.rounded_rectangle([bx1 - hb_w - 6, by1 - hb_h - 6, bx1 - 6, by1 - 6], radius=3, fill=(214, 40, 40))
                    draw.text(((bx1 - hb_w / 2 - 6), by1 - hb_h / 2 - 6), "H", font=_load_font(CELL * 0.08, "Bold"), fill=(255, 255, 255), anchor="mm")
                elif houses > 0:
                    for h in range(houses):
                        hx = bx1 - 10 - h * (CELL * 0.078)
                        hy = by1 - 8
                        hs = CELL * 0.045
                        draw.polygon([(hx - hs, hy - hs * 1.2), (hx, hy - hs * 2.4), (hx + hs, hy - hs * 1.2)], fill=(35, 150, 70))
                        draw.rectangle([hx - hs, hy - hs * 1.2, hx + hs, hy], fill=(35, 150, 70))

    # ── khu trung tâm: tiêu đề + quỹ công viên + thẻ bài người chơi ──
    cxm, cym = SIZE // 2, SIZE // 2
    center_w = SIZE - 2 * CELL

    title_txt = "CỜ TỶ PHÚ"
    tb = draw.textbbox((0, 0), title_txt, font=f_title)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    title_img = Image.new("RGBA", (int(tw + 60), int(th + 60)), (0, 0, 0, 0))
    td = ImageDraw.Draw(title_img)
    td.text((title_img.width // 2, title_img.height // 2), title_txt, font=f_title, fill=(212, 40, 40, 255),
             anchor="mm", stroke_width=max(3, int(CELL // 24)), stroke_fill=(255, 255, 255, 255))
    title_img = title_img.rotate(-4, expand=True, resample=Image.BICUBIC)
    title_y = CELL + int(CELL * 0.9)
    img.paste(title_img, (cxm - title_img.width // 2, title_y - title_img.height // 2), title_img)
    tagline_y = title_y + int(title_img.height * 0.42)
    draw.text((cxm, tagline_y), "— Ai giàu nhất sẽ thắng —", font=f_tagline, fill=(150, 120, 60), anchor="mm")

    if game.get("pot", 0) > 0:
        pot_y = tagline_y + int(CELL * 0.5)
        draw.rounded_rectangle([cxm - CELL * 1.35, pot_y - CELL * 0.22, cxm + CELL * 1.35, pot_y + CELL * 0.22],
                                radius=14, fill=(235, 245, 235), outline=(60, 150, 90), width=2)
        draw.text((cxm, pot_y), f"🅿 Quỹ Công Viên: {_m(game['pot'])}", font=f_tagline, fill=(35, 120, 60), anchor="mm")
        legend_top = pot_y + CELL * 0.55
    else:
        legend_top = tagline_y + int(CELL * 0.35)

    alive = [p for p in game.get("players", []) if not p.get("bankrupt")]
    dead = [p for p in game.get("players", []) if p.get("bankrupt")]
    n_cols = 2 if len(alive) > 1 else 1
    card_w = center_w * 0.42
    card_h = CELL * 0.62
    gap_x = center_w * 0.06
    total_row_w = n_cols * card_w + (n_cols - 1) * gap_x
    start_x = cxm - total_row_w / 2

    for idx_a, p in enumerate(alive):
        idx = game["players"].index(p)
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        col = idx_a % n_cols
        row_n = idx_a // n_cols
        lx = start_x + col * (card_w + gap_x)
        ly = legend_top + row_n * (card_h + CELL * 0.14)
        is_cur = p["id"] == cur_id
        card_fill = (255, 250, 225) if is_cur else (250, 250, 248)
        card_outline = (235, 175, 30) if is_cur else (215, 210, 200)
        draw.rounded_rectangle([lx, ly, lx + card_w, ly + card_h], radius=14, fill=card_fill,
                                outline=card_outline, width=3 if is_cur else 2)
        av_r = int(card_h * 0.34)
        av_cx, av_cy = int(lx + av_r + 10), int(ly + card_h / 2)
        av = avatars.get(p["id"])
        _draw_token(img, draw, av_cx, av_cy, av_r, color, av, is_cur, (p["name"][:1] or "?").upper())
        turn_mark = " 👑" if is_cur else ""
        jail_mark = " ⛓" if p.get("in_jail") else ""
        name_line = p["name"][:16] + turn_mark
        tx = av_cx + av_r + 14
        draw.text((tx, av_cy - card_h * 0.16), name_line, font=f_legend_name, fill=(40, 35, 30), anchor="lm")
        draw.text((tx, av_cy + card_h * 0.16), f"{_m(p['money'])}{jail_mark}", font=f_legend_money, fill=(90, 85, 78), anchor="lm")

    if dead:
        n_rows = (len(alive) + n_cols - 1) // n_cols if alive else 0
        dy = legend_top + n_rows * (card_h + CELL * 0.14) + CELL * 0.2
        draw.text((cxm, dy), "💀 Phá sản: " + ", ".join(p["name"] for p in dead), font=f_legend_money, fill=(160, 50, 50), anchor="mm")

    # ── quân cờ trên các ô (avatar người chơi) ──────────────────────
    for idx, p in enumerate(game.get("players", [])):
        if p.get("bankrupt"):
            continue
        x0, y0, x1, y1 = _cell_rect(p["position"], CELL)
        same = [pp for pp in game["players"] if not pp.get("bankrupt") and pp["position"] == p["position"]]
        n = len(same)
        pos_in_group = same.index(p)
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2 + int(CELL * 0.14)
        if n > 1:
            spread = min(CELL // 2 - 16, 20)
            cx += int(((pos_in_group / max(n - 1, 1)) - 0.5) * 2 * spread)
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        av = avatars.get(p["id"])
        r = int(CELL * 0.15) if p["id"] == cur_id else int(CELL * 0.13)
        _draw_token(img, draw, cx, cy, r, color, av, p["id"] == cur_id, (p["name"][:1] or "?").upper())
        if highlight_id and p["id"] == highlight_id:
            draw.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], outline=(255, 20, 20), width=4)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_zoom_image(game, player, avatars=None):
    """🔎 Vẽ ảnh ZOOM cận cảnh vào đúng ô người chơi đang đứng, kèm bảng
    thông tin chi tiết về ô đó (giá, tiền thuê theo số nhà, chủ sở hữu...)
    ghép ngay bên dưới. Dùng cho nút '📍 Vị Trí Của Tôi'."""
    if not PIL_OK:
        return None
    avatars = avatars or {}
    SIZE = 1400
    CELL = SIZE // 11
    SIZE = CELL * 11
    board_buf = render_board_image(game, avatars=avatars, highlight_id=player["id"])
    if board_buf is None:
        return None
    board_img = Image.open(board_buf).convert("RGB")

    pos = player["position"]
    x0, y0, x1, y1 = _cell_rect(pos, CELL)
    margin = int(CELL * 1.3)
    cx0 = max(0, x0 - margin)
    cy0 = max(0, y0 - margin)
    cx1 = min(SIZE, x1 + margin)
    cy1 = min(SIZE, y1 + margin)
    crop = board_img.crop((cx0, cy0, cx1, cy1))
    scale = min(3.0, 1000 / max(crop.width, crop.height))
    crop = crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))), Image.LANCZOS)

    tile = BOARD[pos]
    prop = game.get("properties", {}).get(str(pos))
    panel_w = crop.width
    panel_h = 320
    panel = Image.new("RGB", (panel_w, panel_h), (255, 253, 247))
    pd = ImageDraw.Draw(panel)
    pd.rectangle([0, 0, panel_w, panel_h], outline=(215, 205, 180), width=2)

    f_h1 = _load_font(38, "Bold")
    f_h2 = _load_font(24, "SemiBold")
    f_body = _load_font(22, "Medium")
    f_small = _load_font(19, "Medium")

    pad = 26
    ty = pad
    pd.text((pad, ty), f"📍 {tile['name']}", font=f_h1, fill=(30, 30, 30))
    ty += 50

    if tile["type"] in OWNABLE_TYPES:
        owner_id = prop.get("owner") if prop else None
        owner_p = next((p for p in game["players"] if p["id"] == owner_id), None) if owner_id else None
        if owner_p:
            pd.text((pad, ty), f"🏷️ Chủ sở hữu: {owner_p['name']}", font=f_h2, fill=(50, 100, 50))
        else:
            pd.text((pad, ty), f"🏷️ Chưa có chủ — giá {_m(tile['price'])}{'' }", font=f_h2, fill=(180, 100, 20))
        ty += 36

        if tile["type"] == "property":
            houses = prop.get("houses", 0) if prop else 0
            rent = tile["rent"][houses]
            house_word = "Khách sạn" if houses == 5 else f"{houses} nhà"
            pd.text((pad, ty), f"🏠 {house_word}  •  💰 Thuê hiện tại: {_m(rent)}", font=f_body, fill=(60, 55, 50))
            ty += 34
            rent_line = "  ".join(f"{h}n:{_m(v)}" for h, v in zip(["0", "1", "2", "3", "4", "KS"], tile["rent"]))
            pd.text((pad, ty), rent_line, font=f_small, fill=(120, 112, 100))
            ty += 30
            pd.text((pad, ty), f"🔨 Giá xây nhà: {_m(tile['house_cost'])} / căn", font=f_small, fill=(120, 112, 100))
        elif tile["type"] == "railroad":
            pd.text((pad, ty), "🚉 Tiền thuê tăng theo số nhà ga cùng chủ sở hữu (25k / 50k / 100k / 200k)", font=f_small, fill=(120, 112, 100))
        elif tile["type"] == "utility":
            pd.text((pad, ty), "🏭 Tiền thuê = tổng xúc xắc × (4k nếu sở hữu 1 cái, 10k nếu sở hữu cả 2)", font=f_small, fill=(120, 112, 100))
    elif tile["type"] == "tax":
        pd.text((pad, ty), f"🧾 Thuế phải nộp: {_m(tile['amount'])}", font=f_h2, fill=(120, 60, 160))
    elif tile["type"] == "chance":
        pd.text((pad, ty), "❓ Ô sự kiện ngẫu nhiên — có thể được thưởng hoặc bị phạt!", font=f_body, fill=(200, 120, 30))
    elif tile["type"] == "go":
        pd.text((pad, ty), f"🚀 Mỗi lần đi qua/dừng tại đây, nhận {_m(MONO_GO_SALARY)}", font=f_body, fill=(40, 130, 70))
    elif tile["type"] == "jail":
        pd.text((pad, ty), "🚔 Chỉ là thăm quan nếu không bị bắt vào tù ở lượt trước", font=f_body, fill=(90, 85, 78))
    elif tile["type"] == "free_parking":
        pot = game.get("pot", 0)
        pd.text((pad, ty), f"🅿️ Quỹ hiện tại: {_m(pot)} — ai dừng ở đây sẽ nhận trọn quỹ!", font=f_body, fill=(40, 130, 70))
    elif tile["type"] == "go_to_jail":
        pd.text((pad, ty), "🚨 Dừng ở đây sẽ bị bắt vào tù ngay lập tức!", font=f_body, fill=(200, 50, 50))
    ty += 44

    pd.line([(pad, ty), (panel_w - pad, ty)], fill=(225, 218, 200), width=2)
    ty += 18
    pd.text((pad, ty), f"👤 {player['name']}   •   💰 {_m(player['money'])}{'  •  ⛓ Đang ở tù' if player.get('in_jail') else ''}",
             font=f_body, fill=(35, 32, 28))

    final_img = Image.new("RGB", (panel_w, crop.height + panel_h), (255, 253, 247))
    final_img.paste(crop, (0, 0))
    final_img.paste(panel, (0, crop.height))

    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# =====================================================================
def setup_monopoly(bot, db, load_user=None, save_user=None, add_history=None):
    mono_col = db["monopoly_games"]
    _locks = {}  # channel_id(str) -> asyncio.Lock, chống double-click race condition

    def get_lock(channel_id):
        cid = str(channel_id)
        if cid not in _locks:
            _locks[cid] = asyncio.Lock()
        return _locks[cid]

    # ── DB HELPERS ────────────────────────────────────────────────────
    def load_game(channel_id):
        try:
            return mono_col.find_one({"_id": str(channel_id)})
        except Exception as e:
            print(f"[MONO] load_game error: {e}")
            return None

    def save_game(game):
        try:
            mono_col.update_one({"_id": game["_id"]}, {"$set": game}, upsert=True)
        except Exception as e:
            print(f"[MONO] save_game error: {e}")

    def delete_game(channel_id):
        try:
            mono_col.delete_one({"_id": str(channel_id)})
        except Exception as e:
            print(f"[MONO] delete_game error: {e}")

    def new_game(channel_id, guild_id, host_id, host_name, mode, host_avatar=None):
        game = {
            "_id": str(channel_id),
            "guild_id": guild_id,
            "status": "waiting",
            "mode": mode,  # "pvp" | "bot"
            "host_id": str(host_id),
            "players": [{
                "id": str(host_id), "name": host_name, "money": MONO_START_MONEY,
                "position": 0, "in_jail": False, "jail_turns": 0,
                "bankrupt": False, "is_bot": False, "get_out_cards": 0,
                "avatar_url": host_avatar,
            }],
            "properties": {},
            "turn_index": 0,
            "last_roll": [0, 0],
            "has_rolled": False,
            "pending_buy": None,
            "doubles_count": 0,
            "pot": 0,
            "message_id": None,
            "log": [f"🎬 {host_name} tạo bàn cờ ({'Đấu Bot 🤖' if mode == 'bot' else 'Nhiều Người 👥'})"],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if mode == "bot":
            game["players"].append({
                "id": "BOT", "name": "🤖 Máy Tính", "money": MONO_START_MONEY,
                "position": 0, "in_jail": False, "jail_turns": 0,
                "bankrupt": False, "is_bot": True, "get_out_cards": 0,
            })
        return game

    def add_log(game, text):
        game.setdefault("log", []).insert(0, text)
        game["log"] = game["log"][:8]

    def get_player(game, user_id):
        for p in game["players"]:
            if p["id"] == str(user_id):
                return p
        return None

    def current_player(game):
        idx = game["turn_index"] % len(game["players"])
        return game["players"][idx]

    def active_players(game):
        return [p for p in game["players"] if not p["bankrupt"]]

    def owns_full_group(game, owner_id, group):
        idxs = GROUP_INDICES.get(group, [])
        return all(game["properties"].get(str(i), {}).get("owner") == owner_id for i in idxs)

    def calc_rent(game, tile_idx, dice_sum=7):
        tile = BOARD[tile_idx]
        prop = game["properties"].get(str(tile_idx))
        if not prop or not prop.get("owner"):
            return 0
        owner = prop["owner"]
        if tile["type"] == "property":
            houses = prop.get("houses", 0)
            rent = tile["rent"][houses]
            if houses == 0 and owns_full_group(game, owner, tile["group"]):
                rent *= 2
            return rent
        if tile["type"] == "railroad":
            owned = sum(1 for i in GROUP_INDICES["railroad"] if game["properties"].get(str(i), {}).get("owner") == owner)
            return int(25_000 * (2 ** max(0, owned - 1)))
        if tile["type"] == "utility":
            owned = sum(1 for i in GROUP_INDICES["utility"] if game["properties"].get(str(i), {}).get("owner") == owner)
            mult = 10_000 if owned >= 2 else 4_000
            return dice_sum * mult
        return 0

    def property_value(game, idx):
        """Ước tính giá trị 1 ô đất (giá gốc + tiền đã đầu tư xây nhà) — dùng cho Bảng Xếp Hạng."""
        tile = BOARD[idx]
        prop = game["properties"].get(str(idx), {})
        val = tile.get("price", 0)
        if tile["type"] == "property":
            val += prop.get("houses", 0) * tile.get("house_cost", 0)
        return val

    def net_worth(game, player):
        total = player["money"]
        for idx_str, prop in game["properties"].items():
            if prop.get("owner") == player["id"]:
                total += property_value(game, int(idx_str))
        return total

    def ensure_property_slots(game):
        for i, t in enumerate(BOARD):
            if t and t["type"] in OWNABLE_TYPES and str(i) not in game["properties"]:
                game["properties"][str(i)] = {"owner": None, "houses": 0}

    def pay(game, payer, amount, payee=None):
        """payer trả amount cho payee (None = ngân hàng). Nếu phá sản, xử lý bankrupt."""
        payer["money"] -= amount
        if payee:
            payee["money"] += amount
        else:
            game["pot"] = game.get("pot", 0) + amount
        if payer["money"] < 0:
            handle_bankrupt(game, payer, payee)

    def handle_bankrupt(game, player, creditor=None):
        if player["bankrupt"]:
            return
        player["bankrupt"] = True
        for idx_str, prop in game["properties"].items():
            if prop.get("owner") == player["id"]:
                if creditor:
                    prop["owner"] = creditor["id"]
                else:
                    prop["owner"] = None
                prop["houses"] = 0
        add_log(game, f"💸 **{player['name']}** đã PHÁ SẢN!" + (f" Tài sản về tay **{creditor['name']}**!" if creditor else " Tài sản về ngân hàng."))

    def move_player(game, player, steps, allow_go_bonus=True):
        old_pos = player["position"]
        new_pos = (old_pos + steps) % 40
        if allow_go_bonus and steps > 0 and new_pos <= old_pos and steps < 40:
            player["money"] += MONO_GO_SALARY
            add_log(game, f"🏁 **{player['name']}** đi qua Xuất Phát, nhận {_m(MONO_GO_SALARY)}{MONEY_EMOJI}!")
        elif allow_go_bonus and steps >= 40:
            player["money"] += MONO_GO_SALARY
        player["position"] = new_pos
        return new_pos

    def send_to_jail(game, player):
        player["position"] = MONO_JAIL_IDX
        player["in_jail"] = True
        player["jail_turns"] = 0
        add_log(game, f"🚨 **{player['name']}** bị bắt vào tù!")

    def draw_chance(game, player, dice_sum):
        card = random.choice(CHANCE_CARDS)
        ctype = card["type"]
        val = card.get("value", 0)
        text = card["text"].format(v=_m(val) + MONEY_EMOJI if val else "")
        add_log(game, f"❓ {player['name']}: {text}")

        if ctype == "gain":
            player["money"] += val
        elif ctype == "lose":
            pay(game, player, val)
        elif ctype == "goto_go":
            player["position"] = 0
            player["money"] += MONO_GO_SALARY
        elif ctype == "gotojail":
            send_to_jail(game, player)
        elif ctype == "collect_each":
            for op in active_players(game):
                if op["id"] != player["id"]:
                    op["money"] -= val
                    player["money"] += val
        elif ctype == "pay_each":
            for op in active_players(game):
                if op["id"] != player["id"]:
                    pay(game, player, val, op)
        elif ctype == "move":
            move_player(game, player, val, allow_go_bonus=(val > 0))
            resolve_tile(game, player, dice_sum, from_chance=True)
        elif ctype == "get_out_card":
            player["get_out_cards"] = player.get("get_out_cards", 0) + 1
        elif ctype == "house_repair":
            total_h = 0
            total_hotel = 0
            for idx_str, prop in game["properties"].items():
                if prop.get("owner") == player["id"]:
                    if prop.get("houses", 0) == 5:
                        total_hotel += 1
                    else:
                        total_h += prop.get("houses", 0)
            cost = total_h * val + total_hotel * val * 3
            if cost > 0:
                pay(game, player, cost)

    def resolve_tile(game, player, dice_sum, from_chance=False):
        tile = BOARD[player["position"]]
        ttype = tile["type"]

        if ttype == "tax":
            pay(game, player, tile["amount"])
            add_log(game, f"🧾 **{player['name']}** nộp thuế {_m(tile['amount'])}{MONEY_EMOJI}")
        elif ttype == "go_to_jail":
            send_to_jail(game, player)
        elif ttype == "chance":
            draw_chance(game, player, dice_sum)
        elif ttype == "free_parking":
            if game.get("pot", 0) > 0:
                player["money"] += game["pot"]
                add_log(game, f"🅿️ **{player['name']}** ẵm trọn quỹ {_m(game['pot'])}{MONEY_EMOJI} ở Công Viên Tự Do!")
                game["pot"] = 0
        elif ttype in OWNABLE_TYPES:
            prop = game["properties"].get(str(player["position"]))
            if prop is None:
                ensure_property_slots(game)
                prop = game["properties"][str(player["position"])]
            owner = prop.get("owner")
            if owner is None:
                if player["money"] >= tile["price"]:
                    game["pending_buy"] = player["position"]
                else:
                    add_log(game, f"💰 **{player['name']}** không đủ tiền mua **{tile['name']}**.")
            elif owner != player["id"]:
                owner_p = get_player(game, owner)
                rent = calc_rent(game, player["position"], dice_sum)
                if owner_p and rent > 0:
                    pay(game, player, rent, owner_p)
                    add_log(game, f"🏠 **{player['name']}** trả **{_m(rent)}**{MONEY_EMOJI} tiền thuê **{tile['name']}** cho **{owner_p['name']}**")
        # property/railroad/utility đã sở hữu bởi chính mình / go / jail(visit): không làm gì

    def check_winner(game):
        alive = active_players(game)
        if len(alive) <= 1 and game["status"] == "playing":
            game["status"] = "finished"
            if alive:
                winner = alive[0]
                add_log(game, f"👑 **{winner['name']}** THẮNG CUỘC — trở thành Tỷ Phú duy nhất!")
                if load_user and save_user and winner["id"] != "BOT":
                    try:
                        human_players = [p for p in game["players"] if not p["is_bot"]]
                        reward = 300_000 if len(human_players) >= 2 else 150_000
                        ud = load_user(winner["id"])
                        ud["money"] = ud.get("money", 0) + reward
                        # SỬA DÒNG NÀY CHO KHỚP VỚI save_user CỦA BẠN:
                        # (nhiều bot.py định nghĩa save_user(user_id, data) — nếu của bạn
                        #  chỉ nhận 1 tham số (tự lưu theo user đang load), xoá "ud" đi)
                        try:
                            save_user(winner["id"], ud)
                        except TypeError:
                            save_user(winner["id"])
                        if add_history:
                            add_history(winner["id"], f"Thắng Cờ Tỷ Phú (+{reward:,} {MONEY_EMOJI})")
                        game["log"][0] += f" (+{_m(reward)}{MONEY_EMOJI} thưởng thật!)"
                    except Exception as e:
                        print(f"[MONO] reward error: {e}")
            return True
        return False

    def advance_turn(game):
        game["has_rolled"] = False
        game["pending_buy"] = None
        game["doubles_count"] = 0
        n = len(game["players"])
        for _ in range(n):
            game["turn_index"] = (game["turn_index"] + 1) % n
            if not game["players"][game["turn_index"]]["bankrupt"]:
                break

    # ── EMBED BUILDERS ───────────────────────────────────────────────
    def build_lobby_embed(game):
        names = "\n".join(f"{'👑' if p['id']==game['host_id'] else '👤'} {p['name']}" for p in game["players"])
        mode_str = "🤖 Đấu Với Bot" if game["mode"] == "bot" else "👥 Nhiều Người Chơi"
        embed = discord.Embed(
            title="🎲 BÀN CỜ TỶ PHÚ — ĐANG CHỜ NGƯỜI CHƠI",
            description=(
                f"Chế độ: **{mode_str}**\n"
                f"Số người: **{len(game['players'])}/{MONO_MAX_PLAYERS}**\n\n"
                f"{names}\n\n"
                f"💰 Vốn khởi điểm: **{_m(MONO_START_MONEY)}**{MONEY_EMOJI}\n\n"
                f"👇 Bấm **Tham Gia** để vào bàn, chủ bàn bấm **Bắt Đầu** khi đủ người!"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Bàn cờ này không bao giờ hết hạn — cứ thoải mái rủ thêm bạn bè!")
        return embed

    def build_game_embed(game):
        cur = current_player(game)
        tile = BOARD[cur["position"]]
        d1, d2 = game.get("last_roll", [0, 0])

        lines = []
        for p in game["players"]:
            if p["bankrupt"]:
                lines.append(f"💀 ~~{p['name']}~~ — Phá sản")
                continue
            marker = "👉" if p["id"] == cur["id"] else "▫️"
            jail_str = " ⛓️" if p["in_jail"] else ""
            n_props = sum(1 for v in game["properties"].values() if v.get("owner") == p["id"])
            lines.append(f"{marker} **{p['name']}**{jail_str} — {_m(p['money'])}{MONEY_EMOJI} | 📍{BOARD[p['position']]['name']} | 🏠{n_props} đất")

        color = discord.Color.blue() if game["status"] == "playing" else discord.Color.dark_grey()
        title_str = "🏆 KẾT THÚC" if game["status"] == "finished" else f"Lượt của {cur['name']}"
        embed = discord.Embed(
            title=f"🎲 CỜ TỶ PHÚ — {title_str}",
            description="\n".join(lines),
            color=color
        )
        if game["status"] == "playing":
            roll_str = f"🎲 {d1} + {d2} = **{d1+d2}**" + (" (ĐÔI!)" if d1 == d2 and (d1 or d2) else "")
            embed.add_field(name="Xúc xắc gần nhất", value=roll_str, inline=True)
            embed.add_field(name="Đang đứng tại", value=f"**{tile['name']}**", inline=True)
            if game.get("pending_buy") is not None:
                pt = BOARD[game["pending_buy"]]
                embed.add_field(
                    name="🏷️ Có thể mua!",
                    value=f"**{pt['name']}** — giá **{_m(pt['price'])}**{MONEY_EMOJI}\nBấm **💰 Mua Đất** hoặc **⏭️ Kết Thúc Lượt** để bỏ qua.",
                    inline=False
                )
            if cur["in_jail"]:
                embed.add_field(
                    name="⛓️ Đang ở tù",
                    value=f"Lần thử: {cur['jail_turns']}/3 | Trả **{_m(MONO_JAIL_FINE)}**{MONEY_EMOJI} hoặc đổ đôi để ra tù.",
                    inline=False
                )
        if game.get("pot", 0) > 0:
            embed.add_field(name="🅿️ Quỹ Công Viên", value=f"{_m(game['pot'])}{MONEY_EMOJI}", inline=True)

        log_text = "\n".join(game.get("log", [])[:6]) or "..."
        embed.add_field(name="📜 Diễn Biến", value=log_text[:1000], inline=False)
        embed.set_footer(text=(
            f"Bàn cờ vĩnh viễn tại kênh này | Chế độ: {'🤖 Bot' if game['mode']=='bot' else '👥 PvP'} | "
            f"📍 Vị Trí • 📋 Tài Sản • 🏆 Xếp Hạng — bấm để xem chi tiết!"
        ))
        return embed

    def build_my_properties_embed(game, player):
        owned = [(int(idx), prop) for idx, prop in game["properties"].items() if prop.get("owner") == player["id"]]
        embed = discord.Embed(
            title=f"📋 Tài Sản Của {player['name']}",
            color=discord.Color.green()
        )
        if not owned:
            embed.description = "Bạn chưa sở hữu ô đất nào cả. Hãy đi vòng quanh bàn cờ và mua đất nhé!"
            embed.add_field(name="💰 Tiền mặt", value=f"{_m(player['money'])}{MONEY_EMOJI}", inline=True)
            return embed

        owned.sort(key=lambda x: x[0])
        by_group = {}
        for idx, prop in owned:
            tile = BOARD[idx]
            group = tile.get("group", tile["type"])
            by_group.setdefault(group, []).append((idx, tile, prop))

        total_value = 0
        for group, items in by_group.items():
            group_label = GROUP_VN_NAMES.get(group, group)
            full = owns_full_group(game, player["id"], group) if group not in ("railroad", "utility") else False
            lines = []
            for idx, tile, prop in items:
                total_value += property_value(game, idx)
                if tile["type"] == "property":
                    houses = prop.get("houses", 0)
                    house_str = "🏨 Khách sạn" if houses == 5 else (f"🏠×{houses}" if houses else "trống")
                    rent = calc_rent(game, idx)
                    lines.append(f"**{tile['name']}** — {house_str} — thuê hiện tại: {_m(rent)}")
                elif tile["type"] == "railroad":
                    rent = calc_rent(game, idx)
                    lines.append(f"**{tile['name']}** — thuê hiện tại: {_m(rent)}")
                else:
                    lines.append(f"**{tile['name']}** — thuê phụ thuộc xúc xắc (x4k/x10k)")
            title = f"{group_label}" + (" ✅ (đủ bộ)" if full else "")
            embed.add_field(name=title, value="\n".join(lines), inline=False)

        embed.add_field(name="💰 Tiền mặt", value=f"{_m(player['money'])}{MONEY_EMOJI}", inline=True)
        embed.add_field(name="🏘️ Tổng giá trị BĐS", value=f"{_m(total_value)}{MONEY_EMOJI}", inline=True)
        embed.add_field(name="💎 Tổng tài sản ròng", value=f"{_m(player['money'] + total_value)}{MONEY_EMOJI}", inline=True)
        return embed

    def build_leaderboard_embed(game):
        ranked = sorted(active_players(game), key=lambda p: net_worth(game, p), reverse=True)
        bankrupt = [p for p in game["players"] if p["bankrupt"]]
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅"]
        lines = []
        for i, p in enumerate(ranked):
            n_props = sum(1 for v in game["properties"].values() if v.get("owner") == p["id"])
            worth = net_worth(game, p)
            lines.append(f"{medals[i] if i < len(medals) else '▫️'} **{p['name']}** — {_m(worth)}{MONEY_EMOJI} tổng tài sản (💵{_m(p['money'])} + 🏠{n_props} đất)")
        for p in bankrupt:
            lines.append(f"💀 ~~{p['name']}~~ — Phá sản")
        embed = discord.Embed(
            title="🏆 BẢNG XẾP HẠNG TÀI SẢN RÒNG",
            description="\n".join(lines) if lines else "Chưa có ai chơi.",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Tài sản ròng = Tiền mặt + Giá trị đất (giá gốc + tiền đã xây nhà)")
        return embed

    # ── HELPERS ẢNH BÀN CỜ (chung + riêng) ────────────────────────────
    async def _gather_avatars(game):
        avatars = {}
        for p in game.get("players", []):
            url = p.get("avatar_url")
            if not url:
                continue
            av = await _get_avatar_image(url)
            if av:
                avatars[p["id"]] = av
        return avatars

    async def _board_file(game, highlight_id=None, filename="board.png"):
        if not PIL_OK:
            return None
        avatars = await _gather_avatars(game)
        buf = render_board_image(game, avatars=avatars, highlight_id=highlight_id)
        if buf is None:
            return None
        return discord.File(buf, filename=filename)

    async def _zoom_file(game, player, filename="zoom.png"):
        if not PIL_OK:
            return None
        avatars = await _gather_avatars(game)
        buf = render_zoom_image(game, player, avatars=avatars)
        if buf is None:
            return None
        return discord.File(buf, filename=filename)

    async def edit_with_board(interaction, game, view):
        """Cập nhật tin nhắn CHUNG trong kênh kèm ảnh bàn cờ mới nhất."""
        embed = build_game_embed(game)
        file = await _board_file(game, filename="board.png")
        if file:
            embed.set_image(url="attachment://board.png")
            await interaction.response.edit_message(embed=embed, view=view, attachments=[file])
        else:
            await interaction.response.edit_message(embed=embed, view=view)

    async def send_personal_board(interaction, game, player):
        """Gửi ẢNH BÀN CỜ RIÊNG (ephemeral) cho người vừa đi, kèm thông tin của họ."""
        if player.get("is_bot"):
            return
        file = await _board_file(game, highlight_id=player["id"], filename="board_private.png")
        if not file:
            return
        embed = discord.Embed(
            title=f"🎲 Bàn cờ của bạn — {player['name']}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="📍 Vị trí", value=BOARD[player['position']]['name'], inline=True)
        embed.add_field(name="💰 Túi tiền", value=f"{_m(player['money'])}{MONEY_EMOJI}", inline=True)
        n_props = sum(1 for v in game["properties"].values() if v.get("owner") == player["id"])
        embed.add_field(name="🏠 Số đất sở hữu", value=str(n_props), inline=True)
        embed.set_image(url="attachment://board_private.png")
        try:
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        except Exception as e:
            print(f"[MONO] send_personal_board error: {e}")

    async def refresh_message(channel, game):
        embed = build_game_embed(game) if game["status"] != "waiting" else build_lobby_embed(game)
        view = MonopolyLobbyView() if game["status"] == "waiting" else MonopolyGameView()
        file = None
        if game["status"] != "waiting":
            file = await _board_file(game, filename="board.png")
            if file:
                embed.set_image(url="attachment://board.png")
        try:
            if game.get("message_id"):
                try:
                    msg = await channel.fetch_message(int(game["message_id"]))
                    if file:
                        await msg.edit(embed=embed, view=view, attachments=[file])
                    else:
                        await msg.edit(embed=embed, view=view)
                    return
                except (discord.NotFound, discord.HTTPException):
                    pass
            if file:
                msg = await channel.send(embed=embed, view=view, file=file)
            else:
                msg = await channel.send(embed=embed, view=view)
            game["message_id"] = msg.id
            save_game(game)
        except Exception as e:
            print(f"[MONO] refresh_message error: {e}")

    # ── XỬ LÝ 1 LƯỢT CHO NGƯỜI/BOT (dùng chung) ───────────────────────
    def do_roll(game, player):
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        game["last_roll"] = [d1, d2]
        dice_sum = d1 + d2
        is_double = d1 == d2

        if player["in_jail"]:
            player["jail_turns"] += 1
            if is_double:
                player["in_jail"] = False
                player["jail_turns"] = 0
                add_log(game, f"🎲 **{player['name']}** đổ đôi {d1}-{d2}, thoát khỏi tù!")
                move_player(game, player, dice_sum)
                resolve_tile(game, player, dice_sum)
            elif player["jail_turns"] >= 3:
                fine = min(MONO_JAIL_FINE, max(0, player["money"]))
                pay(game, player, fine)
                player["in_jail"] = False
                player["jail_turns"] = 0
                add_log(game, f"⛓️ **{player['name']}** hết hạn tạm giam, nộp phạt {_m(fine)}{MONEY_EMOJI} và ra tù.")
                move_player(game, player, dice_sum)
                resolve_tile(game, player, dice_sum)
            else:
                add_log(game, f"🎲 **{player['name']}** đổ {d1}-{d2}, không phải đôi. Vẫn ở tù ({player['jail_turns']}/3).")
            game["has_rolled"] = True
            game["doubles_count"] = 0
            return

        move_player(game, player, dice_sum)
        resolve_tile(game, player, dice_sum)

        if is_double:
            game["doubles_count"] = game.get("doubles_count", 0) + 1
            if game["doubles_count"] >= 3:
                send_to_jail(game, player)
                game["has_rolled"] = True
                game["doubles_count"] = 0
            else:
                add_log(game, f"🎲 **{player['name']}** đổ đôi {d1}-{d2}! Được đi thêm lượt.")
                game["has_rolled"] = False  # được roll tiếp
        else:
            game["has_rolled"] = True
            game["doubles_count"] = 0

    def do_buy(game, player):
        idx = game.get("pending_buy")
        if idx is None:
            return False
        tile = BOARD[idx]
        if player["money"] < tile["price"]:
            return False
        player["money"] -= tile["price"]
        game["properties"][str(idx)]["owner"] = player["id"]
        add_log(game, f"🏷️ **{player['name']}** mua **{tile['name']}** giá {_m(tile['price'])}{MONEY_EMOJI}")
        game["pending_buy"] = None
        return True

    def bot_take_turn(game):
        """AI đơn giản: roll -> auto mua nếu đủ tiền dư dả -> auto xây nhà nếu dư tiền -> kết thúc lượt."""
        bot_p = current_player(game)
        if bot_p["in_jail"]:
            if bot_p["money"] >= MONO_JAIL_FINE * 3:
                pay(game, bot_p, MONO_JAIL_FINE)
                bot_p["in_jail"] = False
                bot_p["jail_turns"] = 0
                add_log(game, f"🤖 **{bot_p['name']}** trả tiền ra tù.")
        do_roll(game, bot_p)
        safety = 0
        while not game["has_rolled"] and safety < 5:
            do_roll(game, bot_p)
            safety += 1

        if game.get("pending_buy") is not None:
            idx = game["pending_buy"]
            tile = BOARD[idx]
            if bot_p["money"] - tile["price"] >= 200_000:
                do_buy(game, bot_p)
            else:
                game["pending_buy"] = None

        if bot_p["money"] >= 500_000:
            for group, idxs in GROUP_INDICES.items():
                if group in ("railroad", "utility"):
                    continue
                if owns_full_group(game, bot_p["id"], group):
                    for i in idxs:
                        prop = game["properties"][str(i)]
                        tile = BOARD[i]
                        if prop["houses"] < 5 and bot_p["money"] - tile["house_cost"] >= 300_000:
                            bot_p["money"] -= tile["house_cost"]
                            prop["houses"] += 1
                            add_log(game, f"🤖 **{bot_p['name']}** xây nhà tại **{tile['name']}**")
                            break

        if not check_winner(game):
            advance_turn(game)

    # ── PERSISTENT VIEWS (custom_id CỐ ĐỊNH — SỐNG VĨNH VIỄN) ─────────
    class MonopolyLobbyView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Tham Gia", emoji="🙋", style=discord.ButtonStyle.success, custom_id="mono_join")
        async def btn_join(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "waiting":
                    return await interaction.response.send_message("⚠️ Không có bàn nào đang chờ ở đây! Dùng `k tybphu tao` để tạo mới.", ephemeral=True)
                if get_player(game, interaction.user.id):
                    return await interaction.response.send_message("✅ Bạn đã trong bàn rồi!", ephemeral=True)
                if game["mode"] == "bot":
                    human_count = sum(1 for p in game["players"] if not p["is_bot"])
                    if human_count >= 1:
                        return await interaction.response.send_message("⚠️ Bàn Đấu Bot chỉ dành cho 1 người chơi!", ephemeral=True)
                if len(game["players"]) >= MONO_MAX_PLAYERS:
                    return await interaction.response.send_message("⚠️ Bàn đã đầy!", ephemeral=True)
                game["players"].append({
                    "id": str(interaction.user.id), "name": interaction.user.display_name,
                    "money": MONO_START_MONEY, "position": 0, "in_jail": False, "jail_turns": 0,
                    "bankrupt": False, "is_bot": False, "get_out_cards": 0,
                    "avatar_url": str(interaction.user.display_avatar.url),
                })
                add_log(game, f"🙋 **{interaction.user.display_name}** đã tham gia bàn!")
                save_game(game)
                await interaction.response.edit_message(embed=build_lobby_embed(game), view=self)

        @discord.ui.button(label="Bắt Đầu", emoji="▶️", style=discord.ButtonStyle.primary, custom_id="mono_start")
        async def btn_start(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "waiting":
                    return await interaction.response.send_message("⚠️ Không có bàn nào đang chờ!", ephemeral=True)
                if str(interaction.user.id) != game["host_id"]:
                    return await interaction.response.send_message("⛔ Chỉ chủ bàn mới được bắt đầu!", ephemeral=True)
                if game["mode"] == "pvp" and len(game["players"]) < 2:
                    return await interaction.response.send_message("⚠️ Cần ít nhất 2 người để bắt đầu chế độ Nhiều Người!", ephemeral=True)
                ensure_property_slots(game)
                game["status"] = "playing"
                add_log(game, "🚦 Ván chơi bắt đầu! Chúc may mắn!")
                save_game(game)
                await edit_with_board(interaction, game, MonopolyGameView())
                await maybe_trigger_bot_turn(interaction.channel, game)

        @discord.ui.button(label="Hủy Bàn", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="mono_cancel_lobby")
        async def btn_cancel(self, interaction: discord.Interaction, button):
            game = load_game(interaction.channel.id)
            if not game:
                return await interaction.response.send_message("⚠️ Không có bàn nào!", ephemeral=True)
            if str(interaction.user.id) != game["host_id"] and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("⛔ Chỉ chủ bàn/Admin mới hủy được!", ephemeral=True)
            delete_game(interaction.channel.id)
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(
                embed=discord.Embed(description="🗑️ Đã hủy bàn cờ. Dùng `k tybphu tao` để tạo bàn mới.", color=discord.Color.dark_grey()),
                view=self
            )

    class MonopolyGameView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        def _check_turn(self, game, user_id):
            cur = current_player(game)
            return (not cur["is_bot"]) and cur["id"] == str(user_id)

        # ── HÀNG 1: hành động chính trong lượt ──────────────────────
        @discord.ui.button(label="Đổ Xúc Xắc", emoji="🎲", style=discord.ButtonStyle.success, custom_id="mono_roll", row=0)
        async def btn_roll(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "playing":
                    return await interaction.response.send_message("⚠️ Ván chơi không tồn tại hoặc đã kết thúc!", ephemeral=True)
                if not self._check_turn(game, interaction.user.id):
                    return await interaction.response.send_message("⚠️ Chưa tới lượt bạn!", ephemeral=True)
                if game.get("has_rolled"):
                    return await interaction.response.send_message("⚠️ Bạn đã đổ xúc xắc rồi, hãy Mua Đất / Kết Thúc Lượt!", ephemeral=True)
                if game.get("pending_buy") is not None:
                    return await interaction.response.send_message("⚠️ Hãy quyết định Mua Đất hoặc Kết Thúc Lượt trước!", ephemeral=True)
                cur = current_player(game)
                do_roll(game, cur)
                check_winner(game)
                save_game(game)
                await edit_with_board(interaction, game, self)
                await send_personal_board(interaction, game, cur)
                if game["status"] == "playing":
                    await maybe_trigger_bot_turn(interaction.channel, game)

        @discord.ui.button(label="Mua Đất", emoji="💰", style=discord.ButtonStyle.primary, custom_id="mono_buy", row=0)
        async def btn_buy(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "playing":
                    return await interaction.response.send_message("⚠️ Ván chơi không hợp lệ!", ephemeral=True)
                if not self._check_turn(game, interaction.user.id):
                    return await interaction.response.send_message("⚠️ Chưa tới lượt bạn!", ephemeral=True)
                cur = current_player(game)
                if not do_buy(game, cur):
                    return await interaction.response.send_message("⚠️ Không có gì để mua hoặc không đủ tiền!", ephemeral=True)
                save_game(game)
                await edit_with_board(interaction, game, self)

        @discord.ui.button(label="Trả Tù", emoji="💳", style=discord.ButtonStyle.secondary, custom_id="mono_pay_jail", row=0)
        async def btn_pay_jail(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "playing":
                    return await interaction.response.send_message("⚠️ Ván chơi không hợp lệ!", ephemeral=True)
                if not self._check_turn(game, interaction.user.id):
                    return await interaction.response.send_message("⚠️ Chưa tới lượt bạn!", ephemeral=True)
                cur = current_player(game)
                if not cur["in_jail"]:
                    return await interaction.response.send_message("⚠️ Bạn không ở trong tù!", ephemeral=True)
                if cur["money"] < MONO_JAIL_FINE:
                    return await interaction.response.send_message("⚠️ Không đủ tiền nộp phạt!", ephemeral=True)
                cur["money"] -= MONO_JAIL_FINE
                cur["in_jail"] = False
                cur["jail_turns"] = 0
                add_log(game, f"💳 **{cur['name']}** trả {_m(MONO_JAIL_FINE)}{MONEY_EMOJI} ra tù.")
                save_game(game)
                await edit_with_board(interaction, game, self)

        @discord.ui.button(label="Kết Thúc Lượt", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="mono_end_turn", row=0)
        async def btn_end_turn(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "playing":
                    return await interaction.response.send_message("⚠️ Ván chơi không hợp lệ!", ephemeral=True)
                if not self._check_turn(game, interaction.user.id):
                    return await interaction.response.send_message("⚠️ Chưa tới lượt bạn!", ephemeral=True)
                if not game.get("has_rolled"):
                    return await interaction.response.send_message("⚠️ Bạn cần đổ xúc xắc trước!", ephemeral=True)
                game["pending_buy"] = None
                if not check_winner(game):
                    advance_turn(game)
                save_game(game)
                await edit_with_board(interaction, game, self)
                if game["status"] == "playing":
                    await maybe_trigger_bot_turn(interaction.channel, game)

        # ── HÀNG 2: quản lý tài sản & rời bàn ────────────────────────
        @discord.ui.button(label="Xây Nhà", emoji="🏠", style=discord.ButtonStyle.success, custom_id="mono_build", row=1)
        async def btn_build(self, interaction: discord.Interaction, button):
            game = load_game(interaction.channel.id)
            if not game or game["status"] != "playing":
                return await interaction.response.send_message("⚠️ Ván chơi không hợp lệ!", ephemeral=True)
            cur = get_player(game, interaction.user.id)
            if not cur or cur["bankrupt"]:
                return await interaction.response.send_message("⚠️ Bạn không trong ván này!", ephemeral=True)

            options = []
            for group, idxs in GROUP_INDICES.items():
                if group in ("railroad", "utility"):
                    continue
                if not owns_full_group(game, cur["id"], group):
                    continue
                for i in idxs:
                    prop = game["properties"][str(i)]
                    tile = BOARD[i]
                    if prop["houses"] < 5:
                        label = f"{tile['name']} (Nhà {prop['houses']}→{prop['houses']+1})"
                        options.append(discord.SelectOption(
                            label=label[:100],
                            description=f"Giá: {_m(tile['house_cost'])}{MONEY_EMOJI}",
                            value=str(i)
                        ))
            if not options:
                return await interaction.response.send_message("⚠️ Bạn chưa sở hữu trọn bộ nhóm màu nào để xây nhà!", ephemeral=True)

            select = discord.ui.Select(placeholder="Chọn ô đất để xây nhà...", options=options[:25])

            async def on_select(inter2: discord.Interaction):
                async with get_lock(inter2.channel.id):
                    g2 = load_game(inter2.channel.id)
                    p2 = get_player(g2, inter2.user.id)
                    idx = int(select.values[0])
                    tile = BOARD[idx]
                    prop = g2["properties"][str(idx)]
                    if p2["money"] < tile["house_cost"]:
                        return await inter2.response.send_message("⚠️ Không đủ tiền!", ephemeral=True)
                    p2["money"] -= tile["house_cost"]
                    prop["houses"] += 1
                    add_log(g2, f"🏠 **{p2['name']}** xây nhà tại **{tile['name']}** (cấp {prop['houses']})")
                    save_game(g2)
                    await inter2.response.send_message(f"✅ Đã xây nhà tại **{tile['name']}**!", ephemeral=True)
                    await refresh_message(inter2.channel, g2)

            select.callback = on_select
            v = discord.ui.View(timeout=60)
            v.add_item(select)
            await interaction.response.send_message("Chọn ô đất để xây nhà:", view=v, ephemeral=True)

        @discord.ui.button(label="Rời Bàn", emoji="🚪", style=discord.ButtonStyle.danger, custom_id="mono_leave", row=1)
        async def btn_leave(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game:
                    return await interaction.response.send_message("⚠️ Không có bàn nào!", ephemeral=True)
                p = get_player(game, interaction.user.id)
                if not p:
                    return await interaction.response.send_message("⚠️ Bạn không trong bàn này!", ephemeral=True)
                if game["status"] == "waiting":
                    game["players"] = [x for x in game["players"] if x["id"] != str(interaction.user.id)]
                    if not game["players"] or str(interaction.user.id) == game["host_id"]:
                        delete_game(interaction.channel.id)
                        for c in self.children:
                            c.disabled = True
                        return await interaction.response.edit_message(
                            embed=discord.Embed(description="🚪 Chủ bàn đã rời — bàn cờ bị hủy.", color=discord.Color.dark_grey()),
                            view=self
                        )
                    save_game(game)
                    return await interaction.response.edit_message(embed=build_lobby_embed(game), view=MonopolyLobbyView())
                else:
                    handle_bankrupt(game, p, None)
                    add_log(game, f"🚪 **{p['name']}** đã rời khỏi ván chơi.")
                    is_cur = current_player(game)["id"] == p["id"]
                    if not check_winner(game) and is_cur:
                        advance_turn(game)
                    save_game(game)
                    await edit_with_board(interaction, game, self)
                    if game["status"] == "playing":
                        await maybe_trigger_bot_turn(interaction.channel, game)

        # ── HÀNG 3: thông tin / tiện ích (xem được bất cứ lúc nào) ───
        @discord.ui.button(label="Vị Trí Của Tôi", emoji="📍", style=discord.ButtonStyle.primary, custom_id="mono_myloc", row=2)
        async def btn_my_location(self, interaction: discord.Interaction, button):
            game = load_game(interaction.channel.id)
            if not game or game["status"] not in ("playing", "finished"):
                return await interaction.response.send_message("⚠️ Ván chơi chưa bắt đầu!", ephemeral=True)
            p = get_player(game, interaction.user.id)
            if not p:
                return await interaction.response.send_message("⚠️ Bạn không trong ván này!", ephemeral=True)
            await interaction.response.defer(ephemeral=True, thinking=True)
            file = await _zoom_file(game, p, filename="zoom.png")
            if not file:
                return await interaction.followup.send("⚠️ Không thể tạo ảnh lúc này, thử lại sau!", ephemeral=True)
            embed = discord.Embed(
                title=f"📍 Vị trí hiện tại — {p['name']}",
                description=f"Bạn đang ở ô **{BOARD[p['position']]['name']}** (ô số {p['position']}).",
                color=discord.Color.blurple()
            )
            embed.set_image(url="attachment://zoom.png")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)

        @discord.ui.button(label="Tài Sản Của Tôi", emoji="📋", style=discord.ButtonStyle.secondary, custom_id="mono_myprops", row=2)
        async def btn_my_properties(self, interaction: discord.Interaction, button):
            game = load_game(interaction.channel.id)
            if not game or game["status"] not in ("playing", "finished"):
                return await interaction.response.send_message("⚠️ Ván chơi chưa bắt đầu!", ephemeral=True)
            p = get_player(game, interaction.user.id)
            if not p:
                return await interaction.response.send_message("⚠️ Bạn không trong ván này!", ephemeral=True)
            embed = build_my_properties_embed(game, p)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label="Bảng Xếp Hạng", emoji="🏆", style=discord.ButtonStyle.secondary, custom_id="mono_leaderboard", row=2)
        async def btn_leaderboard(self, interaction: discord.Interaction, button):
            game = load_game(interaction.channel.id)
            if not game or game["status"] not in ("playing", "finished"):
                return await interaction.response.send_message("⚠️ Ván chơi chưa bắt đầu!", ephemeral=True)
            embed = build_leaderboard_embed(game)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label="Chơi Lại", emoji="🔄", style=discord.ButtonStyle.success, custom_id="mono_replay", row=3)
        async def btn_replay(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "finished":
                    return await interaction.response.send_message("⚠️ Ván chơi chưa kết thúc!", ephemeral=True)
                new_g = new_game(interaction.channel.id, interaction.guild.id, interaction.user.id, interaction.user.display_name, game["mode"],
                                  host_avatar=str(interaction.user.display_avatar.url))
                new_g["message_id"] = game.get("message_id")
                save_game(new_g)
                await interaction.response.edit_message(embed=build_lobby_embed(new_g), view=MonopolyLobbyView(), attachments=[])

    async def maybe_trigger_bot_turn(channel, game):
        """Nếu tới lượt bot, cho bot chơi ngay (loop nhỏ, không cần đợi task nền)."""
        safety = 0
        while game["status"] == "playing" and current_player(game)["is_bot"] and safety < 20:
            await asyncio.sleep(1.2)
            bot_take_turn(game)
            safety += 1
        save_game(game)
        await refresh_message(channel, game)

    # ── ĐĂNG KÝ VIEW VĨNH VIỄN (chạy 1 lần lúc bot sẵn sàng) ──────────
    _monopoly_views_registered = {"done": False}

    @bot.listen('on_ready')
    async def _monopoly_register_persistent_views():
        if _monopoly_views_registered["done"]:
            return
        _monopoly_views_registered["done"] = True
        bot.add_view(MonopolyLobbyView())
        bot.add_view(MonopolyGameView())
        print(">>> [MONOPOLY] Đã đăng ký View vĩnh viễn cho Cờ Tỷ Phú (giao diện v2).")

    # ── COMMANDS ───────────────────────────────────────────────────────
    @bot.group(invoke_without_command=True, aliases=['monopoly', 'cotyphu', 'cty_phu'])
    async def tybphu(ctx):
        """Cờ Tỷ Phú — bàn cờ vĩnh viễn tại kênh này."""
        game = load_game(ctx.channel.id)
        if not game:
            embed = discord.Embed(
                title="🎲 CỜ TỶ PHÚ",
                description=(
                    "Chưa có bàn nào ở kênh này!\n\n"
                    "`k tybphu tao pvp` — Tạo bàn chơi với người khác (nhiều người)\n"
                    "`k tybphu tao bot` — Tạo bàn chơi với Bot 🤖"
                ),
                color=discord.Color.gold()
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if game["status"] == "waiting":
            await ctx.reply(embed=build_lobby_embed(game), view=MonopolyLobbyView(), mention_author=False)
        else:
            embed = build_game_embed(game)
            file = await _board_file(game, filename="board.png")
            if file:
                embed.set_image(url="attachment://board.png")
                await ctx.reply(embed=embed, view=MonopolyGameView(), file=file, mention_author=False)
            else:
                await ctx.reply(embed=embed, view=MonopolyGameView(), mention_author=False)

    @tybphu.command(name="tao", aliases=["create", "new"])
    async def tybphu_tao(ctx, mode: str = "pvp"):
        mode = mode.lower()
        if mode not in ("pvp", "bot"):
            return await ctx.reply("⚠️ Chế độ chỉ gồm `pvp` (nhiều người) hoặc `bot` (đấu máy)!", mention_author=False)

        existing = load_game(ctx.channel.id)
        if existing and existing["status"] != "finished":
            return await ctx.reply(
                embed=discord.Embed(description="⚠️ Kênh này đã có bàn cờ đang hoạt động! Gõ `k tybphu` để xem, hoặc `k tybphu huy` để hủy (chủ bàn/Admin).", color=discord.Color.orange()),
                mention_author=False
            )

        game = new_game(ctx.channel.id, ctx.guild.id, ctx.author.id, ctx.author.display_name, mode,
                        host_avatar=str(ctx.author.display_avatar.url))
        save_game(game)
        msg = await ctx.reply(embed=build_lobby_embed(game), view=MonopolyLobbyView(), mention_author=False)
        game["message_id"] = msg.id
        save_game(game)

    @tybphu.command(name="huy", aliases=["cancel", "xoa"])
    async def tybphu_huy(ctx):
        game = load_game(ctx.channel.id)
        if not game:
            return await ctx.reply("⚠️ Không có bàn nào ở kênh này!", mention_author=False)
        if str(ctx.author.id) != game["host_id"] and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("⛔ Chỉ chủ bàn hoặc Admin mới hủy được!", mention_author=False)
        delete_game(ctx.channel.id)
        await ctx.reply(embed=discord.Embed(description="🗑️ Đã hủy bàn cờ tại kênh này.", color=discord.Color.dark_grey()), mention_author=False)

    @tybphu.command(name="taisan", aliases=["properties", "myprops"])
    async def tybphu_taisan(ctx):
        """Xem nhanh tài sản của bạn bằng lệnh gõ (không cần bấm nút)."""
        game = load_game(ctx.channel.id)
        if not game or game["status"] not in ("playing", "finished"):
            return await ctx.reply("⚠️ Chưa có ván nào đang diễn ra ở kênh này!", mention_author=False)
        p = get_player(game, ctx.author.id)
        if not p:
            return await ctx.reply("⚠️ Bạn không trong ván này!", mention_author=False)
        await ctx.reply(embed=build_my_properties_embed(game, p), mention_author=False)

    @tybphu.command(name="bxh", aliases=["leaderboard", "rank"])
    async def tybphu_bxh(ctx):
        """Xem nhanh bảng xếp hạng bằng lệnh gõ (không cần bấm nút)."""
        game = load_game(ctx.channel.id)
        if not game or game["status"] not in ("playing", "finished"):
            return await ctx.reply("⚠️ Chưa có ván nào đang diễn ra ở kênh này!", mention_author=False)
        await ctx.reply(embed=build_leaderboard_embed(game), mention_author=False)

    @tybphu.command(name="luat", aliases=["rules", "help"])
    async def tybphu_luat(ctx):
        embed = discord.Embed(
            title="📖 LUẬT CHƠI CỜ TỶ PHÚ",
            description=(
                "🎲 Mỗi lượt đổ 2 xúc xắc, di chuyển quanh bàn cờ 40 ô.\n"
                "🏁 Đi qua/dừng tại Xuất Phát nhận **200.000**.\n"
                "🏷️ Dừng ở đất trống → có thể **Mua**. Đất có chủ → trả tiền thuê.\n"
                "🏠 Sở hữu trọn 1 nhóm màu → được **Xây Nhà** tăng tiền thuê (tối đa 4 nhà + 1 khách sạn).\n"
                "🚉 Ga tàu & 🏭 Công ty tiện ích thu tiền thuê theo số lượng sở hữu.\n"
                "❓ Ô Cơ Hội cho hiệu ứng ngẫu nhiên (thưởng/phạt/di chuyển...).\n"
                "🚨 Dính \"Đi Tù\" hoặc đổ đôi 3 lần liên tiếp → vào tù. Ra tù bằng cách trả 50.000, đổ đôi, hoặc dùng thẻ Miễn Tù.\n"
                "💀 Hết tiền (âm) → phá sản, loại khỏi ván. Người cuối cùng còn trụ lại → **THẮNG CUỘC**!\n\n"
                "🤖 Chế độ đấu Bot: máy tự động roll/mua/xây khi tới lượt.\n"
                "🖼️ Sau mỗi lượt đi, bàn cờ CHUNG trong kênh sẽ cập nhật ảnh, và bạn còn được gửi RIÊNG "
                "1 ảnh bàn cờ (chỉ mình bạn thấy) khoanh vùng đỏ đúng vị trí quân cờ của bạn.\n"
                "📍 Bấm **Vị Trí Của Tôi** bất cứ lúc nào để xem ảnh ZOOM cận cảnh ô bạn đang đứng kèm "
                "thông tin chi tiết (giá, tiền thuê, chủ sở hữu...).\n"
                "📋 Bấm **Tài Sản Của Tôi** để xem toàn bộ đất bạn sở hữu, số nhà đã xây, tiền thuê hiện tại.\n"
                "🏆 Bấm **Bảng Xếp Hạng** để so tài sản ròng (tiền mặt + giá trị BĐS) với người khác.\n"
                "♾️ Bàn cờ không bao giờ hết hạn — chơi xong bấm **Chơi Lại** để bắt đầu ván mới ngay tại đây!"
            ),
            color=discord.Color.blue()
        )
        await ctx.reply(embed=embed, mention_author=False)
