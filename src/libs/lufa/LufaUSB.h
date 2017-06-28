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

  void addKey(uint8_t key) __attribute__((noinline)) {
    for (auto& k : keys) {
      if (k == 0) {
        k = key;
        return;
      }
    }
  }

  void clearKey(uint8_t key) __attribute__((noinline)) {
    for (auto& k : keys) {
      if (k == key) {
        k = 0;
        return;
      }
    }
  }

  void toggleKey(uint8_t key) __attribute__((noinline)) {
    for (auto& k : keys) {
      if (k == key) {
        k = 0;
        return;
      }
    }
    // If we get here, the key was not pressed so to toggle it
    // we need to add it now
    addKey(key);
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
  using CommandQueue = Queue<Command, 8>;
  CommandQueue queue_;
  Report pendingReport_;
#if 0
  ExtraReport extraKey_;
#endif

  void tick();

 public:
  static LufaUSB& get();

  void run();

  void populateReport(USB_KeyboardReport_Data_t* ReportData);

  void consumerKey(uint16_t code);
  void systemKey(uint16_t code);
  void basicReport(const Report& report);

  void populateExtraKey();
};
}
}
