#!/usr/bin/env bash
# 由 reference/ + sop/ 自动生成「通用知识包.md」——任何 AI / 人都能直接读用。
# 用法： bash scripts/build_pack.sh
# 注意：通用知识包.md 是生成物，请勿手改；改知识请改 reference//sop/ 后重新跑本脚本。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/通用知识包.md"

# 目录校验（缺失时给可读提示，而非 find 原始报错）
for d in reference sop; do
  [ -d "$ROOT/$d" ] || { echo "缺少目录 $d/，请在仓库根目录运行本脚本" >&2; exit 1; }
done

# 收集 reference/ 与 sop/ 下的知识文件：排除 README.md 与以 _ 开头的辅助文件（如 _消化日志.md）
FILES=$(find "$ROOT/reference" "$ROOT/sop" -type f -name '*.md' ! -name 'README.md' ! -name '_*' | sort)

{
  echo "# TikTok Shop 东南亚运营助理 · 通用知识包"
  echo
  echo "> 本文件由 \`scripts/build_pack.sh\` 从 reference/ 与 sop/ 自动生成，**请勿手改**。"
  echo "> 改知识请改 reference//sop/ 后重新生成。**任何 AI 模型**都可把本文件作为上下文使用。"
  echo "> 当前主攻：马来西亚 · 跨境店（从中国发货）。以文件内标注的时间基准/可信度/来源为准。"
  echo
  echo "## 目录"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    echo "- ${f#"$ROOT"/}"
  done <<< "$FILES"
  echo
  echo "---"
  echo
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || { echo "跳过非常规文件: $f" >&2; continue; }
    echo "# 【${f#"$ROOT"/}】"
    echo
    cat "$f"
    echo
    echo
    echo "---"
    echo
  done <<< "$FILES"
} > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"   # 先写临时文件再原子替换：中途失败不会把 通用知识包.md 留成半截

COUNT=$(printf '%s\n' "$FILES" | grep -c . || true)
echo "已生成 $OUT （纳入 $COUNT 个知识文件）"
