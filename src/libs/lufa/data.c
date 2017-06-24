#include <LUFA/Drivers/USB/USB.h>
#include "lufa_data.h"

// This is here because USB_STRING_DESCRIPTOR_ARRAY doesn't compile
// with a C++11 compiler.

const USB_Descriptor_String_t PROGMEM lufa_LanguageString =
    USB_STRING_DESCRIPTOR_ARRAY(LANGUAGE_ID_ENG);

const USB_Descriptor_String_t PROGMEM lufa_ManufacturerString =
    USB_STRING_DESCRIPTOR(CLACKER_USB_MANUFACTURER_UNICODE);

const USB_Descriptor_String_t PROGMEM lufa_ProductString =
    USB_STRING_DESCRIPTOR(CLACKER_USB_PRODUCT_UNICODE);

/** Buffer to hold the previously generated Keyboard HID report, for comparison
 * purposes inside the HID class driver. */
static uint8_t PrevKeyboardHIDReportBuffer[sizeof(USB_KeyboardReport_Data_t)];

USB_ClassInfo_HID_Device_t lufa_Keyboard_HID_Interface = {
    .Config =
        {
            .InterfaceNumber = INTERFACE_ID_Keyboard,
            .ReportINEndpoint =
                {
                    .Address = KEYBOARD_EPADDR,
                    .Size = KEYBOARD_EPSIZE,
                    .Banks = 1,
                },
            .PrevReportINBuffer = PrevKeyboardHIDReportBuffer,
            .PrevReportINBufferSize = sizeof(PrevKeyboardHIDReportBuffer),
        },
};
