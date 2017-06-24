#include "src/libs/tasks/Result.h"

namespace clacker {
namespace freertos {

BoolResult boolResult(BaseType_t result) {
  if (result == pdTRUE) {
    return BoolResult::Ok();
  }
  return BoolResult::Error(result);
}
}
}
