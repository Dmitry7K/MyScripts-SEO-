from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import pandas as pd
import matplotlib.pyplot as plt

# Определение области доступа
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Функция для авторизации
def authenticate():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('/Users/dmitrijkovalev/SegmantAnalysisApiGoo/credentials/gsc-data-427612-cd5d146298e8.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

# Авторизация и создание клиента для API
credentials = authenticate()
service = build('searchconsole', 'v1', credentials=credentials)

# Функция для получения данных
def get_gsc_data(site_url, start_date, end_date):
    request = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': ['date', 'query', 'page'],
        'rowLimit': 10000
    }
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    return response

# Пример использования
site_url = 'https://www.brostore.uz/'
data = []
for month in range(1, 7):  # Январь по Июнь
    start_date = f'2024-{month:02d}-01'
    end_date = f'2024-{month:02d}-28' if month != 2 else '2024-02-29'
    response = get_gsc_data(site_url, start_date, end_date)
    data.extend(response['rows'])

# Преобразование данных в DataFrame
df = pd.DataFrame(data)
df['clicks'] = df['clicks'].astype(float)
df['impressions'] = df['impressions'].astype(float)
df['ctr'] = df['ctr'].astype(float)
df['position'] = df['position'].astype(float)

# Группировка данных по месяцам и расчет изменений
df['date'] = pd.to_datetime(df['keys'].apply(lambda x: x[0]))
df['query'] = df['keys'].apply(lambda x: x[1])
df['page'] = df['keys'].apply(lambda x: x[2])
df['month'] = df['date'].dt.to_period('M')

# Агрегация данных
monthly_data = df.groupby('month').agg({
    'clicks': 'sum',
    'impressions': 'sum',
    'ctr': 'mean',
    'position': 'mean'
}).reset_index()

# Визуализация
fig, ax1 = plt.subplots()

ax2 = ax1.twinx()
ax1.plot(monthly_data['month'].astype(str), monthly_data['clicks'], 'g-')
ax2.plot(monthly_data['month'].astype(str), monthly_data['position'], 'b-')

ax1.set_xlabel('Месяц')
ax1.set_ylabel('Клики', color='g')
ax2.set_ylabel('Средняя позиция', color='b')

plt.title('Изменения трафика и позиций')
plt.show()