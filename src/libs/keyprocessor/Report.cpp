#include <string.h>
#include "src/libs/keyprocessor/Dispatcher.h"
namespace clacker {

bool Report::operator==(const Report& other) const {
  return memcmp(this, &other, sizeof(*this)) == 0;
}
bool Report::empty() const {
  return mods == 0 && keys[0] == 0 && keys[1] == 0 && keys[2] == 0 &&
      keys[3] == 0 && keys[4] == 0 && keys[5] == 0;
}

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
