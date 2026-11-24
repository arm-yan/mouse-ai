#include <Arduino.h>
#include <BleMouse.h>

// Advertises as a standard BLE HID mouse. The target machine pairs with it
// like any Bluetooth mouse; commands arrive over USB serial from the AI side.
BleMouse bleMouse("MouseAI", "MouseAI", 100);

static const size_t BUF_LEN = 64;
static char buf[BUF_LEN];
static size_t bufPos = 0;

static uint8_t parseButton(char c) {
  switch (c) {
    case 'l': return MOUSE_LEFT;
    case 'r': return MOUSE_RIGHT;
    case 'm': return MOUSE_MIDDLE;
    default:  return 0;
  }
}

static void handleLine(char* line) {
  while (*line == ' ') line++;
  if (*line == '\0') return;

  char cmd = line[0];
  char* args = line + 1;

  if (cmd == '?') {
    Serial.println(bleMouse.isConnected() ? "OK CONNECTED" : "OK DISCONNECTED");
    return;
  }

  if (!bleMouse.isConnected()) {
    Serial.println("ERR NOTCONNECTED");
    return;
  }

  switch (cmd) {
    case 'M': {  // M <dx> <dy>  — relative move, each axis -127..127
      int dx = 0, dy = 0;
      if (sscanf(args, "%d %d", &dx, &dy) == 2) {
        dx = constrain(dx, -127, 127);
        dy = constrain(dy, -127, 127);
        bleMouse.move((signed char)dx, (signed char)dy);
        Serial.println("OK");
      } else {
        Serial.println("ERR ARGS");
      }
      break;
    }
    case 'S': {  // S <n>  — vertical scroll, -127..127
      int n = 0;
      if (sscanf(args, "%d", &n) == 1) {
        n = constrain(n, -127, 127);
        bleMouse.move(0, 0, (signed char)n);
        Serial.println("OK");
      } else {
        Serial.println("ERR ARGS");
      }
      break;
    }
    case 'C':    // C <l|r|m>  — click
    case 'D':    // D <l|r|m>  — press (button down)
    case 'U': {  // U <l|r|m>  — release (button up)
      while (*args == ' ') args++;
      uint8_t b = parseButton(*args);
      if (!b) { Serial.println("ERR ARGS"); break; }
      if (cmd == 'C')      bleMouse.click(b);
      else if (cmd == 'D') bleMouse.press(b);
      else                 bleMouse.release(b);
      Serial.println("OK");
      break;
    }
    default:
      Serial.println("ERR CMD");
  }
}

void setup() {
  Serial.begin(115200);
  bleMouse.begin();
  Serial.println("READY");
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufPos > 0) {
        buf[bufPos] = '\0';
        handleLine(buf);
        bufPos = 0;
      }
    } else if (bufPos < BUF_LEN - 1) {
      buf[bufPos++] = c;
    } else {
      bufPos = 0;
      Serial.println("ERR OVERFLOW");
    }
  }
}
