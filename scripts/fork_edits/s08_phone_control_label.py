#!/usr/bin/env python3
"""无障碍服务名：三份 phone_control.xml 的 label 跟着改名。

这个名字显示在系统设置里，只改 arb 文案会让提示指向系统里不存在的名字。
授权按组件名绑定，改 label 不影响已开启的服务。
"""

from __future__ import annotations

from _common import apply, parse_args


def build_edits(label: str):
    return [
        (
            "android/app/src/main/res/values/phone_control.xml",
            '<string name="phone_control_service_label">Kelivo phone control</string>',
            f'<string name="phone_control_service_label">{label} phone control</string>',
            1,
        ),
        (
            "android/app/src/main/res/values-zh-rCN/phone_control.xml",
            '<string name="phone_control_service_label">Kelivo 手机控制</string>',
            f'<string name="phone_control_service_label">{label} 手机控制</string>',
            1,
        ),
        (
            "android/app/src/main/res/values-zh-rTW/phone_control.xml",
            '<string name="phone_control_service_label">Kelivo 手機控制</string>',
            f'<string name="phone_control_service_label">{label} 手機控制</string>',
            1,
        ),
    ]


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(build_edits(args.label), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
