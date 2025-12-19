#!/bin/bash

gcc -fopenmp program.c -o program -lm

mkdir -p csv_results

if [ -f performance_results.csv ]; then
    rm performance_results.csv
fi

echo threads,points,time >> performance_results.csv

for points in 10000 100000 1000000 10000000
do
    for threads in 1 2 4 8
    do
        ./program $threads $points >> performance_results.csv
    done
done