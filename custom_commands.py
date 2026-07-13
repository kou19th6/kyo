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
#   /poll       — tạo khảo sát nhanh có nút bấm vote
#   /tools      — bảng hướng dẫn tổng hợp mọi công cụ + cú pháp biến
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
from discord.ext import commands
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
DEFAULT_TAG_COOLDOWN    = 3       # giây, tránh spam chạy tag
OWNER_IDS_FOR_SYNC      = []      # điền ID chủ bot vào đây nếu muốn giới hạn /synccmd

# =====================================================================
# TEMPLATE ENGINE — AN TOÀN, KHÔNG EVAL CODE
# =====================================================================
# Cú pháp biến hỗ trợ trong nội dung tag / embed / trigger:
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
        self.tags          = db["cc_tags"]
        self.guild_vars    = db["cc_guild_vars"]
        self.user_vars     = db["cc_user_vars"]
        self.embeds        = db["cc_embeds"]
        self.triggers      = db["cc_triggers"]
        self.reactroles    = db["cc_reactroles"]
        self.polls         = db["cc_polls"]
        self._cooldowns    = {}  # {(guild_id, tag_name, user_id): datetime}

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
    # /button — gắn nút bấm chạy 1 tag có sẵn (không cần gõ lệnh)
    # ══════════════════════════════════════════════════════════════
    @bot.tree.command(name="button", description="Tạo 1 tin nhắn có nút bấm — bấm vào sẽ tự chạy 1 tag")
    @app_commands.describe(tag_name="Tên tag đã tạo bằng /tag create", label="Chữ hiển thị trên nút",
                            message="Nội dung tin nhắn đi kèm nút (tuỳ chọn)")
    async def button_cmd(interaction: discord.Interaction, tag_name: str, label: str, message: str = "\u200b"):
        doc = store.get_tag(interaction.guild_id, tag_name)
        if not doc:
            return await interaction.response.send_message(f"⚠️ Chưa có tag **{tag_name}**! Tạo bằng `/tag create` trước.", ephemeral=True)
        view = RunTagButton(tag_name, label, discord.ButtonStyle.primary)
        await interaction.response.send_message(content=message, view=view)

    # ══════════════════════════════════════════════════════════════
    # /poll — tạo khảo sát nhanh có nút vote
    # ══════════════════════════════════════════════════════════════
    poll_votes_col = db["cc_poll_votes"]

    @bot.tree.command(name="poll", description="Tạo khảo sát nhanh với tối đa 5 lựa chọn (bấm nút để vote)")
    @app_commands.describe(question="Câu hỏi khảo sát",
                            option1="Lựa chọn 1", option2="Lựa chọn 2",
                            option3="Lựa chọn 3 (tuỳ chọn)", option4="Lựa chọn 4 (tuỳ chọn)",
                            option5="Lựa chọn 5 (tuỳ chọn)")
    async def poll_cmd(interaction: discord.Interaction, question: str, option1: str, option2: str,
                        option3: str = None, option4: str = None, option5: str = None):
        options = [o for o in [option1, option2, option3, option4, option5] if o]
        poll_id = f"{interaction.guild_id}_{int(datetime.now().timestamp())}"

        embed = discord.Embed(title=f"📊 {question}", color=discord.Color.blurple())
        counts = "\n".join(f"{i+1}️⃣ **{opt}** — 0 vote" for i, opt in enumerate(options))
        embed.description = counts
        embed.set_footer(text=f"Khảo sát bởi {interaction.user.display_name}")

        view = PollView(poll_id, options)
        await interaction.response.send_message(embed=embed, view=view)
        sent = await interaction.original_response()

        store.polls.insert_one({
            "_id": poll_id, "message_id": sent.id, "guild_id": interaction.guild_id,
            "question": question, "options": options,
        })

    # ══════════════════════════════════════════════════════════════
    # /tools — hướng dẫn tổng hợp
    # ══════════════════════════════════════════════════════════════
    @bot.tree.command(name="tools", description="Xem hướng dẫn toàn bộ công cụ tự tạo tính năng")
    async def tools_cmd(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🧰 BỘ CÔNG CỤ TỰ SÁNG TẠO",
            description=(
                "**/tag** — tạo lệnh riêng của bạn\n"
                "  `/tag create name:chao content:Xin chào {user}!`\n"
                "  `/tag run name:chao`\n\n"
                "**/var** — biến dùng trong tag ({var:ten} / {uvar:ten})\n"
                "  `/var set key:diem value:100`\n\n"
                "**/embed** — tạo embed bằng form, gửi lại nhiều lần\n"
                "  `/embed create name:thongbao` → điền form\n"
                "  `/embed send name:thongbao`\n\n"
                "**/trigger** — tự trả lời khi ai gõ từ khóa\n"
                "  `/trigger add keyword:xin chào response:Chào {user}!`\n\n"
                "**/reactrole** — gắn role khi bấm emoji\n"
                "  `/reactrole add message_id:... emoji:✅ role:@Member`\n\n"
                "**/button** — nút bấm chạy tag có sẵn\n"
                "  `/button tag_name:chao label:Chào hỏi`\n\n"
                "**/poll** — khảo sát nhanh có nút vote\n"
                "  `/poll question:Bạn thích gì? option1:A option2:B`"
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="🧩 CÚ PHÁP BIẾN DÙNG TRONG NỘI DUNG",
            value=(
                "`{user}` `{user.mention}` `{user.id}` `{user.avatar}`\n"
                "`{server}` `{server.id}` `{channel}` `{channel.mention}`\n"
                "`{args}` `{count}` `{random:1-100}` `{choice:a|b|c}`\n"
                "`{var:ten_bien}` `{uvar:ten_bien_rieng}`"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
    # LẮNG NGHE SỰ KIỆN: trigger tự động + nút tag + nút poll + reaction role
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

    async def on_raw_interaction(interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")

        # Nút chạy tag
        if custom_id.startswith("cc_tagbtn::"):
            tag_name = custom_id.split("::", 1)[1]
            await _execute_tag(interaction, store, tag_name, "")
            return

        # Nút vote poll
        if custom_id.startswith("cc_poll::"):
            _, poll_id, idx_str = custom_id.split("::")
            idx = int(idx_str)
            poll = store.polls.find_one({"_id": poll_id})
            if not poll:
                return await interaction.response.send_message("⚠️ Khảo sát không còn tồn tại!", ephemeral=True)

            vote_key = f"{poll_id}:{interaction.user.id}"
            existing = poll_votes_col.find_one({"_id": vote_key})
            if existing and existing.get("choice") == idx:
                return await interaction.response.send_message("⚠️ Bạn đã vote lựa chọn này rồi!", ephemeral=True)
            poll_votes_col.update_one({"_id": vote_key}, {"$set": {"poll_id": poll_id, "choice": idx}}, upsert=True)

            counts = [poll_votes_col.count_documents({"poll_id": poll_id, "choice": i}) for i in range(len(poll["options"]))]
            desc = "\n".join(f"{i+1}️⃣ **{opt}** — {counts[i]} vote" for i, opt in enumerate(poll["options"]))
            embed = discord.Embed(title=f"📊 {poll['question']}", description=desc, color=discord.Color.blurple())
            await interaction.response.edit_message(embed=embed)
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

    print("[custom_commands] Đã gắn module thành công — nhớ chạy /synccmd 1 lần để Discord hiện lệnh /")
    return store
