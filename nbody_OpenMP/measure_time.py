import argparse
import matplotlib.pyplot as plt
import pandas as pd
import subprocess
import time
import os
import random


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", default="./nbody")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--output", default="stats.csv")
    parser.add_argument("--t_end", type=float, default=10.0)
    parser.add_argument("--dt", type=float, default=0.01)

    return parser.parse_args()


def generate_test_file(n, filename):
    if os.path.exists(filename):
        return
    
    print(f"  Генерация {filename}")
    with open(filename, "w") as f:
        f.write(f"{n}\n")
        for _ in range(n):
            mass = random.uniform(1e10, 1e12)
            x = random.uniform(-1e6, 1e6)
            y = random.uniform(-1e6, 1e6)
            z = random.uniform(-1e6, 1e6)
            vx = random.uniform(-1e3, 1e3)
            vy = random.uniform(-1e3, 1e3)
            vz = random.uniform(-1e3, 1e3)
            f.write(f"{mass} {x} {y} {z} {vx} {vy} {vz}\n")


def run_single(executable, t_end, input_file, dt, num_threads):
    cmd = [executable, str(t_end), input_file, "/dev/null", str(dt), str(num_threads)]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    stdout = result.stdout.strip()
    
    if stdout:
        parts = stdout.split(",")
        if len(parts) >= 4:
            return {
                "time": float(parts[0]),
                "particles": int(parts[1]),
                "total_steps": int(parts[2]),
                "num_threads": int(parts[3])
            }
    return None


def run_benchmark(executable, t_end, input_file, dt, num_threads, retries):
    times = []
    last_result = None
    
    for i in range(retries):
        result = run_single(executable, t_end, input_file, dt, num_threads)
        if result:
            times.append(result["time"])
            last_result = result
        time.sleep(0.05)
    
    if times and last_result:
        avg_time = sum(times) / len(times)
        last_result["time"] = avg_time
        return last_result
    return None


def draw_graphs(output):
    df = pd.read_csv(output)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    fig.suptitle("OpenMP N-body Simulation: Задача N тел", fontsize=14)

    df_particles = df[df["experiment"] == "particles"]
    if not df_particles.empty:
        axes[0].plot(df_particles["particles"], df_particles["time"], "o-", linewidth=2, markersize=8)
        axes[0].set_title("Время выполнения от числа частиц")
        axes[0].set_xlabel("Число частиц N")
        axes[0].set_ylabel("Время, с")
        axes[0].set_xscale("log")
        axes[0].set_yscale("log")
        axes[0].grid(True, which="both", linestyle="--", alpha=0.7)

    df_threads = df[df["experiment"] == "threads"]
    if not df_threads.empty:
        axes[1].plot(df_threads["num_threads"], df_threads["time"], "o-", linewidth=2, markersize=8, color="orange")
        axes[1].set_title("Время выполнения от числа потоков (N=1000)")
        axes[1].set_xlabel("Число потоков")
        axes[1].set_ylabel("Время, с")
        axes[1].grid(True, which="both", linestyle="--", alpha=0.7)

    df_speedup = df[df["experiment"] == "threads"].copy()
    if not df_speedup.empty:
        base_time = df_speedup[df_speedup["num_threads"] == 1]["time"].values
        if len(base_time) > 0:
            df_speedup["speedup"] = base_time[0] / df_speedup["time"]
            axes[2].plot(df_speedup["num_threads"], df_speedup["speedup"], "o-", linewidth=2, markersize=8, color="green")
            axes[2].plot(df_speedup["num_threads"], df_speedup["num_threads"], "--", linewidth=1, color="gray", label="Идеальное ускорение")
            axes[2].set_title("Ускорение от числа потоков (N=1000)")
            axes[2].set_xlabel("Число потоков")
            axes[2].set_ylabel("Ускорение")
            axes[2].legend()
            axes[2].grid(True, which="both", linestyle="--", alpha=0.7)

    df_eff = df[df["experiment"] == "threads"].copy()
    if not df_eff.empty:
        base_time = df_eff[df_eff["num_threads"] == 1]["time"].values
        if len(base_time) > 0:
            df_eff["efficiency"] = (base_time[0] / df_eff["time"]) / df_eff["num_threads"] * 100
            axes[3].plot(df_eff["num_threads"], df_eff["efficiency"], "o-", linewidth=2, markersize=8, color="red")
            axes[3].axhline(y=100, linestyle="--", linewidth=1, color="gray", label="Идеальная эффективность")
            axes[3].set_title("Эффективность параллелизации (N=1000)")
            axes[3].set_xlabel("Число потоков")
            axes[3].set_ylabel("Эффективность, %")
            axes[3].legend()
            axes[3].grid(True, which="both", linestyle="--", alpha=0.7)

    plt.tight_layout()
    output_file = output[:output.find('.')] + "_graph.png"
    plt.savefig(output_file, dpi=300)
    print(f"Графики сохранены в {output_file}")


def openmp_task(args):
    
    particles_list = [100, 200, 500, 1000, 2000, 5000]
    threads_list = [1, 2, 4, 6, 8, 10]
    
    results = []
    
    print("\n=== Генерация тестовых файлов ===")
    for n in particles_list:
        generate_test_file(n, f"test_input_{n}.txt")
    
    print("\n=== Зависимость времени от числа частиц (threads=4) ===")
    for n in particles_list:
        input_file = f"test_input_{n}.txt"
        print(f"  N={n}...", end=" ", flush=True)
        
        result = run_benchmark(
            args.executable, args.t_end, input_file, args.dt,
            num_threads=4, retries=args.retries
        )
        
        if result:
            results.append({
                "experiment": "particles",
                "particles": result["particles"],
                "num_threads": result["num_threads"],
                "total_steps": result["total_steps"],
                "time": result["time"]
            })
            print(f"время = {result['time']:.4f} с")
        else:
            print("ОШИБКА")
    
    print("\n=== Зависимость времени от числа потоков (N=1000) ===")
    n = 1000
    input_file = f"test_input_{n}.txt"
    
    for num_threads in threads_list:
        print(f"  threads={num_threads}...", end=" ", flush=True)
        
        result = run_benchmark(
            args.executable, args.t_end, input_file, args.dt,
            num_threads=num_threads, retries=args.retries
        )
        
        if result:
            results.append({
                "experiment": "threads",
                "particles": result["particles"],
                "num_threads": num_threads,
                "total_steps": result["total_steps"],
                "time": result["time"]
            })
            print(f"время = {result['time']:.4f} с")
        else:
            print("ОШИБКА")
    
    print("\n=== Зависимость времени от числа потоков (разные N, разные потоки) ===")
    for n in [500, 1000, 2000]:
        input_file = f"test_input_{n}.txt"
        print(f"  N={n}:")
        
        for num_threads in [1, 2, 4, 8]:
            print(f"    threads={num_threads}...", end=" ", flush=True)
            
            result = run_benchmark(
                args.executable, args.t_end, input_file, args.dt,
                num_threads=num_threads, retries=args.retries
            )
            
            if result:
                results.append({
                    "experiment": "scalability",
                    "particles": result["particles"],
                    "num_threads": num_threads,
                    "total_steps": result["total_steps"],
                    "time": result["time"]
                })
                print(f"время = {result['time']:.4f} с")
    
    df = pd.DataFrame(results)
    df.to_csv(args.output, index=False)
    print(f"\Результаты сохранены в {args.output}")
    print(df.to_string())

    draw_graphs(args.output)


def main():
    args = parse_args()
    openmp_task(args)


if __name__ == "__main__":
    main()
