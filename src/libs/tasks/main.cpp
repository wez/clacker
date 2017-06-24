#include <avr/power.h>
#include "src/libs/tasks/Tasks.h"

// This file serves as the second tier startup code for the projects
// in this repo.  We don't want to replace main() as each arduino
// core has a slightly different initialization sequence.

#ifdef ARDUINO
// For Arduino we have to piggy-back our initialization into the
// setup() function.  Some Arduino cores do some implicit ticking
// of peripherals after calling loop() on each iteration; those
// won't work for us here because there isn't a way to call that
// same code from outside.
// The Adafruit Feather nRF52 board already has freertos integrated,
// so we just need to bridge setup() to launchTasks() on that
// system.
extern "C" void setup(void) {
  launchTasks();
#ifndef ARDUINO_FEATHER52
  vTaskStartScheduler();
#endif
}

extern "C" void loop(void) {}
#else
extern "C" int main(void) {
// The bootloader may have left USB interrupts enabled, but
// the firmware that we're running may not have set up an
// ISR for them, so we must disable them here to avoid
// faulting the MCU after re-flashing.
#ifdef __AVR__
#if defined(UCSRB)
  UCSRB = 0;
#elif defined(UCSR0B)
  UCSR0B = 0;
#endif
#ifdef USBCON
  USBCON = 0;
#endif
#ifdef MCUSR
  MCUSR &= ~(1 << WDRF);
#endif
  wdt_disable();
  /* Disable clock division */
  clock_prescale_set(clock_div_1);
#endif // AVR

  // Call out to the firmware-provided function to set
  // up tasks
  launchTasks();

  // And start up the scheduler
  vTaskStartScheduler();
}
#endif
