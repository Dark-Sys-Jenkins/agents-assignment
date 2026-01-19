from pypdf import PdfReader
import sys

if len(sys.argv) < 2:
    print('Usage: extract_pdf.py <pdf_path>')
    sys.exit(1)

path = sys.argv[1]
reader = PdfReader(path)
text = []
for page in reader.pages:
    try:
        text.append(page.extract_text() or "")
    except Exception as e:
        text.append(f"[error extracting page: {e}]")

out = "\n\n--- PAGE BREAK ---\n\n".join(text)
print(out)
