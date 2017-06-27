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

struct blinker : public Task<blinker> {
  void run() {
    while (true) {
      Led::toggle();
      delayMilliseconds(1000);
      logln(makeConstString("bloop!"));
    }
  }
};

struct scanner : public Task<scanner> {
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

    // TODO: this is a good point to run the keyState through the keymap
    // and emit the USB keycodes
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
