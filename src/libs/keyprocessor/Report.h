#pragma once
#include <stdint.h>
namespace clacker {

// Holds key report information to match the basic keyboard
// report in USB and also in BLE HID reporting.
struct Report {
  uint8_t mods;
  uint8_t keys[6];

  void addKey(uint8_t key);
  void clearKey(uint8_t key);
  void toggleKey(uint8_t key);
  void clear();
  bool empty() const;
  bool operator==(const Report&) const;
} __attribute__((packed));
}
