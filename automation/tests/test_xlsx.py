"""core/xlsx 单测：不依赖 xml.etree 的正则解析（在测试里现造一个最小 xlsx）。"""
import io
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import xlsx  # noqa: E402


def make_xlsx(shared, sheet_xml):
    """现造最小 xlsx：sharedStrings + sheet1。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        si = "".join(f"<si><t>{s}</t></si>" for s in shared)
        z.writestr("xl/sharedStrings.xml",
                   f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{si}</sst>')
        z.writestr("xl/worksheets/sheet1.xml",
                   '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   f"<sheetData>{sheet_xml}</sheetData></worksheet>")
    return buf.getvalue()


class TestReadRows(unittest.TestCase):
    def test_shared_strings_and_numbers(self):
        data = make_xlsx(
            ["商品名", "近30天销量", "测试品"],
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>9800</v></c></row>')
        rows = xlsx.read_rows(data)
        self.assertEqual(rows[0], ["商品名", "近30天销量"])
        self.assertEqual(rows[1], ["测试品", "9800"])

    def test_inline_str_and_gap_columns(self):
        data = make_xlsx(
            [],
            '<row r="1"><c r="A1" t="inlineStr"><is><t>甲</t></is></c>'
            '<c r="C1"><v>3</v></c></row>')
        rows = xlsx.read_rows(data)
        self.assertEqual(rows[0], ["甲", "", "3"])   # B1 空洞补空串

    def test_empty_selfclosed_cell(self):
        data = make_xlsx([], '<row r="1"><c r="A1"/><c r="B1"><v>1</v></c></row>')
        self.assertEqual(xlsx.read_rows(data)[0], ["", "1"])

    def test_no_etree_dependency(self):
        """铁律：禁 import xml.etree（expat 坑）——文档里提到没关系，import 不行。"""
        import re as _re
        auto_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for base, _dirs, files in os.walk(auto_dir):
            if "__pycache__" in base:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                src = open(os.path.join(base, fn), encoding="utf-8").read()
                self.assertIsNone(
                    _re.search(r"^\s*(import\s+xml|from\s+xml)", src, _re.M),
                    f"{fn} import 了 xml.*（expat 坑，改用正则解析）")


if __name__ == "__main__":
    unittest.main()
