"""极简 xlsx 读取（纯标准库，忽略样式/公式）。

只为把出海匠等导出的 xlsx 读成二维文本表格；不依赖 openpyxl（保持零依赖、可移植）。
用法：read_rows(data_bytes) -> list[list[str]]（第一个工作表的所有行）。
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col_index(ref):
    letters = "".join(ch for ch in ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1 if n else 0


def read_rows(data):
    """bytes -> list[list[str]]，读第一个工作表。空单元格补空串。"""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()

    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

    sheets = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml", n))
    if not sheets:
        return []
    root = ET.fromstring(z.read(sheets[0]))

    rows = []
    for row in root.iter(f"{_NS}row"):
        cells = {}
        for c in row.findall(f"{_NS}c"):
            ref = c.get("r") or ""
            idx = _col_index(ref) if ref else len(cells)
            t = c.get("t")
            v = c.find(f"{_NS}v")
            if t == "s":
                val = shared[int(v.text)] if (v is not None and v.text) else ""
            elif t == "inlineStr":
                is_ = c.find(f"{_NS}is")
                val = "".join(x.text or "" for x in is_.iter(f"{_NS}t")) if is_ is not None else ""
            else:
                val = v.text if (v is not None and v.text is not None) else ""
            cells[idx] = val
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows
