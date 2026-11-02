#!/usr/bin/env python3
"""单 ABI：只保留 arm64-v8a，并排除另外两份原生库。

--target-platform 只约束 Flutter 引擎，jniLibs 里的 proot 仍会被打进包；
不排除它们，APK 的 native-code 就不是单 ABI。
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
                'abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86_64")',
                'abiFilters += listOf("arm64-v8a")',
                1,
            ),
            (
                GRADLE,
                "        jniLibs {\n            useLegacyPackaging = true\n        }",
                "        jniLibs {\n            useLegacyPackaging = true\n"
                '            exclude("lib/armeabi-v7a/**")\n'
                '            exclude("lib/x86_64/**")\n'
                "        }",
                1,
            ),
        ],
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
