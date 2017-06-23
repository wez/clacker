#pragma once
#include "src/libs/traits/SmallestInteger.h"
#ifdef __AVR__
#include <avr/interrupt.h>
#endif
namespace clacker {
namespace avr {

enum class ClockSource : uint8_t {
  None,
  Prescale1,
  Prescale8,
  Prescale64,
  Prescale256,
  Prescale1024,
  ExternalFalling,
  ExternalRising,
};

enum class WaveformGenerationMode : uint8_t {
  Normal,
  PwmPhaseCorrect,
  ClearOnTimerMatchOutputCompare,
  FastPwm,
#ifdef WGM02
  PwmPhaseCorrectOutputCompare,
  FastPwmOutputCompare,
#endif
};

struct Timer0 {
  static void setup(WaveformGenerationMode mode, ClockSource source) {
    uint8_t a = 0;
    uint8_t b = 0;
    switch (mode) {
      case WaveformGenerationMode::Normal:
        a = 0;
        b = 0;
        break;
      case WaveformGenerationMode::PwmPhaseCorrect:
        a = _BV(WGM00);
        b = 0;
        break;
      case WaveformGenerationMode::ClearOnTimerMatchOutputCompare:
        a = 0;
        b = _BV(WGM01);
        break;
      case WaveformGenerationMode::FastPwm:
        a = _BV(WGM00);
        b = _BV(WGM01);
        break;
#ifdef WGM02
      case WaveformGenerationMode::PwmPhaseCorrectOutputCompare:
        a = _BV(WGM00);
        b = _BV(WGM02);
        break;
      case WaveformGenerationMode::FastPwmOutputCompare:
        a = _BV(WGM00);
        b = _BV(WGM02) | _BV(WGM01);
        break;
#endif
    }

    switch (source) {
      case ClockSource::None:
        break;
      case ClockSource::Prescale1:
        b |= 0 | 0 | _BV(CS00);
        break;
      case ClockSource::Prescale8:
        b |= 0 | _BV(CS01) | 0;
        break;
      case ClockSource::Prescale64:
        b |= 0 | _BV(CS01) | _BV(CS00);
        break;
      case ClockSource::Prescale256:
        b |= _BV(CS02) | 0 | 0;
        break;
      case ClockSource::Prescale1024:
        b |= _BV(CS02) | 0 | _BV(CS00);
        break;
      case ClockSource::ExternalFalling:
        b |= _BV(CS02) | _BV(CS01) | 0;
        break;
      case ClockSource::ExternalRising:
        b |= _BV(CS02) | _BV(CS01) | _BV(CS00);
        break;
    }

#ifdef TCCR0A
    TCCR0A = a;
    TCCR0B = b;
#elif defined(TCCR0)
    TCCR0 = a | b;
#endif

    // Reset counter to zero
    counter() = 0;
  }

  static void
  setup(WaveformGenerationMode mode, ClockSource source, uint8_t compare) {
    setup(mode, source);

    // Set the match
    outputCompareRegister() = compare;
    enableCompareInterrupt();
  }

  static inline void enableCompareInterrupt() {
#ifdef TIMSK0
    TIMSK0 |= _BV(OCIE0A);
#else
    TIMSK |= _BV(OCIE0);
#endif
  }

  static inline void disableCompareInterrupt() {
#ifdef TIMSK0
    TIMSK0 &= ~_BV(OCIE0A);
#else
    TIMSK &= ~_BV(OCIE0);
#endif
  }

  using resolution_t = uint8_t;
  static inline volatile uint8_t& counter() {
    return TCNT0;
  }

  static inline volatile uint8_t& outputCompareRegister() {
#ifdef OCR0A
    return OCR0A;
#else
    return OCR0;
#endif
  }
};

struct Timer1 {
  static void setup(WaveformGenerationMode mode, ClockSource source) {
    uint8_t a = 0;
    uint8_t b = 0;

    // Note that Timer1 supports more modes than those handled here,
    // but I don't yet have need to use them
    switch (mode) {
      case WaveformGenerationMode::Normal:
        a = 0;
        b = 0;
        break;
      case WaveformGenerationMode::PwmPhaseCorrect:
        a = _BV(WGM10);
        b = 0;
        break;
      case WaveformGenerationMode::ClearOnTimerMatchOutputCompare:
        a = 0;
        b = _BV(WGM12);
        break;
      case WaveformGenerationMode::FastPwm:
        a = _BV(WGM10);
        b = _BV(WGM12);
        break;
#ifdef WGM02
      case WaveformGenerationMode::PwmPhaseCorrectOutputCompare:
        a = _BV(WGM11) | _BV(WGM10);
        b = _BV(WGM13);
        break;
      case WaveformGenerationMode::FastPwmOutputCompare:
        a = _BV(WGM11) | _BV(WGM10);
        b = _BV(WGM12) | _BV(WGM13);
        break;
#endif
    }

    switch (source) {
      case ClockSource::None:
        break;
      case ClockSource::Prescale1:
        b |= 0 | 0 | _BV(CS10);
        break;
      case ClockSource::Prescale8:
        b |= 0 | _BV(CS11) | 0;
        break;
      case ClockSource::Prescale64:
        b |= 0 | _BV(CS11) | _BV(CS10);
        break;
      case ClockSource::Prescale256:
        b |= _BV(CS12) | 0 | 0;
        break;
      case ClockSource::Prescale1024:
        b |= _BV(CS12) | 0 | _BV(CS10);
        break;
      case ClockSource::ExternalFalling:
        b |= _BV(CS12) | _BV(CS11) | 0;
        break;
      case ClockSource::ExternalRising:
        b |= _BV(CS12) | _BV(CS11) | _BV(CS10);
        break;
    }

    TCCR1A = a;
    TCCR1B = b;

    // Reset counter to zero
    counter() = 0;
  }

  static void
  setup(WaveformGenerationMode mode, ClockSource source, uint16_t compare) {
    setup(mode, source);

    // Set the match
    outputCompareRegister() = compare;
    enableCompareInterrupt();
  }

  static inline void enableCompareInterrupt() {
#ifdef TIMSK1
    TIMSK1 |= _BV(OCIE1A);
#else
    TIMSK |= _BV(OCIE1A);
#endif
  }

  static inline void disableCompareInterrupt() {
#ifdef TIMSK1
    TIMSK1 &= ~_BV(OCIE1A);
#else
    TIMSK &= ~_BV(OCIE1A);
#endif
  }

  using resolution_t = uint16_t;

  static inline volatile uint16_t& counter() {
    return TCNT1;
  }

  static inline volatile uint16_t& outputCompareRegister() {
    return OCR1A;
  }
};

struct TimerConfiguration {
  ClockSource source;
  uint32_t compare;
};

template <typename Timer>
TimerConfiguration computeTimerConfig(uint32_t frequency) {
  // Compute parameters such that the timer will trigger its
  // ISR at a rate to match the provided frequency.  We do
  // this by computing the smallest compare value that fits
  // in the timer resolution.
  uint32_t counterLimit =
      numeric_traits<typename Timer::resolution_t>::maximum();

  ClockSource source = ClockSource::Prescale1;
  uint32_t compare = (F_CPU / frequency) - 1;

  if (compare > counterLimit) {
    source = ClockSource::Prescale8;
    compare = ((F_CPU / frequency) / 8) - 1;

    if (compare > counterLimit) {
      source = ClockSource::Prescale64;
      compare = ((F_CPU / frequency) / 64) - 1;

      if (compare > counterLimit) {
        source = ClockSource::Prescale256;
        compare = ((F_CPU / frequency) / 256) - 1;

        if (compare > counterLimit) {
          source = ClockSource::Prescale1024;
          compare = ((F_CPU / frequency) / 1024) - 1;
        }
      }
    }
  }

  return TimerConfiguration{source, compare};
}

template <typename Timer>
void setupTimer(uint32_t frequency) {
  auto config = computeTimerConfig<Timer>(frequency);
  Timer::setup(
      WaveformGenerationMode::ClearOnTimerMatchOutputCompare,
      config.source,
      static_cast<typename Timer::resolution_t>(config.compare));
}
}
}
