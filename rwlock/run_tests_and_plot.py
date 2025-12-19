#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный скрипт для тестирования rwlock реализаций и построения графиков
Заменяет test_simple.bat, test_rwlock.bat и plot_rwlock_comparison.py
"""

import subprocess
import os
import sys
import csv
import time
from typing import List, Tuple

# Попытка импорта библиотек для графиков (опционально)
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("ВНИМАНИЕ: pandas/matplotlib не установлены.")
    print("Установите зависимости: pip install pandas matplotlib numpy")
    print("Режим построения графиков недоступен, но тестирование работает.\n")


# Конфигурация тестов
INITIAL_KEYS = 1000
TOTAL_OPS_VALUES = [10000, 50000, 100000]
THREAD_COUNTS = [1, 2, 4, 8]
TEST_CONFIGS = [
    (0.80, 0.10),  
    (0.90, 0.05), 
    (0.99, 0.005), # 99% поиск, 0.5% вставка, 0.5% удаление
]

# Имена программ
STDLIB_PROG = "pth_ll_rwl_stdlib.exe" if sys.platform == "win32" else "./pth_ll_rwl_stdlib"
CUSTOM_PROG = "pth_ll_rwl_custom.exe" if sys.platform == "win32" else "./pth_ll_rwl_custom"

OUTPUT_CSV = "rwlock_results.csv"
OUTPUT_PLOT = "rwlock_comparison.png"


def compile_programs():
    """Компиляция обеих программ"""
    print("=" * 70)
    print("Компиляция программ...")
    print("=" * 70)
    
    cmd_stdlib = [
        "gcc", "-o", "pth_ll_rwl_stdlib",
        "pth_ll_rwl_stdlib.c", "my_rand.c",
        "-lpthread", "-Wall"
    ]
    
    cmd_custom = [
        "gcc", "-o", "pth_ll_rwl_custom",
        "pth_ll_rwl_custom.c", "my_rand.c", "my_rwlock.c",
        "-lpthread", "-Wall"
    ]
    
    try:
        print("Компилирую stdlib версию...")
        result = subprocess.run(cmd_stdlib, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Ошибка компиляции stdlib: {result.stderr}")
            return False
        print("  [OK] stdlib версия скомпилирована")
        
        print("Компилирую custom версию...")
        result = subprocess.run(cmd_custom, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Ошибка компиляции custom: {result.stderr}")
            return False
        print("  [OK] custom версия скомпилирована")
        
        print()
        return True
        
    except FileNotFoundError:
        print("Ошибка: gcc не найден. Убедитесь, что GCC установлен.")
        return False


def run_single_test(program: str, threads: int, total_ops: int, 
                   search_pct: float, insert_pct: float) -> Tuple[bool, str]:
    """
    Запуск одного теста
    
    Возвращает: (успех, результат_csv_строка)
    """
    input_data = f"{INITIAL_KEYS}\n{total_ops}\n{search_pct}\n{insert_pct}\n"
    
    try:
        result = subprocess.run(
            [program, str(threads)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip()
        else:
            return False, ""
            
    except subprocess.TimeoutExpired:
        print(f"    Timeout при выполнении теста")
        return False, ""
    except Exception as e:
        print(f"    Ошибка: {e}")
        return False, ""


def run_all_tests():
    """Запуск всех тестов и сохранение результатов в CSV"""
    print("=" * 70)
    print("Запуск тестов...")
    print("=" * 70)
    print()
    
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['threads', 'total_ops', 'search_pct', 'insert_pct', 'time', 'implementation'])
    
    total_tests = len(TOTAL_OPS_VALUES) * len(TEST_CONFIGS) * len(THREAD_COUNTS) * 2
    current_test = 0
    
    for total_ops in TOTAL_OPS_VALUES:
        for search_pct, insert_pct in TEST_CONFIGS:
            print(f"Конфигурация: ops={total_ops}, search={search_pct:.0%}, insert={insert_pct:.1%}")
            
            for threads in THREAD_COUNTS:
                current_test += 2
                progress = (current_test / total_tests) * 100
                print(f"  [{progress:5.1f}%] Потоков: {threads}...", end=" ", flush=True)
                
                success, result = run_single_test(
                    STDLIB_PROG, threads, total_ops, search_pct, insert_pct
                )
                
                if success:
                    with open(OUTPUT_CSV, 'a', newline='') as f:
                        f.write(result + '\n')
                else:
                    print("stdlib FAILED", end=" ")
                
                success, result = run_single_test(
                    CUSTOM_PROG, threads, total_ops, search_pct, insert_pct
                )
                
                if success:
                    with open(OUTPUT_CSV, 'a', newline='') as f:
                        f.write(result + '\n')
                    print("[OK]")
                else:
                    print("custom FAILED")
            
            print()
    


def plot_comparison():
    try:
        df = pd.read_csv(OUTPUT_CSV)
        print(f"Загружено {len(df)} записей из {OUTPUT_CSV}")
        
    except FileNotFoundError:
        print(f"Ошибка: файл {OUTPUT_CSV} не найден!")
        return False
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Сравнение производительности rwlock: библиотечная vs кастомная реализация', 
                 fontsize=16, fontweight='bold')
    
    ax1 = axes[0, 0]
    
    grouped = df.groupby(['implementation', 'threads'])['time'].mean().reset_index()
    
    stdlib_data = grouped[grouped['implementation'] == 'stdlib']
    custom_data = grouped[grouped['implementation'] == 'custom']
    
    if len(stdlib_data) > 0:
        ax1.plot(stdlib_data['threads'], stdlib_data['time'], 
                marker='o', linewidth=2, markersize=8, label='Библиотечная (pthread)')
    if len(custom_data) > 0:
        ax1.plot(custom_data['threads'], custom_data['time'], 
                marker='s', linewidth=2, markersize=8, label='Кастомная реализация')
    
    ax1.set_xlabel('Количество потоков', fontsize=12)
    ax1.set_ylabel('Время выполнения (сек)', fontsize=12)
    ax1.set_title('Зависимость времени от количества потоков', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(sorted(df['threads'].unique()))
    
    ax2 = axes[0, 1]
    
    for impl in ['stdlib', 'custom']:
        impl_data = grouped[grouped['implementation'] == impl]
        if len(impl_data) > 0 and impl_data[impl_data['threads'] == 1]['time'].values.size > 0:
            base_time = impl_data[impl_data['threads'] == 1]['time'].values[0]
            speedup = base_time / impl_data['time']
            
            label = 'Библиотечная (pthread)' if impl == 'stdlib' else 'Кастомная реализация'
            marker = 'o' if impl == 'stdlib' else 's'
            ax2.plot(impl_data['threads'], speedup, 
                    marker=marker, linewidth=2, markersize=8, label=label)
    
    thread_counts = sorted(df['threads'].unique())
    ax2.plot(thread_counts, thread_counts, 
            'k--', linewidth=1.5, alpha=0.5, label='Идеальное ускорение')
    
    ax2.set_xlabel('Количество потоков', fontsize=12)
    ax2.set_ylabel('Ускорение', fontsize=12)
    ax2.set_title('Ускорение от количества потоков', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(thread_counts)
    
    ax3 = axes[1, 0]
    
    search_grouped = df.groupby(['implementation', 'search_pct'])['time'].mean().reset_index()
    
    stdlib_search = search_grouped[search_grouped['implementation'] == 'stdlib']
    custom_search = search_grouped[search_grouped['implementation'] == 'custom']
    
    if len(stdlib_search) > 0:
        ax3.plot(stdlib_search['search_pct'] * 100, stdlib_search['time'], 
                marker='o', linewidth=2, markersize=8, label='Библиотечная (pthread)')
    if len(custom_search) > 0:
        ax3.plot(custom_search['search_pct'] * 100, custom_search['time'], 
                marker='s', linewidth=2, markersize=8, label='Кастомная реализация')
    
    ax3.set_xlabel('Доля операций чтения (%)', fontsize=12)
    ax3.set_ylabel('Время выполнения (сек)', fontsize=12)
    ax3.set_title('Влияние доли операций чтения на производительность', 
                  fontsize=13, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    ax4 = axes[1, 1]
    
    ops_grouped = df.groupby(['implementation', 'total_ops'])['time'].mean().reset_index()
    
    stdlib_ops = ops_grouped[ops_grouped['implementation'] == 'stdlib']
    custom_ops = ops_grouped[ops_grouped['implementation'] == 'custom']
    
    x_pos = np.arange(len(stdlib_ops))
    width = 0.35
    
    if len(stdlib_ops) > 0:
        ax4.bar(x_pos - width/2, stdlib_ops['time'], width, 
               label='Библиотечная (pthread)', alpha=0.8)
    if len(custom_ops) > 0:
        ax4.bar(x_pos + width/2, custom_ops['time'], width, 
               label='Кастомная реализация', alpha=0.8)
    
    ax4.set_xlabel('Количество операций', fontsize=12)
    ax4.set_ylabel('Время выполнения (сек)', fontsize=12)
    ax4.set_title('Сравнение по количеству операций', fontsize=13, fontweight='bold')
    if len(stdlib_ops) > 0:
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels(stdlib_ops['total_ops'].values)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    plt.savefig(OUTPUT_PLOT, dpi=300, bbox_inches='tight')
    print(f"[OK] Графики сохранены в файл: {OUTPUT_PLOT}")
    

    print("Производительность:")
    
    for impl in ['stdlib', 'custom']:
        impl_name = 'Библиотечная (pthread)' if impl == 'stdlib' else 'Кастомная реализация'
        impl_data = df[df['implementation'] == impl]['time']
        
        print(f"\n{impl_name}:")
        print(f"  Среднее время: {impl_data.mean():.6f} сек")
        print(f"  Медианное время: {impl_data.median():.6f} сек")
        print(f"  Мин. время: {impl_data.min():.6f} сек")
        print(f"  Макс. время: {impl_data.max():.6f} сек")
        print(f"  Стд. отклонение: {impl_data.std():.6f} сек")
    
    stdlib_mean = df[df['implementation'] == 'stdlib']['time'].mean()
    custom_mean = df[df['implementation'] == 'custom']['time'].mean()
    
    
    if stdlib_mean < custom_mean:
        diff_pct = ((custom_mean - stdlib_mean) / stdlib_mean) * 100
        print(f"\nБиблиотечная реализация быстрее на {diff_pct:.2f}%")
    else:
        diff_pct = ((stdlib_mean - custom_mean) / custom_mean) * 100
        print(f"\nКастомная реализация быстрее на {diff_pct:.2f}%")
    
    
    try:
        plt.show()
    except:
        print("\nПримечание: не удалось отобразить график (возможно, запущено без GUI)")
    
    return True


def main():
    # Проверяем существование программ
    stdlib_exists = os.path.exists(STDLIB_PROG.replace('.exe', '') if sys.platform != 'win32' else STDLIB_PROG)
    custom_exists = os.path.exists(CUSTOM_PROG.replace('.exe', '') if sys.platform != 'win32' else CUSTOM_PROG)
    
    if not stdlib_exists or not custom_exists:
        print("Программы не найдены. Попытка компиляции...")
        if not compile_programs():
            print("Ошибка компиляции. Завершение.")
            return 1
    else:
        print("[OK] Программы найдены")
        print()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        start_time = time.time()
        
        # Запускаем тесты
        run_all_tests()
        
        # Строим графики (если доступны библиотеки)
        if PLOTTING_AVAILABLE:
            plot_comparison()
        else:
            print("\n" + "=" * 70)
            print("Графики не построены (pandas/matplotlib не установлены)")
            print("Результаты доступны в файле:", OUTPUT_CSV)
            print("=" * 70)
        
    
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())

