#pragma once
namespace clacker {

template <class T>
struct remove_reference {
  typedef T type;
};
template <class T>
struct remove_reference<T&> {
  typedef T type;
};
template <class T>
struct remove_reference<T&&> {
  typedef T type;
};

template <class T>
typename remove_reference<T>::type&& move(T&& t) {
  return static_cast<typename remove_reference<T>::type>(t);
}

template <bool Condition, class IfTrue, class IfFalse>
struct conditional {
  using type = IfTrue;
};

template <class IfTrue, class IfFalse>
struct conditional<false, IfTrue, IfFalse> {
  using type = IfFalse;
};

template <bool B, class T = void>
struct enable_if {};

template <class T>
struct enable_if<true, T> {
  using type = T;
};
}
