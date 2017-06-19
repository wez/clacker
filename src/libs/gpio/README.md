# GPIO helpers

There are three types exported for each of the supported systems:

## InputPin

This type represents one of the GPIO pins configured for input.
The following static methods are provided:

```
template <..., bool PULLUP = false>
struct InputPin {
  // Configures the pin for input mode.
  // If the PULLUP template parameter is set, the internal
  // pullup resistor is enabled.
  static void setup();

  // Read the pin, return true for logic high, false for logic low
  static bool read();
};

// Example usage
using Button = avr::InputPin<avr::PortB, 1>;
void setup() {
  Button::setup();
}
void loop() {
  if (Button::read()) {
    // Button is pressed; do something
  }
}
```

## OutputPin

This type represents one of the GPIO pins configured for output.
The following static methods are provided:

```
template <...>
struct OutputPin {
  // Configures the pin for output mode
  static inline void setup();

  // Set the pin to logic high
  static inline void set();

  // Set the pin to logic low
  static inline void clear();

  // If x is true, set the pin to logic high, else logic low
  static inline void write(bool x);

  // Toggle the state of the pin from high <-> low
  static inline void toggle();

  // Read the state of the pin; returns true if the pin is set
  // logic high.
  static inline bool read();
};

// Example usage
using Led = arduino::OutputPin<13>;
void setup() {
  Led::setup();
}
void loop() {
  Led::toggle();
}
```

## OutputPins

This type is used to group up to 8 pins such that writing a bitmask
to the group is dispatched to the listed pins.  On some platforms
this can be optimized to a single write operation per underlying
GPIO port.

```
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
  // Configure the pins for output
  static void setup();

  // Set the pins to high/low depending on the bits set in x.
  // The LSB of x corresponds to the T0 pin.
  // T1 is the next bit and so on.
  // x == 0 means all pins are set to low.
  // x == 1 means that T0 is set to high, the rest are set low.
  // x == 2 means that T1 is set to high, the rest are set low.
  // x == 3 means that T0, T1 are high, the rest low.
  static void write(uint8_t x);
};

// Example usage
using Pin1 = arduino::OutputPin<1>;
using Pin2 = arduino::OutputPin<2>;
using Pin3 = arduino::OutputPin<3>;
using RowPins = arduino::OutputPins<Pin1, Pin2, Pin3>;

void setup() {
  RowPins::setup();

  // This sets Pins 1 and 2 to high, and Pin 3 to low
  RowPins::write(0b011);
}
```
