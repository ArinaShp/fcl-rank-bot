from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Iterable

import discord
from aiohttp import web
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")
GUILD_ID_RAW: Final[str | None] = os.getenv("GUILD_ID")
ROLE_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ROLE_CHANNEL_ID")
LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("LOG_CHANNEL_ID")
PORT: Final[int] = int(os.getenv("PORT", "10000"))
DATABASE_PATH: Final[str] = os.getenv("DATABASE_PATH", "fcl_management.db")

GUILD_ID: Final[int | None] = int(GUILD_ID_RAW) if GUILD_ID_RAW else None
ROLE_CHANNEL_ID: Final[int | None] = int(ROLE_CHANNEL_ID_RAW) if ROLE_CHANNEL_ID_RAW else None
LOG_CHANNEL_ID: Final[int | None] = int(LOG_CHANNEL_ID_RAW) if LOG_CHANNEL_ID_RAW else None

MANAGER_ROLE_NAMES: Final[set[str]] = {
    "Владелец",
    "Администратор",
    "Первая Без Лица",
    "Голос Без Лица",
}

RANK_ROLE_NAMES: Final[tuple[str, ...]] = (
    "Призванный",
    "Отказавшийся",
    "Принятый Обрядом",
    "Носитель Знака",
    "Хранитель Следа",
    "Собиратель Личин",
    "Проводник Лика",
    "Хранитель Печати",
    "Длань Обряда",
    "Голос Без Лица",
    "Первая Без Лица",
)

FAMILY_ROLE_NAMES: Final[set[str]] = set(RANK_ROLE_NAMES)


class OptionalVoiceWarningFilter(logging.Filter):
    HIDDEN_PARTS: Final[tuple[str, ...]] = (
        "PyNaCl is not installed",
        "davey is not installed",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(part in message for part in self.HIDDEN_PARTS)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
for handler in logging.getLogger().handlers:
    handler.addFilter(OptionalVoiceWarningFilter())
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
logger = logging.getLogger("fcl-management")


def validate_environment() -> None:
    if not TOKEN:
        raise RuntimeError("Не найден DISCORD_TOKEN. Добавь токен в переменные Render.")
    if GUILD_ID is None:
        logger.warning("GUILD_ID не указан. Команды будут синхронизированы глобально.")
    if ROLE_CHANNEL_ID is None:
        logger.warning("ROLE_CHANNEL_ID не указан. Команды будут доступны во всех каналах.")
    if LOG_CHANNEL_ID is None:
        logger.warning("LOG_CHANNEL_ID не указан. Кадровый журнал будет отключён.")


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS rank_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_rank TEXT NOT NULL,
                new_rank TEXT NOT NULL,
                reason TEXT
            )
            """
        )
        self.connection.commit()

    def add_history(
        self,
        *,
        guild_id: int,
        member_id: int,
        actor_id: int,
        action: str,
        old_rank: str,
        new_rank: str,
        reason: str | None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO rank_history (
                created_at, guild_id, member_id, actor_id,
                action, old_rank, new_rank, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                guild_id,
                member_id,
                actor_id,
                action,
                old_rank,
                new_rank,
                reason,
            ),
        )
        self.connection.commit()

    def get_history(
        self,
        *,
        guild_id: int,
        member_id: int,
        limit: int = 10,
    ) -> list[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT created_at, actor_id, action, old_rank, new_rank, reason
            FROM rank_history
            WHERE guild_id = ? AND member_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (guild_id, member_id, limit),
        ).fetchall()

    def get_stats(self, *, guild_id: int, member_id: int) -> tuple[int, int, int]:
        rows = self.connection.execute(
            """
            SELECT action, COUNT(*) AS amount
            FROM rank_history
            WHERE guild_id = ? AND member_id = ?
            GROUP BY action
            """,
            (guild_id, member_id),
        ).fetchall()
        counters = {str(row["action"]): int(row["amount"]) for row in rows}
        return (
            sum(counters.values()),
            counters.get("Повышение", 0),
            counters.get("Понижение", 0),
        )


db = Database(DATABASE_PATH)


def has_manager_access(member: discord.Member) -> bool:
    return (
        member.guild.owner_id == member.id
        or member.guild_permissions.administrator
        or any(role.name in MANAGER_ROLE_NAMES for role in member.roles)
    )


def get_current_rank(member: discord.Member) -> discord.Role | None:
    ranks = [role for role in member.roles if role.name in RANK_ROLE_NAMES]
    return max(ranks, key=lambda role: role.position) if ranks else None


def get_rank_index(member: discord.Member) -> int | None:
    rank = get_current_rank(member)
    return RANK_ROLE_NAMES.index(rank.name) if rank else None


def get_role(guild: discord.Guild, name: str) -> discord.Role | None:
    return discord.utils.get(guild.roles, name=name)


def get_named_roles(member: discord.Member, names: Iterable[str]) -> list[discord.Role]:
    names_set = set(names)
    return [role for role in member.roles if role.name in names_set]


def ensure_bot_can_manage(guild: discord.Guild, roles: Iterable[discord.Role]) -> None:
    bot_member = guild.me
    if bot_member is None:
        raise RuntimeError("Не удалось определить роль бота на сервере.")
    blocked = [role for role in roles if role >= bot_member.top_role]
    if blocked:
        names = ", ".join(f"«{role.name}»" for role in blocked)
        raise PermissionError(
            f"Бот не может управлять ролями {names}. Подними роль бота выше указанных ролей."
        )


async def send_private(
    interaction: discord.Interaction,
    content: str | None = None,
    *,
    embed: discord.Embed | None = None,
    view: discord.ui.View | None = None,
) -> None:
    payload: dict[str, object] = {
        "content": content,
        "ephemeral": True,
    }

    if embed is not None:
        payload["embed"] = embed

    if view is not None:
        payload["view"] = view

    if interaction.response.is_done():
        await interaction.followup.send(**payload)
    else:
        await interaction.response.send_message(**payload)


async def validate_manager(interaction: discord.Interaction) -> discord.Member | None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await send_private(interaction, "Команда доступна только на сервере.")
        return None
    if ROLE_CHANNEL_ID is not None and interaction.channel_id != ROLE_CHANNEL_ID:
        await send_private(interaction, "Команда доступна только в закрытом канале управления.")
        return None
    if not has_manager_access(interaction.user):
        await send_private(interaction, "У тебя нет права управлять составом.")
        return None
    return interaction.user


async def write_log(
    *,
    guild: discord.Guild,
    title: str,
    member: discord.Member,
    actor: discord.Member,
    old_rank: str,
    new_rank: str,
    reason: str | None,
) -> None:
    if LOG_CHANNEL_ID is None:
        return
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        logger.warning("Канал журнала не найден или не является текстовым.")
        return

    embed = discord.Embed(title=title, color=discord.Color.purple(), timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Участник", value=member.mention, inline=True)
    embed.add_field(name="Изменил(а)", value=actor.mention, inline=True)
    embed.add_field(name="Изменение", value=f"{old_rank} → **{new_rank}**", inline=False)
    if reason:
        embed.add_field(name="Причина", value=reason, inline=False)
    embed.set_footer(text="The Faceless Ones • кадровый журнал")

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        logger.error("Бот не может отправлять сообщения в канал журнала.")
    except discord.HTTPException as error:
        logger.error("Не удалось отправить запись в журнал: %s", error)


async def notify_member(member: discord.Member, *, title: str, text: str) -> None:
    embed = discord.Embed(title=title, description=text, color=discord.Color.purple())
    embed.set_footer(text="The Faceless Ones")
    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        logger.info("Личные сообщения участника %s закрыты.", member.id)
    except discord.HTTPException as error:
        logger.warning("Не удалось отправить личное сообщение участнику %s: %s", member.id, error)


async def replace_rank(
    *,
    member: discord.Member,
    actor: discord.Member,
    new_rank_name: str,
    action: str,
    reason: str | None = None,
) -> tuple[str, str]:
    guild = member.guild
    old_roles = get_named_roles(member, RANK_ROLE_NAMES)
    old_rank = get_current_rank(member)
    old_rank_text = old_rank.name if old_rank else "не назначен"
    new_role = get_role(guild, new_rank_name)
    if new_role is None:
        raise LookupError(f"Роль «{new_rank_name}» не найдена на сервере.")

    ensure_bot_can_manage(guild, [*old_roles, new_role])
    audit_reason = f"FCL: {action}. Изменил(а): {actor}" + (f". Причина: {reason}" if reason else "")

    if old_roles:
        await member.remove_roles(*old_roles, reason=audit_reason)
    await member.add_roles(new_role, reason=audit_reason)

    db.add_history(
        guild_id=guild.id,
        member_id=member.id,
        actor_id=actor.id,
        action=action,
        old_rank=old_rank_text,
        new_rank=new_role.name,
        reason=reason,
    )
    await write_log(
        guild=guild,
        title=action,
        member=member,
        actor=actor,
        old_rank=old_rank_text,
        new_rank=new_role.name,
        reason=reason,
    )
    return old_rank_text, new_role.name


async def remove_family_roles(
    *,
    member: discord.Member,
    actor: discord.Member,
    reason: str,
) -> tuple[str, str]:
    guild = member.guild
    roles = get_named_roles(member, FAMILY_ROLE_NAMES)
    old_rank = get_current_rank(member)
    old_rank_text = old_rank.name if old_rank else "не назначен"
    ensure_bot_can_manage(guild, roles)

    if roles:
        await member.remove_roles(
            *roles,
            reason=f"FCL: исключение. Изменил(а): {actor}. Причина: {reason}",
        )

    new_rank_text = "исключён из состава"
    db.add_history(
        guild_id=guild.id,
        member_id=member.id,
        actor_id=actor.id,
        action="Исключение",
        old_rank=old_rank_text,
        new_rank=new_rank_text,
        reason=reason,
    )
    await write_log(
        guild=guild,
        title="Исключение",
        member=member,
        actor=actor,
        old_rank=old_rank_text,
        new_rank=new_rank_text,
        reason=reason,
    )
    return old_rank_text, new_rank_text


def history_embed(member: discord.Member, guild: discord.Guild) -> discord.Embed:
    rows = db.get_history(guild_id=guild.id, member_id=member.id, limit=10)
    embed = discord.Embed(title=f"История: {member.display_name}", color=discord.Color.purple())
    embed.set_thumbnail(url=member.display_avatar.url)
    if not rows:
        embed.description = "Записей пока нет."
        return embed

    lines: list[str] = []
    for row in rows:
        moment = datetime.fromisoformat(str(row["created_at"]))
        line = (
            f"**{row['action']}** — {row['old_rank']} → {row['new_rank']}\n"
            f"{discord.utils.format_dt(moment, style='d')} • <@{row['actor_id']}>"
        )
        if row["reason"]:
            line += f"\nПричина: {row['reason']}"
        lines.append(line)
    embed.description = "\n\n".join(lines)
    embed.set_footer(text="Последние 10 изменений")
    return embed


def member_card_embed(member: discord.Member, guild: discord.Guild) -> discord.Embed:
    rank = get_current_rank(member)
    total, promotions, demotions = db.get_stats(guild_id=guild.id, member_id=member.id)
    latest = db.get_history(guild_id=guild.id, member_id=member.id, limit=1)

    embed = discord.Embed(
        title="Карточка участника",
        description=member.mention,
        color=discord.Color.purple(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Текущий ранг", value=f"**{rank.name if rank else 'не назначен'}**", inline=False)
    embed.add_field(
        name="На сервере с",
        value=discord.utils.format_dt(member.joined_at, style="D") if member.joined_at else "неизвестно",
        inline=True,
    )
    embed.add_field(name="Изменений", value=str(total), inline=True)
    embed.add_field(name="Повышений", value=str(promotions), inline=True)
    embed.add_field(name="Понижений", value=str(demotions), inline=True)

    if latest:
        moment = datetime.fromisoformat(str(latest[0]["created_at"]))
        embed.add_field(
            name="Последнее изменение",
            value=(
                f"{latest[0]['old_rank']} → **{latest[0]['new_rank']}**\n"
                f"{discord.utils.format_dt(moment, style='R')}"
            ),
            inline=False,
        )
    embed.set_footer(text="The Faceless Ones • FCL Management")
    return embed


class ReasonModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        target: discord.Member,
        action: str,
        new_rank_name: str | None = None,
    ) -> None:
        super().__init__(title=title)
        self.target = target
        self.action_name = action
        self.new_rank_name = new_rank_name
        self.reason = discord.ui.TextInput(
            label="Причина",
            placeholder="Укажи причину решения",
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        actor = await validate_manager(interaction)
        if actor is None:
            return
        try:
            if self.action_name == "Исключение":
                old_rank, new_rank = await remove_family_roles(
                    member=self.target,
                    actor=actor,
                    reason=str(self.reason),
                )
                await notify_member(
                    self.target,
                    title="Исключение из состава",
                    text=f"Твоё участие в **The Faceless Ones** завершено.\n\nПричина: {self.reason}",
                )
            else:
                if self.new_rank_name is None:
                    raise RuntimeError("Не указан новый ранг.")
                old_rank, new_rank = await replace_rank(
                    member=self.target,
                    actor=actor,
                    new_rank_name=self.new_rank_name,
                    action=self.action_name,
                    reason=str(self.reason),
                )
                await notify_member(
                    self.target,
                    title=self.action_name,
                    text=f"Твой текущий ранг — **«{new_rank}»**.",
                )
        except (PermissionError, LookupError, RuntimeError) as error:
            await send_private(interaction, str(error))
            return
        except discord.Forbidden:
            await send_private(
                interaction,
                "Discord запретил изменение ролей. Проверь право «Управлять ролями» и положение роли бота.",
            )
            return
        except discord.HTTPException as error:
            logger.exception("Ошибка Discord при изменении роли: %s", error)
            await send_private(interaction, "Discord не смог выполнить изменение роли. Повтори попытку позже.")
            return

        await interaction.response.send_message(
            f"Готово: {self.target.mention}\n**{old_rank} → {new_rank}**",
            ephemeral=True,
        )


class RankSelect(discord.ui.Select):
    def __init__(self, target: discord.Member) -> None:
        self.target = target
        super().__init__(
            placeholder="Выбери новый ранг",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=name, value=name) for name in RANK_ROLE_NAMES],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if await validate_manager(interaction) is None:
            return
        selected = self.values[0]
        current = get_current_rank(self.target)
        if current and current.name == selected:
            await send_private(interaction, f"У {self.target.mention} уже установлен ранг **«{selected}»**.")
            return
        await interaction.response.send_modal(
            ReasonModal(
                title="Назначение ранга",
                target=self.target,
                action="Назначение ранга",
                new_rank_name=selected,
            )
        )


class RankSelectView(discord.ui.View):
    def __init__(self, target: discord.Member) -> None:
        super().__init__(timeout=180)
        self.add_item(RankSelect(target))


class ManagementView(discord.ui.View):
    def __init__(self, target: discord.Member) -> None:
        super().__init__(timeout=300)
        self.target = target

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await validate_manager(interaction) is not None

    @discord.ui.button(label="Повысить", style=discord.ButtonStyle.success, row=0)
    async def promote(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        index = get_rank_index(self.target)
        if index is None:
            new_rank = RANK_ROLE_NAMES[0]
        elif index >= len(RANK_ROLE_NAMES) - 1:
            await send_private(interaction, "У участника уже высший ранг.")
            return
        else:
            new_rank = RANK_ROLE_NAMES[index + 1]
        await interaction.response.send_modal(
            ReasonModal(
                title="Повышение",
                target=self.target,
                action="Повышение",
                new_rank_name=new_rank,
            )
        )

    @discord.ui.button(label="Понизить", style=discord.ButtonStyle.secondary, row=0)
    async def demote(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        index = get_rank_index(self.target)
        if index is None:
            await send_private(interaction, "У участника нет ранговой роли.")
            return
        if index == 0:
            await send_private(interaction, "У участника уже самый низкий ранг.")
            return
        await interaction.response.send_modal(
            ReasonModal(
                title="Понижение",
                target=self.target,
                action="Понижение",
                new_rank_name=RANK_ROLE_NAMES[index - 1],
            )
        )

    @discord.ui.button(label="Назначить ранг", style=discord.ButtonStyle.primary, row=0)
    async def assign(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Выбери ранг:",
            view=RankSelectView(self.target),
            ephemeral=True,
        )

    @discord.ui.button(label="История", style=discord.ButtonStyle.secondary, row=1)
    async def history(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is not None:
            await interaction.response.send_message(
                embed=history_embed(self.target, interaction.guild),
                ephemeral=True,
            )

    @discord.ui.button(label="Исключить", style=discord.ButtonStyle.danger, row=1)
    async def exclude(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            ReasonModal(title="Исключение", target=self.target, action="Исключение")
        )

    @discord.ui.button(label="Обновить", style=discord.ButtonStyle.secondary, row=1)
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is not None:
            await interaction.response.edit_message(
                embed=member_card_embed(self.target, interaction.guild),
                view=ManagementView(self.target),
            )


class MemberSelect(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(placeholder="Выбери участника", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        selected = self.values[0]
        if not isinstance(selected, discord.Member):
            await send_private(interaction, "Не удалось выбрать участника сервера.")
            return
        if selected.id == interaction.guild.owner_id:
            await send_private(interaction, "Discord не позволяет изменять роли владельца сервера.")
            return
        await interaction.response.edit_message(
            content=None,
            embed=member_card_embed(selected, interaction.guild),
            view=ManagementView(selected),
        )


class MemberSelectView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=180)
        self.add_item(MemberSelect())


class FCLClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = False
        intents.presences = False

        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.web_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        if GUILD_ID is not None:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()

        logger.info("Синхронизировано команд: %s", len(synced))
        self.web_runner = await start_web_server()

    async def close(self) -> None:
        if self.web_runner is not None:
            await self.web_runner.cleanup()
        db.connection.close()
        await super().close()


client = FCLClient()
tree = client.tree


async def health(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "online",
            "service": "FCL Management",
            "discord_ready": client.is_ready(),
        }
    )


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Web-порт открыт: %s", PORT)
    return runner


@client.event
async def on_ready() -> None:
    if client.user is None:
        return
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(name="Управление составом"),
    )
    logger.info("Бот запущен: %s (%s)", client.user, client.user.id)


@client.event
async def on_disconnect() -> None:
    logger.warning("Соединение с Discord временно потеряно.")


@client.event
async def on_resumed() -> None:
    logger.info("Соединение с Discord восстановлено.")


@tree.command(name="управление", description="Открыть панель управления составом.")
async def management(interaction: discord.Interaction) -> None:
    if await validate_manager(interaction) is None:
        return
    embed = discord.Embed(
        title="FCL Management",
        description="Выбери участника, чтобы открыть его карточку.",
        color=discord.Color.purple(),
    )
    embed.set_footer(text="The Faceless Ones")
    await interaction.response.send_message(embed=embed, view=MemberSelectView(), ephemeral=True)


@tree.command(name="карточка", description="Показать карточку участника.")
@app_commands.describe(участник="Участник семьи")
async def card(interaction: discord.Interaction, участник: discord.Member) -> None:
    if await validate_manager(interaction) is None or interaction.guild is None:
        return
    await interaction.response.send_message(
        embed=member_card_embed(участник, interaction.guild),
        ephemeral=True,
    )


@tree.command(name="история", description="Показать историю изменений ранга участника.")
@app_commands.describe(участник="Участник семьи")
async def history_command(interaction: discord.Interaction, участник: discord.Member) -> None:
    if await validate_manager(interaction) is None or interaction.guild is None:
        return
    await interaction.response.send_message(
        embed=history_embed(участник, interaction.guild),
        ephemeral=True,
    )


@tree.command(name="состав", description="Показать количество участников по рангам.")
async def roster(interaction: discord.Interaction) -> None:
    if await validate_manager(interaction) is None or interaction.guild is None:
        return
    lines: list[str] = []
    total = 0
    for role_name in RANK_ROLE_NAMES:
        role = get_role(interaction.guild, role_name)
        count = len(role.members) if role else 0
        total += count
        lines.append(f"**{role_name}** — {count}")
    embed = discord.Embed(
        title="Состав The Faceless Ones",
        description="\n".join(lines),
        color=discord.Color.purple(),
    )
    embed.add_field(name="Всего ранговых назначений", value=str(total), inline=False)
    embed.set_footer(text="FCL Management")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="исключить", description="Исключить участника из состава семьи.")
@app_commands.describe(участник="Участник семьи")
async def exclude_command(interaction: discord.Interaction, участник: discord.Member) -> None:
    if await validate_manager(interaction) is None:
        return
    await interaction.response.send_modal(
        ReasonModal(title="Исключение", target=участник, action="Исключение")
    )


@tree.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    logger.exception("Ошибка slash-команды", exc_info=error)
    message = "При выполнении команды произошла ошибка. Проверь настройки ролей и переменные Render."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


validate_environment()
client.run(TOKEN)
