import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
import random
import os
from datetime import datetime

XML_URL = "https://parts.gt-shop.ru/yml/gtun.4.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

def parse_price(html):
    """Парсит цену со страницы сайта"""
    soup = BeautifulSoup(html, 'lxml')
    
    price_selectors = [
        'meta[itemprop="price"]',
        '.price',
        '.current-price',
        '.product-price',
        '[itemprop="price"]',
        '.price-value',
    ]
    
    for selector in price_selectors:
        price_tag = soup.select_one(selector)
        if price_tag:
            price_text = price_tag.get('content', '') if selector.startswith('meta') else price_tag.get_text(strip=True)
            if price_text:
                clean_price = (
                    price_text
                    .replace('₽', '')
                    .replace(' ', '')
                    .replace(',', '.')
                    .replace('\xa0', '')
                    .replace('Руб.', '')
                    .replace('Руб', '')
                    .replace('От', '')
                    .replace('от', '')
                    .strip()
                )
                try:
                    return float(clean_price)
                except (ValueError, TypeError):
                    continue
    
    import re
    price_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:₽|руб|Руб)'
    matches = re.findall(price_pattern, html, re.IGNORECASE)
    if matches:
        try:
            return float(matches[0].replace(',', '.'))
        except:
            pass
    
    return None

def save_report(offers_checked, errors, correct_count, total_time):
    """Сохраняет отчёт в файл с уникальным именем"""
    os.makedirs("reports", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/check_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("="*70 + "\n")
        f.write("ПРОВЕРКА ЦЕН С PID\n")
        f.write("="*70 + "\n")
        f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Источник: {XML_URL}\n")
        f.write(f"Проверено товаров: {len(offers_checked)}\n")
        f.write(f"Время выполнения: {total_time:.1f} сек\n")
        f.write("="*70 + "\n\n")
        
        for i, (price_csv, url, price_site, status) in enumerate(offers_checked, 1):
            f.write(f"[{i}/{len(offers_checked)}] {url}\n")
            f.write(f"   Прайс: {price_csv:.0f} RUB | Сайт: {price_site if price_site is not None else 'N/A'} RUB | {status}\n\n")
        
        f.write("="*70 + "\n")
        f.write("ИТОГИ ПРОВЕРКИ\n")
        f.write("="*70 + "\n")
        f.write(f"Корректных: {correct_count}/{len(offers_checked)} ({correct_count/len(offers_checked)*100:.1f}%)\n")
        f.write(f"Ошибок: {len(errors)}\n")
        f.write("="*70 + "\n")
        
        if errors:
            f.write("\nДЕТАЛИ ОШИБОК:\n")
            f.write("="*70 + "\n")
            for url, price_csv, price_site, error_type in errors:
                f.write(f"\nURL: {url}\n")
                f.write(f"  Прайс: {price_csv:.0f} RUB\n")
                if price_site is not None:
                    f.write(f"  Сайт: {price_site:.0f} RUB\n")
                f.write(f"  Ошибка: {error_type}\n")
    
    print(f"\nОтчёт сохранён: {filename}")
    return filename

def check_prices():
    start_time = time.time()
    
    print("Загрузка XML...")
    
    try:
        response = requests.get(XML_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as e:
        print(f"Ошибка загрузки XML: {e}")
        return
    
    all_offers = []
    for offer in root.findall('.//offer'):
        url_tag = offer.find('url')
        price_tag = offer.find('price')
        if url_tag is not None and price_tag is not None:
            try:
                price = float(price_tag.text)
                url_with_pid = url_tag.text
                all_offers.append((price, url_with_pid))
            except:
                continue
    
    print(f"Загружено товаров: {len(all_offers)}")
    
    if len(all_offers) > 20:
        offers = random.sample(all_offers, 20)
    else:
        offers = all_offers
    
    print(f"Выбрано случайных товаров для проверки: {len(offers)}\n")
    
    errors = []
    correct = 0
    offers_checked = []
    
    for i, (price_csv, url_with_pid) in enumerate(offers, 1):
        print(f"[{i}/20] Проверка: {url_with_pid}")
        print(f"   Прайс: {price_csv:.0f} RUB")
        
        status = "OK"
        price_site = None
        
        try:
            response = requests.get(url_with_pid, headers=HEADERS, timeout=15)
            response.raise_for_status()
            price_site = parse_price(response.text)
            
            if price_site is None:
                print(f"   Ошибка: цена не найдена на странице")
                errors.append((url_with_pid, price_csv, None, "PRICE_NOT_FOUND"))
                status = "PRICE_NOT_FOUND"
            elif abs(price_site - price_csv) > 10:
                diff = abs(price_site - price_csv)
                print(f"   Расхождение: сайт {price_site:.0f} RUB (разница {diff:.0f} RUB)")
                errors.append((url_with_pid, price_csv, price_site, f"DIFF_{diff:.0f}"))
                status = f"DIFF_{diff:.0f}"
            else:
                print(f"   Цена совпадает: {price_site:.0f} RUB")
                correct += 1
                status = "OK"
                
        except Exception as e:
            print(f"   Ошибка запроса: {e}")
            errors.append((url_with_pid, price_csv, None, f"REQUEST_ERROR"))
            status = "REQUEST_ERROR"
        
        offers_checked.append((price_csv, url_with_pid, price_site, status))
        time.sleep(1.0)
    
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("="*70)
    print(f"Корректных цен: {correct}/{len(offers)} ({correct/len(offers)*100:.1f}%)")
    print(f"Ошибок: {len(errors)}")
    print(f"Время: {total_time:.1f} сек")
    print("="*70)
    
    save_report(offers_checked, errors, correct, total_time)

if __name__ == "__main__":
    print("="*70)
    print("ПРОВЕРКА ЦЕН С PID (20 случайных товаров)")
    print("="*70)
    print("Требование: цена в прайсе должна совпадать с ценой на странице")
    print("Допуск: +/-10 RUB")
    print("="*70 + "\n")
    
    check_prices()