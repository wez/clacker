#pragma once
#include <stdint.h>
#include "src/libs/progmem/ProgMem.h"
#include "src/libs/result/Logging.h"

namespace clacker {

// A KeyProcessor keeps track of the state of a fixed number of keys.
// A given keymap may have a variety of actions to dispatch based
// on the combination or ordering of key press events.

// Terminology:
// ScanCode - an non-zero integer value identifying a physical key in a
//            key matrix.
//

// KeyState represents what we know about the state of a key
struct KeyState {
  // Which key we're tracking here
  uint8_t scanCode;
  // Whether the key is currently down (1) or up (0)
  unsigned down : 1;
  // Toggle streak; how many times the key has transitioned
  // between down <-> !down within the globally configured
  // tapping interval
  unsigned toggles : 7;
  // Time at which the last transition occurred
  uint16_t eventTime;
  // Previous transition time
  uint16_t priorTime;
};

// Represents the state of all of the keys that we can
// track on the keyboard.  There is a fixed number that
// we can track, specified by the Rollover template parameter.
template <uint8_t Rollover, uint16_t TappingInterval>
class KeyboardState {
 public:
  bool updateKeyState(uint8_t scanCode, bool down, uint16_t eventTime) {
    auto slot = findSlot(scanCode);

    ageSlots(eventTime);

    if (!slot) {
      // Too many keys held down, so there's nothing that we can do
      return false;
    }

    if (slot->scanCode == scanCode && slot->down != down &&
        eventTime - slot->eventTime <= TappingInterval) {
      ++slot->toggles;
    } else {
      // Start a new toggle streak
      slot->toggles = 1;
    }

    if (slot->scanCode != scanCode) {
      slot->priorTime = eventTime;
    } else {
      slot->priorTime = slot->eventTime;
    }

    slot->scanCode = scanCode;
    slot->down = down;
    slot->eventTime = eventTime;
    return true;
  }

  // Clear the state of all keys
  void clear() {
    memset(keys_, 0, sizeof(keys_));
  }

  // Allow consumers read-only access to the keystate
  const KeyState& keys() const {
    return keys_;
  }
  const KeyState* begin() const {
    return keys_;
  }
  const KeyState* end() const {
    return keys_ + Rollover;
  }

 private:
  KeyState keys_[Rollover];

  void ageSlots(uint16_t eventTime) {
    for (auto& k : keys_) {
      if (!k.down && eventTime - k.eventTime > TappingInterval) {
        k.scanCode = 0;
      }
    }
  }

  // Find a suitable slot in keys_ to record information about
  // a given scanCode.  May return nullptr if we cannot track any
  // additional keys.
  KeyState* findSlot(uint8_t scanCode) {
    KeyState* state = nullptr;
    KeyState* available = nullptr;
    KeyState* oldest = nullptr;

    for (auto& s : keys_) {
      if (s.scanCode == scanCode) {
        // Exact match
        return &s;
      }

      if (available) {
        continue;
      }

      if (s.scanCode == 0) {
        // This slot is currently unused, so remember that it is available
        available = &s;
        continue;
      }

      if (!s.down) {
        if (!oldest || s.eventTime < oldest->eventTime) {
          // This key is not currently down and made that transition the
          // longest time ago out of all of the keys_.
          oldest = &s;
        }
      }
    }

    // If we get here we didn't find an exact match.
    if (available) {
      // Best available result is an unused slot
      return available;
    }

    // Otherwise, forget about the oldest inactive key state
    // and re-use that slot, if any.
    return oldest;
  }
};

enum KeyEntryType {
  BasicKey,
  ConsumerKey,
  SystemKey,
  FunctionKey,
  MacroKey,
  LayerKey,
  DualRoleKey,
};

enum BasicKeyMods {
  LeftControl = 1 << 0,
  LeftShift = 1 << 1,
  LeftAlt = 1 << 2,
  LeftGui = 1 << 3,
  Hyper = LeftControl | LeftShift | LeftAlt | LeftGui,
};

union KeyEntry {
  uint16_t raw;

  // BasicKey
  struct BasicKeyEntry {
    unsigned type : 4;
    // BasicKeyMods or'd together; extra modifiers associated
    // with this key being pressed
    unsigned mods : 4;
    uint8_t code;

    constexpr BasicKeyEntry(uint8_t code, uint8_t mods = 0)
        : type(BasicKey), mods(mods), code(code) {}
  } basic;

  // ConsumerKey or SystemKey.
  // These don't work properly at the moment, or macOS can't use them.
  // I'm not sure which is the case.
  struct ExtraKeyEntry {
    unsigned type : 4;
    unsigned usage : 12;

    constexpr ExtraKeyEntry(enum KeyEntryType t, uint16_t usage)
        : type(t), usage(usage) {}
  } extra;

  static constexpr ExtraKeyEntry Consumer(uint16_t usage) {
    return ExtraKeyEntry(ConsumerKey, usage);
  }

  // FunctionKey or MacroKey
  struct FunctionKeyEntry {
    unsigned type : 4;
    unsigned funcid : 12;

    constexpr FunctionKeyEntry(enum KeyEntryType t, uint16_t funcid)
        : type(t), funcid(funcid) {}
  } func;

  static constexpr FunctionKeyEntry MacroKeyEntry(uint16_t macroid) {
    return FunctionKeyEntry(MacroKey, macroid);
  }

  struct LayerKeyEntry {
    unsigned type : 4;
    unsigned momentary : 1;
    unsigned spare_ : 3;
    uint8_t layerid;

    constexpr LayerKeyEntry(uint8_t layerid, bool momentary = true)
        : type(LayerKey), momentary(momentary), spare_(0), layerid(layerid) {}
  } layer;

  struct DualRoleKeyEntry {
    unsigned type : 4;
    unsigned mods : 4;
    uint8_t code;
    constexpr DualRoleKeyEntry(uint8_t code, uint8_t mods = 0)
        : type(DualRoleKey), mods(mods), code(code) {}
  } dual;

  constexpr KeyEntry() : raw(0) {}
  constexpr KeyEntry(BasicKeyEntry b) : basic(b) {}
  constexpr KeyEntry(ExtraKeyEntry b) : extra(b) {}
  constexpr KeyEntry(FunctionKeyEntry b) : func(b) {}
  constexpr KeyEntry(LayerKeyEntry b) : layer(b) {}
  constexpr KeyEntry(DualRoleKeyEntry b) : dual(b) {}
};

void logKey(const KeyEntry& ent);

// An application-provided function to execute a user-defined function
extern void performUserDefinedFunction(uint16_t fnid);

ProgMemIter<uint8_t> emptyMacroDefinition();

// These codes specify how to interpret the USB key codes that are
// part of the macro stream.
// eg: {MacroKeyDown, HID_KEYBOARD_C, MacroKeyUp, HID_KEYBOARD_C, MacroEnd}
// sends the sequence of C being pressed and released.  Note that the
// macro renderer will restore the key state to those keys that are depressed
// once it reaches the end of the macro stream, so you do not need to
// explicitly add MacroKeyUp entries unless you need the macro to release the
// key as part of its execution.
// Note that the numeric values chosen for this enum were selected to
// avoid collisions with the HID_KEYBOARD_XXX namespace.
enum MacroKeyDisposition {
  // Ends a macro sequence
  MacroEnd = 0,
  // The HID Keyboard code that follows is pressed
  MacroKeyDown = 1,
  // The HID Keyboard code that follows is released
  MacroKeyUp = 2,
  // The HID Keyboard code that follows is switched between
  // down <-> up
  MacroKeyToggle = 3,
};
}
