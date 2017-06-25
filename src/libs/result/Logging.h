#pragma once
#include <stdio.h>
#include <stdlib.h>
#include "src/libs/strings/FixedString.h"
#ifdef ARDUINO_ARCH_SAMD
#include <itoa.h>
#endif

namespace clacker {

void logImpl(const char* start, const char* end);
void logImpl(ProgMemIter<char> start, ProgMemIter<char> end);

void panicShutdownUSB();
void panicReset();

[[noreturn]] void panicImpl();

inline void logImpl(int numeric) {
  char numbuf[16];
#ifdef __APPLE__
  // No itoa on this host system, but we can just fall back to
  // snprintf in that case.  That isn't desirable on embedded
  // systems because the printf library is huge.
  auto len = ::snprintf(numbuf, sizeof(numbuf), "%d", numeric);
  logImpl(numbuf, numbuf + len);
#else
  auto s = itoa(numeric, numbuf, 10);
  auto len = strlen(s);
  logImpl(s, s + len);
#endif
}

inline void logHelper() {}

template <size_t Size>
inline void logImpl(const char (&literal)[Size]) {
  logImpl(literal, literal + Size);
}

template <typename String>
inline void logImpl(String&& str) {
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
