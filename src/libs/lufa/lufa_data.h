#pragma once
// Externs for things that won't compile with a C++ compiler

enum InterfaceDescriptors {
  INTERFACE_ID_Keyboard = 0,
};

/** Endpoint address of the Keyboard HID reporting IN endpoint. */
#define KEYBOARD_EPADDR (ENDPOINT_DIR_IN | 1)

/** Size in bytes of the Keyboard HID reporting IN endpoint. */
#define KEYBOARD_EPSIZE 8

#ifdef __cplusplus
extern "C" {
#endif
extern const USB_Descriptor_String_t PROGMEM lufa_LanguageString;
extern const USB_Descriptor_String_t PROGMEM lufa_ManufacturerString;
extern const USB_Descriptor_String_t PROGMEM lufa_ProductString;
extern USB_ClassInfo_HID_Device_t lufa_Keyboard_HID_Interface;
#ifdef __cplusplus
}
#endif
