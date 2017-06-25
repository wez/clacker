#include <LUFA/Drivers/USB/USB.h>
#include "lufa_data.h"
#include "src/libs/result/Logging.h"
#include "src/libs/tasks/Tasks.h"

// This file implements logging functions that route clacker::log to the
// virtual serial device

namespace clacker {
void logImpl(const char* start, const char* end) {
  CriticalSection disableInterrupts;
  CDC_Device_SendData(&lufa_VirtualSerial_CDC_Interface, start, end - start);
}

void logImpl(ProgMemIter<char> start, ProgMemIter<char> end) {
  CriticalSection disableInterrupts;
  auto startP = start.rawPointer();
  CDC_Device_SendData_P(
      &lufa_VirtualSerial_CDC_Interface, startP, end.rawPointer() - startP);
}
}
