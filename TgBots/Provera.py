import requests

# Настройки для Telegram
TELEGRAM_TOKEN = '6940147989:AAES-jHuqQgPBviDSQJb64ZzwkSNx7qf6js'
CHAT_ID = '169716572'
message = 'Тестовое сообщение'

url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
payload = {
    'chat_id': CHAT_ID,
    'text': message
}
headers = {
    'Content-Type': 'application/json'
}

response = requests.post(url, json=payload, headers=headers)
print(f"URL: {url}")
print(f"Payload: {payload}")
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code != 200:
    print(f"Ошибка при отправке сообщения: {response.status_code}, {response.text}")
else:
    print("Сообщение успешно отправлено в Telegram")