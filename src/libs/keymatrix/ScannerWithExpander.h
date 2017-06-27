#pragma once
#include "src/libs/keymatrix/KeyMatrix.h"
#include "src/libs/tasks/Tasks.h"

namespace clacker {
// A generic matrix scanner
// RowPins is a gpio::OutputPins corresponding to the output
// pins for the rows.
// Expander is an IO Expander such as the SX1509
template <typename Matrix, typename RowPins, typename Expander>
class MatrixScannerWithExpander {
 public:
  MatrixScannerWithExpander() {
    static_assert(Matrix::RowCount <= 8, "RowPins supports a max of 8 rows");
    static_assert(Matrix::ColCount <= 16, "Expander supports a max of 16 cols");
  }

  void setup() {
    memset(matrix_.rows, 0, sizeof(matrix_.rows));
    RowPins::setup();
    expander.setup();
    RowPins::write(0);
  }

  bool scanMatrix() __attribute__((noinline)) {
    memcpy(prior_.rows, matrix_.rows, sizeof(prior_.rows));
    memset(matrix_.rows, 0, sizeof(matrix_.rows));
    bool changed = false;

    for (uint8_t row = 0; row < Matrix::RowCount; ++row) {
      RowPins::write(~(1 << row));
      _delay_us(30);

      // Note: 0 means pressed in the expander bits,
      // so invert that for more rational use.
      matrix_.rows[row] = ~expander.read();
      if (prior_.rows[row] != matrix_.rows[row]) {
        changed = true;
      }
    }

    RowPins::write(0);
    return changed;
  }

  const Matrix& current() const {
    return matrix_;
  }
  const Matrix& prior() const {
    return prior_;
  }

 protected:
  Matrix matrix_;
  Matrix prior_;
  Expander expander;
};
}
