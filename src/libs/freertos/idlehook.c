#include "FreeRTOS.h"
#if configUSE_IDLE_HOOK
void vApplicationIdleHook(void) __attribute__((weak));
void vApplicationIdleHook(void) {}
#endif
