#ifndef shm_helper_h
#define shm_helper_h

#include <sys/stat.h>

int shm_open_fixed(const char *name, int oflag, int mode);
int shm_unlink_fixed(const char *name);
int fstat_fixed(int fd, struct stat *buf);

#endif
