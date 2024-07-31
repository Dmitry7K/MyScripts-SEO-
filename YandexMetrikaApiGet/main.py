import requests
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Ваш API токен и ID счетчика
TOKEN = 'y0_AgAAAAAzKum6AAwd1AAAAAEKvFrWAADL2yQdMvpFR7fmu-YRkqSol6J4FQ'
COUNTER_ID = '93294966'  # Удалил 'id='

# Функция для получения данных из Яндекс Метрики
def get_yandex_metrika_data(token, counter_id):
    headers = {
        'Authorization': f'OAuth {token}',
    }

    params = {
        'ids': counter_id,  # Заменил 'id' на 'ids'
        'metrics': 'ym:s:visits,ym:s:pageviews,ym:s:users',
        'date1': '30daysAgo',
        'date2': 'yesterday',
        'dimensions': 'ym:s:date',
        'accuracy': 'full',
        'limit': 100000
    }

    print("Отправка запроса к API Яндекс Метрики...")
    response = requests.get('https://api-metrika.yandex.net/stat/v1/data', headers=headers, params=params)
    print(f"URL запроса: {response.url}")
    if response.status_code == 200:
        print("Данные успешно получены.")
        return response.json()
    else:
        print(f"Ошибка при получении данных: {response.status_code}")
        print(f"Тело ответа: {response.text}")
        return None

# Функция для обработки данных
def process_data(data):
    if data is None or 'data' not in data:
        print("Данные отсутствуют или формат ответа некорректен.")
        return None

    data_list = data['data']
    formatted_data = [{'date': item['dimensions'][0]['name'], 
                       'visits': item['metrics'][0], 
                       'pageviews': item['metrics'][1], 
                       'users': item['metrics'][2]} for item in data_list]

    df = pd.DataFrame(formatted_data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

# Функция для прогнозирования
def forecast_data(df):
    model = ExponentialSmoothing(df['visits'], seasonal='add', seasonal_periods=7)
    fit = model.fit()
    forecast = fit.forecast(30)
    forecast_df = pd.DataFrame(forecast, columns=['forecast_visits'])
    return forecast_df

# Функция для визуализации
def visualize_data(df, forecast_df):
    plt.figure(figsize=(14, 7))
    plt.plot(df['visits'], label='Actual Visits')
    plt.plot(forecast_df, label='Forecast Visits', linestyle='--')
    plt.title('Visits Forecast')
    plt.xlabel('Date')
    plt.ylabel('Number of Visits')
    plt.legend()
    plt.savefig('forecast.png')
    plt.show()

# Основная функция для выполнения всех шагов
def main():
    print("Запуск основной функции...")
    data = get_yandex_metrika_data(TOKEN, COUNTER_ID)
    if data:
        df = process_data(data)
        if df is not None:
            print("Данные обработаны:")
            print(df.head())
            forecast_df = forecast_data(df)
            print("Прогнозирование выполнено.")
            visualize_data(df, forecast_df)
            print("Визуализация завершена.")

# Выполнение основной функции непосредственно для отладки
main()