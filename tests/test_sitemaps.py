"""
Интеграционные тесты для проверки sitemaps
Проверяет доступность и актуальность sitemap-файлов
"""
import pytest
import sys
import os
import urllib.request
from xml.etree import ElementTree as ET
from datetime import datetime, timezone

# Импортируем модуль check_sitemaps
sitemap_dir = os.path.join(os.path.dirname(__file__), 'sitemap')
check_sitemaps_path = os.path.join(sitemap_dir, "check_sitemaps.py")

import importlib.util
spec = importlib.util.spec_from_file_location("check_sitemaps", check_sitemaps_path)
check_sitemaps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_sitemaps)

# Импортируем необходимые константы и функции
BASE_URL = check_sitemaps.BASE_URL
SITEMAP_INDEX_URL = check_sitemaps.SITEMAP_INDEX_URL
ROBOTS_URL = check_sitemaps.ROBOTS_URL
MAX_DAYS_OLD = check_sitemaps.MAX_DAYS_OLD
fetch_xml = check_sitemaps.fetch_xml
check_robots_txt = check_sitemaps.check_robots_txt
parse_sitemap_index = check_sitemaps.parse_sitemap_index
get_lastmod_from_sitemap = check_sitemaps.get_lastmod_from_sitemap
check_sitemap_freshness = check_sitemaps.check_sitemap_freshness


class TestRobotsTxt:
    """Тесты для проверки robots.txt"""
    
    @pytest.mark.integration
    def test_robots_txt_accessible(self):
        """Проверка доступности robots.txt"""
        try:
            with urllib.request.urlopen(ROBOTS_URL, timeout=10) as resp:
                assert resp.getcode() == 200
        except Exception as e:
            pytest.fail(f"robots.txt недоступен: {e}")
    
    @pytest.mark.integration
    def test_robots_txt_content(self):
        """Проверка содержимого robots.txt"""
        try:
            with urllib.request.urlopen(ROBOTS_URL, timeout=10) as resp:
                content = resp.read().decode('utf-8')
                assert len(content) > 0
                # Проверяем наличие упоминания sitemap
                assert 'sitemap' in content.lower()
        except Exception as e:
            pytest.fail(f"Ошибка при чтении robots.txt: {e}")


class TestSitemapIndex:
    """Тесты для основного sitemap.xml"""
    
    @pytest.mark.integration
    def test_sitemap_index_accessible(self):
        """Проверка доступности основного sitemap.xml"""
        root = fetch_xml(SITEMAP_INDEX_URL)
        assert root is not None
    
    @pytest.mark.integration
    def test_sitemap_index_structure(self):
        """Проверка структуры sitemap.xml"""
        root = fetch_xml(SITEMAP_INDEX_URL)
        assert root is not None
        
        # Проверяем namespace
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        assert root.tag == f"{namespace}urlset" or root.tag == f"{namespace}sitemapindex"
    
    @pytest.mark.integration
    def test_sitemap_index_has_sitemaps(self):
        """Проверка наличия дочерних sitemap-файлов"""
        root = fetch_xml(SITEMAP_INDEX_URL)
        assert root is not None
        
        sitemap_urls = parse_sitemap_index(root)
        assert len(sitemap_urls) > 0, "Должен быть хотя бы один sitemap-файл"


class TestSitemapFiles:
    """Тесты для дочерних sitemap-файлов"""
    
    @pytest.fixture
    def sitemap_urls(self):
        """Фикстура для получения списка sitemap URL"""
        root = fetch_xml(SITEMAP_INDEX_URL)
        if root is None:
            pytest.skip("Не удалось загрузить основной sitemap.xml")
        urls = parse_sitemap_index(root)
        if not urls:
            pytest.skip("Нет дочерних sitemap-файлов")
        return urls
    
    @pytest.mark.integration
    def test_sitemap_files_accessible(self, sitemap_urls):
        """Проверка доступности всех sitemap-файлов"""
        failed_urls = []
        
        for url in sitemap_urls[:5]:  # Ограничиваем для скорости тестов
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    assert resp.getcode() == 200, f"{url} вернул статус {resp.getcode()}"
            except Exception as e:
                failed_urls.append((url, str(e)))
        
        if failed_urls:
            pytest.fail(f"Недоступные sitemap-файлы: {failed_urls}")
    
    @pytest.mark.integration
    def test_sitemap_files_freshness(self, sitemap_urls):
        """Проверка актуальности sitemap-файлов"""
        failed_urls = []
        
        for url in sitemap_urls[:5]:  # Ограничиваем для скорости тестов
            if not check_sitemap_freshness(url):
                failed_urls.append(url)
        
        # Предупреждаем, но не проваливаем тест полностью
        if len(failed_urls) > len(sitemap_urls[:5]) * 0.5:  # Если больше 50% устарели
            pytest.fail(f"Слишком много устаревших sitemap-файлов: {len(failed_urls)}/{len(sitemap_urls[:5])}")
    
    @pytest.mark.integration
    def test_sitemap_files_valid_xml(self, sitemap_urls):
        """Проверка валидности XML в sitemap-файлах"""
        failed_urls = []
        
        for url in sitemap_urls[:5]:  # Ограничиваем для скорости тестов
            root = fetch_xml(url)
            if root is None:
                failed_urls.append(url)
        
        if failed_urls:
            pytest.fail(f"Невалидные XML в sitemap-файлах: {failed_urls}")


class TestSitemapFunctions:
    """Тесты для вспомогательных функций"""
    
    def test_parse_sitemap_index(self):
        """Тест парсинга индекса sitemap"""
        root = fetch_xml(SITEMAP_INDEX_URL)
        if root is None:
            pytest.skip("Не удалось загрузить sitemap.xml")
        
        urls = parse_sitemap_index(root)
        assert isinstance(urls, list)
        for url in urls:
            assert url.startswith('http')
    
    def test_get_lastmod_from_sitemap(self):
        """Тест извлечения lastmod из sitemap"""
        root = fetch_xml(SITEMAP_INDEX_URL)
        if root is None:
            pytest.skip("Не удалось загрузить sitemap.xml")
        
        sitemap_urls = parse_sitemap_index(root)
        if not sitemap_urls:
            pytest.skip("Нет дочерних sitemap-файлов")
        
        # Проверяем первый sitemap
        test_url = sitemap_urls[0]
        test_root = fetch_xml(test_url)
        if test_root is None:
            pytest.skip(f"Не удалось загрузить {test_url}")
        
        lastmod = get_lastmod_from_sitemap(test_root)
        # lastmod может быть None, это допустимо
        if lastmod is not None:
            assert isinstance(lastmod, datetime)
            assert lastmod.tzinfo is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
