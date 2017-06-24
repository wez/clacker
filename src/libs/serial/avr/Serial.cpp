#include "src/libs/serial/avr/Serial.h"
#include <avr/io.h>
#include "src/libs/tasks/Tasks.h"

#if !defined(TXC0)
#if defined(TXC)
#if !defined(UPE) && defined(PE)
#define UPE PE
#endif
#define TXC0 TXC
#define RXEN0 RXEN
#define TXEN0 TXEN
#define RXCIE0 RXCIE
#define UDRIE0 UDRIE
#define U2X0 U2X
#define UPE0 UPE
#define UDRE0 UDRE
#elif defined(TXC1)
#define TXC0 TXC1
#define RXEN0 RXEN1
#define TXEN0 TXEN1
#define RXCIE0 RXCIE1
#define UDRIE0 UDRIE1
#define U2X0 U2X1
#define UPE0 UPE1
#define UDRE0 UDRE1
#endif
#endif

namespace clacker {
namespace avr {

Serial::Serial(
    volatile uint8_t& ubrrh,
    volatile uint8_t& ubrrl,
    volatile uint8_t& ucsra,
    volatile uint8_t& ucsrb,
    volatile uint8_t& ucsrc,
    volatile uint8_t& udr)
    : ubrrh_(ubrrh),
      ubrrl_(ubrrl),
      ucsra_(ucsra),
      ucsrb_(ucsrb),
      ucsrc_(ucsrc),
      udr_(udr) {}

freertos::BoolResult Serial::setup(uint32_t baud) {
  auto res = tx_.setup();
  if (res.hasError()) {
    return res;
  }
  res = rx_.setup();
  if (res.hasError()) {
    return res;
  }

  // Compute baud rate setting
  uint16_t setting = (F_CPU / 4 / baud - 1) / 2;
  ubrrh_ = setting >> 8;
  ubrrl_ = setting & 0xff;

  // Set the 2x speed mode bit
  ucsra_ = _BV(U2X0);

  // Enable the Rx and Tx. Also enable the Rx interrupt. The Tx interrupt will
  // get enabled later.
  ucsrb_ = (_BV(RXCIE0) | _BV(RXEN0) | _BV(TXEN0));

  // Set the data bit register to 8n1.
  ucsrc_ = 0x6;

  return freertos::BoolResult::Ok();
}

freertos::BoolResult Serial::send(uint8_t x) {
  auto res = tx_.send(x, 100);
  if (!res.hasError()) {
    enableTxInterrupt();
  }
  return res;
}

Result<uint8_t, BaseType_t> Serial::recv() {
  uint8_t data;
  auto res = rx_.recv(data);
  if (res.hasError()) {
    return Result<uint8_t, BaseType_t>(res.error());
  }
  return Result<uint8_t, BaseType_t>::Ok(data);
}

void Serial::enableTxInterrupt() {
  ucsrb_ = ucsrb_ | _BV(UDRIE0);
}

void Serial::disableTxInterrupt() {
  ucsrb_ = ucsrb_ & ~_BV(UDRIE0);
}

void Serial::_udrIsEmpty() {
  uint8_t data;
  if (tx_.recvFromISR(data, nullptr).hasValue()) {
    udr_ = data;
  } else {
    disableTxInterrupt();
  }
}

void Serial::_rxComplete() {
  uint8_t data = udr_;

  if (!(ucsra_ & _BV(UPE0))) {
    // No partity error? Add to buffer
    rx_.sendFromISR(data, nullptr);
  }
}
}
}
