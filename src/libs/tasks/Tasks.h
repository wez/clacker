#pragma once
#include "FreeRTOS.h"
#include "task.h"

namespace clacker {

TickType_t millisecondsToTicks(uint32_t ms) {
#ifdef ms2tick
  // The NRF52 port provides this macro
  return ms2tick(ms);
#else
  // Otherwise, just use a simple integer division
  return ms / portTICK_PERIOD_MS;
#endif
}

void delayMilliseconds(uint32_t ms) {
  vTaskDelay(millisecondsToTicks(ms));
}

template <uint32_t StackSize = configMINIMAL_STACK_SIZE, uint8_t Priority = 2>
class Task {
  using Func = void (*)();
  TaskHandle_t t_;
  Func f_;
#if configSUPPORT_STATIC_ALLOCATION == 1
  StaticTask_t tBuf_;
  StackType_t stack_[StackSize];
#endif

  static void run(void* self_p) {
    Task* self = reinterpret_cast<Task*>(self_p);
    self->f_();
  }

 public:
  Task(Func func) : f_(func) {}
  Task(const Task&) = delete;
  Task(Task&&) = delete;

  void start() {
#if configSUPPORT_STATIC_ALLOCATION == 1
    t_ = xTaskCreateStatic(run, 0, StackSize, this, Priority, stack_, &tBuf_);
#else
    xTaskCreate(run, 0, StackSize, this, Priority, &t_);
#endif
  }
};
}
