#!/usr/bin/env python3
"""CI 专用：依次跑 fork 改写脚本，把 runner 工作区改成 fork 身份，仓库源码一行都不落库。

每项改动一个脚本，放在 scripts/fork_edits/（文件名前缀即执行顺序）；本文件只负责按序调用，
任一脚本失败即中止 —— 各脚本自己校验「期望原文命中几次」，上游改了写法就不会静默漏改。

用法：
    python3 scripts/ci-fork-identity.py --app-id com.psyche.kelivo.fork --label Kelivo.F
    python3 scripts/ci-fork-identity.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITS_DIR = REPO_ROOT / "scripts" / "fork_edits"

DEFAULT_APP_ID = "com.psyche.kelivo.fork"
DEFAULT_LABEL = "Kelivo.F"

# about_page.dart 被 02 / 09 / 10 依次改写（硬编码应用名、fork 入口行、版本行改长按），
# 各自锚的是不同片段，但顺序固定下来最省心。最后一步 s99 从结果反查残留。
STEPS = (
    ("s01_package_id.py", "包名"),
    ("s02_app_label.py", "显示名"),
    ("s03_ci_version.py", "版本号来源"),
    ("s04_signing_v3.py", "v3 签名"),
    ("s05_r8_keepnames.py", "R8 keepnames"),
    ("s06_abi_arm64.py", "单 ABI"),
    ("s07_l10n.py", "l10n 文案"),
    ("s08_phone_control_label.py", "无障碍服务名"),
    ("s09_about_fork_link.py", "关于页 fork 入口"),
    ("s10_version_long_press.py", "版本行改长按"),
    ("s99_identity_check.py", "身份残留校验"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # 它进 APK 文件名与下载 URL
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.label):
        print(
            f"::error::--label 只允许 A-Za-z0-9._-：{args.label!r}",
            file=sys.stderr,
        )
        return 1

    for index, (name, title) in enumerate(STEPS, 1):
        path = EDITS_DIR / name
        if not path.is_file():
            print(f"::error::缺少改写脚本 {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        print(f"[{index}/{len(STEPS)}] {title}（{name}）", flush=True)
        cmd = [
            sys.executable,
            str(path),
            "--app-id",
            args.app_id,
            "--label",
            args.label,
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        if subprocess.run(cmd, cwd=REPO_ROOT).returncode != 0:
            print(f"::error::{name} 失败，中止", file=sys.stderr)
            return 1

    print(f"已改写为 fork 身份：appId={args.app_id} label={args.label}（仅工作区，不入库）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
