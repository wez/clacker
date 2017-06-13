#include <Arduino.h>
#include "FreeRTOS.h"
#if defined(ARDUINO_SAMD_FEATHER_M0) || defined(NRF52)
extern "C" void delay(uint32_t);
static inline void _delay_ms(uint32_t m) {
  delay(m);
}
#else
#include <util/delay.h>
#endif

#ifndef PIN_LED
#define PIN_LED LED_BUILTIN
#endif

void setup(void) {}

void loop(void) {
  digitalWrite(PIN_LED, true);
  _delay_ms(300);
  digitalWrite(PIN_LED, false);
  _delay_ms(200);
}
