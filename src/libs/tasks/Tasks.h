#pragma once
#include "FreeRTOS.h"
#include "task.h"

namespace clacker {

template <uint32_t StackSize = configMINIMAL_STACK_SIZE, uint8_t Priority = 2>
class Task {
  using Func = void (*)();
  TaskHandle_t t_;
  Func f_;
#ifdef configSUPPORT_STATIC_ALLOCATION
  StaticTask_t tBuf_;
  uint8_t stack_[StackSize];
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
#ifdef configSUPPORT_STATIC_ALLOCATION
    t_ = xTaskCreateStatic(
        run,
        0,
        sizeof(stack_),
        this,
        Priority,
        reinterpret_cast<StackType_t*>(stack_),
        &tBuf_);
#else
    xTaskCreate(run, 0, StackSize, this, Priority, &t_);
#endif
  }
};
}
