#include "my_rwlock.h"
#include <stdlib.h>


int my_rwlock_init(my_rwlock_t* rwlock) {
   int result;
   
   rwlock->active_readers = 0;
   rwlock->waiting_readers = 0;
   rwlock->waiting_writers = 0;
   rwlock->writer_active = 0;
   
   result = pthread_mutex_init(&rwlock->mutex, NULL);
   if (result != 0) return result;
   
   result = pthread_cond_init(&rwlock->readers_cond, NULL);
   if (result != 0) {
      pthread_mutex_destroy(&rwlock->mutex);
      return result;
   }
   
   result = pthread_cond_init(&rwlock->writers_cond, NULL);
   if (result != 0) {
      pthread_mutex_destroy(&rwlock->mutex);
      pthread_cond_destroy(&rwlock->readers_cond);
      return result;
   }
   
   return 0;
}

int my_rwlock_destroy(my_rwlock_t* rwlock) {
   pthread_mutex_destroy(&rwlock->mutex);
   pthread_cond_destroy(&rwlock->readers_cond);
   pthread_cond_destroy(&rwlock->writers_cond);
   return 0;
}


int my_rwlock_rdlock(my_rwlock_t* rwlock) {
   pthread_mutex_lock(&rwlock->mutex);

   rwlock->waiting_readers++;
   while (rwlock->writer_active || rwlock->waiting_writers > 0) {
      pthread_cond_wait(&rwlock->readers_cond, &rwlock->mutex);
   }
   rwlock->waiting_readers--;
   rwlock->active_readers++;
   
   pthread_mutex_unlock(&rwlock->mutex);
   return 0;
}


int my_rwlock_wrlock(my_rwlock_t* rwlock) {
   pthread_mutex_lock(&rwlock->mutex);
   
   rwlock->waiting_writers++;
   while (rwlock->active_readers > 0 || rwlock->writer_active) {
      pthread_cond_wait(&rwlock->writers_cond, &rwlock->mutex);
   }
   rwlock->waiting_writers--;
   
   rwlock->writer_active = 1;
   
   pthread_mutex_unlock(&rwlock->mutex);
   return 0;
}

int my_rwlock_unlock(my_rwlock_t* rwlock) {
   pthread_mutex_lock(&rwlock->mutex);
   
   if (rwlock->writer_active) {
      rwlock->writer_active = 0;
      
      if (rwlock->waiting_writers > 0) {
         pthread_cond_signal(&rwlock->writers_cond);
      } else if (rwlock->waiting_readers > 0) {
         pthread_cond_broadcast(&rwlock->readers_cond);
      }
   } else if (rwlock->active_readers > 0) {
      rwlock->active_readers--;
      
      if (rwlock->active_readers == 0 && rwlock->waiting_writers > 0) {
         pthread_cond_signal(&rwlock->writers_cond);
      }
   }
   
   pthread_mutex_unlock(&rwlock->mutex);
   return 0;
}

