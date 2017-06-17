#pragma once
// This header defines functions for working with strings.
// The main user facing exports from this header file are:
//
// makeFixedString("foo") - return a mutable string holding foo
// FixedString<32> foo; - a string with specified capacity
// makeConstString("foo") - return immutable string holding foo
//
// None of the methods or classes in this file perform any dynamic
// memory allocation.
#include <string.h>
#include "src/libs/progmem/ProgMem.h"
#include "src/libs/traits/Copy.h"
#include "src/libs/traits/IndexSequence.h"
#include "src/libs/traits/SmallestInteger.h"
#include "src/libs/traits/Traits.h"
namespace clacker {

// Compare two strings using iterators.
// Returns -1 if Left < Right, 0 if Left == Right, 1 if Left > Right
template <class LeftIter, class RightIter>
int compareSequences(
    LeftIter left,
    LeftIter leftEnd,
    RightIter right,
    RightIter rightEnd) {
  // We treat the elements as unsigned for comparison purposes
  using UInt = typename numeric_traits<typename remove_cv<
      typename remove_reference<decltype(*left)>::type>::type>::unsigned_type;

  while (left != leftEnd && right != rightEnd) {
    // Only de-ref once, as the ProgMemIter needs to do extra
    // work to load the data from flash
    auto l = UInt(*left);
    auto r = UInt(*right);
    if (l < r) {
      return -1;
    }
    if (l > r) {
      return 1;
    }
    ++left;
    ++right;
  }

  auto l = left == leftEnd ? 0u : UInt(*left);
  auto r = right == rightEnd ? 0u : UInt(*right);

  return l - r;
}

// A common base for string types; it doesn't know about the storage and
// delegates begin(), end() and size() to the Derived type to provide
// those methods.  Look at MutableString and ProgMemString for examples
// of using this base class.
// The base provides common methods for comparing derived instances;
// for example, the operators on this base class allow comparing
// MutableString and ProgMemString instances for equality.
template <class Derived, class Char, class ConstIterator>
class StringBase {
 public:
  using const_iterator = ConstIterator;

  const_iterator begin() const {
    return static_cast<const Derived*>(this)->begin();
  }

  const_iterator end() const {
    return static_cast<const Derived*>(this)->end();
  }

  size_t size() const {
    return static_cast<const Derived*>(this)->size();
  }

  template <typename OtherDerived, typename OtherIter>
  bool operator==(
      const StringBase<OtherDerived, Char, OtherIter>& other) const {
    return compareSequences(begin(), end(), other.begin(), other.end()) == 0;
  }

  bool operator==(const Char* other) const {
    return compareSequences(begin(), end(), other, other + ::strlen(other)) ==
        0;
  }

  template <typename OtherDerived, typename OtherIter>
  bool operator!=(
      const StringBase<OtherDerived, Char, OtherIter>& other) const {
    return compareSequences(begin(), end(), other.begin(), other.end()) != 0;
  }

  bool operator!=(const Char* other) const {
    return compareSequences(begin(), end(), other, other + ::strlen(other)) !=
        0;
  }
};

// MutableString provides the implementation for runtime constructed
// and mutated strings.  It has a fixed storage capacity.  Overflowing
// the capacity is a soft failure; the string is filled until it is
// truncated, and subsequent append operations will fail (return false).
template <size_t Size, class Char>
class MutableString
    : public StringBase<MutableString<Size, Char>, Char, const Char*> {
  Char data_[Size + 1u];
  size_t size_;

  // The template stuff in here expands to initializing the elements of
  // the storage and adding a null terminator at the end
  template <size_t M, size_t... Is>
  MutableString(const Char (&literal)[M], size_t count, index_sequence<Is...>)
      : data_{(Is < count ? literal[Is] : Char(0))..., Char(0)}, size_{count} {}

 public:
  using iterator = Char*;
  using const_iterator = const Char*;

  MutableString() : data_{}, size_{} {}

  // Initialize from a string literal
  // The template stuff in here expands to initializing the elements of
  // the storage and adding a null terminator at the end
  template <size_t M>
  MutableString(const Char (&literal)[M])
      : MutableString{literal, M - 1u, make_index_sequence<M - 1u>{}} {
    static_assert(M - 1 <= Size, "literal too large to fit in MutableString");
  }

  iterator begin() {
    return data_;
  }
  iterator end() {
    return data_ + size_;
  }
  const_iterator begin() const {
    return data_;
  }
  const_iterator end() const {
    return data_ + size_;
  }
  size_t size() const {
    return size_;
  }
  constexpr size_t capacity() const {
    return Size;
  }

  const Char* data() const {
    return data_;
  }
  const Char* c_str() const {
    return data_;
  }

  // Append len bytes of data from src.
  // Returns true if all of the data was copied, false
  // if it was too large.  If the data cannot fit, then
  // as much of the data as can fit will be appended.
  bool append(const Char* src, size_t len) {
    const auto avail = Size - size_;
    const auto toCopy = avail < len ? avail : len;
    if (toCopy > 0) {
      ::memcpy(data_ + size_, src, toCopy);
      size_ += toCopy;
      data_[size_] = 0;
    }
    return toCopy == len;
  }

  template <class InputIt>
  bool append(InputIt first, size_t len) {
    const auto avail = Size - size_;
    const auto toCopy = avail < len ? avail : len;
    if (toCopy > 0) {
      copy_n(first, toCopy, data_ + size_);
      size_ += toCopy;
      data_[size_] = 0;
    }
    return toCopy == len;
  }

  template <class InputIt>
  bool append(InputIt first, InputIt last) {
    return append(first, last - first);
  }

  bool append(const Char* cstr) {
    return append(cstr, ::strlen(cstr));
  }

  template <typename Stringy>
  bool append(const Stringy& other) {
    return append(other.begin(), other.end());
  }
};

// ProgMemString bridges StringBase <-> ProgMemIter and allows working
// with strings that are stored in program memory rather than in the
// main heap space of the program.  On non-AVR systems, this devolves
// to a const string pointer.
template <size_t Size, class Char>
class ProgMemString
    : public StringBase<ProgMemString<Size, Char>, Char, ProgMemIter<Char>> {
  ProgMemIter<Char> data_;

 public:
  using const_iterator = ProgMemIter<Char>;

  ProgMemString(const_iterator data) : data_(data) {}

  const_iterator begin() const {
    return data_;
  }
  const_iterator end() const {
    return data_ + Size;
  }
  constexpr size_t size() const {
    return Size;
  }
};

// FixedString is a convenience for working with mutable byte strings
// with a fixed storage capacity.
template <size_t Size>
using FixedString = MutableString<Size, char>;

// Helper to instantiate a FixedString that is just large enough to
// contain the string literal parameter
template <class Char, size_t Size>
constexpr FixedString<Size - 1u> makeFixedString(const Char (&a)[Size]) {
  return {a};
}
}

#ifdef PROGMEM
#define __CLACKER_PROGMEM PROGMEM
#else
#define __CLACKER_PROGMEM /* nothing */
#endif

// makeConstString("foo") returns an instance of ProgMemString that
// contains "foo".  It is a macro because AVR systems prefer to place
// the string contents in program memory; we need to perform some
// preprocessor gymnastics to declare the static storage required
// for this to work.
#define makeConstString(literal)                             \
  ::clacker::ProgMemString<sizeof(literal) - 1, char>([] {   \
    static const char _data[] __CLACKER_PROGMEM = (literal); \
    return ::clacker::makeProgMemIter(_data);                \
  }())
