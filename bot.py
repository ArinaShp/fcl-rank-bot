from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final, Iterable

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")
GUILD_ID_RAW: Final[str | None] = os.getenv("GUILD_ID")
ROLE_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ROLE_CHANNEL_ID")
LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("LOG_CHANNEL_ID")
ACCESS_LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ACCESS_LOG_CHANNEL_ID")
DIPLOMACY_LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("DIPLOMACY_LOG_CHANNEL_ID")
WEEKLY_REPORT_CHANNEL_ID_RAW: Final[str | None] = os.getenv("WEEKLY_REPORT_CHANNEL_ID")
CHRONICLE_CHANNEL_ID_RAW: Final[str | None] = os.getenv("CHRONICLE_CHANNEL_ID")
ANNOUNCEMENT_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ANNOUNCEMENT_CHANNEL_ID")
ANNIVERSARY_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ANNIVERSARY_CHANNEL_ID")
HONOR_BOARD_CHANNEL_ID_RAW: Final[str | None] = os.getenv("HONOR_BOARD_CHANNEL_ID")
LEAVE_ROLE_NAME: Final[str] = os.getenv("LEAVE_ROLE_NAME", "В отпуске")
VETERAN_ROLE_NAME: Final[str] = os.getenv("VETERAN_ROLE_NAME", "Ветеран")
PLENIPOTENTIARY_ROLE_NAME: Final[str] = os.getenv(
    "PLENIPOTENTIARY_ROLE_NAME",
    "Полномочный Посол",
)
PORT: Final[int] = int(os.getenv("PORT", "10000"))
DATABASE_PATH: Final[str] = os.getenv("DATABASE_PATH", "fcl_management.db")

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ASSETS_DIR: Final[Path] = BASE_DIR / "assets"

BANNER_FILES: Final[dict[str, Path]] = {
    "promotion": ASSETS_DIR / "promotion.png",
    "achievement": ASSETS_DIR / "achievement.png",
    "anniversary": ASSETS_DIR / "anniversary.png",
    "chronicle": ASSETS_DIR / "chronicle.png",
    "weekly_report": ASSETS_DIR / "weekly_report.png",
    "plenipotentiary": ASSETS_DIR / "plenipotentiary.png",
    "alliance": ASSETS_DIR / "alliance.png",
    "honor_board": ASSETS_DIR / "honor_board.png",
}

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
WEEKLY_REPORT_CHANNEL_ID: Final[int | None] = (
    int(WEEKLY_REPORT_CHANNEL_ID_RAW) if WEEKLY_REPORT_CHANNEL_ID_RAW else None
)
CHRONICLE_CHANNEL_ID: Final[int | None] = (
    int(CHRONICLE_CHANNEL_ID_RAW) if CHRONICLE_CHANNEL_ID_RAW else None
)
ANNOUNCEMENT_CHANNEL_ID: Final[int | None] = (
    int(ANNOUNCEMENT_CHANNEL_ID_RAW) if ANNOUNCEMENT_CHANNEL_ID_RAW else None
)
ANNIVERSARY_CHANNEL_ID: Final[int | None] = (
    int(ANNIVERSARY_CHANNEL_ID_RAW) if ANNIVERSARY_CHANNEL_ID_RAW else None
)
HONOR_BOARD_CHANNEL_ID: Final[int | None] = (
    int(HONOR_BOARD_CHANNEL_ID_RAW) if HONOR_BOARD_CHANNEL_ID_RAW else None
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


AUTOMATIC_ACHIEVEMENTS: Final[dict[str, dict[str, object]]] = {
    "Первый шаг": {
        "description": (
            "За принятие своего места среди The Faceless Ones "
            "и начало пути внутри семьи."
        ),
        "points": 0,
    },
    "Ветеран семьи": {
        "description": (
            "За полгода рядом с The Faceless Ones, верность общему пути "
            "и вклад в историю семьи."
        ),
        "points": 3,
    },
}

MANUAL_ACHIEVEMENTS: Final[dict[str, dict[str, object]]] = {
    "Знак доверия": {
        "description": (
            "За надёжность, верность своему слову и поступки, "
            "укрепляющие доверие внутри семьи."
        ),
        "points": 2,
    },
    "Опора семьи": {
        "description": (
            "За постоянную поддержку участников, готовность прийти на помощь "
            "и вклад в сохранение единства The Faceless Ones."
        ),
        "points": 2,
    },
    "Безупречная служба": {
        "description": (
            "За ответственность, стабильность и безупречное исполнение "
            "возложенных обязанностей."
        ),
        "points": 2,
    },
    "След в истории": {
        "description": (
            "За вклад, ставший значимой частью истории "
            "и развития The Faceless Ones."
        ),
        "points": 3,
    },
    "Участник операции": {
        "description": (
            "За достойное участие в значимом мероприятии "
            "и вклад в достижение общей цели."
        ),
        "points": 1,
    },
    "Ключевой участник": {
        "description": (
            "За решающий вклад в подготовку или проведение важного события."
        ),
        "points": 3,
    },
    "Организатор": {
        "description": (
            "За инициативу, ответственность и высокий уровень "
            "организации семейного мероприятия."
        ),
        "points": 1,
    },
    "Наставник": {
        "description": (
            "За помощь новым участникам, передачу опыта "
            "и поддержку на первых этапах их пути."
        ),
        "points": 1,
    },
    "Хранитель традиций": {
        "description": (
            "За сохранение внутреннего порядка, ценностей "
            "и традиций The Faceless Ones."
        ),
        "points": 3,
    },
    "Голос союза": {
        "description": (
            "За достойное представление интересов The Faceless Ones "
            "и вклад в развитие дипломатических отношений."
        ),
        "points": 2,
    },
    "Укрепление союза": {
        "description": (
            "За действия, укрепившие взаимное доверие "
            "и сотрудничество между семьями."
        ),
        "points": 2,
    },
}

ACHIEVEMENT_CHOICES: Final[list[app_commands.Choice[str]]] = [
    app_commands.Choice(name=name, value=name)
    for name in MANUAL_ACHIEVEMENTS
]



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

db.connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS personnel_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        guild_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        actor_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        expires_at TEXT,
        status TEXT NOT NULL DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        guild_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        actor_id INTEGER NOT NULL,
        starts_at TEXT NOT NULL,
        ends_at TEXT NOT NULL,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS activity_log (
        guild_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        last_activity_at TEXT NOT NULL,
        source TEXT NOT NULL,
        PRIMARY KEY (guild_id, member_id)
    );

    CREATE TABLE IF NOT EXISTS mentorships (
        guild_id INTEGER NOT NULL,
        mentee_id INTEGER NOT NULL,
        mentor_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        PRIMARY KEY (guild_id, mentee_id)
    );

    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        guild_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        actor_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS chronicle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        guild_id INTEGER NOT NULL,
        actor_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS alliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        started_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        representative TEXT,
        description TEXT,
        UNIQUE (guild_id, name)
    );

    CREATE TABLE IF NOT EXISTS anniversary_events (
        guild_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        milestone_days INTEGER NOT NULL,
        announced_at TEXT NOT NULL,
        PRIMARY KEY (guild_id, member_id, milestone_days)
    );
    """
)
db.connection.commit()

achievement_columns = {
    str(row["name"])
    for row in db.connection.execute(
        "PRAGMA table_info(achievements)"
    ).fetchall()
}
if "points" not in achievement_columns:
    db.connection.execute(
        "ALTER TABLE achievements "
        "ADD COLUMN points INTEGER NOT NULL DEFAULT 1"
    )
    db.connection.commit()


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

    banner = attach_banner(embed, "achievement")
    try:
        if banner is not None:
            await channel.send(embed=embed, file=banner)
        else:
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


async def publish_rank_announcement(
    *,
    member: discord.Member,
    old_rank: str,
    new_rank: str,
    action: str,
) -> None:
    if ANNOUNCEMENT_CHANNEL_ID is None:
        return
    if action not in {"Повышение", "Назначение ранга"}:
        return

    channel = member.guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return

    embed = discord.Embed(
        title="НОВОЕ НАЗНАЧЕНИЕ",
        description=(
            f"Решением руководства {member.mention} занимает новое место "
            "в структуре The Faceless Ones."
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Предыдущий ранг", value=old_rank, inline=True)
    embed.add_field(name="Новый ранг", value=f"**{new_rank}**", inline=True)
    embed.set_footer(text="The Faceless Ones • путь продолжается")

    banner = attach_banner(embed, "promotion")
    try:
        if banner is not None:
            await channel.send(embed=embed, file=banner)
        else:
            await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        logger.warning("Не удалось опубликовать объявление о назначении.")


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
    await publish_rank_announcement(
        member=member,
        old_rank=old_rank_text,
        new_rank=new_role.name,
        action=action,
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
    personnel = get_personnel_counts(guild.id, member.id)
    mentor_id = get_mentor(guild.id, member.id)
    active_leave = get_active_leave(guild.id, member.id)

    embed.add_field(name="Поощрения", value=str(personnel.get("reward", 0)), inline=True)
    embed.add_field(name="Взыскания", value=str(personnel.get("discipline", 0)), inline=True)
    embed.add_field(name="Достижения", value=str(count_achievements(guild.id, member.id)), inline=True)
    embed.add_field(
        name="Наставник",
        value=f"<@{mentor_id}>" if mentor_id else "не назначен",
        inline=False,
    )
    if active_leave:
        leave_end = datetime.fromisoformat(str(active_leave["ends_at"]))
        embed.add_field(name="Отпуск", value=f"до {leave_end.strftime('%d.%m.%Y')}", inline=False)

    embed.set_footer(text="The Faceless Ones • FCL Management")
    return embed


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_activity(member: discord.Member, source: str) -> None:
    db.connection.execute(
        """
        INSERT INTO activity_log (guild_id, member_id, last_activity_at, source)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id, member_id) DO UPDATE SET
            last_activity_at = excluded.last_activity_at,
            source = excluded.source
        """,
        (member.guild.id, member.id, utc_now_iso(), source),
    )
    db.connection.commit()


def add_personnel_event(
    *,
    guild_id: int,
    member_id: int,
    actor_id: int,
    event_type: str,
    title: str,
    description: str | None,
    expires_at: str | None = None,
) -> None:
    db.connection.execute(
        """
        INSERT INTO personnel_events (
            created_at, guild_id, member_id, actor_id,
            event_type, title, description, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (utc_now_iso(), guild_id, member_id, actor_id, event_type, title, description, expires_at),
    )
    db.connection.commit()


def get_personnel_counts(guild_id: int, member_id: int) -> dict[str, int]:
    rows = db.connection.execute(
        """
        SELECT event_type, COUNT(*) AS amount
        FROM personnel_events
        WHERE guild_id = ? AND member_id = ? AND status = 'active'
        GROUP BY event_type
        """,
        (guild_id, member_id),
    ).fetchall()
    return {str(row["event_type"]): int(row["amount"]) for row in rows}


def get_active_leave(guild_id: int, member_id: int) -> sqlite3.Row | None:
    return db.connection.execute(
        """
        SELECT starts_at, ends_at, reason
        FROM leaves
        WHERE guild_id = ? AND member_id = ? AND status = 'active'
        ORDER BY id DESC LIMIT 1
        """,
        (guild_id, member_id),
    ).fetchone()


def get_mentor(guild_id: int, member_id: int) -> int | None:
    row = db.connection.execute(
        """
        SELECT mentor_id FROM mentorships
        WHERE guild_id = ? AND mentee_id = ? AND status = 'active'
        """,
        (guild_id, member_id),
    ).fetchone()
    return int(row["mentor_id"]) if row else None


def count_achievements(guild_id: int, member_id: int) -> int:
    row = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM achievements WHERE guild_id = ? AND member_id = ?",
        (guild_id, member_id),
    ).fetchone()
    return int(row["amount"]) if row else 0


async def send_personnel_log(
    *,
    guild: discord.Guild,
    title: str,
    description: str,
    member: discord.Member,
    actor: discord.Member,
) -> None:
    if LOG_CHANNEL_ID is None:
        return
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Участник", value=member.mention, inline=True)
    embed.add_field(name="Оформил(а)", value=actor.mention, inline=True)
    embed.set_footer(text="The Faceless Ones • личное дело")
    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        logger.warning("Не удалось отправить кадровую запись.")


def parse_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%d.%m.%Y").replace(tzinfo=timezone.utc)


class PersonnelEventModal(discord.ui.Modal):
    def __init__(self, *, target: discord.Member, event_type: str, title: str) -> None:
        super().__init__(title=title)
        self.target = target
        self.event_type = event_type
        self.event_title = discord.ui.TextInput(
            label="Наименование",
            placeholder="Краткое наименование записи",
            max_length=100,
        )
        self.description = discord.ui.TextInput(
            label="Основание",
            placeholder="Опишите причину или заслугу",
            style=discord.TextStyle.paragraph,
            max_length=700,
        )
        self.add_item(self.event_title)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        actor = await validate_manager(interaction)
        if actor is None:
            return
        add_personnel_event(
            guild_id=self.target.guild.id,
            member_id=self.target.id,
            actor_id=actor.id,
            event_type=self.event_type,
            title=str(self.event_title),
            description=str(self.description),
        )
        await send_personnel_log(
            guild=self.target.guild,
            title=str(self.event_title),
            description=str(self.description),
            member=self.target,
            actor=actor,
        )
        await send_private(interaction, "Запись добавлена в личное дело.")


class LeaveModal(discord.ui.Modal):
    def __init__(self, *, target: discord.Member) -> None:
        super().__init__(title="Оформление отпуска")
        self.target = target
        self.end_date = discord.ui.TextInput(
            label="Дата окончания",
            placeholder="ДД.ММ.ГГГГ",
            max_length=10,
        )
        self.reason = discord.ui.TextInput(
            label="Причина",
            placeholder="Кратко укажите причину",
            style=discord.TextStyle.paragraph,
            max_length=500,
        )
        self.add_item(self.end_date)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        actor = await validate_manager(interaction)
        if actor is None:
            return
        try:
            end = parse_date(str(self.end_date))
        except ValueError:
            await send_private(interaction, "Дата должна быть указана в формате ДД.ММ.ГГГГ.")
            return
        if end <= datetime.now(timezone.utc):
            await send_private(interaction, "Дата окончания должна быть позднее текущей даты.")
            return

        role = get_role(self.target.guild, LEAVE_ROLE_NAME)
        if role is None:
            await send_private(interaction, f"Роль «{LEAVE_ROLE_NAME}» не найдена на сервере.")
            return
        try:
            ensure_bot_can_manage(self.target.guild, [role])
            await self.target.add_roles(role, reason=f"Отпуск до {end.date()}")
        except (PermissionError, discord.Forbidden, discord.HTTPException) as error:
            await send_private(interaction, str(error))
            return

        db.connection.execute(
            "UPDATE leaves SET status = 'closed' WHERE guild_id = ? AND member_id = ? AND status = 'active'",
            (self.target.guild.id, self.target.id),
        )
        db.connection.execute(
            """
            INSERT INTO leaves (
                created_at, guild_id, member_id, actor_id,
                starts_at, ends_at, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(), self.target.guild.id, self.target.id, actor.id,
                utc_now_iso(), end.isoformat(), str(self.reason),
            ),
        )
        db.connection.commit()

        add_personnel_event(
            guild_id=self.target.guild.id,
            member_id=self.target.id,
            actor_id=actor.id,
            event_type="leave",
            title="Отпуск",
            description=str(self.reason),
            expires_at=end.isoformat(),
        )
        await send_personnel_log(
            guild=self.target.guild,
            title="ОТПУСК ОФОРМЛЕН",
            description=f"До {end.strftime('%d.%m.%Y')}\n\n{self.reason}",
            member=self.target,
            actor=actor,
        )
        await send_private(interaction, "Отпуск оформлен.")


class ChronicleModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="Новая запись в хронике")
        self.entry_title = discord.ui.TextInput(
            label="Событие",
            placeholder="Название события",
            max_length=120,
        )
        self.description = discord.ui.TextInput(
            label="Описание",
            placeholder="Опишите событие",
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.add_item(self.entry_title)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        actor = await validate_manager(interaction)
        if actor is None or interaction.guild is None:
            return

        db.connection.execute(
            """
            INSERT INTO chronicle (created_at, guild_id, actor_id, title, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (utc_now_iso(), interaction.guild.id, actor.id, str(self.entry_title), str(self.description)),
        )
        db.connection.commit()

        if CHRONICLE_CHANNEL_ID:
            channel = interaction.guild.get_channel(CHRONICLE_CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                embed = discord.Embed(
                    title=str(self.entry_title),
                    description=str(self.description),
                    color=discord.Color.purple(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_footer(text="Хроника The Faceless Ones")
                banner = attach_banner(embed, "chronicle")
                if banner is not None:
                    await channel.send(embed=embed, file=banner)
                else:
                    await channel.send(embed=embed)
        await send_private(interaction, "Запись добавлена в хронику.")


def has_achievement(
    *,
    guild_id: int,
    member_id: int,
    title: str,
) -> bool:
    row = db.connection.execute(
        """
        SELECT 1
        FROM achievements
        WHERE guild_id = ? AND member_id = ? AND title = ?
        LIMIT 1
        """,
        (guild_id, member_id, title),
    ).fetchone()
    return row is not None


async def publish_achievement(
    *,
    member: discord.Member,
    title: str,
    description: str,
) -> bool:
    if HONOR_BOARD_CHANNEL_ID is None:
        logger.warning(
            "HONOR_BOARD_CHANNEL_ID не указан. "
            "Достижение «%s» не опубликовано.",
            title,
        )
        return False

    channel = member.guild.get_channel(HONOR_BOARD_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        logger.warning(
            "Канал доски почёта не найден или не является текстовым."
        )
        return False

    embed = discord.Embed(
        title="ДОСТИЖЕНИЕ ПОЛУЧЕНО",
        description=f"**{title.upper()}**\n\n{description}",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="Получатель",
        value=member.mention,
        inline=False,
    )
    embed.set_footer(
        text="Запись внесена в архив достижений The Faceless Ones."
    )

    try:
        await channel.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        logger.warning(
            "Не удалось опубликовать достижение «%s».",
            title,
        )
        return False


async def grant_achievement(
    *,
    member: discord.Member,
    actor_id: int,
    title: str,
    description: str,
    points: int,
    publish: bool = True,
) -> bool:
    if has_achievement(
        guild_id=member.guild.id,
        member_id=member.id,
        title=title,
    ):
        return False

    db.connection.execute(
        """
        INSERT INTO achievements (
            created_at,
            guild_id,
            member_id,
            actor_id,
            title,
            description,
            points
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            utc_now_iso(),
            member.guild.id,
            member.id,
            actor_id,
            title,
            description,
            points,
        ),
    )
    db.connection.commit()

    if publish:
        await publish_achievement(
            member=member,
            title=title,
            description=description,
        )

    return True


async def grant_first_step(member: discord.Member) -> bool:
    data = AUTOMATIC_ACHIEVEMENTS["Первый шаг"]
    return await grant_achievement(
        member=member,
        actor_id=member.id,
        title="Первый шаг",
        description=str(data["description"]),
        points=int(data["points"]),
        publish=True,
    )


async def grant_veteran_achievement(member: discord.Member) -> bool:
    data = AUTOMATIC_ACHIEVEMENTS["Ветеран семьи"]

    granted = await grant_achievement(
        member=member,
        actor_id=client.user.id if client.user else member.id,
        title="Ветеран семьи",
        description=str(data["description"]),
        points=int(data["points"]),
        publish=True,
    )

    if not granted:
        return False

    role = get_role(member.guild, VETERAN_ROLE_NAME)
    if role is None:
        logger.warning(
            "Роль «%s» не найдена. Достижение выдано без роли.",
            VETERAN_ROLE_NAME,
        )
        return True

    try:
        ensure_bot_can_manage(member.guild, [role])
        if role not in member.roles:
            await member.add_roles(
                role,
                reason=(
                    "Автоматическое присвоение статуса ветерана "
                    "за 180 дней в семье"
                ),
            )
    except (PermissionError, discord.Forbidden, discord.HTTPException):
        logger.exception(
            "Не удалось выдать роль ветерана участнику %s.",
            member.id,
        )

    return True


def attach_banner(
    embed: discord.Embed,
    banner_key: str,
) -> discord.File | None:
    path = BANNER_FILES.get(banner_key)
    if path is None or not path.exists():
        logger.warning("Баннер «%s» не найден: %s", banner_key, path)
        return None

    filename = path.name
    embed.set_image(url=f"attachment://{filename}")
    return discord.File(path, filename=filename)


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

    @discord.ui.button(label="Поощрение", style=discord.ButtonStyle.success, row=2)
    async def reward(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            PersonnelEventModal(target=self.target, event_type="reward", title="Поощрение")
        )

    @discord.ui.button(label="Взыскание", style=discord.ButtonStyle.danger, row=2)
    async def discipline(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            PersonnelEventModal(target=self.target, event_type="discipline", title="Дисциплинарная запись")
        )

    @discord.ui.button(label="Отпуск", style=discord.ButtonStyle.secondary, row=2)
    async def leave(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(LeaveModal(target=self.target))

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

        await grant_first_step(member)

        dm_sent = False

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

        dm_sent = False

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
        if not leave_watcher.is_running():
            leave_watcher.start()
        if not weekly_reporter.is_running():
            weekly_reporter.start()
        if not anniversary_watcher.is_running():
            anniversary_watcher.start()

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


@client.event
async def on_message(message: discord.Message) -> None:
    if isinstance(message.author, discord.Member) and not message.author.bot:
        record_activity(message.author, "message")


@client.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    if not member.bot and before.channel != after.channel:
        record_activity(member, "voice")


@tasks.loop(hours=1)
async def leave_watcher() -> None:
    now = datetime.now(timezone.utc)
    rows = db.connection.execute(
        "SELECT id, guild_id, member_id, ends_at FROM leaves WHERE status = 'active'"
    ).fetchall()

    for row in rows:
        end = datetime.fromisoformat(str(row["ends_at"]))
        if end > now:
            continue
        guild = client.get_guild(int(row["guild_id"]))
        if guild is None:
            continue
        member = guild.get_member(int(row["member_id"]))
        role = get_role(guild, LEAVE_ROLE_NAME)
        if member and role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Окончание отпуска")
            except (discord.Forbidden, discord.HTTPException):
                logger.warning("Не удалось снять роль отпуска.")
        db.connection.execute("UPDATE leaves SET status = 'closed' WHERE id = ?", (int(row["id"]),))
        db.connection.commit()


@leave_watcher.before_loop
async def before_leave_watcher() -> None:
    await client.wait_until_ready()




@tasks.loop(hours=24)
async def anniversary_watcher() -> None:
    if ANNIVERSARY_CHANNEL_ID is None or GUILD_ID is None:
        return

    guild = client.get_guild(GUILD_ID)
    if guild is None:
        return
    channel = guild.get_channel(ANNIVERSARY_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return

    today = datetime.now(timezone.utc).date()
    rows = db.connection.execute(
        """
        SELECT member_id, created_at
        FROM member_profiles
        WHERE guild_id = ?
        """,
        (guild.id,),
    ).fetchall()

    for row in rows:
        joined = datetime.fromisoformat(str(row["created_at"])).date()
        days = (today - joined).days

        milestone = None
        if days in {30, 90, 180, 365}:
            milestone = days
        elif days >= 730 and days % 365 == 0:
            milestone = days

        if milestone is None:
            continue

        already = db.connection.execute(
            """
            SELECT 1
            FROM anniversary_events
            WHERE guild_id = ? AND member_id = ? AND milestone_days = ?
            """,
            (guild.id, int(row["member_id"]), milestone),
        ).fetchone()
        if already:
            continue

        member = guild.get_member(int(row["member_id"]))
        if member is None:
            continue

        if milestone == 180:
            await grant_veteran_achievement(member)

        if milestone == 180:
            period = "полгода"
        elif milestone < 365:
            period = f"{milestone} дней"
        else:
            years = milestone // 365
            period = f"{years} год" if years == 1 else f"{years} года"

        embed = discord.Embed(
            title="ГОДОВЩИНА В СЕМЬЕ",
            description=(
                f"Сегодня исполняется **{period}** с момента, "
                f"когда {member.mention} стал(а) частью The Faceless Ones."
            ),
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Верность времени не подвластна.")

        banner = attach_banner(embed, "anniversary")
        try:
            if banner is not None:
                await channel.send(embed=embed, file=banner)
            else:
                await channel.send(embed=embed)
            db.connection.execute(
                """
                INSERT INTO anniversary_events (
                    guild_id, member_id, milestone_days, announced_at
                ) VALUES (?, ?, ?, ?)
                """,
                (guild.id, member.id, milestone, utc_now_iso()),
            )
            db.connection.commit()
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Не удалось опубликовать годовщину.")


@anniversary_watcher.before_loop
async def before_anniversary_watcher() -> None:
    await client.wait_until_ready()


@tasks.loop(hours=168)
async def weekly_reporter() -> None:
    if WEEKLY_REPORT_CHANNEL_ID is None or GUILD_ID is None:
        return
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        return
    channel = guild.get_channel(WEEKLY_REPORT_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return

    since_iso = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    access_count = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM access_events WHERE guild_id = ? AND created_at >= ?",
        (guild.id, since_iso),
    ).fetchone()["amount"]
    rank_count = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM rank_history WHERE guild_id = ? AND created_at >= ?",
        (guild.id, since_iso),
    ).fetchone()["amount"]
    rewards = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM personnel_events WHERE guild_id = ? AND event_type = 'reward' AND created_at >= ?",
        (guild.id, since_iso),
    ).fetchone()["amount"]
    disciplines = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM personnel_events WHERE guild_id = ? AND event_type = 'discipline' AND created_at >= ?",
        (guild.id, since_iso),
    ).fetchone()["amount"]

    embed = discord.Embed(
        title="НЕДЕЛЬНЫЙ ОБЗОР",
        description="Сводка изменений внутри The Faceless Ones за последние семь дней.",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Новые допуски", value=str(access_count), inline=True)
    embed.add_field(name="Кадровые изменения", value=str(rank_count), inline=True)
    embed.add_field(name="Поощрения", value=str(rewards), inline=True)
    embed.add_field(name="Взыскания", value=str(disciplines), inline=True)
    embed.set_footer(text="The Faceless Ones • внутренняя статистика")
    banner = attach_banner(embed, "weekly_report")
    if banner is not None:
        await channel.send(embed=embed, file=banner)
    else:
        await channel.send(embed=embed)


@weekly_reporter.before_loop
async def before_weekly_reporter() -> None:
    await client.wait_until_ready()




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


@tree.command(name="мой-профиль", description="Показать ваше личное дело.")
async def my_profile(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await send_private(interaction, "Команда доступна только на сервере.")
        return

    await interaction.response.send_message(
        embed=member_card_embed(interaction.user, interaction.guild),
        ephemeral=True,
    )


@tree.command(name="наставник", description="Назначить наставника участнику.")
@app_commands.describe(участник="Новый участник", наставник="Назначаемый наставник")
async def assign_mentor(
    interaction: discord.Interaction,
    участник: discord.Member,
    наставник: discord.Member,
) -> None:
    actor = await validate_manager(interaction)
    if actor is None or interaction.guild is None:
        return
    db.connection.execute(
        """
        INSERT INTO mentorships (guild_id, mentee_id, mentor_id, created_at, status)
        VALUES (?, ?, ?, ?, 'active')
        ON CONFLICT(guild_id, mentee_id) DO UPDATE SET
            mentor_id = excluded.mentor_id,
            created_at = excluded.created_at,
            status = 'active'
        """,
        (interaction.guild.id, участник.id, наставник.id, utc_now_iso()),
    )
    db.connection.commit()
    await send_private(interaction, f"{наставник.mention} назначен наставником для {участник.mention}.")


@tree.command(
    name="достижение",
    description="Присвоить достижение из утверждённого списка.",
)
@app_commands.describe(
    участник="Участник семьи",
    достижение="Выберите достижение",
)
@app_commands.choices(достижение=ACHIEVEMENT_CHOICES)
async def add_achievement(
    interaction: discord.Interaction,
    участник: discord.Member,
    достижение: app_commands.Choice[str],
) -> None:
    actor = await validate_manager(interaction)
    if actor is None or interaction.guild is None:
        return

    data = MANUAL_ACHIEVEMENTS.get(достижение.value)
    if data is None:
        await send_private(
            interaction,
            "Выбранное достижение не найдено.",
        )
        return

    granted = await grant_achievement(
        member=участник,
        actor_id=actor.id,
        title=достижение.value,
        description=str(data["description"]),
        points=int(data["points"]),
        publish=True,
    )

    if not granted:
        await send_private(
            interaction,
            f"У {участник.mention} уже есть достижение "
            f"**«{достижение.value}»**.",
        )
        return

    await send_private(
        interaction,
        f"Достижение **«{достижение.value}»** "
        f"присвоено {участник.mention}.",
    )


@tree.command(name="хроника", description="Добавить новое событие в хронику семьи.")
async def chronicle_command(interaction: discord.Interaction) -> None:
    if await validate_manager(interaction) is None:
        return
    await interaction.response.send_modal(ChronicleModal())


@tree.command(name="неактив", description="Показать участников с длительным отсутствием активности.")
@app_commands.describe(дней="Количество дней без активности")
async def inactivity_report(
    interaction: discord.Interaction,
    дней: app_commands.Range[int, 1, 365] = 14,
) -> None:
    if await validate_manager(interaction) is None or interaction.guild is None:
        return
    threshold = datetime.now(timezone.utc) - timedelta(days=int(дней))
    rows = db.connection.execute(
        """
        SELECT member_id, last_activity_at
        FROM activity_log
        WHERE guild_id = ? AND last_activity_at < ?
        ORDER BY last_activity_at ASC LIMIT 30
        """,
        (interaction.guild.id, threshold.isoformat()),
    ).fetchall()
    if not rows:
        await send_private(interaction, f"Участников без активности более {дней} дней не найдено.")
        return
    lines = [
        f"<@{row['member_id']}> — {discord.utils.format_dt(datetime.fromisoformat(str(row['last_activity_at'])), style='R')}"
        for row in rows
    ]
    embed = discord.Embed(title="КОНТРОЛЬ АКТИВНОСТИ", description="\n".join(lines), color=discord.Color.purple())
    embed.set_footer(text=f"Без активности более {дней} дней")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(
    name="назначить-посла",
    description="Назначить лидеру союзной семьи роль «Полномочный Посол».",
)
@app_commands.describe(
    участник="Лидер или официальный глава союзной семьи",
)
async def appoint_plenipotentiary(
    interaction: discord.Interaction,
    участник: discord.Member,
) -> None:
    actor = await validate_manager(interaction)
    if actor is None or interaction.guild is None:
        return

    role = get_role(interaction.guild, PLENIPOTENTIARY_ROLE_NAME)
    if role is None:
        await send_private(
            interaction,
            f"Роль «{PLENIPOTENTIARY_ROLE_NAME}» не найдена на сервере.",
        )
        return

    if role in участник.roles:
        await send_private(
            interaction,
            f"{участник.mention} уже обладает ролью "
            f"**«{PLENIPOTENTIARY_ROLE_NAME}»**.",
        )
        return

    try:
        ensure_bot_can_manage(interaction.guild, [role])
        await участник.add_roles(
            role,
            reason=(
                f"Назначение полномочным послом. "
                f"Оформил(а): {actor}"
            ),
        )
    except PermissionError as error:
        await send_private(interaction, str(error))
        return
    except discord.Forbidden:
        await send_private(
            interaction,
            "Бот не может выдать роль. Проверьте право «Управлять ролями» "
            "и положение роли бота.",
        )
        return
    except discord.HTTPException:
        logger.exception(
            "Не удалось выдать роль полномочного посла участнику %s.",
            участник.id,
        )
        await send_private(
            interaction,
            "Не удалось назначить полномочного посла.",
        )
        return

    if DIPLOMACY_LOG_CHANNEL_ID is not None:
        channel = interaction.guild.get_channel(DIPLOMACY_LOG_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="НАЗНАЧЕН ПОЛНОМОЧНЫЙ ПОСОЛ",
                description=(
                    f"{участник.mention} официально назначен представителем "
                    "союзной семьи в Посольстве The Faceless Ones."
                ),
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(
                name="Роль",
                value=PLENIPOTENTIARY_ROLE_NAME,
                inline=True,
            )
            embed.add_field(
                name="Назначил(а)",
                value=actor.mention,
                inline=True,
            )
            embed.set_footer(
                text="The Faceless Ones • журнал дипломатии"
            )
            banner = attach_banner(embed, "plenipotentiary")
            try:
                if banner is not None:
                    await channel.send(embed=embed, file=banner)
                else:
                    await channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Не удалось опубликовать назначение полномочного посла."
                )

    await send_private(
        interaction,
        f"{участник.mention} назначен полномочным послом.",
    )


@tree.command(
    name="союз",
    description="Создать или обновить дипломатический паспорт союзной семьи.",
)
@app_commands.describe(
    название="Название союзной семьи",
    статус="Текущий статус союза",
    представитель="Основной представитель союзной семьи",
    описание="Краткое описание союза",
)
@app_commands.choices(
    статус=[
        app_commands.Choice(name="Действующий", value="active"),
        app_commands.Choice(name="Приостановлен", value="paused"),
        app_commands.Choice(name="Завершён", value="closed"),
    ]
)
async def alliance_passport(
    interaction: discord.Interaction,
    название: str,
    статус: app_commands.Choice[str],
    представитель: discord.Member,
    описание: str,
) -> None:
    actor = await validate_manager(interaction)
    if actor is None or interaction.guild is None:
        return

    status_labels = {
        "active": "Действующий",
        "paused": "Приостановлен",
        "closed": "Завершён",
    }
    status_label = status_labels[статус.value]

    db.connection.execute(
        """
        INSERT INTO alliances (
            guild_id,
            name,
            started_at,
            status,
            representative,
            description
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(guild_id, name) DO UPDATE SET
            status = excluded.status,
            representative = excluded.representative,
            description = excluded.description
        """,
        (
            interaction.guild.id,
            название,
            utc_now_iso(),
            статус.value,
            str(представитель.id),
            описание,
        ),
    )
    db.connection.commit()

    embed = discord.Embed(
        title=f"СОЮЗ • {название}",
        description=описание,
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="Статус",
        value=status_label,
        inline=True,
    )
    embed.add_field(
        name="Основной представитель",
        value=представитель.mention,
        inline=True,
    )
    embed.set_footer(
        text="The Faceless Ones • дипломатический паспорт"
    )

    banner = attach_banner(embed, "alliance")
    if banner is not None:
        await interaction.response.send_message(embed=embed, file=banner)
    else:
        await interaction.response.send_message(embed=embed)


@tree.command(name="доска-почета", description="Показать участников с наибольшим числом заслуг.")
async def honor_board(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    rows = db.connection.execute(
        """
        SELECT member_id, SUM(points) AS total_points
        FROM (
            SELECT member_id, COUNT(*) AS points
            FROM personnel_events
            WHERE guild_id = ? AND event_type = 'reward'
            GROUP BY member_id
            UNION ALL
            SELECT member_id, COALESCE(SUM(points), 0) AS points
            FROM achievements
            WHERE guild_id = ?
            GROUP BY member_id
        )
        GROUP BY member_id
        ORDER BY total_points DESC LIMIT 10
        """,
        (interaction.guild.id, interaction.guild.id),
    ).fetchall()
    if not rows:
        await send_private(interaction, "Доска почёта пока пуста.")
        return
    lines = [f"**{i}.** <@{row['member_id']}> — {row['total_points']} балл(ов)" for i, row in enumerate(rows, 1)]
    embed = discord.Embed(title="ДОСКА ПОЧЁТА", description="\n".join(lines), color=discord.Color.purple())
    embed.set_footer(text="The Faceless Ones • признание заслуг")

    if HONOR_BOARD_CHANNEL_ID:
        channel = interaction.guild.get_channel(HONOR_BOARD_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            banner = attach_banner(embed, "honor_board")
            if banner is not None:
                await channel.send(embed=embed, file=banner)
            else:
                await channel.send(embed=embed)
            await send_private(interaction, "Доска почёта опубликована.")
            return

    await interaction.response.send_message(embed=embed)


@tree.command(name="статистика", description="Показать общую статистику семьи.")
async def organization_stats(interaction: discord.Interaction) -> None:
    if await validate_manager(interaction) is None or interaction.guild is None:
        return
    gid = interaction.guild.id
    members = sum(
        len(role.members)
        for role_name in RANK_ROLE_NAMES
        if (role := get_role(interaction.guild, role_name)) is not None
    )
    rewards = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM personnel_events WHERE guild_id = ? AND event_type = 'reward'",
        (gid,),
    ).fetchone()["amount"]
    disciplines = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM personnel_events WHERE guild_id = ? AND event_type = 'discipline'",
        (gid,),
    ).fetchone()["amount"]
    achievements_count = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM achievements WHERE guild_id = ?",
        (gid,),
    ).fetchone()["amount"]
    alliances_count = db.connection.execute(
        "SELECT COUNT(*) AS amount FROM alliances WHERE guild_id = ? AND status = 'active'",
        (gid,),
    ).fetchone()["amount"]

    embed = discord.Embed(title="THE FACELESS ONES • СТАТИСТИКА", color=discord.Color.purple())
    embed.add_field(name="Ранговых назначений", value=str(members), inline=True)
    embed.add_field(name="Поощрений", value=str(rewards), inline=True)
    embed.add_field(name="Взысканий", value=str(disciplines), inline=True)
    embed.add_field(name="Достижений", value=str(achievements_count), inline=True)
    embed.add_field(name="Действующих союзов", value=str(alliances_count), inline=True)
    embed.set_footer(text="FCL Management")
    await interaction.response.send_message(embed=embed, ephemeral=True)


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
