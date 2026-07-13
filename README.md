# FCL Management v5

Обновлённая версия внутреннего бота The Faceless Ones.

## Изменено

- бот переведён на `discord.Client` без префиксных команд;
- предупреждение о Message Content Intent устранено;
- необязательные предупреждения голосовых библиотек скрыты;
- добавлен минималистичный статус;
- улучшено логирование подключения и переподключения;
- добавлена проверка переменных Render;
- сохранён веб-порт для Render и UptimeRobot;
- сохранены команды, панель управления и SQLite-история.

## Команды

- `/управление`
- `/карточка`
- `/история`
- `/состав`
- `/исключить`

## Render

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
python bot.py
```

UptimeRobot:

```text
https://fcl-rank-bot.onrender.com/health
```
