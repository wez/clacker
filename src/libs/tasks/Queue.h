#pragma once
#include "FreeRTOS.h"
#include "semphr.h"
#include "src/libs/tasks/Result.h"
#include "src/libs/tasks/Timing.h"

namespace clacker {

template <typename T, uint8_t Size>
class Queue {
  QueueHandle_t h_;
#if configSUPPORT_STATIC_ALLOCATION == 1
  T buffer_[Size];
  StaticQueue_t q_;
#endif

 public:
  Queue() {
#if configSUPPORT_STATIC_ALLOCATION == 1
    h_ = xQueueCreateStatic(
        Size, sizeof(T), reinterpret_cast<uint8_t*>(buffer_), &q_);
#else
    h_ = xQueueCreate(Size, sizeof(T));
    if (!h_) {
      panic(makeConstString("OOM in xQueueCreate"));
    }
#endif
  }

  Queue(const Queue&) = delete;
  Queue(Queue&&) = delete;

  freertos::BoolResult send(const T& item) {
    return freertos::boolResult(xQueueSendToBack(
        h_, reinterpret_cast<const void*>(&item), portMAX_DELAY));
  }

  freertos::BoolResult send(const T& item, uint32_t timeoutms) {
    return freertos::boolResult(xQueueSendToBack(
        h_,
        reinterpret_cast<const void*>(&item),
        millisecondsToTicks(timeoutms)));
  }

  freertos::BoolResult recv(T& item, uint32_t timeoutms) {
    return freertos::boolResult(xQueueReceive(
        h_, reinterpret_cast<void*>(&item), millisecondsToTicks(timeoutms)));
  }

  freertos::BoolResult recv(T& item) {
    return freertos::boolResult(
        xQueueReceive(h_, reinterpret_cast<void*>(&item), portMAX_DELAY));
  }

  freertos::BoolResult sendFromISR(
      const T& item,
      BaseType_t* needsContextSwitch) {
    return freertos::boolResult(xQueueSendToBackFromISR(
        h_, reinterpret_cast<const void*>(&item), needsContextSwitch));
  }

  freertos::BoolResult recvFromISR(T& item, BaseType_t* needsContextSwitch) {
    return freertos::boolResult(xQueueReceiveFromISR(
        h_, reinterpret_cast<void*>(&item), needsContextSwitch));
  }
};
}
