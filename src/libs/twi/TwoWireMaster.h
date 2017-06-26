#pragma once
#include "inttypes.h"
#include "src/libs/result/Result.h"
namespace clacker {

enum TwiError {
  BusFault, // A TWI bus fault occurred while attempting to capture the bus
  BusCaptureTimeout, // timed out waiting for the bus to be ready
  SlaveResponseTimeout, // No ACK from slave within the timeout period
  SlaveNotReady, // Slave NACKd the START condition
  SlaveNack, // Slave NACKd during data transfer
};

using TwiResult = Result<Unit, TwiError>;

class TwoWireMaster {
  TwoWireMaster() = default;

 public:
  // Meyers singleton.  Not strictly needed, but future-proofs things
  // in case we need to adopt ISR driven transfers later on.
  static TwoWireMaster& get();

  void enable(uint32_t busFrequency);
  void disable();

  // Synchronously read data into destBuf
  TwiResult readBuffer(
      uint8_t slaveAddress,
      uint16_t timeoutMs,
      uint8_t readAddress,
      uint8_t* destBuf,
      uint16_t destLen);

  // Synchronously read data into dest
  template <typename T>
  TwiResult
  read(uint8_t slaveAddress, uint16_t timeoutMs, uint8_t readAddress, T& dest) {
    return readBuffer(
        slaveAddress,
        timeoutMs,
        readAddress,
        reinterpret_cast<uint8_t*>(&dest),
        sizeof(T));
  }

  // Synchronously write data from srcBuf
  TwiResult writeBuffer(
      uint8_t slaveAddress,
      uint16_t timeoutMs,
      uint8_t writeAddress,
      const uint8_t* srcBuf,
      uint16_t srcLen);

  // Synchronously write data from src
  template <typename T>
  TwiResult write(
      uint8_t slaveAddress,
      uint16_t timeoutMs,
      uint8_t writeAddress,
      const T& src) {
    return writeBuffer(
        slaveAddress,
        timeoutMs,
        writeAddress,
        reinterpret_cast<const uint8_t*>(&src),
        sizeof(T));
  }
};
}
