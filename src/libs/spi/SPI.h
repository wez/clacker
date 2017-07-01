#pragma once
#include "src/libs/tasks/Mutex.h"
namespace clacker {

class SPI {
 public:
  static Synchronized<SPI>& get();

  class Settings {
    uint8_t spcr_, spsr_;
    friend class SPI;

   public:
    Settings();
  };

  SPI();

  static LockedPtr<SPI> start(const Settings& settings);

  uint8_t transferByte(uint8_t byte);
  inline uint8_t readByte() {
    return transferByte(0 /* dummy */);
  }
  void sendBytes(const uint8_t* bytes, uint8_t len);
  void recvBytes(uint8_t* bytes, uint8_t len);
};
}
