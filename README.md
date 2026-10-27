# tekken-pads

Play local two-player games on Linux with **two keyboards that use the same keys**.

Each connected keyboard becomes its own virtual Xbox-style gamepad, so the game sees two separate controllers. Built for Tekken 7 (Steam / Proton), but it works with any game that supports gamepads.

This is a Linux alternative to [djlastnight's Keyboard Splitter](https://github.com/djlastnight/Keyboard-Splitter), which is Windows-only.

## Features

- **Auto-detects keyboards** on every launch. No device paths to pass in.
- **Works with one keyboard, two, or different brands.** Handy when you travel and bring whatever is available.
- **Same layout on every keyboard**, because each one feeds its own pad.
- **Real D-pad hat axis** and analog triggers, so games read it like a normal controller.
- **Grabs the keyboards exclusively** while running, so keypresses never reach your desktop or window manager (Hyprland, Sway, KDE, etc.).
- **Waits for keys to be released before grabbing**, which avoids the stuck-Enter problem.
- Handles keyboards that expose multiple input nodes (media keys, etc.) as a single keyboard.
- Releases everything cleanly when you quit or unplug a keyboard.

## Requirements

- Linux with `uinput` available (standard on most distros)
- Python 3.8+
- [`python-evdev`](https://python-evdev.readthedocs.io/)
- Root access, or a user with permission to read `/dev/input/*` and write `/dev/uinput`

Install evdev:

```bash
# Arch / CachyOS / Manjaro
sudo pacman -S python-evdev

# Debian / Ubuntu
sudo apt install python3-evdev

# Fedora
sudo dnf install python3-evdev

# Anything else
pip install evdev
```

## Usage

```bash
sudo python tekken_pads.py --list                 # show detected keyboards and exit
sudo python tekken_pads.py                        # grab every keyboard found
sudo python tekken_pads.py --skip "AT Translated" # ignore keyboards whose name contains this text
```

- Plug in your keyboards **before** starting the script. Detection happens once at launch.
- Press **F12** on any keyboard to quit and release everything.
- `--skip` can be repeated and matches part of the name shown by `--list`. Use it to keep a laptop keyboard free for typing.

> **Heads up:** while the script runs, the grabbed keyboards stop typing and stop triggering your desktop shortcuts. Keep a mouse or trackpad handy, or use `--skip` on the keyboard you want to keep using.

**Suggested workflow:** open Steam and navigate to the game's Play button, start the script, then click Play with your mouse or trackpad.

## Default layout

Every keyboard uses the same layout.

| Key | Tekken input | Pad output |
|---|---|---|
| `A` | 1 | X |
| `S` | 2 | Y |
| `Z` | 3 | A |
| `X` | 4 | B |
| `Q` | 1+2 | LB |
| `W` | 3+4 | RB |
| `E` | 1+4 | LT |
| `F` | 2+3 | RT |
| `1` | Rage Art | Left stick click |
| `2` | Ki charge | Right stick click |
| Arrow keys | Up / Down / Left / Right | D-pad |
| `D` | Right | D-pad right |
| `C` | Left | D-pad left |
| `Enter` | Start | Start |
| `V` | Select | Select |
| `F12` | Quit | n/a |

Tekken reads left and right as absolute directions and converts them to forward and back depending on which side you are standing on. So `D` is forward for the player on the left and back for the player on the right. This is how it works on any controller.

You can change the layout by editing the `BUTTONS`, `TRIGGERS`, and `HAT` dictionaries at the top of `tekken_pads.py`.

## Tekken 7 setup

1. **Disable Steam Input for the game** if the pads behave oddly: Steam → Tekken 7 → Properties → Controller → *Disable Steam Input*.
2. Start the script **before** launching the game.
3. In Tekken 7's controller settings, press a button on each keyboard to assign it to a player slot.
4. Bind the shortcut buttons once per pad:

| Pad input | Bind in-game as |
|---|---|
| LB | 1+2 |
| RB | 3+4 |
| LT | 1+4 |
| RT | 2+3 |
| Left stick click | Rage Art |
| Right stick click | Ki charge |

## Running without sudo (optional)

Add your user to the `input` group and allow access to `uinput`:

```bash
sudo usermod -aG input "$USER"
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' \
  | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Log out and back in for the group change to take effect.

## Troubleshooting

**The script says no keyboards were found.**
Run it with `sudo`, and check `--list`. A device is treated as a keyboard only if it has the letter keys, `1`, Enter, and F12.

**Could not grab a keyboard / device busy.**
Something else has it grabbed. Stop other remappers (for example `sudo systemctl stop input-remapper`) and try again.

**A key keeps repeating after I start or quit the script.**
Tap that key once on the affected keyboard. The script waits for all keys to be released before grabbing to avoid this, but it can still happen if a key is pressed at the exact moment of exit.

**Some inputs drop on a laptop keyboard.**
Many laptop keyboards cannot register certain combinations of 3 or more simultaneous keys (ghosting). That is a hardware limit. The combo keys (`Q`, `W`, `E`, `F`) help because each is a single keypress.

**The game does not see the pads.**
Check that they exist with `sudo evtest`. You should see "Tekken Pad 1" (and "Tekken Pad 2" with two keyboards). Make sure the script was started before the game, and try disabling Steam Input for the game.

**Pad numbering changed between sessions.**
Pad order depends on which keyboards are connected. Re-claim the slots in the game's controller screen by pressing a button on each keyboard.

## Input latency

The script adds one extra hop (keyboard → kernel → Python → uinput → game), which is typically well under 1 ms. Your keyboard's polling rate, display latency, and vsync settings matter far more. If you want to squeeze out a bit more, run it with real-time priority:

```bash
sudo chrt -f 50 python tekken_pads.py
```

## Limitations

- Keyboards are detected once at launch. Restart the script after plugging one in.
- Linux only.
- No analog stick output. Directions are digital via the D-pad hat axis, which is all fighting games need.


## Credits

Inspired by [djlastnight's Keyboard Splitter](https://github.com/djlastnight/Keyboard-Splitter) for Windows. Not affiliated with it, or with Bandai Namco or Valve.
