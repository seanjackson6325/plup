#!/usr/bin/env python3
"""Plup - a tiny pixel-art penguin desktop buddy with an LLM for a brain."""
import json
import os
import random
import re
import signal
import sys
import threading
from collections import OrderedDict

# Run through XWayland so the buddy can float on top and be placed freely
# (native Wayland on GNOME doesn't let apps position or pin windows).
os.environ.setdefault("GDK_BACKEND", "x11")

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

try:  # optional: lets clicks pass through the transparent pixels around Plup
    gi.require_foreign("cairo")
    import cairo
    HAVE_CAIRO = True
except ImportError:
    HAVE_CAIRO = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animations  # noqa: E402
import sprite  # noqa: E402
import themes  # noqa: E402
from brain import make_brain  # noqa: E402

CONFIG_PATH = os.path.expanduser("~/.config/plup/config.json")
TODO_PATH = os.path.expanduser("~/.config/plup/todo.json")
DEFAULTS = {
    "brain": "claude-code",
    "model": None,              # e.g. "sonnet"; None = Claude Code's default
    "permission_mode": "auto",  # what Plup may do without asking
    "cwd": "~",                 # where Plup works
    "scale": 3,
    "color": "blue",            # any Club Penguin colour, or "#rrggbb"
    "theme": "dos",             # console theme, see themes.py
    "sleep_after_seconds": 180,  # 0 = never nap
    "idle_tricks": True,        # do random tricks when idle
    "wander": True,             # allowed to waddle/slide around the desktop
    "todo_on_start": True,      # open the todo list when Plup starts
    "x": None,
    "y": None,
}
IDLE_GAP = (60, 160)  # ticks between idle tricks
THANKS = re.compile(r"\b(thanks|thank you|thx|ty|love (you|u)|good (job|boy|penguin)|great job|"
                    r"awesome|you rock|nice one|well done)\b", re.I)



def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(**changes):
    """Write only these keys, leaving the user's other settings untouched."""
    try:
        with open(CONFIG_PATH) as f:
            saved = json.load(f)
    except (OSError, ValueError):
        saved = {}
    saved.update(changes)
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(saved, f, indent=2)


def make_transparent(win):
    visual = win.get_screen().get_rgba_visual()
    if visual:
        win.set_visual(visual)


def grid_pixbuf(grid, scale):
    w, h = sprite.W * scale, sprite.H * scale
    return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(sprite.to_rgba(grid, scale)),
                                           GdkPixbuf.Colorspace.RGB, True, 8, w, h, w * 4)


class Buddy(Gtk.Window):
    """The penguin itself: a borderless, transparent, always-on-top window.

    He is always either playing a trick (a one-shot animation from
    animations.TRICKS) or looping the animation for his current state."""

    def __init__(self, app):
        super().__init__(title="Plup")
        self.app = app
        self.scale = app.cfg["scale"]
        self.set_name("buddy")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()
        make_transparent(self)
        self.image = Gtk.Image()
        self.add(self.image)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK
                        | Gdk.EventMask.LEAVE_NOTIFY_MASK | Gdk.EventMask.SCROLL_MASK)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)
        self.connect("scroll-event", self.on_scroll)
        self.connect("realize", lambda *_: self.update_shape())

        self.rng = random.Random()
        self.t = 0
        self.state = "idle"          # idle think talk work sleep alert drag
        self.tool = None             # tool he's using while in "work"
        self.tool_since = 0          # tick that tool kind started
        self.trick = None            # [frames, index, ticks left, name, then]
        self.next_trick = self.rng.randint(*IDLE_GAP)
        self.blink_at = 30
        self.last_talk = -100
        self.last_activity = 0
        self.press = None
        self.dragging = False
        self.clicks = []
        self.hover_timer = None
        self.grids = OrderedDict()   # penguin renders, keyed by pose
        self.frames = OrderedDict()  # finished pixbufs, keyed by pose + effects
        self.key = None
        self.grid = None
        self.advance()
        GLib.timeout_add(animations.TICK_MS, self.tick)

    # ---- behaviour ---------------------------------------------------------
    def play(self, name, then=None, **kw):
        frames = animations.build(name, self.rng, **kw)
        self.trick = [frames, 0, frames[0][0], name, then]
        self.advance()

    def playing(self):
        return self.trick[3] if self.trick else None

    def set_state(self, state):
        self.state = state
        self.advance()

    def poke(self):
        self.last_activity = self.t

    def talk(self):
        self.last_talk, self.tool = self.t, None

    def work(self, tool):
        kind = animations.TOOL_KIND.get(tool)
        if self.state != "work" or kind != animations.TOOL_KIND.get(self.tool):
            self.tool_since = self.t
        self.last_talk, self.tool = -100, tool

    def tick(self):
        self.t += 1
        if self.app.busy and self.state != "drag":
            talking = self.t - self.last_talk < 8
            self.state = "talk" if talking else ("work" if self.tool else "think")
        elif not self.app.busy and self.state in ("think", "talk", "work"):
            self.state = "idle"

        if self.trick:
            frames, i, left, name, then = self.trick
            if frames[i][1].get("move"):
                self.step(frames[i][1]["move"])
            if left > 1:
                self.trick[2] = left - 1
            elif i + 1 < len(frames):
                self.trick[1:3] = [i + 1, frames[i + 1][0]]
            else:
                self.trick = None
                if any(f[1].get("move") for f in frames):
                    self.save_position()
                if then:
                    then()
        elif self.state == "idle" and not self.press:
            self.idle_behaviour()
        self.advance()
        return True

    def idle_behaviour(self):
        cfg = self.app.cfg
        chat_open = self.app.chat.get_visible()
        nap = cfg["sleep_after_seconds"] * 1000 // animations.TICK_MS
        if nap and not chat_open and self.t - self.last_activity > nap:
            self.play("doze", then=lambda: self.set_state("sleep"))
        elif cfg["idle_tricks"] and self.t >= self.next_trick:
            self.next_trick = self.t + self.rng.randint(*IDLE_GAP)
            name = animations.pick_idle(self.rng, cfg["wander"] and not chat_open)
            if animations.TRICKS[name][3]:
                self.play(name, direction=self.roomier_side())
            else:
                self.play(name)

    def wake(self):
        self.poke()
        if self.state == "sleep":
            self.state = "idle"
            self.play("surprised")
            return True
        return False

    # ---- moving around the desktop ----------------------------------------
    def workarea(self):
        x, y = self.get_position()
        w, h = self.get_size()
        mon = Gdk.Display.get_default().get_monitor_at_point(x + w // 2, y + h // 2)
        return mon.get_workarea()

    def roomier_side(self):
        x, _ = self.get_position()
        w, _ = self.get_size()
        area = self.workarea()
        left, right = x - area.x, area.x + area.width - (x + w)
        if min(left, right) < 250:
            return -1 if left > right else 1
        return self.rng.choice((-1, 1))

    def step(self, dx):
        x, y = self.get_position()
        w, _ = self.get_size()
        area = self.workarea()
        nx = max(area.x, min(area.x + area.width - w, x + dx))
        if nx != x:
            self.move(nx, y)
            if self.app.chat.get_visible():
                self.app.chat.place_near(self)

    def reset_art(self):
        """Colour or size changed: drop cached frames and redraw, feet staying put."""
        x, y = self.get_position()
        ow, oh = self.get_size()
        self.scale = self.app.cfg["scale"]
        self.grids.clear()
        self.frames.clear()
        self.key = None
        self.advance()
        nw, nh = sprite.W * self.scale, sprite.H * self.scale
        self.resize(nw, nh)
        self.move(x + (ow - nw) // 2, y + oh - nh)
        GLib.timeout_add(100, lambda: self.save_position() or False)

    def save_position(self):
        x, y = self.get_position()
        self.app.cfg.update(x=x, y=y)
        save_config(x=x, y=y)

    # ---- drawing -----------------------------------------------------------
    def pose(self):
        if self.trick:
            p = dict(self.trick[0][self.trick[1]][1])
            p.pop("move", None)
        else:
            p = animations.loop(self.state, self.t, self.tool, self.tool_since)
        if p.get("eyes", "open") == "open" and not p.get("glasses") and self.t >= self.blink_at:
            p["eyes"] = "blink"
            if self.t > self.blink_at:
                self.blink_at = self.t + self.rng.randint(25, 70)
        return p

    def advance(self):
        p = self.pose()
        fx = tuple(p.pop("fx", ()))
        pkey = tuple(sorted(p.items()))
        key = (pkey, fx)
        if key == self.key:
            return
        self.key = key
        frame = self.frames.get(key)
        if frame is None:
            grid = self.grids.get(pkey)
            if grid is None:
                grid = self.grids[pkey] = sprite.render_penguin(p, self.app.cfg["color"])
                if len(self.grids) > 800:
                    self.grids.popitem(last=False)
            full = sprite.compose(grid, fx, p.get("lift", 0), p.get("ox", 0))
            frame = self.frames[key] = (full, grid_pixbuf(full, self.scale))
            if len(self.frames) > 500:
                self.frames.popitem(last=False)
        else:
            self.frames.move_to_end(key)
        self.grid, pixbuf = frame
        self.image.set_from_pixbuf(pixbuf)
        self.update_shape()
        if self.app.chat.full:
            self.app.chat.show_plup(pixbuf)

    def update_shape(self):
        """Only the penguin's own pixels catch clicks; the rest is click-through."""
        if not HAVE_CAIRO or not self.get_realized() or not self.grid:
            return
        s, rects = self.scale, []
        for y, row in enumerate(self.grid):
            x = 0
            while x < len(row):
                if row[x]:
                    x0 = x
                    while x < len(row) and row[x]:
                        x += 1
                    rects.append(cairo.RectangleInt(x0 * s, y * s, (x - x0) * s, s))
                else:
                    x += 1
        self.input_shape_combine_region(cairo.Region(rects))

    # ---- mouse -------------------------------------------------------------
    def on_enter(self, *_):
        if self.hover_timer:
            GLib.source_remove(self.hover_timer)
        self.hover_timer = GLib.timeout_add(1500, self.on_hover)

    def on_leave(self, _w, ev):
        if ev.detail != Gdk.NotifyType.INFERIOR and self.hover_timer:
            GLib.source_remove(self.hover_timer)
            self.hover_timer = None

    def on_hover(self):
        """Resting the pointer on him counts as a pat on the head."""
        self.hover_timer = None
        if self.state == "idle" and not self.trick and not self.press:
            self.poke()
            self.play("pet")
        return False

    def on_scroll(self, *_):
        """Scrolling over him tickles."""
        if not self.wake() and self.playing() != "laugh":
            self.play("laugh")
        return True

    def on_press(self, _w, ev):
        if ev.type != Gdk.EventType.BUTTON_PRESS:
            return True
        if ev.button == 1:
            wx, wy = self.get_position()
            self.press = (ev.x_root, ev.y_root, wx, wy)
            self.dragging = False
        elif ev.button == 3:
            self.app.show_menu(ev)
        return True

    def on_motion(self, _w, ev):
        if not self.press:
            return False
        px, py, wx, wy = self.press
        dx, dy = ev.x_root - px, ev.y_root - py
        if not self.dragging and abs(dx) + abs(dy) > 4:
            self.dragging = True
            self.trick = None
            self.state = "drag"
        if self.dragging:
            self.move(int(wx + dx), int(wy + dy))
            if self.app.chat.get_visible():
                GLib.idle_add(self.app.chat.place_near, self)
        return True

    def on_release(self, _w, ev):
        if ev.button != 1 or not self.press:
            return True
        self.press = None
        if self.dragging:
            self.dragging = False
            self.state = "idle"
            self.poke()
            self.play("land")
            self.save_position()
            return True
        self.clicked(ev.time)
        return True

    def clicked(self, time, toggle=True):
        if self.wake():
            return  # the first click only wakes him up
        self.clicks = [c for c in self.clicks if self.t - c < 30] + [self.t]
        if len(self.clicks) >= 5:
            self.clicks = []
            self.play("dizzy")
            return
        if not self.trick:
            self.play("boing")
        if toggle:
            self.app.toggle_chat(time)


class ChatWindow(Gtk.Window):
    """Plup's speech bubble: conversation log plus an input box."""

    def __init__(self, app):
        super().__init__(title="Plup")
        self.app = app
        self.set_name("chat")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        # a normal window: GNOME only lets normal windows go fullscreen
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_default_size(520, 520)
        make_transparent(self)
        self.connect("delete-event", lambda *_: self.close() or True)
        self.connect("key-press-event", self.on_key)
        self.connect("window-state-event", self.on_window_state)

        card = self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.set_name("card")
        self.add(card)
        self.full = False

        bar = Gtk.Box()
        bar.set_name("titlebar")
        self.title_label = Gtk.Label(label="≡ PLUP.EXE", xalign=0)
        bar.pack_start(self.title_label, False, False, 0)
        for label, cb in (("[X]", lambda *_: self.close()),
                          ("[Full]", lambda *_: self.set_full(not self.full)),
                          ("[Set]", lambda *_: app.open_settings()),
                          ("[Todo]", lambda *_: app.toggle_todo()),
                          ("[New]", lambda *_: app.new_chat())):
            btn = Gtk.Button(label=label, relief=Gtk.ReliefStyle.NONE)
            btn.connect("clicked", cb)
            bar.pack_end(btn, False, False, 0)
            if label == "[Full]":
                self.full_btn = btn
        card.pack_start(bar, False, False, 0)

        self.buf = Gtk.TextBuffer()
        for name, props in {
            "you": {"foreground": "#ffff55", "pixels_above_lines": 8},
            "body": {},
            "tool": {"foreground": "#55ffff"},
            "code": {"foreground": "#55ff55"},
            "bold": {"foreground": "#ffffff"},
            "error": {"foreground": "#ff5555"},
            "meta": {"foreground": "#5555ff"},
        }.items():
            self.buf.create_tag(name, **props)
        self.end_mark = self.buf.create_mark(None, self.buf.get_end_iter(), False)

        self.view = Gtk.TextView(buffer=self.buf, editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.view.set_name("log")
        for side in ("left", "right", "top", "bottom"):
            getattr(self.view, f"set_{side}_margin")(4)
        scroll = Gtk.ScrolledWindow()
        # EXTERNAL: wrap to whatever width we get instead of demanding the text's
        # width (otherwise the window can't shrink back after fullscreen)
        scroll.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_width(300)
        scroll.add(self.view)
        inner = Gtk.Box()  # two nested boxes make the double-line DOS border
        inner.set_name("logframe-inner")
        inner.pack_start(scroll, True, True, 0)
        frame = Gtk.Box()
        frame.set_name("logframe")
        frame.pack_start(inner, True, True, 0)
        middle = Gtk.Box()
        middle.pack_start(frame, True, True, 0)
        # in fullscreen Plup lives here, inside the console
        self.stage = Gtk.EventBox(valign=Gtk.Align.END, no_show_all=True)
        self.stage.set_name("stage")
        self.stage.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK
                              | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.stage_img = Gtk.Image()
        self.stage_img.show()
        self.stage.add(self.stage_img)
        self.stage.connect("button-press-event", self.on_stage_click)
        self.stage.connect("scroll-event", lambda *_: app.buddy.on_scroll())
        self.stage.connect("enter-notify-event", lambda *a: app.buddy.on_enter())
        self.stage.connect("leave-notify-event", lambda w, ev: app.buddy.on_leave(w, ev))
        middle.pack_start(self.stage, False, False, 0)
        card.pack_start(middle, True, True, 0)

        row = Gtk.Box()
        row.set_name("inputrow")
        prompt = Gtk.Label(label="C:\\PLUP>")
        prompt.set_name("prompt")
        self.entry = Gtk.Entry(has_frame=False)
        self.entry.set_name("input")
        self.entry.connect("activate", lambda *_: self.submit())
        row.pack_start(prompt, False, False, 0)
        row.pack_start(self.entry, True, True, 0)
        card.pack_start(row, False, False, 0)

        status_bar = Gtk.Box()
        status_bar.set_name("statusbar")
        self.hint = Gtk.Label(xalign=0)
        status_bar.pack_start(self.hint, False, False, 0)
        self.status = Gtk.Label(label="READY", xalign=1)
        status_bar.pack_end(self.status, False, False, 0)
        card.pack_start(status_bar, False, False, 0)

        card.show_all()
        self.update_hint()
        self.reply_mark = None
        self.segments = []
        self.render_pending = False
        self.greet()

    # ---- placement ---------------------------------------------------------
    def place_near(self, buddy):
        if self.full:
            return False
        bx, by = buddy.get_position()
        bw, bh = buddy.get_size()
        cw, ch = self.get_size()
        mon = Gdk.Display.get_default().get_monitor_at_point(bx + bw // 2, by + bh // 2)
        area = mon.get_workarea()
        x = bx - cw - 4 if bx - cw - 4 >= area.x else bx + bw + 4
        y = by + bh - ch
        x = max(area.x, min(x, area.x + area.width - cw))
        y = max(area.y, min(y, area.y + area.height - ch))
        self.move(x, y)
        return False

    def retheme(self, t):
        self.title_label.set_text(t["title"])
        for tag, key in (("you", "user"), ("tool", "tool"), ("code", "code"), ("bold", "bright"),
                         ("error", "error"), ("meta", "meta")):
            self.buf.get_tag_table().lookup(tag).set_property("foreground", t[key])

    def update_hint(self):
        self.hint.set_text("F2=Setup  F3=Todo  Alt+Enter=Window  Esc=Window" if self.full else
                           "F2=Setup  F3=Todo  Alt+Enter=Full  Esc=Hide")
        self.full_btn.set_label("[Win]" if self.full else "[Full]")

    def set_full(self, on):
        """Alt+Enter, DOS style: ask the window manager for fullscreen. The
        layout switches in on_window_state, once fullscreen really happened."""
        if on:
            if not self.get_visible():
                self.app.toggle_chat()
            self.fullscreen()
        else:
            self.unfullscreen()

    def on_window_state(self, _w, ev):
        if ev.changed_mask & Gdk.WindowState.FULLSCREEN:
            self.apply_full(bool(ev.new_window_state & Gdk.WindowState.FULLSCREEN))
        return False

    def apply_full(self, on):
        """Fullscreen layout: bigger text, and Plup moves inside the console,
        shown big next to the text, instead of floating on the desktop."""
        if on == self.full:
            return
        buddy = self.app.buddy
        self.full = on
        ctx = self.card.get_style_context()
        if on:
            mon = Gdk.Display.get_default().get_monitor_at_window(self.get_window())
            if mon.get_geometry().width >= 1600:  # 2x keeps the VGA font pixel-exact
                ctx.add_class("full")
            self.stage.show()
            buddy.hide()
            buddy.key = None  # force a redraw onto the stage
            buddy.advance()
        else:
            ctx.remove_class("full")
            self.stage.hide()
            buddy.show_all()
            GLib.timeout_add(150, self.restore_size)
        self.update_hint()
        self.entry.grab_focus()
        self.scroll_end()

    def restore_size(self):
        self.resize(520, 520)  # GTK won't shrink back on its own after fullscreen
        self.place_near(self.app.buddy)
        return False

    def show_plup(self, pixbuf):
        w, h = pixbuf.get_width(), pixbuf.get_height()
        self.stage_img.set_from_pixbuf(pixbuf.scale_simple(w * 2, h * 2, GdkPixbuf.InterpType.NEAREST))

    def on_stage_click(self, _w, ev):
        if ev.type == Gdk.EventType.BUTTON_PRESS:
            if ev.button == 1:
                self.app.buddy.clicked(ev.time, toggle=False)
            elif ev.button == 3:
                self.app.show_menu(ev)
        return True

    def close(self):
        if self.full:
            self.unfullscreen()
            self.apply_full(False)
        self.hide()

    def on_key(self, _w, ev):
        alt = ev.state & Gdk.ModifierType.MOD1_MASK
        if ev.keyval == Gdk.KEY_F11 or (alt and ev.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter)):
            self.set_full(not self.full)
            return True
        if ev.keyval == Gdk.KEY_F2:
            self.app.open_settings()
            return True
        if ev.keyval == Gdk.KEY_F3:
            self.app.toggle_todo()
            return True
        if ev.keyval == Gdk.KEY_Escape:
            if self.full:
                self.set_full(False)
            else:
                self.hide()
            return True
        if ev.state & Gdk.ModifierType.CONTROL_MASK and ev.keyval in (Gdk.KEY_n, Gdk.KEY_N):
            self.app.new_chat()
            return True
        if ev.state & Gdk.ModifierType.CONTROL_MASK and ev.keyval in (Gdk.KEY_c, Gdk.KEY_C) \
                and self.app.busy and not self.entry.get_selection_bounds():
            self.app.cancel()
            return True
        return False

    # ---- log ---------------------------------------------------------------
    def scroll_end(self):
        self.buf.move_mark(self.end_mark, self.buf.get_end_iter())
        GLib.idle_add(lambda: self.view.scroll_to_mark(self.end_mark, 0, False, 0, 0) and False)

    def append(self, text, *tags):
        self.buf.insert_with_tags_by_name(self.buf.get_end_iter(), text, *tags)
        self.scroll_end()

    def greet(self):
        self.append("PLUP-DOS Version 1.0\n"
                    "(C) Copyright Plup Penguin Corp 1993. All rights reserved.\n\n", "bold")
        self.append("Hi! I'm Plup. Type a task at the prompt and press ENTER, and I'll "
                    "waddle off and do it.\n", "body")

    def clear(self):
        self.buf.set_text("")
        self.reply_mark = None
        self.greet()

    def add_user(self, text):
        self.append(f"C:\\PLUP>{text}\n", "you")

    def start_reply(self):
        self.reply_mark = self.buf.create_mark(None, self.buf.get_end_iter(), True)
        self.segments = []
        self.render()

    def add_text(self, text):
        if self.segments and self.segments[-1][0] == "text":
            self.segments[-1] = ("text", self.segments[-1][1] + text)
        else:
            self.segments.append(("text", text))
        self.queue_render()

    def add_break(self):
        if self.segments and self.segments[-1][0] == "text":
            self.segments.append(("text", "\n\n"))

    def add_tool(self, desc):
        self.segments.append(("tool", desc))
        self.queue_render()

    def add_error(self, msg):
        self.segments.append(("error", msg))
        self.queue_render()

    def add_meta(self, msg):
        self.segments.append(("meta", msg))
        self.queue_render()

    def queue_render(self):
        if not self.render_pending:
            self.render_pending = True
            GLib.timeout_add(50, self.render)

    def render(self):
        self.render_pending = False
        if not self.reply_mark:
            return False
        start = self.buf.get_iter_at_mark(self.reply_mark)
        self.buf.delete(start, self.buf.get_end_iter())
        it = self.buf.get_iter_at_mark(self.reply_mark)
        if not self.segments:
            self.buf.insert_with_tags_by_name(it, "_\n", "body")
        for i, (kind, val) in enumerate(self.segments):
            if kind == "text":
                insert_markdown(self.buf, it, val.strip("\n") if i == 0 else val)
                self.buf.insert(it, "\n")
            elif kind == "tool":
                name, _, detail = val.partition(": ")
                line = f"► {name.upper()}" + (f"  {detail}" if detail else "")
                self.buf.insert_with_tags_by_name(it, line + "\n", "tool")
            elif kind == "error":
                self.buf.insert_with_tags_by_name(it, f"ERROR: {val}\n", "error")
            elif kind == "meta":
                self.buf.insert_with_tags_by_name(it, f"{val}\n", "meta")
        self.scroll_end()
        return False

    # ---- input -------------------------------------------------------------
    def submit(self):
        if self.app.busy:
            self.app.cancel()
            return
        text = self.entry.get_text().strip()
        if text:
            self.entry.set_text("")
            self.app.send(text)

    def set_busy(self, busy):
        self.status.set_text("BUSY" if busy else "READY")
        if busy:
            GLib.timeout_add(150, self.spin)

    def spin(self):
        if not self.app.busy:
            return False
        text = self.status.get_text()
        frame = "|/-\\"[(GLib.get_monotonic_time() // 150000) % 4]
        self.status.set_text(text[:-1] + frame if text.endswith(tuple("|/-\\")) else text + " " + frame)
        return True


INLINE = re.compile(r"(\*\*[^*\n]+\*\*|`[^`\n]+`)")


def insert_markdown(buf, it, text):
    """Just enough markdown for chat: code blocks, inline code, bold, headings, bullets."""
    in_code = False
    lines = text.split("\n")
    for n, line in enumerate(lines):
        nl = "\n" if n < len(lines) - 1 else ""
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            buf.insert_with_tags_by_name(it, line + nl, "body", "code")
            continue
        heading = re.match(r"#{1,6}\s+(.*)", line)
        if heading:
            buf.insert_with_tags_by_name(it, heading.group(1) + nl, "body", "bold")
            continue
        line = re.sub(r"^(\s*)[-*]\s+", r"\1• ", line)
        for part in INLINE.split(line):
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                buf.insert_with_tags_by_name(it, part[2:-2], "body", "bold")
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                buf.insert_with_tags_by_name(it, part[1:-1], "body", "code")
            elif part:
                buf.insert_with_tags_by_name(it, part, "body")
        if nl:
            buf.insert(it, nl)


PERMISSIONS = [
    ("auto", "auto: acts, risky things blocked"),
    ("acceptEdits", "acceptEdits: may edit files"),
    ("plan", "plan: looks, doesn't touch"),
    ("bypassPermissions", "bypass: anything goes (!)"),
]


class SettingsWindow(Gtk.Window):
    """SETUP.EXE: console theme, penguin and brain settings. Changes apply at once."""

    def __init__(self, app):
        super().__init__(title="Plup Setup")
        self.app = app
        cfg = app.cfg
        self.set_name("settings")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        make_transparent(self)
        self.connect("delete-event", lambda *_: self.hide() or True)
        self.connect("key-press-event", self.on_key)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.set_name("card")
        self.add(card)
        bar = Gtk.Box()
        bar.set_name("titlebar")
        bar.pack_start(Gtk.Label(label="≡ SETUP.EXE", xalign=0), False, False, 0)
        close = Gtk.Button(label="[X]", relief=Gtk.ReliefStyle.NONE)
        close.connect("clicked", lambda *_: self.hide())
        bar.pack_end(close, False, False, 0)
        card.pack_start(bar, False, False, 0)

        form = Gtk.Grid(row_spacing=6, column_spacing=14)
        form.set_name("form")
        inner = Gtk.Box()
        inner.set_name("logframe-inner")
        inner.pack_start(form, True, True, 0)
        frame = Gtk.Box()
        frame.set_name("logframe")
        frame.pack_start(inner, True, True, 0)
        card.pack_start(frame, True, True, 0)
        rows = iter(range(100))

        def heading(text):
            lab = Gtk.Label(label=text, xalign=0)
            lab.get_style_context().add_class("heading")
            form.attach(lab, 0, next(rows), 2, 1)

        def add(text, widget, hint=None):
            r = next(rows)
            form.attach(Gtk.Label(label=text, xalign=0), 0, r, 1, 1)
            if hint:
                box = Gtk.Box(spacing=8)
                box.pack_start(widget, False, False, 0)
                h = Gtk.Label(label=hint, xalign=0)
                h.get_style_context().add_class("hint")
                box.pack_start(h, False, False, 0)
                widget = box
            form.attach(widget, 1, r, 1, 1)

        def combo(items, active, key, entry=False):
            w = Gtk.ComboBoxText.new_with_entry() if entry else Gtk.ComboBoxText()
            for ident, text in items:
                w.append(ident, text)
            if not w.set_active_id(active) and entry:
                w.get_child().set_text(active or "")
            w.connect("changed", lambda w: app.set_option(
                key, (w.get_child().get_text().strip() or None) if entry else w.get_active_id()))
            return w

        def check(text, key):
            w = Gtk.CheckButton(label=text, active=cfg[key])
            w.connect("toggled", lambda w: app.set_option(key, w.get_active()))
            return w

        def spin(lo, hi, step, key):
            w = Gtk.SpinButton.new_with_range(lo, hi, step)
            w.set_value(cfg[key])
            w.connect("value-changed", lambda w: app.set_option(key, w.get_value_as_int()))
            return w

        heading("CONSOLE")
        self.theme = combo([(n, themes.label(n)) for n in themes.ORDER], cfg["theme"], "theme")
        add("Theme", self.theme)

        heading("PENGUIN")
        colors = list(sprite.COLORS)
        if cfg["color"] not in colors:
            colors.append(cfg["color"])
        add("Colour", combo([(c, c.title() if not c.startswith("#") else c) for c in colors],
                            cfg["color"], "color"))
        add("Size", spin(2, 8, 1, "scale"), "pixels per pixel")
        add("Nap after", spin(0, 3600, 30, "sleep_after_seconds"), "seconds, 0 = never")
        add("", check("Random tricks", "idle_tricks"))
        add("", check("Wander around the desktop", "wander"))
        add("", check("Open todo list at start", "todo_on_start"))

        heading("BRAIN: " + app.brain.name.upper())
        add("Model", combo([(m, m) for m in ("opus", "sonnet", "haiku")], cfg["model"], "model",
                           entry=True), "empty = default")
        add("Permissions", combo(PERMISSIONS, cfg["permission_mode"], "permission_mode"))
        folder = Gtk.FileChooserButton(title="Plup's working folder",
                                       action=Gtk.FileChooserAction.SELECT_FOLDER)
        folder.set_filename(os.path.expanduser(cfg["cwd"]))
        folder.connect("file-set", lambda w: app.set_option("cwd", w.get_filename()))
        add("Works in", folder)
        note = Gtk.Label(label="Brain changes apply from your next message.", xalign=0)
        note.get_style_context().add_class("hint")
        form.attach(note, 0, next(rows), 2, 1)

        status = Gtk.Box()
        status.set_name("statusbar")
        status.pack_start(Gtk.Label(label="Changes apply instantly  Esc=Close", xalign=0), False, False, 0)
        ok = Gtk.Button(label="[ OK ]", relief=Gtk.ReliefStyle.NONE)
        ok.connect("clicked", lambda *_: self.hide())
        status.pack_end(ok, False, False, 0)
        card.pack_start(status, False, False, 0)
        card.show_all()

    def on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def open(self):
        chat = self.app.chat
        self.set_transient_for(chat if chat.get_visible() else None)
        self.theme.set_active_id(self.app.cfg["theme"])
        if not self.get_visible():
            self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT if chat.get_visible()
                              else Gtk.WindowPosition.CENTER)
        self.show()
        self.present()


class TodoWindow(Gtk.Window):
    """TODO.EXE: a little checklist, saved to ~/.config/plup/todo.json."""

    def __init__(self, app):
        super().__init__(title="Plup Todo")
        self.app = app
        self.set_name("todo")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_default_size(300, 320)
        make_transparent(self)
        self.connect("delete-event", lambda *_: self.hide() or True)
        self.connect("key-press-event", self.on_key)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.set_name("card")
        self.add(card)
        bar = Gtk.EventBox()  # drag the title bar to move the window
        bar.connect("button-press-event", self.on_bar_press)
        bar_box = Gtk.Box()
        bar_box.set_name("titlebar")
        bar.add(bar_box)
        bar_box.pack_start(Gtk.Label(label="≡ TODO.EXE", xalign=0), False, False, 0)
        for label, cb in (("[X]", lambda *_: self.hide()), ("[Clear done]", lambda *_: self.clear_done())):
            btn = Gtk.Button(label=label, relief=Gtk.ReliefStyle.NONE)
            btn.connect("clicked", cb)
            bar_box.pack_end(btn, False, False, 0)
        card.pack_start(bar, False, False, 0)

        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.list.set_name("form")
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.list)
        inner = Gtk.Box()
        inner.set_name("logframe-inner")
        inner.pack_start(scroll, True, True, 0)
        frame = Gtk.Box()
        frame.set_name("logframe")
        frame.pack_start(inner, True, True, 0)
        card.pack_start(frame, True, True, 0)

        row = Gtk.Box()
        row.set_name("inputrow")
        prompt = Gtk.Label(label="ADD>")
        prompt.set_name("prompt")
        self.entry = Gtk.Entry(has_frame=False, placeholder_text="type a task, press ENTER")
        self.entry.set_name("input")
        self.entry.connect("activate", lambda *_: self.add_item())
        row.pack_start(prompt, False, False, 0)
        row.pack_start(self.entry, True, True, 0)
        card.pack_start(row, False, False, 0)

        status = Gtk.Box()
        status.set_name("statusbar")
        self.count = Gtk.Label(xalign=0)
        status.pack_start(self.count, False, False, 0)
        status.pack_end(Gtk.Label(label="F3/Esc=Hide", xalign=1), False, False, 0)
        card.pack_start(status, False, False, 0)

        self.items = self.load()
        self.refresh()
        card.show_all()

    # ---- storage -----------------------------------------------------------
    def load(self):
        try:
            with open(TODO_PATH) as f:
                return [{"text": str(i["text"]), "done": bool(i.get("done"))} for i in json.load(f)]
        except (OSError, ValueError, TypeError, KeyError):
            return []

    def save(self):
        os.makedirs(os.path.dirname(TODO_PATH), exist_ok=True)
        with open(TODO_PATH, "w") as f:
            json.dump(self.items, f, indent=2)

    # ---- list --------------------------------------------------------------
    def refresh(self):
        for child in self.list.get_children():
            child.destroy()
        if not self.items:
            empty = Gtk.Label(label="Nothing to do. Add a task below!", xalign=0)
            empty.get_style_context().add_class("hint")
            self.list.pack_start(empty, False, False, 0)
        for i, item in enumerate(self.items):
            line = Gtk.Box(spacing=6)
            check = Gtk.CheckButton(active=item["done"])
            check.connect("toggled", lambda w, i=i: self.set_done(i, w.get_active()))
            text = Gtk.Label(label=item["text"], xalign=0, wrap=True)
            text.set_line_wrap_mode(2)  # Pango.WrapMode.WORD_CHAR
            if item["done"]:
                text.get_style_context().add_class("hint")
                text.set_markup(f"<s>{GLib.markup_escape_text(item['text'])}</s>")
            delete = Gtk.Button(label="x", relief=Gtk.ReliefStyle.NONE)
            delete.set_tooltip_text("Remove")
            delete.connect("clicked", lambda _w, i=i: self.remove(i))
            line.pack_start(check, False, False, 0)
            line.pack_start(text, True, True, 0)
            line.pack_end(delete, False, False, 0)
            self.list.pack_start(line, False, False, 0)
        self.list.show_all()
        left = sum(not i["done"] for i in self.items)
        self.count.set_text(f"{left} to do, {len(self.items) - left} done")

    def add_item(self):
        text = self.entry.get_text().strip()
        if not text:
            return
        self.entry.set_text("")
        self.items.append({"text": text, "done": False})
        self.save()
        self.refresh()

    def set_done(self, i, done):
        self.items[i]["done"] = done
        self.save()
        self.refresh()
        if done:
            self.app.buddy.poke()
            self.app.buddy.play(random.choice(animations.DONE_TRICKS))

    def remove(self, i):
        del self.items[i]
        self.save()
        self.refresh()

    def clear_done(self):
        self.items = [i for i in self.items if not i["done"]]
        self.save()
        self.refresh()

    # ---- window ------------------------------------------------------------
    def on_bar_press(self, _w, ev):
        if ev.button == 1 and ev.type == Gdk.EventType.BUTTON_PRESS:
            self.begin_move_drag(ev.button, int(ev.x_root), int(ev.y_root), ev.time)
        return False

    def on_key(self, _w, ev):
        if ev.keyval in (Gdk.KEY_Escape, Gdk.KEY_F3):
            self.hide()
            return True
        return False

    def open(self, time=Gdk.CURRENT_TIME):
        if not self.get_visible():
            mon = Gdk.Display.get_default().get_primary_monitor() or \
                Gdk.Display.get_default().get_monitor(0)
            area = mon.get_workarea()
            w, _ = self.get_size()
            self.move(area.x + area.width - w - 40, area.y + 40)
        self.show()
        self.present_with_time(time)
        self.entry.grab_focus()


class App:
    def __init__(self):
        self.cfg = load_config()
        self.brain = make_brain(self.cfg)
        self.busy = False

        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

        self.thanked = self.errored = self.quitting = False
        self.chat = ChatWindow(self)
        self.settings = None
        self.todo = TodoWindow(self)
        self.apply_theme()
        self.buddy = Buddy(self)
        self.buddy.connect("destroy", lambda *_: Gtk.main_quit())
        pixbuf = grid_pixbuf(sprite.render({"eyes": "happy"}, self.cfg["color"]), 3)
        self.buddy.set_icon(pixbuf)
        self.chat.set_icon(pixbuf)

        x, y = self.cfg["x"], self.cfg["y"]
        if x is None or y is None:
            area = Gdk.Display.get_default().get_primary_monitor() or \
                Gdk.Display.get_default().get_monitor(0)
            wa = area.get_workarea()
            w, h = sprite.W * self.cfg["scale"], sprite.H * self.cfg["scale"]
            x, y = wa.x + wa.width - w - 40, wa.y + wa.height - h - 20
        self.buddy.move(x, y)
        self.buddy.show_all()
        self.buddy.play("greet")
        if self.cfg["todo_on_start"]:
            self.todo.open()

    # ---- settings ----------------------------------------------------------
    def apply_theme(self):
        t = themes.get(self.cfg["theme"])
        self.css.load_from_data(themes.css(t).encode())
        self.chat.retheme(t)

    def set_option(self, key, value):
        if self.cfg.get(key) == value:
            return
        self.cfg[key] = value
        save_config(**{key: value})
        if key == "theme":
            self.apply_theme()
            if self.settings:
                self.settings.theme.set_active_id(value)
        elif key in ("color", "scale"):
            self.buddy.reset_art()
        elif key in ("model", "permission_mode", "cwd"):
            self.brain.configure(self.cfg)

    def open_settings(self):
        if not self.settings:
            self.settings = SettingsWindow(self)
        self.settings.open()

    def toggle_todo(self):
        if self.todo.get_visible():
            self.todo.hide()
        else:
            self.todo.open()

    # ---- chat --------------------------------------------------------------
    def toggle_chat(self, time=Gdk.CURRENT_TIME):
        self.buddy.poke()
        if self.chat.get_visible():
            self.chat.close()
            return
        if self.buddy.state == "alert":
            self.buddy.set_state("idle")
        self.chat.place_near(self.buddy)
        self.chat.show()
        self.chat.present_with_time(time)
        self.chat.entry.grab_focus()

    def new_chat(self):
        self.cancel()
        self.brain.reset()
        self.chat.clear()
        self.buddy.play("spin")

    def send(self, text):
        self.busy = True
        self.thanked, self.errored = bool(THANKS.search(text)), False
        self.buddy.poke()
        self.buddy.tool = None
        self.chat.add_user(text)
        self.chat.start_reply()
        self.chat.set_busy(True)
        self.chat.status.set_text("THINKING")

        def emit(kind, data):
            GLib.idle_add(self.on_event, kind, data)

        def work():
            try:
                self.brain.send(text, emit)
            except Exception as e:  # keep the buddy alive whatever the brain does
                emit("error", str(e))
            emit("finished", None)

        threading.Thread(target=work, daemon=True).start()

    def cancel(self):
        if self.busy:
            self.brain.cancel()
            self.chat.add_meta("^C")

    def on_event(self, kind, data):
        chat, buddy = self.chat, self.buddy
        if kind == "text":
            chat.add_text(data)
            buddy.talk()
            chat.status.set_text("TYPING")
        elif kind == "break":
            chat.add_break()
        elif kind == "tool":
            chat.add_tool(data)
            buddy.work(data.split(":")[0])
            chat.status.set_text(f"RUNNING {data.split(':')[0].upper()}")
        elif kind == "error":
            chat.add_error(data)
            self.errored = True
        elif kind == "done":
            cost = f" · ${data['cost']:.3f}" if data.get("cost") else ""
            chat.add_meta(f"{data.get('seconds', 0):.1f}s{cost}")
        elif kind == "finished":
            self.busy = False
            chat.set_busy(False)
            buddy.poke()
            if self.errored:
                buddy.play("sad")
            elif self.thanked:
                buddy.play("love")
            elif not chat.get_visible():  # celebrate, then wave a "!" until clicked
                buddy.play("celebrate", then=lambda: buddy.set_state("alert"))
            else:
                buddy.play(random.choice(animations.DONE_TRICKS))
        return False

    # ---- menu --------------------------------------------------------------
    def show_menu(self, ev):
        buddy = self.buddy
        menu = Gtk.Menu()

        def item(label, cb, parent=menu):
            mi = Gtk.MenuItem(label=label)
            mi.connect("activate", lambda *_: cb())
            parent.append(mi)

        def toggle(label, key):
            mi = Gtk.CheckMenuItem(label=label, active=self.cfg[key])
            mi.connect("toggled", lambda w: (self.cfg.update({key: w.get_active()}),
                                             save_config(**{key: w.get_active()})))
            menu.append(mi)

        item("Chat with Plup", self.toggle_chat)
        item("New conversation", self.new_chat)
        item("Exit full screen" if self.chat.full else "Full screen console",
             lambda: self.chat.set_full(not self.chat.full))
        tricks = Gtk.Menu()
        for name, (label, _, _, moves) in sorted(animations.TRICKS.items(), key=lambda kv: kv[1][0]):
            if moves:
                item(label, lambda n=name: buddy.play(n, direction=buddy.roomier_side()), tricks)
            else:
                item(label, lambda n=name: buddy.play(n), tricks)
        sub = Gtk.MenuItem(label="Do a trick")
        sub.set_submenu(tricks)
        menu.append(sub)
        theme_menu, group = Gtk.Menu(), None
        for name in themes.ORDER:
            mi = Gtk.RadioMenuItem(label=themes.label(name), group=group)
            group = group or mi
            mi.set_active(name == self.cfg["theme"])
            mi.connect("toggled", lambda w, n=name: w.get_active() and self.set_option("theme", n))
            theme_menu.append(mi)
        sub = Gtk.MenuItem(label="Console theme")
        sub.set_submenu(theme_menu)
        menu.append(sub)
        item("Hide todo list" if self.todo.get_visible() else "Todo list", self.toggle_todo)
        item("Settings…", self.open_settings)
        if buddy.state == "sleep":
            item("Wake up", buddy.wake)
        else:
            item("Nap time", lambda: buddy.play("doze", then=lambda: buddy.set_state("sleep")))
        menu.append(Gtk.SeparatorMenuItem())
        toggle("Random tricks", "idle_tricks")
        toggle("Wander around", "wander")
        menu.append(Gtk.SeparatorMenuItem())
        item("Goodbye, Plup", self.quit)
        menu.show_all()
        menu.attach_to_widget(buddy)
        menu.popup_at_pointer(ev)
        self._menu = menu

    def quit(self):
        if self.quitting:
            return
        self.quitting = True
        self.brain.cancel()
        self.chat.close()
        self.buddy.play("goodbye", then=Gtk.main_quit)


def main():
    App()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()


if __name__ == "__main__":
    main()
