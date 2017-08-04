/*
 * HeyeHack
 * Copyright 2017 Pierre-Jean Grenier
 * Licensed under MIT 
 */
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

#include "timestamp.h"

u_int32_t get_current_timestamp() {
    // The mark to set is a u_int32_t, so we use 32 bits to store
    // our timestamp. We want a precision of 0.1 millisecond (ms).
    // This make the timestamp wrap around every (2^32 / 10^4) seconds (s),
    // that is approximately 429,497 seconds, or 119 hours, or almost 5 days.

	// everything is in milliseconds (ms)
    struct timespec tms;
    clock_gettime(CLOCK_MONOTONIC, &tms);
    // tms.tv_nsec is a long, so it is 64-bit-long on 64-bit OS
    //     Valid values are [0, 999,999,999], it is not supposed to
    //     grow bigger
    // tms.tv_sec is a time_t, problem is the type is not garantueed
    //     in the C specification
    //     (see https://stackoverflow.com/questions/471248)
    
    // (tms.tv_nsec/PRECISION_NS) is at wort 14-bit long
    u_int32_t now = (u_int32_t)(tms.tv_nsec/PRECISION_NS) + (u_int32_t)(tms.tv_sec*PADDING_S);
    return now;
}
