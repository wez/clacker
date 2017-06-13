#include "FreeRTOS.h"
#if configUSE_TICKLESS_IDLE != 0
void vApplicationSleep(TickType_t xExpectedIdleTime) __attribute__((weak));
void vApplicationSleep(TickType_t xExpectedIdleTime) {}
#endif
