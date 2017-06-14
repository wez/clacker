#pragma once
#include "FreeRTOS.h"
#include "task.h"

// This function is provided by the firmware project to launch
// the tasks that will be run by the firmware.  It logically
// replaces the use of main(), setup() and loop().
// When this function returns, the scheduler will be started.
extern "C" void launchTasks(void);

namespace clacker {

TickType_t millisecondsToTicks(uint32_t ms);
void delayMilliseconds(uint32_t ms);

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
    t_ = xTaskCreateStatic(run, "", StackSize, this, Priority, stack_, &tBuf_);
#else
    xTaskCreate(run, "", StackSize, this, Priority, &t_);
#endif
  }
};
}
