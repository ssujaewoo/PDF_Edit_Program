# Windows PDF Editor

Python 기반의 Windows용 PDF 편집기입니다. PDF 페이지의 순서 변경(Drag & Drop), 삭제, 회전, 파일 병합 기능을 제공하는 가볍고 직관적인 GUI 도구입니다.

## Key Features
- 페이지 순서 변경 (Drag & Drop)
- 페이지 삭제
- 페이지 회전
- PDF 병합 (파일 추가)
- 썸네일 줌 및 다크/라이트 테마 전환

## Installation
```powershell
git clone <YOUR_GITHUB_REPO_URL>
cd PDF_Edit_Program
pip install -r requirements.txt
```

## How to Use
```powershell
python main.py
```

간단 사용법
- `PDF 열기`로 편집할 PDF를 불러옵니다.
- 썸네일을 드래그해 페이지 순서를 변경합니다.
- `삭제` / `회전` 버튼으로 페이지를 편집합니다.
- `파일 추가`로 다른 PDF를 병합합니다.
- 슬라이더로 썸네일 크기를 조절하고 스위치로 테마를 전환합니다.
- `전체 저장`으로 결과를 저장합니다.

## Tech Stack
- Python
- CustomTkinter
- PyMuPDF (fitz)
- Pillow
