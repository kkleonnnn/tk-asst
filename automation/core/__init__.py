"""core/ —— 纯计算模块（dict 进、dict 出）。

硬约束（见 CONTRIBUTING.md 代码规范章）：
- 只放纯函数：不碰文件、网络、环境变量、当前时间（时间由调用方传入）。
- 纯 Python 标准库；禁 xml.etree（expat 坑），解析 XML 用正则。
"""
