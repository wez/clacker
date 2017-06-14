#pragma once
#ifdef __AVR__
#include <avr/io.h>
#define configMINIMAL_STACK_SIZE 85U
#define portPOINTER_SIZE_TYPE uint16_t
#define configTICK_RATE_HZ 66
#define configUSE_16_BIT_TICKS 1
#elif defined(__MKL26Z64__) || defined(ARDUINO_SAMD_FEATHER_M0)
#define configMINIMAL_STACK_SIZE 100U
#define portPOINTER_SIZE_TYPE uint32_t
#define configTICK_RATE_HZ 1000
#define configUSE_16_BIT_TICKS 0
#endif

#define configUSE_PREEMPTION 1
#define configUSE_IDLE_HOOK 0
#define configUSE_TICK_HOOK 0
#define configCPU_CLOCK_HZ F_CPU
#define configMAX_PRIORITIES 4
#define configMAX_TASK_NAME_LEN 1
#define configUSE_TRACE_FACILITY 0
#define configIDLE_SHOULD_YIELD 1
#define configUSE_TICKLESS_IDLE 1
#define configUSE_MUTEXES 1
#define configUSE_RECURSIVE_MUTEXES 1
#define configUSE_COUNTING_SEMAPHORES 1
#define configUSE_QUEUE_SETS 0
#define configQUEUE_REGISTRY_SIZE 0
#define configUSE_TIME_SLICING 1
#define configCHECK_FOR_STACK_OVERFLOW 1
#define configUSE_MALLOC_FAILED_HOOK 0

#define configSUPPORT_STATIC_ALLOCATION 1
#define configSUPPORT_DYNAMIC_ALLOCATION 0

#define configUSE_TIMERS 0
#define configTIMER_TASK_PRIORITY 3U
#define configTIMER_QUEUE_LENGTH 10U
#define configTIMER_TASK_STACK_DEPTH configMINIMAL_STACK_SIZE

#define configUSE_CO_ROUTINES 0

#define INCLUDE_vTaskPrioritySet 0
#define INCLUDE_uxTaskPriorityGet 0
#define INCLUDE_vTaskDelete 0
#define INCLUDE_vTaskCleanUpResources 0
#define INCLUDE_vTaskSuspend 1
#define INCLUDE_vResumeFromISR 1
#define INCLUDE_vTaskDelayUntil 1
#define INCLUDE_vTaskDelay 1
#define INCLUDE_xTaskGetSchedulerState 0
#define INCLUDE_xTaskGetIdleTaskHandle 0
#define INCLUDE_xTaskGetCurrentTaskHandle 0
#define INCLUDE_uxTaskGetStackHighWaterMark 1
