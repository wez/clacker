#include "src/testing/lest/lest.hpp"
using namespace lest;

static tests specification;

lest_CASE(specification, "example") {
  EXPECT(false == is_true(false));
}

int main(int argc, char* argv[]) {
  return run(specification, argc, argv);
}
