import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import csv
from datetime import datetime

def check_robots_txt(url):
    robots_url = f"{url}/robots.txt"
    try:
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            return "Disallow: /" in response.text
    except requests.RequestException as e:
        return f"Ошибка: {str(e)}"
    return False

def check_meta_tags(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            noindex = soup.find('meta', attrs={'name': 'robots', 'content': lambda x: x and 'noindex' in x.lower()})
            nofollow = soup.find('meta', attrs={'name': 'robots', 'content': lambda x: x and 'nofollow' in x.lower()})
            return bool(noindex), bool(nofollow)
    except requests.RequestException as e:
        return f"Ошибка: {str(e)}", f"Ошибка: {str(e)}"
    return False, False

def get_gsc_data(service, site_url):
    try:
        # Получение данных о состоянии индексации
        index_request = service.urlInspection().index().list(
            body={
                "inspectionUrl": site_url,
                "siteUrl": site_url
            }
        )
        index_response = index_request.execute()
        index_status = index_response.get('inspectionResult', {}).get('indexStatusResult', {})

        # Получение данных о мобильной пригодности
        mobile_request = service.urlInspection().index().list(
            body={
                "inspectionUrl": site_url,
                "siteUrl": site_url,
                "languageCode": "ru"  # или другой нужный язык
            }
        )
        mobile_response = mobile_request.execute()
        mobile_usability = mobile_response.get('inspectionResult', {}).get('mobileUsabilityResult', {})

        return {
            'verdict': index_status.get('verdict', 'Unknown'),
            'robotsTxtState': index_status.get('robotsTxtState', 'Unknown'),
            'indexingState': index_status.get('indexingState', 'Unknown'),
            'lastCrawlTime': index_status.get('lastCrawlTime', 'Unknown'),
            'pageFetchState': index_status.get('pageFetchState', 'Unknown'),
            'googleCanonical': index_status.get('googleCanonical', 'Unknown'),
            'userCanonical': index_status.get('userCanonical', 'Unknown'),
            'mobileUsabilityResult': mobile_usability.get('verdict', 'Unknown'),
            'mobileUsabilityIssues': ', '.join([issue.get('issue', '') for issue in mobile_usability.get('issues', [])])
        }
    except HttpError as e:
        return {'error': f"Ошибка API: {str(e)}"}
    except Exception as e:
        return {'error': f"Неизвестная ошибка: {str(e)}"}

def main():
    SERVICE_ACCOUNT_FILE = '/Users/dmitrijkovalev/MonitorGSC(Claude)/credentials/gsc-data-427612-cd5d146298e8.json'
    
    print("Начало выполнения скрипта")

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/webmasters']
        )
        print("Аутентификация успешна")

        service = build('searchconsole', 'v1', credentials=credentials)
        print("Сервис Google Search Console создан")

        sites_request = service.sites().list()
        sites = sites_request.execute()
        
        print(f"Получен список сайтов. Количество сайтов: {len(sites.get('siteEntry', []))}")

        if not sites.get('siteEntry'):
            print("Список сайтов пуст. Проверьте права доступа сервисного аккаунта.")
            return

        # Подготовка CSV файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"website_analysis_{timestamp}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['URL', 'Robots.txt блокирует', 'Noindex', 'Nofollow', 'Verdict', 'RobotsTxtState', 
                          'IndexingState', 'LastCrawlTime', 'PageFetchState', 'GoogleCanonical', 'UserCanonical', 
                          'MobileUsabilityResult', 'MobileUsabilityIssues']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for site in sites.get('siteEntry', []):
                url = site['siteUrl']
                print(f"\nАнализ сайта: {url}")
                
                robots_blocked = check_robots_txt(url)
                noindex, nofollow = check_meta_tags(url)
                
                gsc_data = get_gsc_data(service, url)
                
                writer.writerow({
                    'URL': url,
                    'Robots.txt блокирует': robots_blocked,
                    'Noindex': noindex,
                    'Nofollow': nofollow,
                    'Verdict': gsc_data.get('verdict', ''),
                    'RobotsTxtState': gsc_data.get('robotsTxtState', ''),
                    'IndexingState': gsc_data.get('indexingState', ''),
                    'LastCrawlTime': gsc_data.get('lastCrawlTime', ''),
                    'PageFetchState': gsc_data.get('pageFetchState', ''),
                    'GoogleCanonical': gsc_data.get('googleCanonical', ''),
                    'UserCanonical': gsc_data.get('userCanonical', ''),
                    'MobileUsabilityResult': gsc_data.get('mobileUsabilityResult', ''),
                    'MobileUsabilityIssues': gsc_data.get('mobileUsabilityIssues', '')
                })
                
                print(f"Данные для {url} записаны в CSV")

        print(f"\nАнализ завершен. Результаты сохранены в файл {csv_filename}")

    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

    print("Выполнение скрипта завершено")

if __name__ == "__main__":
    main()
