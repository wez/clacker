#ifdef __AVR__
#include <avr/power.h>
#include <avr/wdt.h>
#endif
#include "src/libs/result/Logging.h"
#include "src/libs/tasks/Bootloader.h"
#include "src/libs/tasks/Tasks.h"
namespace clacker {
namespace bootloader {

#ifdef __AVR__

#if !defined(MCUSR) && defined(MCUCSR)
#define MCUSR MCUCSR
#endif

// The Caterina bootloader uses this protocol to decide whether to start
// the loaded sketch or enter upload mode.  We use the same protocol on
// non-Caterina systems in order to keep the code similar, but we need
// to check for this ourselves in the latter case.
static constexpr uint16_t kBootRequest = 0x7777;
#define BootKey (uint16_t*)0x0800

// The attributes set on this function cause it to be run before main.
// We need this code to make sure that the system is appropriately reset
// when we are reset by software.  This can be either due to a panic
// or as part of entering the bootloader to flash a new firmware.
void beforeMain(void) __attribute__((used, naked, section(".init3")));
void beforeMain(void) {
#if !BOOTLOADER_IS_CATERINA
  bool bootloaderRequest = (MCUSR & _BV(WDRF)) && *BootKey == kBootRequest;
#endif

// The bootloader may have left USB interrupts enabled, but
// the firmware that we're running may not have set up an
// ISR for them, so we must disable them here to avoid
// faulting the MCU after re-flashing.
#if defined(UCSRB)
  UCSRB = 0;
#elif defined(UCSR0B)
  UCSR0B = 0;
#endif
#ifdef USBCON
  USBCON = 0;
  /* Disable clock division */
  clock_prescale_set(clock_div_1);
#endif
#ifdef MCUSR
  MCUSR &= ~(1 << WDRF);
#endif
  wdt_disable();
  *BootKey = 0;

#if !BOOTLOADER_IS_CATERINA
  if (bootloaderRequest) {
#define BOOTLOADER_START ((FLASHEND + 1L) - BOOTLOADER_SIZE)
    ((void (*)(void))(BOOTLOADER_START / 2))();
  }
#endif
}

void enterBootloader() {
  // Make sure that we disable interrupts as we may be poking memory that
  // may be mutated at any time
  taskENTER_CRITICAL();
  *BootKey = kBootRequest;
  panicReset();
}
#endif // AVR
}
}
