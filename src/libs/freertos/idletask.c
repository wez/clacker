#include "FreeRTOS.h"
#ifdef configSUPPORT_STATIC_ALLOCATION

#ifdef configIDLE_TASK_STACK_SIZE
#define IDLE_STACK_SIZE configIDLE_TASK_STACK_SIZE
#else
#define IDLE_STACK_SIZE configMINIMAL_STACK_SIZE
#endif

static StackType_t idle_stack[IDLE_STACK_SIZE];
static StaticTask_t idle_task;

void vApplicationGetIdleTaskMemory(
    StaticTask_t** task,
    StackType_t** stack,
    uint32_t* stackSize) {
  *task = &idle_task;
  *stack = idle_stack;
  *stackSize = IDLE_STACK_SIZE;
}
#endif
