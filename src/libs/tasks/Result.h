#pragma once
#include "FreeRTOS.h"
#include "src/libs/result/Result.h"

namespace clacker {
namespace freertos {

using BoolResult = Result<Unit, BaseType_t>;
BoolResult boolResult(BaseType_t result);
}
}
