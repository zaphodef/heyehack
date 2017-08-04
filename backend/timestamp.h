#include <stdlib.h>

// define the precision we want, in nanoseconds (ns)
#define PRECISION_NS 100000

// DO NOT change this value
#define PADDING_S 1000000000/PRECISION_NS

u_int32_t get_current_timestamp();
