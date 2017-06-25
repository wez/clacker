#include "src/libs/result/Logging.h"
#ifdef __CLACKER_HOST_BOARD
#include <cstdio>
#include <string>
#endif
#ifdef ARDUINO
#include <Arduino.h>
#endif

namespace clacker {
void logImpl(const char* start, const char* end) __attribute__((weak));
void logImpl(ProgMemIter<char> start, ProgMemIter<char> end)
    __attribute__((weak));

void logImpl(const char* start, const char* end) {
#ifdef __CLACKER_HOST_BOARD
  fwrite(start, sizeof(char), end - start, stdout);
#endif
#ifdef ARDUINO
  Serial.write(start, end - start);
#endif
}

void logImpl(ProgMemIter<char> start, ProgMemIter<char> end) {
#ifdef __CLACKER_HOST_BOARD
  while (start != end) {
    fputc(*start, stdout);
    ++start;
  }
#endif
#ifdef ARDUINO
  while (start != end) {
    Serial.write(*start);
    ++start;
  }
#endif
}

void panicShutdownUSB() __attribute__((weak));
void panicShutdownUSB() {}

void enterBootloader() __attribute__((weak));
void enterBootloader() {
  while (true) {
  }
}

void panicReset() __attribute__((weak));
void panicReset() {
  while (true) {
  }
}
}
