import ctypes
import os
import customtkinter as ctk
from tkinter import messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image

from pdf_engine import PdfEngine
from ui_components import UIComponents
from event_handlers import PdfEventHandlers
from dnd_manager import DndManager

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class PdfEditorApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self._dnd_available = True
        except Exception:
            self._dnd_available = False

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
        self.max_columns = 1
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
        self._last_selected_index = None
        self._external_drag_requested = False
        self.dnd_temp_files = []
        self.handlers = PdfEventHandlers(self)
        self.dnd = DndManager(self)
        self.ui = UIComponents(self)

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.ui.build()
        if self._dnd_available:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self.dnd.on_file_drop)
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _bind_shortcuts(self):
        self.bind_all("<Control-z>", lambda event: self.handlers.undo())
        self.bind_all("<Control-y>", lambda event: self.handlers.redo())
        self.bind_all("<Control-Z>", lambda event: self.handlers.redo())
        self.bind_all("<Control-Shift-Z>", lambda event: self.handlers.redo())
        self.bind_all("<Control-a>", lambda event: self._select_all())
        self.bind_all("<Control-c>", lambda event: self.handlers.copy_selected())
        self.bind_all("<Control-v>", lambda event: self.handlers.paste_pages())
        self.bind_all("<Delete>", lambda event: self.handlers.delete_selected())

    def _load_thumbnails(self, keep_selection=False):
        if self.engine.page_count() == 0:
            return

        self._clear_thumbnails(keep_selection=keep_selection)

        for page_index in range(self.engine.page_count()):
            pix = self.engine.get_page_pixmap(page_index, self.thumbnail_scale)
            if pix is None:
                continue

            mode = "RGBA" if pix.alpha else "RGB"
            image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(pix.width, pix.height))

            frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
            frame.grid(row=page_index, column=0, padx=12, pady=12, sticky="ew")
            frame.grid_columnconfigure(0, weight=1)

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
                    "image_label": image_label,
                    "page_label": page_label,
                }
            )

        self._refresh_undo_redo()
        self._refresh_selection_styles()
        self._update_scrollregion()
        if self.engine.page_count() > 0:
            self.ui.show_page_in_viewer(0)

    def _clear_thumbnails(self, keep_selection=False):
        for item in self.page_widgets:
            item["frame"].destroy()
        self.page_widgets.clear()
        if not keep_selection:
            self.selected_indices.clear()
        self.dnd.clear_drag_state()

    def _refresh_thumbnail(self, page_index):
        if page_index < 0 or page_index >= len(self.page_widgets):
            return
        pix = self.engine.get_page_pixmap(page_index, self.thumbnail_scale)
        if pix is None:
            return
        mode = "RGBA" if pix.alpha else "RGB"
        image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(pix.width, pix.height))
        item = self.page_widgets[page_index]
        item["image"] = ctk_image
        item["pil_image"] = image
        item["image_label"].configure(image=ctk_image, text="")

    def _refresh_thumbnails(self, indices):
        for idx in indices:
            self._refresh_thumbnail(idx)


    def _register_drag_source(self, widget, page_index):
        try:
            widget.drag_source_register(1, DND_FILES)
            widget.dnd_bind("<<DragInitCmd>>", lambda event, idx=page_index: self.dnd.on_drag_init(event, idx))
        except Exception:
            return

    def _bind_drag_events(self, frame, image_label, page_label, page_index):
        frame.bind("<Button-1>", lambda event, idx=page_index: self._on_thumbnail_click(event, idx))
        frame.bind("<B1-Motion>", self.dnd.on_drag_motion)
        frame.bind("<ButtonRelease-1>", self.dnd.on_drag_release)

        image_label.bind("<Button-1>", lambda event, idx=page_index: self._on_thumbnail_click(event, idx))
        image_label.bind("<B1-Motion>", self.dnd.on_drag_motion)
        image_label.bind("<ButtonRelease-1>", self.dnd.on_drag_release)

        page_label.bind("<Button-1>", lambda event, idx=page_index: self._on_thumbnail_click(event, idx))
        page_label.bind("<B1-Motion>", self.dnd.on_drag_motion)
        page_label.bind("<ButtonRelease-1>", self.dnd.on_drag_release)

    def _on_thumbnail_click(self, event, page_index):
        self.dnd.on_page_press(event, page_index)
        self.ui.show_page_in_viewer(page_index)

    def _on_columns_change(self, value):
        self.max_columns = max(1, int(round(float(value))))
        if hasattr(self, "columns_value"):
            self.columns_value.configure(text=str(self.max_columns))
        if self.engine.page_count() > 0:
            self._load_thumbnails(keep_selection=True)

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
        for temp_path in list(self.dnd_temp_files):
            try:
                os.remove(temp_path)
            except OSError:
                pass
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
        self._last_selected_index = None
        self._refresh_selection_styles()

    def _on_background_click(self, event):
        canvas = getattr(self.scroll_frame, "_parent_canvas", None)
        if event.widget is self.scroll_frame or (canvas is not None and event.widget is canvas):
            self._clear_selection()

    def _modifier_state(self, event):
        if event is None:
            return {"shift": False, "ctrl": False}
        state = getattr(event, "state", 0)
        return {
            "shift": bool(state & 0x0001),
            "ctrl": bool(state & 0x0004),
        }

    def _apply_click_selection(self, page_index, event):
        if page_index is None:
            return
        mods = self._modifier_state(event)
        if mods["shift"] and self._last_selected_index is not None:
            start = min(self._last_selected_index, page_index)
            end = max(self._last_selected_index, page_index)
            self.selected_indices = set(range(start, end + 1))
            self._refresh_selection_styles()
        elif mods["ctrl"]:
            self._toggle_selection(page_index)
        else:
            self.selected_indices = {page_index}
            self._refresh_selection_styles()
        self._last_selected_index = page_index

    def _select_all(self):
        if self.engine.page_count() == 0:
            return
        all_indices = set(range(self.engine.page_count()))
        if self.selected_indices == all_indices:
            self._clear_selection()
        else:
            self.selected_indices = all_indices
            self._last_selected_index = 0
            self._refresh_selection_styles()

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

