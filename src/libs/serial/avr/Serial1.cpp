#include <avr/interrupt.h>
#include <avr/io.h>
#include "src/libs/serial/avr/Serial.h"
namespace clacker {
namespace avr {

#ifdef UBRR1H
Serial Serial1(UBRR1H, UBRR1L, UCSR1A, UCSR1B, UCSR1C, UDR1);

ISR(USART1_RX_vect) {
  Serial1._rxComplete();
}

ISR(UART1_UDRE_vect) {
  Serial1._udrIsEmpty();
}
#endif
}
}
