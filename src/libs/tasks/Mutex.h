#pragma once
#include "FreeRTOS.h"
#include "semphr.h"
#include "src/libs/tasks/Result.h"
#include "src/libs/tasks/Timing.h"
namespace clacker {

// The Mutex class is used to implement mutual exclusion between
// tasks.  Only one task can own a mutex at a time.  Ownership
// of a Mutex is represented by the Mutex::Lock class.  Owning
// a mutex does not disable interrupts or task scheduling.
// Mutexes are not recursive!
class Mutex {
  SemaphoreHandle_t h_;
#if configSUPPORT_STATIC_ALLOCATION == 1
  StaticSemaphore_t buf_;
#endif

 public:
  // Construct an unowned mutex
  Mutex();
  // No copying or moving
  Mutex(const Mutex&) = delete;
  Mutex(Mutex&&) = delete;

  // A lock represents ownership of the associated mutex.
  // The lock is released when the Lock object is destroyed.
  class Lock {
    friend class Mutex;
    SemaphoreHandle_t h_;

    // Construct from an owned semaphore
    Lock(SemaphoreHandle_t h);

   public:
    // No copying
    Lock(const Lock&) = delete;
    // Moving is allowed
    Lock(Lock&&);
    Lock& operator=(Lock&& other);
    // The destructor implicitly calls unlock()
    ~Lock();
    // Unlock and release ownership of the mutex
    void unlock();
  };

  // Lock the mutex, blocking until the mutex is acquired
  Lock lock();

  // Attempt to lock the mutex with a timeout
  Result<Lock, BaseType_t> lock(uint32_t ms);

  // Attempt to lock the mutex from an ISR
  Result<Lock, BaseType_t> lockFromISR();
};

// LockedPtr is a helper class representing a pointer to a locked
// resource and its associated Lock.  While the LockedPtr is in
// scope it owns the lock.  When it falls out of scope the lock
// is also released.
// LockedPtr offers operator-> to access the wrapped and locked
// type.
template <typename T>
class LockedPtr {
  Mutex::Lock l_;
  T* t_;

 public:
  LockedPtr(Mutex::Lock&& l, T* t) : l_(move(l)), t_(t) {}
  LockedPtr(const LockedPtr&) = delete;
  LockedPtr(LockedPtr&& other) : l_(move(other.l_)), t_(other.t_) {
    other.t_ = nullptr;
  }
  LockedPtr& operator=(LockedPtr&& other) {
    if (&other != this) {
      l_.unlock();
      l_ = move(other.l_);
      t_ = other.t_;
      other.t_ = nullptr;
    }
    return *this;
  }

  T* operator->() {
    return t_;
  }

  T* operator->() const {
    return t_;
  }
};

// The Synchronized class provides a way to make it difficult to
// access a resource without acquiring ownership of a lock.
// The resource is exposed via the lock() methods which return a
// LockedPtr instance after acquiring a lock.  The lock is
// implicitly released when the result of the lock() method
// falls out of scope.
template <typename T>
class Synchronized {
  T t_;
  mutable Mutex m_;

 public:
  LockedPtr<T> lock() {
    return LockedPtr<T>(m_.lock(), &t_);
  }

  LockedPtr<T> lock() const {
    return LockedPtr<T>(m_.lock(), &t_);
  }

  Result<LockedPtr<T>, BaseType_t> lockFromISR() {
    auto l = m_.lockFromISR();
    if (l.hasError()) {
      return Result<LockedPtr<T>, BaseType_t>::Error(l.error());
    }
    return Result<LockedPtr<T>, BaseType_t>::Ok(
        LockedPtr<T>(move(l.value())), &t_);
  }

  Result<LockedPtr<T>, BaseType_t> lockFromISR() const {
    auto l = m_.lockFromISR();
    if (l.hasError()) {
      return Result<LockedPtr<T>, BaseType_t>::Error(l.error());
    }
    return Result<LockedPtr<T>, BaseType_t>::Ok(
        LockedPtr<T>(move(l.value())), &t_);
  }
};
}
