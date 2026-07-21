# =====================================================================
# 🎲 CỜ TỶ PHÚ (MONOPOLY) — MODULE RIÊNG, GHÉP VÀO bot.py
# =====================================================================
# CÁCH CÀI ĐẶT:
# 1) Đặt file này (monopoly.py) cùng thư mục với bot.py.
# 2) Cài thêm thư viện vẽ ảnh (bắt buộc cho bản này):
#        pip install Pillow
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
#     truyền, minigame vẫn chạy bình thường, chỉ là không có thưởng thật.)
#
# ĐẶC ĐIỂM:
# - Mỗi kênh Discord có TỐI ĐA 1 bàn cờ đang hoạt động (lưu trong Mongo,
#   collection "monopoly_games", key = channel_id).
# - Bàn cờ KHÔNG BAO GIỜ HẾT HẠN: dùng discord.ui.View(timeout=None) với
#   custom_id CỐ ĐỊNH (không nhúng ID vào custom_id), đăng ký 1 lần duy
#   nhất bằng bot.add_view() lúc bot khởi động (on_ready). Nhờ vậy nút
#   bấm hoạt động vĩnh viễn, kể cả sau khi bot restart, khỏi cần gia hạn.
# - 2 chế độ: `pvp` (chơi với người) và `bot` (chơi với máy — AI tự roll,
#   tự mua đất, tự xây nhà mỗi khi tới lượt).
# - Hỗ trợ nhiều người tham gia cùng lúc (tối đa 6 người/bàn).
# - 🖼️ MỚI: Bàn cờ được VẼ THÀNH ẢNH giống bàn cờ ngoài đời (hình vuông,
#   40 ô quanh viền, quân cờ màu cho từng người). Sau mỗi lượt đi:
#     • Ảnh bàn cờ CHUNG được cập nhật trong tin nhắn ở kênh.
#     • Người vừa đi được gửi THÊM 1 ảnh bàn cờ RIÊNG (ephemeral, chỉ họ
#       thấy) kèm thông tin vị trí/túi tiền của chính họ cho dễ theo dõi.
# =====================================================================

import discord
from discord.ext import commands, tasks
import random
import asyncio
import io
import re
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[MONO] ⚠️ Chưa cài Pillow! Chạy: pip install Pillow  (ảnh bàn cờ sẽ không hoạt động)")

MONO_START_MONEY   = 1_500_000
MONO_GO_SALARY     = 200_000
MONO_JAIL_FINE     = 50_000
MONO_MAX_PLAYERS   = 6
MONO_JAIL_IDX      = 10
MONO_GOTOJAIL_IDX  = 30
MONO_FREEPARK_IDX  = 20

MONEY_EMOJI = "<:Money_kyo:1528673432613552188>"

GROUP_COLORS = {
    "brown":     (139, 69, 19),
    "lightblue": (135, 206, 235),
    "pink":      (255, 105, 180),
    "orange":    (255, 165, 0),
    "red":       (220, 20, 60),
    "yellow":    (255, 199, 0),
    "green":     (34, 139, 34),
    "blue":      (30, 60, 200),
    "railroad":  (60, 60, 60),
    "utility":   (120, 120, 120),
}
PLAYER_COLORS = [
    (231, 76, 60), (52, 152, 219), (46, 204, 113),
    (241, 196, 15), (155, 89, 182), (26, 188, 156),
]

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F000-\U0001FFFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U0000FE00-\U0000FE0F"
    "\U00002B00-\U00002BFF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(s):
    return EMOJI_PATTERN.sub("", s).strip()


def _m(n):
    return f"{n:,}".replace(",", ".")


# ── DỮ LIỆU BÀN CỜ (40 Ô, LẤY THEO TỈ LỆ CỜ TỶ PHÚ CỔ ĐIỂN) ───────────
def _build_board():
    board = [None] * 40
    board[0]  = {"name": "🚀 Xuất Phát", "type": "go"}
    board[10] = {"name": "🚔 Nhà Tù (Thăm Quan)", "type": "jail"}
    board[20] = {"name": "🅿️ Công Viên Tự Do", "type": "free_parking"}
    board[30] = {"name": "🚨 Đi Tù!", "type": "go_to_jail"}

    for i in (2, 7, 17, 22, 36):
        board[i] = {"name": "❓ Cơ Hội", "type": "chance"}
    board[4]  = {"name": "🧾 Thuế Thu Nhập", "type": "tax", "amount": 200_000}
    board[33] = {"name": "🧾 Thuế Tài Sản", "type": "tax", "amount": 100_000}
    board[38] = {"name": "🧾 Thuế Xa Xỉ", "type": "tax", "amount": 75_000}

    for i, name in [(5, "🚉 Ga Sài Gòn"), (15, "🚉 Ga Hà Nội"), (25, "🚉 Ga Đà Nẵng"), (35, "🚉 Ga Nha Trang")]:
        board[i] = {"name": name, "type": "railroad", "price": 200_000, "group": "railroad"}

    for i, name in [(12, "⚡ Cty Điện Lực"), (28, "🚰 Cty Cấp Nước")]:
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
# 🖼️ VẼ ẢNH BÀN CỜ (giống bàn cờ Tỷ Phú ngoài đời — hình vuông, 40 ô quanh viền)
# =====================================================================
_FONT_CACHE = {}


def _load_font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    font = None
    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _cell_rect(i, cell):
    """Trả về (x0,y0,x1,y1) của ô thứ i trên lưới 11x11 (giống layout bàn cờ Tỷ Phú thật)."""
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


def _wrap(text, max_chars=9):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def render_board_image(game, highlight_id=None):
    """Vẽ toàn bộ bàn cờ ra 1 ảnh PNG (BytesIO). highlight_id: id người chơi cần
    khoanh vùng nổi bật (dùng cho ảnh riêng gửi ephemeral)."""
    if not PIL_OK:
        return None

    SIZE = 950
    CELL = SIZE // 11
    img = Image.new("RGB", (SIZE, SIZE), (238, 246, 236))
    draw = ImageDraw.Draw(img)
    f_tiny = _load_font(11)
    f_small = _load_font(12, bold=True)
    f_title = _load_font(20, bold=True)
    f_mid = _load_font(13, bold=True)

    # tâm bàn cờ
    draw.rectangle([CELL, CELL, SIZE - CELL, SIZE - CELL], fill=(223, 240, 216), outline=(40, 40, 40), width=3)
    draw.text((SIZE // 2, SIZE // 2 - 10), "CỜ TỶ PHÚ", font=f_title, fill=(44, 62, 80), anchor="mm")

    cur_idx = game["turn_index"] % len(game["players"]) if game.get("players") else -1
    cur_id = game["players"][cur_idx]["id"] if cur_idx >= 0 else None

    for i in range(40):
        tile = BOARD[i]
        x0, y0, x1, y1 = _cell_rect(i, CELL)
        is_corner = i in (0, 10, 20, 30)

        bg = (255, 255, 255)
        draw.rectangle([x0, y0, x1, y1], outline=(30, 30, 30), width=1, fill=bg)

        band_color = None
        if tile["type"] in OWNABLE_TYPES:
            band_color = GROUP_COLORS.get(tile["group"], (150, 150, 150))
        elif tile["type"] == "go":
            band_color = (198, 40, 40)
        elif tile["type"] == "jail":
            band_color = (100, 100, 100)
        elif tile["type"] == "free_parking":
            band_color = (39, 174, 96)
        elif tile["type"] == "go_to_jail":
            band_color = (198, 40, 40)
        elif tile["type"] == "chance":
            band_color = (243, 156, 18)
        elif tile["type"] == "tax":
            band_color = (142, 68, 173)

        if band_color and not is_corner:
            band_h = 16 if (i <= 10 or (21 <= i <= 30)) else None
            # dải màu luôn nằm ở mép hướng vào tâm bàn cờ
            if i <= 10:  # hàng dưới -> dải màu ở trên ô
                draw.rectangle([x0, y0, x1, y0 + 14], fill=band_color)
            elif i <= 20:  # cột trái -> dải màu ở bên phải ô
                draw.rectangle([x1 - 14, y0, x1, y1], fill=band_color)
            elif i <= 30:  # hàng trên -> dải màu ở dưới ô
                draw.rectangle([x0, y1 - 14, x1, y1], fill=band_color)
            else:  # cột phải -> dải màu ở bên trái ô
                draw.rectangle([x0, y0, x0 + 14, y1], fill=band_color)
        elif is_corner and band_color:
            draw.rectangle([x0, y0, x1, y1], fill=tuple(min(255, c + 60) for c in band_color))

        # tên ô
        clean_name = _strip_emoji(tile["name"]) or tile["name"]
        lines = _wrap(clean_name, 8 if not is_corner else 10)
        ty = (y0 + y1) // 2 - (len(lines) * 6)
        if tile["type"] in OWNABLE_TYPES and not is_corner:
            ty = y0 + 24
        for ln in lines:
            draw.text(((x0 + x1) // 2, ty), ln, font=f_tiny, fill=(20, 20, 20), anchor="mm")
            ty += 11

        # giá
        if tile["type"] in OWNABLE_TYPES:
            draw.text(((x0 + x1) // 2, y1 - 16), f"{tile['price']//1000}k", font=f_tiny, fill=(60, 60, 60), anchor="mm")

        # chủ sở hữu + nhà/khách sạn
        prop = game.get("properties", {}).get(str(i))
        if prop and prop.get("owner"):
            owner_p = next((p for p in game["players"] if p["id"] == prop["owner"]), None)
            if owner_p:
                oc_idx = game["players"].index(owner_p) % len(PLAYER_COLORS)
                oc = PLAYER_COLORS[oc_idx]
                draw.rectangle([x0 + 2, y0 + 2, x0 + 10, y0 + 10], fill=oc, outline=(0, 0, 0))
                houses = prop.get("houses", 0)
                if houses == 5:
                    draw.rectangle([x1 - 26, y1 - 30, x1 - 4, y1 - 20], fill=(200, 30, 30))
                    draw.text((x1 - 15, y1 - 25), "H", font=f_tiny, fill=(255, 255, 255), anchor="mm")
                elif houses > 0:
                    for h in range(houses):
                        hx = x1 - 8 - h * 8
                        draw.rectangle([hx - 3, y1 - 28, hx + 3, y1 - 22], fill=(0, 150, 0))

        # viền đỏ cho ô đang có lượt hiện tại (tuỳ chọn nhẹ, chỉ viền quân cờ ở dưới)

    # quân cờ người chơi
    for idx, p in enumerate(game.get("players", [])):
        if p.get("bankrupt"):
            continue
        x0, y0, x1, y1 = _cell_rect(p["position"], CELL)
        same = [pp for pp in game["players"] if not pp.get("bankrupt") and pp["position"] == p["position"]]
        n = len(same)
        pos_in_group = same.index(p)
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        if n > 1:
            spread = min(CELL // 2 - 12, 16)
            cx += int(((pos_in_group / max(n - 1, 1)) - 0.5) * 2 * spread)
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        r = 11 if p["id"] == cur_id else 9
        outline_c = (255, 215, 0) if p["id"] == cur_id else (0, 0, 0)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=outline_c, width=2 if p["id"] == cur_id else 1)
        if highlight_id and p["id"] == highlight_id:
            draw.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], outline=(255, 0, 0), width=2)

    # bảng chú thích người chơi ở giữa bàn cờ
    legend_y = SIZE // 2 + 20
    for idx, p in enumerate(game.get("players", [])):
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        lx = SIZE // 2 - 140 + (idx % 2) * 150
        ly = legend_y + (idx // 2) * 24
        draw.ellipse([lx, ly, lx + 14, ly + 14], fill=color, outline=(0, 0, 0))
        status = "💀" if p.get("bankrupt") else _m(p["money"])
        draw.text((lx + 20, ly + 7), f"{p['name'][:12]}: {status}", font=f_mid, fill=(30, 30, 30), anchor="lm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
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

    def new_game(channel_id, guild_id, host_id, host_name, mode):
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

    def calc_rent(game, tile_idx, dice_sum):
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
        embed.set_footer(text=f"Bàn cờ vĩnh viễn tại kênh này | Chế độ: {'🤖 Bot' if game['mode']=='bot' else '👥 PvP'}")
        return embed

    # ── HELPERS ẢNH BÀN CỜ (chung + riêng) ────────────────────────────
    def _board_file(game, highlight_id=None, filename="board.png"):
        if not PIL_OK:
            return None
        buf = render_board_image(game, highlight_id=highlight_id)
        if buf is None:
            return None
        return discord.File(buf, filename=filename)

    async def edit_with_board(interaction, game, view):
        """Cập nhật tin nhắn CHUNG trong kênh kèm ảnh bàn cờ mới nhất."""
        embed = build_game_embed(game)
        file = _board_file(game, filename="board.png")
        if file:
            embed.set_image(url="attachment://board.png")
            await interaction.response.edit_message(embed=embed, view=view, attachments=[file])
        else:
            await interaction.response.edit_message(embed=embed, view=view)

    async def send_personal_board(interaction, game, player):
        """Gửi ẢNH BÀN CỜ RIÊNG (ephemeral) cho người vừa đi, kèm thông tin của họ."""
        if player.get("is_bot"):
            return
        file = _board_file(game, highlight_id=player["id"], filename="board_private.png")
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
            file = _board_file(game, filename="board.png")
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
        # nếu được roll thêm (đôi) thì roll tiếp luôn (giới hạn phòng loop vô hạn)
        safety = 0
        while not game["has_rolled"] and safety < 5:
            do_roll(game, bot_p)
            safety += 1

        if game.get("pending_buy") is not None:
            idx = game["pending_buy"]
            tile = BOARD[idx]
            # Bot giữ lại tối thiểu 200k, mua nếu dư dả
            if bot_p["money"] - tile["price"] >= 200_000:
                do_buy(game, bot_p)
            else:
                game["pending_buy"] = None

        # Bot thử xây nhà ngẫu nhiên trên nhóm đã sở hữu trọn nếu dư tiền nhiều
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

        @discord.ui.button(label="Kết Thúc Lượt", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="mono_end_turn", row=1)
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

        @discord.ui.button(label="Chơi Lại", emoji="🔄", style=discord.ButtonStyle.success, custom_id="mono_replay", row=2)
        async def btn_replay(self, interaction: discord.Interaction, button):
            async with get_lock(interaction.channel.id):
                game = load_game(interaction.channel.id)
                if not game or game["status"] != "finished":
                    return await interaction.response.send_message("⚠️ Ván chơi chưa kết thúc!", ephemeral=True)
                new_g = new_game(interaction.channel.id, interaction.guild.id, interaction.user.id, interaction.user.display_name, game["mode"])
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
    # Dùng bot.listen thay vì bot.loop.create_task, vì lúc setup_monopoly()
    # được gọi (trước bot.run()), bot.loop CHƯA tồn tại -> AttributeError.
    _monopoly_views_registered = {"done": False}

    @bot.listen('on_ready')
    async def _monopoly_register_persistent_views():
        if _monopoly_views_registered["done"]:
            return
        _monopoly_views_registered["done"] = True
        bot.add_view(MonopolyLobbyView())
        bot.add_view(MonopolyGameView())
        print(">>> [MONOPOLY] Đã đăng ký View vĩnh viễn cho Cờ Tỷ Phú.")

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
            file = _board_file(game, filename="board.png")
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

        game = new_game(ctx.channel.id, ctx.guild.id, ctx.author.id, ctx.author.display_name, mode)
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
                "♾️ Bàn cờ không bao giờ hết hạn — chơi xong bấm **Chơi Lại** để bắt đầu ván mới ngay tại đây!"
            ),
            color=discord.Color.blue()
        )
        await ctx.reply(embed=embed, mention_author=False)
