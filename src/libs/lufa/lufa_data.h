#pragma once
// Externs for things that won't compile with a C++ compiler

enum InterfaceDescriptors {
  INTERFACE_ID_CDC_CCI,
  INTERFACE_ID_CDC_DCI,
  INTERFACE_ID_Keyboard,
  INTERFACE_ID_ExtraKeys,
};

/** Endpoint address of the Keyboard HID reporting IN endpoint. */
#define KEYBOARD_EPADDR (ENDPOINT_DIR_IN | 1)

/** Endpoint address of the CDC device-to-host notification IN endpoint. */
#define CDC_NOTIFICATION_EPADDR (ENDPOINT_DIR_IN | 2)

/** Endpoint address of the CDC device-to-host data IN endpoint. */
#define CDC_TX_EPADDR (ENDPOINT_DIR_IN | 3)

/** Endpoint address of the CDC host-to-device data OUT endpoint. */
#define CDC_RX_EPADDR (ENDPOINT_DIR_OUT | 4)

#define EXTRAKEY_EPADDR (ENDPOINT_DIR_IN | 5)

/** Size in bytes of the Keyboard HID reporting IN endpoint. */
#define KEYBOARD_EPSIZE 8
#define EXTRAKEY_EPSIZE 8

/** Size in bytes of the CDC device-to-host notification IN endpoint. */
#define CDC_NOTIFICATION_EPSIZE 8

/** Size in bytes of the CDC data IN and OUT endpoints. */
#define CDC_TXRX_EPSIZE 16

#ifdef __cplusplus
extern "C" {
#endif
extern const USB_Descriptor_String_t PROGMEM lufa_LanguageString;
extern const USB_Descriptor_String_t PROGMEM lufa_ManufacturerString;
extern const USB_Descriptor_String_t PROGMEM lufa_ProductString;
extern USB_ClassInfo_HID_Device_t lufa_Keyboard_HID_Interface;
extern USB_ClassInfo_CDC_Device_t lufa_VirtualSerial_CDC_Interface;
#ifdef __cplusplus
}
#endif
