# check_sitemaps.py
# Скрипт для проверки доступности robots.txt и всех sitemap-файлов сайта.
# Проверяет:
#   - Доступность файлов (HTTP 200)
#   - Наличие и актуальность даты <lastmod> (не старше 14 дней)
# Весь вывод сохраняется в файл sitemap_check_report.txt

import urllib.request
from xml.etree import ElementTree as ET
from datetime import datetime, timezone, timedelta
import sys

# Настройка логирования в файл
# Открываем файл для записи отчёта
log_file = open("sitemap_check_report.txt", "w", encoding="utf-8")

def log_print(*args, **kwargs):
    """
    Выводит сообщение одновременно в консоль и в файл.
    """
    print(*args, **kwargs, file=log_file, flush=True)  
    print(*args, **kwargs)  
  

#Константы 
BASE_URL = "https://parts.gt-shop.ru"
SITEMAP_INDEX_URL = f"{BASE_URL}/sitemap.xml"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
MAX_DAYS_OLD = 14  # Максимально допустимый возраст данных в днях


def fetch_xml(url):
    """
    Загружает XML-файл по URL и возвращает корневой элемент дерева.
    Возвращает None в случае ошибки.
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.getcode() != 200:
                log_print(f"Ошибка: {url} вернул статус {response.getcode()}")
                return None
            return ET.fromstring(response.read())
    except Exception as e:
        log_print(f"Не удалось загрузить {url}: {e}")
        return None


def check_robots_txt():
    """
    Проверяет доступность файла robots.txt.
    """
    log_print("Проверка robots.txt...")
    try:
        with urllib.request.urlopen(ROBOTS_URL, timeout=10) as resp:
            if resp.getcode() == 200:
                log_print("robots.txt доступен")
            else:
                log_print(f"robots.txt недоступен (статус {resp.getcode()})")
    except Exception as e:
        log_print(f"Ошибка при проверке robots.txt: {e}")


def parse_sitemap_index(root):
    """
    Извлекает список URL дочерних sitemap-файлов из основного индекса.
    """
    urls = []
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for sitemap in root.findall(f".//{namespace}sitemap"):
        loc_elem = sitemap.find(f"{namespace}loc")
        if loc_elem is not None and loc_elem.text:
            urls.append(loc_elem.text.strip())
    return urls


def get_lastmod_from_sitemap(root):
    """
    Находит самую свежую дату <lastmod> в sitemap-файле.
    Возвращает объект datetime или None, если даты не найдены.
    """
    lastmods = []
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for url_entry in root.findall(f".//{namespace}url"):
        lastmod_elem = url_entry.find(f"{namespace}lastmod")
        if lastmod_elem is not None and lastmod_elem.text:
            try:
                dt_str = lastmod_elem.text.strip()
                if dt_str.endswith('Z'):
                    dt = datetime.fromisoformat(dt_str[:-1] + '+00:00')
                else:
                    dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                lastmods.append(dt)
            except ValueError:
                continue
    return max(lastmods) if lastmods else None


def check_sitemap_freshness(sitemap_url):
    """
    Проверяет один sitemap-файл:
    - Доступен ли (HTTP 200)
    - Есть ли в нём дата <lastmod>
    - Не старше ли дата MAX_DAYS_OLD дней
    Возвращает True, если файл считается валидным.
    """
    # Проверка доступности
    try:
        with urllib.request.urlopen(sitemap_url, timeout=10) as resp:
            if resp.getcode() != 200:
                log_print(f"[FAIL] {sitemap_url} -> статус {resp.getcode()}")
                return False
    except Exception as e:
        log_print(f"[FAIL] {sitemap_url} -> ошибка доступа: {e}")
        return False

    # Загрузка XML
    root = fetch_xml(sitemap_url)
    if root is None:
        return False

    # Поиск последней даты обновления
    lastmod = get_lastmod_from_sitemap(root)
    if lastmod is None:
        log_print(f"[INFO] {sitemap_url} -> нет данных lastmod (файл считается допустимым)")
        return True

    # Проверка актуальности
    now = datetime.now(timezone.utc)
    days_old = (now - lastmod).days
    if days_old <= MAX_DAYS_OLD:
        log_print(f"[OK] {sitemap_url} -> обновлено {days_old} дней назад")
        return True
    else:
        log_print(f"[WARN] {sitemap_url} -> устарело ({days_old} дней, лимит: {MAX_DAYS_OLD})")
        return False


def main():
    """
    Основная логика скрипта:
    1. Проверяет robots.txt
    2. Загружает основной sitemap.xml
    3. Проверяет все дочерние sitemap-файлы
    """
    log_print("Запуск проверки robots.txt и sitemap...")

    check_robots_txt()
    log_print()

    log_print("Загрузка sitemap.xml...")
    root = fetch_xml(SITEMAP_INDEX_URL)
    if root is None:
        log_print("Критическая ошибка: не удалось загрузить основной sitemap.xml")
        log_file.close()
        sys.exit(1)

    sitemap_urls = parse_sitemap_index(root)
    log_print(f"Найдено {len(sitemap_urls)} sitemap-файлов\n")

    if not sitemap_urls:
        log_print("Нет вложенных sitemap-файлов для проверки")
        log_file.close()
        return

    failed = 0
    for i, url in enumerate(sitemap_urls, 1):
        log_print(f"[{i}/{len(sitemap_urls)}]", end=" ")
        if not check_sitemap_freshness(url):
            failed += 1

    log_print("\n" + "="*50)
    if failed == 0:
        log_print("Все sitemap-файлы доступны и актуальны.")
    else:
        log_print(f"{failed} из {len(sitemap_urls)} файлов имеют проблемы.")

    log_file.close()


if __name__ == "__main__":
    main()