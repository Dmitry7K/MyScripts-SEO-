import os
import sys

print("Current working directory:", os.getcwd())
print("Contents of the directory:", os.listdir())

import whois
import pandas as pd
from datetime import datetime
from telegram import Bot

# Вставьте ваши токен и chat_id прямо в код
TELEGRAM_TOKEN = 'your_telegram_bot_token'
CHAT_ID = 'your_chat_id'

def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=message)

def check_domain_expiration(domain):
    try:
        domain_info = whois.whois(domain)
        expiration_date = domain_info.expiration_date
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]
        return expiration_date
    except Exception as e:
        return None

def main():
    # Загрузка доменов из Excel файла
    df = pd.read_excel('domains.xlsx')

    # Проверка каждого домена
    for index, row in df.iterrows():
        domain = row['domain']
        expiration_date = check_domain_expiration(domain)
        if expiration_date:
            days_left = (expiration_date - datetime.now()).days
            if days_left < 30:
                message = f'Domain {domain} expires on {expiration_date}. Only {days_left} days left!'
                send_telegram_message(message)
                print(message)
            else:
                print(f'Domain {domain} is valid until {expiration_date}.')
        else:
            print(f'Could not fetch expiration date for domain {domain}.')

if __name__ == '__main__':
    main()