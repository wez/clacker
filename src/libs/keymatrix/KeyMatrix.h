#pragma once
#include "src/libs/traits/SmallestInteger.h"
namespace clacker {

template <uint8_t NumRows, uint8_t NumCols>
struct KeyMatrix {
  static constexpr uint8_t RowCount = NumRows;
  static constexpr uint8_t ColCount = NumCols;
  using ColumnType = typename smallest_integer_bits<NumCols>::type;

  ColumnType rows[NumRows];
};
}
