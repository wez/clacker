#pragma once
#include <LUFA/Drivers/USB/USB.h>
#include "src/libs/tasks/Queue.h"
#include "src/libs/tasks/Tasks.h"
namespace clacker {
namespace lufa {

enum CommandType {
  KeyReport,
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
};

struct Command {
  uint8_t CommandType;
  union {
    Report report;
  } u;
} __attribute__((packed));

static_assert(sizeof(Command) == 8, "packed ok");

class LufaUSB {
  Task<configMINIMAL_STACK_SIZE, 1> task_;
  Report pendingReport_;
  LufaUSB();

 public:
  using CommandQueue = Queue<Command, 3>;

  static LufaUSB& get();
  void start();
  void tick();

  void taskLoop();

  void populateReport(USB_KeyboardReport_Data_t* ReportData);
  void bloop();

  CommandQueue queue;
};
}
}
