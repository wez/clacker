#include "src/libs/tasks/Result.h"
#ifdef __EXCEPTIONS
#include <stdexcept>
#endif

namespace clacker {

void panic(const char* reason) {
// TODO: log something to the output/serial
#ifdef __EXCEPTIONS
  throw std::runtime_error(reason);
#endif
  // TODO: either blink the led or jump to the bootloader
  while (true) {
    ;
  }
}
}
