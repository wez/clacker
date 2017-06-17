#pragma once
namespace clacker {
// A little bit of compile time magic to determinimume the smallest
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
struct numeric_traits<int8_t> {
  using unsigned_type = uint8_t;
  using signed_type = int8_t;

  static constexpr int8_t minimum() {
    return -maximum();
  }
  static constexpr int8_t maximum() {
    return (1u << 7) - 1u;
  }
};

template <>
struct numeric_traits<char> {
  using unsigned_type = unsigned char;
  using signed_type = char;

  static constexpr char minimum() {
    return -maximum();
  }
  static constexpr char maximum() {
    return (1u << 7) - 1u;
  }
};

template <>
struct numeric_traits<int16_t> {
  using unsigned_type = uint16_t;
  using signed_type = int16_t;

  static constexpr int16_t minimum() {
    return -maximum();
  }
  static constexpr uint16_t maximum() {
    return (1u << 15) - 1u;
  }
};

template <>
struct numeric_traits<int32_t> {
  using unsigned_type = uint32_t;
  using signed_type = int32_t;

  static constexpr int32_t minimum() {
    return -maximum();
  }
  static constexpr uint32_t maximum() {
    return (1u << 31) - 1u;
  }
};

template <>
struct numeric_traits<int64_t> {
  using unsigned_type = uint64_t;
  using signed_type = int64_t;

  static constexpr int64_t minimum() {
    return -maximum();
  }
  static constexpr int64_t maximum() {
    return (1ull << 63) - 1u;
  }
};

template <>
struct numeric_traits<uint8_t> {
  using unsigned_type = uint8_t;
  using signed_type = int8_t;

  static constexpr uint8_t minimum() {
    return 0u;
  }
  static constexpr uint8_t maximum() {
    return 0xffu;
  }
};

template <>
struct numeric_traits<uint16_t> {
  using unsigned_type = uint16_t;
  using signed_type = int16_t;

  static constexpr uint16_t minimum() {
    return 0u;
  }
  static constexpr uint16_t maximum() {
    return 0xffffu;
  }
};

template <>
struct numeric_traits<uint32_t> {
  using unsigned_type = uint32_t;
  using signed_type = int32_t;

  static constexpr uint32_t minimum() {
    return 0u;
  }
  static constexpr uint32_t maximum() {
    return 0xffffffffu;
  }
};

template <>
struct numeric_traits<uint64_t> {
  using unsigned_type = uint64_t;
  using signed_type = int64_t;

  static constexpr uint64_t minimum() {
    return 0u;
  }
  static constexpr uint64_t maximum() {
    return 0xffffffffffffffffu;
  }
};

// smallest_integer_maximum<123U>::type evalutes to uint8_t; the smallest
// integer
// type that can hold the unsigned integer template parameter.
template <unsigned int N>
struct smallest_integer_maximum {
  using type = typename conditional<
      (N <= numeric_traits<uint8_t>::maximum()),
      uint8_t,
      typename conditional<
          (N <= numeric_traits<uint16_t>::maximum()),
          uint16_t,
          typename conditional<
              (N <= numeric_traits<uint32_t>::maximum()),
              uint32_t,
              uint64_t>::type>::type>::type;
};
}
