#pragma once
#ifdef ARDUINO
#include <Arduino.h>
namespace clacker {
namespace gpio {
namespace arduino {

template <unsigned PIN, bool PULLUP = false>
struct InputPin {
  static void setup() {
    pinMode(PIN, PULLUP ? INPUT_PULLUP : INPUT);
  }

  static bool read() {
    return digitalRead(PIN) == HIGH;
  }
};

template <unsigned PIN>
struct OutputPin {
  static inline void setup() {
    pinMode(PIN, OUTPUT);
  }
  static inline void set() {
    digitalWrite(PIN, true);
  }
  static inline void clear() {
    digitalWrite(PIN, false);
  }
  static inline void write(bool x) {
    x ? set() : clear();
  }
  static inline void toggle() {
    write(!read());
  }
  static inline bool read() {
    return digitalRead(PIN) == HIGH;
  }
};

struct NoOutputPin;

template <typename Pin>
void setupPin() {
  Pin::setup();
}

template <>
void setupPin<NoOutputPin>() {}

template <typename Pin>
void writePin(bool b) {
  Pin::write(b);
}

template <>
void writePin<NoOutputPin>(bool b) {}

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
    setupPin<T0>();
    setupPin<T1>();
    setupPin<T2>();
    setupPin<T3>();
    setupPin<T4>();
    setupPin<T5>();
    setupPin<T6>();
    setupPin<T7>();
  }

  static void write(uint8_t x) {
    writePin<T0>(x & 1u);
    writePin<T1>(x & 2u);
    writePin<T2>(x & 4u);
    writePin<T3>(x & 8u);
    writePin<T4>(x & 16u);
    writePin<T5>(x & 32u);
    writePin<T6>(x & 64u);
    writePin<T7>(x & 128u);
  }
};

} // arduino
} // gpio
} // clacker
#endif // ARDUINO
