#pragma once
#include "src/libs/gpio/AvrGpio.h"
#include "src/libs/spi/SPI.h"
#include "src/libs/strings/FixedString.h"
#include "src/libs/tasks/Queue.h"
#include "src/libs/tasks/Tasks.h"
#include "src/libs/traits/Copy.h"
namespace clacker {

namespace spifriend {
// Commands are encoded using SDEP and sent via SPI
// https://github.com/adafruit/Adafruit_BluefruitLE_nRF51/blob/master/SDEP.md

enum ble_cmd {
  BleInitialize = 0xbeef,
  BleAtWrapper = 0x0a00,
  BleUartTx = 0x0a01,
  BleUartRx = 0x0a02,
};

enum sdep_type {
  SdepCommand = 0x10,
  SdepResponse = 0x20,
  SdepAlert = 0x40,
  SdepError = 0x80,
  SdepSlaveNotReady = 0xfe, // Try again later
  SdepSlaveOverflow = 0xff, // You read more data than is available
};

static constexpr uint32_t SdepMaxPayload = 16;
struct SdepMsg {
  uint8_t type;
  uint8_t cmd_low;
  uint8_t cmd_high;
  struct __attribute__((packed)) {
    uint8_t len : 7;
    uint8_t more : 1;
  };
  uint8_t payload[SdepMaxPayload];

  SdepMsg() = default;
  SdepMsg(enum ble_cmd command)
      : type(SdepCommand),
        cmd_low(command & 0xff),
        cmd_high(command >> 8),
        len(0),
        more(false) {
    static_assert(sizeof(*this) == 20, "msg is correctly packed");
  }

  template <typename Iter>
  SdepMsg(enum ble_cmd command, Iter start, uint8_t datalen, bool moredata)
      : type(SdepCommand),
        cmd_low(command & 0xff),
        cmd_high(command >> 8),
        len(datalen),
        more(moredata && len == SdepMaxPayload) {
    static_assert(sizeof(*this) == 20, "msg is correctly packed");
    copy_n(start, datalen, payload);
  }

} __attribute__((packed));

enum ble_system_event_bits {
  BleSystemConnected = 0,
  BleSystemDisconnected = 1,
  BleSystemUartRx = 8,
  BleSystemMidiRx = 10,
};
}

// A dummy output pin class for systems that have the SPIFriend
// integrated in a way that it is always powered on
struct AlwaysOnPowerPin {
  static inline void setup() {}
  static inline void set() {}
  static inline void clear() {}
  static inline void write(bool x) {}
  static inline void toggle() {}
  static inline bool read() {
    return true;
  }
};

template <typename Pin>
struct ChipSelectHolder {
  ChipSelectHolder() {
    Pin::clear();
  }
  ~ChipSelectHolder() {
    Pin::set();
  }
  ChipSelectHolder(const ChipSelectHolder&) = delete;
  ChipSelectHolder(ChipSelectHolder&&) = delete;
  void backOff() {
    Pin::set();
    _delay_us(25);
    Pin::clear();
  }
};

template <
    typename ResetPin,
    typename CSPin,
    typename IRQPin,
    bool useHardwareReset,
    typename PowerPin>
class SPIFriend
    : public Task<
          SPIFriend<ResetPin, CSPin, IRQPin, useHardwareReset, PowerPin>,
          configMINIMAL_STACK_SIZE * 3,
          2> {
  bool connected_;
  bool initialized_;
  bool configured_;
  Report lastReport_;
  SPI::Settings settings_;
  using ChipSelect = ChipSelectHolder<CSPin>;
  using SdepMsg = spifriend::SdepMsg;
  enum CommandType {
    KeyReport,
    ConsumerKeyReport,
  };

  struct Command {
    uint8_t CommandType;
    union {
      Report report;
      uint16_t consumer;
    } u;
  } __attribute__((packed));
  using CommandQueue = Queue<Command, 8>;
  CommandQueue queue_;

  bool send(const SdepMsg* msg, TickType_t timeout) {
    auto spi = SPI::start(settings_);
    auto startTick = xTaskGetTickCount();
    ChipSelect cs;

    do {
      if (spi->transferByte(msg->type) != spifriend::SdepSlaveNotReady) {
        spi->sendBytes(
            &msg->cmd_low,
            sizeof(*msg) - (1 + sizeof(msg->payload)) + msg->len);
        return true;
      }

      cs.backOff();

    } while (xTaskGetTickCount() - startTick < timeout);
    return false;
  }

  bool waitForSpiData(TickType_t timeout) {
    auto startTick = xTaskGetTickCount();
    do {
      if (IRQPin::read()) {
        return true;
      }
      _delay_us(1);
    } while (xTaskGetTickCount() - startTick < timeout);
    logln(makeConstString("waitForSpiData fail"));
    return false;
  }

  bool recv(SdepMsg* msg, TickType_t timeout) {
    if (!waitForSpiData(timeout)) {
      return false;
    }

    auto spi = SPI::start(settings_);
    auto startTick = xTaskGetTickCount();
    ChipSelect cs;

    do {
      // Read the command type, waiting for the data to be ready
      msg->type = spi->readByte();
      if (msg->type == spifriend::SdepSlaveNotReady ||
          msg->type == spifriend::SdepSlaveOverflow) {
        // Release it and let it initialize
        cs.backOff();
        continue;
      }

      // Read the rest of the header
      spi->recvBytes(&msg->cmd_low, sizeof(*msg) - (1 + sizeof(msg->payload)));

      // and get the payload if there is any
      if (msg->len <= spifriend::SdepMaxPayload) {
        spi->recvBytes(msg->payload, msg->len);
      }
      return true;

    } while (xTaskGetTickCount() - startTick < timeout);
    logln(makeConstString("spi not ready"));
    return false;
  }

  void hwinit() {
    IRQPin::setup();
    CSPin::setup();
    ResetPin::setup();
    PowerPin::setup();

    CSPin::set();
    connected_ = false;
  }

  bool reset() {
    lastReport_.clear();
    logln(makeConstString("reset ble"));
    PowerPin::set();
    if (useHardwareReset) {
      ResetPin::set();
      ResetPin::clear();
      _delay_ms(10);
      ResetPin::set();
    } else {
      SdepMsg reset(spifriend::BleInitialize);

      if (!send(&reset, 1000 / portTICK_PERIOD_MS)) {
        return false;
      }
    }

    delayMilliseconds(1000);
    return true;
  }

  template <typename CmdString, typename RespString>
  bool atCommand(CmdString&& cmd, RespString& result, TickType_t timeout) {
    auto start = cmd.begin();
    auto end = cmd.end();
    logln(cmd);

    while (end - start > spifriend::SdepMaxPayload) {
      SdepMsg msg(
          spifriend::BleAtWrapper, start, spifriend::SdepMaxPayload, true);
      if (!send(&msg, timeout)) {
        logln(makeConstString("send failed"));
        return false;
      }
      start += spifriend::SdepMaxPayload;
    }

    SdepMsg msg(spifriend::BleAtWrapper, start, end - start, false);
    if (!send(&msg, timeout)) {
      logln(makeConstString("send final failed"));
      return false;
    }

    result.clear();
    while (true) {
      if (!recv(&msg, timeout)) {
        logln(makeConstString("recv fail"));
        return false;
      }
      result.append(msg.payload, msg.len);
      if (!msg.more) {
        // We read the entire (possibly fragmented) response
        break;
      }
    }
    logln("{", result, "}");

    // Now we're looking for "OK" at the end of the textual buffer
    result.rtrim();
    if (result.endsWith(makeConstString("OK"))) {
      return true;
    }
    logln(makeConstString("not ok in {"), result, "}");
    return false;
  }

  bool configureKeyboard() {
    FixedString<32> resp;
    constexpr TickType_t tickTimeout = 1000 / portTICK_PERIOD_MS;
    // This string concatenation is too complex for our makeConstString inline
    // asm magic to handle, so we separate it out here.
    static const char GapName[] __CLACKER_PROGMEM =
        "AT+GAPDEVNAME=" CLACKER_USB_PRODUCT " " CLACKER_USB_MANUFACTURER;
    return atCommand(makeConstString("ATE=0"), resp, tickTimeout) &&
        atCommand(
               makeConstString("AT+GAPINTERVALS=10,30,,"), resp, tickTimeout) &&
        atCommand(
               ProgMemString<sizeof(GapName) - 1, char>(
                   makeProgMemIter(GapName)),
               resp,
               tickTimeout) &&
        atCommand(makeConstString("AT+BLEHIDEN=1"), resp, tickTimeout) &&
        atCommand(makeConstString("AT+BLEPOWERLEVEL=-40"), resp, tickTimeout) &&
        atCommand(makeConstString("ATZ"), resp, tickTimeout);
  }

 public:
  void run() {
    hwinit();

    do {
      initialized_ = reset();
      delayMilliseconds(1000);
    } while (!initialized_);
    logln(makeConstString("ble init"));

    do {
      configured_ = configureKeyboard();
      delayMilliseconds(1000);
    } while (!configured_);
    logln(makeConstString("configd"));

    while (true) {
      Command cmd;
      FixedString<48> cmdStr;

      if (queue_.recv(cmd, 1000).hasValue()) {
        switch (cmd.CommandType) {
          case KeyReport:
            if (cmd.u.report == lastReport_) {
              break;
            }
            cmdStr.clear();
            cmdStr.append(makeConstString("AT+BLEKEYBOARDCODE="));
            cmdStr.appendHex(cmd.u.report.mods);
            cmdStr.append(makeConstString("-00-"));
            cmdStr.appendHex(cmd.u.report.keys[0]);
            cmdStr.append(makeConstString("-"));
            cmdStr.appendHex(cmd.u.report.keys[1]);
            cmdStr.append(makeConstString("-"));
            cmdStr.appendHex(cmd.u.report.keys[2]);
            cmdStr.append(makeConstString("-"));
            cmdStr.appendHex(cmd.u.report.keys[3]);
            cmdStr.append(makeConstString("-"));
            cmdStr.appendHex(cmd.u.report.keys[4]);
            cmdStr.append(makeConstString("-"));
            cmdStr.appendHex(cmd.u.report.keys[5]);
            atCommand(cmdStr, cmdStr, 1000 / portTICK_PERIOD_MS);
            lastReport_ = cmd.u.report;
            break;
          case ConsumerKeyReport:
            cmdStr.clear();
            cmdStr.append(makeConstString("AT+BLEHIDCONTROLKEY=0x"));
            cmdStr.appendHex(cmd.u.consumer);
            atCommand(cmdStr, cmdStr, 1000 / portTICK_PERIOD_MS);
            break;
        }
      }
    }
  }
  void basicReport(const Report& report) {
    Command cmd;
    cmd.CommandType = KeyReport;
    cmd.u.report = report;
    queue_.send(cmd);
  }
  void consumerKey(uint16_t code) {
    Command cmd;
    cmd.CommandType = ConsumerKeyReport;
    cmd.u.consumer = code;
    queue_.send(cmd);
  }
};

using Feather32U4BLE = SPIFriend<
    gpio::avr::OutputPin<gpio::avr::PortD, 4>, // ResetPin
    gpio::avr::OutputPin<gpio::avr::PortB, 4>, // CSPin
    gpio::avr::InputPin<gpio::avr::PortE, 6>, // IRQ
    true, // useHardwareReset
    AlwaysOnPowerPin>;
}
