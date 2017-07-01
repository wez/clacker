/* Portions of this file are:
  Copyright 2017  Dean Camera (dean [at] fourwalledcubicle [dot] com)

  Permission to use, copy, modify, distribute, and sell this
  software and its documentation for any purpose is hereby granted
  without fee, provided that the above copyright notice appear in
  all copies and that both that the copyright notice and this
  permission notice and warranty disclaimer appear in supporting
  documentation, and that the name of the author not be used in
  advertising or publicity pertaining to distribution of the
  software without specific, written prior permission.

  The author disclaims all warranties with regard to this
  software, including all implied warranties of merchantability
  and fitness.  In no event shall the author be liable for any
  special, indirect or consequential damages or any damages
  whatsoever resulting from loss of use, data or profits, whether
  in an action of contract, negligence or other tortious action,
  arising out of or in connection with the use or performance of
  this software.
*/
#include "src/libs/twi/TwoWireMaster.h"
#include <util/delay.h>
#include <util/twi.h>
#include "src/libs/gpio/AvrGpio.h"

static constexpr uint8_t TWI_ADDRESS_READ = 0x01;
static constexpr uint8_t TWI_ADDRESS_WRITE = 0x00;
static constexpr uint8_t TWI_DEVICE_ADDRESS_MASK = 0xFE;

namespace clacker {

using SDAPin = gpio::avr::InputPin<gpio::avr::PortD, 0, gpio::kEnablePullUp>;
using SCLPin = gpio::avr::InputPin<gpio::avr::PortD, 1, gpio::kEnablePullUp>;

// Helper to make sure that we release the bus.
// The bus starts out unowned, but is then claimed by calling the start()
// method.  Reads will typically write the register number and then read
// the data back from the device, which results in two start() calls.
// The bus is considered to be owned from the first start() call onwards.
// The bus is released automatically when this xmit helper falls out of scope.
class TwiXmit {
  bool owned_;

 public:
  TwiXmit() : owned_(false) {}
  TwiXmit(const TwiXmit&) = delete;

  ~TwiXmit() {
    stop();
  }

  TwiResult start(const uint8_t slaveAddress, const uint8_t TimeoutMS) {
    bool busCaptured = false;
    uint16_t timeoutRemaining;

    timeoutRemaining = (TimeoutMS * 100);
    TWCR = ((1 << TWINT) | (1 << TWSTA) | (1 << TWEN));
    while (!busCaptured && timeoutRemaining) {
      if (TWCR & (1 << TWINT)) {
        switch (TWSR & TW_STATUS_MASK) {
          case TW_START:
          case TW_REP_START:
            busCaptured = true;
            break;
          case TW_MT_ARB_LOST:
            TWCR = ((1 << TWINT) | (1 << TWSTA) | (1 << TWEN));
            // Restart bus arbitration with the full timeout
            timeoutRemaining = (TimeoutMS * 100);
            continue;
          default:
            TWCR = (1 << TWEN);
            return TwiResult::Error(TwiError::BusFault);
        }
      }

      _delay_us(10);
      timeoutRemaining--;
    }

    if (!timeoutRemaining) {
      TWCR = (1 << TWEN);
      return TwiResult::Error(TwiError::BusCaptureTimeout);
    }

    TWDR = slaveAddress;
    TWCR = ((1 << TWINT) | (1 << TWEN));

    timeoutRemaining = (TimeoutMS * 100);
    while (timeoutRemaining) {
      if (TWCR & (1 << TWINT)) {
        break;
      }
      _delay_us(10);
      timeoutRemaining--;
    }

    if (!timeoutRemaining) {
      return TwiResult::Error(TwiError::SlaveResponseTimeout);
    }

    switch (TWSR & TW_STATUS_MASK) {
      case TW_MT_SLA_ACK:
      case TW_MR_SLA_ACK:
        owned_ = true;
        return TwiResult::Ok();
      default:
        TWCR = ((1 << TWINT) | (1 << TWSTO) | (1 << TWEN));
        return TwiResult::Error(TwiError::SlaveNotReady);
    }
  }

  // Sends a TWI STOP onto the TWI bus, terminating communication with the
  // currently addressed device.
  void stop() {
    if (!owned_) {
      return;
    }
    TWCR = ((1 << TWINT) | (1 << TWSTO) | (1 << TWEN));
    // Wait for bus to release (this is important for the ergodox!)
    while (TWCR & (1 << TWSTO))
      ;
    owned_ = false;
  }

  TwiResult recvByte(uint8_t* dest, const bool isFinalByte) {
    if (isFinalByte) {
      TWCR = ((1 << TWINT) | (1 << TWEN));
    } else {
      TWCR = ((1 << TWINT) | (1 << TWEN) | (1 << TWEA));
    }

    while (!(TWCR & (1 << TWINT)))
      ;
    *dest = TWDR;

    uint8_t Status = (TWSR & TW_STATUS_MASK);

    if (isFinalByte ? (Status == TW_MR_DATA_NACK)
                    : (Status == TW_MR_DATA_ACK)) {
      return TwiResult::Ok();
    }
    return TwiResult::Error(TwiError::SlaveNack);
  }

  TwiResult sendByte(const uint8_t Byte) {
    TWDR = Byte;
    TWCR = ((1 << TWINT) | (1 << TWEN));
    while (!(TWCR & (1 << TWINT)))
      ;

    if ((TWSR & TW_STATUS_MASK) == TW_MT_DATA_ACK) {
      return TwiResult::Ok();
    }
    return TwiResult::Error(TwiError::SlaveNack);
  }
};

Synchronized<TwoWireMaster>& TwoWireMaster::get() {
  static Synchronized<TwoWireMaster> twi;
  return twi;
}

void TwoWireMaster::enable(uint32_t busFrequency) {
  // Enable internal pull-ups on SDA, SCL
  SDAPin::setup();
  SCLPin::setup();
  TWSR = 0; // no prescaling
  TWBR = (((F_CPU / busFrequency) - 16) / 2);
}

void TwoWireMaster::disable() {
  TWCR &= ~(1 << TWEN);
}

TwiResult TwoWireMaster::readBuffer(
    uint8_t slaveAddress,
    uint16_t timeoutMs,
    uint8_t readAddress,
    uint8_t* destBuf,
    uint16_t destLen) {
  slaveAddress <<= 1;
  TwiXmit xmit;

  auto res = xmit.start(
      (slaveAddress & TWI_DEVICE_ADDRESS_MASK) | TWI_ADDRESS_WRITE, timeoutMs);
  if (res.hasError()) {
    return res;
  }

  res = xmit.sendByte(readAddress);
  if (res.hasError()) {
    return res;
  }

  res = xmit.start(
      (slaveAddress & TWI_DEVICE_ADDRESS_MASK) | TWI_ADDRESS_READ, timeoutMs);
  if (res.hasError()) {
    return res;
  }

  while (destLen--) {
    res = xmit.recvByte(destBuf++, destLen == 0);
    if (res.hasError()) {
      return res;
    }
  }

  return TwiResult::Ok();
}

Result<Unit, TwiError> TwoWireMaster::writeBuffer(
    uint8_t slaveAddress,
    uint16_t timeoutMs,
    uint8_t writeAddress,
    const uint8_t* srcBuf,
    uint16_t srcLen) {
  slaveAddress <<= 1;
  TwiXmit xmit;

  auto res = xmit.start(
      (slaveAddress & TWI_DEVICE_ADDRESS_MASK) | TWI_ADDRESS_WRITE, timeoutMs);
  if (res.hasError()) {
    return res;
  }

  res = xmit.sendByte(writeAddress);
  if (res.hasError()) {
    return res;
  }

  while (srcLen--) {
    res = xmit.sendByte(*srcBuf++);
    if (res.hasError()) {
      return res;
    }
  }

  return TwiResult::Ok();
}
}
