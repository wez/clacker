#pragma once
#include "FreeRTOS.h"
#include "src/libs/tasks/Result.h"
#include "src/libs/tasks/Timing.h"
#include "task.h"

// This function is provided by the firmware project to launch
// the tasks that will be run by the firmware.  It logically
// replaces the use of main(), setup() and loop().
// When this function returns, the scheduler will be started.
extern "C" void launchTasks(void);

namespace clacker {

// A Critical section disables interrupts while it is in scope.
// CriticalSections must not nest.
// FreeRTOS APIs must not be called from within a CriticalSection.
struct CriticalSection {
  CriticalSection() {
    taskENTER_CRITICAL();
  }
  ~CriticalSection() {
    taskEXIT_CRITICAL();
  }

  CriticalSection(const CriticalSection&) = delete;
  CriticalSection(CriticalSection&&) = delete;
};

// While an instance of SuspendScheduler is in scope, the RTOS
// task scheduler is suspended.  Interrupts are still enabled!
// SuspendScheduler may be nested.
// API calls that may cause a context switch must not be called
// while the scheduler is suspended.
struct SuspendScheduler {
  SuspendScheduler() {
    vTaskSuspendAll();
  }
  ~SuspendScheduler() {
    xTaskResumeAll();
  }
  SuspendScheduler(const SuspendScheduler&) = delete;
  SuspendScheduler(SuspendScheduler&&) = delete;
};

template <
    class Derived,
    uint32_t StackSize = configMINIMAL_STACK_SIZE,
    uint8_t Priority = 2>
class Task {
  TaskHandle_t t_;
#if configSUPPORT_STATIC_ALLOCATION == 1
  StaticTask_t tBuf_;
  StackType_t stack_[StackSize];
#endif

  static void runTask(void* self_p) {
    auto self = static_cast<Derived*>(self_p);
    self->run();
  }

 public:
  Task() {}
  Task(const Task&) = delete;
  Task(Task&&) = delete;

  freertos::BoolResult start() {
#if configSUPPORT_STATIC_ALLOCATION == 1
    t_ = xTaskCreateStatic(
        runTask, "", StackSize, this, Priority, stack_, &tBuf_);
    return freertos::BoolResult::Ok();
#else
    return freertos::boolResult(
        xTaskCreate(runTask, "", StackSize, this, Priority, &t_));
#endif
  }

#ifdef INCLUDE_xTaskAbortDelay
  bool abortDelay() {
    return xTaskAbortDelay(t_);
  }
#endif

  const TaskHandle_t handle() const {
    return t_;
  }
};
}
