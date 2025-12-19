/* my_rwlock.h - Собственная реализация read-write lock */
#ifndef _MY_RWLOCK_H_
#define _MY_RWLOCK_H_

#include <pthread.h>

typedef struct {
   pthread_mutex_t mutex;              /* Мьютекс для защиты структуры */
   pthread_cond_t readers_cond;        /* Условная переменная для читателей */
   pthread_cond_t writers_cond;        /* Условная переменная для писателей */
   int active_readers;                 /* Количество активных читателей */
   int waiting_readers;                /* Количество ожидающих читателей */
   int waiting_writers;                /* Количество ожидающих писателей */
   int writer_active;                  /* Флаг активного писателя (0 или 1) */
} my_rwlock_t;

int my_rwlock_init(my_rwlock_t* rwlock);
int my_rwlock_destroy(my_rwlock_t* rwlock);
int my_rwlock_rdlock(my_rwlock_t* rwlock);
int my_rwlock_wrlock(my_rwlock_t* rwlock);
int my_rwlock_unlock(my_rwlock_t* rwlock);

#endif

