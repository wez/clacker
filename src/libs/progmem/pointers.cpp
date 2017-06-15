#include "src/libs/progmem/ProgMem.h"

namespace clacker {
template class ProgMemIter<void*>;
template class ProgMemIter<char*>;
}
