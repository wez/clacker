#include "src/libs/spi/SPI.h"
#include "src/libs/gpio/AvrGpio.h"
namespace clacker {

constexpr uint32_t SpiBusSpeed = 4000000UL;
using SSPin = gpio::avr::OutputPin<gpio::avr::PortB, 0>;
using SCKPin = gpio::avr::OutputPin<gpio::avr::PortB, 1>;
using MOSIPin = gpio::avr::OutputPin<gpio::avr::PortB, 2>;

SPI::Settings::Settings() : spcr_(_BV(SPE) | _BV(MSTR)), spsr_(_BV(SPI2X)) {
  static_assert(SpiBusSpeed == F_CPU / 2, "hard coded at 4Mhz");
}

SPI::SPI() {
  SSPin::setup();
  SSPin::set();

  SPCR = _BV(SPE) | _BV(MSTR);
  SCKPin::setup();
  MOSIPin::setup();
}

Synchronized<SPI>& SPI::get() {
  static Synchronized<SPI> spi;
  return spi;
}

LockedPtr<SPI> SPI::start(const Settings& settings) {
  auto spi = get().lock();
  SPCR = settings.spcr_;
  SPSR = settings.spsr_;
  return spi;
}

uint8_t SPI::transferByte(uint8_t byte) {
  SPDR = byte;
  asm volatile("nop");
  while (!(SPSR & _BV(SPIF))) {
    ; // wait
  }
  return SPDR;
}

void SPI::sendBytes(const uint8_t* buf, uint8_t len) {
  if (len == 0)
    return;
  const uint8_t* end = buf + len;
  while (buf < end) {
    SPDR = *buf;
    while (!(SPSR & _BV(SPIF))) {
      ; // wait
    }
    ++buf;
  }
}

void SPI::recvBytes(uint8_t* buf, uint8_t len) {
  const uint8_t* end = buf + len;
  if (len == 0)
    return;
  while (buf < end) {
    SPDR = 0; // write a dummy to initiate read
    while (!(SPSR & _BV(SPIF))) {
      ; // wait
    }
    *buf = SPDR;
    ++buf;
  }
}
}
