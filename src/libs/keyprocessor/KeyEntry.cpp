#include "src/libs/keyprocessor/KeyProcessor.h"
namespace clacker {

void logKey(const KeyEntry& ent) {
  switch (ent.basic.type) {
    case BasicKey:
      log("BasicKey mods=", ent.basic.mods, " code=", ent.basic.code);
      return;
    case FunctionKey:
      log("FunctionKey ", ent.func.funcid);
      return;
    case MacroKey:
      log("MacroKey ", ent.func.funcid);
      return;
    case LayerKey:
      log("LayerKey ", ent.layer.layerid);
      return;
    case ConsumerKey:
      log("Consumer ", ent.extra.usage);
      return;
    default:
      log("Unknown");
      return;
  }
}
}
