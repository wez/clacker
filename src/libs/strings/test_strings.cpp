#include "src/libs/strings/FixedString.h"
#include "src/testing/lest/lest.hpp"
using namespace lest;
using namespace clacker;

static tests specification;

lest_CASE(specification, "const string") {
  auto cstr = makeConstString("woto");
  EXPECT(cstr == "woto");
  EXPECT(cstr != "wooo");
  EXPECT(cstr != "w");
  EXPECT(cstr != "waaaaa");
}

lest_CASE(specification, "fixed string") {
  FixedString<12> hello("hello");
  EXPECT(hello.size() == 5);
  EXPECT(std::string(hello.data(), hello.size()) == "hello");
  hello.append("there");
  EXPECT(hello == "hellothere");
  hello.append("woot");
  // woot gets truncated to fit the available space
  EXPECT(hello == "hellotherewo");

  auto s1 = makeFixedString("woah");
  EXPECT(s1.size() == 4);
  EXPECT(s1.capacity() == 4);
  EXPECT(std::string(s1.data(), s1.size()) == "woah");
}

lest_CASE(specification, "concat") {
  FixedString<24> str;
  str.append(makeConstString("hello"));
  EXPECT(str == "hello");

  auto there = makeConstString("there");
  str.append(there.begin(), 2);
  EXPECT(str == "helloth");
}

int main(int argc, char* argv[]) {
  return run(specification, argc, argv);
}
