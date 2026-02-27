import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk


class UIComponents:
    def __init__(self, app):
        self.app = app

    def build(self):
        app = self.app

        app.toolbar_frame = ctk.CTkFrame(app, corner_radius=0)
        app.toolbar_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        app.toolbar_frame.grid_columnconfigure(4, weight=1)

        app.open_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="📂",
            width=45,
            height=45,
            command=app.handlers.open_pdf,
            font=app.icon_font,
        )
        app.merge_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="➕",
            width=45,
            height=45,
            command=app.handlers.merge_pdf,
            font=app.icon_font,
        )
        app.save_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="💾",
            width=45,
            height=45,
            command=app.handlers.save_all,
            font=app.icon_font,
        )
        app.reset_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="⟲",
            width=45,
            height=45,
            command=app.handlers.reset,
            font=app.icon_font,
        )

        app.open_btn.grid(row=0, column=0, padx=(12, 8), pady=6)
        app.merge_btn.grid(row=0, column=1, padx=(0, 8), pady=6)
        app.save_btn.grid(row=0, column=2, padx=(0, 8), pady=6)
        app.reset_btn.grid(row=0, column=3, padx=(0, 12), pady=6)

        spacer = ctk.CTkFrame(app.toolbar_frame, fg_color="transparent")
        spacer.grid(row=0, column=4, sticky="ew")

        app.undo_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="↶",
            width=45,
            height=45,
            command=app.handlers.undo,
            font=app.icon_font,
        )
        app.redo_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="↷",
            width=45,
            height=45,
            command=app.handlers.redo,
            font=app.icon_font,
        )
        app.rotate_left_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="⟲",
            width=45,
            height=45,
            command=lambda: app.handlers.rotate_selected(-90),
            font=app.icon_font,
        )
        app.rotate_right_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="⟳",
            width=45,
            height=45,
            command=lambda: app.handlers.rotate_selected(90),
            font=app.icon_font,
        )
        app.delete_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="🗑",
            width=45,
            height=45,
            command=app.handlers.delete_selected,
            font=app.icon_font,
        )
        app.select_all_btn = ctk.CTkButton(
            app.toolbar_frame,
            text="▦",
            width=45,
            height=45,
            command=app._select_all,
            font=app.icon_font,
        )
        app.undo_btn.grid(row=0, column=5, padx=(0, 8), pady=6)
        app.redo_btn.grid(row=0, column=6, padx=(0, 8), pady=6)
        app.rotate_left_btn.grid(row=0, column=7, padx=(0, 8), pady=6)
        app.rotate_right_btn.grid(row=0, column=8, padx=(0, 8), pady=6)
        app.delete_btn.grid(row=0, column=9, padx=(0, 8), pady=6)
        app.select_all_btn.grid(row=0, column=10, padx=(0, 12), pady=6)

        app.theme_switch = ctk.CTkSwitch(
            app.toolbar_frame,
            text="다크/라이트",
            command=app._toggle_theme,
            font=app.ui_font,
        )
        app.theme_switch.select()
        app.theme_switch.grid(row=0, column=13, padx=(0, 12), pady=6)

        app.info_size = ctk.CTkLabel(app.toolbar_frame, text="용량: -", font=("Pretendard", 12))
        app.info_pages = ctk.CTkLabel(app.toolbar_frame, text="페이지 수: -", font=("Pretendard", 12))
        app.info_size.grid(row=0, column=14, padx=(0, 8), pady=6)
        app.info_pages.grid(row=0, column=15, padx=(0, 12), pady=6)

        self._attach_tooltip(app.open_btn, "PDF 열기")
        self._attach_tooltip(app.merge_btn, "파일 추가")
        self._attach_tooltip(app.save_btn, "전체 저장")
        self._attach_tooltip(app.reset_btn, "초기화")
        self._attach_tooltip(app.undo_btn, "되돌리기")
        self._attach_tooltip(app.redo_btn, "다시 실행")
        self._attach_tooltip(app.rotate_left_btn, "왼쪽 90도 회전")
        self._attach_tooltip(app.rotate_right_btn, "오른쪽 90도 회전")
        self._attach_tooltip(app.delete_btn, "선택 삭제")
        self._attach_tooltip(app.select_all_btn, "전체 선택")

        app.nav_frame = ctk.CTkFrame(app, width=240, corner_radius=0)
        app.nav_frame.grid(row=1, column=0, sticky="nsew")
        app.nav_frame.grid_rowconfigure(0, weight=1)
        app.nav_frame.grid_columnconfigure(0, weight=1)
        app.viewer_frame = ctk.CTkFrame(app, corner_radius=0)
        app.viewer_frame.grid(row=1, column=1, sticky="nsew")
        app.viewer_frame.grid_rowconfigure(0, weight=1)
        app.viewer_frame.grid_columnconfigure(0, weight=1)

        app.viewer_canvas = tk.Canvas(app.viewer_frame, highlightthickness=0, bg="#1E1E1E")
        app.viewer_canvas.grid(row=0, column=0, sticky="nsew")

        app.viewer_vbar = tk.Scrollbar(app.viewer_frame, orient="vertical", command=app.viewer_canvas.yview)
        app.viewer_hbar = tk.Scrollbar(app.viewer_frame, orient="horizontal", command=app.viewer_canvas.xview)
        app.viewer_canvas.configure(yscrollcommand=app.viewer_vbar.set, xscrollcommand=app.viewer_hbar.set)
        app.viewer_vbar.grid(row=0, column=1, sticky="ns")
        app.viewer_hbar.grid(row=1, column=0, sticky="ew")

        app.viewer_image_id = None
        app.viewer_photo = None
        app.viewer_page_index = None
        app.viewer_zoom = 1.0

        app.viewer_canvas.bind("<MouseWheel>", self._on_viewer_wheel)
        app.viewer_canvas.bind("<Button-4>", self._on_viewer_wheel)
        app.viewer_canvas.bind("<Button-5>", self._on_viewer_wheel)
        app.viewer_canvas.bind("<ButtonPress-1>", self._on_viewer_pan_start)
        app.viewer_canvas.bind("<B1-Motion>", self._on_viewer_pan_move)

        app.scroll_frame = ctk.CTkScrollableFrame(app.nav_frame, corner_radius=0)
        app.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        app.scroll_frame.bind("<Button-1>", app._on_background_click)
        if hasattr(app.scroll_frame, "_parent_canvas"):
            app.scroll_frame._parent_canvas.bind("<Button-1>", app._on_background_click)
            app.scroll_frame._parent_canvas.bind("<Configure>", app._update_scrollregion)
            app.insert_line = app.scroll_frame._parent_canvas.create_line(
                0,
                0,
                0,
                0,
                fill="#F2A900",
                width=3,
                state="hidden",
            )
        app.scroll_frame.bind("<Configure>", app._update_scrollregion)
        app._refresh_undo_redo()


    def clear_viewer(self):
        app = self.app
        app.viewer_page_index = None
        app.viewer_zoom = 1.0
        if hasattr(app, "viewer_canvas"):
            app.viewer_canvas.delete("all")
            app.viewer_image_id = None
            app.viewer_photo = None
            app.viewer_canvas.config(scrollregion=(0, 0, 0, 0))

    def show_page_in_viewer(self, page_index, reset_zoom=True):
        app = self.app
        if app.engine.page_count() == 0:
            return
        if page_index < 0 or page_index >= app.engine.page_count():
            return

        app.viewer_page_index = page_index
        if reset_zoom:
            app.viewer_zoom = 1.0
        self._render_viewer_image()

    def _render_viewer_image(self):
        app = self.app
        if app.viewer_page_index is None:
            return

        app.viewer_canvas.update_idletasks()
        available_w = max(1, app.viewer_canvas.winfo_width() - 24)
        available_h = max(1, app.viewer_canvas.winfo_height() - 24)

        base_scale = 1.0
        pix = app.engine.get_page_pixmap(app.viewer_page_index, base_scale)
        if pix is None:
            return

        scale_w = available_w / max(1, pix.width)
        scale_h = available_h / max(1, pix.height)
        fit_scale = min(scale_w, scale_h)
        fit_scale = max(0.2, min(fit_scale, 2.0))

        zoom = max(0.2, min(app.viewer_zoom, 4.0))
        target_scale = fit_scale * zoom

        if abs(target_scale - base_scale) > 0.01:
            pix = app.engine.get_page_pixmap(app.viewer_page_index, target_scale)
            if pix is None:
                return

        mode = "RGBA" if pix.alpha else "RGB"
        image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        app.viewer_photo = ImageTk.PhotoImage(image)
        if app.viewer_image_id is None:
            app.viewer_image_id = app.viewer_canvas.create_image(0, 0, anchor="nw", image=app.viewer_photo)
        else:
            app.viewer_canvas.itemconfigure(app.viewer_image_id, image=app.viewer_photo)
        app.viewer_canvas.config(scrollregion=(0, 0, pix.width, pix.height))

    def _on_viewer_wheel(self, event):
        app = self.app
        if app.viewer_page_index is None:
            return

        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = event.delta
        elif hasattr(event, "num"):
            if event.num == 4:
                delta = 120
            elif event.num == 5:
                delta = -120
        if delta == 0:
            return

        ctrl_pressed = bool(getattr(event, "state", 0) & 0x0004)
        if ctrl_pressed:
            factor = 1.1 if delta > 0 else 0.9
            app.viewer_zoom = max(0.2, min(app.viewer_zoom * factor, 4.0))
            self._render_viewer_image()
            return

        # default: scroll vertically
        app.viewer_canvas.yview_scroll(-1 if delta > 0 else 1, "units")

    def _on_viewer_pan_start(self, event):
        self.app.viewer_canvas.scan_mark(event.x, event.y)

    def _on_viewer_pan_move(self, event):
        self.app.viewer_canvas.scan_dragto(event.x, event.y, gain=1)

    def _attach_tooltip(self, widget, text):
        tooltip = {"window": None}

        def show_tooltip(_event=None):
            if tooltip["window"] is not None:
                return
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.attributes("-topmost", True)
            label = tk.Label(
                win,
                text=text,
                bg="#1E1E1E",
                fg="#F2F2F2",
                padx=8,
                pady=4,
                font=("Pretendard", 11),
            )
            label.pack()
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 6
            win.wm_geometry(f"+{x}+{y}")
            tooltip["window"] = win

        def hide_tooltip(_event=None):
            win = tooltip.get("window")
            if win is not None:
                win.destroy()
                tooltip["window"] = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
        widget.bind("<ButtonPress>", hide_tooltip)
