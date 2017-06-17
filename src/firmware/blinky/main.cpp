#ifdef ARDUINO
#include <Arduino.h>
#else
#include <stdio.h>
#endif
#include "src/libs/strings/FixedString.h"
#include "src/libs/tasks/Tasks.h"

#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif
clacker::Task<> blinker([] {
  while (true) {
#ifdef ARDUINO
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));
#else
    printf("toggle\n");
#endif
    clacker::delayMilliseconds(300);
  }
});

void launchTasks(void) {
#ifdef ARDUINO
  pinMode(PIN_LED, OUTPUT);
#endif
  blinker.start();
}
