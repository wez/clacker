#pragma once
#include "src/libs/traits/Traits.h"

namespace clacker {

// A stand-in for the void type, but easier to match in templates
struct Unit {};

[[noreturn]] void panic(const char* reason);

template <typename Value, typename ErrorType>
class Result {
  enum class State { kEMPTY, kVALUE, kERROR };

  struct ErrorConstruct {};

 public:
  using value_type = Value;
  using error_type = ErrorType;

  Result() : state_(State::kEMPTY) {}
  ~Result() {
    switch (state_) {
      case State::kEMPTY:
        break;
      case State::kVALUE:
        value_.~Value();
        break;
      case State::kERROR:
        error_.~ErrorType();
        break;
    }
  }

  // Default construct a successful Value result
  inline static Result Ok() {
    return Result(Value());
  }

  // Copy in a successful Value result
  inline static Result Ok(const Value& value) {
    return Result(value);
  }

  // Move in a successful Value result
  inline static Result Ok(Value&& value) {
    return Result(move(value));
  }

  // Default construct an error result
  inline static Result Error() {
    return Result(ErrorType(), ErrorConstruct{});
  }

  // Copy in an error result
  inline static Result Error(const ErrorType& error) {
    return Result(error, ErrorConstruct{});
  }

  // Move construct an error result
  inline static Result Error(ErrorType&& error) {
    return Result(move(error), ErrorConstruct{});
  }

  // Copy a value into the result
  explicit Result(const Value& other) : state_(State::kVALUE), value_(other) {}

  // Move in value
  explicit Result(Value&& other) : state_(State::kVALUE), value_(move(other)) {}

  // Copy in error
  explicit Result(const ErrorType& error, ErrorConstruct)
      : state_(State::kERROR), error_(error) {}

  // Move in error
  explicit Result(ErrorType&& error, ErrorConstruct)
      : state_(State::kERROR), error_(move(error)) {}

  // Move construct
  explicit Result(Result&& other) noexcept : state_(other.state_) {
    switch (state_) {
      case State::kEMPTY:
        break;
      case State::kVALUE:
        // new (&value_) Value(move(other.value_));
        value_ = move(other.value_);
        break;
      case State::kERROR:
        // new (&error_) ErrorType(move(other.error_));
        error_ = move(other.error_);
        break;
    }
    other.~Result();
    other.state_ = State::kEMPTY;
  }

  // Move assign
  Result& operator=(Result&& other) noexcept {
    if (&other != this) {
      this->~Result();

      state_ = other.state_;
      switch (state_) {
        case State::kEMPTY:
          break;
        case State::kVALUE:
          // new (&value_) Value(move(other.value_));
          value_ = move(other.value_);
          break;
        case State::kERROR:
          // new (&error_) ErrorType(move(other.error_));
          error_ = move(other.error_);
          break;
      }

      other.~Result();
      other.state_ = State::kEMPTY;
    }
    return *this;
  }

  // Copy construct
  Result(const Result& other) {
    state_ = other.state_;
    switch (state_) {
      case State::kEMPTY:
        break;
      case State::kVALUE:
        value_ = other.value_;
        break;
      case State::kERROR:
        error_ = other.error_;
        break;
    }
  }

  // Copy assign
  Result& operator=(const Result& other) {
    if (&other != this) {
      this->~Result();
      state_ = other.state_;
      switch (state_) {
        case State::kEMPTY:
          break;
        case State::kVALUE:
          value_ = other.value_;
          break;
        case State::kERROR:
          error_ = other.error_;
          break;
      }
    }
    return *this;
  }

  bool hasValue() const {
    return state_ == State::kVALUE;
  }

  bool hasError() const {
    return state_ == State::kERROR;
  }

  bool empty() const {
    return state_ == State::kEMPTY;
  }

  // If Result does not contain a valid Value, panic
  void panicIfError() const {
    switch (state_) {
      case State::kVALUE:
        return;
      case State::kEMPTY:
        panic("Uninitialized Result");
      case State::kERROR:
        panic("Result holds Error, not Value");
    }
  }

  // Get a mutable reference to the value.  If the value is
  // not assigned, a panic will be issued by panicIfError().
  Value& value() & {
    panicIfError();
    return value_;
  }

  // Get an rvalue reference to the value.  If the value is
  // not assigned, a panic will be issued by panicIfError().
  Value&& value() && {
    panicIfError();
    return value_;
  }

  // Get a const reference to the value.  If the value is
  // not assigned, a panic will be issued by panicIfError().
  const Value& value() const & {
    panicIfError();
    return value_;
  }

  // Throws a logic exception if the result does not contain an Error
  void panicIfNotError() {
    switch (state_) {
      case State::kVALUE:
        panic("Result holds Value, not Error");
      case State::kEMPTY:
        panic("Uninitialized Result");
      case State::kERROR:
        return;
    }
  }

  // Get a mutable reference to the error.  If the error is
  // not assigned, a panic will be issued by panicIfNotError().
  ErrorType& error() & {
    panicIfNotError();
    return error_;
  }

  // Get an rvalue reference to the error.  If the error is
  // not assigned, a panic will be issued by panicIfNotError().
  ErrorType&& error() && {
    panicIfNotError();
    return error_;
  }

  // Get a const reference to the error.  If the error is
  // not assigned, a panic will be issued by panicIfNotError().
  const ErrorType& error() const & {
    panicIfNotError();
    return error_;
  }

 private:
  State state_;
  union {
    Value value_;
    ErrorType error_;
  };
};
}
