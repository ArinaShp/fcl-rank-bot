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
ACCESS_LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ACCESS_LOG_CHANNEL_ID")
DIPLOMACY_LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("DIPLOMACY_LOG_CHANNEL_ID")
PORT: Final[int] = int(os.getenv("PORT", "10000"))
DATABASE_PATH: Final[str] = os.getenv("DATABASE_PATH", "fcl_management.db")

GUILD_ID: Final[int | None] = int(GUILD_ID_RAW) if GUILD_ID_RAW else None
ROLE_CHANNEL_ID: Final[int | None] = int(ROLE_CHANNEL_ID_RAW) if ROLE_CHANNEL_ID_RAW else None
LOG_CHANNEL_ID: Final[int | None] = int(LOG_CHANNEL_ID_RAW) if LOG_CHANNEL_ID_RAW else None
ACCESS_LOG_CHANNEL_ID: Final[int | None] = (
    int(ACCESS_LOG_CHANNEL_ID_RAW) if ACCESS_LOG_CHANNEL_ID_RAW else LOG_CHANNEL_ID
)
DIPLOMACY_LOG_CHANNEL_ID: Final[int | None] = (
    int(DIPLOMACY_LOG_CHANNEL_ID_RAW)
    if DIPLOMACY_LOG_CHANNEL_ID_RAW
    else ACCESS_LOG_CHANNEL_ID
)

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

ACCESS_ROLE_NAME: Final[str] = "Призванный"
ACCESS_BUTTON_CUSTOM_ID: Final[str] = "fcl:access:join"

ACCESS_EMBED_TITLE: Final[str] = "ДОПУСК К THE FACELESS ONES"
ACCESS_EMBED_DESCRIPTION: Final[str] = (
    "Есть двери, которые не открываются случайным людям.\n\n"
    "The Faceless Ones принимает тех, чьё слово имеет вес, "
    "а присутствие не требует лишних доказательств.\n\n"
    "Здесь ценят сдержанность, верность и уважение к тем, кто стоит рядом.\n\n"
    "**Семья уже ждёт тех, кто готов идти этим путём. "
    "Осталось лишь сделать первый шаг.**"
)


ALLIANCE_ROLE_NAME: Final[str] = "Союзник"
ALLIANCE_BUTTON_CUSTOM_ID: Final[str] = "fcl:alliance:join"

ALLIANCE_EMBED_TITLE: Final[str] = "ДОСТУП К ПОСОЛЬСТВУ"
ALLIANCE_EMBED_DESCRIPTION: Final[str] = (
    "Есть союзы, которые заключаются ради выгоды, "
    "и есть те, что рождаются из взаимного уважения и доверия.\n\n"
    "The Faceless Ones открывает Посольство только тем, "
    "чьё слово имеет вес, а поступки подтверждают намерения.\n\n"
    "Здесь встречаются представители семей, объединённых общей целью "
    "и готовностью действовать сообща.\n\n"
    "**Пусть этот союз станет началом крепкого сотрудничества "
    "и взаимного доверия.**"
)



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
        logger.warning("ROLE_CHANNEL_ID не указан. Команды управления будут доступны во всех каналах.")
    if LOG_CHANNEL_ID is None:
        logger.warning("LOG_CHANNEL_ID не указан. Кадровый журнал будет отключён.")
    if ACCESS_LOG_CHANNEL_ID is None:
        logger.warning("ACCESS_LOG_CHANNEL_ID не указан. Журнал допуска будет отключён.")
    if DIPLOMACY_LOG_CHANNEL_ID is None:
        logger.warning("DIPLOMACY_LOG_CHANNEL_ID не указан. Журнал дипломатии будет отключён.")


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
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
            );

            CREATE TABLE IF NOT EXISTS member_profiles (
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                static_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, member_id),
                UNIQUE (guild_id, static_id)
            );

            CREATE TABLE IF NOT EXISTS access_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                static_id TEXT NOT NULL,
                role_name TEXT NOT NULL,
                old_nickname TEXT,
                new_nickname TEXT,
                dm_sent INTEGER NOT NULL DEFAULT 0,
                log_sent INTEGER NOT NULL DEFAULT 0
            );

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

    def save_profile(self, *, guild_id: int, member_id: int, static_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """
            INSERT INTO member_profiles (
                guild_id, member_id, static_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, member_id) DO UPDATE SET
                static_id = excluded.static_id,
                updated_at = excluded.updated_at
            """,
            (guild_id, member_id, static_id, now, now),
        )
        self.connection.commit()

    def get_static_id(self, *, guild_id: int, member_id: int) -> str | None:
        row = self.connection.execute(
            """
            SELECT static_id
            FROM member_profiles
            WHERE guild_id = ? AND member_id = ?
            """,
            (guild_id, member_id),
        ).fetchone()
        return str(row["static_id"]) if row else None

    def find_member_by_static_id(self, *, guild_id: int, static_id: str) -> int | None:
        row = self.connection.execute(
            """
            SELECT member_id
            FROM member_profiles
            WHERE guild_id = ? AND static_id = ?
            """,
            (guild_id, static_id),
        ).fetchone()
        return int(row["member_id"]) if row else None

    def add_access_event(
        self,
        *,
        guild_id: int,
        member_id: int,
        static_id: str,
        role_name: str,
        old_nickname: str | None,
        new_nickname: str | None,
        dm_sent: bool,
        log_sent: bool,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO access_events (
                created_at, guild_id, member_id, static_id, role_name,
                old_nickname, new_nickname,
                dm_sent, log_sent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                guild_id,
                member_id,
                static_id,
                role_name,
                old_nickname,
                new_nickname,
                int(dm_sent),
                int(log_sent),
            ),
        )
        self.connection.commit()



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


async def validate_manager(
    interaction: discord.Interaction,
    *,
    restrict_channel: bool = True,
) -> discord.Member | None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await send_private(interaction, "Команда доступна только на сервере.")
        return None
    if (
        restrict_channel
        and ROLE_CHANNEL_ID is not None
        and interaction.channel_id != ROLE_CHANNEL_ID
    ):
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


def build_member_nickname(role_name: str, static_id: str) -> str:
    nickname = f"{role_name} | {static_id}"
    return nickname[:32]


async def update_member_nickname(
    member: discord.Member,
    *,
    role_name: str,
    static_id: str,
    reason: str,
) -> tuple[str, bool]:
    nickname = build_member_nickname(role_name, static_id)
    try:
        await member.edit(nick=nickname, reason=reason)
        return nickname, True
    except (discord.Forbidden, discord.HTTPException):
        logger.warning("Не удалось изменить никнейм участника %s.", member.id)
        return nickname, False


async def send_access_log(
    *,
    member: discord.Member,
    static_id: str,
    nickname: str,
) -> bool:
    if ACCESS_LOG_CHANNEL_ID is None:
        return False

    channel = member.guild.get_channel(ACCESS_LOG_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        logger.warning("Канал журнала допуска не найден или не является текстовым.")
        return False

    embed = discord.Embed(
        title="НОВЫЙ ДОПУСК",
        description="Участник подтвердил своё вступление в The Faceless Ones.",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Участник", value=member.mention, inline=True)
    embed.add_field(name="Static ID", value=static_id, inline=True)
    embed.add_field(name="Стартовый ранг", value=ACCESS_ROLE_NAME, inline=True)
    embed.add_field(name="Идентификация", value=nickname, inline=False)
    embed.set_footer(text="The Faceless Ones • журнал допуска")

    try:
        await channel.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        logger.warning("Не удалось отправить запись в журнал допуска.")
        return False


async def send_access_dm(
    *,
    member: discord.Member,
    static_id: str,
) -> bool:
    identification = build_member_nickname(ACCESS_ROLE_NAME, static_id)

    embed = discord.Embed(
        title="ДОБРО ПОЖАЛОВАТЬ",
        description=(
            "Добро пожаловать в **The Faceless Ones**.\n\n"
            "Доступ открыт. С этого момента вы становитесь частью семьи, "
            "где доверие заслуживается поступками, а уважение сохраняется "
            "верностью своему слову.\n\n"
            "Теперь перед вами открыт внутренний мир семьи. Осмотритесь, "
            "познакомьтесь с её порядком и позвольте своему пути начаться."
        ),
        color=discord.Color.purple(),
    )
    embed.add_field(
        name="Ваше обозначение",
        value=identification,
        inline=False,
    )
    embed.set_footer(text="No face. One family. One purpose.")

    try:
        await member.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        logger.info(
            "Не удалось отправить приветствие участнику %s в личные сообщения.",
            member.id,
        )
        return False



async def send_alliance_log(
    *,
    member: discord.Member,
    static_id: str,
    nickname: str,
) -> bool:
    if DIPLOMACY_LOG_CHANNEL_ID is None:
        return False

    channel = member.guild.get_channel(DIPLOMACY_LOG_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        logger.warning("Канал журнала дипломатии не найден или не является текстовым.")
        return False

    embed = discord.Embed(
        title="НОВЫЙ СОЮЗНИК",
        description=(
            "Представителю союзной семьи предоставлен доступ "
            "к Посольству The Faceless Ones."
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Участник", value=member.mention, inline=True)
    embed.add_field(name="Static ID", value=static_id, inline=True)
    embed.add_field(name="Роль", value=ALLIANCE_ROLE_NAME, inline=True)
    embed.add_field(name="Идентификация", value=nickname, inline=False)
    embed.set_footer(text="The Faceless Ones • журнал дипломатии")

    try:
        await channel.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        logger.warning("Не удалось отправить запись в журнал дипломатии.")
        return False


async def send_alliance_dm(
    *,
    member: discord.Member,
    static_id: str,
) -> bool:
    identification = build_member_nickname(ALLIANCE_ROLE_NAME, static_id)

    embed = discord.Embed(
        title="ДОБРО ПОЖАЛОВАТЬ В ПОСОЛЬСТВО",
        description=(
            "Благодарим за принятое приглашение.\\n\\n"
            "Для вас открыт дипломатический раздел The Faceless Ones — "
            "пространство, где союзники обмениваются информацией, "
            "обсуждают совместные инициативы и поддерживают постоянную связь.\\n\\n"
            "Пусть это сотрудничество станет прочной основой "
            "для будущих совместных достижений."
        ),
        color=discord.Color.purple(),
    )
    embed.add_field(
        name="Ваше обозначение",
        value=identification,
        inline=False,
    )
    embed.set_footer(text="Trust builds alliances.")

    try:
        await member.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        logger.info(
            "Не удалось отправить дипломатическое приветствие участнику %s.",
            member.id,
        )
        return False


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

    static_id = db.get_static_id(guild_id=guild.id, member_id=member.id)
    if static_id:
        await update_member_nickname(
            member,
            role_name=new_role.name,
            static_id=static_id,
            reason=f"FCL: обновление никнейма после действия «{action}»",
        )

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




class AccessStaticIdModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="Подтверждение личности")
        self.static_id = discord.ui.TextInput(
            label="STATIC ID",
            placeholder="Укажите Static ID вашего персонажа",
            required=True,
            min_length=1,
            max_length=10,
        )
        self.add_item(self.static_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await send_private(interaction, "Получение доступа возможно только на сервере.")
            return

        member = interaction.user
        static_id = str(self.static_id).strip()

        if not static_id.isdigit():
            await send_private(interaction, "Static ID должен состоять только из цифр.")
            return

        existing_member_id = db.find_member_by_static_id(
            guild_id=interaction.guild.id,
            static_id=static_id,
        )
        if existing_member_id is not None and existing_member_id != member.id:
            await send_private(
                interaction,
                "Этот Static ID уже закреплён за другим участником. Обратитесь к руководству.",
            )
            return

        role = get_role(interaction.guild, ACCESS_ROLE_NAME)
        if role is None:
            await send_private(
                interaction,
                f"Роль «{ACCESS_ROLE_NAME}» не найдена. Обратитесь к руководству.",
            )
            return

        existing_rank = get_current_rank(member)
        if existing_rank is not None:
            stored_static_id = db.get_static_id(
                guild_id=interaction.guild.id,
                member_id=member.id,
            )
            details = (
                f" Ваш Static ID — **{stored_static_id}**."
                if stored_static_id
                else ""
            )
            await send_private(
                interaction,
                f"Доступ уже предоставлен. Ваш текущий ранг — **«{existing_rank.name}»**.{details}",
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        old_nickname = member.nick
        nickname = build_member_nickname(ACCESS_ROLE_NAME, static_id)

        try:
            ensure_bot_can_manage(interaction.guild, [role])
            await member.add_roles(
                role,
                reason="Самостоятельное получение доступа через FCL Management",
            )
        except PermissionError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send(
                "Бот не может выдать роль. Проверьте право «Управлять ролями» "
                "и положение роли бота.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            logger.exception("Не удалось выдать роль доступа.")
            await interaction.followup.send(
                "Не удалось выдать доступ. Повторите попытку позже.",
                ephemeral=True,
            )
            return

        db.save_profile(
            guild_id=interaction.guild.id,
            member_id=member.id,
            static_id=static_id,
        )

        _, nickname_changed = await update_member_nickname(
            member,
            role_name=ACCESS_ROLE_NAME,
            static_id=static_id,
            reason="Оформление участника после получения доступа",
        )

        db.add_history(
            guild_id=interaction.guild.id,
            member_id=member.id,
            actor_id=member.id,
            action="Получение доступа",
            old_rank="не назначен",
            new_rank=ACCESS_ROLE_NAME,
            reason=f"Самостоятельное подтверждение доступа. Static ID: {static_id}",
        )


        dm_sent = await send_access_dm(
            member=member,
            static_id=static_id,
        )

        log_sent = await send_access_log(
            member=member,
            static_id=static_id,
            nickname=nickname,
        )

        db.add_access_event(
            guild_id=interaction.guild.id,
            member_id=member.id,
            static_id=static_id,
            role_name=ACCESS_ROLE_NAME,
            old_nickname=old_nickname,
            new_nickname=nickname if nickname_changed else old_nickname,
            dm_sent=dm_sent,
            log_sent=log_sent,
        )

        result = discord.Embed(
            title="ДОСТУП ПРЕДОСТАВЛЕН",
            description=(
                "Добро пожаловать в **The Faceless Ones**.\n\n"
                "Доступ открыт. С этого момента вы становитесь частью семьи, "
                "где доверие заслуживается поступками, а уважение сохраняется "
                "верностью своему слову.\n\n"
                "Теперь перед вами открыт внутренний мир семьи. Осмотритесь, "
                "познакомьтесь с её порядком и позвольте своему пути начаться."
            ),
            color=discord.Color.purple(),
        )
        result.add_field(
            name="Ваше обозначение",
            value=(
                nickname
                if nickname_changed
                else f"{ACCESS_ROLE_NAME} | {static_id}"
            ),
            inline=False,
        )
        result.set_footer(text="No face. One family. One purpose.")

        await interaction.followup.send(embed=result, ephemeral=True)


class AccessButtonView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Получить доступ",
        style=discord.ButtonStyle.primary,
        custom_id=ACCESS_BUTTON_CUSTOM_ID,
    )
    async def receive_access(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(AccessStaticIdModal())


class AllianceStaticIdModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="Подтверждение личности")
        self.static_id = discord.ui.TextInput(
            label="STATIC ID",
            placeholder="Укажите Static ID вашего персонажа",
            required=True,
            min_length=1,
            max_length=10,
        )
        self.add_item(self.static_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await send_private(interaction, "Получение доступа возможно только на сервере.")
            return

        member = interaction.user
        static_id = str(self.static_id).strip()

        if not static_id.isdigit():
            await send_private(interaction, "Static ID должен состоять только из цифр.")
            return

        existing_member_id = db.find_member_by_static_id(
            guild_id=interaction.guild.id,
            static_id=static_id,
        )
        if existing_member_id is not None and existing_member_id != member.id:
            await send_private(
                interaction,
                "Этот Static ID уже закреплён за другим участником. Обратитесь к руководству.",
            )
            return

        alliance_role = get_role(interaction.guild, ALLIANCE_ROLE_NAME)
        if alliance_role is None:
            await send_private(
                interaction,
                f"Роль «{ALLIANCE_ROLE_NAME}» не найдена. Обратитесь к руководству.",
            )
            return

        if alliance_role in member.roles:
            stored_static_id = db.get_static_id(
                guild_id=interaction.guild.id,
                member_id=member.id,
            )
            details = (
                f" Ваш Static ID — **{stored_static_id}**."
                if stored_static_id
                else ""
            )
            await send_private(
                interaction,
                f"Доступ к Посольству уже предоставлен.{details}",
            )
            return

        family_rank = get_current_rank(member)
        if family_rank is not None:
            await send_private(
                interaction,
                "Вы уже состоите в составе The Faceless Ones. "
                "Союзный допуск для членов семьи не требуется.",
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        old_nickname = member.nick
        nickname = build_member_nickname(ALLIANCE_ROLE_NAME, static_id)

        try:
            ensure_bot_can_manage(interaction.guild, [alliance_role])
            await member.add_roles(
                alliance_role,
                reason="Самостоятельное получение доступа к Посольству",
            )
        except PermissionError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send(
                "Бот не может выдать роль. Проверьте право «Управлять ролями» "
                "и положение роли бота.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            logger.exception("Не удалось выдать роль союзника.")
            await interaction.followup.send(
                "Не удалось предоставить доступ. Повторите попытку позже.",
                ephemeral=True,
            )
            return

        db.save_profile(
            guild_id=interaction.guild.id,
            member_id=member.id,
            static_id=static_id,
        )

        _, nickname_changed = await update_member_nickname(
            member,
            role_name=ALLIANCE_ROLE_NAME,
            static_id=static_id,
            reason="Оформление представителя союзной семьи",
        )

        db.add_history(
            guild_id=interaction.guild.id,
            member_id=member.id,
            actor_id=member.id,
            action="Союзный допуск",
            old_rank="доступ отсутствовал",
            new_rank=ALLIANCE_ROLE_NAME,
            reason=f"Самостоятельное подтверждение доступа. Static ID: {static_id}",
        )

        dm_sent = await send_alliance_dm(
            member=member,
            static_id=static_id,
        )

        log_sent = await send_alliance_log(
            member=member,
            static_id=static_id,
            nickname=nickname,
        )

        db.add_access_event(
            guild_id=interaction.guild.id,
            member_id=member.id,
            static_id=static_id,
            role_name=ALLIANCE_ROLE_NAME,
            old_nickname=old_nickname,
            new_nickname=nickname if nickname_changed else old_nickname,
            dm_sent=dm_sent,
            log_sent=log_sent,
        )

        result = discord.Embed(
            title="ДОСТУП ПРЕДОСТАВЛЕН",
            description=(
                "Добро пожаловать в **Посольство The Faceless Ones**.\\n\\n"
                "Для вас открыт дипломатический раздел семьи, "
                "созданный для союзников и представителей дружественных организаций.\\n\\n"
                "Пусть наше сотрудничество строится на взаимном уважении, "
                "доверии и общей цели."
            ),
            color=discord.Color.purple(),
        )
        result.add_field(
            name="Ваше обозначение",
            value=(
                nickname
                if nickname_changed
                else f"{ALLIANCE_ROLE_NAME} | {static_id}"
            ),
            inline=False,
        )
        result.set_footer(text="Trust builds alliances.")

        await interaction.followup.send(embed=result, ephemeral=True)


class AllianceButtonView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Получить доступ",
        style=discord.ButtonStyle.primary,
        custom_id=ALLIANCE_BUTTON_CUSTOM_ID,
    )
    async def receive_access(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(AllianceStaticIdModal())


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
        self.add_view(AccessButtonView())
        self.add_view(AllianceButtonView())

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


@tree.command(
    name="создать-доступ",
    description="Опубликовать оформленную кнопку получения роли «Призванный».",
)
@app_commands.describe(
    баннер="Изображение для оформления сообщения",
)
async def create_access_message(
    interaction: discord.Interaction,
    баннер: discord.Attachment | None = None,
) -> None:
    if await validate_manager(interaction, restrict_channel=False) is None:
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        await send_private(interaction, "Сообщение можно создать только в текстовом канале.")
        return

    embed = discord.Embed(
        title=ACCESS_EMBED_TITLE,
        description=ACCESS_EMBED_DESCRIPTION,
        color=discord.Color.purple(),
    )
    embed.set_footer(text="The Faceless Ones • право быть среди своих")

    if баннер is not None:
        if баннер.content_type and not баннер.content_type.startswith("image/"):
            await send_private(interaction, "В качестве баннера необходимо загрузить изображение.")
            return
        embed.set_image(url=баннер.url)

    try:
        await interaction.channel.send(
            embed=embed,
            view=AccessButtonView(),
        )
    except discord.Forbidden:
        await send_private(interaction, "Бот не может отправлять сообщения в этот канал.")
        return
    except discord.HTTPException:
        logger.exception("Не удалось создать сообщение доступа.")
        await send_private(interaction, "Не удалось создать сообщение с кнопкой.")
        return

    await send_private(interaction, "Сообщение с кнопкой доступа опубликовано.")


@tree.command(
    name="создать-доступ-посольство",
    description="Опубликовать кнопку получения роли «Союзник».",
)
@app_commands.describe(
    баннер="Изображение для оформления сообщения",
)
async def create_alliance_access_message(
    interaction: discord.Interaction,
    баннер: discord.Attachment | None = None,
) -> None:
    if await validate_manager(interaction, restrict_channel=False) is None:
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        await send_private(interaction, "Сообщение можно создать только в текстовом канале.")
        return

    embed = discord.Embed(
        title=ALLIANCE_EMBED_TITLE,
        description=ALLIANCE_EMBED_DESCRIPTION,
        color=discord.Color.purple(),
    )
    embed.set_footer(text="The Faceless Ones • доверие объединяет")

    if баннер is not None:
        if баннер.content_type and not баннер.content_type.startswith("image/"):
            await send_private(interaction, "В качестве баннера необходимо загрузить изображение.")
            return
        embed.set_image(url=баннер.url)

    try:
        await interaction.channel.send(
            embed=embed,
            view=AllianceButtonView(),
        )
    except discord.Forbidden:
        await send_private(interaction, "Бот не может отправлять сообщения в этот канал.")
        return
    except discord.HTTPException:
        logger.exception("Не удалось создать сообщение доступа к Посольству.")
        await send_private(interaction, "Не удалось создать сообщение с кнопкой.")
        return

    await send_private(
        interaction,
        "Сообщение с кнопкой доступа к Посольству опубликовано.",
    )


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
