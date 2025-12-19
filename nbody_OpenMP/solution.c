#include "timer.h"

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <omp.h>

#define G 6.67430e-11
#define EPSILON 1e-9

typedef struct {
    double x, y, z; 
    double vx, vy, vz; 
    double mass; 
} Particle;

void compute_forces(Particle *particles, double *Fx, double *Fy, double *Fz, int n) {
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; i++) {
        double fx = 0.0;
        double fy = 0.0;
        double fz = 0.0;
        
        double xi = particles[i].x;
        double yi = particles[i].y;
        double zi = particles[i].z;
        double mi = particles[i].mass;
        
        for (int j = 0; j < n; j++) {
            if (i == j) continue;
            
            double dx = particles[j].x - xi;
            double dy = particles[j].y - yi;
            double dz = particles[j].z - zi;
            
            double dist_sq = dx*dx + dy*dy + dz*dz + EPSILON;
            double dist = sqrt(dist_sq);
            double dist_cubed = dist_sq * dist;
            
            double factor = G * mi * particles[j].mass / dist_cubed;
            
            fx += factor * dx;
            fy += factor * dy;
            fz += factor * dz;
        }
        
        Fx[i] = fx;
        Fy[i] = fy;
        Fz[i] = fz;
    }
}

void integrate_euler(Particle *particles, double *Fx, double *Fy, double *Fz, int n, double dt) {
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; i++) {
        double mass = particles[i].mass;
        
        particles[i].vx += (Fx[i] / mass) * dt;
        particles[i].vy += (Fy[i] / mass) * dt;
        particles[i].vz += (Fz[i] / mass) * dt;
        
        particles[i].x += particles[i].vx * dt;
        particles[i].y += particles[i].vy * dt;
        particles[i].z += particles[i].vz * dt;
    }
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <t_end> <input_file> [output_file] [dt] [num_threads]\n", argv[0]);
        return 1;
    }
    
    double t_end = atof(argv[1]);
    const char *input_file = argv[2];
    const char *output_file = (argc > 3) ? argv[3] : "output.csv";
    double dt = (argc > 4) ? atof(argv[4]) : 0.001;
    int num_threads = (argc > 5) ? atoi(argv[5]) : omp_get_max_threads();
    
    omp_set_num_threads(num_threads);
    
    FILE *fp = fopen(input_file, "r");
    int n;
    fscanf(fp, "%d", &n);
    
    Particle *particles = (Particle *)malloc(n * sizeof(Particle));

    for (int i = 0; i < n; i++) {
        double mass, x, y, z, vx, vy, vz;
        fscanf(fp, "%lf %lf %lf %lf %lf %lf %lf", &mass, &x, &y, &z, &vx, &vy, &vz);
        particles[i].mass = mass;
        particles[i].x = x;
        particles[i].y = y;
        particles[i].z = z;
        particles[i].vx = vx;
        particles[i].vy = vy;
        particles[i].vz = vz;
    }
    fclose(fp);
    
    double *Fx = (double *)malloc(n * sizeof(double));
    double *Fy = (double *)malloc(n * sizeof(double));
    double *Fz = (double *)malloc(n * sizeof(double));
    
    double t = 0.0;
    int step = 0;
    
    double start_time, end_time;
    GET_TIME(start_time);
    
    while (t <= t_end) {
        compute_forces(particles, Fx, Fy, Fz, n);
        integrate_euler(particles, Fx, Fy, Fz, n, dt);
        
        t += dt;
        step++;
    }
    
    GET_TIME(end_time);
    
    printf("%f,%d,%d,%d\n", end_time - start_time, n, step, num_threads);
    
    FILE *out = fopen(output_file, "w");
    fprintf(out, "%f", t_end);
    for (int i = 0; i < n; i++) {
        fprintf(out, ",%f,%f", particles[i].x, particles[i].y);
    }
    fprintf(out, "\n");
    fclose(out);
    
    free(particles);
    free(Fx);
    free(Fy);
    free(Fz);
    
    return 0;
}
