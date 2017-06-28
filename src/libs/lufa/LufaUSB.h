#pragma once
#include <LUFA/Drivers/USB/USB.h>
#include "src/libs/tasks/Queue.h"
#include "src/libs/tasks/Tasks.h"
namespace clacker {
namespace lufa {

enum CommandType {
  KeyReport,
  ExtraKeyReport,
};

struct Report {
  uint8_t mods;
  uint8_t keys[6];

  void addKey(uint8_t key) {
    for (auto& k : keys) {
      if (k == 0) {
        k = key;
        return;
      }
    }
  }

  void clear() {
    memset(this, 0, sizeof(*this));
  }
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

class LufaUSB : public Task<LufaUSB, configMINIMAL_STACK_SIZE, 1> {
  Report pendingReport_;
  ExtraReport extraKey_;

  void tick();

 public:
  using CommandQueue = Queue<Command, 3>;

  static LufaUSB& get();

  void run();

  void populateReport(USB_KeyboardReport_Data_t* ReportData);

  CommandQueue queue;

  void consumerKey(uint16_t code);
  void systemKey(uint16_t code);

  void populateExtraKey();
};
}
}
