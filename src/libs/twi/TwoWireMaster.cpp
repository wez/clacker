#include "src/libs/twi/TwoWireMaster.h"
#ifdef __AVR__
#include "LUFA/Drivers/Peripheral/TWI.h"
#endif

namespace clacker {

static inline TwiResult ErrorResult(uint8_t code) {
  switch (code) {
    case TWI_ERROR_NoError:
      return TwiResult::Ok();
    case TWI_ERROR_BusFault:
      return TwiResult::Error(TwiError::BusFault);
    case TWI_ERROR_BusCaptureTimeout:
      return TwiResult::Error(TwiError::BusCaptureTimeout);
    case TWI_ERROR_SlaveResponseTimeout:
      return TwiResult::Error(TwiError::SlaveResponseTimeout);
    case TWI_ERROR_SlaveNotReady:
      return TwiResult::Error(TwiError::SlaveNotReady);
    case TWI_ERROR_SlaveNAK:
      return TwiResult::Error(TwiError::SlaveNack);
    default:
      panic(makeConstString("illegal TwiResult"));
  }
}

TwoWireMaster& TwoWireMaster::get() {
  static TwoWireMaster twi;
  return twi;
}

void TwoWireMaster::enable(uint32_t busFrequency) {
  // Enable internal pull-ups on SDA, SCL
  PORTD |= (1 << 0) | (1 << 1);
  TWI_Init(TWI_BIT_PRESCALE_1, TWI_BITLENGTH_FROM_FREQ(1, busFrequency));
}

void TwoWireMaster::disable() {
  TWI_Disable();
}

TwiResult TwoWireMaster::readBuffer(
    uint8_t slaveAddress,
    uint16_t timeoutMs,
    uint8_t readAddress,
    uint8_t* destBuf,
    uint16_t destLen) {
  return ErrorResult(TWI_ReadPacket(
      slaveAddress << 1, timeoutMs, &readAddress, 1, destBuf, destLen));
}

Result<Unit, TwiError> TwoWireMaster::writeBuffer(
    uint8_t slaveAddress,
    uint16_t timeoutMs,
    uint8_t writeAddress,
    const uint8_t* srcBuf,
    uint16_t srcLen) {
  return ErrorResult(TWI_WritePacket(
      slaveAddress << 1, timeoutMs, &writeAddress, 1, srcBuf, srcLen));
}
}
