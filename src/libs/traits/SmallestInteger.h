#pragma once
namespace clacker {
// A little bit of compile time magic to determine the smallest
// integer width suitable to hold a given number of bits.
// http://stackoverflow.com/a/9095432/149111
template <unsigned int N>
struct smallest_integer_bits {
  using type = typename smallest_integer_bits<N - 1>::type;
};

template <>
struct smallest_integer_bits<0> {
  using type = uint8_t;
};
template <>
struct smallest_integer_bits<8> {
  using type = uint16_t;
};
template <>
struct smallest_integer_bits<16> {
  using type = uint32_t;
};
template <>
struct smallest_integer_bits<32> {
  using type = uint64_t;
};

template <typename T>
struct numeric_traits;

template <>
struct numeric_traits<uint8_t> {
  static constexpr uint8_t min() {
    return 0;
  }
  static constexpr uint8_t max() {
    return (1 << 8) - 1;
  }
};

template <>
struct numeric_traits<uint16_t> {
  static constexpr uint16_t min() {
    return 0;
  }
  static constexpr uint16_t max() {
    return (1 << 16) - 1;
  }
};

template <>
struct numeric_traits<uint32_t> {
  static constexpr uint32_t min() {
    return 0;
  }
  static constexpr uint32_t max() {
    return (1 << 32) - 1;
  }
};

template <>
struct numeric_traits<uint64_t> {
  static constexpr uint64_t min() {
    return 0;
  }
  static constexpr uint64_t max() {
    return (1 << 64) - 1;
  }
};

// smallest_integer_max<123U>::type evalutes to uint8_t; the smallest integer
// type that can hold the unsigned integer template parameter.
template <unsigned int N>
struct smallest_integer_max {
  using type = typename conditional<
      (N <= numeric_traits<uint8_t>::max()),
      uint8_t,
      typename conditional<
          (N <= numeric_traits<uint16_t>::max()),
          uint16_t,
          typename conditional<
              (N <= numeric_traits<uint32_t>::max()),
              uint32_t,
              uint64_t>::type>::type>::type;
};
}
