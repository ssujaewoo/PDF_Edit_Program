import os
import re
import tempfile
import fitz
from tkinter import filedialog, messagebox


class PdfEventHandlers:
    def __init__(self, app):
        self.app = app

    def open_pdf(self, path=None, confirm_discard=True):
        app = self.app
        if confirm_discard and not app._confirm_discard_if_dirty():
            return
        if path is None:
            path = filedialog.askopenfilename(
                title="PDF 파일 선택",
                filetypes=[("PDF files", "*.pdf")],
            )
        if not path:
            return

        app.engine.close()
        app._clear_thumbnails()
        app.undo_stack.clear()
        app.redo_stack.clear()
        app._refresh_undo_redo()

        ok, err = app.engine.open(path)
        if not ok:
            messagebox.showerror("오류", f"PDF를 열 수 없습니다.\n{err}")
            return

        app.current_path = path
        app._update_file_info()
        app._load_thumbnails()

    def merge_pdf(self, path=None):
        app = self.app
        if app.engine.page_count() == 0:
            messagebox.showinfo("안내", "먼저 PDF를 열어주세요.")
            return
        if path is None:
            path = filedialog.askopenfilename(
                title="추가할 PDF 선택",
                filetypes=[("PDF files", "*.pdf")],
            )
        if not path:
            return

        pushed = app._push_undo_state()
        ok, err = app.engine.insert_pdf(path)
        if not ok:
            if pushed:
                app.undo_stack.pop()
                app._refresh_undo_redo()
            messagebox.showerror("오류", f"PDF 병합에 실패했습니다.\n{err}")
            return

        app._update_file_info()
        app._load_thumbnails()

    def save_all(self):
        app = self.app
        if app.engine.page_count() == 0:
            messagebox.showinfo("안내", "저장할 문서가 없습니다.")
            return

        path = filedialog.asksaveasfilename(
            title="전체 저장",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return

        ok, err = app.engine.save(path)
        if not ok:
            messagebox.showerror("오류", f"저장에 실패했습니다.\n{err}")
            return

        app.current_path = path
        app._update_file_info()
        messagebox.showinfo("완료", "저장이 완료되었습니다.")

    def reset(self):
        app = self.app
        if not app._confirm_discard_if_dirty():
            return
        app.engine.close()
        app._clear_thumbnails()
        app.undo_stack.clear()
        app.redo_stack.clear()
        app.current_path = None
        app._update_file_info()
        app._refresh_undo_redo()

    def undo(self):
        app = self.app
        if not app.undo_stack or app.engine.doc is None:
            return
        current = app.engine.get_state_bytes()
        state = app.undo_stack.pop()
        ok, err = app.engine.load_state_bytes(state, mark_dirty=True)
        if not ok:
            messagebox.showerror("오류", f"Undo 실패했습니다.\n{err}")
            return
        if current is not None:
            app.redo_stack.append(current)
        app._refresh_undo_redo()
        app.selected_indices.clear()
        app._load_thumbnails()

    def redo(self):
        app = self.app
        if not app.redo_stack or app.engine.doc is None:
            return
        current = app.engine.get_state_bytes()
        state = app.redo_stack.pop()
        ok, err = app.engine.load_state_bytes(state, mark_dirty=True)
        if not ok:
            messagebox.showerror("오류", f"Redo 실패했습니다.\n{err}")
            return
        if current is not None:
            app.undo_stack.append(current)
        app._refresh_undo_redo()
        app.selected_indices.clear()
        app._load_thumbnails()

    def delete_page(self, page_index):
        app = self.app
        pushed = app._push_undo_state()
        ok, err = app.engine.delete_page(page_index)
        if not ok:
            if pushed:
                app.undo_stack.pop()
                app._refresh_undo_redo()
            messagebox.showerror("오류", f"페이지 삭제에 실패했습니다.\n{err}")
            return
        app._load_thumbnails()

    def rotate_page(self, page_index):
        app = self.app
        pushed = app._push_undo_state()
        ok, err = app.engine.rotate_page_by(page_index, 90)
        if not ok:
            if pushed:
                app.undo_stack.pop()
                app._refresh_undo_redo()
            messagebox.showerror("오류", f"페이지 회전에 실패했습니다.\n{err}")
            return
        app._load_thumbnails()

    def rotate_selected(self, delta):
        app = self.app
        if not app.selected_indices:
            return
        pushed = app._push_undo_state()
        for idx in sorted(app.selected_indices):
            ok, err = app.engine.rotate_page_by(idx, delta)
            if not ok:
                if pushed:
                    app.undo_stack.pop()
                    app._refresh_undo_redo()
                messagebox.showerror("오류", f"페이지 회전에 실패했습니다.\n{err}")
                return
        app._refresh_thumbnails(sorted(app.selected_indices))
        app._refresh_selection_styles()
        if getattr(app, "viewer_page_index", None) in app.selected_indices:
            app.ui.show_page_in_viewer(app.viewer_page_index, reset_zoom=False)

    def delete_selected(self):
        app = self.app
        if not app.selected_indices:
            return
        pushed = app._push_undo_state()
        count = app.engine.page_count()
        remaining = [i for i in range(count) if i not in app.selected_indices]
        if not remaining:
            app.engine.close()
            app._clear_thumbnails()
            app.undo_stack.clear()
            app.redo_stack.clear()
            app.selected_indices.clear()
            app._update_file_info()
            app._refresh_undo_redo()
            app.ui.clear_viewer()
            return

        ok, err = app.engine.keep_pages(remaining)
        if not ok:
            if pushed:
                app.undo_stack.pop()
                app._refresh_undo_redo()
            messagebox.showerror("오류", f"페이지 삭제에 실패했습니다.\n{err}")
            return
        app.selected_indices.clear()
        app._update_file_info()
        app._load_thumbnails()

    def insert_pdf_at(self, path, index):
        app = self.app
        if app.engine.page_count() == 0:
            return self.open_pdf(path)
        ok, err = app.engine.insert_pdf_at(path, index)
        if not ok:
            messagebox.showerror("오류", f"PDF 삽입에 실패했습니다.\n{err}")
            return
        app._update_file_info()
        app._load_thumbnails()

    def copy_selected(self):
        app = self.app
        if not app.selected_indices:
            return
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_path = temp.name
        temp.close()

        ok, err = app.engine.export_pages(sorted(app.selected_indices), temp_path)
        if not ok:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            messagebox.showerror("Error", f"Copy failed.\n{err}")
            return

        app.clipboard_clear()
        app.clipboard_append(temp_path)
        app.dnd_temp_files.append(temp_path)

    def paste_pages(self):
        app = self.app
        paths = self._parse_clipboard_files()
        if not paths:
            return

        pdfs = [p for p in paths if os.path.exists(p) and p.lower().endswith(".pdf")]
        if not pdfs:
            messagebox.showinfo("Info", "No PDF file in clipboard.")
            return

        if app.engine.page_count() == 0:
            self.open_pdf(pdfs[0], confirm_discard=False)
            for path in pdfs[1:]:
                self.merge_pdf(path)
            return

        app._push_undo_state()
        insert_at = max(app.selected_indices) + 1 if app.selected_indices else app.engine.page_count()
        new_indices = []
        for path in pdfs:
            ok, err = app.engine.insert_pdf_at(path, insert_at)
            if not ok:
                messagebox.showerror("Error", f"Paste failed.\n{err}")
                break
            count = self._count_pages_in_pdf(path)
            if count:
                new_indices.extend(range(insert_at, insert_at + count))
                insert_at += count

        app._update_file_info()
        app._load_thumbnails()
        if new_indices:
            app.selected_indices = set(new_indices)
            app._last_selected_index = new_indices[-1]
            app._refresh_selection_styles()
            app.ui.show_page_in_viewer(new_indices[0])

    def _parse_clipboard_files(self):
        app = self.app
        try:
            text = app.clipboard_get()
        except Exception:
            return []
        if not text:
            return []
        if "{" in text and "}" in text:
            return [item.strip() for item in re.findall(r"\{([^}]*)\}", text) if item.strip()]
        return [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]

    def _count_pages_in_pdf(self, path):
        try:
            doc = fitz.open(path)
            try:
                return len(doc)
            finally:
                doc.close()
        except Exception:
            return 0
