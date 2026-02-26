import fitz


class PdfEngine:
    def __init__(self):
        self.doc = None
        self.is_dirty = False

    def open(self, path):
        try:
            self.doc = fitz.open(path)
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = False
        return True, ""

    def close(self):
        if self.doc is not None:
            try:
                self.doc.close()
            finally:
                self.doc = None
                self.is_dirty = False

    def get_state_bytes(self):
        if not self.doc:
            return None
        return self.doc.tobytes()

    def load_state_bytes(self, data, mark_dirty=True):
        if data is None:
            return False, "臾몄꽌媛 ?대젮 ?덉? ?딆뒿?덈떎."
        try:
            if self.doc is not None:
                self.doc.close()
            self.doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = mark_dirty
        return True, ""

    def page_count(self):
        return len(self.doc) if self.doc else 0

    def get_page_pixmap(self, index, scale):
        if not self.doc:
            return None
        page = self.doc.load_page(index)
        return page.get_pixmap(matrix=fitz.Matrix(scale, scale))

    def save(self, path):
        if not self.doc:
            return False, "문서가 열려 있지 않습니다."
        try:
            self.doc.save(path)
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = False
        return True, ""

    def delete_page(self, index):
        if not self.doc:
            return False, "문서가 열려 있지 않습니다."
        if index < 0 or index >= len(self.doc):
            return False, "유효하지 않은 페이지입니다."
        try:
            self.doc.delete_page(index)
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = True
        return True, ""

    def rotate_page(self, index):
        return self.rotate_page_by(index, 90)

    def rotate_page_by(self, index, delta):
        if not self.doc:
            return False, "??? ?? ?? ????."
        if index < 0 or index >= len(self.doc):
            return False, "???? ?? ??????."
        try:
            page = self.doc.load_page(index)
            page.set_rotation((page.rotation + delta) % 360)
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = True
        return True, ""

    def move_page(self, from_index, to_index):
        if not self.doc:
            return False, "문서가 열려 있지 않습니다."
        if from_index < 0 or from_index >= len(self.doc):
            return False, "유효하지 않은 페이지입니다."
        if to_index < 0 or to_index >= len(self.doc):
            return False, "유효하지 않은 페이지입니다."
        try:
            self.doc.move_page(from_index, to_index)
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = True
        return True, ""

    def reorder_pages(self, order):
        if not self.doc:
            return False, "문서가 열려 있지 않습니다."
        if len(order) != len(self.doc):
            return False, "유효하지 않은 페이지 순서입니다."
        if sorted(order) != list(range(len(self.doc))):
            return False, "유효하지 않은 페이지 순서입니다."
        try:
            new_doc = fitz.open()
            for idx in order:
                new_doc.insert_pdf(self.doc, from_page=idx, to_page=idx)
            self.doc.close()
            self.doc = new_doc
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = True
        return True, ""

    def insert_pdf(self, path):
        if not self.doc:
            return False, "문서가 열려 있지 않습니다."
        try:
            other_doc = fitz.open(path)
            try:
                self.doc.insert_pdf(other_doc)
            finally:
                other_doc.close()
        except Exception as exc:
            return False, str(exc)
        self.is_dirty = True
        return True, ""
