import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import re
import urllib.parse
import logging
import json

# Настройка логирования
logging.basicConfig(filename='scan_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Максимальное количество страниц для сканирования
MAX_PAGES = 15000

# Функция для получения всех URL на странице
def get_links_from_page(url, domain):
    links = []
    try:
        logging.info(f"Запрос страницы: {url}")
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urllib.parse.urljoin(url, href)
            if domain in full_url and full_url not in visited_urls and full_url.startswith('http'):
                links.append(full_url)
    except requests.RequestException as e:
        logging.error(f"Ошибка при запросе страницы {url}: {e}")
    return links

# Функция для рекурсивного сканирования сайта с ограничением глубины
def crawl(url, domain, max_depth=3, current_depth=0):
    global all_urls
    if current_depth > max_depth or len(all_urls) >= MAX_PAGES:
        logging.info(f"Достигнут лимит глубины или количества страниц для {url}")
        return
    
    if url not in visited_urls:
        visited_urls.add(url)
        logging.info(f"Сканирование страницы: {url} на глубине {current_depth}")
        
        try:
            new_links = get_links_from_page(url, domain)
            logging.info(f"Найдено {len(new_links)} новых ссылок на странице {url}")
            
            for link in new_links:
                if link not in all_urls and len(all_urls) < MAX_PAGES:
                    all_urls.append(link)
                    crawl(link, domain, max_depth, current_depth + 1)
                if len(all_urls) >= MAX_PAGES:
                    logging.info("Достигнут максимальный лимит страниц")
                    return
        except Exception as e:
            logging.error(f"Ошибка при сканировании {url}: {e}")

# Настройка Selenium
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.set_capability("goog:loggingPrefs", {'performance': 'ALL', 'browser': 'ALL'})

# Регулярные выражения для поиска метрик, GTM, Яндекс Вебмастера и Google Search Console
yandex_metrika_regex = re.compile(r'(mc\.yandex\.ru/metrika)|(yandex\.ru/metrika)|(ym\((\d+),\s*"init")')
google_analytics_regex = re.compile(r'(google-analytics\.com/analytics.js)|(gtag\("config"|GA_TRACKING_ID)|(ga\("create"|ga\("send")')
gtm_regex = re.compile(r'(googletagmanager\.com/gtm\.js)|(GTM-[A-Z0-9]+)')
yandex_webmaster_regex = re.compile(r'<meta\s+name=["\']yandex-verification["\'][^>]*content=["\']([^"\']+)["\']')
google_search_console_regex = re.compile(r'<meta\s+name=["\']google-site-verification["\'][^>]*content=["\']([^"\']+)["\']')

# Функция для проверки наличия метрик, Яндекс Вебмастера и Google Search Console на странице
def check_metrics(driver, url):
    # Ждем загрузку страницы
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Получаем все выполненные скрипты
    scripts = driver.execute_script("var scripts = document.getElementsByTagName('script'); return Array.from(scripts).map(s => s.innerHTML).join(' ');")
    
    # Получаем полный HTML-контент страницы
    html_content = driver.page_source + scripts

    # Проверка глобальных переменных и функций
    global_checks = driver.execute_script("""
        return {
            'ga': typeof ga !== 'undefined',
            'gtag': typeof gtag !== 'undefined',
            'yaCounter': typeof window['yaCounter' + Object.keys(window).find(key => key.startsWith('yaCounter'))] !== 'undefined',
            'ym': typeof ym !== 'undefined',
            'dataLayer': typeof dataLayer !== 'undefined'
        }
    """)

    # Анализ сетевых запросов
    logs = driver.get_log('performance')
    network_requests = [json.loads(log['message'])['message'] for log in logs if 'Network.requestWillBeSent' in log['message']]
    
    yandex_found = yandex_metrika_regex.search(html_content) or global_checks['yaCounter'] or global_checks['ym']
    google_found = google_analytics_regex.search(html_content) or global_checks['ga'] or global_checks['gtag']
    gtm_found = gtm_regex.search(html_content) or global_checks['dataLayer']
    yandex_webmaster_found = yandex_webmaster_regex.search(html_content)
    google_search_console_found = google_search_console_regex.search(html_content)

    # Дополнительная проверка сетевых запросов
    for request in network_requests:
        request_url = request['params'].get('request', {}).get('url', '')
        if 'mc.yandex.ru' in request_url:
            yandex_found = True
        elif 'google-analytics.com' in request_url:
            google_found = True
        elif 'googletagmanager.com' in request_url:
            gtm_found = True

    # Проверка консольных логов
    console_logs = driver.get_log('browser')
    for log in console_logs:
        if 'Yandex.Metrika counter' in log['message']:
            yandex_found = True
        elif 'Google Analytics' in log['message']:
            google_found = True
        elif 'Google Tag Manager' in log['message']:
            gtm_found = True

    # Дополнительная проверка для GTM и анализа dataLayer
    if gtm_found and not google_found:
        data_layer = driver.execute_script("return window.dataLayer || [];")
        for entry in data_layer:
            if isinstance(entry, dict):
                for key, value in entry.items():
                    if isinstance(value, str) and google_analytics_regex.search(value):
                        google_found = True
                        break

    logging.info(f"Результаты для {url}: Яндекс Метрика: {yandex_found}, Google Analytics: {google_found}, GTM: {gtm_found}")

    return yandex_found, google_found, gtm_found, yandex_webmaster_found, google_search_console_found

# Начальная страница для сканирования
start_url = 'https://eurodez.uz'
domain = urllib.parse.urlparse(start_url).netloc

# Переменные для хранения результатов
all_urls = [start_url]
visited_urls = set()
pages_with_all_metrics = []
pages_without_any_metrics = []
pages_with_partial_metrics = []
pages_with_yandex_webmaster = []
pages_with_google_search_console = []

# Рекурсивное сканирование сайта
print("Начинаем сканирование сайта...")
logging.info("Начинаем сканирование сайта...")
crawl(start_url, domain)
total_pages_to_check = len(all_urls)
print(f"Всего страниц для проверки: {total_pages_to_check}")
logging.info(f"Всего страниц для проверки: {total_pages_to_check}")

# Создание экземпляра веб-драйвера
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Счетчик обработанных страниц
processed_count = 0

for url in all_urls:
    try:
        print(f"Обрабатываем страницу: {url}")
        logging.info(f"Обрабатываем страницу: {url}")
        driver.get(url)

        # Проверка на наличие метрик, GTM, Яндекс Вебмастера и Google Search Console
        yandex_found, google_found, gtm_found, yandex_webmaster_found, google_search_console_found = check_metrics(driver, url)

        if yandex_found and google_found and gtm_found:
            pages_with_all_metrics.append(url)
        elif not yandex_found and not google_found and not gtm_found:
            pages_without_any_metrics.append(url)
        else:
            pages_with_partial_metrics.append((url, yandex_found, google_found, gtm_found))

        if yandex_webmaster_found:
            pages_with_yandex_webmaster.append(url)
        
        if google_search_console_found:
            pages_with_google_search_console.append(url)

        # Обновляем счетчик и выводим статус
        processed_count += 1
        print(f"Обработано {processed_count} из {total_pages_to_check} страниц.")
        logging.info(f"Обработано {processed_count} из {total_pages_to_check} страниц.")

    except Exception as e:
        logging.error(f"Ошибка при обработке страницы {url}: {e}")

# Закрытие браузера
driver.quit()

# Подсчет процентов
total_pages = len(all_urls)
all_metrics_percentage = (len(pages_with_all_metrics) / total_pages) * 100
no_metrics_percentage = (len(pages_without_any_metrics) / total_pages) * 100
partial_metrics_percentage = (len(pages_with_partial_metrics) / total_pages) * 100
yandex_webmaster_percentage = (len(pages_with_yandex_webmaster) / total_pages) * 100
google_search_console_percentage = (len(pages_with_google_search_console) / total_pages) * 100

# Вывод результатов
print(f"Всего страниц: {total_pages}")
print(f"Страниц со всеми метриками: {len(pages_with_all_metrics)} ({all_metrics_percentage:.2f}%)")
print(f"Страниц без метрик: {len(pages_without_any_metrics)} ({no_metrics_percentage:.2f}%)")
print(f"Страниц с частичными метриками: {len(pages_with_partial_metrics)} ({partial_metrics_percentage:.2f}%)")
print(f"Страниц с Яндекс Вебмастером: {len(pages_with_yandex_webmaster)} ({yandex_webmaster_percentage:.2f}%)")
print(f"Страниц с Google Search Console: {len(pages_with_google_search_console)} ({google_search_console_percentage:.2f}%)")

# Запись результатов в файл
with open('metrics_report.txt', 'w', encoding='utf-8') as f:
    f.write(f"Всего страниц: {total_pages}\n")
    f.write(f"Страниц со всеми метриками: {len(pages_with_all_metrics)} ({all_metrics_percentage:.2f}%)\n")
    f.write(f"Страниц без метрик: {len(pages_without_any_metrics)} ({no_metrics_percentage:.2f}%)\n")
    f.write(f"Страниц с частичными метриками: {len(pages_with_partial_metrics)} ({partial_metrics_percentage:.2f}%)\n")
    f.write(f"Страниц с Яндекс Вебмастером: {len(pages_with_yandex_webmaster)} ({yandex_webmaster_percentage:.2f}%)\n")
    f.write(f"Страниц с Google Search Console: {len(pages_with_google_search_console)} ({google_search_console_percentage:.2f}%)\n\n")
    
    f.write("Страницы со всеми метриками:\n")
    for page in pages_with_all_metrics:
        f.write(f"{page}\n")
    
    f.write("\nСтраницы без метрик:\n")
    for page in pages_without_any_metrics:
        f.write(f"{page}\n")
    
    f.write("\nСтраницы с частичными метриками:\n")
    for page, yandex, google, gtm in pages_with_partial_metrics:
        f.write(f"{page} - Яндекс: {'Да' if yandex else 'Нет'}, Google: {'Да' if google else 'Нет'}, GTM: {'Да' if gtm else 'Нет'}\n")
    
    f.write("\nСтраницы с Яндекс Вебмастером:\n")
    for page in pages_with_yandex_webmaster:
        f.write(f"{page}\n")
    
    f.write("\nСтраницы с Google Search Console:\n")
    for page in pages_with_google_search_console:
        f.write(f"{page}\n")

print("Процесс завершен. Проверьте файлы scan_log.txt и metrics_report.txt для получения подробных результатов.")