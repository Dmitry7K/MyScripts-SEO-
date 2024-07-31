from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def fetch_words_from_url(driver, url, retries=3):
    for attempt in range(retries):
        try:
            print(f"Открытие страницы... (Попытка {attempt + 1})")
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'article-link')))
            print("Страница успешно загружена.")
            return driver.find_elements(By.CLASS_NAME, 'article-link')
        except Exception as e:
            print(f"Ошибка при загрузке страницы: {e}")
            print("Повторная попытка...")
            time.sleep(5)
    print("Не удалось загрузить страницу после нескольких попыток.")
    return []

# Укажите путь к вашему chromedriver
service = Service('/opt/homebrew/bin/chromedriver')  # Убедитесь, что путь правильный

# Настройте ChromeDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Опционально, если не хотите, чтобы открывалось окно браузера
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-extensions")

try:
    print("Запуск ChromeDriver...")
    driver = webdriver.Chrome(service=service, options=options)
    
    url = 'https://ozhegov.slovaronline.com/articles/%D0%92/page-1'  # Замените на нужный URL
    words = fetch_words_from_url(driver, url)

    if words:
        print(f"Найдено {len(words)} элементов.")
        # Извлеките текст из каждого элемента и сохраните в список
        word_list = [word.text for word in words]

        # Сохраните слова в файл
        print("Сохранение слов в файл...")
        with open('words_list.txt', 'w') as file:
            for word in word_list:
                file.write(f"{word}\n")

        print("Слова успешно сохранены в words_list.txt")
    else:
        print("Элементы не найдены. Проверьте правильность CSS селектора и убедитесь, что страница полностью загружена.")

    # Закройте драйвер
    driver.quit()
except Exception as e:
    print(f"Произошла ошибка: {e}")