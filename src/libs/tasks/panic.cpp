#include "src/libs/tasks/Result.h"
#ifdef __EXCEPTIONS
#include <stdexcept>
#endif

namespace clacker {

[[noreturn]] void panicImpl() __attribute__((weak));
[[noreturn]] void panicImpl() {
#ifdef __EXCEPTIONS
  throw std::runtime_error("panicked");
#endif
  panicReset();
  exit(1);
}
}
