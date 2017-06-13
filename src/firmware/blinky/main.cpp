#include <Arduino.h>
#include "src/libs/tasks/Tasks.h"

#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif

clacker::Task<> blinker([] {
  while (true) {
    digitalWrite(PIN_LED, true);
    vTaskDelay(300 / portTICK_PERIOD_MS);
    digitalWrite(PIN_LED, false);
    vTaskDelay(200 / portTICK_PERIOD_MS);
  }
});

void setup(void) {
  blinker.start();
}

void loop(void) {}
