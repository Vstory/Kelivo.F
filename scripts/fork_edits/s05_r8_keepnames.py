#!/usr/bin/env python3
"""R8：保留 kotlin.coroutines.Continuation 的类名。

release 的 R8 在 Flutter 里恒开（--no-shrink 已是空开关），它会改 JNI 签名里的类名；
Pigeon JNI 按原签名查方法，Continuation 被改名就 NoSuchMethodError —— 启动即崩。
"""

from __future__ import annotations

from _common import apply, parse_args

PROGUARD = "android/app/proguard-rules.pro"


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(
        [
            (
                PROGUARD,
                "-dontwarn com.tom_roush.pdfbox.filter.JPXFilter",
                "-dontwarn com.tom_roush.pdfbox.filter.JPXFilter\n"
                "-keepnames class kotlin.coroutines.Continuation",
                1,
            )
        ],
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
