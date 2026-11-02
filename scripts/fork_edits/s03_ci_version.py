#!/usr/bin/env python3
"""版本号来源：versionCode/versionName 改从 CI 环境变量取。

Flutter 的 --build-name 只收数字点分版本，塞不进 +ci-<变体>.<短号>；改成读
CI_VERSION_CODE / CI_VERSION_NAME 后才写得出自定义构建元数据，缺省仍回落 flutter 的值。
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
                "        versionCode = flutter.versionCode",
                '        versionCode = System.getenv("CI_VERSION_CODE")?.toIntOrNull() ?: flutter.versionCode',
                1,
            ),
            (
                GRADLE,
                "        versionName = flutter.versionName",
                '        versionName = System.getenv("CI_VERSION_NAME") ?: flutter.versionName',
                1,
            ),
        ],
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
