#include <stdio.h>
#include <omp.h>
#include <stdlib.h>
#include <time.h>

#define MAX_ITER 1000

#define MIN_X -2.0
#define MAX_X 1.0
#define MIN_Y -1.5
#define MAX_Y 1.5

int is_in_mandelbrot(double c_real, double c_imagine) {
    double z_real = 0.0;
    double z_imagine = 0.0;
    
    for (int i = 0; i < MAX_ITER; i++) {
        double z_real_sq = z_real * z_real;
        double z_imagine_sq = z_imagine * z_imagine;
        
        if (z_real_sq + z_imagine_sq >= 4.0) {
            return 0;
        }
        
        double new_real = z_real_sq - z_imagine_sq + c_real;
        double new_imagine = 2.0 * z_real * z_imagine + c_imagine;
        
        z_real = new_real;
        z_imagine = new_imagine;
    }
    
    return 1;
}

int main(int argc, char** argv) {
    if (argc != 3) {
        fprintf(stderr, "How to launch: %s <nthreads> <npoints>\n", argv[0]);
        return 1;
    }

    int nthreads = atoi(argv[1]);
    int npoints = atoi(argv[2]);

    if (nthreads <= 0 || npoints <= 0) {
        fprintf(stderr, "Error: arguments must be positive\n");
        return 1;
    }

    omp_set_num_threads(nthreads);

    char fname[64];
    sprintf(fname, "csv_results/set_%d_%d.csv", nthreads, npoints);

    FILE* rfile = fopen(fname, "w");
    fprintf(rfile, "x,y\n");
    
    int stop_flag = 0;
    int global_count = 0;

    double start_time = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ omp_get_thread_num());
        
        while (1) {
            if (stop_flag) break;

            double x = (double)rand_r(&seed) / RAND_MAX * (MAX_X - MIN_X) + MIN_X;
            double y = (double)rand_r(&seed) / RAND_MAX * (MAX_Y - MIN_Y) + MIN_Y;

            if (is_in_mandelbrot(x, y)) {
                #pragma omp critical
                {
                    if (global_count < npoints) {
                        fprintf(rfile, "%.6lf,%.6lf\n", x, y);
                        global_count++;
                        if (global_count >= npoints) {
                            stop_flag = 1;
                        }
                    }
                }
            }
        }
    }

    double end_time = omp_get_wtime();
    
    double elapsed_time = end_time - start_time;

    fprintf(stdout, "%d,%d,%lf\n", nthreads, npoints, elapsed_time);

    fclose(rfile);
    return 0;
}