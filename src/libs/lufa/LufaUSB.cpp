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
#include "src/libs/tasks/Bootloader.h"
namespace clacker {

// This is present to provide a way to safely shutdown USB when software
// initiates a reset
void panicShutdownUSB() {
  USB_Disable();
  cli();
  _delay_ms(1000);
}

namespace lufa {

enum StringDescriptors {
  STRING_ID_Language = 0, // must be zero
  STRING_ID_Manufacturer = 1,
  STRING_ID_Product = 2,
};

struct USB_Descriptor_Configuration_t {
  USB_Descriptor_Configuration_Header_t Config;

  // CDC Control Interface
  USB_Descriptor_Interface_Association_t CDC_IAD;
  USB_Descriptor_Interface_t CDC_CCI_Interface;
  USB_CDC_Descriptor_FunctionalHeader_t CDC_Functional_Header;
  USB_CDC_Descriptor_FunctionalACM_t CDC_Functional_ACM;
  USB_CDC_Descriptor_FunctionalUnion_t CDC_Functional_Union;
  USB_Descriptor_Endpoint_t CDC_NotificationEndpoint;

  // CDC Data Interface
  USB_Descriptor_Interface_t CDC_DCI_Interface;
  USB_Descriptor_Endpoint_t CDC_DataOutEndpoint;
  USB_Descriptor_Endpoint_t CDC_DataInEndpoint;

  // Keyboard HID Interface
  USB_Descriptor_Interface_t HID_Interface;
  USB_HID_Descriptor_HID_t HID_KeyboardHID;
  USB_Descriptor_Endpoint_t HID_ReportINEndpoint;
  USB_Descriptor_Interface_t Extrakey_Interface;
  USB_HID_Descriptor_HID_t Extrakey_HID;
  USB_Descriptor_Endpoint_t Extrakey_INEndpoint;
};

const USB_Descriptor_HIDReport_Datatype_t PROGMEM KeyboardReport[] = {
    HID_DESCRIPTOR_KEYBOARD(6)};

enum {
  REPORT_ID_SYSTEM = 2,
  REPORT_ID_CONSUMER = 3,
};

const USB_Descriptor_HIDReport_Datatype_t PROGMEM ExtrakeyReport[] = {
    HID_RI_USAGE_PAGE(8, 0x01), /* Generic Desktop */
    HID_RI_USAGE(8, 0x80), /* System Control */
    HID_RI_COLLECTION(8, 0x01), /* Application */
    HID_RI_REPORT_ID(8, REPORT_ID_SYSTEM),
    HID_RI_LOGICAL_MINIMUM(16, 0x0001),
    HID_RI_LOGICAL_MAXIMUM(16, 0x0003),
    HID_RI_USAGE_MINIMUM(16, 0x0081), /* System Power Down */
    HID_RI_USAGE_MAXIMUM(16, 0x0083), /* System Wake Up */
    HID_RI_REPORT_SIZE(8, 16),
    HID_RI_REPORT_COUNT(8, 1),
    HID_RI_INPUT(8, HID_IOF_DATA | HID_IOF_ARRAY | HID_IOF_ABSOLUTE),
    HID_RI_END_COLLECTION(0),

    HID_RI_USAGE_PAGE(8, 0x0C), /* Consumer */
    HID_RI_USAGE(8, 0x01), /* Consumer Control */
    HID_RI_COLLECTION(8, 0x01), /* Application */
    HID_RI_REPORT_ID(8, REPORT_ID_CONSUMER),
    HID_RI_LOGICAL_MINIMUM(16, 0x0001),
    HID_RI_LOGICAL_MAXIMUM(16, 0x029C),
    HID_RI_USAGE_MINIMUM(16, 0x0001), /* +10 */
    HID_RI_USAGE_MAXIMUM(16, 0x029C), /* AC Distribute Vertically */
    HID_RI_REPORT_SIZE(8, 16),
    HID_RI_REPORT_COUNT(8, 1),
    HID_RI_INPUT(8, HID_IOF_DATA | HID_IOF_ARRAY | HID_IOF_ABSOLUTE),
    HID_RI_END_COLLECTION(0),
};

const USB_Descriptor_Device_t PROGMEM DeviceDescriptor = {
    .Header = {.Size = sizeof(USB_Descriptor_Device_t), .Type = DTYPE_Device},

    .USBSpecification = VERSION_BCD(1, 1, 0),
    .Class = USB_CSCP_IADDeviceClass,
    .SubClass = USB_CSCP_IADDeviceSubclass,
    .Protocol = USB_CSCP_IADDeviceProtocol,

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
               .TotalInterfaces = INTERFACE_COUNT,

               .ConfigurationNumber = 1,
               .ConfigurationStrIndex = NO_DESCRIPTOR,

               .ConfigAttributes =
                   (USB_CONFIG_ATTR_RESERVED | USB_CONFIG_ATTR_SELFPOWERED),

               .MaxPowerConsumption = USB_CONFIG_POWER_MA(100)},

    .CDC_IAD = {.Header = {.Size =
                               sizeof(USB_Descriptor_Interface_Association_t),
                           .Type = DTYPE_InterfaceAssociation},

                .FirstInterfaceIndex = INTERFACE_ID_CDC_CCI,
                .TotalInterfaces = 2,

                .Class = CDC_CSCP_CDCClass,
                .SubClass = CDC_CSCP_ACMSubclass,
                .Protocol = CDC_CSCP_ATCommandProtocol,

                .IADStrIndex = NO_DESCRIPTOR},

    .CDC_CCI_Interface = {.Header = {.Size = sizeof(USB_Descriptor_Interface_t),
                                     .Type = DTYPE_Interface},

                          .InterfaceNumber = INTERFACE_ID_CDC_CCI,
                          .AlternateSetting = 0,

                          .TotalEndpoints = 1,

                          .Class = CDC_CSCP_CDCClass,
                          .SubClass = CDC_CSCP_ACMSubclass,
                          .Protocol = CDC_CSCP_ATCommandProtocol,

                          .InterfaceStrIndex = NO_DESCRIPTOR},

    .CDC_Functional_Header =
        {
            .Header = {.Size = sizeof(USB_CDC_Descriptor_FunctionalHeader_t),
                       .Type = DTYPE_CSInterface},
            .Subtype = CDC_DSUBTYPE_CSInterface_Header,

            .CDCSpecification = VERSION_BCD(1, 1, 0),
        },

    .CDC_Functional_ACM =
        {
            .Header = {.Size = sizeof(USB_CDC_Descriptor_FunctionalACM_t),
                       .Type = DTYPE_CSInterface},
            .Subtype = CDC_DSUBTYPE_CSInterface_ACM,

            .Capabilities = 0x06,
        },

    .CDC_Functional_Union =
        {
            .Header = {.Size = sizeof(USB_CDC_Descriptor_FunctionalUnion_t),
                       .Type = DTYPE_CSInterface},
            .Subtype = CDC_DSUBTYPE_CSInterface_Union,

            .MasterInterfaceNumber = INTERFACE_ID_CDC_CCI,
            .SlaveInterfaceNumber = INTERFACE_ID_CDC_DCI,
        },

    .CDC_NotificationEndpoint =
        {.Header = {.Size = sizeof(USB_Descriptor_Endpoint_t),
                    .Type = DTYPE_Endpoint},

         .EndpointAddress = CDC_NOTIFICATION_EPADDR,
         .Attributes =
             (EP_TYPE_INTERRUPT | ENDPOINT_ATTR_NO_SYNC | ENDPOINT_USAGE_DATA),
         .EndpointSize = CDC_NOTIFICATION_EPSIZE,
         .PollingIntervalMS = 0xFF},

    .CDC_DCI_Interface = {.Header = {.Size = sizeof(USB_Descriptor_Interface_t),
                                     .Type = DTYPE_Interface},

                          .InterfaceNumber = INTERFACE_ID_CDC_DCI,
                          .AlternateSetting = 0,

                          .TotalEndpoints = 2,

                          .Class = CDC_CSCP_CDCDataClass,
                          .SubClass = CDC_CSCP_NoDataSubclass,
                          .Protocol = CDC_CSCP_NoDataProtocol,

                          .InterfaceStrIndex = NO_DESCRIPTOR},

    .CDC_DataOutEndpoint = {.Header = {.Size =
                                           sizeof(USB_Descriptor_Endpoint_t),
                                       .Type = DTYPE_Endpoint},

                            .EndpointAddress = CDC_RX_EPADDR,
                            .Attributes =
                                (EP_TYPE_BULK | ENDPOINT_ATTR_NO_SYNC |
                                 ENDPOINT_USAGE_DATA),
                            .EndpointSize = CDC_TXRX_EPSIZE,
                            .PollingIntervalMS = 5},

    .CDC_DataInEndpoint = {.Header = {.Size = sizeof(USB_Descriptor_Endpoint_t),
                                      .Type = DTYPE_Endpoint},

                           .EndpointAddress = CDC_TX_EPADDR,
                           .Attributes =
                               (EP_TYPE_BULK | ENDPOINT_ATTR_NO_SYNC |
                                ENDPOINT_USAGE_DATA),
                           .EndpointSize = CDC_TXRX_EPSIZE,
                           .PollingIntervalMS = 5},
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
                             .PollingIntervalMS = 10},
    .Extrakey_Interface = {.Header = {.Size =
                                          sizeof(USB_Descriptor_Interface_t),
                                      .Type = DTYPE_Interface},

                           .InterfaceNumber = INTERFACE_ID_ExtraKeys,
                           .AlternateSetting = 0x00,

                           .TotalEndpoints = 1,

                           .Class = HID_CSCP_HIDClass,
                           .SubClass = HID_CSCP_NonBootSubclass,
                           .Protocol = HID_CSCP_NonBootProtocol,

                           .InterfaceStrIndex = NO_DESCRIPTOR},

    .Extrakey_HID = {.Header = {.Size = sizeof(USB_HID_Descriptor_HID_t),
                                .Type = HID_DTYPE_HID},

                     .HIDSpec = VERSION_BCD(1, 1, 1),
                     .CountryCode = 0x00,
                     .TotalReportDescriptors = 1,
                     .HIDReportType = HID_DTYPE_Report,
                     .HIDReportLength = sizeof(ExtrakeyReport)},

    .Extrakey_INEndpoint = {.Header = {.Size =
                                           sizeof(USB_Descriptor_Endpoint_t),
                                       .Type = DTYPE_Endpoint},

                            .EndpointAddress = EXTRAKEY_EPADDR,
                            .Attributes =
                                (EP_TYPE_INTERRUPT | ENDPOINT_ATTR_NO_SYNC |
                                 ENDPOINT_USAGE_DATA),
                            .EndpointSize = EXTRAKEY_EPSIZE,
                            .PollingIntervalMS = 10},

};

extern "C" uint16_t CALLBACK_USB_GetDescriptor(
    const uint16_t wValue,
    const uint16_t wIndex,
    const void** const DescriptorAddress) {
  const uint8_t DescriptorType = (wValue >> 8);
  const uint8_t DescriptorNumber = (wValue & 0xFF);

#define getDesc(what) *DescriptorAddress = &what, sizeof(what)

  switch (DescriptorType) {
    case DTYPE_Device:
      return getDesc(DeviceDescriptor);

    case DTYPE_Configuration:
      return getDesc(ConfigurationDescriptor);

    case DTYPE_String:
      switch (DescriptorNumber) {
        case STRING_ID_Language:
          *DescriptorAddress = &lufa_LanguageString;
          return pgm_read_byte(&lufa_LanguageString.Header.Size);
        case STRING_ID_Manufacturer:
          *DescriptorAddress = &lufa_ManufacturerString;
          return pgm_read_byte(&lufa_ManufacturerString.Header.Size);
        case STRING_ID_Product:
          *DescriptorAddress = &lufa_ProductString;
          return pgm_read_byte(&lufa_ProductString.Header.Size);
      }
      break;
    case HID_DTYPE_HID:
      switch (wIndex) {
        case INTERFACE_ID_Keyboard:
          return getDesc(ConfigurationDescriptor.HID_KeyboardHID);
        case INTERFACE_ID_ExtraKeys:
          return getDesc(ConfigurationDescriptor.Extrakey_HID);
      }
      break;
    case HID_DTYPE_Report:
      switch (wIndex) {
        case INTERFACE_ID_Keyboard:
          return getDesc(KeyboardReport);
        case INTERFACE_ID_ExtraKeys:
          return getDesc(ExtrakeyReport);
      }
  }

  *DescriptorAddress = nullptr;
  return NO_DESCRIPTOR;
#undef getDesc
}

extern "C" void EVENT_USB_Device_ConfigurationChanged(void) {
  CDC_Device_ConfigureEndpoints(&lufa_VirtualSerial_CDC_Interface);
  HID_Device_ConfigureEndpoints(&lufa_Keyboard_HID_Interface);
  Endpoint_ConfigureEndpoint(
      EXTRAKEY_EPADDR, EP_TYPE_INTERRUPT, EXTRAKEY_EPSIZE, 1);
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
  CDC_Device_ProcessControlRequest(&lufa_VirtualSerial_CDC_Interface);
  HID_Device_ProcessControlRequest(&lufa_Keyboard_HID_Interface);
}

extern "C" void EVENT_USB_Device_StartOfFrame(void) {
  HID_Device_MillisecondElapsed(&lufa_Keyboard_HID_Interface);
}

extern "C" void EVENT_CDC_Device_ControLineStateChanged(
    USB_ClassInfo_CDC_Device_t* const CDCInterfaceInfo) {
  // This is how we can tell if the host is connected to the port
  bool HostReady = (CDCInterfaceInfo->State.ControlLineStates.HostToDevice &
                    CDC_CONTROL_LINE_OUT_DTR) != 0;

  if (!HostReady && CDCInterfaceInfo->State.LineEncoding.BaudRateBPS == 1200) {
    // If the host opens and closes the serial port at 1200 baud, that
    // is the arduino compatible way to request that we enter the
    // bootloader.  So let's do it!
    bootloader::enterBootloader();
  }
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

void LufaUSB::tick() {
  // We need to disable interrupts here, otherwise something
  // in lufa gets unhappy and breaks the scheduler.
  CriticalSection disableInterrupts;

  /* Must throw away unused bytes from the host, or it will lock up while
   * waiting for the device */
  CDC_Device_ReceiveByte(&lufa_VirtualSerial_CDC_Interface);
  CDC_Device_USBTask(&lufa_VirtualSerial_CDC_Interface);
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

void LufaUSB::run() {
  {
    CriticalSection disableInterrupts;
    USB_Init();
  }

  auto lastState = USB_DeviceState;
  uint16_t delay = 0;
  TickType_t stateTick = xTaskGetTickCount();

  while (true) {
    Command cmd;

    auto now = xTaskGetTickCount();
    if (lastState != USB_DeviceState) {
      lastState = USB_DeviceState;
      stateTick = now;
      delay = 0;
    }
    if (delay == 0 && (lastState == DEVICE_STATE_Unattached ||
                       lastState == DEVICE_STATE_Suspended)) {
      if ((now - stateTick) > TickType_t{10000} / portTICK_PERIOD_MS) {
        // If we're not connected to the host then we don't need to
        // check for things as frequently.   This will allow us to
        // sleep for longer.  We give it a few seconds grace to
        // de-bounce around plug/unplug events
        delay = 1000;
      }
    }

    if (queue_.recv(cmd, delay).hasValue()) {
      // Do something with cmd
      switch (cmd.CommandType) {
        case KeyReport:
          memcpy(&pendingReport_, &cmd.u.report, sizeof(pendingReport_));
          if (USB_DeviceState == DEVICE_STATE_Suspended &&
              USB_Device_RemoteWakeupEnabled) {
            USB_Device_SendRemoteWakeup();
          }
          break;
        case ExtraKeyReport:

        {
          Endpoint_SelectEndpoint(EXTRAKEY_EPADDR & ENDPOINT_EPNUM_MASK);
          /* Check if write ready for a polling interval around 10ms */
          uint8_t timeout = 255;
          while (timeout-- && !Endpoint_IsReadWriteAllowed()) {
            _delay_us(40);
          }
          if (Endpoint_IsReadWriteAllowed()) {
            Endpoint_Write_Stream_LE(&cmd.u.extra, sizeof(cmd.u.extra), NULL);
            Endpoint_ClearIN();
            logln(makeConstString("sent extra key"), cmd.u.extra.usage);
          } else {
            logln(makeConstString(
                "timed out waiting for extrakey endpoint to be ready"));
          }
        } break;
      }
    }

    tick();
    taskYIELD();
  }
}
void LufaUSB::consumerKey(uint16_t code) {
  Command cmd;
  cmd.CommandType = ExtraKeyReport;
  cmd.u.extra.report_id = REPORT_ID_CONSUMER;
  cmd.u.extra.usage = code;
  queue_.send(cmd);
}

void LufaUSB::systemKey(uint16_t code) {
  Command cmd;
  cmd.CommandType = ExtraKeyReport;
  cmd.u.extra.report_id = REPORT_ID_SYSTEM;
  cmd.u.extra.usage = code - 0x81 /* HID_SYSTEM_POWER_DOWN */;
  queue_.send(cmd);
}

void LufaUSB::basicReport(const Report& report) {
  Command cmd;
  cmd.CommandType = KeyReport;
  cmd.u.report = report;
  static bool lastNull;
  bool shouldLog = true;

  if (report.mods == 0) {
    bool isNull = true;
    for (int i = 0; i < 6; ++i) {
      if (report.keys[i]) {
        isNull = false;
        break;
      }
    }
    if (isNull && lastNull) {
      shouldLog = false;
    }
    lastNull = isNull;
  } else {
    lastNull = false;
  }

  if (shouldLog) {
    logln(
        makeConstString("report: "),
        int{report.mods},
        makeConstString(" "),
        int{report.keys[0]},
        makeConstString(" "),
        int{report.keys[1]},
        makeConstString(" "),
        int{report.keys[2]},
        makeConstString(" "),
        int{report.keys[3]},
        makeConstString(" "),
        int{report.keys[4]},
        makeConstString(" "),
        int{report.keys[5]});
  }
  queue_.send(cmd);
}
}
}
