#!/usr/bin/env python3
# SCRIPT_VERSION=1.1.0    # 脚本版本(无模板上游, 独立维护; 内容变更 +1)
"""无障碍服务名：values*/phone_control.xml 的 label 跟着改名。

这个名字显示在系统设置里，只改 arb 文案会让提示指向系统里不存在的名字。
授权按组件名绑定，改 label 不影响已开启的服务。
按行匹配而不是按整串：各语言把品牌名放的位置不同（ru 是「Управление телефоном Kelivo」后缀）。
"""

from __future__ import annotations

from _common import REPO_ROOT, apply, fail, parse_args

LABEL_LINE = 'name="phone_control_service_label">'


def build_edits(label: str):
    edits = []
    files = sorted(REPO_ROOT.glob("android/app/src/main/res/values*/phone_control.xml"))
    if not files:
        fail("android/app/src/main/res 下没找到 phone_control.xml")
    for path in files:
        rel = str(path.relative_to(REPO_ROOT))
        hits = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if LABEL_LINE not in line or "Kelivo" not in line:
                continue
            hits += 1
            edits.append((rel, line, line.replace("Kelivo", label), 1))
        if hits != 1:
            fail(f"{rel}: label 行匹配到 {hits} 处（期望 1 处），上游可能改了写法")
    return edits


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(build_edits(args.label), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
