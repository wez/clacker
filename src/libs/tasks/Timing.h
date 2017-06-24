#pragma once
#include "FreeRTOS.h"
namespace clacker {

TickType_t millisecondsToTicks(uint32_t ms);
void delayMilliseconds(uint32_t ms);
}
