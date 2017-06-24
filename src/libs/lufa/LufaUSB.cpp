/* Portions of this file are:
  Copyright 2017  Dean Camera (dean [at] fourwalledcubicle [dot] com)

  Permission to use, copy, modify, distribute, and sell this
  software and its documentation for any purpose is hereby granted
  without fee, provided that the above copyright notice appear in
  all copies and that both that the copyright notice and this
  permission notice and warranty disclaimer appear in supporting
  documentation, and that the name of the author not be used in
  advertising or publicity pertaining to distribution of the
  software without specific, written prior permission.

  The author disclaims all warranties with regard to this
  software, including all implied warranties of merchantability
  and fitness.  In no event shall the author be liable for any
  special, indirect or consequential damages or any damages
  whatsoever resulting from loss of use, data or profits, whether
  in an action of contract, negligence or other tortious action,
  arising out of or in connection with the use or performance of
  this software.
*/
#include "LufaUSB.h"
#include <LUFA/Drivers/USB/USB.h>
#include "lufa_data.h"
namespace clacker {
namespace lufa {

enum StringDescriptors {
  STRING_ID_Language = 0, // must be zero
  STRING_ID_Manufacturer = 1,
  STRING_ID_Product = 2,
};

struct USB_Descriptor_Configuration_t {
  USB_Descriptor_Configuration_Header_t Config;

  // Keyboard HID Interface
  USB_Descriptor_Interface_t HID_Interface;
  USB_HID_Descriptor_HID_t HID_KeyboardHID;
  USB_Descriptor_Endpoint_t HID_ReportINEndpoint;
};

const USB_Descriptor_HIDReport_Datatype_t PROGMEM KeyboardReport[] = {
    HID_DESCRIPTOR_KEYBOARD(6)};

const USB_Descriptor_Device_t PROGMEM DeviceDescriptor = {
    .Header = {.Size = sizeof(USB_Descriptor_Device_t), .Type = DTYPE_Device},

    .USBSpecification = VERSION_BCD(1, 1, 0),
    .Class = USB_CSCP_NoDeviceClass,
    .SubClass = USB_CSCP_NoDeviceSubclass,
    .Protocol = USB_CSCP_NoDeviceProtocol,

    .Endpoint0Size = FIXED_CONTROL_ENDPOINT_SIZE,

    .VendorID = CLACKER_USB_VID,
    .ProductID = CLACKER_USB_PID,
    .ReleaseNumber = VERSION_BCD(0, 0, 1),

    .ManufacturerStrIndex = STRING_ID_Manufacturer,
    .ProductStrIndex = STRING_ID_Product,
    .SerialNumStrIndex = NO_DESCRIPTOR,

    .NumberOfConfigurations = FIXED_NUM_CONFIGURATIONS};

const USB_Descriptor_Configuration_t PROGMEM ConfigurationDescriptor = {
    .Config = {.Header = {.Size = sizeof(USB_Descriptor_Configuration_Header_t),
                          .Type = DTYPE_Configuration},

               .TotalConfigurationSize = sizeof(USB_Descriptor_Configuration_t),
               .TotalInterfaces = 1,

               .ConfigurationNumber = 1,
               .ConfigurationStrIndex = NO_DESCRIPTOR,

               .ConfigAttributes =
                   (USB_CONFIG_ATTR_RESERVED | USB_CONFIG_ATTR_SELFPOWERED),

               .MaxPowerConsumption = USB_CONFIG_POWER_MA(100)},

    .HID_Interface = {.Header = {.Size = sizeof(USB_Descriptor_Interface_t),
                                 .Type = DTYPE_Interface},

                      .InterfaceNumber = INTERFACE_ID_Keyboard,
                      .AlternateSetting = 0x00,

                      .TotalEndpoints = 1,

                      .Class = HID_CSCP_HIDClass,
                      .SubClass = HID_CSCP_BootSubclass,
                      .Protocol = HID_CSCP_KeyboardBootProtocol,

                      .InterfaceStrIndex = NO_DESCRIPTOR},

    .HID_KeyboardHID = {.Header = {.Size = sizeof(USB_HID_Descriptor_HID_t),
                                   .Type = HID_DTYPE_HID},

                        .HIDSpec = VERSION_BCD(1, 1, 1),
                        .CountryCode = 0x00,
                        .TotalReportDescriptors = 1,
                        .HIDReportType = HID_DTYPE_Report,
                        .HIDReportLength = sizeof(KeyboardReport)},

    .HID_ReportINEndpoint = {.Header = {.Size =
                                            sizeof(USB_Descriptor_Endpoint_t),
                                        .Type = DTYPE_Endpoint},

                             .EndpointAddress = KEYBOARD_EPADDR,
                             .Attributes =
                                 (EP_TYPE_INTERRUPT | ENDPOINT_ATTR_NO_SYNC |
                                  ENDPOINT_USAGE_DATA),
                             .EndpointSize = KEYBOARD_EPSIZE,
                             .PollingIntervalMS = 0x05},
};

extern "C" uint16_t CALLBACK_USB_GetDescriptor(
    const uint16_t wValue,
    const uint16_t wIndex,
    const void** const DescriptorAddress) {
  const uint8_t DescriptorType = (wValue >> 8);
  const uint8_t DescriptorNumber = (wValue & 0xFF);

  const void* Address = NULL;
  uint16_t Size = NO_DESCRIPTOR;

  switch (DescriptorType) {
    case DTYPE_Device:
      Address = &DeviceDescriptor;
      Size = sizeof(USB_Descriptor_Device_t);
      break;
    case DTYPE_Configuration:
      Address = &ConfigurationDescriptor;
      Size = sizeof(USB_Descriptor_Configuration_t);
      break;
    case DTYPE_String:
      switch (DescriptorNumber) {
        case STRING_ID_Language:
          Address = &lufa_LanguageString;
          Size = pgm_read_byte(&lufa_LanguageString.Header.Size);
          break;
        case STRING_ID_Manufacturer:
          Address = &lufa_ManufacturerString;
          Size = pgm_read_byte(&lufa_ManufacturerString.Header.Size);
          break;
        case STRING_ID_Product:
          Address = &lufa_ProductString;
          Size = pgm_read_byte(&lufa_ProductString.Header.Size);
          break;
      }
      break;
    case HID_DTYPE_HID:
      Address = &ConfigurationDescriptor.HID_KeyboardHID;
      Size = sizeof(USB_HID_Descriptor_HID_t);
      break;
    case HID_DTYPE_Report:
      Address = &KeyboardReport;
      Size = sizeof(KeyboardReport);
      break;
  }

  *DescriptorAddress = Address;
  return Size;
}

extern "C" void EVENT_USB_Device_ConfigurationChanged(void) {
  HID_Device_ConfigureEndpoints(&lufa_Keyboard_HID_Interface);
  USB_Device_EnableSOFEvents();
}

// This is the function that sends the key report to the host.
// It collects the pendingReport_ from the LufaUSB instance
extern "C" bool CALLBACK_HID_Device_CreateHIDReport(
    USB_ClassInfo_HID_Device_t* const HIDInterfaceInfo,
    uint8_t* const ReportID,
    const uint8_t ReportType,
    void* ReportData,
    uint16_t* const ReportSize) {
  auto KeyboardReport = (USB_KeyboardReport_Data_t*)ReportData;
  *ReportSize = sizeof(*KeyboardReport);
  LufaUSB::get().populateReport(KeyboardReport);

  // No need to flush the report
  return false;
}

extern "C" void EVENT_USB_Device_ControlRequest(void) {
  HID_Device_ProcessControlRequest(&lufa_Keyboard_HID_Interface);
}

extern "C" void EVENT_USB_Device_StartOfFrame(void) {
  HID_Device_MillisecondElapsed(&lufa_Keyboard_HID_Interface);
}

extern "C" void CALLBACK_HID_Device_ProcessHIDReport(
    USB_ClassInfo_HID_Device_t* const HIDInterfaceInfo,
    const uint8_t ReportID,
    const uint8_t ReportType,
    const void* ReportData,
    const uint16_t ReportSize) {
  // TODO: we could interpret the report to discover which LEDs
  // the host would like us to activate.
}

// Meyers singleton to avoid SIOF
LufaUSB& LufaUSB::get() {
  static LufaUSB usb;
  return usb;
}

LufaUSB::LufaUSB() : task_([] { LufaUSB::get().taskLoop(); }) {}

void LufaUSB::start() {
  task_.start();
}

void LufaUSB::tick() {
  // We need to disable interrupts here, otherwise something
  // in lufa gets unhappy and breaks the scheduler.
  CriticalSection disableInterrupts;
  HID_Device_USBTask(&lufa_Keyboard_HID_Interface);
  USB_USBTask();
}

void LufaUSB::populateReport(USB_KeyboardReport_Data_t* ReportData) {
  memcpy(ReportData->KeyCode, pendingReport_.keys, sizeof(ReportData->KeyCode));
  static_assert(
      sizeof(ReportData->KeyCode) == sizeof(pendingReport_.keys),
      "same size keys vector");
  ReportData->Modifier = pendingReport_.mods;
}

void LufaUSB::taskLoop() {
  {
    SuspendScheduler suspend;
    USB_Init();
  }

  while (true) {
    Command cmd;

    if (queue.recv(cmd, 0).hasValue()) {
      // Do something with cmd
      switch (cmd.CommandType) {
        case KeyReport:
          memcpy(&pendingReport_, &cmd.u.report, sizeof(pendingReport_));
          break;
      }
    }

    tick();

    taskYIELD();
  }
}
}
}
