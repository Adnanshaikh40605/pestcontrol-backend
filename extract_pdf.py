from pathlib import Path
try:
    from pypdf import PdfReader
except ImportError:
    print("install pypdf")
    raise

base = Path(__file__).parent
for p in sorted(base.glob("DocScanner*.pdf")):
    print("=" * 60, p.name)
    r = PdfReader(str(p))
    for i, page in enumerate(r.pages):
        t = page.extract_text() or ""
        print(f"--- page {i+1} ---")
        print(t[:5000])
