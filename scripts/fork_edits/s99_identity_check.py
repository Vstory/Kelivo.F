#!/usr/bin/env python3
# SCRIPT_VERSION=1.1.1    # 脚本版本(无模板上游, 独立维护; 内容变更 +1)
"""收尾校验：改写完之后不许再残留上游身份。

前面各步都按「期望原文命中几次」校验过，但它们只保证自己那段被改到；这里从结果反查，
漏改的可见身份（尤其不走 l10n 的那几处硬编码）不会报错，只会在界面上露出来。
l10n 与 phone_control 按文件 glob 反查 —— 上游加语言（2026-11 加 ru / ko / tr）时，
写死清单的检查会跟着一起漏。
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

L10N_SKIP_KEYS = {
    "aboutPageQQGroupOne",
    "aboutPageQQGroupTwo",
    "aboutPageQQGroupThree",
}
# 值里可能出现 \" 转义引号（tr 的备份文案就是），只写 [^"]* 会把整条漏掉。
ARB_ENTRY = re.compile(
    r'^\s*"(?P<key>[^"@][^"]*)"\s*:\s*"(?P<value>(?:[^"\\]|\\.)*)"\s*,?\s*$',
    re.MULTILINE,
)
LABEL_LINE = 'name="phone_control_service_label">'


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
    for arb in sorted((REPO_ROOT / "lib/l10n").glob("app_*.arb")):
        rel = str(arb.relative_to(REPO_ROOT))
        for match in ARB_ENTRY.finditer(arb.read_text(encoding="utf-8")):
            if match.group("key") in L10N_SKIP_KEYS:
                continue
            if "Kelivo" in match.group("value").replace(args.label, ""):
                hits.append(f"{rel}: {match.group('key')}")
    for xml in sorted(REPO_ROOT.glob("android/app/src/main/res/values*/phone_control.xml")):
        rel = str(xml.relative_to(REPO_ROOT))
        for lineno, line in enumerate(xml.read_text(encoding="utf-8").splitlines(), 1):
            if LABEL_LINE in line and "Kelivo" in line.replace(args.label, ""):
                hits.append(f"{rel}:{lineno}: 无障碍服务名未改名")
    # 生成物也要查：arb 改对了但生成物漏改时界面露的是旧名。key 名（aboutPageKelivoSearch*）
    # 与 QQ 群文案不算残留，生成器写的 /// 文档注释里带原文也不影响运行。
    for dart in sorted((REPO_ROOT / "lib/l10n").glob("app_localizations_*.dart")):
        rel = str(dart.relative_to(REPO_ROOT))
        for lineno, line in enumerate(dart.read_text(encoding="utf-8").splitlines(), 1):
            if "Kelivo" not in line.replace(args.label, ""):
                continue
            if "aboutPageKelivoSearch" in line or "aboutPageQQGroup" in line:
                continue
            if line.lstrip().startswith("///"):
                continue
            hits.append(f"{rel}:{lineno}: 生成物文案未改名")

    if hits:
        print("::error::改写后仍残留上游身份：", file=sys.stderr)
        for hit in hits:
            print(f"  - {hit}", file=sys.stderr)
        fail(f"共 {len(hits)} 处残留")
    print("身份残留校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
