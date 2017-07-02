#pragma once
// Helpers for doing GPIO on AVR systems.
// GPIO ports on these system are addressed via bitfields,
// making it possible to switch multiple pins in a single
// store operation.
// The helpers in this header allow combining these writes
// without troubling the author of the code with thinking
// about which bits need to be written out together.
#include <stdint.h>
#include "src/libs/gpio/GpioCommon.h"
#ifdef __AVR__
#include <avr/io.h>
#endif

namespace clacker {
namespace gpio {
namespace avr {

// Represents an 8-bit GPIO port
template <class PortType>
struct Port {
  // The Data Direction Register
  static inline volatile uint8_t& ddr();
  // The Port register for setting the output
  static inline volatile uint8_t& port();
  // The pin register for reading the input
  static inline const volatile uint8_t& pin();
};

struct NO_PORT;

template <>
struct Port<NO_PORT> {
  using port = NO_PORT;
};

// Performs a compile time x << N operation
template <int N, bool IS_NEGATIVE>
struct shift_impl {
  static constexpr uint8_t shift(uint8_t x) {
    return x << N;
  }
};

// Performs a compile time x >> -N operation
template <int N>
struct shift_impl<N, true> {
  static constexpr uint8_t shift(uint8_t x) {
    return x >> -N;
  }
};

// Performs a compile time bit shift of x by N
template <int N>
constexpr uint8_t shift(uint8_t x) {
  return shift_impl<N, (N < 0)>::shift(x);
}

// Base case for bit mapping helper; returns 0.
// This case is used when PortType != PINPORT and thus no bits
// should be set.
template <class PortType, class PINPORT, class PIN, int BIT>
struct map_bit_impl {
  static uint8_t map_bit(uint8_t x) {
    return 0;
  }
  static constexpr uint8_t mask = 0;
};

// Bit mapping helper; for a given PortType and PIN definition, and a supplied
// input value x, if BIT is set in x, return the equivalent bit that
// should be set for PortType/PIN.
template <class PortType, class PIN, int BIT>
struct map_bit_impl<PortType, PortType, PIN, BIT> {
  static uint8_t map_bit(uint8_t x) {
    return shift<PIN::bit - BIT>(static_cast<uint8_t>(x & (1 << BIT)));
  }
  static constexpr uint8_t mask = PIN::mask;
};

// Given a PortType and a set of output pins, and an input value x,
// compute the bit mask that should be set to turn on the appropriate
// bits in PortType in a single write operation.
template <
    class PortType,
    class T0,
    class T1,
    class T2,
    class T3,
    class T4,
    class T5,
    class T6,
    class T7>
struct map_bits_impl {
  static constexpr uint8_t map_bits(uint8_t x) {
    return map_bit_impl<PortType, typename T0::port, T0, 0>::map_bit(x) |
        map_bit_impl<PortType, typename T1::port, T1, 1>::map_bit(x) |
        map_bit_impl<PortType, typename T2::port, T2, 2>::map_bit(x) |
        map_bit_impl<PortType, typename T3::port, T3, 3>::map_bit(x) |
        map_bit_impl<PortType, typename T4::port, T4, 4>::map_bit(x) |
        map_bit_impl<PortType, typename T5::port, T5, 5>::map_bit(x) |
        map_bit_impl<PortType, typename T6::port, T6, 6>::map_bit(x) |
        map_bit_impl<PortType, typename T7::port, T7, 7>::map_bit(x);
  }

  static const uint8_t mask =
      map_bit_impl<PortType, typename T0::port, T0, 0>::mask |
      map_bit_impl<PortType, typename T1::port, T1, 1>::mask |
      map_bit_impl<PortType, typename T2::port, T2, 2>::mask |
      map_bit_impl<PortType, typename T3::port, T3, 3>::mask |
      map_bit_impl<PortType, typename T4::port, T4, 4>::mask |
      map_bit_impl<PortType, typename T5::port, T5, 5>::mask |
      map_bit_impl<PortType, typename T6::port, T6, 6>::mask |
      map_bit_impl<PortType, typename T7::port, T7, 7>::mask;
};

template <
    class PortType,
    class T0,
    class T1,
    class T2,
    class T3,
    class T4,
    class T5,
    class T6,
    class T7,
    int MASK>
struct write_bits_impl {
  static void write_bits(volatile uint8_t& reg, uint8_t x) {
    reg = map_bits_impl<PortType, T0, T1, T2, T3, T4, T5, T6, T7>::map_bits(x) |
        (reg & ~MASK);
  }
};

template <
    class PortType,
    class T0,
    class T1,
    class T2,
    class T3,
    class T4,
    class T5,
    class T6,
    class T7>
struct write_bits_impl<PortType, T0, T1, T2, T3, T4, T5, T6, T7, 0> {
  static void write_bits(volatile uint8_t& reg, uint8_t x) {}
};

// Represents a Pin in a port that is to be configured
// as an input pin.  The template parameters specify
// the port, the pin bit and whether the internal
// pull-up resistor should be enabled.
template <class PortType, unsigned BIT, bool PULLUP = false>
struct InputPin : Port<PortType> {
  static_assert(BIT < 8, "bit out of range");

  static constexpr int bit = BIT;
  static constexpr uint8_t mask = 1 << BIT;

  static void setup() {
    Port<PortType>::ddr() &= ~mask;
    if (PULLUP) {
      Port<PortType>::reg() |= mask;
    }
  }

  static bool read() {
    return (Port<PortType>::pin() & mask) != 0;
  }
};

// Represents a Pin in a port that is to be configured
// as an output pin.  The template parameters specify
// the port and the pin bit.
template <class PortType, unsigned BIT>
struct OutputPin : Port<PortType> {
  static_assert(BIT < 8, "bit out of range");

  static constexpr int bit = BIT;
  static constexpr uint8_t mask = 1 << BIT;

  static inline void setup() {
    Port<PortType>::ddr() |= mask;
  }
  static inline void set() {
    Port<PortType>::reg() |= mask;
  }
  static inline void clear() {
    Port<PortType>::reg() &= ~mask;
  }
  static inline void write(bool x) {
    x ? set() : clear();
  }
  static inline void toggle() {
    Port<PortType>::reg() ^= mask;
  }
  static inline bool read() {
    return (Port<PortType>::reg() & mask) == mask;
  }
};

using NoOutputPin = OutputPin<NO_PORT, 0>;

#ifdef PORTB
struct PortB;
template <>
struct Port<PortB> {
  using port = PortB;
  static inline volatile uint8_t& ddr() {
    return DDRB;
  }
  static inline volatile uint8_t& reg() {
    return PORTB;
  }
  static inline volatile const uint8_t& pin() {
    return PINB;
  }
};
#endif

#ifdef PORTC
struct PortC;
template <>
struct Port<PortC> {
  using port = PortC;
  static inline volatile uint8_t& ddr() {
    return DDRC;
  }
  static inline volatile uint8_t& reg() {
    return PORTC;
  }
  static inline volatile const uint8_t& pin() {
    return PINC;
  }
};
#endif

#ifdef PORTD
struct PortD;
template <>
struct Port<PortD> {
  using port = PortD;
  static inline volatile uint8_t& ddr() {
    return DDRD;
  }
  static inline volatile uint8_t& reg() {
    return PORTD;
  }
  static inline volatile const uint8_t& pin() {
    return PIND;
  }
};
#endif

#ifdef PORTE
struct PortE;
template <>
struct Port<PortE> {
  using port = PortE;
  static inline volatile uint8_t& ddr() {
    return DDRE;
  }
  static inline volatile uint8_t& reg() {
    return PORTE;
  }
  static inline volatile const uint8_t& pin() {
    return PINE;
  }
};
#endif

#ifdef PORTF
struct PortF;
template <>
struct Port<PortF> {
  using port = PortF;
  static inline volatile uint8_t& ddr() {
    return DDRF;
  }
  static inline volatile uint8_t& reg() {
    return PORTF;
  }
  static inline volatile const uint8_t& pin() {
    return PINF;
  }
};
#endif

#ifdef __CLACKER_TESTING_GPIO__
struct TestPortA;
template <>
struct Port<TestPortA> {
  using port = TestPortA;

  static inline volatile uint8_t& ddr() {
    static uint8_t r;
    return r;
  }
  static inline volatile uint8_t& reg() {
    static uint8_t r;
    return r;
  }

  // This is for tests to set the fake input
  static inline volatile uint8_t& input_reg() {
    static uint8_t r;
    return r;
  }

  static inline volatile const uint8_t& pin() {
    return input_reg();
  }
};
struct TestPortB;
template <>
struct Port<TestPortB> {
  using port = TestPortB;

  static inline volatile uint8_t& ddr() {
    static uint8_t r;
    return r;
  }
  static inline volatile uint8_t& reg() {
    static uint8_t r;
    return r;
  }

  // This is for tests to set the fake input
  static inline volatile uint8_t& input_reg() {
    static uint8_t r;
    return r;
  }

  static inline volatile const uint8_t& pin() {
    return input_reg();
  }
};
#endif

// Sets up the DDR
template <
    class PortType,
    class T0,
    class T1,
    class T2,
    class T3,
    class T4,
    class T5,
    class T6,
    class T7>
void do_setup_pins(uint8_t mask) {
  write_bits_impl<
      PortType,
      T0,
      T1,
      T2,
      T3,
      T4,
      T5,
      T6,
      T7,
      map_bits_impl<PortType, T0, T1, T2, T3, T4, T5, T6, T7>::mask>::
      write_bits(Port<PortType>::ddr(), mask);
}

// Sets the pin output levels
template <
    class PortType,
    class T0,
    class T1,
    class T2,
    class T3,
    class T4,
    class T5,
    class T6,
    class T7>
void do_write_pins(uint8_t mask) {
  write_bits_impl<
      PortType,
      T0,
      T1,
      T2,
      T3,
      T4,
      T5,
      T6,
      T7,
      map_bits_impl<PortType, T0, T1, T2, T3, T4, T5, T6, T7>::mask>::
      write_bits(Port<PortType>::reg(), mask);
}

// OutputPins is used to combine a set of OutputPin types
// into an aggregate type.  The template parameters consist
// of up to 8 output pins.  Writing a byte to the aggregate
// causes the corresponding bits to be set in the related
// output pins.  The bits are combined in such a way that
// pins common to a single port are set together in a single
// write operation to the port.
// The first template parameter (T0) corresponds to the
// least significant bit in the value being written, through
// to T7 mapping to the most significant bit.
// A similar technique could be used to create an InputPins
// class; it would need a helper that does the inverse of
// map_bits_impl.

template <
    class T0,
    class T1 = NoOutputPin,
    class T2 = NoOutputPin,
    class T3 = NoOutputPin,
    class T4 = NoOutputPin,
    class T5 = NoOutputPin,
    class T6 = NoOutputPin,
    class T7 = NoOutputPin> // LSB to MSB order
struct OutputPins {
  static void setup() {
#ifdef PORTB
    do_setup_pins<PortB, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
#endif
#ifdef PORTC
    do_setup_pins<PortC, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
#endif
#ifdef PORTD
    do_setup_pins<PortD, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
#endif
#ifdef PORTE
    do_setup_pins<PortE, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
#endif
#ifdef PORTF
    do_setup_pins<PortF, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
#endif
#ifdef __CLACKER_TESTING_GPIO__
    do_setup_pins<TestPortA, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
    do_setup_pins<TestPortB, T0, T1, T2, T3, T4, T5, T6, T7>(0xff);
#endif
  }

  static void write(uint8_t x) {
#ifdef PORTB
    do_write_pins<PortB, T0, T1, T2, T3, T4, T5, T6, T7>(x);
#endif
#ifdef PORTC
    do_write_pins<PortC, T0, T1, T2, T3, T4, T5, T6, T7>(x);
#endif
#ifdef PORTD
    do_write_pins<PortD, T0, T1, T2, T3, T4, T5, T6, T7>(x);
#endif
#ifdef PORTE
    do_write_pins<PortE, T0, T1, T2, T3, T4, T5, T6, T7>(x);
#endif
#ifdef PORTF
    do_write_pins<PortF, T0, T1, T2, T3, T4, T5, T6, T7>(x);
#endif
#ifdef __CLACKER_TESTING_GPIO__
    do_write_pins<TestPortA, T0, T1, T2, T3, T4, T5, T6, T7>(x);
    do_write_pins<TestPortB, T0, T1, T2, T3, T4, T5, T6, T7>(x);
#endif
  }
};

using NoInputPin = InputPin<NO_PORT, 0>;

template <typename Pin>
void setupPin() {
  Pin::setup();
}

template <>
inline void setupPin<NoInputPin>() {}

template <typename Pin>
uint8_t readPin(uint8_t value) {
  return Pin::read() ? value : 0;
}

template <>
inline uint8_t readPin<NoInputPin>(uint8_t) {
  return 0;
}

template <
    class T0,
    class T1 = NoInputPin,
    class T2 = NoInputPin,
    class T3 = NoInputPin,
    class T4 = NoInputPin,
    class T5 = NoInputPin,
    class T6 = NoInputPin,
    class T7 = NoInputPin> // LSB to MSB order
struct InputPins {
  static void setup() {
    setupPin<T0>();
    setupPin<T1>();
    setupPin<T2>();
    setupPin<T3>();
    setupPin<T4>();
    setupPin<T5>();
    setupPin<T6>();
    setupPin<T7>();
  }

  static uint8_t read() {
    return readPin<T0>(1 << 0) | readPin<T1>(1 << 1) | readPin<T2>(1 << 2) |
        readPin<T3>(1 << 3) | readPin<T4>(1 << 4) | readPin<T5>(1 << 5) |
        readPin<T6>(1 << 6) | readPin<T7>(1 << 7);
  }
};

} // avr
} // gpio
} // clacker
