#include "src/libs/gpio/AvrGpio.h"
#include "src/libs/lufa/LufaUSB.h"
#include "src/libs/tasks/Tasks.h"

// This file is generated by the KeyMatrix entry in info.py
#include "outputs/src/firmware/flutterby/matrix/matrix-matrix.h"

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

clacker::Task<> blinker([] {
  while (true) {
    Led::toggle();
    delayMilliseconds(1000);
    lufa::LufaUSB::get().bloop();
  }
});

void launchTasks(void) {
  Led::setup();
  RowPins::setup();
  blinker.start().panicIfError();
  lufa::LufaUSB::get().start();
}
