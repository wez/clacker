// This file was influenced by the equivalent in the Arduino_FreeRTOS_Library
// https://github.com/feilipu/Arduino_FreeRTOS_Library
#pragma once
#include <avr/wdt.h>
#define portCHAR char
#define portFLOAT float
#define portDOUBLE double
#define portLONG long
#define portSHORT int
#define portSTACK_TYPE uint8_t
#define portBASE_TYPE uint8_t

// 15ms time slicing
#define portUSE_WDTO WDTO_15MS
#define configTICK_RATE_HZ 66

/* Timing for the scheduler.
 * Watchdog Timer is 128kHz nominal,
 * but 120 kHz at 5V DC and 25 degrees is actually more accurate,
 * from data sheet.
 */
#define portTICK_PERIOD_MS ((TickType_t)16)

typedef portSTACK_TYPE StackType_t;
typedef signed char BaseType_t;
typedef unsigned char UBaseType_t;

#if configUSE_16_BIT_TICKS == 1
typedef uint16_t TickType_t;
#define portMAX_DELAY (TickType_t)0xffffU
#else
typedef uint32_t TickType_t;
#define portMAX_DELAY (TickType_t)0xffffffffUL
#endif

#define portENTER_CRITICAL()     \
  __asm__ __volatile__(          \
      "in __tmp_reg__, __SREG__" \
      "\n\t"                     \
      "cli"                      \
      "\n\t"                     \
      "push __tmp_reg__"         \
      "\n\t" ::                  \
          : "memory")

#define portEXIT_CRITICAL()       \
  __asm__ __volatile__(           \
      "pop __tmp_reg__"           \
      "\n\t"                      \
      "out __SREG__, __tmp_reg__" \
      "\n\t" ::                   \
          : "memory")

#define portDISABLE_INTERRUPTS() __asm__ __volatile__("cli" ::: "memory")
#define portENABLE_INTERRUPTS() __asm__ __volatile__("sei" ::: "memory")

#define portSTACK_GROWTH (-1)
#define portBYTE_ALIGNMENT 1
#define portNOP() __asm__ __volatile__("nop");

#define portSUPPRESS_TICKS_AND_SLEEP(duration) vApplicationSleep(duration)

#ifdef __cplusplus
extern "C" {
#endif
extern void vPortYield(void) __attribute__((naked));
extern void vApplicationSleep(TickType_t xExpectedIdleTime)
    __attribute__((weak));
#ifdef __cplusplus
}
#endif

#define portYIELD() vPortYield()

#if defined(__AVR_ATmega2560__) || defined(__AVR_ATmega2561__)
/* Task function macros as described on the FreeRTOS.org WEB site. */
// This changed to add .lowtext tag for the linker for ATmega2560 and
// ATmega2561. To make sure they are loaded in low memory.
#define portTASK_FUNCTION_PROTO(vFunction, pvParameters) \
  void vFunction(void* pvParameters) __attribute__((section(".lowtext")))
#else
#define portTASK_FUNCTION_PROTO(vFunction, pvParameters) \
  void vFunction(void* pvParameters)
#endif

#define portTASK_FUNCTION(vFunction, pvParameters) \
  void vFunction(void* pvParameters)
