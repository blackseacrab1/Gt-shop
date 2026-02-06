# GT-Shop Regression Tests

Внешние интеграционные тесты для проверки работоспособности сервисов GT-Shop.

## Описание

Этот репозиторий содержит интеграционные тесты для проверки:
- **main.py** - проверка соответствия цен в прайсе и на сайте
- **sitemaps** - проверка доступности и актуальности sitemap-файлов

## Структура проекта

```
gt-shop/
├── main.py                      # Скрипт проверки цен
├── requirements.txt             # Зависимости Python
├── pytest.ini                  # Конфигурация pytest
├── .gitlab-ci.yml              # CI/CD конфигурация GitLab
├── .gitignore                  # Игнорируемые файлы
├── README.md                   # Этот файл
├── run_tests.py                # Скрипт запуска тестов
├── setup_local.bat             # Скрипт настройки (Windows)
└── tests/
    ├── __init__.py
    ├── test_main.py            # Интеграционные тесты для main.py
    ├── test_sitemaps.py        # Интеграционные тесты для sitemaps
    └── sitemap/
        └── check_sitemaps.py   # Оригинальный скрипт проверки sitemaps
```

## Установка

### Вариант 1: Без виртуального окружения (проще)

1. Клонируйте репозиторий:
```bash
git clone https://github.com/blackseacrab1/Gt-shop.git
cd Gt-shop
```

2. Установите зависимости глобально:
```bash
pip install -r requirements.txt
```

### Вариант 2: С виртуальным окружением (рекомендуется)

**Windows:**
```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
# Создать виртуальное окружение
python3 -m venv venv

# Активировать окружение
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

**Или используйте готовый скрипт:**
- Windows: `setup_local.bat`

> **Примечание:** Виртуальное окружение не обязательно! Можно установить зависимости глобально через `pip install -r requirements.txt`

## Запуск тестов

### Локальный запуск (быстрый старт)

**Если виртуальное окружение активно (или зависимости установлены глобально):**
```bash
# Все тесты
pytest tests/ -v

# Только интеграционные тесты
pytest tests/ -v -m integration

# Только тесты для main.py
pytest tests/test_main.py -v

# Только тесты для sitemaps
pytest tests/test_sitemaps.py -v -m integration
```

**Или используйте готовый скрипт:**
```bash
python run_tests.py
```

### Запуск оригинальных скриптов

```bash
# Проверка цен (проверяет 20 случайных товаров)
python main.py

# Проверка sitemaps
python tests/sitemap/check_sitemaps.py
```

### Проверка что всё работает

```bash
# 1. Проверка синтаксиса
python -m py_compile main.py tests/*.py

# 2. Быстрая проверка импортов
python -c "from main import check_prices, parse_price; print('OK')"

# 3. Запуск одного быстрого теста
pytest tests/test_main.py::TestParsePrice -v
```

## CI/CD

Тесты автоматически запускаются в GitLab CI при каждом коммите. Конфигурация находится в `.gitlab-ci.yml`.

### Стадии CI/CD:

- **test_main** - запуск тестов для main.py
- **test_sitemaps** - запуск pytest тестов для sitemaps
- **sitemap_check** - запуск оригинального скрипта check_sitemaps.py
- **test_all** - запуск всех тестов вместе

Артефакты (отчёты) сохраняются в GitLab и доступны в течение 1 недели.

## Требования

- Python 3.11+
- Доступ к интернету (для интеграционных тестов)
- Доступ к сайту https://parts.gt-shop.ru

## Описание тестов

### Тесты main.py

Проверяют:
- Парсинг цен с различных селекторов HTML
- Доступность XML прайса
- Валидность структуры XML
- Наличие параметра `pid` в URL
- Корректность работы функции проверки цен
- Выбор 20 случайных товаров
- Создание отчётов

### Тесты sitemaps

Проверяют:
- Доступность robots.txt
- Доступность основного sitemap.xml
- Доступность всех дочерних sitemap-файлов
- Актуальность дат обновления (не старше 14 дней)
- Валидность XML структуры

## Отчёты

После выполнения тестов создаются отчёты:
- `reports/check_YYYYMMDD_HHMMSS.txt` - отчёт проверки цен
- `sitemap_check_report.txt` - отчёт проверки sitemaps

## Разработка

Для добавления новых тестов:
1. Создайте файл `test_*.py` в директории `tests/`
2. Используйте маркер `@pytest.mark.integration` для интеграционных тестов
3. Следуйте структуре существующих тестов

## Лицензия

Внутренний проект для Greyhard.
