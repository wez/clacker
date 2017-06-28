#include "src/libs/keyprocessor/KeyProcessor.h"
namespace clacker {
void performUserDefinedFunction(uint16_t fnid) __attribute__((weak));
void performUserDefinedFunction(uint16_t fnid) {}

ProgMemIter<uint8_t> emptyMacroDefinition() {
  static const uint8_t emptyMacro[]
#ifdef PROGMEM
      PROGMEM
#endif
      = {MacroEnd};
  return emptyMacro;
}

ProgMemIter<uint8_t> lookupMacroDefinition(uint16_t macroid)
    __attribute__((weak));
ProgMemIter<uint8_t> lookupMacroDefinition(uint16_t macroid) {
  return emptyMacroDefinition();
}
}
