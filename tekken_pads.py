#!/usr/bin/env python3
"""Turn every connected keyboard into its own virtual Xbox-style pad for Tekken 7."""
import argparse, asyncio, sys
from evdev import InputDevice, UInput, AbsInfo, list_devices, ecodes as e

# key -> pad button
BUTTONS = {
    e.KEY_A: e.BTN_NORTH,   # 1  (Xbox X)
    e.KEY_S: e.BTN_WEST,    # 2  (Xbox Y)
    e.KEY_Z: e.BTN_SOUTH,   # 3  (Xbox A)
    e.KEY_X: e.BTN_EAST,    # 4  (Xbox B)
    e.KEY_Q: e.BTN_TL,      # 1+2 -> LB (bind in-game)
    e.KEY_W: e.BTN_TR,      # 3+4 -> RB (bind in-game)
    e.KEY_1: e.BTN_THUMBL,  # Rage Art (bind in-game)
    e.KEY_2: e.BTN_THUMBR,  # Ki charge (bind in-game)
    e.KEY_ENTER: e.BTN_START,
    e.KEY_V: e.BTN_SELECT,
}

# key -> trigger axis (pressed = full)
TRIGGERS = {
    e.KEY_E: e.ABS_Z,       # 1+4 -> LT (bind in-game)
    e.KEY_F: e.ABS_RZ,      # 2+3 -> RT (bind in-game)
}

# key -> (hat axis, direction)
HAT = {
    e.KEY_UP:    (e.ABS_HAT0Y, -1),
    e.KEY_DOWN:  (e.ABS_HAT0Y,  1),
    e.KEY_RIGHT: (e.ABS_HAT0X,  1),
    e.KEY_LEFT:  (e.ABS_HAT0X, -1),
    e.KEY_D:     (e.ABS_HAT0X,  1),   # right
    e.KEY_C:     (e.ABS_HAT0X, -1),   # left
}

EXIT_KEY = e.KEY_F12
MAPPED = set(BUTTONS) | set(TRIGGERS) | set(HAT)

# Declare a full Xbox 360 layout so games/SDL index the buttons and axes correctly
PAD_BUTTONS = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST, e.BTN_TL, e.BTN_TR,
               e.BTN_SELECT, e.BTN_START, e.BTN_MODE, e.BTN_THUMBL, e.BTN_THUMBR]
STICK = AbsInfo(0, -32768, 32767, 16, 128, 0)
CAPS = {
    e.EV_KEY: PAD_BUTTONS,
    e.EV_ABS: [
        (e.ABS_X, STICK), (e.ABS_Y, STICK),
        (e.ABS_Z, AbsInfo(0, 0, 255, 0, 0, 0)),
        (e.ABS_RX, STICK), (e.ABS_RY, STICK),
        (e.ABS_RZ, AbsInfo(0, 0, 255, 0, 0, 0)),
        (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
        (e.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
    ],
}

# A device counts as a keyboard if it has all of these keys
NEEDED = [e.KEY_A, e.KEY_Z, e.KEY_1, e.KEY_ENTER, e.KEY_F12]
# Virtual devices to never grab
IGNORE = ["tekken pad", "input-remapper", "ydotool"]


class Pad:
    def __init__(self, name):
        self.ui = UInput(CAPS, name=name, vendor=0x045e, product=0x028e, version=0x0110)
        self.held = set()   # (device path, key code)
        self.last = {}

    def _set(self, etype, code, value):
        if self.last.get((etype, code)) != value:
            self.last[(etype, code)] = value
            self.ui.write(etype, code, value)

    def refresh(self):
        keys = {code for _, code in self.held}
        for b in PAD_BUTTONS:
            self._set(e.EV_KEY, b, int(any(BUTTONS.get(k) == b for k in keys)))
        for axis in (e.ABS_Z, e.ABS_RZ):
            self._set(e.EV_ABS, axis, 255 if any(TRIGGERS.get(k) == axis for k in keys) else 0)
        for axis in (e.ABS_HAT0X, e.ABS_HAT0Y):
            v = sum(HAT[k][1] for k in keys if k in HAT and HAT[k][0] == axis)
            self._set(e.EV_ABS, axis, max(-1, min(1, v)))
        self.ui.syn()


def find_keyboards(skip):
    skip = [s.lower() for s in IGNORE + skip]
    groups = {}
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        keys = dev.capabilities().get(e.EV_KEY, [])
        if any(s in dev.name.lower() for s in skip) or not all(k in keys for k in NEEDED):
            dev.close()
            continue
        # Nodes of the same physical keyboard share a phys prefix -> one pad
        base = (dev.phys or path).split("/input")[0]
        groups.setdefault(base, []).append(dev)
    return [groups[k] for k in sorted(groups)]


async def feed(dev, pad, stop):
    try:
        async for ev in dev.async_read_loop():
            if ev.type != e.EV_KEY or ev.value == 2:
                continue
            if ev.code == EXIT_KEY and ev.value == 1:
                stop.set()
                return
            if ev.code in MAPPED:
                if ev.value == 1:
                    pad.held.add((dev.path, ev.code))
                else:
                    pad.held.discard((dev.path, ev.code))
                pad.refresh()
    except OSError:
        print(f"{dev.name} disconnected")
    finally:
        pad.held = {h for h in pad.held if h[0] != dev.path}
        pad.refresh()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="show detected keyboards and exit")
    ap.add_argument("--skip", action="append", default=[], metavar="TEXT",
                    help="ignore keyboards whose name contains TEXT (repeatable)")
    args = ap.parse_args()

    groups = find_keyboards(args.skip)
    for i, devs in enumerate(groups, 1):
        print(f"Pad {i}: " + ", ".join(f"{d.name} ({d.path})" for d in devs))
    if args.list:
        return
    if not groups:
        sys.exit("No keyboards found (are you running with sudo?)")

    pads, tasks, grabbed = [], [], []
    stop = asyncio.Event()
    try:
        for i, devs in enumerate(groups, 1):
            pad = Pad(f"Tekken Pad {i}")
            pads.append(pad)
            for dev in devs:
                while dev.active_keys():          # wait for all keys to be released
                    await asyncio.sleep(0.05)
                try:
                    dev.grab()
                except OSError as err:
                    print(f"Could not grab {dev.name}: {err}")
                    continue
                grabbed.append(dev)
                tasks.append(asyncio.create_task(feed(dev, pad, stop)))
        if not tasks:
            sys.exit("Could not grab any keyboard.")
        print("Running. Press F12 on any keyboard to quit.")
        await stop.wait()
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for d in grabbed:
            try:
                d.ungrab()
            except Exception:
                pass
        for p in pads:
            p.ui.close()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
