## Установка

1. Создай venv / conda env
2. `pip install -r requirements.txt`
3. `cp .env.example .env`
4. Заполни переменные в `.env`:
   - `BOT_TOKEN` - токен бота от @BotFather
   - `ADMIN_ID` - твой Telegram user ID
   - `XUI_URL`, `XUI_USER`, `XUI_PASS` - данные панели 3x-ui
   - `XUI_INBOUND_ID` - ID инбаунда в панели
   - `SERVER_IP`, `SERVER_PORT`, `PUBLIC_KEY`, `SNI`, `SHORT_ID` - настройки VPN сервера
5. `python -m app.main`

## Функции

- ✅ Автоматическая активация подписок через XUI панель
- ✅ Проверка баланса перед активацией
- ✅ Автоматическое отключение истекших подписок (expire_worker)
- ✅ Генерация VLESS ключей
- ✅ Управление депозитами (для админа)
- ✅ Логирование всех операций

## Переменные окружения

См. `.env.example` для полного списка переменных.
