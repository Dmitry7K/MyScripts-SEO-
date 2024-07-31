import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import tkinter as tk
from tkinter import messagebox

def check_noindex_nofollow(url, use_selenium=False):
    try:
        if use_selenium:
            options = Options()
            options.headless = True
            service = Service('/opt/homebrew/bin/chromedriver')  # Замените на путь к вашему chromedriver
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            time.sleep(5)  # Дождаться загрузки страницы
            html = driver.page_source
            driver.quit()
        else:
            response = requests.get(url)
            html = response.text

        soup = BeautifulSoup(html, 'html.parser')

        noindex_tag = soup.find('meta', attrs={'name': 'robots', 'content': 'noindex'})
        nofollow_tag = soup.find('meta', attrs={'name': 'robots', 'content': 'nofollow'})

        if noindex_tag or nofollow_tag:
            return True
        return False
    except Exception as e:
        messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
        return False

def notify_if_noindex_nofollow():
    url = url_entry.get()
    use_selenium = selenium_var.get()
    result = check_noindex_nofollow(url, use_selenium)
    if result:
        result_label.config(text=f"Внимание! Сайт {url} содержит теги noindex или nofollow.")
    else:
        result_label.config(text=f"Сайт {url} открыт для индексации.")

# Создание GUI
root = tk.Tk()
root.title("Проверка тегов noindex и nofollow")

tk.Label(root, text="Введите URL сайта:").pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

selenium_var = tk.BooleanVar()
tk.Checkbutton(root, text="Использовать Selenium", variable=selenium_var).pack(pady=5)

check_button = tk.Button(root, text="Проверить", command=notify_if_noindex_nofollow)
check_button.pack(pady=20)

result_label = tk.Label(root, text="", wraplength=400)
result_label.pack(pady=10)

root.mainloop()