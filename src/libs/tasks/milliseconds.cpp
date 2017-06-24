#include "src/libs/tasks/Timing.h"
#include "task.h"

namespace clacker {
TickType_t millisecondsToTicks(uint32_t ms) {
#ifdef ms2tick
  // The NRF52 port provides this macro
  return ms2tick(ms);
#else
  // Otherwise, just use a simple integer division
  return ms / portTICK_PERIOD_MS;
#endif
}

void delayMilliseconds(uint32_t ms) {
  vTaskDelay(millisecondsToTicks(ms));
}
}
