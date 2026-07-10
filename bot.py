import logging
import os
from typing import Final

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")
GUILD_ID_RAW: Final[str | None] = os.getenv("GUILD_ID")
ROLE_CHANNEL_ID_RAW: Final[str | None] = os.getenv("ROLE_CHANNEL_ID")
LOG_CHANNEL_ID_RAW: Final[str | None] = os.getenv("LOG_CHANNEL_ID")

GUILD_ID = int(GUILD_ID_RAW) if GUILD_ID_RAW else None
ROLE_CHANNEL_ID = int(ROLE_CHANNEL_ID_RAW) if ROLE_CHANNEL_ID_RAW else None
LOG_CHANNEL_ID = int(LOG_CHANNEL_ID_RAW) if LOG_CHANNEL_ID_RAW else None

# Роли, которым разрешено использовать /ранг.
MANAGER_ROLE_NAMES: Final[set[str]] = {
    "Владелец",
    "Администратор",
    "Первая Без Лица",
    "Голос Без Лица",
}

# ВАЖНО: названия должны полностью совпадать с ролями на сервере Discord.
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

RANK_CHOICES: Final[list[app_commands.Choice[str]]] = [
    app_commands.Choice(name=name, value=name) for name in RANK_ROLE_NAMES
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("fcl-rank-bot")


def has_manager_access(member: discord.Member) -> bool:
    """Проверяет, имеет ли пользователь право менять ранги."""
    if member.guild.owner_id == member.id:
        return True

    if member.guild_permissions.administrator:
        return True

    return any(role.name in MANAGER_ROLE_NAMES for role in member.roles)


class FCLBot(commands.Bot):
    async def setup_hook(self) -> None:
        # Для одного сервера команды появятся почти сразу.
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Синхронизировано команд на сервере: %s", len(synced))
        else:
            synced = await self.tree.sync()
            logger.info("Глобально синхронизировано команд: %s", len(synced))


intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = FCLBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    if bot.user:
        logger.info("Бот запущен: %s (%s)", bot.user, bot.user.id)


@bot.tree.command(
    name="ранг",
    description="Заменить текущий ранг участника на выбранный.",
)
@app_commands.describe(
    участник="Участник семьи, которому нужно изменить ранг",
    новый_ранг="Новый ранг участника",
)
@app_commands.choices(новый_ранг=RANK_CHOICES)
async def change_rank(
    interaction: discord.Interaction,
    участник: discord.Member,
    новый_ранг: app_commands.Choice[str],
) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "Команда доступна только на сервере.",
            ephemeral=True,
        )
        return

    if ROLE_CHANNEL_ID and interaction.channel_id != ROLE_CHANNEL_ID:
        await interaction.response.send_message(
            "Эта команда доступна только в закрытом канале управления ролями.",
            ephemeral=True,
        )
        return

    if not has_manager_access(interaction.user):
        await interaction.response.send_message(
            "У вас нет права изменять ранги участников.",
            ephemeral=True,
        )
        return

    guild = interaction.guild
    bot_member = guild.me

    if bot_member is None:
        await interaction.response.send_message(
            "Не удалось определить роль бота на сервере.",
            ephemeral=True,
        )
        return

    if участник.id == guild.owner_id:
        await interaction.response.send_message(
            "Discord не позволяет изменять роли владельца сервера.",
            ephemeral=True,
        )
        return

    selected_role = discord.utils.get(guild.roles, name=новый_ранг.value)
    if selected_role is None:
        await interaction.response.send_message(
            f"Роль «{новый_ранг.value}» не найдена. Проверьте её название.",
            ephemeral=True,
        )
        return

    if selected_role >= bot_member.top_role:
        await interaction.response.send_message(
            f"Роль бота должна находиться выше роли «{selected_role.name}».",
            ephemeral=True,
        )
        return

    current_rank_roles = [
        role
        for role in участник.roles
        if role.name in RANK_ROLE_NAMES and role != selected_role
    ]

    unmanageable_roles = [
        role for role in current_rank_roles if role >= bot_member.top_role
    ]
    if unmanageable_roles:
        names = ", ".join(f"«{role.name}»" for role in unmanageable_roles)
        await interaction.response.send_message(
            f"Бот не может снять роли {names}: его роль находится ниже них.",
            ephemeral=True,
        )
        return

    old_rank_names = [role.name for role in current_rank_roles]

    try:
        await interaction.response.defer(ephemeral=True)

        if current_rank_roles:
            await участник.remove_roles(
                *current_rank_roles,
                reason=f"Изменение ранга пользователем {interaction.user}",
            )

        if selected_role not in участник.roles:
            await участник.add_roles(
                selected_role,
                reason=f"Изменение ранга пользователем {interaction.user}",
            )

    except discord.Forbidden:
        await interaction.followup.send(
            "Discord запретил изменение ролей. Проверьте право «Управлять ролями» "
            "и положение роли бота.",
            ephemeral=True,
        )
        return
    except discord.HTTPException as error:
        logger.exception("Ошибка Discord API при изменении ранга")
        await interaction.followup.send(
            f"Не удалось изменить ранг из-за ошибки Discord: {error}",
            ephemeral=True,
        )
        return

    old_rank_text = ", ".join(old_rank_names) if old_rank_names else "не назначен"
    confirmation = (
        f"Ранг участника {участник.mention} изменён:\n"
        f"**{old_rank_text} → {selected_role.name}**"
    )
    await interaction.followup.send(confirmation, ephemeral=True)

    if LOG_CHANNEL_ID:
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):
            embed = discord.Embed(
                title="Изменение ранга",
                color=discord.Color.purple(),
            )
            embed.add_field(name="Участник", value=участник.mention, inline=True)
            embed.add_field(
                name="Изменение",
                value=f"{old_rank_text} → **{selected_role.name}**",
                inline=False,
            )
            embed.add_field(
                name="Изменил(а)",
                value=interaction.user.mention,
                inline=True,
            )
            await log_channel.send(embed=embed)


@change_rank.error
async def change_rank_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    logger.exception("Ошибка команды /ранг", exc_info=error)

    message = "При выполнении команды произошла ошибка."
    if isinstance(error, app_commands.CommandInvokeError):
        message = "Не удалось изменить ранг. Проверьте настройки ролей бота."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if not TOKEN:
    raise RuntimeError(
        "Не найден DISCORD_TOKEN. Создайте файл .env и добавьте токен бота."
    )

bot.run(TOKEN)
