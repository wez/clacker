#include <avr/io.h>
#include <avr/pgmspace.h>
#include <util/delay.h>

#define LED_ON (PORTD |= (1 << 6))
#define LED_OFF (PORTD &= ~(1 << 6))
#define LED_CONFIG (DDRD |= (1 << 6))

int main(void) {
  LED_CONFIG;
  LED_OFF;

  while (1) {
    LED_ON;
    _delay_ms(300);
    LED_OFF;
    _delay_ms(200);
  }
}
