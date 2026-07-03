# macOS-styled GUI using Tkinter.

import os
import threading
import tkinter as tk

import config
import storage
import engine


# ---------------------------------------------------------------------------
# macOS-style button helpers (on Canvas)
# ---------------------------------------------------------------------------

def _create_rounded_rect_method():
    """Monkey-patch Canvas to support rounded rectangles."""
    def _create_rounded_rect(canvas, x1, y1, x2, y2, radius=8, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)
    tk.Canvas.create_rounded_rect = _create_rounded_rect


def _mac_button(canvas, x1, y1, x2, y2, text, fill, hover_fill, text_color, command,
                font_size=13, radius=8, tags=None):
    """Draw a rounded macOS-style button. Returns (rect_id, text_id)."""
    r = radius
    rect = canvas.create_rounded_rect(
        x1, y1, x2, y2, r, fill=fill, outline=fill, tags=tags,
    )
    txt = canvas.create_text(
        (x1 + x2) // 2, (y1 + y2) // 2, text=text,
        fill=text_color, font=(config.FONT_FAMILY, font_size), tags=tags,
    )
    canvas._mac_btn_data = getattr(canvas, "_mac_btn_data", {})
    canvas._mac_btn_data[(rect, txt)] = {
        "fill": fill, "hover_fill": hover_fill, "text_color": text_color,
        "command": command, "tags": tags,
    }
    return rect, txt


def _setup_mac_button_hover(canvas):
    """Bind hover/click events for all mac buttons on a canvas."""
    canvas.tag_bind("mac_btn", "<Enter>", lambda e: _on_btn_enter(canvas, e))
    canvas.tag_bind("mac_btn", "<Leave>", lambda e: _on_btn_leave(canvas, e))
    canvas.tag_bind("mac_btn_text", "<Enter>", lambda e: _on_btn_enter(canvas, e))
    canvas.tag_bind("mac_btn_text", "<Leave>", lambda e: _on_btn_leave(canvas, e))
    canvas.tag_bind("mac_btn", "<Button-1>", lambda e: _on_btn_click(canvas, e))
    canvas.tag_bind("mac_btn_text", "<Button-1>", lambda e: _on_btn_click(canvas, e))


def _on_btn_enter(canvas, event):
    items = canvas.find_withtag("current")
    if not items:
        return
    item = items[0]
    data = canvas._mac_btn_data
    for (rect, txt), btn_data in data.items():
        if item in (rect, txt):
            canvas.itemconfig(rect, fill=btn_data["hover_fill"], outline=btn_data["hover_fill"])
            return


def _on_btn_leave(canvas, event):
    items = canvas.find_withtag("current")
    if not items:
        return
    item = items[0]
    data = canvas._mac_btn_data
    for (rect, txt), btn_data in data.items():
        if item in (rect, txt):
            canvas.itemconfig(rect, fill=btn_data["fill"], outline=btn_data["fill"])
            return


def _on_btn_click(canvas, event):
    items = canvas.find_withtag("current")
    if not items:
        return
    item = items[0]
    data = canvas._mac_btn_data
    for (rect, txt), btn_data in data.items():
        if item in (rect, txt):
            btn_data["command"]()
            return


# ---------------------------------------------------------------------------
# Custom macOS-style slider
# ---------------------------------------------------------------------------

class MacSlider:
    """Volume slider rendered on a Canvas."""

    TRACK_Y = 14
    KNOB_R = 8

    def __init__(self, canvas, x_left, x_right, var, on_change=None):
        self.canvas = canvas
        self.track_left = x_left + self.KNOB_R
        self.track_right = x_right - self.KNOB_R
        self.var = var  # tk.DoubleVar 0..100
        self.on_change = on_change
        self._drag = False

        # Track background (inactive)
        self.track_bg = canvas.create_line(
            self.track_left, self.TRACK_Y, self.track_right, self.TRACK_Y,
            fill=config.MAC_BORDER, width=4, capstyle=tk.ROUND,
        )
        # Track fill (active)
        self.track_active = canvas.create_line(
            self.track_left, self.TRACK_Y, self.track_left, self.TRACK_Y,
            fill=config.MAC_ACCENT, width=4, capstyle=tk.ROUND,
        )
        # Knob
        self.knob = canvas.create_oval(
            self.track_left - self.KNOB_R, self.TRACK_Y - self.KNOB_R,
            self.track_left + self.KNOB_R, self.TRACK_Y + self.KNOB_R,
            fill="#ffffff", outline=config.MAC_BORDER, width=1,
        )

        # Bind events
        canvas.tag_bind(self.track_bg, "<Button-1>", self._on_click)
        canvas.tag_bind(self.track_active, "<Button-1>", self._on_click)
        canvas.tag_bind(self.knob, "<Button-1>", self._on_drag_start)
        canvas.tag_bind(self.knob, "<B1-Motion>", self._on_drag)
        canvas.tag_bind(self.knob, "<ButtonRelease-1>", self._on_drag_end)
        canvas.bind("<Button-1>", self._on_click, add="+")
        canvas.bind("<B1-Motion>", self._on_drag, add="+")
        canvas.bind("<ButtonRelease-1>", self._on_drag_end, add="+")

    def _x_to_val(self, x):
        frac = max(0.0, min(1.0, (x - self.track_left) / (self.track_right - self.track_left)))
        return frac * 100

    def _val_to_x(self, val):
        frac = val / 100.0
        return self.track_left + frac * (self.track_right - self.track_left)

    def redraw(self, val):
        x = self._val_to_x(val)
        self.canvas.coords(self.track_active, self.track_left, self.TRACK_Y, x, self.TRACK_Y)
        self.canvas.coords(
            self.knob,
            x - self.KNOB_R, self.TRACK_Y - self.KNOB_R,
            x + self.KNOB_R, self.TRACK_Y + self.KNOB_R,
        )

    def _on_click(self, event):
        val = self._x_to_val(event.x)
        self.var.set(val)
        self.redraw(val)

    def _on_drag_start(self, event):
        self._drag = True
        val = self._x_to_val(event.x)
        self.var.set(val)
        self.redraw(val)

    def _on_drag(self, event):
        if self._drag:
            val = self._x_to_val(event.x)
            self.var.set(val)
            self.redraw(val)

    def _on_drag_end(self, event):
        self._drag = False


# ---------------------------------------------------------------------------
# Main GUI
# ---------------------------------------------------------------------------

def create_gui():
    _create_rounded_rect_method()

    root = tk.Tk()
    root.title("Live Translate")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg=config.MAC_BG, highlightthickness=0)

    status_var = tk.StringVar(value="")

    def set_status(text):
        root.after(0, status_var.set, text)

    ui_state = {"paused": False, "busy": False}

    # --- Monitor volume slider variable (0..100) ---
    MAX_MONITOR_VOLUME = 0.5
    monitor_vol_var = tk.DoubleVar(value=(config.MONITOR_VOLUME / MAX_MONITOR_VOLUME) * 100)

    def on_monitor_volume_changed(*_args):
        new_vol = (monitor_vol_var.get() / 100.0) * MAX_MONITOR_VOLUME
        with config.app_state["monitor_volume_lock"]:
            config.app_state["monitor_volume"] = new_vol

    monitor_vol_var.trace_add("write", on_monitor_volume_changed)

    # ==================== Key screen ====================
    key_frame = tk.Frame(root, bg=config.MAC_BG, padx=24, pady=24)

    key_var = tk.StringVar(value=os.environ.get("GEMINI_API_KEY", ""))
    show_key_var = tk.BooleanVar(value=False)
    key_error_var = tk.StringVar()

    tk.Label(
        key_frame, text="Gemini API Key",
        font=(config.FONT_FAMILY, 16, "bold"), fg=config.MAC_TEXT, bg=config.MAC_BG,
    ).pack(anchor="w", pady=(0, 2))

    tk.Label(
        key_frame, text="Key is stored in ~/.live_translate/config.json",
        font=(config.FONT_FAMILY, 11), fg=config.MAC_SECONDARY, bg=config.MAC_BG,
    ).pack(anchor="w", pady=(0, 20))

    # Entry
    entry_frame = tk.Frame(key_frame, bg=config.MAC_CARD_BG,
                           highlightbackground=config.MAC_BORDER,
                           highlightthickness=1, highlightcolor=config.MAC_ACCENT)
    entry_frame.pack(fill=tk.X, pady=(0, 8))

    key_entry = tk.Entry(
        entry_frame, textvariable=key_var, show="*",
        font=(config.FONT_MONO, 12), fg=config.MAC_TEXT, bg=config.MAC_CARD_BG,
        relief=tk.FLAT, insertbackground=config.MAC_ACCENT,
        highlightthickness=0, borderwidth=8,
    )
    key_entry.pack(fill=tk.X)

    # Show/hide key toggle
    chk_frame = tk.Frame(key_frame, bg=config.MAC_BG)
    chk_frame.pack(anchor="w", pady=(2, 0))

    def toggle_key_visibility():
        show = show_key_var.get()
        key_entry.config(show="" if show else "*")
        chk_label.config(text="Hide key" if show else "Show key")

    show_key_var.trace_add("write", lambda *_: toggle_key_visibility())

    chk_label = tk.Label(
        chk_frame, text="Show key",
        font=(config.FONT_FAMILY, 11), fg=config.MAC_ACCENT, bg=config.MAC_BG,
        cursor="pointinghand",
    )
    chk_label.pack(side=tk.LEFT)
    chk_label.bind("<Button-1>", lambda e: show_key_var.set(not show_key_var.get()))

    # Error label
    error_label = tk.Label(
        key_frame, textvariable=key_error_var,
        font=(config.FONT_FAMILY, 11), fg=config.MAC_RED, bg=config.MAC_BG,
    )
    error_label.pack(anchor="w", pady=(8, 2))

    # Save button
    btn_canvas_key = tk.Canvas(key_frame, width=340, height=40,
                               bg=config.MAC_BG, highlightthickness=0)
    btn_canvas_key.pack(fill=tk.X, pady=(16, 0))

    def on_save_key():
        key = key_var.get().strip()
        if not key:
            key_error_var.set("Enter API key")
            return
        storage.save_api_key(key)
        key_error_var.set("")
        show_main_screen(key)

    _mac_button(
        btn_canvas_key, 0, 0, 340, 40, "Save & Start Translation",
        config.MAC_ACCENT, config.MAC_ACCENT_HOVER, "#ffffff", on_save_key,
        font_size=13, tags=("mac_btn", "mac_btn_text"),
    )
    _setup_mac_button_hover(btn_canvas_key)
    btn_canvas_key.config(width=340, height=40)

    # ==================== Main screen ====================
    main_frame = tk.Frame(root, bg=config.MAC_BG, padx=24, pady=24)

    # Status badge
    status_badge_frame = tk.Frame(main_frame, bg=config.MAC_CARD_BG,
                                  highlightbackground=config.MAC_BORDER,
                                  highlightthickness=1)
    status_badge_frame.pack(fill=tk.X, pady=(0, 20))

    status_label = tk.Label(
        status_badge_frame, textvariable=status_var,
        font=(config.FONT_FAMILY, 12, "bold"), fg=config.MAC_ACCENT,
        bg=config.MAC_CARD_BG, padx=16, pady=10,
    )
    status_label.pack(fill=tk.X)

    # --- Volume section ---
    vol_section = tk.Frame(main_frame, bg=config.MAC_BG)
    vol_section.pack(fill=tk.X, pady=(0, 8))

    vol_header = tk.Frame(vol_section, bg=config.MAC_BG)
    vol_header.pack(fill=tk.X)

    tk.Label(
        vol_header, text="Monitor Volume",
        font=(config.FONT_FAMILY, 11, "bold"), fg=config.MAC_TEXT, bg=config.MAC_BG,
    ).pack(side=tk.LEFT)

    vol_value_label = tk.Label(
        vol_header, text="",
        font=(config.FONT_FAMILY, 11), fg=config.MAC_SECONDARY, bg=config.MAC_BG,
    )
    vol_value_label.pack(side=tk.RIGHT)

    def update_vol_label(*_args):
        val = int(monitor_vol_var.get())
        if val == 0:
            vol_value_label.config(text="Off", fg=config.MAC_SECONDARY)
        else:
            vol_value_label.config(text=f"{val}%", fg=config.MAC_ACCENT)
    monitor_vol_var.trace_add("write", update_vol_label)
    update_vol_label()

    # Custom slider
    slider_canvas = tk.Canvas(vol_section, width=300, height=28,
                              bg=config.MAC_BG, highlightthickness=0)
    slider_canvas.pack(fill=tk.X, pady=(6, 0))

    mac_slider = MacSlider(slider_canvas, 0, 300, monitor_vol_var)

    root.after(10, lambda: mac_slider.redraw(monitor_vol_var.get()))

    # --- Separator ---
    sep = tk.Frame(main_frame, bg=config.MAC_BORDER, height=1)
    sep.pack(fill=tk.X, pady=(16, 16))

    # --- Buttons ---
    BTN_W = 300
    BTN_H = 38

    # Pause button
    pause_canvas = tk.Canvas(main_frame, width=BTN_W, height=BTN_H,
                             bg=config.MAC_BG, highlightthickness=0)
    pause_canvas.pack(pady=(0, 8))

    def toggle_pause():
        if ui_state["busy"]:
            return
        ui_state["busy"] = True
        set_mac_buttons_state("disabled")

        if not ui_state["paused"]:
            def worker():
                engine.request_pause_sync()
                ui_state["paused"] = True
                root.after(0, lambda: update_pause_btn_text("Resume"))
                root.after(0, lambda: set_mac_buttons_state("normal"))
                root.after(0, lambda: ui_state.__setitem__("busy", False))
            threading.Thread(target=worker, daemon=True).start()
        else:
            def worker():
                engine.request_resume_sync()
                ui_state["paused"] = False
                root.after(0, lambda: update_pause_btn_text("Pause"))
                root.after(0, lambda: set_mac_buttons_state("normal"))
                root.after(0, lambda: ui_state.__setitem__("busy", False))
            threading.Thread(target=worker, daemon=True).start()

    def update_pause_btn_text(text):
        pause_canvas.delete("mac_btn")
        pause_canvas.delete("mac_btn_text")
        pause_canvas._mac_btn_data.clear()
        _mac_button(
            pause_canvas, 0, 0, BTN_W, BTN_H, text,
            config.MAC_ACCENT, config.MAC_ACCENT_HOVER, "#ffffff", toggle_pause,
            font_size=13, tags=("mac_btn", "mac_btn_text"),
        )
        _setup_mac_button_hover(pause_canvas)

    _mac_button(
        pause_canvas, 0, 0, BTN_W, BTN_H, "Pause",
        config.MAC_ACCENT, config.MAC_ACCENT_HOVER, "#ffffff", toggle_pause,
        font_size=13, tags=("mac_btn", "mac_btn_text"),
    )
    _setup_mac_button_hover(pause_canvas)

    # Quit button
    quit_canvas = tk.Canvas(main_frame, width=BTN_W, height=BTN_H,
                            bg=config.MAC_BG, highlightthickness=0)
    quit_canvas.pack(pady=(0, 8))

    def on_closing():
        set_status("Shutting down...")
        set_mac_buttons_state("disabled")

        def worker():
            engine.stop_engine_sync()
            root.after(0, root.destroy)

        threading.Thread(target=worker, daemon=True).start()

    _mac_button(
        quit_canvas, 0, 0, BTN_W, BTN_H, "Quit",
        config.MAC_RED, config.MAC_RED_HOVER, "#ffffff", on_closing,
        font_size=13, tags=("mac_btn", "mac_btn_text"),
    )
    _setup_mac_button_hover(quit_canvas)

    # Settings link
    settings_label = tk.Label(
        main_frame, text="Change API Key",
        font=(config.FONT_FAMILY, 11), fg=config.MAC_ACCENT, bg=config.MAC_BG,
        cursor="pointinghand",
    )
    settings_label.pack(pady=(8, 0))

    def set_mac_buttons_state(state):
        """Enable or disable all interactive elements."""
        is_normal = state == "normal"
        new_cursor = "pointinghand" if is_normal else "arrow"
        for canvas in (pause_canvas, quit_canvas):
            canvas.configure(cursor=new_cursor)
            for (rect, txt), data in canvas._mac_btn_data.items():
                if is_normal:
                    canvas.itemconfig(rect, fill=data["fill"], outline=data["fill"])
                    canvas.itemconfig(txt, fill=data["text_color"])
                else:
                    canvas.itemconfig(rect, fill=config.MAC_BORDER, outline=config.MAC_BORDER)
                    canvas.itemconfig(txt, fill=config.MAC_DISABLED_TEXT)
        settings_label.configure(
            cursor=new_cursor if is_normal else "arrow",
            fg=config.MAC_ACCENT if is_normal else config.MAC_DISABLED_TEXT,
        )
        slider_canvas.configure(cursor=new_cursor if is_normal else "arrow")

    # Slider scroll support
    def on_slider_scroll(event):
        if ui_state["busy"]:
            return
        delta = -1 if event.delta > 0 else 1
        new_val = max(0, min(100, monitor_vol_var.get() + delta))
        monitor_vol_var.set(new_val)
        mac_slider.redraw(new_val)

    slider_canvas.bind("<MouseWheel>", on_slider_scroll, add="+")
    slider_canvas.bind("<Button-4>", lambda e: monitor_vol_var.set(min(100, monitor_vol_var.get() + 1)) or mac_slider.redraw(monitor_vol_var.get()), add="+")
    slider_canvas.bind("<Button-5>", lambda e: monitor_vol_var.set(max(0, monitor_vol_var.get() - 1)) or mac_slider.redraw(monitor_vol_var.get()), add="+")

    # ==================== Settings dialog ====================
    def open_settings():
        dlg = tk.Toplevel(root)
        dlg.title("Settings")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.transient(root)
        dlg.configure(bg=config.MAC_BG, highlightthickness=0)

        frm = tk.Frame(dlg, bg=config.MAC_BG, padx=24, pady=24)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frm, text="New API Key\n(leave empty to delete key)",
            font=(config.FONT_FAMILY, 12), fg=config.MAC_TEXT, bg=config.MAC_BG,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 16))

        new_key_var = tk.StringVar()
        show_new_var = tk.BooleanVar(value=False)

        new_entry_frame = tk.Frame(frm, bg=config.MAC_CARD_BG,
                                   highlightbackground=config.MAC_BORDER,
                                   highlightthickness=1)
        new_entry_frame.pack(fill=tk.X, pady=(0, 6))

        new_entry = tk.Entry(
            new_entry_frame, textvariable=new_key_var, show="*",
            font=(config.FONT_MONO, 12), fg=config.MAC_TEXT, bg=config.MAC_CARD_BG,
            relief=tk.FLAT, insertbackground=config.MAC_ACCENT,
            highlightthickness=0, borderwidth=8,
        )
        new_entry.pack(fill=tk.X)

        new_chk_frame = tk.Frame(frm, bg=config.MAC_BG)
        new_chk_frame.pack(anchor="w", pady=(2, 18))

        def toggle_new_visibility():
            show = show_new_var.get()
            new_entry.config(show="" if show else "*")
            new_chk_label.config(text="Hide" if show else "Show")

        show_new_var.trace_add("write", lambda *_: toggle_new_visibility())

        new_chk_label = tk.Label(
            new_chk_frame, text="Show",
            font=(config.FONT_FAMILY, 11), fg=config.MAC_ACCENT, bg=config.MAC_BG,
            cursor="pointinghand",
        )
        new_chk_label.pack(side=tk.LEFT)
        new_chk_label.bind("<Button-1>", lambda e: show_new_var.set(not show_new_var.get()))

        dlg_btn_w = 160
        dlg_btn_h = 36
        dlg_btn_frame = tk.Frame(frm, bg=config.MAC_BG)
        dlg_btn_frame.pack(fill=tk.X)

        save_canvas = tk.Canvas(dlg_btn_frame, width=dlg_btn_w, height=dlg_btn_h,
                                bg=config.MAC_BG, highlightthickness=0)
        save_canvas.pack(side=tk.LEFT, padx=(0, 8))

        def do_save():
            new_key = new_key_var.get().strip()
            dlg.destroy()
            if new_key:
                apply_key_change(new_key)

        _mac_button(
            save_canvas, 0, 0, dlg_btn_w, dlg_btn_h, "Save",
            config.MAC_ACCENT, config.MAC_ACCENT_HOVER, "#ffffff", do_save,
            tags=("mac_btn", "mac_btn_text"),
        )
        _setup_mac_button_hover(save_canvas)

        del_canvas = tk.Canvas(dlg_btn_frame, width=dlg_btn_w, height=dlg_btn_h,
                               bg=config.MAC_BG, highlightthickness=0)
        del_canvas.pack(side=tk.LEFT)

        def do_clear():
            dlg.destroy()
            apply_key_change(None)

        _mac_button(
            del_canvas, 0, 0, dlg_btn_w, dlg_btn_h, "Delete Key",
            config.MAC_RED, config.MAC_RED_HOVER, "#ffffff", do_clear,
            tags=("mac_btn", "mac_btn_text"),
        )
        _setup_mac_button_hover(del_canvas)

        new_entry.focus_set()

    def apply_key_change(new_key_or_none):
        set_mac_buttons_state("disabled")
        set_status("Restarting...")

        def worker():
            engine.stop_engine_sync()
            if new_key_or_none is None:
                storage.clear_api_key()
                root.after(0, show_key_screen)
            else:
                storage.save_api_key(new_key_or_none)
                root.after(0, lambda: show_main_screen(new_key_or_none))

        threading.Thread(target=worker, daemon=True).start()

    # ==================== Screen switching ====================
    def show_key_screen():
        main_frame.pack_forget()
        root.title("Live Translate — Setup")
        root.geometry("")
        root.update_idletasks()
        w = max(390, key_frame.winfo_reqwidth())
        h = key_frame.winfo_reqheight()
        root.geometry(f"{w}x{h}")
        key_frame.pack(fill=tk.BOTH, expand=True)
        key_entry.focus_set()

    def _show_blackhole_error():
        """Show error dialog when BlackHole is not installed."""
        dlg = tk.Toplevel(root)
        dlg.title("Missing Dependency")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.transient(root)
        dlg.configure(bg=config.MAC_BG, highlightthickness=0)

        frm = tk.Frame(dlg, bg=config.MAC_BG, padx=24, pady=24)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frm,
            text="BlackHole is not installed",
            font=(config.FONT_FAMILY, 14, "bold"), fg=config.MAC_RED, bg=config.MAC_BG,
        ).pack(anchor="w", pady=(0, 12))

        install_text = (
            "BlackHole is a virtual audio device required for Live Translate\n"
            "to send translated audio to apps like Google Meet or Zoom.\n\n"
            "To install, open Terminal and run:\n"
            "  brew install blackhole-2ch\n\n"
            "After installation, restart Live Translate."
        )
        tk.Label(
            frm, text=install_text,
            font=(config.FONT_FAMILY, 11), fg=config.MAC_TEXT, bg=config.MAC_BG,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 18))

        dlg_btn_w = 120
        dlg_btn_h = 36

        btn_frame = tk.Frame(frm, bg=config.MAC_BG)
        btn_frame.pack(fill=tk.X)

        ok_canvas = tk.Canvas(btn_frame, width=dlg_btn_w, height=dlg_btn_h,
                              bg=config.MAC_BG, highlightthickness=0)
        ok_canvas.pack(side=tk.LEFT)

        _mac_button(
            ok_canvas, 0, 0, dlg_btn_w, dlg_btn_h, "OK",
            config.MAC_ACCENT, config.MAC_ACCENT_HOVER, "#ffffff", dlg.destroy,
            tags=("mac_btn", "mac_btn_text"),
        )
        _setup_mac_button_hover(ok_canvas)

        dlg.update_idletasks()
        w = max(420, dlg.winfo_reqwidth())
        h = dlg.winfo_reqheight()
        dlg.geometry(f"{w}x{h}")

    def show_main_screen(api_key):
        # Pre-flight: check BlackHole is available
        if not engine.check_blackhole():
            _show_blackhole_error()

        key_frame.pack_forget()
        root.title("Live Translate")
        root.geometry("")
        root.update_idletasks()
        w = max(350, main_frame.winfo_reqwidth())
        h = main_frame.winfo_reqheight()
        root.geometry(f"{w}x{h}")
        ui_state["paused"] = False
        ui_state["busy"] = False
        update_pause_btn_text("Pause")
        set_mac_buttons_state("normal")
        main_frame.pack(fill=tk.BOTH, expand=True)
        set_status("Connecting...")
        engine.start_engine(api_key, set_status)

    settings_label.bind("<Button-1>", lambda e: open_settings())
    root.protocol("WM_DELETE_WINDOW", on_closing)

    existing_key = storage.load_api_key()
    if existing_key:
        show_main_screen(existing_key)
    else:
        show_key_screen()

    root.mainloop()
