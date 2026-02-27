import os
import tkinter as tk
from PIL import ImageTk
from tkinterdnd2 import COPY, DND_FILES


class DndManager:
    def __init__(self, app):
        self.app = app


    def on_file_drop(self, event):
        app = self.app
        paths = self._parse_drop_files(getattr(event, "data", ""))
        pdfs = [p for p in paths if p.lower().endswith(".pdf")]
        if not pdfs:
            return

        drop_index = None
        if app.page_widgets:
            target_index = self.find_closest_index(event.x_root, event.y_root)
            if target_index is not None:
                insert_after = self.is_insert_after(target_index, event.x_root)
                drop_index = target_index + 1 if insert_after else target_index

        if app.engine.page_count() == 0:
            app.handlers.open_pdf(pdfs[0])
            pdfs = pdfs[1:]
            drop_index = None

        if drop_index is None:
            for path in pdfs:
                app.handlers.merge_pdf(path)
            return

        for path in pdfs:
            before = app.engine.page_count()
            app.handlers.insert_pdf_at(path, drop_index)
            after = app.engine.page_count()
            added = max(0, after - before)
            drop_index += added

    def _parse_drop_files(self, data):
        if not data:
            return []
        files = []
        current = ""
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                current = ""
            elif ch == "}":
                in_brace = False
                if current:
                    files.append(current)
                    current = ""
            elif ch == " " and not in_brace:
                if current:
                    files.append(current)
                    current = ""
            else:
                current += ch
        if current:
            files.append(current)

        cleaned = []
        for path in files:
            if path.startswith("file://"):
                path = path[7:]
                if path.startswith("/") and len(path) > 3 and path[2] == ":":
                    path = path[1:]
            path = path.strip()
            if path and os.path.exists(path):
                cleaned.append(path)
        return cleaned


    def on_drag_init(self, event, page_index):
        app = self.app
        ctrl = False
        if hasattr(event, "modifiers") and event.modifiers:
            ctrl = "Control" in event.modifiers
        if not ctrl:
            state = getattr(event, "state", 0)
            ctrl = bool(state & 0x0004)
        if not ctrl:
            return None
        if app.engine.page_count() == 0:
            return None

        if app.selected_indices:
            indices = sorted(app.selected_indices)
        else:
            indices = [page_index]
            app.selected_indices = {page_index}
            app._refresh_selection_styles()

        path = self._export_selected_pages(indices)
        if not path:
            return None
        data = self._format_drop_path(path)
        return (COPY, DND_FILES, data)

    def _export_selected_pages(self, indices):
        app = self.app
        import tempfile
        fd, path = tempfile.mkstemp(prefix="pdf_edit_", suffix=".pdf")
        os.close(fd)
        ok, err = app.engine.export_pages(indices, path)
        if not ok:
            try:
                os.remove(path)
            except OSError:
                pass
            return None
        if not hasattr(app, "dnd_temp_files"):
            app.dnd_temp_files = []
        app.dnd_temp_files.append(path)
        return path

    def _format_drop_path(self, path):
        if " " in path or "\t" in path:
            return "{" + path + "}"
        return path

    def on_page_press(self, event, page_index):
        app = self.app
        app._press_index = page_index
        app._press_pos = (event.x_root, event.y_root)
        app._drag_started = False
        app._external_drag_requested = bool(getattr(event, "state", 0) & 0x0004)

    def on_drag_motion(self, event):
        app = self.app
        if app._external_drag_requested:
            if app.drag_ghost is None:
                self.start_drag_ghost(event, app._press_index, alpha=0.4)
            self.move_drag_ghost(event)
            return
        if app._press_index is None:
            return
        if not app._drag_started and app._press_pos is not None:
            dx = event.x_root - app._press_pos[0]
            dy = event.y_root - app._press_pos[1]
            if (dx * dx + dy * dy) < 36:
                return
            app._drag_started = True
            if app._press_index not in app.selected_indices:
                app.selected_indices.add(app._press_index)
                app._refresh_selection_styles()
            app.drag_start_index = app._press_index
            app.drag_target_index = app._press_index
            app.drag_drop_index = app._press_index
            app.drag_source_frame = app.page_widgets[app._press_index]["frame"]
            self.set_drag_highlight(app.drag_source_frame, True, app._press_index)
            self.start_drag_ghost(event, app._press_index)
        if not app._drag_started:
            return

        target_index = self.find_closest_index(event.x_root, event.y_root)
        if target_index is None:
            return

        insert_after = self.is_insert_after(target_index, event.x_root)
        drop_index = target_index + 1 if insert_after else target_index
        self.set_target_highlight(target_index)
        app.drag_drop_index = drop_index
        self.update_insert_indicator(target_index, insert_after)
        self.move_drag_ghost(event)

    def on_drag_release(self, event):
        app = self.app
        if app._press_index is None:
            return
        if app._external_drag_requested:
            self.stop_drag_ghost()
            app._press_index = None
            app._press_pos = None
            app._external_drag_requested = False
            return
        if not app._drag_started:
            app._apply_click_selection(app._press_index, event)
            app._press_index = None
            app._press_pos = None
            return

        if app.drag_drop_index is None:
            self.clear_drag_state()
            self.stop_drag_ghost()
            app._press_index = None
            app._press_pos = None
            return

        to_index = app.drag_drop_index
        self.clear_drag_state()
        self.stop_drag_ghost()
        app._move_selected_to(to_index)
        app._press_index = None
        app._press_pos = None

    def find_closest_index(self, x_root, y_root):
        app = self.app
        if not app.page_widgets:
            return None

        closest_index = None
        closest_distance = None
        for index, item in enumerate(app.page_widgets):
            frame = item["frame"]
            cx = frame.winfo_rootx() + frame.winfo_width() / 2
            cy = frame.winfo_rooty() + frame.winfo_height() / 2
            distance = (cx - x_root) ** 2 + (cy - y_root) ** 2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_index = index

        return closest_index

    def set_drag_highlight(self, frame, enabled, index):
        app = self.app
        if enabled:
            if index in app.selected_indices:
                frame.configure(border_color="#F2A900")
            else:
                frame.configure(border_width=2, border_color="#F2A900")
        else:
            if index in app.selected_indices:
                frame.configure(border_color=app.selected_border)
            else:
                frame.configure(border_width=0)

    def set_target_highlight(self, target_index):
        app = self.app
        if (
            app.drag_target_frame is not None
            and app.drag_target_index != target_index
            and app.drag_target_frame is not app.drag_source_frame
        ):
            self.set_drag_highlight(app.drag_target_frame, False, app.drag_target_index)

        app.drag_target_index = target_index
        app.drag_target_frame = app.page_widgets[target_index]["frame"]
        if app.drag_target_frame is not app.drag_source_frame:
            self.set_drag_highlight(app.drag_target_frame, True, target_index)
        self.update_insert_indicator(target_index, False)

    def clear_drag_state(self):
        app = self.app
        if app.drag_source_frame is not None and app.drag_start_index is not None:
            self.set_drag_highlight(app.drag_source_frame, False, app.drag_start_index)
        if (
            app.drag_target_frame is not None
            and app.drag_target_frame is not app.drag_source_frame
            and app.drag_target_index is not None
        ):
            self.set_drag_highlight(app.drag_target_frame, False, app.drag_target_index)
        self.hide_insert_indicator()

        app.drag_start_index = None
        app.drag_target_index = None
        app.drag_source_frame = None
        app.drag_target_frame = None
        app.drag_drop_index = None

    def start_drag_ghost(self, event, page_index, alpha=1.0):
        app = self.app
        self.stop_drag_ghost()
        if page_index < 0 or page_index >= len(app.page_widgets):
            return
        pil_image = app.page_widgets[page_index]["pil_image"]
        ghost = tk.Toplevel(app)
        ghost.wm_overrideredirect(True)
        ghost.attributes("-topmost", True)
        try:
            ghost.attributes("-alpha", alpha)
        except Exception:
            pass
        image = ImageTk.PhotoImage(pil_image)
        label = tk.Label(ghost, image=image, bd=0)
        label.image = image
        label.pack()
        ghost.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        app.drag_ghost = ghost
        app.drag_ghost_image = image

    def move_drag_ghost(self, event):
        app = self.app
        if app.drag_ghost is None:
            return
        app.drag_ghost.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

    def stop_drag_ghost(self):
        app = self.app
        if app.drag_ghost is not None:
            app.drag_ghost.destroy()
            app.drag_ghost = None
            app.drag_ghost_image = None

    def update_insert_indicator(self, target_index, insert_after):
        app = self.app
        if not hasattr(app.scroll_frame, "_parent_canvas") or app.insert_line is None:
            return
        if target_index is None or not app.page_widgets:
            return
        canvas = app.scroll_frame._parent_canvas
        frame = app.page_widgets[target_index]["frame"]
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
        canvas.coords(app.insert_line, rel_x, rel_y0, rel_x, rel_y1)
        canvas.itemconfigure(app.insert_line, state="normal")

    def hide_insert_indicator(self):
        app = self.app
        if hasattr(app.scroll_frame, "_parent_canvas") and app.insert_line is not None:
            app.scroll_frame._parent_canvas.itemconfigure(app.insert_line, state="hidden")

    def is_insert_after(self, target_index, x_root):
        app = self.app
        frame = app.page_widgets[target_index]["frame"]
        center = frame.winfo_rootx() + frame.winfo_width() / 2
        return x_root >= center
