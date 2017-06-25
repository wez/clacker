#include "src/libs/result/Logging.h"
#ifdef __AVR__
#include <avr/wdt.h>
#endif
namespace clacker {

void panicReset() {
  panicShutdownUSB();
#ifdef __AVR__
  wdt_enable(WDTO_250MS);
#endif
  while (true) {
  }
}
}
