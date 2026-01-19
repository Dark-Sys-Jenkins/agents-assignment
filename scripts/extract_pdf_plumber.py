import sys
from pathlib import Path

import pdfplumber

if len(sys.argv) < 2:
    print('Usage: extract_pdf_plumber.py <pdf_path> [out_path]')
    sys.exit(1)

pdf_path = Path(sys.argv[1])
out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / 'pdf_text_plumber.txt'

text_pages = []
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages, start=1):
        try:
            ptext = page.extract_text() or ''
        except Exception as e:
            ptext = f'[error extracting page {i}: {e}]'
        text_pages.append(ptext)

out_path.write_text('\n\n--- PAGE BREAK ---\n\n'.join(text_pages), encoding='utf-8')
print(f'Wrote extracted text to: {out_path}')
