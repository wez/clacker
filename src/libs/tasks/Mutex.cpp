#include "src/libs/tasks/Mutex.h"
namespace clacker {
Mutex::Mutex() {
#if configSUPPORT_STATIC_ALLOCATION == 1
  h_ = xSemaphoreCreateMutexStatic(&buf_);
#else
  if (xSemaphoreCreateMutex() == nullptr) {
    panic(makeConstString("OOM xSemaphoreCreateMutexStatic"));
  }
#endif
}

Mutex::Lock::Lock(SemaphoreHandle_t h) : h_(h) {}
Mutex::Lock::~Lock() {
  unlock();
}

Mutex::Lock::Lock(Lock&& other) : h_(other.h_) {
  other.h_ = nullptr;
}

void Mutex::Lock::unlock() {
  if (h_) {
    xSemaphoreGive(h_);
    h_ = nullptr;
  }
}
Mutex::Lock Mutex::lock() {
  xSemaphoreTake(h_, portMAX_DELAY);
  return Lock(h_);
}

Mutex::Lock& Mutex::Lock::operator=(Mutex::Lock&& other) {
  if (&other != this) {
    unlock();
    h_ = other.h_;
    other.h_ = nullptr;
  }
  return *this;
}

Result<Mutex::Lock, BaseType_t> Mutex::lock(uint32_t ms) {
  auto res = xSemaphoreTake(h_, millisecondsToTicks(ms));
  if (res == true) {
    return Result<Lock, BaseType_t>::Ok(Lock(h_));
  }
  return Result<Lock, BaseType_t>::Error(false);
}

Result<Mutex::Lock, BaseType_t> Mutex::lockFromISR() {
  auto res = xSemaphoreTakeFromISR(h_, nullptr);
  if (res == true) {
    return Result<Lock, BaseType_t>::Ok(Lock(h_));
  }
  return Result<Lock, BaseType_t>::Error(false);
}
}
