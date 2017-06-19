#ifdef ARDUINO
#include <Arduino.h>
#else
#include <stdio.h>
#endif
#include "src/libs/gpio/ArduinoGpio.h"
#include "src/libs/gpio/AvrGpio.h"
#include "src/libs/strings/FixedString.h"
#include "src/libs/tasks/Tasks.h"

#ifdef ARDUINO
#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif
using Led = clacker::gpio::arduino::OutputPin<PIN_LED>;
#endif

clacker::Task<> blinker([] {
  while (true) {
#ifdef ARDUINO
    Led::toggle();
#else
    printf("toggle\n");
#endif
    clacker::delayMilliseconds(300);
  }
});

void launchTasks(void) {
#ifdef ARDUINO
  Led::setup();
#endif
  blinker.start();
}
