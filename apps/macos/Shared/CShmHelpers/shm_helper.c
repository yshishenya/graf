#include "shm_helper.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>

int shm_open_fixed(const char *name, int oflag, int mode) {
    return shm_open(name, oflag, (mode_t)mode);
}

int shm_unlink_fixed(const char *name) {
    return shm_unlink(name);
}

int fstat_fixed(int fd, struct stat *buf) {
    return fstat(fd, buf);
}
