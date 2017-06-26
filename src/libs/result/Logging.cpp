#include "src/libs/result/Logging.h"
#include <stdio.h>
#include <stdlib.h>
#include "src/libs/strings/FixedString.h"
#ifdef ARDUINO_ARCH_SAMD
#include <itoa.h>
#endif
namespace clacker {

void logImpl(int numeric) {
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
}
