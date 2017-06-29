#pragma once
#include <stdio.h>
#include <stdlib.h>
#include "src/libs/strings/FixedString.h"

namespace clacker {

void logImpl(const char* start, const char* end);
void logImpl(ProgMemIter<char> start, ProgMemIter<char> end);

void panicShutdownUSB();
void panicReset();

[[noreturn]] void panicImpl();

void logImpl(int numeric);
void logImpl(unsigned int numeric);
void logImpl(uint8_t numeric);

inline void logHelper() {}

template <size_t Size>
void logImpl(const char (&literal)[Size]) {
  logImpl(literal, literal + Size);
}

template <typename String>
void logImpl(String&& str) {
  logImpl(str.begin(), str.end());
}

template <typename First, typename... Args>
void logHelper(First&& first, Args&&... args) {
  logImpl(first);
  logHelper(args...);
}

template <typename... Args>
void log(Args&&... args) {
  logHelper(args...);
}

template <typename... Args>
void logln(Args&&... args) {
  logHelper(args..., makeConstString("\r\n"));
}

template <typename... Args>
[[noreturn]] void panic(Args&&... args) {
  logln(args...);
  panicImpl();
}
}
