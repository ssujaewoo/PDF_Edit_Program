import ctypes
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from pdf_engine import PdfEngine

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class PdfEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.15)
        ctk.set_window_scaling(1.15)

        self.title("PDF Editor")
        self.geometry("1100x700")
        self.minsize(1100, 700)

        self.engine = PdfEngine()
        self.page_widgets = []
        self.drag_start_index = None
        self.drag_target_index = None
        self.drag_source_frame = None
        self.drag_target_frame = None
        self.drag_drop_index = None
        self.thumbnail_scale = 0.2
        self._zoom_job = None
        self.max_columns = 5
        self.ui_font = ("Pretendard", 14)
        self.icon_font = ("Pretendard", 20)
        self.undo_stack = []
        self.redo_stack = []
        self.current_path = None
        self.selected_indices = set()
        self.selected_fg = "#2A364A"
        self.selected_border = "#1f6aa5"
        self.drag_ghost = None
        self.drag_ghost_image = None
        self._press_index = None
        self._press_pos = None
        self._drag_started = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=6, sashrelief="raised", bd=0)
        self.paned.grid(row=0, column=0, sticky="nsew")

        self._build_sidebar()
        self._build_main_area()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid_rowconfigure(9, weight=1)
        self.paned.add(self.sidebar, minsize=180)

        btn_open = ctk.CTkButton(self.sidebar, text="PDF 열기", command=self.open_pdf, font=self.ui_font)
        btn_merge = ctk.CTkButton(self.sidebar, text="파일 추가", command=self.merge_pdf, font=self.ui_font)
        btn_save = ctk.CTkButton(self.sidebar, text="전체 저장", command=self.save_all, font=self.ui_font)
        btn_reset = ctk.CTkButton(self.sidebar, text="초기화", command=self.reset, font=self.ui_font)

        btn_open.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        btn_merge.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        btn_save.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        btn_reset.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        zoom_label = ctk.CTkLabel(self.sidebar, text="썸네일 줌", font=self.ui_font)
        zoom_label.grid(row=4, column=0, padx=20, pady=(20, 6), sticky="w")

        self.zoom_slider = ctk.CTkSlider(
            self.sidebar,
            from_=0.1,
            to=0.5,
            command=self._on_zoom_change,
        )
        self.zoom_slider.set(self.thumbnail_scale)
        self.zoom_slider.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")

        columns_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        columns_header.grid(row=6, column=0, padx=20, pady=(8, 2), sticky="ew")
        columns_header.grid_columnconfigure(0, weight=1)
        columns_label = ctk.CTkLabel(columns_header, text="가로 최대 개수", font=self.ui_font)
        columns_label.grid(row=0, column=0, sticky="w")
        self.columns_value = ctk.CTkLabel(columns_header, text=str(self.max_columns), font=("Pretendard", 12))
        self.columns_value.grid(row=0, column=1, sticky="e")
        self.columns_slider = ctk.CTkSlider(
            self.sidebar,
            from_=1,
            to=8,
            number_of_steps=7,
            command=self._on_columns_change,
        )
        self.columns_slider.set(self.max_columns)
        self.columns_slider.grid(row=7, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.theme_switch = ctk.CTkSwitch(
            self.sidebar,
            text="다크/라이트 모드",
            command=self._toggle_theme,
            font=self.ui_font,
        )
        self.theme_switch.select()
        self.theme_switch.grid(row=8, column=0, padx=20, pady=(6, 12), sticky="w")

        self.info_frame = ctk.CTkFrame(self.sidebar, corner_radius=10)
        self.info_frame.grid(row=9, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        info_title = ctk.CTkLabel(self.info_frame, text="파일 정보", font=("Pretendard", 13))
        info_title.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")
        self.info_size = ctk.CTkLabel(self.info_frame, text="용량: -", font=("Pretendard", 12))
        self.info_size.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="w")
        self.info_pages = ctk.CTkLabel(self.info_frame, text="페이지 수: -", font=("Pretendard", 12))
        self.info_pages.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="w")

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.paned.add(self.main_frame, minsize=480)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(self.main_frame, corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        toolbar.grid_columnconfigure(0, weight=0)

        self.undo_btn = ctk.CTkButton(
            toolbar,
            text="↶",
            width=45,
            height=45,
            command=self._undo,
            font=self.icon_font,
        )
        self.redo_btn = ctk.CTkButton(
            toolbar,
            text="↷",
            width=45,
            height=45,
            command=self._redo,
            font=self.icon_font,
        )
        self.rotate_left_btn = ctk.CTkButton(
            toolbar,
            text="⟲",
            width=45,
            height=45,
            command=lambda: self._rotate_selected(-90),
            font=self.icon_font,
        )
        self.rotate_right_btn = ctk.CTkButton(
            toolbar,
            text="⟳",
            width=45,
            height=45,
            command=lambda: self._rotate_selected(90),
            font=self.icon_font,
        )
        self.delete_btn = ctk.CTkButton(
            toolbar,
            text="🗑",
            width=45,
            height=45,
            command=self._delete_selected,
            font=self.icon_font,
        )
        self.select_all_btn = ctk.CTkButton(
            toolbar,
            text="📋",
            width=45,
            height=45,
            command=self._select_all,
            font=self.icon_font,
        )
        self.undo_btn.grid(row=0, column=0, padx=(0, 8), pady=6)
        self.redo_btn.grid(row=0, column=1, padx=(0, 8), pady=6)
        self.rotate_left_btn.grid(row=0, column=2, padx=(0, 8), pady=6)
        self.rotate_right_btn.grid(row=0, column=3, padx=(0, 8), pady=6)
        self.delete_btn.grid(row=0, column=4, padx=(0, 8), pady=6)
        self.select_all_btn.grid(row=0, column=5, padx=(0, 8), pady=6)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self.scroll_frame.bind("<Button-1>", self._on_background_click)
        if hasattr(self.scroll_frame, "_parent_canvas"):
            self.scroll_frame._parent_canvas.bind("<Button-1>", self._on_background_click)
            self.scroll_frame._parent_canvas.bind("<Configure>", self._update_scrollregion)
            self.insert_line = self.scroll_frame._parent_canvas.create_line(
                0,
                0,
                0,
                0,
                fill="#F2A900",
                width=3,
                state="hidden",
            )
        self.scroll_frame.bind("<Configure>", self._update_scrollregion)
        self._refresh_undo_redo()
        self._attach_tooltip(self.undo_btn, "되돌리기")
        self._attach_tooltip(self.redo_btn, "다시실행")
        self._attach_tooltip(self.rotate_left_btn, "왼쪽 90도 회전")
        self._attach_tooltip(self.rotate_right_btn, "오른쪽 90도 회전")
        self._attach_tooltip(self.delete_btn, "선택 삭제")
        self._attach_tooltip(self.select_all_btn, "전체 선택")

    def _bind_shortcuts(self):
        self.bind_all("<Control-z>", lambda event: self._undo())
        self.bind_all("<Control-y>", lambda event: self._redo())
        self.bind_all("<Control-Z>", lambda event: self._redo())
        self.bind_all("<Control-Shift-Z>", lambda event: self._redo())
        self.bind_all("<Control-a>", lambda event: self._select_all())
        self.bind_all("<Delete>", lambda event: self._delete_selected())

    def open_pdf(self):
        if not self._confirm_discard_if_dirty():
            return

        path = filedialog.askopenfilename(
            title="PDF 파일 선택",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return

        self.engine.close()
        self._clear_thumbnails()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._refresh_undo_redo()

        ok, err = self.engine.open(path)
        if not ok:
            messagebox.showerror("오류", f"PDF를 열 수 없습니다.\n{err}")
            return

        self.current_path = path
        self._update_file_info()
        self._load_thumbnails()

    def merge_pdf(self):
        if self.engine.page_count() == 0:
            messagebox.showinfo("안내", "먼저 PDF를 열어주세요.")
            return

        path = filedialog.askopenfilename(
            title="추가할 PDF 선택",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return

        pushed = self._push_undo_state()
        ok, err = self.engine.insert_pdf(path)
        if not ok:
            if pushed:
                self.undo_stack.pop()
                self._refresh_undo_redo()
            messagebox.showerror("오류", f"PDF 병합에 실패했습니다.\n{err}")
            return

        self._update_file_info()
        self._load_thumbnails()

    def _load_thumbnails(self, keep_selection=False):
        if self.engine.page_count() == 0:
            return

        self._clear_thumbnails(keep_selection=keep_selection)

        columns = None
        for page_index in range(self.engine.page_count()):
            pix = self.engine.get_page_pixmap(page_index, self.thumbnail_scale)
            if pix is None:
                continue

            mode = "RGBA" if pix.alpha else "RGB"
            image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(pix.width, pix.height))

            frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
            if columns is None:
                columns = self._calculate_columns(pix.width)
            row = page_index // columns
            col = page_index % columns
            frame.grid(row=row, column=col, padx=16, pady=16, sticky="nsew")

            image_label = ctk.CTkLabel(frame, image=ctk_image, text="")
            image_label.grid(row=0, column=0, padx=12, pady=(12, 8))

            page_label = ctk.CTkLabel(frame, text=f"페이지 {page_index + 1}", font=self.ui_font)
            page_label.grid(row=1, column=0, padx=12, pady=(0, 12))

            self._bind_drag_events(frame, image_label, page_label, page_index)
            default_fg = frame.cget("fg_color")
            self.page_widgets.append(
                {
                    "frame": frame,
                    "image": ctk_image,
                    "default_fg": default_fg,
                    "pil_image": image,
                }
            )
        self._refresh_undo_redo()
        self._refresh_selection_styles()
        self._update_scrollregion()

    def save_all(self):
        if self.engine.page_count() == 0:
            messagebox.showinfo("안내", "저장할 문서가 없습니다.")
            return

        path = filedialog.asksaveasfilename(
            title="전체 저장",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return

        ok, err = self.engine.save(path)
        if not ok:
            messagebox.showerror("오류", f"저장에 실패했습니다.\n{err}")
            return

        self.current_path = path
        self._update_file_info()
        messagebox.showinfo("완료", "저장이 완료되었습니다.")

    def reset(self):
        if not self._confirm_discard_if_dirty():
            return
        self.engine.close()
        self._clear_thumbnails()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_path = None
        self._update_file_info()
        self._refresh_undo_redo()

    def _clear_thumbnails(self, keep_selection=False):
        for item in self.page_widgets:
            item["frame"].destroy()
        self.page_widgets.clear()
        if not keep_selection:
            self.selected_indices.clear()
        self._clear_drag_state()

    def _delete_page(self, page_index):
        pushed = self._push_undo_state()
        ok, err = self.engine.delete_page(page_index)
        if not ok:
            if pushed:
                self.undo_stack.pop()
                self._refresh_undo_redo()
            messagebox.showerror("오류", f"페이지 삭제에 실패했습니다.\n{err}")
            return
        self._load_thumbnails()

    def _rotate_page(self, page_index):
        pushed = self._push_undo_state()
        ok, err = self.engine.rotate_page_by(page_index, 90)
        if not ok:
            if pushed:
                self.undo_stack.pop()
                self._refresh_undo_redo()
            messagebox.showerror("오류", f"페이지 회전에 실패했습니다.\n{err}")
            return
        self._load_thumbnails()

    def _bind_drag_events(self, frame, image_label, page_label, page_index):
        frame.bind("<Button-1>", lambda event, idx=page_index: self._on_page_press(event, idx))
        frame.bind("<B1-Motion>", self._on_drag_motion)
        frame.bind("<ButtonRelease-1>", self._on_drag_release)

        image_label.bind("<Button-1>", lambda event, idx=page_index: self._on_page_press(event, idx))
        image_label.bind("<B1-Motion>", self._on_drag_motion)
        image_label.bind("<ButtonRelease-1>", self._on_drag_release)

        page_label.bind("<Button-1>", lambda event, idx=page_index: self._on_page_press(event, idx))
        page_label.bind("<B1-Motion>", self._on_drag_motion)
        page_label.bind("<ButtonRelease-1>", self._on_drag_release)

    def _on_page_press(self, event, page_index):
        self._press_index = page_index
        self._press_pos = (event.x_root, event.y_root)
        self._drag_started = False

    def _on_drag_motion(self, event):
        if self._press_index is None:
            return
        if not self._drag_started and self._press_pos is not None:
            dx = event.x_root - self._press_pos[0]
            dy = event.y_root - self._press_pos[1]
            if (dx * dx + dy * dy) < 36:
                return
            self._drag_started = True
            if self._press_index not in self.selected_indices:
                self.selected_indices.add(self._press_index)
                self._refresh_selection_styles()
            self.drag_start_index = self._press_index
            self.drag_target_index = self._press_index
            self.drag_drop_index = self._press_index
            self.drag_source_frame = self.page_widgets[self._press_index]["frame"]
            self._set_drag_highlight(self.drag_source_frame, True, self._press_index)
            self._start_drag_ghost(event, self._press_index)
        if not self._drag_started:
            return

        target_index = self._find_closest_index(event.x_root, event.y_root)
        if target_index is None:
            return

        insert_after = self._is_insert_after(target_index, event.x_root)
        if insert_after:
            drop_index = target_index + 1
        else:
            drop_index = target_index
        self._set_target_highlight(target_index)
        self.drag_drop_index = drop_index
        self._update_insert_indicator(target_index, insert_after)
        self._move_drag_ghost(event)

    def _on_drag_release(self, event):
        if self._press_index is None:
            return
        if not self._drag_started:
            self._toggle_selection(self._press_index)
            self._press_index = None
            self._press_pos = None
            return

        if self.drag_drop_index is None:
            self._clear_drag_state()
            self._stop_drag_ghost()
            self._press_index = None
            self._press_pos = None
            return

        to_index = self.drag_drop_index
        self._clear_drag_state()
        self._stop_drag_ghost()
        self._move_selected_to(to_index)
        self._press_index = None
        self._press_pos = None

    def _find_closest_index(self, x_root, y_root):
        if not self.page_widgets:
            return None

        closest_index = None
        closest_distance = None
        for index, item in enumerate(self.page_widgets):
            frame = item["frame"]
            cx = frame.winfo_rootx() + frame.winfo_width() / 2
            cy = frame.winfo_rooty() + frame.winfo_height() / 2
            distance = (cx - x_root) ** 2 + (cy - y_root) ** 2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_index = index

        return closest_index

    def _set_drag_highlight(self, frame, enabled, index):
        if enabled:
            if index in self.selected_indices:
                frame.configure(border_color="#F2A900")
            else:
                frame.configure(border_width=2, border_color="#F2A900")
        else:
            if index in self.selected_indices:
                frame.configure(border_color=self.selected_border)
            else:
                frame.configure(border_width=0)

    def _set_target_highlight(self, target_index):
        if (
            self.drag_target_frame is not None
            and self.drag_target_index != target_index
            and self.drag_target_frame is not self.drag_source_frame
        ):
            self._set_drag_highlight(self.drag_target_frame, False, self.drag_target_index)

        self.drag_target_index = target_index
        self.drag_target_frame = self.page_widgets[target_index]["frame"]
        if self.drag_target_frame is not self.drag_source_frame:
            self._set_drag_highlight(self.drag_target_frame, True, target_index)
        self._update_insert_indicator(target_index, False)

    def _clear_drag_state(self):
        if self.drag_source_frame is not None and self.drag_start_index is not None:
            self._set_drag_highlight(self.drag_source_frame, False, self.drag_start_index)
        if (
            self.drag_target_frame is not None
            and self.drag_target_frame is not self.drag_source_frame
            and self.drag_target_index is not None
        ):
            self._set_drag_highlight(self.drag_target_frame, False, self.drag_target_index)
        self._hide_insert_indicator()

        self.drag_start_index = None
        self.drag_target_index = None
        self.drag_source_frame = None
        self.drag_target_frame = None
        self.drag_drop_index = None

    def _start_drag_ghost(self, event, page_index):
        self._stop_drag_ghost()
        if page_index < 0 or page_index >= len(self.page_widgets):
            return
        pil_image = self.page_widgets[page_index]["pil_image"]
        ghost = tk.Toplevel(self)
        ghost.wm_overrideredirect(True)
        ghost.attributes("-topmost", True)
        image = ImageTk.PhotoImage(pil_image)
        label = tk.Label(ghost, image=image, bd=0)
        label.image = image
        label.pack()
        ghost.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        self.drag_ghost = ghost
        self.drag_ghost_image = image

    def _move_drag_ghost(self, event):
        if self.drag_ghost is None:
            return
        self.drag_ghost.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

    def _stop_drag_ghost(self):
        if self.drag_ghost is not None:
            self.drag_ghost.destroy()
            self.drag_ghost = None
            self.drag_ghost_image = None

    def _update_insert_indicator(self, target_index, insert_after):
        if not hasattr(self.scroll_frame, "_parent_canvas") or self.insert_line is None:
            return
        if target_index is None or not self.page_widgets:
            return
        canvas = self.scroll_frame._parent_canvas
        frame = self.page_widgets[target_index]["frame"]
        canvas.update_idletasks()
        x0 = frame.winfo_rootx()
        y0 = frame.winfo_rooty()
        x1 = x0 + frame.winfo_width()
        y1 = y0 + frame.winfo_height()
        if insert_after:
            x_line = x1 + 6
        else:
            x_line = x0 - 6
        cx0 = canvas.winfo_rootx()
        cy0 = canvas.winfo_rooty()
        rel_x = x_line - cx0
        rel_y0 = y0 - cy0
        rel_y1 = y1 - cy0
        canvas.coords(self.insert_line, rel_x, rel_y0, rel_x, rel_y1)
        canvas.itemconfigure(self.insert_line, state="normal")

    def _hide_insert_indicator(self):
        if hasattr(self.scroll_frame, "_parent_canvas") and self.insert_line is not None:
            self.scroll_frame._parent_canvas.itemconfigure(self.insert_line, state="hidden")

    def _is_insert_after(self, target_index, x_root):
        frame = self.page_widgets[target_index]["frame"]
        center = frame.winfo_rootx() + frame.winfo_width() / 2
        return x_root >= center

    def _on_zoom_change(self, value):
        self.thumbnail_scale = float(value)
        if self._zoom_job is not None:
            self.after_cancel(self._zoom_job)
        self._zoom_job = self.after(200, self._apply_zoom)

    def _on_columns_change(self, value):
        self.max_columns = max(1, int(round(float(value))))
        if hasattr(self, "columns_value"):
            self.columns_value.configure(text=str(self.max_columns))
        if self.engine.page_count() > 0:
            self._load_thumbnails(keep_selection=True)

    def _apply_zoom(self):
        self._zoom_job = None
        if self.engine.page_count() > 0:
            self._load_thumbnails()

    def _update_scrollregion(self, _event=None):
        if hasattr(self.scroll_frame, "_parent_canvas"):
            canvas = self.scroll_frame._parent_canvas
            region = canvas.bbox("all")
            if region is not None:
                canvas.configure(scrollregion=region)

    def _calculate_columns(self, thumb_width):
        self.update_idletasks()
        if hasattr(self.scroll_frame, "_parent_canvas"):
            available = self.scroll_frame._parent_canvas.winfo_width()
        else:
            available = self.scroll_frame.winfo_width()
        if available <= 1:
            return 4
        padding = 32
        columns = int(available // (thumb_width + padding))
        columns = max(1, columns)
        return min(columns, self.max_columns)

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def _update_file_info(self):
        if not hasattr(self, "info_size"):
            return
        if self.engine.page_count() == 0:
            self.info_size.configure(text="용량: -")
            self.info_pages.configure(text="페이지 수: -")
            return
        size_text = "-"
        path = getattr(self, "current_path", None)
        if path and os.path.exists(path):
            size_bytes = os.path.getsize(path)
            size_text = f"{size_bytes / 1024:.1f} KB"
        self.info_size.configure(text=f"용량: {size_text}")
        self.info_pages.configure(text=f"페이지 수: {self.engine.page_count()}")

    def _confirm_discard_if_dirty(self):
        if not self.engine.is_dirty:
            return True
        return messagebox.askyesno("확인", "저장되지 않은 변경사항이 있습니다. 계속하시겠습니까?")

    def _on_close(self):
        if not self._confirm_discard_if_dirty():
            return
        self.engine.close()
        self.destroy()

    def _push_undo_state(self):
        state = self.engine.get_state_bytes()
        if state is None:
            return False
        self.undo_stack.append(state)
        self.redo_stack.clear()
        self._refresh_undo_redo()
        return True

    def _apply_selection_style(self, frame, default_fg, selected):
        if selected:
            frame.configure(border_width=4, border_color=self.selected_border, fg_color=self.selected_fg)
        else:
            frame.configure(border_width=0, fg_color=default_fg)

    def _refresh_selection_styles(self):
        if self.engine.page_count() == 0:
            self.selected_indices.clear()
            return
        max_index = self.engine.page_count() - 1
        self.selected_indices = {i for i in self.selected_indices if 0 <= i <= max_index}
        for idx, item in enumerate(self.page_widgets):
            self._apply_selection_style(
                item["frame"],
                item["default_fg"],
                idx in self.selected_indices,
            )
        self._refresh_action_buttons()

    def _toggle_selection(self, page_index):
        if page_index in self.selected_indices:
            self.selected_indices.remove(page_index)
        else:
            self.selected_indices.add(page_index)
        self._refresh_selection_styles()

    def _clear_selection(self):
        if not self.selected_indices:
            return
        self.selected_indices.clear()
        self._refresh_selection_styles()

    def _on_background_click(self, event):
        canvas = getattr(self.scroll_frame, "_parent_canvas", None)
        if event.widget is self.scroll_frame or (canvas is not None and event.widget is canvas):
            self._clear_selection()

    def _select_all(self):
        if self.engine.page_count() == 0:
            return
        self.selected_indices = set(range(self.engine.page_count()))
        self._refresh_selection_styles()

    def _rotate_selected(self, delta):
        if not self.selected_indices:
            return
        pushed = self._push_undo_state()
        for idx in sorted(self.selected_indices):
            ok, err = self.engine.rotate_page_by(idx, delta)
            if not ok:
                if pushed:
                    self.undo_stack.pop()
                    self._refresh_undo_redo()
                messagebox.showerror("오류", f"페이지 회전에 실패했습니다.\n{err}")
                return
        self._load_thumbnails(keep_selection=True)

    def _delete_selected(self):
        if not self.selected_indices:
            return
        pushed = self._push_undo_state()
        for idx in sorted(self.selected_indices, reverse=True):
            ok, err = self.engine.delete_page(idx)
            if not ok:
                if pushed:
                    self.undo_stack.pop()
                    self._refresh_undo_redo()
                messagebox.showerror("오류", f"페이지 삭제에 실패했습니다.\n{err}")
                return
        self.selected_indices.clear()
        self._update_file_info()
        self._load_thumbnails()

    def _move_selected_to(self, target_index):
        if not self.selected_indices:
            return
        count = self.engine.page_count()
        if count == 0:
            return
        if target_index < 0 or target_index > count:
            return

        selected = sorted(self.selected_indices)
        if len(selected) == 1:
            from_index = selected[0]
            if from_index == target_index:
                return
            if target_index == count:
                remaining = [i for i in range(count) if i != from_index]
                order = remaining + [from_index]
                pushed = self._push_undo_state()
                ok, err = self.engine.reorder_pages(order)
                if not ok:
                    if pushed:
                        self.undo_stack.pop()
                        self._refresh_undo_redo()
                    messagebox.showerror("오류", f"페이지 이동에 실패했습니다.\n{err}")
                    return
                self.selected_indices.clear()
                self._load_thumbnails()
                return
            pushed = self._push_undo_state()
            ok, err = self.engine.move_page(from_index, target_index)
            if not ok:
                if pushed:
                    self.undo_stack.pop()
                    self._refresh_undo_redo()
                messagebox.showerror("오류", f"페이지 이동에 실패했습니다.\n{err}")
                return
            self.selected_indices.clear()
            self._update_file_info()
            self._load_thumbnails()
            return

        if target_index in self.selected_indices:
            return

        remaining = [i for i in range(count) if i not in self.selected_indices]
        insert_pos = 0
        for idx in remaining:
            if idx < target_index:
                insert_pos += 1
            else:
                break

        order = remaining[:insert_pos] + selected + remaining[insert_pos:]
        pushed = self._push_undo_state()
        ok, err = self.engine.reorder_pages(order)
        if not ok:
            if pushed:
                self.undo_stack.pop()
                self._refresh_undo_redo()
            messagebox.showerror("오류", f"페이지 이동에 실패했습니다.\n{err}")
            return
        self.selected_indices.clear()
        self._update_file_info()
        self._load_thumbnails()

    def _refresh_undo_redo(self):
        if not hasattr(self, "undo_btn"):
            return
        has_doc = self.engine.doc is not None
        self.undo_btn.configure(state="normal" if has_doc and self.undo_stack else "disabled")
        self.redo_btn.configure(state="normal" if has_doc and self.redo_stack else "disabled")
        self._refresh_action_buttons()

    def _refresh_action_buttons(self):
        if not hasattr(self, "rotate_left_btn"):
            return
        has_doc = self.engine.doc is not None
        has_selection = bool(self.selected_indices)
        rotate_state = "normal" if has_doc and has_selection else "disabled"
        delete_state = "normal" if has_doc and has_selection else "disabled"
        select_all_state = "normal" if has_doc else "disabled"
        self.rotate_left_btn.configure(state=rotate_state)
        self.rotate_right_btn.configure(state=rotate_state)
        self.delete_btn.configure(state=delete_state)
        self.select_all_btn.configure(state=select_all_state)

    def _undo(self):
        if not self.undo_stack or self.engine.doc is None:
            return
        current = self.engine.get_state_bytes()
        state = self.undo_stack.pop()
        ok, err = self.engine.load_state_bytes(state, mark_dirty=True)
        if not ok:
            messagebox.showerror("오류", f"Undo 실패했습니다.\n{err}")
            return
        if current is not None:
            self.redo_stack.append(current)
        self._refresh_undo_redo()
        self.selected_indices.clear()
        self._load_thumbnails()

    def _redo(self):
        if not self.redo_stack or self.engine.doc is None:
            return
        current = self.engine.get_state_bytes()
        state = self.redo_stack.pop()
        ok, err = self.engine.load_state_bytes(state, mark_dirty=True)
        if not ok:
            messagebox.showerror("오류", f"Redo 실패했습니다.\n{err}")
            return
        if current is not None:
            self.undo_stack.append(current)
        self._refresh_undo_redo()
        self.selected_indices.clear()
        self._load_thumbnails()

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
