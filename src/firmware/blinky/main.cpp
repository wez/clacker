#include <Arduino.h>
#include "src/libs/tasks/Tasks.h"

#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif

clacker::Task<> blinker([] {
  while (true) {
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));
    vTaskDelay(300 / portTICK_PERIOD_MS);
  }
});

void setup(void) {
  pinMode(PIN_LED, OUTPUT);
  blinker.start();
  vTaskStartScheduler();
}

void loop(void) {}
