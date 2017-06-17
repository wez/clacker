Library(name='strings', srcs=[],
        deps=[
            'src/libs/traits:traits',
            'src/libs/progmem:progmem',
])

UnitTest(name='stringtest',
         srcs=['test_strings.cpp'],
         deps=[':strings'])
