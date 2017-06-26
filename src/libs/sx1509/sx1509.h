/*
Copyright 2016-2017 Wez Furlong

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
#pragma once
#include <inttypes.h>

namespace clacker {

class SX1509 {
 public:
  /** Configure the expander as all inputs */
  void setup();

  /** Read all the input pins */
  uint16_t read();

  /** Returns mask of pins that were sources of interrupts,
   * and clears that state */
  uint16_t interruptSources();

  void enableInterrupts();
  void disableInterrupts();
};
}
