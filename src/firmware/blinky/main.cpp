#ifdef ARDUINO
#include <Arduino.h>
#else
#include <stdio.h>
#endif
#include "src/libs/gpio/ArduinoGpio.h"
#include "src/libs/gpio/AvrGpio.h"
#include "src/libs/tasks/Tasks.h"

#ifdef ARDUINO
#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif
#define HAVE_LED 1
using Led = clacker::gpio::arduino::OutputPin<PIN_LED>;
#elif defined(__AVR__)
using Led = clacker::gpio::avr::OutputPin<clacker::gpio::avr::PortC, 7>;
#define HAVE_LED 1
#endif

clacker::Task<> blinker([] {
  while (true) {
#if HAVE_LED
    Led::toggle();
#else
    printf("toggle\n");
#endif
    clacker::delayMilliseconds(1000);
  }
});

void launchTasks(void) {
#if HAVE_LED
  Led::setup();
  Led::set();
#endif
  blinker.start();
}
