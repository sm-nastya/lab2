import argparse
import matplotlib.pyplot as plt
import pandas as pd
import subprocess
import time
import os
import random


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--executable", default="./data"
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--output", default="stats.csv")
    parser.add_argument("--t_end", type=float, default=10.0)
    parser.add_argument("--dt", type=float, default=0.01)

    return parser.parse_args()


def run_single(executable, t_end, input_file, dt, block_size, num_blocks=0):
    cmd = [executable, str(t_end), input_file, "/dev/null", str(dt), str(block_size)]
    if num_blocks > 0:
        cmd.append(str(num_blocks))
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    stdout = result.stdout.strip()
    
    if stdout:
        parts = stdout.split(",")   
        if len(parts) >= 5:
            return {
                "time": float(parts[0]),
                "particles": int(parts[1]),
                "total_steps": int(parts[2]),
                "num_blocks": int(parts[3]),
                "threads": int(parts[4])
            }
    return None


def run_benchmark(executable, t_end, input_file, dt, block_size, num_blocks, retries):
    times = []
    last_result = None
    
    for i in range(retries):
        result = run_single(executable, t_end, input_file, dt, block_size, num_blocks)
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
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("CUDA N-body Simulation: Задача N тел", fontsize=14)

    # График 1: Время от числа частиц
    df_particles = df[df["experiment"] == "particles"]
    if not df_particles.empty:
        axes[0].plot(df_particles["particles"], df_particles["time"], "o-", linewidth=2, markersize=8)
        axes[0].set_title("Время выполнения от числа частиц")
        axes[0].set_xlabel("Число частиц N")
        axes[0].set_ylabel("Время, с")
        axes[0].set_xscale("log")
        axes[0].set_yscale("log")
        axes[0].grid(True, which="both", linestyle="--", alpha=0.7)

    # График 2: Время от block_size
    df_block = df[df["experiment"] == "block_size"]
    if not df_block.empty:
        axes[1].plot(df_block["block_size"], df_block["time"], "o-", linewidth=2, markersize=8, color="orange")
        axes[1].set_title("Время выполнения от block_size (N=5000)")
        axes[1].set_xlabel("Threads per block")
        axes[1].set_ylabel("Время, с")
        axes[1].grid(True, which="both", linestyle="--", alpha=0.7)

    # График 3: Время от num_blocks
    df_blocks = df[df["experiment"] == "num_blocks"]
    if not df_blocks.empty:
        axes[2].plot(df_blocks["num_blocks"], df_blocks["time"], "o-", linewidth=2, markersize=8, color="green")
        axes[2].set_title("Время выполнения от num_blocks (N=5000)")
        axes[2].set_xlabel("Number of blocks")
        axes[2].set_ylabel("Время, с")
        axes[2].set_ylim(0, df_blocks["time"].max() * 1.1)  # Ось Y начинается с 0
        axes[2].grid(True, which="both", linestyle="--", alpha=0.7)

    plt.tight_layout()
    output_file = output[:output.find('.')] + "_graph.png"
    plt.savefig(output_file, dpi=300)
    print(f"Графики сохранены в {output_file}")


def cuda_task(args):    
    particles_list = [100, 500, 1000, 2000, 5000, 10000]
    block_sizes = [1, 32, 64, 128, 256, 512, 1024]
    num_blocks_list = [1, 2, 4, 8, 16, 32, 64, 128]
    
    results = []
    
    print("\n=== Эксперимент 1: Зависимость от числа частиц ===")
    for n in particles_list:
        input_file = f"test_input_{n}.txt"
        print(f"  N={n}...", end=" ", flush=True)
        
        result = run_benchmark(
            args.executable, args.t_end, input_file, args.dt,
            block_size=256, num_blocks=0, retries=args.retries
        )
        
        if result:
            results.append({
                "experiment": "particles",
                "particles": result["particles"],
                "block_size": 256,
                "num_blocks": result["num_blocks"],
                "threads": result["threads"],
                "total_steps": result["total_steps"],
                "time": result["time"]
            })
            print(f"время = {result['time']:.4f} с")
        else:
            print("ОШИБКА")
    
    print("\n=== Эксперимент 2: Зависимость от block_size (N=5000) ===")
    n = 5000
    input_file = f"test_input_{n}.txt"
    
    for block_size in block_sizes:
        print(f"  block_size={block_size}...", end=" ", flush=True)
        
        result = run_benchmark(
            args.executable, args.t_end, input_file, args.dt,
            block_size=block_size, num_blocks=0, retries=args.retries
        )
        
        if result:
            results.append({
                "experiment": "block_size",
                "particles": result["particles"],
                "block_size": block_size,
                "num_blocks": result["num_blocks"],
                "threads": result["threads"],
                "total_steps": result["total_steps"],
                "time": result["time"]
            })
            print(f"время = {result['time']:.4f} с")
        else:
            print("ОШИБКА")
    
    print("\n=== Эксперимент 3: Зависимость от num_blocks (N=5000) ===")
    
    for num_blocks in num_blocks_list:
        print(f"  num_blocks={num_blocks}...", end=" ", flush=True)
        
        result = run_benchmark(
            args.executable, args.t_end, input_file, args.dt,
            block_size=256, num_blocks=num_blocks, retries=args.retries
        )
        
        if result:
            results.append({
                "experiment": "num_blocks",
                "particles": result["particles"],
                "block_size": 256,
                "num_blocks": num_blocks,
                "threads": result["threads"],
                "total_steps": result["total_steps"],
                "time": result["time"]
            })
            print(f"время = {result['time']:.4f} с")
        else:
            print("ОШИБКА")
    
    df = pd.DataFrame(results)
    df.to_csv(args.output, index=False)
    print(f"\Результаты сохранены в {args.output}")
    print(df.to_string())
    
    draw_graphs(args.output)


def main():
    args = parse_args()
    cuda_task(args)


if __name__ == "__main__":
    main()
