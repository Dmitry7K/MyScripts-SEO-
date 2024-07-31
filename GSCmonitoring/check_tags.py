import requests
from bs4 import BeautifulSoup

def check_nofollow_noindex(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    nofollow = any(tag.has_attr('rel') and 'nofollow' in tag['rel'] for tag in soup.find_all('a'))
    noindex = soup.find('meta', {'name': 'robots', 'content': 'noindex'}) is not None

    return nofollow, noindex