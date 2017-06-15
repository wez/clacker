#include "src/libs/progmem/ProgMem.h"
#include "src/testing/lest/lest.hpp"
using namespace lest;
using namespace clacker;

static tests specification;

lest_CASE(specification, "basic iteration") {
  static const char* const helloData = "hello";
  auto hello = makeProgMemIter(helloData);

  EXPECT(*hello == 'h');
  ++hello;
  EXPECT(*hello == 'e');
  ++hello;
  EXPECT(*hello == 'l');
  ++hello;
  EXPECT(*hello == 'l');
  ++hello;
  EXPECT(*hello == 'o');
}

lest_CASE(specification, "advance by numeric offset") {
  static const char* const helloData = "hello";
  auto hello = makeProgMemIter(helloData) + 2;

  EXPECT(*hello == 'l');

  auto backOne = hello - 1;
  EXPECT(backOne != hello);
  EXPECT(*backOne == 'e');
  EXPECT(*--backOne == 'h');

  EXPECT(backOne + 2 == hello);
}

int main(int argc, char* argv[]) {
  return run(specification, argc, argv);
}
