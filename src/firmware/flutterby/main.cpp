#include "src/libs/gpio/AvrGpio.h"
#include "src/libs/lufa/LufaUSB.h"
#include "src/libs/tasks/Tasks.h"

// This file is generated by the KeyMatrix entry in info.py
#include "outputs/src/firmware/flutterby/matrix/matrix-matrix.h"
#include "src/libs/keymatrix/ScannerWithExpander.h"
#include "src/libs/keyprocessor/KeyProcessor.h"
#include "src/libs/sx1509/sx1509.h"

// The keyboard matrix is attached to the following pins:
// thumbstick X: A0 - PF7 18
// thumbstick Y: A1 - PF6 19
// row0: A2 - PF5
// row1: A3 - PF4
// row2: A4 - PF1
// row3: A5 - PF0
// col0-15:   sx1509
// IO expander interrupt output is connected to arduino pin 11
// (physical pin 12, PCINT7)

using namespace clacker;

// PC7 has the led
using Led = gpio::avr::OutputPin<gpio::avr::PortC, 7>;

using Row0 = gpio::avr::OutputPin<gpio::avr::PortF, 5>;
using Row1 = gpio::avr::OutputPin<gpio::avr::PortF, 4>;
using Row2 = gpio::avr::OutputPin<gpio::avr::PortF, 1>;
using Row3 = gpio::avr::OutputPin<gpio::avr::PortF, 0>;
using RowPins = gpio::avr::OutputPins<Row0, Row1, Row2, Row3>;

using Scanner = MatrixScannerWithExpander<Matrix, RowPins, SX1509>;

enum MacroIds {
  MacroCopy,
  MacroPaste,
};
namespace clacker {
ProgMemIter<uint8_t> lookupMacroDefinition(uint16_t macroid) {
  switch (macroid) {
    case MacroCopy:
      static const uint8_t copy[] PROGMEM = {MacroKeyDown,
                                             HID_KEYBOARD_LEFT_GUI,
                                             MacroKeyDown,
                                             HID_KEYBOARD_C_AND_C,
                                             MacroEnd};
      return copy;

    case MacroPaste:
      static const uint8_t paste[] PROGMEM = {MacroKeyDown,
                                              HID_KEYBOARD_LEFT_GUI,
                                              MacroKeyDown,
                                              HID_KEYBOARD_V_AND_V,
                                              MacroEnd};
      return paste;
  }
  return emptyMacroDefinition();
}
}

const KeyEntry localKeyMapData[64] PROGMEM = {
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_NO_EVENT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_1_AND_EXCLAMATION_POINT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_2_AND_AT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_3_AND_POUND),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_4_AND_DOLLAR),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_5_AND_PERCENT),
    KeyEntry::FunctionKeyEntry(MacroKey, MacroCopy),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_LEFT_CONTROL),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_LEFT_ALT),
    KeyEntry::FunctionKeyEntry(MacroKey, MacroPaste),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_6_AND_CARAT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_7_AND_AMPERSAND),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_8_AND_ASTERISK),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_9_AND_LEFT_PAREN),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_0_AND_RIGHT_PAREN),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_NO_EVENT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_TAB),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_Q_AND_Q),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_W_AND_W),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_E_AND_E),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_R_AND_R),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_T_AND_T),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_LEFT_BRACKET_AND_LEFT_CURLY_BRACE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_NO_EVENT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_LEFT_GUI),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_RIGHT_BRACKET_AND_RIGHT_CURLY_BRACE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_Y_AND_Y),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_U_AND_U),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_I_AND_I),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_O_AND_O),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_P_AND_P),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_BACKSLASH_AND_PIPE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_ESCAPE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_A_AND_A),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_S_AND_S),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_D_AND_D),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_F_AND_F),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_G_AND_G),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_MINUS_AND_UNDERSCORE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_DELETE_FORWARD),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_ENTER),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_EQUALS_AND_PLUS),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_H_AND_H),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_J_AND_J),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_K_AND_K),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_L_AND_L),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_SEMICOLON_AND_COLON),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_QUOTE_AND_DOUBLEQUOTE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_LEFT_SHIFT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_Z_AND_Z),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_X_AND_X),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_C_AND_C),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_V_AND_V),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_B_AND_B),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_NO_EVENT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_DELETE),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_SPACEBAR),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_NO_EVENT),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_N_AND_N),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_M_AND_M),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_COMMA_AND_LESS_THAN),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_PERIOD_AND_GREATER_THAN),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_SLASH_AND_QUESTION_MARK),
    KeyEntry::BasicKeyEntry(HID_KEYBOARD_LEFT_SHIFT),
};

struct blinker : public Task<blinker> {
  void run() {
    while (true) {
      Led::toggle();
      delayMilliseconds(1000);
      // logln(makeConstString("bloop!"));
    }
  }
};

struct scanner : public Task<scanner, configMINIMAL_STACK_SIZE * 2> {
  Scanner scanner;
  KeyboardState<16, 200 / portTICK_PERIOD_MS> keyState;

  void updateKeyState() {
    uint16_t nowTick = xTaskGetTickCount();

    for (uint8_t rowNum = 0; rowNum < Matrix::RowCount; ++rowNum) {
      auto prior = scanner.prior().rows[rowNum];
      auto current = scanner.current().rows[rowNum];
      for (uint8_t colNum = 0; colNum < Matrix::ColCount; ++colNum) {
        auto mask = 1 << colNum;

        if ((prior & mask) != (current & mask)) {
          auto scanCode = (rowNum * Matrix::ColCount) + colNum + 1;
          keyState.updateKeyState(scanCode, current & mask, nowTick);
        }
      }
    }

    // this is a good point to run the keyState through the keymap
    // and emit the USB keycodes
    lufa::Report report;
    report.clear();
    auto& usb = lufa::LufaUSB::get();
    bool haveMacro = false;

    for (auto& k : keyState) {
      if (k.scanCode != 0 && k.down) {
        auto action = progMemLoad(localKeyMapData + k.scanCode - 1);

        switch (action.basic.type) {
          case BasicKey:
            if (action.basic.code == HID_KEYBOARD_NO_EVENT) {
              continue;
            }

            if (action.basic.code >= HID_KEYBOARD_LEFT_CONTROL &&
                action.basic.code <= HID_KEYBOARD_RIGHT_GUI) {
              // Convert to modifier bits
              report.mods |= 1
                  << (action.basic.code - HID_KEYBOARD_LEFT_CONTROL);
              continue;
            }

            report.addKey(action.basic.code);
            break;
          case ConsumerKey:
            usb.consumerKey(action.extra.usage);
            break;
          case SystemKey:
            usb.systemKey(action.extra.usage);
            break;
          case MacroKey:
            haveMacro = true;
            break;
        }
      }
    }

    if (haveMacro) {
      for (auto& k : keyState) {
        if (k.scanCode != 0 && k.down) {
          auto action = progMemLoad(localKeyMapData + k.scanCode - 1);

          switch (action.basic.type) {
            case MacroKey:
              runMacro(report, action.func.funcid);
              break;
          }
        }
      }
    }

    usb.basicReport(report);
  }

  void runMacro(const lufa::Report& report, uint16_t macroid) {
    auto macroReport = report;
    auto iter = lookupMacroDefinition(macroid);
    auto& usb = lufa::LufaUSB::get();
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
          usb.basicReport(macroReport);
          // Allow enough time for the device on the other end to
          // have registered the keypress
          delayMilliseconds(32);
          needReport = false;
          break;
        }
        case MacroEnd:
          if (needReport) {
            usb.basicReport(macroReport);
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
      auto current = scanner.current().rows[rowNum];
      log("row", rowNum, " ");
      for (auto colNum = 0; colNum < Matrix::ColCount; ++colNum) {
        auto mask = 1 << colNum;
        int down = (current & mask) ? 1 : 0;
        log(down);
      }
      log("\r\n");
    }
  }

  void run() {
    scanner.setup();

    while (true) {
      delayMilliseconds(30);
      if (scanner.scanMatrix()) {
        logMatrixState();
        updateKeyState();
      }
    }
  }
};

blinker blinkerTask;
scanner scannerTask;

void launchTasks(void) {
  Led::setup();
  lufa::LufaUSB::get().start().panicIfError();
  scannerTask.start().panicIfError();
  blinkerTask.start().panicIfError();
}
