#!/usr/bin/env python
"""
Скрипт для запуска всех тестов
"""
import sys
import subprocess

def run_tests():
    """Запускает все тесты через pytest"""
    print("="*70)
    print("Запуск интеграционных тестов GT-Shop")
    print("="*70)
    print()
    
    # Запускаем pytest
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "-m", "integration",
        "--tb=short"
    ])
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
