Library(name='gpio', srcs=[])

UnitTest(name='gpiotest',
         srcs=['test_gpio.cpp'],
         deps=[':gpio'])
