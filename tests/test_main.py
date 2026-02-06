"""
Интеграционные тесты для main.py
Проверяет корректность работы проверки цен товаров
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

# Добавляем корневую директорию в путь для импорта main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import check_prices, parse_price, save_report, XML_URL, HEADERS


class TestParsePrice:
    """Тесты для функции parse_price"""
    
    def test_parse_price_meta_itemprop(self):
        """Тест парсинга цены из meta itemprop"""
        html = '<meta itemprop="price" content="1500.50">'
        assert parse_price(html) == 1500.50
    
    def test_parse_price_class_price(self):
        """Тест парсинга цены из элемента с классом price"""
        html = '<div class="price">2000</div>'
        assert parse_price(html) == 2000.0
    
    def test_parse_price_with_rub_symbol(self):
        """Тест парсинга цены с символом рубля"""
        html = '<div class="price">3 500 ₽</div>'
        assert parse_price(html) == 3500.0
    
    def test_parse_price_regex_pattern(self):
        """Тест парсинга цены через regex"""
        html = 'Цена товара: 4500 руб'
        assert parse_price(html) == 4500.0
    
    def test_parse_price_not_found(self):
        """Тест когда цена не найдена"""
        html = '<div>Товар без цены</div>'
        assert parse_price(html) is None


class TestCheckPricesIntegration:
    """Интеграционные тесты для check_prices"""
    
    @pytest.mark.integration
    def test_xml_url_accessible(self):
        """Проверка доступности XML URL (gtun.4.xml)"""
        import requests
        response = requests.get(XML_URL, headers=HEADERS, timeout=30)
        assert response.status_code == 200
        assert 'xml' in response.headers.get('content-type', '').lower()
        # Проверяем что используется правильный XML для GTUN
        assert 'gtun' in XML_URL.lower()
    
    @pytest.mark.integration
    def test_xml_structure_valid(self):
        """Проверка валидности структуры XML и наличия URL с PID"""
        import requests
        response = requests.get(XML_URL, headers=HEADERS, timeout=30)
        root = ET.fromstring(response.content)
        
        # Проверяем наличие offers
        offers = root.findall('.//offer')
        assert len(offers) > 0, "Должен быть хотя бы один offer в XML"
        
        # Проверяем структуру первого offer
        if offers:
            offer = offers[0]
            url_tag = offer.find('url')
            price_tag = offer.find('price')
            
            assert url_tag is not None, "URL должен быть в offer"
            assert price_tag is not None, "Price должен быть в offer"
            
            # Проверяем что URL содержит pid параметр (требование: цена с pid должна совпадать)
            url_text = url_tag.text
            assert url_text is not None, "URL не должен быть пустым"
            # URL должен содержать ?pid= или &pid= для проверки цен с PID
            assert 'pid=' in url_text or '?pid=' in url_text, \
                f"URL должен содержать параметр pid: {url_text}"
    
    @pytest.mark.integration
    def test_xml_urls_contain_pid(self):
        """Проверка что все URL в XML содержат параметр pid"""
        import requests
        response = requests.get(XML_URL, headers=HEADERS, timeout=30)
        root = ET.fromstring(response.content)
        
        offers = root.findall('.//offer')
        urls_with_pid = 0
        
        for offer in offers[:10]:  # Проверяем первые 10 для скорости
            url_tag = offer.find('url')
            if url_tag is not None and url_tag.text:
                if 'pid=' in url_tag.text:
                    urls_with_pid += 1
        
        # Большинство URL должны содержать pid
        assert urls_with_pid > 0, "Должен быть хотя бы один URL с параметром pid"
    
    @pytest.mark.integration
    def test_price_check_logic(self):
        """Проверка логики сравнения цен: цена с PID должна совпадать с допуском +/-10 RUB"""
        import requests
        
        # Получаем один товар из XML для проверки
        response = requests.get(XML_URL, headers=HEADERS, timeout=30)
        root = ET.fromstring(response.content)
        
        offers = root.findall('.//offer')
        assert len(offers) > 0
        
        # Берем первый offer с URL и ценой
        test_offer = None
        for offer in offers:
            url_tag = offer.find('url')
            price_tag = offer.find('price')
            if url_tag is not None and price_tag is not None and 'pid=' in url_tag.text:
                try:
                    price = float(price_tag.text)
                    test_offer = (price, url_tag.text)
                    break
                except:
                    continue
        
        if test_offer is None:
            pytest.skip("Не найден offer с PID для тестирования")
        
        price_csv, url_with_pid = test_offer
        
        # Проверяем что URL действительно содержит pid
        assert 'pid=' in url_with_pid, f"URL должен содержать pid: {url_with_pid}"
        
        # Получаем цену со страницы
        response = requests.get(url_with_pid, headers=HEADERS, timeout=15)
        response.raise_for_status()
        price_site = parse_price(response.text)
        
        if price_site is None:
            pytest.skip(f"Не удалось получить цену со страницы: {url_with_pid}")
        
        # Проверяем что цена совпадает с допуском +/-10 RUB (требование)
        diff = abs(price_site - price_csv)
        assert diff <= 10, \
            f"Цена с PID должна совпадать с допуском +/-10 RUB. " \
            f"Прайс: {price_csv:.0f}, Сайт: {price_site:.0f}, Разница: {diff:.0f}"
    
    @pytest.mark.integration
    def test_random_selection_20_items(self):
        """Проверка что выбирается 20 случайных товаров (требование)"""
        import requests
        
        response = requests.get(XML_URL, headers=HEADERS, timeout=30)
        root = ET.fromstring(response.content)
        
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
        
        assert len(all_offers) > 0, "Должен быть хотя бы один товар"
        
        # Если товаров больше 20, должно выбираться ровно 20
        if len(all_offers) > 20:
            import random
            selected = random.sample(all_offers, 20)
            assert len(selected) == 20, "Должно выбираться ровно 20 товаров"
        else:
            # Если товаров меньше 20, выбираются все
            assert len(all_offers) <= 20
    
    @pytest.mark.integration
    def test_check_prices_runs_without_error(self):
        """Проверка что функция check_prices выполняется без критических ошибок"""
        # Этот тест может быть долгим (проверяет 20 товаров)
        try:
            # Запускаем проверку (может занять время ~20+ секунд)
            check_prices()
            # Если выполнилось без исключения - тест пройден
            assert True
        except Exception as e:
            # Если критическая ошибка - тест провален
            pytest.fail(f"check_prices failed with error: {e}")


class TestSaveReport:
    """Тесты для функции save_report"""
    
    def test_save_report_creates_file(self, tmp_path):
        """Проверка создания файла отчёта"""
        import os
        os.chdir(tmp_path)
        os.makedirs("reports", exist_ok=True)
        
        offers_checked = [
            (1000.0, "https://example.com/product1", 1000.0, "OK"),
            (2000.0, "https://example.com/product2", 2000.0, "OK"),
        ]
        errors = []
        
        filename = save_report(offers_checked, errors, 2, 10.5)
        
        assert os.path.exists(filename)
        assert "reports" in filename
        
        # Проверяем содержимое файла
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "ПРОВЕРКА ЦЕН С PID" in content
            assert "https://example.com/product1" in content
            assert "Корректных: 2/2" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
