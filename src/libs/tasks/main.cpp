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
  // Call out to the firmware-provided function to set
  // up tasks
  launchTasks();

  // And start up the scheduler
  vTaskStartScheduler();
}
#endif
