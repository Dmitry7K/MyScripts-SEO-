import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from datetime import datetime, timedelta
import csv

# Функция для обработки команды /start
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я бот для мониторинга доменов.")

# Функция для отправки информации о доменах
def send_domain_info(update, context):
    # Открываем файл CSV и считываем данные о доменах
    with open('domain_expiration_dates.csv', 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            domain_name = row['domain']
            uptime = row['uptime']
            creation_date = row['creation_date']
            expiration_date = row['expiration_date']

            # Проверяем, если дата окончания домена меньше 30 дней, то отправляем уведомление
            expiration_date_obj = datetime.strptime(expiration_date, "%Y-%m-%d")
            days_until_expiration = (expiration_date_obj - datetime.now()).days

            if days_until_expiration < 30:
                domain_info = f"⚠️ Внимание! Домен {domain_name} истекает через {days_until_expiration} дней. ⚠️\n\nАптайм: {uptime}\nДата создания: {creation_date}\nДата окончания: {expiration_date}"
                context.bot.send_message(chat_id=update.effective_chat.id, text=domain_info)
            else:
                domain_info = f"Информация о домене {domain_name}:\n\nАптайм: {uptime}\nДата создания: {creation_date}\nДата окончания: {expiration_date}"
                context.bot.send_message(chat_id=update.effective_chat.id, text=domain_info)

# Функция для запуска бота
def main():
    # Укажите здесь токен доступа вашего бота
    BOT_TOKEN = '6940147989:AAES-jHuqQgPBviDSQJb64ZzwkSNx7qf6js'

    # Создаем объект Updater и регистрируем обработчики команд и сообщений
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    message_handler = MessageHandler(Filters.text & ~Filters.command, send_domain_info)
    dispatcher.add_handler(message_handler)

    # Запускаем бота
    updater.start_polling()

if __name__ == '__main__':
    main()
