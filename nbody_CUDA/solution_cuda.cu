#include "timer.h"

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <cuda_runtime.h>

#define G 6.67430e-11f
#define EPSILON 1e-9f

typedef struct {
    float x, y, z;
    float vx, vy, vz;
    float mass;
} Particle;

__global__ void compute_forces_kernel(Particle *particles, float *Fx, float *Fy, float *Fz, int n) {
    extern __shared__ Particle shared_particles[];
    
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int tid = threadIdx.x;
    
    float fx = 0.0f;
    float fy = 0.0f;
    float fz = 0.0f;
    
    float xi, yi, zi, mi;
    if (i < n) {
        xi = particles[i].x;
        yi = particles[i].y;
        zi = particles[i].z;
        mi = particles[i].mass;
    }
    
    int numTiles = (n + blockDim.x - 1) / blockDim.x;
    for (int tile = 0; tile < numTiles; tile++) {
        int j = tile * blockDim.x + tid;
        
        if (j < n) {
            shared_particles[tid] = particles[j];
        } else {
            shared_particles[tid].mass = 0.0f;
        }
        __syncthreads();
        
        if (i < n) {
            #pragma unroll 8
            for (int k = 0; k < blockDim.x; k++) {
                int global_j = tile * blockDim.x + k;
                if (global_j >= n || i == global_j) continue;
                
                float dx = shared_particles[k].x - xi;
                float dy = shared_particles[k].y - yi;
                float dz = shared_particles[k].z - zi;
                
                float dist_sq = dx*dx + dy*dy + dz*dz + EPSILON;
                float inv_dist = rsqrtf(dist_sq);
                float inv_dist3 = inv_dist * inv_dist * inv_dist;
                
                float factor = G * mi * shared_particles[k].mass * inv_dist3;
                
                fx += factor * dx;
                fy += factor * dy;
                fz += factor * dz;
            }
        }
        __syncthreads();
    }
    
    if (i < n) {
        Fx[i] = fx;
        Fy[i] = fy;
        Fz[i] = fz;
    }
}

__global__ void integrate_euler_kernel(Particle *particles, float *Fx, float *Fy, float *Fz, int n, float dt) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (i >= n) return;
    
    float mass = particles[i].mass;
    float ax = Fx[i] / mass;
    float ay = Fy[i] / mass;
    float az = Fz[i] / mass;
    
    particles[i].vx += ax * dt;
    particles[i].vy += ay * dt;
    particles[i].vz += az * dt;
    
    particles[i].x += particles[i].vx * dt;
    particles[i].y += particles[i].vy * dt;
    particles[i].z += particles[i].vz * dt;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Not enough arguments: %s <t_end> <input_file> [output_file] [dt] [block_size] [num_blocks]\n", argv[0]);
        return 1;
    }
    
    float t_end = atof(argv[1]);
    const char *input_file = argv[2];
    const char *output_file = (argc > 3) ? argv[3] : "output.csv";
    float dt = (argc > 4) ? atof(argv[4]) : 0.001f;
    int block_size = (argc > 5) ? atoi(argv[5]) : 256;
    int num_blocks_param = (argc > 6) ? atoi(argv[6]) : 0;
    
    FILE *fp = fopen(input_file, "r");
    int n;
    fscanf(fp, "%d", &n);
    
    Particle *h_particles = (Particle *)malloc(n * sizeof(Particle));

    // Читаем данные частиц: масса x y z vx vy vz
    for (int i = 0; i < n; i++) {
        double mass, x, y, z, vx, vy, vz;
        fscanf(fp, "%lf %lf %lf %lf %lf %lf %lf", &mass, &x, &y, &z, &vx, &vy, &vz);
        h_particles[i].mass = (float)mass;
        h_particles[i].x = (float)x;
        h_particles[i].y = (float)y;
        h_particles[i].z = (float)z;
        h_particles[i].vx = (float)vx;
        h_particles[i].vy = (float)vy;
        h_particles[i].vz = (float)vz;
    }
    fclose(fp);
    
    // Выделяем память на GPU
    Particle *d_particles;
    float *d_Fx, *d_Fy, *d_Fz;
    
    cudaMalloc(&d_particles, n * sizeof(Particle));
    cudaMalloc(&d_Fx, n * sizeof(float));
    cudaMalloc(&d_Fy, n * sizeof(float));
    cudaMalloc(&d_Fz, n * sizeof(float));
    
    // Копируем начальные данные на GPU
    cudaMemcpy(d_particles, h_particles, n * sizeof(Particle), cudaMemcpyHostToDevice);
    
    // Конфигурация запуска ядер
    int numBlocks;
    if (num_blocks_param > 0) {
        numBlocks = num_blocks_param;
    } else {
        numBlocks = (n + block_size - 1) / block_size;
    }
    size_t sharedMemSize = block_size * sizeof(Particle);
    int total_threads = numBlocks * block_size;
    
    float t = 0.0f;
    int step = 0;
    
    // Замер времени с использованием timer.h
    double start_time, end_time;
    GET_TIME(start_time);
    
    // Основной цикл симуляции
    while (t <= t_end) {
        // Вычисляем силы на GPU
        compute_forces_kernel<<<numBlocks, block_size, sharedMemSize>>>(d_particles, d_Fx, d_Fy, d_Fz, n);
        
        // Интегрируем методом Эйлера на GPU
        integrate_euler_kernel<<<numBlocks, block_size>>>(d_particles, d_Fx, d_Fy, d_Fz, n, dt);
        
        t += dt;
        step++;
    }
    
    cudaDeviceSynchronize();
    GET_TIME(end_time);
    
    // Вывод: время, частицы, total_steps, num_blocks, threads
    printf("%f,%d,%d,%d,%d\n", end_time - start_time, n, step, numBlocks, total_threads);
    
    // Копируем финальные данные только один раз в конце
    cudaMemcpy(h_particles, d_particles, n * sizeof(Particle), cudaMemcpyDeviceToHost);
    
    // Записываем только финальное состояние (формат: t, x1, y1, z1, x2, y2, z2, ...)
    FILE *out = fopen(output_file, "w");
    fprintf(out, "%f", t_end);
    for (int i = 0; i < n; i++) {
        fprintf(out, ",%f,%f,%f", h_particles[i].x, h_particles[i].y, h_particles[i].z);
    }
    fprintf(out, "\n");
    fclose(out);

    cudaFree(d_particles);
    cudaFree(d_Fx);
    cudaFree(d_Fy);
    cudaFree(d_Fz);
    free(h_particles);
    
    return 0;
}
