# Windows PDF Editor

Python 기반의 Windows용 PDF 편집기입니다. 페이지 순서 변경, 삭제, 회전, 병합/삽입을 빠르게 처리하는 가벼운 GUI 도구입니다.

## Key Features
- 페이지 썸네일 기반 정렬: 드래그 앤 드롭으로 순서 변경
- 다중 선택: `Ctrl`/`Shift` 클릭, `Ctrl+A` 전체 선택
- 선택 페이지 회전(좌/우 90도) 및 삭제
- Undo/Redo 지원
- PDF 병합 및 특정 위치에 삽입(파일 드롭 포함)
- 페이지 미리보기 뷰어: 확대/축소(`Ctrl+휠`), 드래그 이동
- 다크/라이트 테마 전환
- 파일 크기/페이지 수 표시
- 선택 페이지 복사/붙여넣기(클립보드 경유)

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
- `파일 추가` 버튼 또는 파일 드롭으로 PDF를 병합/삽입합니다.
- `회전` / `삭제` 버튼으로 선택 페이지를 편집합니다.
- 우측 뷰어에서 `Ctrl+휠`로 확대/축소, 마우스 드래그로 이동합니다.
- `전체 저장`으로 결과를 저장합니다.

단축키
- `Ctrl+Z` / `Ctrl+Y`: Undo / Redo
- `Ctrl+A`: 전체 선택
- `Delete`: 선택 페이지 삭제
- `Ctrl+C` / `Ctrl+V`: 선택 페이지 복사 / 붙여넣기

## Tech Stack
- Python
- CustomTkinter
- PyMuPDF (fitz)
- Pillow
- tkinterdnd2
