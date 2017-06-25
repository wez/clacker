Library(name='tasks',
        srcs=['main.cpp', 'milliseconds.cpp', 'panic.cpp', 'Result.cpp',
              'beforeMain.cpp'],
        deps=['src/libs/freertos:freertos', 'src/libs/result:result'])
