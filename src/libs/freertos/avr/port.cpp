// This file was influenced by the equivalent in the Arduino_FreeRTOS_Library
// https://github.com/feilipu/Arduino_FreeRTOS_Library
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <stdlib.h>

#include "FreeRTOS.h"
#include "task.h"

/* Start tasks with interrupts enabled. */
#define portFLAGS_INT_ENABLED ((StackType_t)0x80)

#if portTICK_USES_WDT
#define portSCHEDULER_ISR WDT_vect
#else
#include "src/libs/timer/Timer.h"
#define portSCHEDULER_ISR TIMER1_COMPA_vect
#endif

/* We require the address of the pxCurrentTCB variable, but don't want to know
 * any details of its type. */
typedef void TCB_t;
extern volatile TCB_t* volatile pxCurrentTCB;

/*
 * Perform hardware setup to enable ticks from Watchdog Timer.
 */
static void prvSetupTimerInterrupt(void);

/*
 * Macro to save all the general purpose registers, the save the stack pointer
 * into the TCB.
 *
 * The first thing we do is save the flags then disable interrupts.  This is to
 * guard our stack against having a context switch interrupt after we have
 * already pushed the registers onto the stack - causing the 32 registers to be
 * on the stack twice.
 *
 * r1 is set to zero as the compiler expects it to be thus, however some
 * of the math routines make use of R1.
 *
 * The interrupts will have been disabled during the call to portSAVE_CONTEXT()
 * so we need not worry about reading/writing to the stack pointer.
 */
#if defined(__AVR_ATmega2560__) || defined(__AVR_ATmega2561__)
/* 3-Byte PC Save */
#define portSAVE_CONTEXT()                                  \
  __asm__ __volatile__(                                     \
      "push   r0                                      \n\t" \
      "in		r0, __SREG__                    \n\t"            \
      "cli                                            \n\t" \
      "push	r0                                      \n\t"   \
      "in     r0, 0x3b                                \n\t" \
      "push   r0                                      \n\t" \
      "in     r0, 0x3c                                \n\t" \
      "push   r0                                      \n\t" \
      "push   r1                                      \n\t" \
      "clr    r1                                      \n\t" \
      "push   r2                                      \n\t" \
      "push   r3                                      \n\t" \
      "push   r4                                      \n\t" \
      "push   r5                                      \n\t" \
      "push   r6                                      \n\t" \
      "push   r7                                      \n\t" \
      "push   r8                                      \n\t" \
      "push   r9                                      \n\t" \
      "push   r10                                     \n\t" \
      "push   r11                                     \n\t" \
      "push   r12                                     \n\t" \
      "push   r13                                     \n\t" \
      "push   r14                                     \n\t" \
      "push   r15                                     \n\t" \
      "push   r16                                     \n\t" \
      "push   r17                                     \n\t" \
      "push   r18                                     \n\t" \
      "push   r19                                     \n\t" \
      "push   r20                                     \n\t" \
      "push   r21                                     \n\t" \
      "push   r22                                     \n\t" \
      "push   r23                                     \n\t" \
      "push   r24                                     \n\t" \
      "push   r25                                     \n\t" \
      "push   r26                                     \n\t" \
      "push   r27                                     \n\t" \
      "push   r28                                     \n\t" \
      "push   r29                                     \n\t" \
      "push   r30                                     \n\t" \
      "push   r31                                     \n\t" \
      "lds    r26, pxCurrentTCB                       \n\t" \
      "lds    r27, pxCurrentTCB + 1                   \n\t" \
      "in     r0, 0x3d                                \n\t" \
      "st     x+, r0                                  \n\t" \
      "in     r0, 0x3e                                \n\t" \
      "st     x+, r0                                  \n\t");
#else
/* 2-Byte PC Save */
#define portSAVE_CONTEXT()                                  \
  __asm__ __volatile__(                                     \
      "push   r0                                      \n\t" \
      "in     r0, __SREG__                            \n\t" \
      "cli                                            \n\t" \
      "push   r0                                      \n\t" \
      "push   r1                                      \n\t" \
      "clr    r1                                      \n\t" \
      "push   r2                                      \n\t" \
      "push   r3                                      \n\t" \
      "push   r4                                      \n\t" \
      "push   r5                                      \n\t" \
      "push   r6                                      \n\t" \
      "push   r7                                      \n\t" \
      "push   r8                                      \n\t" \
      "push   r9                                      \n\t" \
      "push   r10                                     \n\t" \
      "push   r11                                     \n\t" \
      "push   r12                                     \n\t" \
      "push   r13                                     \n\t" \
      "push   r14                                     \n\t" \
      "push   r15                                     \n\t" \
      "push   r16                                     \n\t" \
      "push   r17                                     \n\t" \
      "push   r18                                     \n\t" \
      "push   r19                                     \n\t" \
      "push   r20                                     \n\t" \
      "push   r21                                     \n\t" \
      "push   r22                                     \n\t" \
      "push   r23                                     \n\t" \
      "push   r24                                     \n\t" \
      "push   r25                                     \n\t" \
      "push   r26                                     \n\t" \
      "push   r27                                     \n\t" \
      "push   r28                                     \n\t" \
      "push   r29                                     \n\t" \
      "push   r30                                     \n\t" \
      "push   r31                                     \n\t" \
      "lds    r26, pxCurrentTCB                       \n\t" \
      "lds    r27, pxCurrentTCB + 1                   \n\t" \
      "in     r0, 0x3d                                \n\t" \
      "st     x+, r0                                  \n\t" \
      "in     r0, 0x3e                                \n\t" \
      "st     x+, r0                                  \n\t");
#endif

/*
 * Opposite to portSAVE_CONTEXT().  Interrupts will have been disabled during
 * the context save so we can write to the stack pointer.
 */
#if defined(__AVR_ATmega2560__) || defined(__AVR_ATmega2561__)
/* 3-Byte PC Restore */
#define portRESTORE_CONTEXT()                               \
  __asm__ __volatile__(                                     \
      "lds    r26, pxCurrentTCB                       \n\t" \
      "lds    r27, pxCurrentTCB + 1                   \n\t" \
      "ld     r28, x+                                 \n\t" \
      "out    __SP_L__, r28                           \n\t" \
      "ld     r29, x+                                 \n\t" \
      "out    __SP_H__, r29                           \n\t" \
      "pop    r31                                     \n\t" \
      "pop    r30                                     \n\t" \
      "pop    r29                                     \n\t" \
      "pop    r28                                     \n\t" \
      "pop    r27                                     \n\t" \
      "pop    r26                                     \n\t" \
      "pop    r25                                     \n\t" \
      "pop    r24                                     \n\t" \
      "pop    r23                                     \n\t" \
      "pop    r22                                     \n\t" \
      "pop    r21                                     \n\t" \
      "pop    r20                                     \n\t" \
      "pop    r19                                     \n\t" \
      "pop    r18                                     \n\t" \
      "pop    r17                                     \n\t" \
      "pop    r16                                     \n\t" \
      "pop    r15                                     \n\t" \
      "pop    r14                                     \n\t" \
      "pop    r13                                     \n\t" \
      "pop    r12                                     \n\t" \
      "pop    r11                                     \n\t" \
      "pop    r10                                     \n\t" \
      "pop    r9                                      \n\t" \
      "pop    r8                                      \n\t" \
      "pop    r7                                      \n\t" \
      "pop    r6                                      \n\t" \
      "pop    r5                                      \n\t" \
      "pop    r4                                      \n\t" \
      "pop    r3                                      \n\t" \
      "pop    r2                                      \n\t" \
      "pop    r1                                      \n\t" \
      "pop    r0                                      \n\t" \
      "out    0x3c, r0                                \n\t" \
      "pop    r0                                      \n\t" \
      "out    0x3b, r0                                \n\t" \
      "pop    r0                                      \n\t" \
      "out    __SREG__, r0                            \n\t" \
      "pop    r0                                      \n\t");
#else
/* 2-Byte PC Restore */
#define portRESTORE_CONTEXT()                               \
  __asm__ __volatile__(                                     \
      "lds    r26, pxCurrentTCB                       \n\t" \
      "lds    r27, pxCurrentTCB + 1                   \n\t" \
      "ld     r28, x+                                 \n\t" \
      "out    __SP_L__, r28                           \n\t" \
      "ld     r29, x+                                 \n\t" \
      "out    __SP_H__, r29                           \n\t" \
      "pop    r31                                     \n\t" \
      "pop    r30                                     \n\t" \
      "pop    r29                                     \n\t" \
      "pop    r28                                     \n\t" \
      "pop    r27                                     \n\t" \
      "pop    r26                                     \n\t" \
      "pop    r25                                     \n\t" \
      "pop    r24                                     \n\t" \
      "pop    r23                                     \n\t" \
      "pop    r22                                     \n\t" \
      "pop    r21                                     \n\t" \
      "pop    r20                                     \n\t" \
      "pop    r19                                     \n\t" \
      "pop    r18                                     \n\t" \
      "pop    r17                                     \n\t" \
      "pop    r16                                     \n\t" \
      "pop    r15                                     \n\t" \
      "pop    r14                                     \n\t" \
      "pop    r13                                     \n\t" \
      "pop    r12                                     \n\t" \
      "pop    r11                                     \n\t" \
      "pop    r10                                     \n\t" \
      "pop    r9                                      \n\t" \
      "pop    r8                                      \n\t" \
      "pop    r7                                      \n\t" \
      "pop    r6                                      \n\t" \
      "pop    r5                                      \n\t" \
      "pop    r4                                      \n\t" \
      "pop    r3                                      \n\t" \
      "pop    r2                                      \n\t" \
      "pop    r1                                      \n\t" \
      "pop    r0                                      \n\t" \
      "out    __SREG__, r0                            \n\t" \
      "pop    r0                                      \n\t");
#endif

/*
 * See header file for description.
 */
StackType_t* pxPortInitialiseStack(
    StackType_t* pxTopOfStack,
    TaskFunction_t pxCode,
    void* pvParameters) {
  uint16_t usAddress;

  /* Place a few bytes of known values on the bottom of the stack.
  This is just useful for debugging. */

  *pxTopOfStack = 0x11;
  pxTopOfStack--;
  *pxTopOfStack = 0x22;
  pxTopOfStack--;
  *pxTopOfStack = 0x33;
  pxTopOfStack--;

/* Simulate how the stack would look after a call to vPortYield() generated
 * by the compiler. */

/* The start of the task code will be popped off the stack last, so place it
 * on first. */

#if defined(__AVR_ATmega2560__) || defined(__AVR_ATmega2561__)
  /* The AVR ATmega2560/ATmega2561 have 256KBytes of program memory and a 17-bit
   * program counter.  When a code address is stored on the stack, it takes 3
   * bytes
   * instead of 2 for the other ATmega* chips.
   *
   * Store 0 as the top byte since we force all task routines to the bottom 128K
   * of flash. We do this by using the .lowtext label in the linker script.
   *
   * In order to do this properly, we would need to get a full 3-byte pointer to
   * pxCode.  That requires a change to GCC.  Not likely to happen any time
   * soon.
   */
  usAddress = (uint16_t)pxCode;
  *pxTopOfStack = (StackType_t)(usAddress & (uint16_t)0x00ff);
  pxTopOfStack--;

  usAddress >>= 8;
  *pxTopOfStack = (StackType_t)(usAddress & (uint16_t)0x00ff);
  pxTopOfStack--;

  *pxTopOfStack = 0;
  pxTopOfStack--;
#else
  usAddress = (uint16_t)pxCode;
  *pxTopOfStack = (StackType_t)(usAddress & (uint16_t)0x00ff);
  pxTopOfStack--;

  usAddress >>= 8;
  *pxTopOfStack = (StackType_t)(usAddress & (uint16_t)0x00ff);
  pxTopOfStack--;
#endif

  /* Next simulate the stack as if after a call to portSAVE_CONTEXT().
  portSAVE_CONTEXT places the flags on the stack immediately after r0
  to ensure the interrupts get disabled as soon as possible, and so ensuring
  the stack use is minimal should a context switch interrupt occur. */
  *pxTopOfStack = (StackType_t)0x00; /* R0 */
  pxTopOfStack--;
  *pxTopOfStack = portFLAGS_INT_ENABLED;
  pxTopOfStack--;

#if defined(__AVR_ATmega2560__) || defined(__AVR_ATmega2561__)

  /* If we have an ATmega256x, we are also saving the RAMPZ and EIND registers.
   * We should default those to 0.
   */
  *pxTopOfStack = (StackType_t)0x00; /* EIND */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x00; /* RAMPZ */
  pxTopOfStack--;

#endif

  /* Now the remaining registers.   The compiler expects R1 to be 0. */
  *pxTopOfStack = (StackType_t)0x00; /* R1 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x02; /* R2 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x03; /* R3 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x04; /* R4 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x05; /* R5 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x06; /* R6 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x07; /* R7 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x08; /* R8 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x09; /* R9 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x10; /* R10 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x11; /* R11 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x12; /* R12 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x13; /* R13 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x14; /* R14 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x15; /* R15 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x16; /* R16 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x17; /* R17 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x18; /* R18 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x19; /* R19 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x20; /* R20 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x21; /* R21 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x22; /* R22 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x23; /* R23 */
  pxTopOfStack--;

  /* Place the parameter on the stack in the expected location. */
  usAddress = (uint16_t)pvParameters;
  *pxTopOfStack = (StackType_t)(usAddress & (uint16_t)0x00ff);
  pxTopOfStack--;

  usAddress >>= 8;
  *pxTopOfStack = (StackType_t)(usAddress & (uint16_t)0x00ff);
  pxTopOfStack--;

  *pxTopOfStack = (StackType_t)0x26; /* R26 X */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x27; /* R27 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x28; /* R28 Y */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x29; /* R29 */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x30; /* R30 Z */
  pxTopOfStack--;
  *pxTopOfStack = (StackType_t)0x031; /* R31 */
  pxTopOfStack--;

  return pxTopOfStack;
}

BaseType_t xPortStartScheduler(void) {
  /* Setup the relevant timer hardware to generate the tick. */
  prvSetupTimerInterrupt();

  /* Restore the context of the first task that is going to run. */
  portRESTORE_CONTEXT();

  /* Simulate a function call end as generated by the compiler.  We will now
  jump to the start of the task the context of which we have just restored. */
  __asm__ __volatile__("ret");

  /* Should not get here. */
  return pdTRUE;
}

void vPortEndScheduler(void) {
// It is unlikely that the AVR port will get stopped.  If required simply
// disable the tick interrupt here.
#if portTICK_USES_WDT
  wdt_disable(); // disable Watchdog Timer
#endif
}

/*
 * Manual context switch.  The first thing we do is save the registers so we
 * can use a naked attribute.
 */
void vPortYield(void) __attribute__((hot, flatten, naked));
void vPortYield(void) {
  portSAVE_CONTEXT();
  vTaskSwitchContext();
  portRESTORE_CONTEXT();

  __asm__ __volatile__("ret");
}

/*
 * Context switch function used by the tick.  This must be identical to
 * vPortYield() from the call to vTaskSwitchContext() onwards.  The only
 * difference from vPortYield() is the tick count is incremented as the
 * call comes from the tick ISR.
 */
void vPortYieldFromTick(void) __attribute__((hot, flatten, naked));
void vPortYieldFromTick(void) {
  portSAVE_CONTEXT();

  // reset the sleep_mode() faster than sleep_disable();
  _SLEEP_CONTROL_REG = 0;

  if (xTaskIncrementTick() != pdFALSE) {
    vTaskSwitchContext();
  }

  portRESTORE_CONTEXT();

  __asm__ __volatile__("ret");
}

#ifdef WDT_vect
/**
        Enable the watchdog timer, configuring it for expire after
        (value) timeout (which is a combination of the WDP0
        through WDP3 bits).
        This function is derived from <avr/wdt.h> but enables only
        the interrupt bit (WDIE), rather than the reset bit (WDE).
        Can't find it documented but the WDT, once enabled,
        rolls over and fires a new interrupt each time.
        See also the symbolic constants WDTO_15MS et al.
*/
#define wdt_interrupt_enable(value)                                        \
  __asm__ __volatile__(                                                    \
      "in __tmp_reg__,__SREG__"                                            \
      "\n\t"                                                               \
      "cli"                                                                \
      "\n\t"                                                               \
      "wdr"                                                                \
      "\n\t"                                                               \
      "sts %0,%1"                                                          \
      "\n\t"                                                               \
      "out __SREG__,__tmp_reg__"                                           \
      "\n\t"                                                               \
      "sts %0,%2"                                                          \
      "\n\t"                                                               \
      : /* no outputs */                                                   \
      : "M"(_SFR_MEM_ADDR(_WD_CONTROL_REG)),                               \
        "r"(_BV(_WD_CHANGE_BIT) | _BV(WDE)),                               \
        "r"((uint8_t)(                                                     \
            (value & 0x08 ? _WD_PS3_MASK : 0x00) | _BV(WDIF) | _BV(WDIE) | \
            (value & 0x07)))                                               \
      : "r0")
#endif

// initialize watchdog
void prvSetupTimerInterrupt(void) {
#if portTICK_USES_WDT
  // reset watchdog
  wdt_reset();

  // set up WDT Interrupt (rather than the WDT Reset).
  wdt_interrupt_enable(portUSE_WDTO);
#else
  // Use timer instead
  using namespace clacker::avr;
  setupTimer<Timer1>(configTICK_RATE_HZ);
#if 0
 Timer1::setup(
     WaveformGenerationMode::ClearOnTimerMatchOutputCompare,
     ClockSource::Prescale256,
     1170);
#endif
#endif
}

#if configUSE_PREEMPTION == 1

/*
 * Tick ISR for preemptive scheduler.  We can use a naked attribute as
 * the context is saved at the start of vPortYieldFromTick().  The tick
 * count is incremented after the context is saved.
 *
 * use ISR_NOBLOCK where there is an important timer running, that should
 * preempt the scheduler.
 */
ISR(portSCHEDULER_ISR, ISR_NAKED) __attribute__((hot, flatten));
ISR(portSCHEDULER_ISR, ISR_NAKED) {
  vPortYieldFromTick();
  __asm__ __volatile__("reti");
}

#else
/*
 * Tick ISR for the cooperative scheduler.  All this does is increment the
 * tick count.  We don't need to switch context, this can only be done by
 * manual calls to taskYIELD();
 *
 * use ISR_NOBLOCK where there is an important timer running, that should
 * preempt the scheduler.
 */
ISR(portSCHEDULER_ISR) __attribute__((hot, flatten));
ISR(portSCHEDULER_ISR) {
  xTaskIncrementTick();
}

#endif
