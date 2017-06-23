#include "FreeRTOS.h"
#if configUSE_TICKLESS_IDLE != 0

#ifdef __AVR__

#if portTICK_USES_WDT
// We don't know how to count the passage of time
#error disable TICKLESS IDLE on this system
#endif

#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include "src/libs/timer/Timer.h"
#include "task.h"
#endif

void vApplicationSleep(TickType_t xExpectedIdleTime) __attribute__((weak));
void vApplicationSleep(TickType_t xExpectedIdleTime) {
#ifdef __AVR__
  portENTER_CRITICAL();
  auto status = eTaskConfirmSleepModeStatus();

  if (status == eAbortSleep) {
    // Raced with some other action that prevents sleeping
    portEXIT_CRITICAL();
    return;
  }

  auto sleepDuration = WDTO_8S;

#if 0
  if (status == eNoTasksWaitingTimeout) {
    // Could do a longer sleep here, but we don't know enough about
    // the other peripherals to know that it is safe to do that
  }
#endif

  if (xExpectedIdleTime >= 4000 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_4S;
  } else if (xExpectedIdleTime >= 2000 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_2S;
  } else if (xExpectedIdleTime >= 1000 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_1S;
  } else if (xExpectedIdleTime >= 500 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_500MS;
  } else if (xExpectedIdleTime >= 250 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_250MS;
  } else if (xExpectedIdleTime >= 120 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_120MS;
  } else if (xExpectedIdleTime >= 60 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_60MS;
  } else if (xExpectedIdleTime >= 30 / portTICK_PERIOD_MS) {
    sleepDuration = WDTO_30MS;
  } else {
    sleepDuration = WDTO_15MS;
  }

  using clacker::avr::Timer1;
  using clacker::avr::WaveformGenerationMode;
  Timer1::disableCompareInterrupt();
  auto config = clacker::avr::computeTimerConfig<Timer1>(configTICK_RATE_HZ);
  Timer1::setup(WaveformGenerationMode::Normal, config.source);

  wdt_enable(sleepDuration);
  set_sleep_mode(SLEEP_MODE_IDLE);

  /* Re-enabling interrupts to awake and go to sleep*/
  sleep_enable();
  sei();
  sleep_cpu();
  /* Sleeps here until awaken, then continues */
  sleep_disable();
  cli();

  wdt_disable();

  vTaskStepTick(Timer1::counter() / config.compare);
  Timer1::setup(
      WaveformGenerationMode::ClearOnTimerMatchOutputCompare,
      config.source,
      config.compare);
  portEXIT_CRITICAL();
#endif
}
#endif
