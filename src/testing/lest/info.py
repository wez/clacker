Library(name='lest', cppflags=['-Dlest_FEATURE_AUTO_REGISTER=1'])

UnitTest(name='test', srcs=['example.cpp'])
