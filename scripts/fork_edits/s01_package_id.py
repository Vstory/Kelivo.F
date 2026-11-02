#!/usr/bin/env python3
"""包名：applicationId 换成 fork 的，与上游原版并存安装。

⚠️ 只动 applicationId，不动 namespace —— R 类与 Manifest 的 .MainActivity 都跟 namespace 走。
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
                'applicationId = "com.psyche.kelivo"',
                f'applicationId = "{args.app_id}"',
                1,
            )
        ],
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
