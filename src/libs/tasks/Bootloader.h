#pragma once
namespace clacker {
namespace bootloader {

#ifndef BOOTLOADER_IS_CATERINA
#ifdef ARDUINO
#define BOOTLOADER_IS_CATERINA 1
#else
#define BOOTLOADER_IS_CATERINA 0
#endif
#endif

#ifndef BOOTLOADER_SIZE
#ifdef BOOTLOADER_IS_CATERINA
#define BOOTLOADER_SIZE 4096
#endif
#endif

void enterBootloader();
}
}
