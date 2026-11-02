#!/usr/bin/env python3
"""签名：显式打开 v3 签名方案。

AGP 8.12 落盘时默认只签 v2；同一把钥匙，不影响与上游原版并存装。
"""

from __future__ import annotations

from _common import apply, parse_args

GRADLE = "android/app/build.gradle.kts"


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(
        [
            (
                GRADLE,
                '        create("release") {\n            if (keystorePropertiesFile.exists()) {',
                '        create("release") {\n'
                "            enableV3Signing = true\n"
                '            if (keystorePropertiesFile.exists()) {',
                1,
            )
        ],
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
