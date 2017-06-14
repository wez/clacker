#include <Arduino.h>
#include "src/libs/tasks/Tasks.h"

#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif

clacker::Task<> blinker([] {
  while (true) {
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));
    clacker::delayMilliseconds(300);
  }
});

void launchTasks(void) {
  pinMode(PIN_LED, OUTPUT);
  blinker.start();
}
