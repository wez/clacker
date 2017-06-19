#define __CLACKER_TESTING_GPIO__
#include "src/libs/gpio/AvrGpio.h"
#include "src/testing/lest/lest.hpp"
using namespace lest;
using namespace clacker;

static tests specification;

using PinA0 = gpio::avr::OutputPin<gpio::avr::TestPortA, 0>;
using PinA1 = gpio::avr::OutputPin<gpio::avr::TestPortA, 1>;
using PinA2 = gpio::avr::OutputPin<gpio::avr::TestPortA, 2>;
using PinA3 = gpio::avr::OutputPin<gpio::avr::TestPortA, 3>;
using PinA4 = gpio::avr::OutputPin<gpio::avr::TestPortA, 4>;
using PinA5 = gpio::avr::OutputPin<gpio::avr::TestPortA, 5>;
using PinA6 = gpio::avr::OutputPin<gpio::avr::TestPortA, 6>;
using PinA7 = gpio::avr::OutputPin<gpio::avr::TestPortA, 7>;

using PinB0 = gpio::avr::OutputPin<gpio::avr::TestPortB, 0>;
using PinB1 = gpio::avr::OutputPin<gpio::avr::TestPortB, 1>;
using PinB2 = gpio::avr::OutputPin<gpio::avr::TestPortB, 2>;
using PinB3 = gpio::avr::OutputPin<gpio::avr::TestPortB, 3>;
using PinB4 = gpio::avr::OutputPin<gpio::avr::TestPortB, 4>;
using PinB5 = gpio::avr::OutputPin<gpio::avr::TestPortB, 5>;
using PinB6 = gpio::avr::OutputPin<gpio::avr::TestPortB, 6>;
using PinB7 = gpio::avr::OutputPin<gpio::avr::TestPortB, 7>;

using ABits = gpio::avr::
    OutputPins<PinA0, PinA1, PinA2, PinA3, PinA4, PinA5, PinA6, PinA7>;

using PortA = gpio::avr::Port<gpio::avr::TestPortA>;
using PortB = gpio::avr::Port<gpio::avr::TestPortB>;

using AandB = gpio::avr::
    OutputPins<PinA3, PinA2, PinA1, PinA0, PinB7, PinB6, PinB5, PinB4>;

lest_CASE(specification, "single output pin") {
  PinA0::setup();
  EXPECT(PortA::ddr() == 1u);

  PinA0::set();
  EXPECT(PortA::reg() == 1u);

  PinA0::clear();
  EXPECT(PortA::reg() == 0u);
}

lest_CASE(specification, "A only") {
  ABits::setup();
  // Should all be set for output
  EXPECT((int)PortA::ddr() == 0xff);

  for (int x = 0; x <= 0xff; ++x) {
    ABits::write(x);
    EXPECT((int)PortA::reg() == x);
  }
}

lest_CASE(specification, "A and B") {
  // Zero out the registers because we're not sure what order the other
  // tests may have run in, and we want to be sure that we've set the
  // right bits below.
  PortA::ddr() = 0;
  PortB::ddr() = 0;
  PortA::reg() = 0;
  PortB::reg() = 0;

  AandB::setup();
  EXPECT((int)PortA::ddr() == 0b00001111);
  EXPECT((int)PortB::ddr() == 0b11110000);

  AandB::write(0);
  EXPECT((int)PortA::reg() == 0);
  EXPECT((int)PortB::reg() == 0);

  AandB::write(1);
  EXPECT((int)PortA::reg() == 0b00001000);
  EXPECT((int)PortB::reg() == 0);

  AandB::write(2);
  EXPECT((int)PortA::reg() == 0b00000100);
  EXPECT((int)PortB::reg() == 0);

  AandB::write(4);
  EXPECT((int)PortA::reg() == 0b00000010);
  EXPECT((int)PortB::reg() == 0);

  AandB::write(8);
  EXPECT((int)PortA::reg() == 0b00000001);
  EXPECT((int)PortB::reg() == 0);

  AandB::write(16);
  EXPECT((int)PortA::reg() == 0);
  EXPECT((int)PortB::reg() == 0b10000000);

  AandB::write(32);
  EXPECT((int)PortA::reg() == 0);
  EXPECT((int)PortB::reg() == 0b01000000);

  AandB::write(64);
  EXPECT((int)PortA::reg() == 0);
  EXPECT((int)PortB::reg() == 0b00100000);

  AandB::write(128);
  EXPECT((int)PortA::reg() == 0);
  EXPECT((int)PortB::reg() == 0b00010000);

  AandB::write(0xff);
  EXPECT((int)PortA::reg() == 0b00001111);
  EXPECT((int)PortB::reg() == 0b11110000);

  AandB::write(0b00111100);
  EXPECT((int)PortA::reg() == 0b00000011);
  EXPECT((int)PortB::reg() == 0b11000000);
}

int main(int argc, char* argv[]) {
  return run(specification, argc, argv);
}
