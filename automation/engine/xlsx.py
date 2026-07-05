"""极简 xlsx 读取（纯标准库 + 正则，忽略样式/公式）。

只为把出海匠等导出的 xlsx 读成二维文本表格。
⚠️ 刻意**不用 xml.etree.ElementTree**——某些 Python 环境（如部分 brew Python）缺 pyexpat，
   会报 "No module named expat"。改用正则解析 xlsx 的 XML，任何 python3 都能跑（含校长机器）。
用法：read_rows(data_bytes) -> list[list[str]]（第一个工作表的所有行）。
"""
import io
import re
import zipfile
from html import unescape

_ROW = re.compile(r"<row\b[^>]*>(.*?)</row>", re.S)
# 单元格：自组闭合 <c .../>  或  <c ...>...</c>
_CELL = re.compile(r"<c\b([^>]*?)/>|<c\b([^>]*?)>(.*?)</c>", re.S)
_ATTR_R = re.compile(r'\br="([^"]*)"')
_ATTR_T = re.compile(r'\bt="([^"]*)"')
_V = re.compile(r"<v[^>]*>(.*?)</v>", re.S)
_T = re.compile(r"<t[^>]*>(.*?)</t>", re.S)
_SI = re.compile(r"<si>(.*?)</si>", re.S)
_SHEET = re.compile(r"xl/worksheets/sheet\d+\.xml")


def _col_index(ref):
    m = re.match(r"[A-Za-z]+", ref or "")
    if not m:
        return 0
    n = 0
    for ch in m.group(0).upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _shared_strings(xml):
    return [unescape("".join(_T.findall(si))) for si in _SI.findall(xml)]


def read_rows(data):
    """bytes -> list[list[str]]，读第一个工作表。空单元格补空串。"""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()

    shared = []
    if "xl/sharedStrings.xml" in names:
        shared = _shared_strings(z.read("xl/sharedStrings.xml").decode("utf-8", "ignore"))

    sheets = sorted(n for n in names if _SHEET.fullmatch(n))
    if not sheets:
        return []
    xml = z.read(sheets[0]).decode("utf-8", "ignore")

    rows = []
    for rowxml in _ROW.findall(xml):
        cells = {}
        auto = 0
        for m in _CELL.finditer(rowxml):
            if m.group(1) is not None:          # 自闭合空单元格 <c .../>
                attrs, inner = m.group(1), None
            else:
                attrs, inner = m.group(2), m.group(3)
            ref = _ATTR_R.search(attrs)
            idx = _col_index(ref.group(1)) if ref else auto
            auto = idx + 1
            if inner is None:
                val = ""
            else:
                tm = _ATTR_T.search(attrs)
                t = tm.group(1) if tm else None
                if t == "s":                     # 共享字符串
                    vm = _V.search(inner)
                    val = shared[int(vm.group(1))] if vm else ""
                elif t == "inlineStr":           # 内联字符串
                    val = unescape("".join(_T.findall(inner)))
                else:                            # 数字 / 普通字符串(t="str")
                    vm = _V.search(inner)
                    val = unescape(vm.group(1)) if vm else ""
            cells[idx] = val
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows
