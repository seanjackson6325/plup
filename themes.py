"""Console themes. A theme is a dict of colours and a font; css() turns it
into the GTK stylesheet for the console and the settings window.

"terminal" isn't fixed: it is read from the user's kitty config each time, so
Plup matches whatever the terminal currently looks like."""
import os
import re

BASE = {
    "font": "PxPlus IBM VGA 9x16", "size": 16, "pixel": True, "radius": 0, "double": True,
    "title": "≡ PLUP.EXE",
}

THEMES = {
    "dos": dict(
        BASE, label="MS-DOS Edit",
        bg="#0000aa", fg="#aaaaaa", bright="#ffffff", user="#ffff55", tool="#55ffff",
        code="#55ff55", error="#ff5555", meta="#5555ff", prompt="#ffff55", caret="#ffff55",
        bar_bg="#aaaaaa", bar_fg="#000000", status_bg="#00aaaa", status_fg="#000000",
        hover_bg="#000000", hover_fg="#aaaaaa", border="#aaaaaa", outer="#000000",
        sel_bg="#aaaaaa", sel_fg="#0000aa", slider="#00aaaa", trough="#000080"),
    # colours from ~/.config/micro/colorschemes/bisqwit.micro (Bisqwit's "that editor")
    "bisqwit": dict(
        BASE, label="Bisqwit (micro)", title="PLUP.CPP", double=False,
        bg="#000000", fg="#a8a8a8", bright="#f8f8f8", user="#f8f8f8", tool="#00a8a8",
        code="#00a8d0", error="#f80000", meta="#a860f8", prompt="#80f860", caret="#a8a8a8",
        bar_bg="#a8a8a8", bar_fg="#000000", status_bg="#a8a8a8", status_fg="#000000",
        hover_bg="#00a8a8", hover_fg="#000000", border="#383838", outer="#000000",
        sel_bg="#a8a8a8", sel_fg="#000000", slider="#a8a8a8", trough="#000000"),
    # colours from ~/.config/kitty/aero.conf
    "aero": dict(
        BASE, label="Frutiger Aero", title="Plup", font="DejaVu Sans Mono", size=15,
        pixel=False, radius=10, double=False,
        bg="#0a2342", fg="#e6f3ff", bright="#ffffff", user="#ffd45a", tool="#5ae6f0",
        code="#7fe05a", error="#ff7a5c", meta="#8ccaff", prompt="#7fe0ff", caret="#7fe0ff",
        bar_bg="#a3d4ff", bar_fg="#04182e", status_bg="#26507d", status_fg="#cfe4f7",
        hover_bg="#5ab4ff", hover_fg="#04182e", border="#5ab4ff", outer="#04182e",
        sel_bg="#3399ff", sel_fg="#ffffff", slider="#5ab4ff", trough="#0a1e36"),
    "norton": dict(
        BASE, label="Norton Commander", title="  Left  Files  Commands",
        bg="#0000aa", fg="#55ffff", bright="#ffffff", user="#ffff55", tool="#ffffff",
        code="#55ff55", error="#ff5555", meta="#00aaaa", prompt="#ffffff", caret="#ffffff",
        bar_bg="#00aaaa", bar_fg="#000000", status_bg="#000000", status_fg="#55ffff",
        hover_bg="#000000", hover_fg="#55ffff", border="#55ffff", outer="#000000",
        sel_bg="#00aaaa", sel_fg="#000000", slider="#55ffff", trough="#000080"),
    "turbo": dict(
        BASE, label="Turbo Pascal", title="≡ File Edit Search Run",
        bg="#0000aa", fg="#ffff55", bright="#ffffff", user="#ffffff", tool="#55ffff",
        code="#55ff55", error="#ff5555", meta="#aaaaaa", prompt="#ffffff", caret="#ffff55",
        bar_bg="#aaaaaa", bar_fg="#000000", status_bg="#aaaaaa", status_fg="#aa0000",
        hover_bg="#00aa00", hover_fg="#000000", border="#ffffff", outer="#000000",
        sel_bg="#00aaaa", sel_fg="#000000", slider="#00aaaa", trough="#000080"),
    "amber": dict(
        BASE, label="Amber CRT", title="PLUP", double=False,
        bg="#1a0f00", fg="#ffb000", bright="#ffd27f", user="#ffcc55", tool="#ff9900",
        code="#ffc040", error="#ff6a3d", meta="#a06a00", prompt="#ffd27f", caret="#ffb000",
        bar_bg="#ffb000", bar_fg="#1a0f00", status_bg="#ffb000", status_fg="#1a0f00",
        hover_bg="#1a0f00", hover_fg="#ffb000", border="#ffb000", outer="#000000",
        sel_bg="#ffb000", sel_fg="#1a0f00", slider="#ffb000", trough="#1a0f00"),
    "green": dict(
        BASE, label="Green phosphor", title="PLUP", double=False,
        bg="#001400", fg="#33ff66", bright="#b4ffc4", user="#b4ffc4", tool="#00cc44",
        code="#66ff99", error="#ccff00", meta="#118833", prompt="#b4ffc4", caret="#33ff66",
        bar_bg="#33ff66", bar_fg="#001400", status_bg="#33ff66", status_fg="#001400",
        hover_bg="#001400", hover_fg="#33ff66", border="#33ff66", outer="#000000",
        sel_bg="#33ff66", sel_fg="#001400", slider="#33ff66", trough="#001400"),
    "c64": dict(
        BASE, label="Commodore 64", title="**** PLUP 64 ****", font="PxPlus IBM VGA 8x16",
        double=False,
        bg="#40318d", fg="#7869c4", bright="#ffffff", user="#ffffff", tool="#6abfc6",
        code="#9ae29b", error="#b86962", meta="#a0a0ff", prompt="#ffffff", caret="#7869c4",
        bar_bg="#7869c4", bar_fg="#40318d", status_bg="#7869c4", status_fg="#40318d",
        hover_bg="#40318d", hover_fg="#ffffff", border="#7869c4", outer="#7869c4",
        sel_bg="#7869c4", sel_fg="#40318d", slider="#7869c4", trough="#40318d"),
    "win31": dict(
        BASE, label="Windows 3.1", title="Plup - Notepad", font="DejaVu Sans", size=14,
        pixel=False, double=False,
        bg="#ffffff", fg="#000000", bright="#000080", user="#000080", tool="#008080",
        code="#008000", error="#800000", meta="#808080", prompt="#000000", caret="#000000",
        bar_bg="#000080", bar_fg="#ffffff", status_bg="#c0c0c0", status_fg="#000000",
        hover_bg="#c0c0c0", hover_fg="#000000", border="#000000", outer="#000000",
        sel_bg="#000080", sel_fg="#ffffff", slider="#c0c0c0", trough="#e0e0e0"),
    "clubpenguin": dict(
        BASE, label="Club Penguin", title="Plup's Igloo", font="DejaVu Sans", size=14,
        pixel=False, radius=14, double=False,
        bg="#ffffff", fg="#003366", bright="#00264d", user="#e05a00", tool="#1f5fc8",
        code="#2a8a2a", error="#c8222c", meta="#6a8aaa", prompt="#1f5fc8", caret="#1f5fc8",
        bar_bg="#1f5fc8", bar_fg="#ffffff", status_bg="#8fd0ff", status_fg="#003366",
        hover_bg="#ffd23a", hover_fg="#003366", border="#8fd0ff", outer="#0b3f8f",
        sel_bg="#8fd0ff", sel_fg="#003366", slider="#1f5fc8", trough="#d4efff"),
}
ORDER = ["dos", "terminal", "bisqwit", "aero", "norton", "turbo", "amber", "green", "c64",
         "win31", "clubpenguin"]


def _kitty_settings(path=os.path.expanduser("~/.config/kitty/kitty.conf"), seen=None):
    """kitty.conf as a dict, following `include` lines (later lines win)."""
    seen = seen if seen is not None else set()
    out = {}
    path = os.path.realpath(path)
    if path in seen or not os.path.isfile(path):
        return out
    seen.add(path)
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, val = line.partition(" ")
            val = val.strip()
            if key == "include":
                out.update(_kitty_settings(os.path.join(os.path.dirname(path), os.path.expanduser(val)), seen))
            else:
                out[key] = val
    return out


def terminal_theme():
    """The theme of the terminal right now, from the kitty config."""
    k = _kitty_settings()
    c = lambda n, d: k.get(f"color{n}", d)  # noqa: E731
    fam = k.get("font_family", "monospace")
    m = re.search(r'family="([^"]+)"', fam)
    font = m.group(1) if m else fam
    try:
        size = round(float(k.get("font_size", "12")) * 4 / 3)
    except ValueError:
        size = 16
    pixel = bool(re.search(r"Px437|PxPlus|VGA", font))
    bg, fg = k.get("background", "#000000"), k.get("foreground", "#aaaaaa")
    bar_bg = k.get("active_tab_background", c(7, "#aaaaaa"))
    bar_fg = k.get("active_tab_foreground", bg)
    return dict(
        BASE, label="Terminal (kitty)", title="plup — kitty", font=font, size=size, pixel=pixel,
        double=False,
        bg=bg, fg=fg, bright=c(15, "#ffffff"), user=c(11, "#ffff55"), tool=c(14, "#55ffff"),
        code=c(10, "#55ff55"), error=c(9, "#ff5555"), meta=c(8, "#555555"), prompt=c(11, "#ffff55"),
        caret=k.get("cursor", fg), bar_bg=bar_bg, bar_fg=bar_fg, status_bg=bar_bg, status_fg=bar_fg,
        hover_bg=bg, hover_fg=fg, border=c(8, "#555555"), outer=bg,
        sel_bg=k.get("selection_background", fg), sel_fg=k.get("selection_foreground", bg),
        slider=c(7, "#aaaaaa"), trough=bg)


def get(name):
    if name == "terminal":
        return terminal_theme()
    return THEMES.get(name, THEMES["dos"])


def label(name):
    return "Terminal (kitty)" if name == "terminal" else THEMES[name]["label"]


def css(t):
    r = t["radius"]
    inner = 2 if t["double"] else 0
    big = t["size"] * 2 if t["pixel"] else round(t["size"] * 1.6)
    return f"""
#buddy, #chat, #settings, #todo {{ background-color: transparent; box-shadow: none; border: none; }}
#card, #card * {{
  font-family: "{t['font']}", monospace; font-size: {t['size']}px;
  border-radius: 0; box-shadow: none; text-shadow: none; background-image: none;
}}
#card {{ background-color: {t['bg']}; border: 2px solid {t['outer']}; border-radius: {r}px; }}
#titlebar {{ background-color: {t['bar_bg']}; border-radius: {max(0, r - 2)}px {max(0, r - 2)}px 0 0; }}
#titlebar label {{ color: {t['bar_fg']}; padding: 2px 6px; }}
#titlebar button {{
  background-color: {t['bar_bg']}; border: none; min-height: 0; min-width: 0; padding: 2px 6px; margin: 0;
}}
#titlebar button label {{ padding: 0; }}
#titlebar button:hover {{ background-color: {t['hover_bg']}; }}
#titlebar button:hover label {{ color: {t['hover_fg']}; }}
#logframe {{ border: 2px solid {t['border']}; margin: 6px 6px 0 6px; padding: {inner}px; }}
#logframe-inner {{ border: {inner}px solid {t['border']}; padding: 2px; }}
#log, #log text {{ background-color: {t['bg']}; color: {t['fg']}; }}
#log text selection {{ background-color: {t['sel_bg']}; color: {t['sel_fg']}; }}
#card scrollbar, #card scrollbar trough {{ background-color: {t['trough']}; border: none; min-width: 12px; }}
#card scrollbar slider {{ background-color: {t['slider']}; border: none; min-width: 12px; min-height: 16px; margin: 0; }}
#inputrow {{ margin: 6px 6px 6px 10px; }}
#prompt {{ color: {t['prompt']}; }}
#input {{
  background-color: {t['bg']}; color: {t['bright']}; border: none; padding: 0 0 0 4px;
  caret-color: {t['caret']}; -GtkWidget-cursor-aspect-ratio: 0.5; min-height: 0;
}}
#input selection {{ background-color: {t['sel_bg']}; color: {t['sel_fg']}; }}
#statusbar {{ background-color: {t['status_bg']}; border-radius: 0 0 {max(0, r - 2)}px {max(0, r - 2)}px; }}
#statusbar label {{ color: {t['status_fg']}; padding: 2px 6px; }}
#statusbar button {{
  background-color: {t['status_bg']}; border: none; min-height: 0; min-width: 0; padding: 2px 6px; margin: 0;
}}
#statusbar button label {{ color: {t['status_fg']}; padding: 0; }}
#statusbar button:hover {{ background-color: {t['hover_bg']}; }}
#statusbar button:hover label {{ color: {t['hover_fg']}; }}
#card.full, #card.full * {{ font-size: {big}px; }}
#stage {{ background-color: {t['bg']}; padding: 0 12px 6px 12px; }}

/* settings */
#form {{ padding: 10px 14px; }}
#form label {{ color: {t['fg']}; }}
#form label.heading {{ color: {t['bright']}; }}
#form label.hint {{ color: {t['meta']}; }}
#form button, #form combobox button, #form spinbutton, #form entry {{
  background-color: {t['bg']}; color: {t['bright']}; border: 1px solid {t['border']};
  min-height: 0; padding: 2px 6px;
}}
#form button label, #form combobox button cellview {{ color: {t['bright']}; }}
#form button:hover, #form combobox button:hover {{ background-color: {t['sel_bg']}; }}
#form button:hover label {{ color: {t['sel_fg']}; }}
#form spinbutton entry, #form spinbutton button {{ border: none; color: {t['bright']}; background-color: {t['bg']}; }}
#form checkbutton label {{ color: {t['fg']}; }}
#form check {{
  background-color: {t['bg']}; border: 2px solid {t['border']}; color: {t['bright']};
  min-width: 12px; min-height: 12px; -gtk-icon-source: none;
}}
#form check:checked {{ background-color: {t['tool']}; }}
#todo #form button {{ padding: 0 6px; border: none; }}
menu, .menu, menuitem {{ font-family: "{t['font']}", monospace; }}
"""
