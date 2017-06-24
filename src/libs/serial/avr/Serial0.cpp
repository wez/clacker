#include <avr/interrupt.h>
#include <avr/io.h>
#include "src/libs/serial/avr/Serial.h"
namespace clacker {
namespace avr {

#ifdef UBRR0H
Serial Serial0(UBRR0H, UBRR0L, UCSR0A, UCSR0B, UCSR0C, UDR0);

ISR(USART0_RX_vect) {
  Serial0._rxComplete();
}

ISR(UART0_UDRE_vect) {
  Serial0._udrIsEmpty();
}
#endif
}
}
