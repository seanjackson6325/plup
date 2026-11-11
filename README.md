# Plup 🐧

A Club Penguin-style penguin, rendered like a RollerCoaster Tycoon sprite, who lives on your desktop with an LLM for a brain. You talk to him through an MS-DOS style console.

    python3 ~/plup/plup.py        # or launch "Plup" from the app grid

- **Left-click** Plup to open/close the chat bubble. **Drag** to move him. **Right-click** for the menu.
- **Hover** on him for a pat, **scroll** over him to tickle, **click 5 times fast** to make him dizzy, **drag** him and he flails then lands. Right-click > **Do a trick** plays any animation.

- **Todo list:** TODO.EXE opens at start. Type a task and press ENTER to add it, tick it off (Plup celebrates), `x` removes it. Toggle it with F3, `[Todo]` in the console, or the right-click menu. Saved to `~/.config/plup/todo.json`.

## Animations (`animations.py`)

- **While working:** thinking dots with flipper on chin, typing on a laptop (Bash), magnifying glass (Read/Grep/Glob), pencil (Edit/Write), spinning globe (web), beak moving while replying.
- **Reactions:** drop-in greeting, cheer/hop/spin when a task finishes, party hat + confetti then a `!` if it finished while the console was closed, heart eyes when you say thanks, sad sweat drop on errors, dizzy stars, petting, tickling, being dragged and landing, falling asleep and waking up startled, goodbye jump.
- **Idle tricks** (random every 6-16 s): wave, look around, yawn, stretch, hop, spin, dance, sing, laugh, sneeze, eat a fish, throw a snowball, read a book, hot cocoa, cool shades, propeller hat hover, puffle visit, backflip, shiver in the snow, tap foot, have an idea, bow, juggle snowballs, peek, and, when the console is closed, waddle or belly-slide across the desktop.

To add one: write a function returning `[F(ticks, **pose), ...]`, decorate it with `@trick("Label", weight)`; pose keys are listed in `sprite.NEUTRAL`.

## Settings

Open **Settings** with F2 or `[Set]` in the console, or from the right-click menu (which also has a quick **Console theme** switcher). Everything is saved to `~/.config/plup/config.json`:

| key | default | meaning |
|---|---|---|
| `brain` | `"claude-code"` | which brain to use (see `brain.py`) |
| `model` | `null` | model alias for the brain, e.g. `"sonnet"` |
| `permission_mode` | `"auto"` | Claude Code permission mode (`auto`, `acceptEdits`, `plan`, `bypassPermissions`, ...) |
| `cwd` | `"~"` | Plup's working directory |
| `scale` | `3` | pixel size |
| `theme` | `"dos"` | console theme: dos, terminal (follows your kitty config), bisqwit, aero, norton, turbo, amber, green, c64, win31, clubpenguin |
| `color` | `"blue"` | Club Penguin colour: blue, red, green, black, pink, purple, yellow, orange, lime, aqua, brown, peach, dark green, light blue, or `"#rrggbb"` |
| `sleep_after_seconds` | `180` | idle time before napping |
| `idle_tricks` | `true` | random tricks while idle (also in the right-click menu) |
| `wander` | `true` | allowed to waddle and slide around the desktop |
| `todo_on_start` | `true` | open the TODO.EXE list when Plup starts |

## Files

- `plup.py`: windows, animation, chat UI
- `themes.py`: console themes; `terminal` is read live from kitty's config
- `animations.py`: state loops and all the tricks
- `sprite.py`: procedural pixel art; each frame is lit 3D ellipsoids, palettized and dithered (`python3 sprite.py sheet.png [color]` dumps all poses)
- `brain.py`: the `Brain` interface plus `ClaudeCodeBrain`, which runs `claude -p` headless with streaming. To use another LLM, subclass `Brain`, implement `send(prompt, emit)`, and add it to `BRAINS`.

The console font is PxPlus IBM VGA 9x16; `~/.config/fontconfig/conf.d/60-pxplus-crisp.conf` turns off smoothing for it so it stays pixel-sharp.
