#include "FreeRTOS.h"
#include "task.h"
#if configCHECK_FOR_STACK_OVERFLOW
void vApplicationStackOverflowHook(TaskHandle_t, portCHAR*)
    __attribute__((weak));
void vApplicationStackOverflowHook(TaskHandle_t h, portCHAR* p) {
  while (1) {
    ;
  }
}
#endif
