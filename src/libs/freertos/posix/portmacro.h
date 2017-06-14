/*
  FreeRTOS.org V5.2.0 - Copyright (C) 2003-2009 Richard Barry.

  FreeRTOS.org is free software; you can redistribute it and/or modify it
  under the terms of the GNU General Public License (version 2) as published
  by the Free Software Foundation and modified by the FreeRTOS exception.

  FreeRTOS.org is distributed in the hope that it will be useful, but WITHOUT
  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
  more details.

  You should have received a copy of the GNU General Public License along
  with FreeRTOS.org; if not, write to the Free Software Foundation, Inc.,
  59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

  A special exception to the GPL is included to allow you to distribute a
  combined work that includes FreeRTOS.org without being obliged to provide
  the source code for any proprietary components.  See the licensing section
  of http://www.FreeRTOS.org for full details.
*/

#pragma once
#include <inttypes.h>
#ifdef __cplusplus
extern "C" {
#endif

#define portCHAR char
#define portFLOAT float
#define portDOUBLE double
#define portLONG long
#define portSHORT short
#define portSTACK_TYPE intptr_t
#define portBASE_TYPE intptr_t

typedef portSTACK_TYPE StackType_t;
typedef intptr_t BaseType_t;
typedef uintptr_t UBaseType_t;

#if (configUSE_16_BIT_TICKS == 1)
typedef unsigned portSHORT TickType_t;
#define portMAX_DELAY (portTickType)0xffff
#else
typedef unsigned portLONG TickType_t;
#define portMAX_DELAY (portTickType)0xffffffff
#endif

#define portSTACK_GROWTH (-1)
#define portTICK_RATE_MICROSECONDS ((portTickType)1000000 / configTICK_RATE_HZ)
#define portTICK_PERIOD_MS ((TickType_t)1000 / configTICK_RATE_HZ)

#ifdef __x86_64__
#define portBYTE_ALIGNMENT 8
#else
#define portBYTE_ALIGNMENT 4
#endif

#define portREMOVE_STATIC_QUALIFIER

extern void vPortYieldFromISR(void);
extern void vPortYield(void);

#define portYIELD() vPortYield()

#define portEND_SWITCHING_ISR(xSwitchRequired) \
  if (xSwitchRequired)                         \
  vPortYieldFromISR()

extern void vPortDisableInterrupts(void);
extern void vPortEnableInterrupts(void);
#define portSET_INTERRUPT_MASK() (vPortDisableInterrupts())
#define portCLEAR_INTERRUPT_MASK() (vPortEnableInterrupts())

extern portBASE_TYPE xPortSetInterruptMask(void);
extern void vPortClearInterruptMask(portBASE_TYPE xMask);

#define portSET_INTERRUPT_MASK_FROM_ISR() xPortSetInterruptMask()
#define portCLEAR_INTERRUPT_MASK_FROM_ISR(x) vPortClearInterruptMask(x)

extern void vPortEnterCritical(void);
extern void vPortExitCritical(void);

#define portDISABLE_INTERRUPTS() portSET_INTERRUPT_MASK()
#define portENABLE_INTERRUPTS() portCLEAR_INTERRUPT_MASK()
#define portENTER_CRITICAL() vPortEnterCritical()
#define portEXIT_CRITICAL() vPortExitCritical()

#define portTASK_FUNCTION_PROTO(vFunction, pvParameters) \
  void vFunction(void* pvParameters)
#define portTASK_FUNCTION(vFunction, pvParameters) \
  void vFunction(void* pvParameters)

#define portNOP()

#define portOUTPUT_BYTE(a, b)

extern void vPortForciblyEndThread(void* pxTaskToDelete);
#define traceTASK_DELETE(pxTaskToDelete) vPortForciblyEndThread(pxTaskToDelete)

extern void vPortAddTaskHandle(void* pxTaskHandle);
#define traceTASK_CREATE(pxNewTCB) vPortAddTaskHandle(pxNewTCB)

/* Posix Signal definitions that can be changed or read as appropriate. */
#define SIG_SUSPEND SIGUSR1
#define SIG_RESUME SIGUSR2

/* Enable the following hash defines to make use of the real-time tick where
 * time progresses at real-time. */
#define SIG_TICK SIGALRM
#define TIMER_TYPE ITIMER_REAL
/* Enable the following hash defines to make use of the process tick where time
progresses only when the process is executing.
#define SIG_TICK					SIGVTALRM
#define TIMER_TYPE					ITIMER_VIRTUAL
*/
/* Enable the following hash defines to make use of the profile tick where time
progresses when the process or system calls are executing.
#define SIG_TICK					SIGPROF
#define TIMER_TYPE					ITIMER_PROF */

/* Make use of times(man 2) to gather run-time statistics on the tasks. */
extern void vPortFindTicksPerSecond(void);
#define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS()                          \
  vPortFindTicksPerSecond() /* Nothing to do because the timer is already \
                               present. */
extern unsigned long ulPortGetTimerValue(void);
#define portGET_RUN_TIME_COUNTER_VALUE() \
  ulPortGetTimerValue() /* Query the System time stats for this process. */

#ifdef __cplusplus
}
#endif
