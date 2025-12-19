import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def generate_plots(filename):
    # Проверяем наличие файла
    if not os.path.exists(filename):
        print(f"Ошибка: Файл '{filename}' не найден.")
        return

    # Чтение данных
    try:
        df = pd.read_csv(filename)
    except Exception as e:
        print(f"Ошибка при чтении CSV: {e}")
        return

    # Проверка необходимых колонок
    required_columns = {'threads', 'points', 'time'}
    if not required_columns.issubset(df.columns):
        print(f"Ошибка: В CSV файле должны быть колонки: {required_columns}")
        return

    # Сортировка данных для корректного отображения линий
    df = df.sort_values(by=['points', 'threads'])

    # ---------------------------------------------------------
    # Расчет метрик (Ускорение и Эффективность)
    # ---------------------------------------------------------
    
    # Находим T_serial (время на 1 потоке) для каждого размера задачи (points)
    # Создаем словарь {points: time}, где threads == 1
    t_serial_map = df[df['threads'] == 1].set_index('points')['time'].to_dict()

    # Если для какого-то points нет данных с 1 потоком, мы не сможем посчитать ускорение
    if not t_serial_map:
        print("Ошибка: В данных отсутствуют записи с threads=1 (необходимы для расчета ускорения).")
        return

    # Добавляем колонку T_serial в датафрейм, сопоставляя по points
    df['t_serial'] = df['points'].map(t_serial_map)

    # Вычисляем Ускорение (Speedup): S = T_serial / T_parallel
    df['speedup'] = df['t_serial'] / df['time']

    # Вычисляем Эффективность (Efficiency): E = S / p
    df['efficiency'] = df['speedup'] / df['threads']

    # ---------------------------------------------------------
    # Построение графиков
    # ---------------------------------------------------------
    
    # Создаем фигуру с 3 подграфиками (Time, Speedup, Efficiency)
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Получаем уникальные размеры задач для построения отдельных линий
    unique_points = sorted(df['points'].unique())

    # --- График 1: Время выполнения (Time) ---
    ax = axes[0]
    for p in unique_points:
        subset = df[df['points'] == p]
        ax.plot(subset['threads'], subset['time'], marker='o', label=f'Points: {p}')
    
    ax.set_title('Время выполнения (Time)')
    ax.set_xlabel('Количество потоков (p)')
    ax.set_ylabel('Время (сек)')
    ax.set_yscale('log') # Логарифмическая шкала удобна, если разброс времени велик
    ax.grid(True, which="both", ls="-", alpha=0.5)
    ax.legend()

    # --- График 2: Ускорение (Speedup) ---
    ax = axes[1]
    for p in unique_points:
        subset = df[df['points'] == p]
        ax.plot(subset['threads'], subset['speedup'], marker='o', label=f'Points: {p}')
    
    # Добавляем линию идеального ускорения (y = x)
    max_threads = df['threads'].max()
    ax.plot([1, max_threads], [1, max_threads], 'k--', label='Идеальное ускорение', alpha=0.5)

    ax.set_title('Ускорение (Speedup)')
    ax.set_xlabel('Количество потоков (p)')
    ax.set_ylabel('S = T_serial / T_parallel')
    ax.grid(True, ls="-", alpha=0.5)
    ax.legend()

    # --- График 3: Эффективность (Efficiency) ---
    ax = axes[2]
    for p in unique_points:
        subset = df[df['points'] == p]
        ax.plot(subset['threads'], subset['efficiency'], marker='o', label=f'Points: {p}')

    # Добавляем линию идеальной эффективности (y = 1)
    ax.axhline(y=1.0, color='k', linestyle='--', label='Идеальная эффективность', alpha=0.5)

    ax.set_title('Эффективность (Efficiency)')
    ax.set_xlabel('Количество потоков (p)')
    ax.set_ylabel('E = S / p')
    ax.set_ylim(0, 1.2) # Обычно эффективность от 0 до 1 (иногда выше из-за кэша)
    ax.grid(True, ls="-", alpha=0.5)
    ax.legend()

    plt.tight_layout()
    
    # Сохранение или показ
    output_img = 'performance_plots.png'
    plt.savefig(output_img)
    print(f"Графики успешно сохранены в файл: {output_img}")
    plt.show()

if __name__ == "__main__":
    # Имя файла по умолчанию или из аргумента командной строки
    csv_file = "performance_results.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    generate_plots(csv_file)