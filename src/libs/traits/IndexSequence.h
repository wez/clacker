#pragma once
// Integer sequences are useful in template metaprogramming
#include <stddef.h>

namespace clacker {

template <class T, T... Ints>
struct integer_sequence {
  using value_type = T;

  static constexpr size_t size() noexcept {
    return sizeof...(Ints);
  }
};

template <size_t... Ints>
using index_sequence = clacker::integer_sequence<size_t, Ints...>;

namespace detail {
template <size_t N, size_t... Ints>
struct make_index_sequence
    : detail::make_index_sequence<N - 1, N - 1, Ints...> {};

template <size_t... Ints>
struct make_index_sequence<0, Ints...> : clacker::index_sequence<Ints...> {};
}

template <size_t N>
using make_index_sequence = detail::make_index_sequence<N>;
}
