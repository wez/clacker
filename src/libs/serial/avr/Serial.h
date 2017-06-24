#pragma once
#include "src/libs/tasks/Queue.h"
#include "src/libs/tasks/Tasks.h"

namespace clacker {
namespace avr {

class Serial {
  Queue<uint8_t, 16> tx_;
  Queue<uint8_t, 16> rx_;
  volatile uint8_t& ubrrh_;
  volatile uint8_t& ubrrl_;
  volatile uint8_t& ucsra_;
  volatile uint8_t& ucsrb_;
  volatile uint8_t& ucsrc_;
  volatile uint8_t& udr_;

 public:
  Serial(
      volatile uint8_t& ubrrh,
      volatile uint8_t& ubrrl,
      volatile uint8_t& ucsra,
      volatile uint8_t& ucsrb,
      volatile uint8_t& ucsrc,
      volatile uint8_t& udr);
  freertos::BoolResult setup(uint32_t baud = 9600);

  freertos::BoolResult send(uint8_t x);
  Result<uint8_t, BaseType_t> recv();

  void _udrIsEmpty();
  void _rxComplete();

 private:
  void enableTxInterrupt();
  void disableTxInterrupt();
};

#ifdef UBRR0H
extern Serial Serial0;
#endif
#ifdef UBRR1H
extern Serial Serial1;
#endif
}
}
