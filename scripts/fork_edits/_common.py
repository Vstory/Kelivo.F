"""fork 改写的共用部分：定位仓库根、校验锚点、写回工作区。

所有改写只作用于 CI 的 runner 工作区 —— 身份一旦落库，每次 rebase 上游都要撞冲突。
每条改写都声明「期望原文应命中几次」，上游改了写法就整体失败，不允许静默漏改。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# (相对仓库根的路径, 期望原文, 替换文本, 期望命中次数；-1 表示至少命中一次)
Edit = tuple[str, str, str, int]

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_APP_ID = "com.psyche.kelivo.fork"
DEFAULT_LABEL = "Kelivo.F"


def fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.label):
        # label 会进 APK 文件名与下载 URL
        fail(f"--label 只允许 A-Za-z0-9._-：{args.label!r}")
    return args


def _head(text: str) -> str:
    first = text.splitlines()[0] if text else ""
    return first[:70]


def apply(edits: list[Edit], *, dry_run: bool) -> None:
    problems: list[str] = []
    for rel, old, new, want in edits:
        path = REPO_ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: 文件不存在")
            continue
        got = path.read_text(encoding="utf-8").count(old)
        if want < 0:
            if got < 1:
                problems.append(f"{rel}: 未命中: {_head(old)}")
        elif got != want:
            problems.append(f"{rel}: 期望 {want} 处、实际 {got} 处: {_head(old)}")

    if problems:
        print("::error::fork 改写的前置校验未通过：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        raise SystemExit(1)

    if dry_run:
        for rel, old, new, _ in edits:
            print(f"[dry-run] {rel}\n    - {old}\n    + {new}")
        return

    counts: dict[str, int] = {}
    for rel, old, new, _ in edits:
        path = REPO_ROOT / rel
        path.write_text(
            path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
        )
        counts[rel] = counts.get(rel, 0) + 1
    for rel, count in counts.items():
        print(f"  {rel}: 已改写 {count} 处")
