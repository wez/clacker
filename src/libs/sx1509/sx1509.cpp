/*
Copyright 2016-2017 Wez Furlong

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
#include "sx1509.h"
#include "src/libs/twi/TwoWireMaster.h"

namespace clacker {

// Controls the SX1509 16 pin I/O expander

#define i2cAddress 0x3e // Configurable with jumpers
enum sx1509_registers {
  RegReset = 0x7d,
  RegDirA = 0x0f,
  RegDirB = 0x0e,
  RegPullUpA = 0x07,
  RegPullUpB = 0x06,
  DataA = 0x11,
  DataB = 0x10,
  RegInterruptMaskA = 0x13, // IOs configured to raise interrupts
  RegInterruptMaskB = 0x12,

  // Each pin has 2 bits:
  // 00 None
  // 01 Rising
  // 10 Falling
  // 11 Both
  // 7:6 Data[15], 5:4 Data[14], 3:2 Data[13], 1:0 Data[12]
  RegSenseHighB = 0x14,
  // 7:6 Data[11], 5:4 Data[10], 3:2 Data[9], 1:0 Data[8]
  RegSenseLowB = 0x15,
  // 7:6 Data[7], 5:4 Data[6], 3:2 Data[5], 1:0 Data[4]
  RegSenseHighA = 0x16,
  // 7:6 Data[3], 5:4 Data[2], 3:2 Data[1], 1:0 Data[0]
  RegSenseLowA = 0x17,

  // A 1 indicates that a pin was the source of an interrupt.
  // Writing a 1 clears this and corresponding bit in RegEventStatus
  // When all are cleared, interrupt pin goes back to high.
  RegInterruptSourceA = 0x19,
  RegInterruptSourceB = 0x18,

  // A 1 indicates that an event occurred on a pin.
  // Writing a 1 clears this and corresponding bit in RegInterruptSource.
  // When all are cleared, interrupt pin goes back to high.
  RegEventStatusA = 0x1b,
  RegEventStatusB = 0x1a,
};

static void
set_reg(LockedPtr<TwoWireMaster>& twi, enum sx1509_registers reg, uint8_t val) {
  twi->write(i2cAddress, 100, uint8_t(reg), val);
}

void SX1509::setup() {
  auto twi = TwoWireMaster::get().lock();
  twi->enable(400000);

  // Software reset
  set_reg(twi, RegReset, 0x12);
  set_reg(twi, RegReset, 0x34);

  // Set all the pins as inputs
  set_reg(twi, RegDirA, 0xff);
  set_reg(twi, RegDirB, 0xff);

  // Turn on internal pull-ups
  set_reg(twi, RegPullUpA, 0xff);
  set_reg(twi, RegPullUpB, 0xff);
}

// Read all 16 inputs and return them
uint16_t SX1509::read() {
  uint8_t result[2];
  TwoWireMaster::get().lock()->readBuffer(
      i2cAddress, 1000, uint8_t(DataB), result, sizeof(result));
  return (result[0] << 8) | result[1];
}

uint16_t SX1509::interruptSources() {
  uint8_t result[2];
  auto twi = TwoWireMaster::get().lock();
  twi->readBuffer(
      i2cAddress, 1000, uint8_t(RegInterruptSourceB), result, sizeof(result));

  // Clear the bits
  uint16_t ones = 0xffff;
  twi->write(i2cAddress, 1000, uint8_t(RegInterruptSourceB), ones);

  return (result[0] << 8) | result[1];
}

void SX1509::enableInterrupts() {
  auto twi = TwoWireMaster::get().lock();
  // Trigger an interrupt for both rising and falling events
  set_reg(twi, RegSenseHighB, 0xff);
  set_reg(twi, RegSenseLowB, 0xff);
  set_reg(twi, RegSenseHighA, 0xff);
  set_reg(twi, RegSenseLowA, 0xff);

  // Enable interrupts
  set_reg(twi, RegInterruptMaskA, 0x00);
  set_reg(twi, RegInterruptMaskB, 0x00);
}

void SX1509::disableInterrupts() {
  auto twi = TwoWireMaster::get().lock();
  // Disable interrupts
  set_reg(twi, RegInterruptMaskA, 0xff);
  set_reg(twi, RegInterruptMaskB, 0xff);

  set_reg(twi, RegSenseHighB, 0);
  set_reg(twi, RegSenseLowB, 0);
  set_reg(twi, RegSenseHighA, 0);
  set_reg(twi, RegSenseLowA, 0);
}
}
