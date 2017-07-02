#pragma once
#include <LUFA/Drivers/USB/USB.h>
#include "src/libs/keyprocessor/Dispatcher.h"
#include "src/libs/tasks/Queue.h"
#include "src/libs/tasks/Tasks.h"

namespace clacker {
namespace lufa {

enum CommandType {
  KeyReport,
  ExtraKeyReport,
};

struct ExtraReport {
  uint8_t report_id;
  uint16_t usage;
} __attribute__((packed));

struct Command {
  uint8_t CommandType;
  union {
    Report report;
    ExtraReport extra;
  } u;
} __attribute__((packed));

class LufaUSB : public Task<LufaUSB, configMINIMAL_STACK_SIZE * 2, 1> {
  using CommandQueue = Queue<Command, 8>;
  CommandQueue queue_;
  Report pendingReport_;
  volatile uint8_t lastState_;

  void tick();

 public:
  static LufaUSB& get();

  void run();

  void populateReport(USB_KeyboardReport_Data_t* ReportData);
  void maybeWakeTask();

  void consumerKey(uint16_t code);
  void systemKey(uint16_t code);
  void basicReport(const Report& report);
};
}
}
