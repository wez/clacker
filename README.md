# Bits and pieces for making mechanical keyboards

One of my (@wez) hobbies is making custom mechanical keyboards.
This repository is where I'm collecting my tools.  It includes:

* A FreeRTOS-based firmware for keyboards
* A keyboard-layout-editor.com (KLE) parser and code generator that
  can take layout information and generate the keymap data
  for use with the firmware.
* Can target boards supported by Arduino (via the FQBN), and
  directly target the AVR toolchain.  Adding support for other
  targets is pretty straight forward

Things planned for the future:

* Generate SKIDL schematics and a PCB design from KLE data
* Generate plate/case design files from KLE data

## Getting started

Everything is driven via the `clacker.py` script in the root of
the repo.  Running it for the first time will pull in some python
dependencies needed to run some of the subcommands.

### build

Running `clacker.py build` will build all of the possible targets.
You can specify a target from a subdirectory using a command like
`clacker.py build src/firmware/flutterby:flutterby`.   Targets
are defined by the `info.py` files that are found throughout the
repo.  In the example given already, the portion of the name to
the left of the colon corresponds to the subdirectory containing
the `info.py` file and the portion to the right of the colon
corresponds to the `name` property of one of the targets defined
in that `info.py` file.

You can find a list of possible targets by running:

`clacker.py list-firmware`

### test

Running `clacker.py test` will run all the unit tests.  The unit
tests are built with the host system compiler and are intended to
verify architecture neutral components.

You can find a list of possible tests by running:

`clacker.py list-tests`

### upload

This subcommand will build and upload a firmware to the device.
For example:

`./clacker.py upload src/firmware/flutterby:flutterby --port /dev/cu.usbmodem14?1`

will build and upload the flutterby firmware to the device on the specified port.

# Clacker keyboard firmware

Why another keyboard firmware?  There are a couple of properties that I
strongly desire and that are not easy to add to existing firmware projects, but
the main thing for me is Low power utilization.  Other projects are optimized
for USB bus powered devices and use very busy loops.  I'm aiming for low power
bluetooth devices and desire the ability to put the device to sleep when
possible.

In addition, I'd like to take advantage of more modern C++ features to help
make the firmware a bit more composable.
