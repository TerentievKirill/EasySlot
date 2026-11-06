# EasySlot

Простая онлайн-запись для небольших мастеров: один FastAPI, один Docker, отдельный Google Calendar и HTML-шаблон на мастера.

## Логика

- Мастер создаёт в **своём календаре** событие с точным названием **Доступен для записи** (например, 09:00–23:00).
- Сервис предлагает часовые слоты внутри этих событий на ближайшие 30 дней.
- Все посторонние события игнорируются. Только события, созданные EasySlot (отмеченные private extended property), занимают слоты.
- При записи сохраняются имя и телефон, событие создаётся в том же календаре, мастеру отправляется Telegram-уведомление.
- Нет регистрации клиентов, CRM и базы клиентских записей. SQLite хранит только настройки мастеров.

## Подготовка Google API

1. Создать Google Cloud project, включить **Google Calendar API**.
2. Настроить OAuth consent screen и создать OAuth Client ID типа **Desktop app**.
3. Скачать JSON клиента в локальный файл `credentials.json`. В репозиторий не добавлять.
4. Локально выполнить `pip install -r requirements.txt`, затем `python scripts/google_auth.py --client credentials.json --output token.json`. Авторизовать **свой** Google-аккаунт. Если приложение в Testing, refresh token может истекать через 7 дней — для стабильной работы нужно правильно настроить публикацию OAuth-приложения.
5. Создать отдельный календарь на каждого мастера в этом аккаунте и получить его Calendar ID в настройках календаря.
6. Скопировать `token.json` в `secrets/google_token.json` на сервере. Хранить файл приватно, не коммитить.

## Запуск

```bash
cp .env.example .env
mkdir -p data secrets
# Заполнить TELEGRAM_BOT_TOKEN, убедиться что GOOGLE_TOKEN_FILE указывает на secrets/google_token.json
docker compose up -d --build
```

Создать мастера (запускается на сервере из корня проекта):

```bash
DATABASE_PATH=./data/easyslot.db python scripts/add_master.py \
  --hostname 1.heartlab.app --name "Мастер 1" \
  --calendar-id "calendar-id@group.calendar.google.com" \
  --telegram-chat-id "123456789" --template master_1.html
```

Для второго мастера повторить с другим hostname, calendar ID, Telegram ID и `master_2.html`. Бот должен получить `/start` от мастера, иначе отправка сообщения не сработает.

Nginx проксирует оба поддомена на `http://127.0.0.1:8088`, сохраняя `Host`. Нужны DNS и HTTPS. Не публиковать порт FastAPI напрямую в интернет.

## API

- `GET /` — страница мастера по Host
- `GET /api/slots` — свободные интервалы
- `POST /api/book` — запись
- `GET /health` — проверка процесса

## Важно

- Для MVP защита от одновременной записи работает через asyncio.Lock **внутри одного процесса**. Не запускать несколько uvicorn workers или реплик без общей блокировки.
- Telegram-уведомление отправляется после создания записи. Если Telegram недоступен, запись всё равно остаётся в календаре.
- События доступности должны иметь точное название `Доступен для записи` и время начала/конца (не all-day).
- Шаблоны `master_1.html` и `master_2.html` пока наследуют общий `default.html` и готовы к индивидуальной доработке.
- Токены, телефоны клиентов и секреты не коммитить.
