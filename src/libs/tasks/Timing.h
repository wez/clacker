#pragma once
#include "FreeRTOS.h"
namespace clacker {

static constexpr uint32_t kInfiniteMs = 0xffffffffu;

TickType_t millisecondsToTicks(uint32_t ms);
void delayMilliseconds(uint32_t ms);
}
