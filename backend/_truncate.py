"""One-shot script: remove everything after '# -- END OF FILE --' in storage_service.py"""
import pathlib

p = pathlib.Path(__file__).with_name("storage_service.py")
text = p.read_text(encoding="utf-8")
marker = "# -- END OF FILE --"
idx = text.find(marker)
if idx == -1:
    print("ERROR: marker not found")
else:
    new_text = text[: idx + len(marker)] + "\n"
    p.write_text(new_text, encoding="utf-8")
    print(f"OK  — kept {new_text.count(chr(10))} lines")
