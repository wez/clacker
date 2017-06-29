#include <string.h>
#include "src/libs/keyprocessor/Dispatcher.h"
namespace clacker {

void Report::addKey(uint8_t key) {
  for (auto& k : keys) {
    if (k == 0) {
      k = key;
      return;
    }
  }
}

void Report::clearKey(uint8_t key) {
  for (auto& k : keys) {
    if (k == key) {
      k = 0;
      return;
    }
  }
}

void Report::toggleKey(uint8_t key) {
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

void Report::clear() {
  memset(this, 0, sizeof(*this));
}
}
