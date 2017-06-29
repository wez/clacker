#pragma once
#include "src/libs/keyprocessor/HIDTables.h"
#include "src/libs/keyprocessor/KeyProcessor.h"
#include "src/libs/keyprocessor/Report.h"
#include "src/libs/result/Logging.h"
#include "src/libs/tasks/Tasks.h"

namespace clacker {

// The keymap data is either provided by the application, or more easily,
// generated from keyboard-layout-editor.com data via info.py
extern const KeyEntry keyMapData[]
#ifdef PROGMEM
    PROGMEM
#endif
    ;

// An application-provided function to return an iterator to the specified
// macro sequence.
extern ProgMemIter<uint8_t> lookupMacroDefinition(uint16_t macroid);

// This template defines a DispatcherTask class that is responsible for
// driving the keyboard scanner, maintaining state for the pressed keys,
// looking up the appropriate actions based on the keyMapData and
// dispatching them to the application provided Dispatcher class.
// The Dispatcher is expected to implement the following methods:
//
// void consumerKey(uint16_t code);
// void systemKey(uint16_t code);
// void basicReport(const Report& report);
//
// Matrix is the matrix type.
// Scanner is the scanner type.
// TappingIntervalMs specifies how many milliseconds bounds a tap
// (as opposed to a hold) of a key.
// Rollover specifies how many concurrent key states we can track
// (this is distinct from the rollover of the Dispatcher/host).
// StackSize is the size of the stack created for the associated task.
template <
    typename Dispatcher,
    typename Matrix,
    typename Scanner,
    uint32_t TappingIntervalMs,
    uint32_t StackSize = configMINIMAL_STACK_SIZE * 2,
    uint8_t Rollover = 16>
struct DispatcherTask : public Task<
                            DispatcherTask<
                                Dispatcher,
                                Matrix,
                                Scanner,
                                TappingIntervalMs,
                                StackSize,
                                Rollover>,
                            StackSize> {
  // Convert the interval to ticks
  static constexpr uint32_t TappingInterval =
      TappingIntervalMs / portTICK_PERIOD_MS;
  Scanner scanner_;
  KeyboardState<Rollover, TappingInterval> keyState_;
  uint8_t currentLayer_;
  uint16_t lastStateTick_;
  Dispatcher dispatcher_;

  KeyEntry loadEntry(uint8_t scanCode) {
    auto layerMap =
        keyMapData + (currentLayer_ * Matrix::RowCount * Matrix::ColCount);
    auto entry = progMemLoad(((KeyEntry*)(layerMap)) + scanCode - 1);
    if (currentLayer_ > 0 && entry.raw == 0) {
      // Try base layer. TODO: when using layer stack, walk up the stack
      layerMap = keyMapData;
      entry = progMemLoad(((KeyEntry*)(layerMap)) + scanCode - 1);
    }
    return entry;
  }

  void updateKeyState() {
    uint16_t nowTick = xTaskGetTickCount();

    for (uint8_t rowNum = 0; rowNum < Matrix::RowCount; ++rowNum) {
      auto prior = scanner_.prior().rows[rowNum];
      auto current = scanner_.current().rows[rowNum];
      for (uint8_t colNum = 0; colNum < Matrix::ColCount; ++colNum) {
        auto mask = 1 << colNum;

        if ((prior & mask) != (current & mask)) {
          auto scanCode = (rowNum * Matrix::ColCount) + colNum + 1;
          keyState_.updateKeyState(scanCode, current & mask, nowTick);
        }
      }
    }

    // this is a good point to run the keyState through the keymap
    // and emit the USB keycodes
    Report report;
    report.clear();
    uint8_t macroScanCode = 0;

    // First pass: process layer transitions that just occurred
    for (auto& k : keyState_) {
      if (k.scanCode != 0 && k.eventTime >= lastStateTick_) {
        auto action = loadEntry(k.scanCode);
        log(makeConstString("Consider layer, "));
        logKey(action);
        log(makeConstString("\r\n"));
        if (action.layer.type != LayerKey) {
          continue;
        }

        if (k.down) {
          // Holding down a momentary layer key switches the layer.
          // We also transition on press for non-momentary switches
          // to account for the user very quickly pressing a key
          // that belongs in the target layer after pressing the
          // layer modifier.
          // TODO: should be a stack
          currentLayer_ = action.layer.layerid;
          logln(makeConstString("move to layer "), currentLayer_);
        } else if (action.layer.momentary) {
          // Finished a momentary layer switch, restore prior layer
          // TODO: stack!
          logln(makeConstString("restore layer"));
          currentLayer_ = 0;
        }
      }
    }

    for (auto& k : keyState_) {
      if (k.scanCode == 0) {
        continue;
      }
      if (k.down) {
        auto action = loadEntry(k.scanCode);

        switch (action.basic.type) {
          case BasicKey:
            if (action.basic.code == HID_KEYBOARD_NO_EVENT &&
                action.basic.mods == 0) {
              continue;
            }

            report.mods |= action.basic.mods;

            if (action.basic.code >= HID_KEYBOARD_LEFT_CONTROL &&
                action.basic.code <= HID_KEYBOARD_RIGHT_GUI) {
              // Convert to modifier bits
              report.mods |= 1
                  << (action.basic.code - HID_KEYBOARD_LEFT_CONTROL);
              continue;
            }

            report.addKey(action.basic.code);
            break;
          case DualRoleKey:
            // While held down, we emit the modifiers.
            report.mods |= action.dual.mods;
            break;

          case ConsumerKey:
            dispatcher_.consumerKey(action.extra.usage);
            break;
          case SystemKey:
            dispatcher_.systemKey(action.extra.usage);
            break;
        }
      } else if (k.eventTime > lastStateTick_) {
        logln(
            makeConstString("key eventTime "),
            k.eventTime,
            makeConstString(" >= lastStateTick "),
            lastStateTick_);
        // We just released this key
        auto action = loadEntry(k.scanCode);
        switch (action.basic.type) {
          case DualRoleKey:
            // If we tapped the key then we emit the key code
            if (k.eventTime - k.priorTime <= TappingInterval) {
              report.addKey(action.dual.code);

              // Avoid the modifiers from the down state bleeding
              // into the present one for the dual role tap by
              // delaying for long enough that the prior report
              // was fully picked up
              {
                Report empty;
                empty.clear();
                empty.mods = report.mods;
                dispatcher_.basicReport(empty);
                delayMilliseconds(32);
              }
            }
            break;
          case MacroKey:
            if (k.eventTime - k.priorTime <= TappingInterval) {
              macroScanCode = k.scanCode;
            }
            break;

          case ConsumerKey:
            dispatcher_.consumerKey(0);
            break;
          case SystemKey:
            dispatcher_.systemKey(0);
            break;
        }
      }
    }

    if (macroScanCode != 0) {
      auto action = loadEntry(macroScanCode);
      macroScanCode = 0;

      switch (action.basic.type) {
        case MacroKey:
          runMacro(report, action.func.funcid);
          break;
      }
    }

    dispatcher_.basicReport(report);
    lastStateTick_ = nowTick;
  }

  void runMacro(const Report& report, uint16_t macroid) {
    auto macroReport = report;
    auto iter = lookupMacroDefinition(macroid);
    bool needReport = false;
    while (true) {
      auto macro = *iter;
      ++iter;
      switch (macro) {
        case MacroKeyDown:
        case MacroKeyToggle:
        case MacroKeyUp: {
          auto key = *iter;
          ++iter;

          if (key >= HID_KEYBOARD_LEFT_CONTROL &&
              key <= HID_KEYBOARD_RIGHT_GUI) {
            // Convert to modifier bits
            auto mask = 1 << (key - HID_KEYBOARD_LEFT_CONTROL);

            if (macro == MacroKeyToggle) {
              macro = (macroReport.mods & mask) ? MacroKeyUp : MacroKeyDown;
            }

            if (macro == MacroKeyDown) {
              macroReport.mods |= mask;
            } else {
              macroReport.mods &= ~mask;
            }
            needReport = true;
            continue;
          }

          if (macro == MacroKeyDown) {
            macroReport.addKey(key);
          } else if (macro == MacroKeyUp) {
            macroReport.clearKey(key);
          } else {
            macroReport.toggleKey(key);
          }
          dispatcher_.basicReport(macroReport);
          // Allow enough time for the device on the other end to
          // have registered the keypress
          delayMilliseconds(32);
          needReport = false;
          break;
        }
        case MacroEnd:
          if (needReport) {
            dispatcher_.basicReport(macroReport);
            // Allow enough time for the device on the other end to
            // have registered the keypress
            delayMilliseconds(32);
          }
          return;

        default:
          return;
      }
    }
  }

  void logMatrixState() {
    logln(makeConstString("matrix changed!"));

    for (auto rowNum = 0; rowNum < Matrix::RowCount; ++rowNum) {
      auto current = scanner_.current().rows[rowNum];
      log(makeConstString("row"), rowNum, makeConstString(" "));
      for (auto colNum = 0; colNum < Matrix::ColCount; ++colNum) {
        auto mask = 1 << colNum;
        int down = (current & mask) ? 1 : 0;
        log(down);
      }
      log(makeConstString("\r\n"));
    }
  }

 public:
  void run() {
    scanner_.setup();
    lastStateTick_ = 0;

    while (true) {
      delayMilliseconds(30);
      if (scanner_.scanMatrix()) {
        logMatrixState();
      }
      updateKeyState();
    }
  }
};
}
