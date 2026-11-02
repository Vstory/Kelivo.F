#!/usr/bin/env python3
"""收尾校验：改写完之后不许再残留上游身份。

前面各步都按「期望原文命中几次」校验过，但它们只保证自己那段被改到；这里从结果反查，
漏改的可见身份（尤其不走 l10n 的那几处硬编码）不会报错，只会在界面上露出来。
"""

from __future__ import annotations

import re
import sys

from _common import REPO_ROOT, fail, parse_args

FILES = (
    "android/app/build.gradle.kts",
    "android/app/src/main/AndroidManifest.xml",
    "lib/main.dart",
    "lib/features/settings/pages/about_page.dart",
    "lib/desktop/setting/about_pane.dart",
    "lib/features/browser/pages/browser_page.dart",
    "lib/core/services/notification_service.dart",
    "lib/desktop/desktop_tray_controller.dart",
    "android/app/src/main/res/values/phone_control.xml",
    "android/app/src/main/res/values-zh-rCN/phone_control.xml",
    "android/app/src/main/res/values-zh-rTW/phone_control.xml",
)

FORBIDDEN = (
    'applicationId = "com.psyche.kelivo"',
    'android:label="Kelivo"',
    "title: 'Kelivo'",
    "versionCode = flutter.versionCode",
    "versionName = flutter.versionName",
    "                              'Kelivo',",
    "                'Kelivo',",
    "ticker: 'Kelivo',",
    "setToolTip('Kelivo')",
)

L10N_LANGS = ("en", "zh", "zh_Hans", "zh_Hant")
L10N_SKIP_KEYS = {
    "aboutPageQQGroupOne",
    "aboutPageQQGroupTwo",
    "aboutPageQQGroupThree",
}
ARB_ENTRY = re.compile(
    r'^\s*"(?P<key>[^"@][^"]*)"\s*:\s*"(?P<value>[^"]*)"\s*,?\s*$', re.MULTILINE
)


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    if args.dry_run:
        print("dry-run：跳过身份残留校验（此时尚未真正改写）")
        return 0
    hits: list[str] = []
    for rel in FILES:
        # 剔除 fork 自己写进去的名字，剩下的 Kelivo 才是漏改。
        text = (REPO_ROOT / rel).read_text(encoding="utf-8").replace(args.label, "")
        for lineno, line in enumerate(text.splitlines(), 1):
            for needle in FORBIDDEN:
                if needle in line:
                    hits.append(f"{rel}:{lineno}: {needle}")
    for lang in L10N_LANGS:
        rel = f"lib/l10n/app_{lang}.arb"
        for match in ARB_ENTRY.finditer((REPO_ROOT / rel).read_text(encoding="utf-8")):
            if match.group("key") in L10N_SKIP_KEYS:
                continue
            if "Kelivo" in match.group("value").replace(args.label, ""):
                hits.append(f"{rel}: {match.group('key')}")

    if hits:
        print("::error::改写后仍残留上游身份：", file=sys.stderr)
        for hit in hits:
            print(f"  - {hit}", file=sys.stderr)
        fail(f"共 {len(hits)} 处残留")
    print("身份残留校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
