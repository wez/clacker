Library(name='progmem', srcs=['pointers.cpp'], deps=['src/libs/traits:traits'])

UnitTest(name='progmemtest',
         srcs=['test_progmem.cpp'],
         deps=[':progmem'])
