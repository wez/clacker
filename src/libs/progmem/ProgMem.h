#pragma once
#include "src/libs/traits/Traits.h"

#ifdef __AVR__
#include <avr/pgmspace.h>
#else
#include <stdlib.h>
#include <string.h>
#endif

namespace clacker {

// Returns a copy of T from the specified progMem location
template <typename T>
typename enable_if<sizeof(T) == 1, T>::type progMemLoad(const T* p) {
#ifdef __AVR__
  return reinterpret_cast<T>(pgm_read_byte(p));
#else
  return reinterpret_cast<T>(*p);
#endif
}

// Populates a T into result, copying it from the specified progMem location
template <typename T>
void progMemLoad(
    const T* p,
    typename enable_if<sizeof(T) == 1, T>::type& result) {
#ifdef __AVR__
  result = reinterpret_cast<T>(pgm_read_byte(p));
#else
  result = reinterpret_cast<T>(*p);
#endif
}

// Returns a copy of T from the specified progMem location
template <typename T>
typename enable_if<(sizeof(T) > 1), T>::type progMemLoad(const T* p) {
  T result;
#ifdef __AVR__
  memcpy_P(&result, p, sizeof(T));
#else
  memcpy(&result, p, sizeof(T));
#endif
  return result;
}

// Populates a T into result, copying it from the specified progMem location
template <typename T>
void progMemLoad(
    const T* p,
    typename enable_if<(sizeof(T) > 1), T>::type& result) {
#ifdef __AVR__
  memcpy_P(&result, p, sizeof(T));
#else
  memcpy(&result, p, sizeof(T));
#endif
}

// An iterator that knows how to deref progmem data
template <typename T>
class ProgMemIter {
  const T* p_;

 public:
  constexpr ProgMemIter() : p_(0) {}
  constexpr ProgMemIter(const T* p) : p_(p) {}

#ifdef __AVR__
  T operator*() const {
    return progMemLoad(p_);
  }
#else
  constexpr T operator*() const {
    return *p_;
  }
#endif

  ProgMemIter& operator=(const ProgMemIter&) = default;

  ProgMemIter& operator++() {
    ++p_;
    return *this;
  }

  constexpr ProgMemIter operator++(int)const {
    return ProgMemIter(p_ + 1);
  }

  ProgMemIter& operator--() {
    --p_;
    return *this;
  }

  constexpr ProgMemIter operator--(int)const {
    return ProgMemIter(p_ - 1);
  }

  ProgMemIter& operator+=(size_t n) {
    p_ += n;
    return *this;
  }

  ProgMemIter& operator-=(size_t n) {
    p_ -= n;
    return *this;
  }

  constexpr ProgMemIter operator+(size_t n) const {
    return ProgMemIter(p_ + n);
  }

  constexpr ProgMemIter operator-(size_t n) const {
    return ProgMemIter(p_ - n);
  }

  constexpr bool operator==(const ProgMemIter& other) const {
    return p_ == other.p_;
  }

  constexpr bool operator!=(const ProgMemIter& other) const {
    return p_ != other.p_;
  }

  constexpr size_t operator-(const ProgMemIter& other) const {
    return p_ - other.p_;
  }
};

template <typename T>
ProgMemIter<T> makeProgMemIter(const T* ptr) {
  return ProgMemIter<T>(ptr);
}

// These are instantiated in pointers.cpp to avoid inlining
// common pointer types and bloating the code
extern template class ProgMemIter<void*>;
extern template class ProgMemIter<char*>;
}
