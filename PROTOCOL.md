# MouseAI serial protocol

Line-based ASCII over USB serial at 115200 baud. Every command gets exactly
one reply line starting with `OK` or `ERR`. Lines end with `\n` (lone `\r`
is also accepted).

## Commands

| Command      | Meaning                                      | Reply |
|--------------|----------------------------------------------|-------|
| `?`          | BLE status                                   | `OK CONNECTED` or `OK DISCONNECTED` |
| `M <dx> <dy>`| Relative move; each axis clamped to -127..127| `OK`  |
| `S <n>`      | Vertical scroll, -127..127 (positive = up)   | `OK`  |
| `C <l\|r\|m>`| Click button                                 | `OK`  |
| `D <l\|r\|m>`| Button down (press and hold)                 | `OK`  |
| `U <l\|r\|m>`| Button up (release)                          | `OK`  |

## Errors

| Reply              | Cause                                           |
|--------------------|-------------------------------------------------|
| `ERR NOTCONNECTED` | No BLE host connected; only `?` works until one pairs |
| `ERR CMD`          | Unknown command letter                          |
| `ERR ARGS`         | Arguments missing or unparsable                 |
| `ERR OVERFLOW`     | Line longer than 63 bytes; it was discarded     |

On boot the firmware prints `READY` once. Hosts should ignore any
unsolicited lines that are not `OK...`/`ERR...` replies to their own
commands (boot messages, `READY`).

Larger moves than ±127 are the host's job: send several `M` commands
(`EspMouse.move()` in the Python library does this chunking).
