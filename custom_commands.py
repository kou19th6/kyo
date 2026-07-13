# =====================================================================
# custom_commands.py
# =====================================================================
# Module BỔ SUNG cho bot Discord hiện có (bot.py của bạn).
# Cho phép NGƯỜI DÙNG tự tạo vô số "tính năng" bằng lệnh SLASH ( / )
# mà KHÔNG cần đụng vào code Python — an toàn, không eval/exec code lạ.
#
# BỘ CÔNG CỤ GỒM:
#   /tag        — tạo lệnh tùy chỉnh (như "custom command"/"tag")
#   /var        — kho biến (đếm số, lưu điểm, lưu chuỗi...) dùng trong tag
#   /embed      — tạo & gửi embed đẹp bằng form (modal), lưu để tái sử dụng
#   /trigger    — auto-reply khi có ai gõ từ khóa trong tin nhắn
#   /reactrole  — gắn role khi bấm emoji/nút, gỡ khi bấm lại
#   /button     — gắn nút bấm vào 1 tin nhắn để chạy 1 tag có sẵn
#                 + /button clicks — XEM AI ĐÃ BẤM NÚT, lúc nào
#   /poll       — tạo khảo sát nhanh có nút bấm vote
#                 + /poll voters — XEM AI ĐÃ VOTE GÌ
#   /giveaway   — MỚI: giveaway có nút "Tham gia", tự chọn người thắng
#   /suggestion — MỚI: hộp góp ý, có nút 👍👎 cho cộng đồng vote
#   /welcome    — MỚI: tin nhắn chào mừng + auto-role khi có member mới
#   /afk        — MỚI: đặt trạng thái vắng mặt, tự thông báo khi bị mention
#   /menu       — MỚI: bảng điều khiển nhanh bằng NÚT + FORM, không cần
#                 nhớ cú pháp lệnh
#   /tools      — bảng hướng dẫn dạng DROPDOWN (chọn mục để xem, gọn hơn)
#
# ĐIỂM MỚI QUAN TRỌNG — XÁC NHẬN AI ĐÃ BẤM NÚT:
#   Mọi lượt bấm nút (chạy tag, vote poll, tham gia giveaway, vote góp ý)
#   đều được ghi log vào MongoDB (guild_id, custom_id, user, thời gian).
#   - Người bấm luôn nhận 1 tin nhắn ephemeral xác nhận ngay lập tức.
#   - Admin có thể xem lại toàn bộ lịch sử bằng `/button clicks` hoặc
#     `/poll voters`.
#
# CÁCH GẮN VÀO BOT CHÍNH (bot.py):
#   from custom_commands import setup_custom_commands
#   ...
#   bot = commands.Bot(...)
#   ...
#   setup_custom_commands(bot, mongo_client["DiscordBotDB"])
#   ...
#   bot.run(TOKEN)
#
# LƯU Ý: setup_custom_commands() tự đăng ký app_commands group vào
# bot.tree — bạn vẫn cần đồng bộ slash command 1 lần (lệnh /synccmd bên
# dưới, chỉ OWNER dùng được) để Discord hiển thị lệnh "/" trên client.
# =====================================================================

import discord
from discord import app_commands
from discord.ext import commands, tasks
import re
import random
import asyncio
from datetime import datetime, timedelta

# =====================================================================
# CẤU HÌNH
# =====================================================================
MAX_TAGS_PER_GUILD      = 300
MAX_TAG_CONTENT_LEN     = 1800
MAX_VAR_VALUE_LEN       = 500
MAX_SUGGESTION_LEN      = 1000
DEFAULT_TAG_COOLDOWN    = 3       # giây, tránh spam chạy tag
GIVEAWAY_CHECK_INTERVAL = 20      # giây, tần suất kiểm tra giveaway hết hạn
OWNER_IDS_FOR_SYNC      = []      # điền ID chủ bot vào đây nếu muốn giới hạn /synccmd

# =====================================================================
# TEMPLATE ENGINE — AN TOÀN, KHÔNG EVAL CODE
# =====================================================================
# Cú pháp biến hỗ trợ trong nội dung tag / embed / trigger / welcome:
#   {user}            -> tên hiển thị người dùng lệnh
#   {user.mention}     -> mention người dùng lệnh
#   {user.id}          -> ID người dùng lệnh
#   {user.avatar}      -> URL avatar
#   {server}           -> tên server
#   {server.id}        -> ID server
#   {channel}          -> tên kênh
#   {channel.mention}  -> mention kênh
#   {args}             -> toàn bộ tham số người dùng nhập sau tên tag
#   {random:1-100}     -> số ngẫu nhiên trong khoảng
#   {choice:a|b|c}      -> chọn ngẫu nhiên 1 trong các lựa chọn
#   {var:ten_bien}      -> lấy giá trị biến đã lưu bằng /var (scope server)
#   {uvar:ten_bien}     -> lấy giá trị biến riêng của người dùng (scope user)
#   {count}             -> số lần tag này đã được chạy (tự tăng mỗi lần)
# =====================================================================

VAR_PATTERN = re.compile(r"\{([^{}]+)\}")


def _safe_truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[: limit - 3] + "..."


def render_template(template: str, *, user: discord.abc.User, guild: discord.Guild,
                     channel, args: str, guild_vars: dict, user_vars: dict,
                     run_count: int) -> str:
    """Thay thế mọi {biến} trong template. Không bao giờ chạy code do người dùng nhập."""

    def resolver(match: re.Match) -> str:
        token = match.group(1).strip()

        try:
            if token == "user":
                return user.display_name
            if token == "user.mention":
                return user.mention
            if token == "user.id":
                return str(user.id)
            if token == "user.avatar":
                return str(user.display_avatar.url)
            if token == "server":
                return guild.name if guild else "DM"
            if token == "server.id":
                return str(guild.id) if guild else "0"
            if token == "channel":
                return getattr(channel, "name", "kênh")
            if token == "channel.mention":
                return getattr(channel, "mention", "#kênh")
            if token == "args":
                return args or ""
            if token == "count":
                return str(run_count)

            if token.startswith("random:"):
                rng_part = token.split(":", 1)[1]
                lo, hi = rng_part.split("-")
                return str(random.randint(int(lo), int(hi)))

            if token.startswith("choice:"):
                options = token.split(":", 1)[1].split("|")
                options = [o for o in options if o != ""]
                return random.choice(options) if options else ""

            if token.startswith("var:"):
                key = token.split(":", 1)[1]
                return str(guild_vars.get(key, "0"))

            if token.startswith("uvar:"):
                key = token.split(":", 1)[1]
                return str(user_vars.get(key, "0"))

        except Exception:
            return match.group(0)  # nếu cú pháp sai, giữ nguyên chuỗi gốc

        return match.group(0)  # token lạ -> không thay thế

    result = VAR_PATTERN.sub(resolver, template)
    return _safe_truncate(result, 2000)


# =====================================================================
# LỚP QUẢN LÝ DỮ LIỆU (MongoDB)
# =====================================================================
class CustomCommandStore:
    def __init__(self, db):
        self.tags               = db["cc_tags"]
        self.guild_vars         = db["cc_guild_vars"]
        self.user_vars          = db["cc_user_vars"]
        self.embeds             = db["cc_embeds"]
        self.triggers           = db["cc_triggers"]
        self.reactroles         = db["cc_reactroles"]
        self.polls               = db["cc_polls"]
        self.click_logs          = db["cc_click_logs"]        # MỚI: log ai bấm nút gì, lúc nào
        self.giveaways           = db["cc_giveaways"]          # MỚI
        self.afk                 = db["cc_afk"]                # MỚI
        self.suggestion_config   = db["cc_suggestion_config"]  # MỚI
        self.suggestions         = db["cc_suggestions"]        # MỚI
        self.welcome_config      = db["cc_welcome_config"]     # MỚI
        self._cooldowns          = {}  # {(guild_id, tag_name, user_id): datetime}

    # ── TAG ──────────────────────────────────────────────────────────
    def get_tag(self, guild_id: int, name: str):
        return self.tags.find_one({"_id": f"{guild_id}:{name.lower()}"})

    def list_tags(self, guild_id: int, prefix: str = ""):
        cur = self.tags.find({"guild_id": guild_id, "name": {"$regex": f"^{re.escape(prefix)}", "$options": "i"}})
        return list(cur)[:25]

    def count_tags(self, guild_id: int) -> int:
        return self.tags.count_documents({"guild_id": guild_id})

    def create_tag(self, guild_id, name, content, author_id, role_ids=None, cooldown=DEFAULT_TAG_COOLDOWN):
        doc = {
            "_id": f"{guild_id}:{name.lower()}",
            "guild_id": guild_id,
            "name": name.lower(),
            "content": content,
            "author_id": str(author_id),
            "role_ids": role_ids or [],
            "cooldown": cooldown,
            "run_count": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.tags.insert_one(doc)
        return doc

    def edit_tag(self, guild_id, name, new_content):
        self.tags.update_one({"_id": f"{guild_id}:{name.lower()}"}, {"$set": {"content": new_content}})

    def delete_tag(self, guild_id, name):
        return self.tags.delete_one({"_id": f"{guild_id}:{name.lower()}"})

    def bump_run_count(self, guild_id, name) -> int:
        doc = self.tags.find_one_and_update(
            {"_id": f"{guild_id}:{name.lower()}"},
            {"$inc": {"run_count": 1}},
            return_document=True,
        )
        return doc["run_count"] if doc else 0

    def check_cooldown(self, guild_id, name, user_id, cooldown_secs) -> float:
        """Trả về số giây còn lại (0 nếu sẵn sàng chạy)."""
        key = (guild_id, name.lower(), user_id)
        last = self._cooldowns.get(key)
        now = datetime.now()
        if last:
            elapsed = (now - last).total_seconds()
            if elapsed < cooldown_secs:
                return cooldown_secs - elapsed
        self._cooldowns[key] = now
        return 0

    # ── VARIABLES ────────────────────────────────────────────────────
    def get_guild_vars(self, guild_id) -> dict:
        doc = self.guild_vars.find_one({"_id": str(guild_id)})
        return doc.get("vars", {}) if doc else {}

    def get_user_vars(self, guild_id, user_id) -> dict:
        doc = self.user_vars.find_one({"_id": f"{guild_id}:{user_id}"})
        return doc.get("vars", {}) if doc else {}

    def set_guild_var(self, guild_id, key, value):
        self.guild_vars.update_one({"_id": str(guild_id)}, {"$set": {f"vars.{key}": value}}, upsert=True)

    def set_user_var(self, guild_id, user_id, key, value):
        self.user_vars.update_one({"_id": f"{guild_id}:{user_id}"}, {"$set": {f"vars.{key}": value}}, upsert=True)

    def delete_guild_var(self, guild_id, key):
        self.guild_vars.update_one({"_id": str(guild_id)}, {"$unset": {f"vars.{key}": ""}})

    def delete_user_var(self, guild_id, user_id, key):
        self.user_vars.update_one({"_id": f"{guild_id}:{user_id}"}, {"$unset": {f"vars.{key}": ""}})

    # ── EMBED TEMPLATES ──────────────────────────────────────────────
    def save_embed(self, guild_id, name, data, author_id):
        self.embeds.update_one(
            {"_id": f"{guild_id}:{name.lower()}"},
            {"$set": {**data, "guild_id": guild_id, "name": name.lower(), "author_id": str(author_id)}},
            upsert=True,
        )

    def get_embed(self, guild_id, name):
        return self.embeds.find_one({"_id": f"{guild_id}:{name.lower()}"})

    def list_embeds(self, guild_id):
        return list(self.embeds.find({"guild_id": guild_id}))[:25]

    def delete_embed(self, guild_id, name):
        return self.embeds.delete_one({"_id": f"{guild_id}:{name.lower()}"})

    # ── TRIGGERS (AUTORESPONDER) ─────────────────────────────────────
    def add_trigger(self, guild_id, keyword, response, author_id, exact=False):
        doc_id = f"{guild_id}:{keyword.lower()}"
        self.triggers.update_one(
            {"_id": doc_id},
            {"$set": {
                "guild_id": guild_id, "keyword": keyword.lower(), "response": response,
                "exact": exact, "author_id": str(author_id),
            }},
            upsert=True,
        )

    def get_triggers(self, guild_id):
        return list(self.triggers.find({"guild_id": guild_id}))

    def delete_trigger(self, guild_id, keyword):
        return self.triggers.delete_one({"_id": f"{guild_id}:{keyword.lower()}"})

    # ── REACTION ROLE ────────────────────────────────────────────────
    def add_reactrole(self, message_id, emoji, role_id, guild_id):
        self.reactroles.update_one(
            {"_id": f"{message_id}:{emoji}"},
            {"$set": {"message_id": message_id, "emoji": emoji, "role_id": role_id, "guild_id": guild_id}},
            upsert=True,
        )

    def get_reactrole(self, message_id, emoji):
        return self.reactroles.find_one({"_id": f"{message_id}:{emoji}"})

    def remove_reactrole(self, message_id, emoji):
        return self.reactroles.delete_one({"_id": f"{message_id}:{emoji}"})

    # ── CLICK LOG (MỚI) — xác nhận ai đã bấm nút gì, lúc nào ──────────
    def log_click(self, guild_id, custom_id, user):
        self.click_logs.insert_one({
            "guild_id": guild_id,
            "custom_id": custom_id,
            "user_id": str(user.id),
            "username": str(user),
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def get_click_log(self, custom_id, limit=15):
        return list(self.click_logs.find({"custom_id": custom_id}).sort("at", -1).limit(limit))

    def count_clicks(self, custom_id) -> int:
        return self.click_logs.count_documents({"custom_id": custom_id})

    # ── GIVEAWAY (MỚI) ─────────────────────────────────────────────────
    def create_giveaway(self, guild_id, channel_id, message_id, prize, winners_count, end_at, host_id):
        gid = f"{guild_id}_{int(datetime.now().timestamp())}"
        doc = {
            "_id": gid, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id,
            "prize": prize, "winners_count": winners_count,
            "end_at": end_at.strftime("%Y-%m-%d %H:%M:%S"),
            "entries": [], "ended": False, "host_id": str(host_id),
        }
        self.giveaways.insert_one(doc)
        return doc

    def get_giveaway(self, giveaway_id):
        return self.giveaways.find_one({"_id": giveaway_id})

    def add_giveaway_entry(self, giveaway_id, user_id):
        self.giveaways.update_one({"_id": giveaway_id}, {"$addToSet": {"entries": str(user_id)}})

    def mark_giveaway_ended(self, giveaway_id):
        self.giveaways.update_one({"_id": giveaway_id}, {"$set": {"ended": True}})

    def due_giveaways(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return list(self.giveaways.find({"ended": False, "end_at": {"$lte": now_str}}))

    # ── AFK (MỚI) ────────────────────────────────────────────────────
    def set_afk(self, guild_id, user_id, reason):
        self.afk.update_one(
            {"_id": f"{guild_id}:{user_id}"},
            {"$set": {"reason": reason, "since": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}},
            upsert=True,
        )

    def clear_afk(self, guild_id, user_id):
        self.afk.delete_one({"_id": f"{guild_id}:{user_id}"})

    def get_afk(self, guild_id, user_id):
        return self.afk.find_one({"_id": f"{guild_id}:{user_id}"})

    # ── SUGGESTION BOX (MỚI) ────────────────────────────────────────
    def set_suggestion_channel(self, guild_id, channel_id):
        self.suggestion_config.update_one({"_id": str(guild_id)}, {"$set": {"channel_id": channel_id}}, upsert=True)

    def get_suggestion_channel(self, guild_id):
        doc = self.suggestion_config.find_one({"_id": str(guild_id)})
        return doc.get("channel_id") if doc else None

    def create_suggestion(self, guild_id, author_id, content):
        sid = f"{guild_id}_{int(datetime.now().timestamp() * 1000)}"
        doc = {
            "_id": sid, "guild_id": guild_id, "author_id": str(author_id),
            "content": content, "up": [], "down": [], "message_id": None,
        }
        self.suggestions.insert_one(doc)
        return doc

    def set_suggestion_message(self, sid, message_id):
        self.suggestions.update_one({"_id": sid}, {"$set": {"message_id": message_id}})

    def get_suggestion(self, sid):
        return self.suggestions.find_one({"_id": sid})

    def vote_suggestion(self, sid, user_id, up: bool):
        uid = str(user_id)
        if up:
            self.suggestions.update_one({"_id": sid}, {"$pull": {"down": uid}})
            self.suggestions.update_one({"_id": sid}, {"$addToSet": {"up": uid}})
        else:
            self.suggestions.update_one({"_id": sid}, {"$pull": {"up": uid}})
            self.suggestions.update_one({"_id": sid}, {"$addToSet": {"down": uid}})
        return self.get_suggestion(sid)

    # ── WELCOME (MỚI) ────────────────────────────────────────────────
    def set_welcome(self, guild_id, channel_id, message, role_id=None):
        self.welcome_config.update_one(
            {"_id": str(guild_id)},
            {"$set": {"channel_id": channel_id, "message": message, "role_id": role_id}},
            upsert=True,
        )

    def get_welcome(self, guild_id):
        return self.welcome_config.find_one({"_id": str(guild_id)})

    def disable_welcome(self, guild_id):
        self.welcome_config.delete_one({"_id": str(guild_id)})


# =====================================================================
# VIEW: NÚT BẤM CHẠY TAG (persistent, dùng chung 1 view cho mọi tag)
# =====================================================================
class RunTagButton(discord.ui.View):
    """View tạm thời khi vừa tạo nút — dùng custom_id mã hoá sẵn tên tag
    để bộ lắng nghe raw interaction (đăng ký ở setup_custom_commands)
    có thể xử lý xuyên suốt kể cả sau khi bot restart."""

    def __init__(self, tag_name: str, label: str, style: discord.ButtonStyle, emoji=None):
        super().__init__(timeout=None)
        btn = discord.ui.Button(
            label=label[:80],
            style=style,
            emoji=emoji,
            custom_id=f"cc_tagbtn::{tag_name.lower()}",
        )
        self.add_item(btn)


class PollView(discord.ui.View):
    def __init__(self, poll_id: str, options: list):
        super().__init__(timeout=None)
        for idx, opt in enumerate(options[:5]):
            btn = discord.ui.Button(
                label=opt[:75],
                style=discord.ButtonStyle.primary,
                custom_id=f"cc_poll::{poll_id}::{idx}",
            )
            self.add_item(btn)


class GiveawayJoinView(discord.ui.View):
    """MỚI: nút Tham Gia cho giveaway. Xử lý thực tế nằm ở on_raw_interaction
    (giống RunTagButton) nên vẫn hoạt động sau khi bot restart."""

    def __init__(self, giveaway_id: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="🎉 Tham gia", style=discord.ButtonStyle.success,
            custom_id=f"cc_gw::{giveaway_id}",
        ))


class SuggestionVoteView(discord.ui.View):
    """MỚI: 2 nút 👍 / 👎 gắn vào 1 góp ý."""

    def __init__(self, suggestion_id: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="👍", style=discord.ButtonStyle.success,
            custom_id=f"cc_sugg::{suggestion_id}::up",
        ))
        self.add_item(discord.ui.Button(
            label="👎", style=discord.ButtonStyle.danger,
            custom_id=f"cc_sugg::{suggestion_id}::down",
        ))


# =====================================================================
# MODAL: TẠO EMBED BẰNG FORM (không cần gõ JSON)
# =====================================================================
class EmbedBuilderModal(discord.ui.Modal, title="🎨 Tạo Embed"):
    def __init__(self, store: CustomCommandStore, name: str):
        super().__init__()
        self.store = store
        self.name = name

        self.f_title = discord.ui.TextInput(label="Tiêu đề", required=False, max_length=256)
        self.f_desc = discord.ui.TextInput(label="Nội dung", style=discord.TextStyle.paragraph,
                                            required=False, max_length=3900)
        self.f_color = discord.ui.TextInput(label="Màu (hex, vd: FF0000)", required=False, max_length=6)
        self.f_image = discord.ui.TextInput(label="URL ảnh lớn (tuỳ chọn)", required=False)
        self.f_thumb = discord.ui.TextInput(label="URL ảnh nhỏ góc (tuỳ chọn)", required=False)

        for item in (self.f_title, self.f_desc, self.f_color, self.f_image, self.f_thumb):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        color_val = 0x5865F2
        if self.f_color.value:
            try:
                color_val = int(self.f_color.value.strip("#"), 16)
            except Exception:
                pass

        data = {
            "title": self.f_title.value or "",
            "description": self.f_desc.value or "",
            "color": color_val,
            "image": self.f_image.value or "",
            "thumbnail": self.f_thumb.value or "",
        }
        self.store.save_embed(interaction.guild_id, self.name, data, interaction.user.id)

        preview = build_embed_from_data(data)
        await interaction.response.send_message(
            content=f"✅ Đã lưu embed **{self.name}**! Dùng `/embed send name:{self.name}` để gửi.",
            embed=preview, ephemeral=True,
        )


class EmbedNameModal(discord.ui.Modal, title="🎨 Tạo Embed — Bước 1/2"):
    """MỚI: modal đầu tiên chỉ hỏi tên, sau đó mở tiếp EmbedBuilderModal
    (dùng cho nút '🎨 Tạo Embed' trong /menu — không cần gõ lệnh trước)."""

    def __init__(self, store: CustomCommandStore):
        super().__init__()
        self.store = store
        self.f_name = discord.ui.TextInput(label="Tên embed (để lưu & gửi lại sau)", max_length=32)
        self.add_item(self.f_name)

    async def on_submit(self, interaction: discord.Interaction):
        name = self.f_name.value.strip().lower()
        await interaction.response.send_modal(EmbedBuilderModal(self.store, name))


class TagQuickModal(discord.ui.Modal, title="🏷️ Tạo Tag Nhanh"):
    """MỚI: tạo tag trực tiếp bằng form, dùng trong /menu."""

    def __init__(self, store: CustomCommandStore):
        super().__init__()
        self.store = store
        self.f_name = discord.ui.TextInput(label="Tên tag (chữ thường, không dấu cách)", max_length=32)
        self.f_content = discord.ui.TextInput(label="Nội dung", style=discord.TextStyle.paragraph, max_length=1800)
        self.f_cooldown = discord.ui.TextInput(label="Cooldown giây (để trống = 3)", required=False, max_length=5)
        for item in (self.f_name, self.f_content, self.f_cooldown):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("⚠️ Chỉ dùng được trong server!", ephemeral=True)
        name = self.f_name.value.strip().lower()
        if not re.match(r"^[a-z0-9_\-]{2,32}$", name):
            return await interaction.response.send_message(
                "⚠️ Tên chỉ gồm chữ thường/số/gạch dưới, dài 2-32 ký tự!", ephemeral=True)
        if self.store.get_tag(interaction.guild_id, name):
            return await interaction.response.send_message(f"⚠️ Tag **{name}** đã tồn tại!", ephemeral=True)
        if self.store.count_tags(interaction.guild_id) >= MAX_TAGS_PER_GUILD:
            return await interaction.response.send_message(
                f"⚠️ Server đã đạt giới hạn {MAX_TAGS_PER_GUILD} tag!", ephemeral=True)
        try:
            cd = int(self.f_cooldown.value) if self.f_cooldown.value else DEFAULT_TAG_COOLDOWN
        except ValueError:
            cd = DEFAULT_TAG_COOLDOWN
        content = _safe_truncate(self.f_content.value, MAX_TAG_CONTENT_LEN)
        self.store.create_tag(interaction.guild_id, name, content, interaction.user.id, [], max(0, cd))
        await interaction.response.send_message(
            f"✅ Đã tạo tag **{name}**! Chạy bằng `/tag run name:{name}`", ephemeral=True)


class TriggerQuickModal(discord.ui.Modal, title="🔔 Tạo Trigger Nhanh"):
    """MỚI: tạo trigger auto-reply trực tiếp bằng form, dùng trong /menu."""

    def __init__(self, store: CustomCommandStore):
        super().__init__()
        self.store = store
        self.f_keyword = discord.ui.TextInput(label="Từ khóa", max_length=100)
        self.f_response = discord.ui.TextInput(label="Nội dung trả lời", style=discord.TextStyle.paragraph, max_length=1800)
        self.f_exact = discord.ui.TextInput(label="Khớp chính xác? (co / khong)", required=False, max_length=5)
        for item in (self.f_keyword, self.f_response, self.f_exact):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("⚠️ Chỉ dùng được trong server!", ephemeral=True)
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        exact = self.f_exact.value.strip().lower() in ("co", "có", "yes", "true", "1")
        self.store.add_trigger(
            interaction.guild_id, self.f_keyword.value,
            _safe_truncate(self.f_response.value, MAX_TAG_CONTENT_LEN),
            interaction.user.id, exact,
        )
        await interaction.response.send_message(f"✅ Đã thêm trigger **{self.f_keyword.value}**!", ephemeral=True)


def build_embed_from_data(data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=data.get("title") or None,
        description=data.get("description") or None,
        color=data.get("color", 0x5865F2),
    )
    if data.get("image"):
        embed.set_image(url=data["image"])
    if data.get("thumbnail"):
        embed.set_thumbnail(url=data["thumbnail"])
    return embed


# =====================================================================
# GIAO DIỆN TRỢ GIÚP DẠNG DROPDOWN (MỚI — dễ dùng hơn 1 embed dài)
# =====================================================================
HELP_CATEGORIES = [
    ("overview", "🏠 Tổng quan", "Chọn 1 mục ở menu bên dưới để xem chi tiết cú pháp. Danh sách nhanh:\n\n"
                                  "🏷️ `/tag` — lệnh tùy chỉnh\n"
                                  "🔢 `/var` — biến dùng trong tag\n"
                                  "🎨 `/embed` — embed tuỳ chỉnh\n"
                                  "🔔 `/trigger` — auto-reply từ khóa\n"
                                  "🎭 `/reactrole` — role theo emoji\n"
                                  "🖱️ `/button` — nút chạy tag (+ xem ai bấm)\n"
                                  "📊 `/poll` — khảo sát (+ xem ai vote)\n"
                                  "🎉 `/giveaway` — tổ chức giveaway\n"
                                  "💡 `/suggestion` — hộp góp ý\n"
                                  "👋 `/welcome` — chào mừng + auto-role\n"
                                  "💤 `/afk` — trạng thái vắng mặt\n"
                                  "🧭 `/menu` — tạo nhanh bằng nút + form\n"
                                  "🧩 Cú pháp biến — xem mục cuối"),
    ("tag", "🏷️ Tag", "**/tag create** name content [cooldown] [role_required]\n"
                        "**/tag run** name [args]\n"
                        "**/tag edit / delete / list / info**\n"
                        "Tạo lệnh trả lời riêng, hỗ trợ toàn bộ cú pháp biến."),
    ("var", "🔢 Biến (Var)", "**/var set / myset** key value — lưu biến chung/riêng\n"
                              "**/var get / myget / list / delete**\n"
                              "Dùng trong tag qua `{var:ten}` và `{uvar:ten}`."),
    ("embed", "🎨 Embed", "**/embed create** name → mở form nhập nội dung\n"
                           "**/embed send / list / delete**"),
    ("trigger", "🔔 Trigger", "**/trigger add** keyword response [exact]\n"
                               "**/trigger list / delete**\n"
                               "Tự động trả lời khi ai gõ đúng từ khóa."),
    ("reactrole", "🎭 Reaction Role", "**/reactrole add** message_id emoji role\n"
                                       "**/reactrole remove**"),
    ("button", "🖱️ Nút & Log", "**/button create** tag_name label [message]\n"
                                 "**/button clicks** tag_name — xem CHÍNH XÁC ai đã bấm & lúc nào!"),
    ("poll", "📊 Khảo sát", "**/poll create** question option1 option2 ...\n"
                             "**/poll voters** poll_id — xem ai vote lựa chọn nào"),
    ("giveaway", "🎉 Giveaway", "**/giveaway start** prize duration_minutes winners\n"
                                 "**/giveaway end** giveaway_id — kết thúc sớm\n"
                                 "**/giveaway reroll** giveaway_id — bốc lại người thắng"),
    ("suggestion", "💡 Góp ý", "**/suggestion setup** channel — đặt kênh nhận góp ý\n"
                                "**/suggestion submit** idea — gửi góp ý, có nút 👍👎ẽ cộng đồng vote"),
    ("welcome", "👋 Chào mừng", "**/welcome set** channel message [autorole]\n"
                                 "**/welcome off**"),
    ("afk", "💤 AFK", "**/afk set** [reason]\n**/afk clear**\n"
                       "Tự động thông báo khi có người mention bạn lúc đang AFK."),
    ("menu", "🧭 Menu nhanh", "**/menu** — bảng điều khiển bằng nút bấm + form,\n"
                               "tạo tag / trigger / embed mà không cần nhớ cú pháp lệnh."),
    ("syntax", "🧩 Cú pháp biến", "`{user}` `{user.mention}` `{user.id}` `{user.avatar}`\n"
                                   "`{server}` `{server.id}` `{channel}` `{channel.mention}`\n"
                                   "`{args}` `{count}` `{random:1-100}` `{choice:a|b|c}`\n"
                                   "`{var:ten}` `{uvar:ten}`"),
]


def build_help(index: int):
    key, title, body = HELP_CATEGORIES[index]
    embed = discord.Embed(title=title, description=body, color=discord.Color.gold())
    embed.set_footer(text=f"Mục {index + 1}/{len(HELP_CATEGORIES)} — chọn mục khác ở menu bên dưới")
    return embed, HelpView()


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=title, value=str(i)) for i, (_, title, _) in enumerate(HELP_CATEGORIES)]
        super().__init__(placeholder="📚 Chọn mục hướng dẫn...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        embed, view = build_help(idx)
        await interaction.response.edit_message(embed=embed, view=view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())


class MenuView(discord.ui.View):
    """MỚI: bảng điều khiển nhanh — bấm nút thay vì gõ lệnh dài."""

    def __init__(self, store: CustomCommandStore):
        super().__init__(timeout=300)
        self.store = store

    @discord.ui.button(label="🏷️ Tạo Tag", style=discord.ButtonStyle.primary, row=0)
    async def btn_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TagQuickModal(self.store))

    @discord.ui.button(label="🔔 Tạo Trigger", style=discord.ButtonStyle.primary, row=0)
    async def btn_trigger(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TriggerQuickModal(self.store))

    @discord.ui.button(label="🎨 Tạo Embed", style=discord.ButtonStyle.primary, row=0)
    async def btn_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedNameModal(self.store))

    @discord.ui.button(label="📋 Trợ giúp", style=discord.ButtonStyle.secondary, row=1)
    async def btn_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, view = build_help(0)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# =====================================================================
# HÀM CHÍNH: GẮN MODULE VÀO BOT
# =====================================================================
def setup_custom_commands(bot: commands.Bot, db):
    store = CustomCommandStore(db)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /tag
    # ══════════════════════════════════════════════════════════════
    tag_group = app_commands.Group(name="tag", description="Tạo & chạy lệnh tùy chỉnh của riêng bạn")

    async def tag_name_autocomplete(interaction: discord.Interaction, current: str):
        docs = store.list_tags(interaction.guild_id, current)
        return [app_commands.Choice(name=d["name"], value=d["name"]) for d in docs]

    @tag_group.command(name="create", description="Tạo 1 lệnh tùy chỉnh mới")
    @app_commands.describe(
        name="Tên lệnh (không dấu cách)",
        content="Nội dung trả lời — có thể dùng {user}, {random:1-100}, {var:ten}, v.v. Xem /tools",
        cooldown="Cooldown giây giữa các lần chạy (mặc định 3s)",
        role_required="Chỉ role này mới chạy được (tuỳ chọn)",
    )
    async def tag_create(interaction: discord.Interaction, name: str, content: str,
                          cooldown: int = DEFAULT_TAG_COOLDOWN, role_required: discord.Role = None):
        if not interaction.guild:
            return await interaction.response.send_message("⚠️ Chỉ dùng được trong server!", ephemeral=True)
        name = name.strip().lower()
        if not re.match(r"^[a-z0-9_\-]{2,32}$", name):
            return await interaction.response.send_message(
                "⚠️ Tên chỉ gồm chữ thường/số/gạch dưới, dài 2-32 ký tự!", ephemeral=True)
        if store.get_tag(interaction.guild_id, name):
            return await interaction.response.send_message(
                f"⚠️ Tag **{name}** đã tồn tại! Dùng `/tag edit` để sửa.", ephemeral=True)
        if store.count_tags(interaction.guild_id) >= MAX_TAGS_PER_GUILD:
            return await interaction.response.send_message(
                f"⚠️ Server đã đạt giới hạn {MAX_TAGS_PER_GUILD} tag!", ephemeral=True)

        content = _safe_truncate(content, MAX_TAG_CONTENT_LEN)
        role_ids = [role_required.id] if role_required else []
        store.create_tag(interaction.guild_id, name, content, interaction.user.id, role_ids, max(0, cooldown))

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ ĐÃ TẠO TAG!",
                description=f"Chạy bằng: `/tag run name:{name}`\n\n**Preview:**\n{content[:500]}",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @tag_group.command(name="run", description="Chạy 1 tag đã tạo")
    @app_commands.autocomplete(name=tag_name_autocomplete)
    @app_commands.describe(name="Tên tag", args="Tham số truyền vào (dùng qua {args})")
    async def tag_run(interaction: discord.Interaction, name: str, args: str = ""):
        await _execute_tag(interaction, store, name, args)

    @tag_group.command(name="edit", description="Sửa nội dung tag đã tạo (chỉ người tạo hoặc Admin)")
    @app_commands.autocomplete(name=tag_name_autocomplete)
    async def tag_edit(interaction: discord.Interaction, name: str, content: str):
        doc = store.get_tag(interaction.guild_id, name)
        if not doc:
            return await interaction.response.send_message("⚠️ Không tìm thấy tag!", ephemeral=True)
        is_owner_or_admin = (str(interaction.user.id) == doc["author_id"]
                              or interaction.user.guild_permissions.manage_guild)
        if not is_owner_or_admin:
            return await interaction.response.send_message("⛔ Chỉ người tạo hoặc Admin mới sửa được!", ephemeral=True)
        store.edit_tag(interaction.guild_id, name, _safe_truncate(content, MAX_TAG_CONTENT_LEN))
        await interaction.response.send_message(f"✅ Đã cập nhật tag **{name}**!", ephemeral=True)

    @tag_group.command(name="delete", description="Xoá 1 tag (chỉ người tạo hoặc Admin)")
    @app_commands.autocomplete(name=tag_name_autocomplete)
    async def tag_delete(interaction: discord.Interaction, name: str):
        doc = store.get_tag(interaction.guild_id, name)
        if not doc:
            return await interaction.response.send_message("⚠️ Không tìm thấy tag!", ephemeral=True)
        is_owner_or_admin = (str(interaction.user.id) == doc["author_id"]
                              or interaction.user.guild_permissions.manage_guild)
        if not is_owner_or_admin:
            return await interaction.response.send_message("⛔ Chỉ người tạo hoặc Admin mới xoá được!", ephemeral=True)
        store.delete_tag(interaction.guild_id, name)
        await interaction.response.send_message(f"🗑️ Đã xoá tag **{name}**.", ephemeral=True)

    @tag_group.command(name="list", description="Xem danh sách tag trong server")
    async def tag_list(interaction: discord.Interaction):
        docs = store.list_tags(interaction.guild_id)
        if not docs:
            return await interaction.response.send_message("📋 Server chưa có tag nào. Dùng `/tag create` để tạo!", ephemeral=True)
        lines = [f"• **{d['name']}** — chạy {d.get('run_count',0)} lần (bởi <@{d['author_id']}>)" for d in docs]
        embed = discord.Embed(title="📋 DANH SÁCH TAG", description="\n".join(lines), color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tag_group.command(name="info", description="Xem chi tiết 1 tag")
    @app_commands.autocomplete(name=tag_name_autocomplete)
    async def tag_info(interaction: discord.Interaction, name: str):
        doc = store.get_tag(interaction.guild_id, name)
        if not doc:
            return await interaction.response.send_message("⚠️ Không tìm thấy tag!", ephemeral=True)
        embed = discord.Embed(title=f"🏷️ TAG: {doc['name']}", color=discord.Color.blue())
        embed.add_field(name="Nội dung (raw)", value=f"```{doc['content'][:1000]}```", inline=False)
        embed.add_field(name="Người tạo", value=f"<@{doc['author_id']}>", inline=True)
        embed.add_field(name="Đã chạy", value=f"{doc.get('run_count',0)} lần", inline=True)
        embed.add_field(name="Cooldown", value=f"{doc.get('cooldown', DEFAULT_TAG_COOLDOWN)}s", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(tag_group)

    async def _execute_tag(interaction: discord.Interaction, store: CustomCommandStore, name: str, args: str):
        if not interaction.guild:
            return await interaction.response.send_message("⚠️ Chỉ dùng được trong server!", ephemeral=True)
        doc = store.get_tag(interaction.guild_id, name)
        if not doc:
            return await interaction.response.send_message(f"⚠️ Không tìm thấy tag **{name}**!", ephemeral=True)

        role_ids = doc.get("role_ids", [])
        if role_ids and not any(r.id in role_ids for r in interaction.user.roles):
            return await interaction.response.send_message("⛔ Bạn không có role để dùng tag này!", ephemeral=True)

        remain = store.check_cooldown(interaction.guild_id, name, interaction.user.id, doc.get("cooldown", DEFAULT_TAG_COOLDOWN))
        if remain > 0:
            return await interaction.response.send_message(f"⏳ Đợi **{remain:.1f}s** nữa!", ephemeral=True)

        run_count = store.bump_run_count(interaction.guild_id, name)
        gvars = store.get_guild_vars(interaction.guild_id)
        uvars = store.get_user_vars(interaction.guild_id, interaction.user.id)

        rendered = render_template(
            doc["content"], user=interaction.user, guild=interaction.guild,
            channel=interaction.channel, args=args, guild_vars=gvars, user_vars=uvars,
            run_count=run_count,
        )
        await interaction.response.send_message(rendered)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /var — kho biến để tag dùng chung (đếm số, lưu điểm...)
    # ══════════════════════════════════════════════════════════════
    var_group = app_commands.Group(name="var", description="Lưu biến dùng trong tag: {var:ten} và {uvar:ten}")

    @var_group.command(name="set", description="Đặt biến CHUNG của server (dùng {var:ten} trong tag)")
    @app_commands.describe(key="Tên biến", value="Giá trị")
    async def var_set(interaction: discord.Interaction, key: str, value: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server để đặt biến chung!", ephemeral=True)
        value = _safe_truncate(value, MAX_VAR_VALUE_LEN)
        store.set_guild_var(interaction.guild_id, key, value)
        await interaction.response.send_message(f"✅ `{key}` = `{value}`", ephemeral=True)

    @var_group.command(name="myset", description="Đặt biến RIÊNG của bạn (dùng {uvar:ten} trong tag)")
    async def var_myset(interaction: discord.Interaction, key: str, value: str):
        value = _safe_truncate(value, MAX_VAR_VALUE_LEN)
        store.set_user_var(interaction.guild_id, interaction.user.id, key, value)
        await interaction.response.send_message(f"✅ Biến riêng `{key}` = `{value}`", ephemeral=True)

    @var_group.command(name="get", description="Xem giá trị biến chung của server")
    async def var_get(interaction: discord.Interaction, key: str):
        gvars = store.get_guild_vars(interaction.guild_id)
        await interaction.response.send_message(f"`{key}` = `{gvars.get(key, '(chưa có)')}`", ephemeral=True)

    @var_group.command(name="myget", description="Xem giá trị biến riêng của bạn")
    async def var_myget(interaction: discord.Interaction, key: str):
        uvars = store.get_user_vars(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(f"`{key}` = `{uvars.get(key, '(chưa có)')}`", ephemeral=True)

    @var_group.command(name="list", description="Xem tất cả biến chung của server")
    async def var_list(interaction: discord.Interaction):
        gvars = store.get_guild_vars(interaction.guild_id)
        if not gvars:
            return await interaction.response.send_message("📋 Chưa có biến nào.", ephemeral=True)
        lines = [f"`{k}` = `{v}`" for k, v in gvars.items()]
        await interaction.response.send_message("\n".join(lines)[:1900], ephemeral=True)

    @var_group.command(name="delete", description="Xoá 1 biến chung")
    async def var_delete(interaction: discord.Interaction, key: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        store.delete_guild_var(interaction.guild_id, key)
        await interaction.response.send_message(f"🗑️ Đã xoá biến `{key}`.", ephemeral=True)

    bot.tree.add_command(var_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /embed — tạo embed bằng form, lưu & gửi lại
    # ══════════════════════════════════════════════════════════════
    embed_group = app_commands.Group(name="embed", description="Tạo & gửi embed tuỳ chỉnh không cần code")

    @embed_group.command(name="create", description="Mở form tạo embed mới (lưu lại để dùng nhiều lần)")
    async def embed_create(interaction: discord.Interaction, name: str):
        name = name.strip().lower()
        await interaction.response.send_modal(EmbedBuilderModal(store, name))

    @embed_group.command(name="send", description="Gửi 1 embed đã lưu vào kênh hiện tại")
    async def embed_send(interaction: discord.Interaction, name: str):
        doc = store.get_embed(interaction.guild_id, name)
        if not doc:
            return await interaction.response.send_message("⚠️ Không tìm thấy embed này!", ephemeral=True)
        embed = build_embed_from_data(doc)
        await interaction.response.send_message(embed=embed)

    @embed_group.command(name="list", description="Xem danh sách embed đã lưu")
    async def embed_list(interaction: discord.Interaction):
        docs = store.list_embeds(interaction.guild_id)
        if not docs:
            return await interaction.response.send_message("📋 Chưa có embed nào. Dùng `/embed create`!", ephemeral=True)
        lines = [f"• **{d['name']}**" for d in docs]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @embed_group.command(name="delete", description="Xoá embed đã lưu")
    async def embed_delete(interaction: discord.Interaction, name: str):
        store.delete_embed(interaction.guild_id, name)
        await interaction.response.send_message(f"🗑️ Đã xoá embed **{name}**.", ephemeral=True)

    bot.tree.add_command(embed_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /trigger — auto-reply theo từ khóa (autoresponder)
    # ══════════════════════════════════════════════════════════════
    trigger_group = app_commands.Group(name="trigger", description="Tự động trả lời khi ai đó gõ từ khóa")

    @trigger_group.command(name="add", description="Thêm từ khóa tự động phản hồi")
    @app_commands.describe(keyword="Từ khóa cần bắt", response="Nội dung trả lời (hỗ trợ {user}, {random:...} v.v.)",
                            exact="Chỉ khớp khi tin nhắn ĐÚNG BẰNG từ khóa (mặc định: chỉ cần chứa từ khóa)")
    async def trigger_add(interaction: discord.Interaction, keyword: str, response: str, exact: bool = False):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        store.add_trigger(interaction.guild_id, keyword, _safe_truncate(response, MAX_TAG_CONTENT_LEN),
                           interaction.user.id, exact)
        await interaction.response.send_message(f"✅ Đã thêm trigger cho từ khóa **{keyword}**!", ephemeral=True)

    @trigger_group.command(name="list", description="Xem danh sách trigger")
    async def trigger_list(interaction: discord.Interaction):
        docs = store.get_triggers(interaction.guild_id)
        if not docs:
            return await interaction.response.send_message("📋 Chưa có trigger nào.", ephemeral=True)
        lines = [f"• `{d['keyword']}` {'(khớp chính xác)' if d.get('exact') else '(chứa từ khóa)'}" for d in docs]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @trigger_group.command(name="delete", description="Xoá 1 trigger")
    async def trigger_delete(interaction: discord.Interaction, keyword: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        store.delete_trigger(interaction.guild_id, keyword)
        await interaction.response.send_message(f"🗑️ Đã xoá trigger **{keyword}**.", ephemeral=True)

    bot.tree.add_command(trigger_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /reactrole — gắn role khi bấm reaction
    # ══════════════════════════════════════════════════════════════
    reactrole_group = app_commands.Group(name="reactrole", description="Tự cấp role khi bấm emoji vào tin nhắn")

    @reactrole_group.command(name="add", description="Gắn 1 emoji -> role vào tin nhắn (dùng ID tin nhắn)")
    @app_commands.describe(message_id="ID tin nhắn (bật Developer Mode để copy)", emoji="Emoji dùng để bấm", role="Role sẽ được cấp")
    async def reactrole_add(interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("⛔ Cần quyền Manage Roles!", ephemeral=True)
        try:
            msg_id = int(message_id)
            msg = await interaction.channel.fetch_message(msg_id)
        except Exception:
            return await interaction.response.send_message("⚠️ Không tìm thấy tin nhắn với ID đó trong kênh này!", ephemeral=True)

        try:
            await msg.add_reaction(emoji)
        except Exception:
            return await interaction.response.send_message("⚠️ Emoji không hợp lệ hoặc bot thiếu quyền reaction!", ephemeral=True)

        store.add_reactrole(msg_id, emoji, role.id, interaction.guild_id)
        await interaction.response.send_message(f"✅ Ai bấm {emoji} vào tin nhắn đó sẽ nhận role {role.mention}!", ephemeral=True)

    @reactrole_group.command(name="remove", description="Gỡ 1 reaction-role")
    async def reactrole_remove(interaction: discord.Interaction, message_id: str, emoji: str):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("⛔ Cần quyền Manage Roles!", ephemeral=True)
        store.remove_reactrole(int(message_id), emoji)
        await interaction.response.send_message("🗑️ Đã gỡ reaction-role.", ephemeral=True)

    bot.tree.add_command(reactrole_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /button — nút bấm chạy tag + XEM AI ĐÃ BẤM (MỚI)
    # ══════════════════════════════════════════════════════════════
    button_group = app_commands.Group(name="button", description="Tạo nút bấm chạy tag & xem ai đã bấm")

    @button_group.command(name="create", description="Tạo 1 tin nhắn có nút bấm — bấm vào sẽ tự chạy 1 tag")
    @app_commands.describe(tag_name="Tên tag đã tạo bằng /tag create", label="Chữ hiển thị trên nút",
                            message="Nội dung tin nhắn đi kèm nút (tuỳ chọn)")
    async def button_create(interaction: discord.Interaction, tag_name: str, label: str, message: str = "\u200b"):
        doc = store.get_tag(interaction.guild_id, tag_name)
        if not doc:
            return await interaction.response.send_message(f"⚠️ Chưa có tag **{tag_name}**! Tạo bằng `/tag create` trước.", ephemeral=True)
        view = RunTagButton(tag_name, label, discord.ButtonStyle.primary)
        await interaction.response.send_message(content=message, view=view)

    @button_group.command(name="clicks", description="Xem CHÍNH XÁC ai đã bấm nút của 1 tag & lúc nào")
    async def button_clicks(interaction: discord.Interaction, tag_name: str):
        custom_id = f"cc_tagbtn::{tag_name.lower()}"
        total = store.count_clicks(custom_id)
        logs = store.get_click_log(custom_id, 15)
        if not logs:
            return await interaction.response.send_message(f"📋 Chưa ai bấm nút tag **{tag_name}**.", ephemeral=True)
        lines = [f"• <@{l['user_id']}> — {l['at']}" for l in logs]
        embed = discord.Embed(
            title=f"🖱️ AI ĐÃ BẤM NÚT: {tag_name}",
            description="\n".join(lines),
            color=discord.Color.teal(),
        )
        embed.set_footer(text=f"Tổng cộng: {total} lượt bấm — hiển thị {len(logs)} lượt gần nhất")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(button_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /poll — khảo sát nhanh có nút vote + XEM AI VOTE GÌ (MỚI)
    # ══════════════════════════════════════════════════════════════
    poll_votes_col = db["cc_poll_votes"]
    poll_group = app_commands.Group(name="poll", description="Khảo sát nhanh có nút vote")

    @poll_group.command(name="create", description="Tạo khảo sát nhanh với tối đa 5 lựa chọn (bấm nút để vote)")
    @app_commands.describe(question="Câu hỏi khảo sát",
                            option1="Lựa chọn 1", option2="Lựa chọn 2",
                            option3="Lựa chọn 3 (tuỳ chọn)", option4="Lựa chọn 4 (tuỳ chọn)",
                            option5="Lựa chọn 5 (tuỳ chọn)")
    async def poll_create(interaction: discord.Interaction, question: str, option1: str, option2: str,
                           option3: str = None, option4: str = None, option5: str = None):
        options = [o for o in [option1, option2, option3, option4, option5] if o]
        poll_id = f"{interaction.guild_id}_{int(datetime.now().timestamp())}"

        embed = discord.Embed(title=f"📊 {question}", color=discord.Color.blurple())
        counts = "\n".join(f"{i+1}️⃣ **{opt}** — 0 vote" for i, opt in enumerate(options))
        embed.description = counts
        embed.set_footer(text=f"Khảo sát bởi {interaction.user.display_name} • ID: {poll_id}")

        view = PollView(poll_id, options)
        await interaction.response.send_message(embed=embed, view=view)
        sent = await interaction.original_response()

        store.polls.insert_one({
            "_id": poll_id, "message_id": sent.id, "guild_id": interaction.guild_id,
            "question": question, "options": options,
        })

    @poll_group.command(name="voters", description="Xem ai đã vote gì trong 1 khảo sát (dùng ID trong footer)")
    async def poll_voters(interaction: discord.Interaction, poll_id: str):
        poll = store.polls.find_one({"_id": poll_id, "guild_id": interaction.guild_id})
        if not poll:
            return await interaction.response.send_message("⚠️ Không tìm thấy khảo sát!", ephemeral=True)
        votes = list(poll_votes_col.find({"poll_id": poll_id}))
        if not votes:
            return await interaction.response.send_message("📋 Chưa có ai vote.", ephemeral=True)
        lines = []
        for v in votes:
            uid = v["_id"].split(":")[-1]
            choice = v.get("choice", -1)
            opt = poll["options"][choice] if 0 <= choice < len(poll["options"]) else "?"
            lines.append(f"• <@{uid}> → **{opt}**")
        embed = discord.Embed(
            title=f"🗳️ VOTE CHI TIẾT: {poll['question']}",
            description="\n".join(lines)[:4000],
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(poll_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /giveaway — MỚI: giveaway có nút Tham Gia, tự chọn thắng cuộc
    # ══════════════════════════════════════════════════════════════
    giveaway_group = app_commands.Group(name="giveaway", description="Tổ chức giveaway có nút tham gia")

    async def _finish_giveaway(giveaway_id: str):
        gw = store.get_giveaway(giveaway_id)
        if not gw or gw.get("ended"):
            return
        store.mark_giveaway_ended(giveaway_id)
        channel = bot.get_channel(gw["channel_id"])
        entries = gw.get("entries", [])
        winners_count = gw.get("winners_count", 1)
        if not entries:
            result_text = "😢 Không có ai tham gia giveaway này."
        else:
            winners = random.sample(entries, min(winners_count, len(entries)))
            result_text = "🎉 Chúc mừng: " + ", ".join(f"<@{w}>" for w in winners)
        if channel:
            try:
                await channel.send(embed=discord.Embed(
                    title=f"🎉 GIVEAWAY KẾT THÚC: {gw['prize']}",
                    description=result_text,
                    color=discord.Color.gold(),
                ))
                try:
                    msg = await channel.fetch_message(gw["message_id"])
                    old_embed = msg.embeds[0] if msg.embeds else discord.Embed(title=gw["prize"])
                    old_embed.title = f"🎉 [ĐÃ KẾT THÚC] {gw['prize']}"
                    old_embed.color = discord.Color.dark_grey()
                    await msg.edit(embed=old_embed, view=None)
                except Exception:
                    pass
            except Exception:
                pass

    @tasks.loop(seconds=GIVEAWAY_CHECK_INTERVAL)
    async def giveaway_checker():
        for gw in store.due_giveaways():
            await _finish_giveaway(gw["_id"])

    @giveaway_checker.before_loop
    async def _before_giveaway_checker():
        await bot.wait_until_ready()

    async def _start_giveaway_checker(*args, **kwargs):
        if not giveaway_checker.is_running():
            giveaway_checker.start()

    bot.add_listener(_start_giveaway_checker, "on_ready")

    @giveaway_group.command(name="start", description="Bắt đầu 1 giveaway mới")
    @app_commands.describe(prize="Phần thưởng", duration_minutes="Thời gian chạy (phút, mặc định 60)",
                            winners="Số người thắng (mặc định 1)")
    async def giveaway_start(interaction: discord.Interaction, prize: str,
                              duration_minutes: int = 60, winners: int = 1):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        winners = max(1, min(winners, 20))
        duration_minutes = max(1, min(duration_minutes, 10080))
        end_at = datetime.now() + timedelta(minutes=duration_minutes)

        embed = discord.Embed(
            title=f"🎉 GIVEAWAY: {prize}",
            description=(f"Bấm nút bên dưới để tham gia!\n"
                         f"🏆 Số người thắng: **{winners}**\n"
                         f"⏰ Kết thúc: <t:{int(end_at.timestamp())}:R>"),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Tổ chức bởi {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
        sent = await interaction.original_response()
        doc = store.create_giveaway(interaction.guild_id, interaction.channel_id, sent.id,
                                     prize, winners, end_at, interaction.user.id)
        view = GiveawayJoinView(doc["_id"])
        await sent.edit(view=view)
        await interaction.followup.send(f"✅ Đã tạo giveaway **{prize}**! ID: `{doc['_id']}`", ephemeral=True)

    @giveaway_group.command(name="end", description="Kết thúc giveaway ngay lập tức")
    async def giveaway_end(interaction: discord.Interaction, giveaway_id: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        gw = store.get_giveaway(giveaway_id)
        if not gw or gw["guild_id"] != interaction.guild_id:
            return await interaction.response.send_message("⚠️ Không tìm thấy giveaway!", ephemeral=True)
        if gw.get("ended"):
            return await interaction.response.send_message("⚠️ Giveaway này đã kết thúc rồi!", ephemeral=True)
        await interaction.response.send_message("✅ Đang kết thúc giveaway...", ephemeral=True)
        await _finish_giveaway(giveaway_id)

    @giveaway_group.command(name="reroll", description="Bốc lại người thắng cho giveaway đã kết thúc")
    async def giveaway_reroll(interaction: discord.Interaction, giveaway_id: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        gw = store.get_giveaway(giveaway_id)
        if not gw or gw["guild_id"] != interaction.guild_id:
            return await interaction.response.send_message("⚠️ Không tìm thấy giveaway!", ephemeral=True)
        entries = gw.get("entries", [])
        if not entries:
            return await interaction.response.send_message("😢 Không có ai tham gia để bốc lại!", ephemeral=True)
        winners = random.sample(entries, min(gw.get("winners_count", 1), len(entries)))
        await interaction.response.send_message(
            f"🎉 Người thắng mới cho **{gw['prize']}**: " + ", ".join(f"<@{w}>" for w in winners)
        )

    bot.tree.add_command(giveaway_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /afk — MỚI: đặt trạng thái vắng mặt
    # ══════════════════════════════════════════════════════════════
    afk_group = app_commands.Group(name="afk", description="Đặt trạng thái vắng mặt (AFK)")

    @afk_group.command(name="set", description="Đặt trạng thái AFK — tự thông báo khi có người mention bạn")
    async def afk_set(interaction: discord.Interaction, reason: str = "Đang bận"):
        store.set_afk(interaction.guild_id, interaction.user.id, _safe_truncate(reason, 200))
        await interaction.response.send_message(f"💤 Đã đặt AFK: {reason}")

    @afk_group.command(name="clear", description="Gỡ trạng thái AFK")
    async def afk_clear(interaction: discord.Interaction):
        store.clear_afk(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message("✅ Đã gỡ trạng thái AFK.", ephemeral=True)

    bot.tree.add_command(afk_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /suggestion — MỚI: hộp góp ý có nút 👍👎
    # ══════════════════════════════════════════════════════════════
    suggestion_group = app_commands.Group(name="suggestion", description="Hộp góp ý cho server")

    @suggestion_group.command(name="setup", description="Đặt kênh nhận góp ý")
    async def suggestion_setup(interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        store.set_suggestion_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(f"✅ Đã đặt kênh góp ý: {channel.mention}", ephemeral=True)

    @suggestion_group.command(name="submit", description="Gửi góp ý cho server")
    async def suggestion_submit(interaction: discord.Interaction, idea: str):
        ch_id = store.get_suggestion_channel(interaction.guild_id)
        if not ch_id:
            return await interaction.response.send_message(
                "⚠️ Server chưa đặt kênh góp ý! Nhờ Admin dùng `/suggestion setup`.", ephemeral=True)
        channel = interaction.guild.get_channel(ch_id)
        if not channel:
            return await interaction.response.send_message("⚠️ Kênh góp ý không còn tồn tại!", ephemeral=True)
        idea = _safe_truncate(idea, MAX_SUGGESTION_LEN)
        doc = store.create_suggestion(interaction.guild_id, interaction.user.id, idea)

        embed = discord.Embed(title="💡 GÓP Ý MỚI", description=idea, color=discord.Color.blue())
        embed.set_footer(text=f"Gửi bởi {interaction.user.display_name}")
        embed.add_field(name="👍", value="0", inline=True)
        embed.add_field(name="👎", value="0", inline=True)

        view = SuggestionVoteView(doc["_id"])
        sent = await channel.send(embed=embed, view=view)
        store.set_suggestion_message(doc["_id"], sent.id)
        await interaction.response.send_message(f"✅ Đã gửi góp ý của bạn vào {channel.mention}!", ephemeral=True)

    bot.tree.add_command(suggestion_group)

    # ══════════════════════════════════════════════════════════════
    # GROUP: /welcome — MỚI: tin nhắn chào mừng + auto-role
    # ══════════════════════════════════════════════════════════════
    welcome_group = app_commands.Group(name="welcome", description="Tin nhắn chào mừng thành viên mới")

    @welcome_group.command(name="set", description="Đặt tin nhắn chào mừng khi có thành viên mới")
    @app_commands.describe(channel="Kênh gửi tin chào mừng",
                            message="Nội dung (dùng {user}, {user.mention}, {server})",
                            autorole="Role tự động gắn cho thành viên mới (tuỳ chọn)")
    async def welcome_set(interaction: discord.Interaction, channel: discord.TextChannel, message: str,
                           autorole: discord.Role = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        store.set_welcome(interaction.guild_id, channel.id, _safe_truncate(message, MAX_TAG_CONTENT_LEN),
                           autorole.id if autorole else None)
        await interaction.response.send_message(f"✅ Đã bật chào mừng tại {channel.mention}!", ephemeral=True)

    @welcome_group.command(name="off", description="Tắt tin nhắn chào mừng")
    async def welcome_off(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("⛔ Cần quyền Manage Server!", ephemeral=True)
        store.disable_welcome(interaction.guild_id)
        await interaction.response.send_message("✅ Đã tắt chào mừng.", ephemeral=True)

    bot.tree.add_command(welcome_group)

    # ══════════════════════════════════════════════════════════════
    # /menu — MỚI: bảng điều khiển nhanh bằng nút + form
    # ══════════════════════════════════════════════════════════════
    @bot.tree.command(name="menu", description="Bảng điều khiển nhanh — tạo tag/trigger/embed bằng form, không cần nhớ lệnh")
    async def menu_cmd(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🧭 BẢNG ĐIỀU KHIỂN NHANH",
            description="Bấm nút bên dưới để tạo tính năng ngay bằng form — không cần gõ lệnh dài!",
            color=discord.Color.purple(),
        )
        await interaction.response.send_message(embed=embed, view=MenuView(store), ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    # /tools — hướng dẫn dạng DROPDOWN (gọn & dễ dùng hơn)
    # ══════════════════════════════════════════════════════════════
    @bot.tree.command(name="tools", description="Xem hướng dẫn toàn bộ công cụ tự tạo tính năng")
    async def tools_cmd(interaction: discord.Interaction):
        embed, view = build_help(0)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    # /help — MỚI: lệnh trợ giúp nhanh, mở thẳng màn hình Tổng quan
    # ══════════════════════════════════════════════════════════════
    @bot.tree.command(name="help", description="Xem tổng quan tất cả lệnh của bot + hướng dẫn dùng nhanh")
    async def help_cmd(interaction: discord.Interaction):
        embed, view = build_help(0)  # index 0 = mục "🏠 Tổng quan"
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    # /synccmd — đồng bộ slash command lên Discord (chỉ chủ bot)
    # ══════════════════════════════════════════════════════════════
    @bot.tree.command(name="synccmd", description="[Admin] Đồng bộ lại danh sách lệnh / với Discord")
    async def synccmd(interaction: discord.Interaction):
        if OWNER_IDS_FOR_SYNC and interaction.user.id not in OWNER_IDS_FOR_SYNC:
            return await interaction.response.send_message("⛔ Không có quyền!", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã đồng bộ **{len(synced)}** lệnh slash!", ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    # LẮNG NGHE SỰ KIỆN
    # ══════════════════════════════════════════════════════════════
    async def on_message_check_triggers(message: discord.Message):
        if message.author.bot or not message.guild:
            return
        content_lower = message.content.lower()
        for trig in store.get_triggers(message.guild.id):
            kw = trig["keyword"]
            matched = (content_lower == kw) if trig.get("exact") else (kw in content_lower)
            if matched:
                gvars = store.get_guild_vars(message.guild.id)
                uvars = store.get_user_vars(message.guild.id, message.author.id)
                rendered = render_template(
                    trig["response"], user=message.author, guild=message.guild,
                    channel=message.channel, args="", guild_vars=gvars, user_vars=uvars, run_count=0,
                )
                try:
                    await message.channel.send(rendered)
                except Exception:
                    pass
                break  # chỉ khớp trigger đầu tiên tìm thấy

    bot.add_listener(on_message_check_triggers, "on_message")

    # MỚI: xử lý AFK (tự gỡ AFK khi nhắn lại + báo khi bị mention lúc đang AFK)
    async def on_message_afk_handler(message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if store.get_afk(message.guild.id, message.author.id):
            store.clear_afk(message.guild.id, message.author.id)
            try:
                await message.channel.send(
                    f"👋 Chào mừng trở lại, {message.author.mention}! Đã gỡ trạng thái AFK.", delete_after=6)
            except Exception:
                pass
        for u in message.mentions:
            afk_doc = store.get_afk(message.guild.id, u.id)
            if afk_doc:
                try:
                    await message.channel.send(f"💤 **{u.display_name}** đang AFK: {afk_doc.get('reason', '')}")
                except Exception:
                    pass

    bot.add_listener(on_message_afk_handler, "on_message")

    # MỚI: chào mừng + auto-role khi có thành viên mới
    async def on_member_join_handler(member: discord.Member):
        cfg = store.get_welcome(member.guild.id)
        if not cfg:
            return
        channel = member.guild.get_channel(cfg["channel_id"])
        if channel:
            rendered = render_template(
                cfg["message"], user=member, guild=member.guild, channel=channel,
                args="", guild_vars=store.get_guild_vars(member.guild.id), user_vars={}, run_count=0,
            )
            try:
                await channel.send(rendered)
            except Exception:
                pass
        if cfg.get("role_id"):
            role = member.guild.get_role(cfg["role_id"])
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role chào mừng")
                except Exception:
                    pass

    bot.add_listener(on_member_join_handler, "on_member_join")

    async def on_raw_interaction(interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")

        # Nút chạy tag — MỚI: ghi log + xác nhận ai đã bấm
        if custom_id.startswith("cc_tagbtn::"):
            tag_name = custom_id.split("::", 1)[1]
            store.log_click(interaction.guild_id, custom_id, interaction.user)
            await _execute_tag(interaction, store, tag_name, "")
            try:
                await interaction.followup.send(
                    f"📝 Đã ghi nhận: {interaction.user.mention} bấm nút lúc "
                    f"{datetime.now().strftime('%H:%M:%S')}",
                    ephemeral=True,
                )
            except Exception:
                pass
            return

        # Nút vote poll — MỚI: ghi log + xác nhận vote riêng cho người bấm
        if custom_id.startswith("cc_poll::"):
            _, poll_id, idx_str = custom_id.split("::")
            idx = int(idx_str)
            poll = store.polls.find_one({"_id": poll_id})
            if not poll:
                return await interaction.response.send_message("⚠️ Khảo sát không còn tồn tại!", ephemeral=True)

            store.log_click(interaction.guild_id, custom_id, interaction.user)
            vote_key = f"{poll_id}:{interaction.user.id}"
            existing = poll_votes_col.find_one({"_id": vote_key})
            if existing and existing.get("choice") == idx:
                return await interaction.response.send_message("⚠️ Bạn đã vote lựa chọn này rồi!", ephemeral=True)
            poll_votes_col.update_one({"_id": vote_key}, {"$set": {"poll_id": poll_id, "choice": idx}}, upsert=True)

            counts = [poll_votes_col.count_documents({"poll_id": poll_id, "choice": i}) for i in range(len(poll["options"]))]
            desc = "\n".join(f"{i+1}️⃣ **{opt}** — {counts[i]} vote" for i, opt in enumerate(poll["options"]))
            embed = discord.Embed(title=f"📊 {poll['question']}", description=desc, color=discord.Color.blurple())
            await interaction.response.edit_message(embed=embed)
            try:
                await interaction.followup.send(
                    f"✅ Đã ghi nhận vote của bạn: **{poll['options'][idx]}**", ephemeral=True)
            except Exception:
                pass
            return

        # Nút tham gia giveaway — MỚI
        if custom_id.startswith("cc_gw::"):
            gid = custom_id.split("::", 1)[1]
            gw = store.get_giveaway(gid)
            if not gw or gw.get("ended"):
                return await interaction.response.send_message(
                    "⚠️ Giveaway đã kết thúc hoặc không tồn tại!", ephemeral=True)
            store.log_click(interaction.guild_id, custom_id, interaction.user)
            uid = str(interaction.user.id)
            if uid in gw.get("entries", []):
                return await interaction.response.send_message("⚠️ Bạn đã tham gia giveaway này rồi!", ephemeral=True)
            store.add_giveaway_entry(gid, interaction.user.id)
            return await interaction.response.send_message(
                f"✅ Bạn đã tham gia giveaway **{gw['prize']}**! Chúc may mắn 🍀", ephemeral=True)

        # Nút vote góp ý (👍/👎) — MỚI
        if custom_id.startswith("cc_sugg::"):
            _, sid, direction = custom_id.split("::")
            store.log_click(interaction.guild_id, custom_id, interaction.user)
            doc = store.vote_suggestion(sid, interaction.user.id, direction == "up")
            if not doc:
                return await interaction.response.send_message("⚠️ Góp ý không còn tồn tại!", ephemeral=True)
            embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title="💡 GÓP Ý")
            try:
                embed.set_field_at(0, name="👍", value=str(len(doc.get("up", []))), inline=True)
                embed.set_field_at(1, name="👎", value=str(len(doc.get("down", []))), inline=True)
            except Exception:
                pass
            await interaction.response.edit_message(embed=embed)
            try:
                await interaction.followup.send(
                    f"✅ Đã ghi nhận vote **{'👍' if direction == 'up' else '👎'}** của bạn!", ephemeral=True)
            except Exception:
                pass
            return

    bot.add_listener(on_raw_interaction, "on_interaction")

    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot:
            return
        emoji_str = str(payload.emoji)
        rr = store.get_reactrole(payload.message_id, emoji_str)
        if not rr:
            return
        guild = bot.get_guild(rr["guild_id"])
        if not guild:
            return
        role = guild.get_role(rr["role_id"])
        member = guild.get_member(payload.user_id)
        if role and member:
            try:
                await member.add_roles(role, reason="Reaction Role")
            except Exception:
                pass

    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
        emoji_str = str(payload.emoji)
        rr = store.get_reactrole(payload.message_id, emoji_str)
        if not rr:
            return
        guild = bot.get_guild(rr["guild_id"])
        if not guild:
            return
        role = guild.get_role(rr["role_id"])
        member = guild.get_member(payload.user_id)
        if role and member:
            try:
                await member.remove_roles(role, reason="Reaction Role gỡ bỏ")
            except Exception:
                pass

    bot.add_listener(on_raw_reaction_add, "on_raw_reaction_add")
    bot.add_listener(on_raw_reaction_remove, "on_raw_reaction_remove")

    print("[custom_commands] Đã gắn module thành công (bản nâng cấp: log click, giveaway, afk, "
          "suggestion, welcome, menu) — nhớ chạy /synccmd 1 lần để Discord hiện lệnh /")
    return store
