#include "src/libs/result/Logging.h"
#include <stdio.h>
#include <stdlib.h>
#include "src/libs/strings/FixedString.h"
#ifdef ARDUINO_ARCH_SAMD
#include <itoa.h>
#endif

#if defined(__APPLE__) || defined(__linux__)
# define HAVE_ITOA 0
#else
# define HAVE_ITOA 1
#endif

namespace clacker {

void logImpl(int numeric) {
  char numbuf[16];
#if !HAVE_ITOA
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

void logImpl(unsigned int numeric) {
  char numbuf[16];
#if !HAVE_ITOA
  // No itoa on this host system, but we can just fall back to
  // snprintf in that case.  That isn't desirable on embedded
  // systems because the printf library is huge.
  auto len = ::snprintf(numbuf, sizeof(numbuf), "%u", numeric);
  logImpl(numbuf, numbuf + len);
#else
  auto s = utoa(numeric, numbuf, 10);
  auto len = strlen(s);
  logImpl(s, s + len);
#endif
}

void logImpl(uint8_t numeric) {
  logImpl((unsigned int)numeric);
}
}
