#!/usr/bin/env python3
"""CI 专用：把 runner 工作区改写成 fork 身份，仓库源码一行都不落库。

fork 包与上游原版要能同时安装、同时运行，包名与显示名必须错开。改写只作用于 CI 的
工作区 —— 包名一旦落进仓库，每次 rebase 上游都要撞冲突。逐项校验「期望的原文还在」，
上游改了写法就整体失败，不允许静默漏改。

用法：
    python3 scripts/ci-fork-identity.py --app-id com.psyche.kelivo.fork --label Kelivo.F
    python3 scripts/ci-fork-identity.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GRADLE = "android/app/build.gradle.kts"
MANIFEST = "android/app/src/main/AndroidManifest.xml"
PROGUARD = "android/app/proguard-rules.pro"
MAIN_DART = "lib/main.dart"
ABOUT_PAGE = "lib/features/settings/pages/about_page.dart"
BROWSER_PAGE = "lib/features/browser/pages/browser_page.dart"
NOTIFICATION_SERVICE = "lib/core/services/notification_service.dart"
TRAY_CONTROLLER = "lib/desktop/desktop_tray_controller.dart"

DEFAULT_APP_ID = "com.psyche.kelivo.fork"
DEFAULT_LABEL = "Kelivo.F"


def build_edits(app_id: str, label: str) -> list[tuple[str, str, str, int]]:
    return [
        (GRADLE, 'applicationId = "com.psyche.kelivo"', f'applicationId = "{app_id}"', 1),
        (MANIFEST, 'android:label="Kelivo"', f'android:label="{label}"', 1),
        # 最近任务的标题来自 MaterialApp.title（经 Title widget 推成 TaskDescription），
        # 与 manifest 的 application label 互不影响，两处都要改才不会再顶着上游名字。
        (MAIN_DART, "title: 'Kelivo'", f"title: '{label}'", 6),
        # Flutter 的 --build-name 只收数字点分版本，塞不进 +ci-<变体>.<短号>；改成从环境变量
        # 取 versionName/versionCode，CI 才能照 Mishka 的命名规则写构建元数据。
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
        # AGP 8.12 落盘时默认只签 v2，v3 要显式开；同一把钥匙，不影响与上游原版并存装。
        (
            GRADLE,
            '        create("release") {\n            if (keystorePropertiesFile.exists()) {',
            '        create("release") {\n'
            "            enableV3Signing = true\n"
            '            if (keystorePropertiesFile.exists()) {',
            1,
        ),
        # release 的 R8 在 Flutter 里恒开（--no-shrink 已是空开关），它会改 JNI 签名里的类名；
        # Pigeon JNI 按原签名查方法，Continuation 被改名就 NoSuchMethodError —— 启动即崩。
        (
            PROGUARD,
            "-dontwarn com.tom_roush.pdfbox.filter.JPXFilter",
            "-dontwarn com.tom_roush.pdfbox.filter.JPXFilter\n"
            "-keepnames class kotlin.coroutines.Continuation",
            1,
        ),
        # 只编 arm64-v8a：三个 ABI 会白编两份用不上的原生库。
        (
            GRADLE,
            'abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86_64")',
            'abiFilters += listOf("arm64-v8a")',
            1,
        ),
        # --target-platform 只约束 Flutter 引擎，jniLibs 里三份 proot 仍会被打进包；
        # 不排除它们，APK 的 native-code 就不是单 ABI。
        (
            GRADLE,
            "        jniLibs {\n            useLegacyPackaging = true\n        }",
            "        jniLibs {\n            useLegacyPackaging = true\n"
            '            exclude("lib/armeabi-v7a/**")\n'
            '            exclude("lib/x86_64/**")\n'
            "        }",
            1,
        ),
        # 无障碍服务名显示在系统设置里，只改 arb 文案会让提示指向系统里不存在的名字。
        # 授权按组件名绑定，改 label 不影响已开启的服务。
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
        # 移动端关于页顶部的应用名是**硬编码字面量**，不走 arb（桌面端 about_pane.dart 用的是
        #   l10n.aboutPageAppName）⇒ 只改 l10n 时手机上的「关于」仍顶着上游名字，两端口径不一。
        #   连带 ValueKey 一起匹配：单改那一行字面量容易在别的 'Kelivo' 上误命中。
        (
            ABOUT_PAGE,
            "                              'Kelivo',\n"
            "                              key: const ValueKey('about-page-app-name'),",
            f"                              '{label}',\n"
            f"                              key: const ValueKey('about-page-app-name'),",
            1,
        ),
        # 浏览器起始页那个 38px 大标题同样是写死的。
        (
            BROWSER_PAGE,
            "              Text(\n"
            "                'Kelivo',\n"
            "                style: TextStyle(\n"
            "                  fontSize: 38,",
            f"              Text(\n"
            f"                '{label}',\n"
            f"                style: TextStyle(\n"
            f"                  fontSize: 38,",
            1,
        ),
        # 通知 ticker（状态栏滚动那一行）与桌面托盘 tooltip：都没有 l10n，属可见身份。
        (
            NOTIFICATION_SERVICE,
            "ticker: 'Kelivo',",
            f"ticker: '{label}',",
            1,
        ),
        (
            TRAY_CONTROLLER,
            "await trayManager.setToolTip('Kelivo');",
            f"await trayManager.setToolTip('{label}');",
            1,
        ),
    ]


FORBIDDEN = [
    'applicationId = "com.psyche.kelivo"',
    'android:label="Kelivo"',
    "title: 'Kelivo'",
    "versionCode = flutter.versionCode",
    "versionName = flutter.versionName",
    # 下面四条对应「不走 l10n 的可见身份」：漏改不会报错，只会在界面上露出上游名。
    "                              'Kelivo',",
    "                'Kelivo',",
    "ticker: 'Kelivo',",
    "setToolTip('Kelivo')",
]

L10N_LANGS = ("en", "zh", "zh_Hans", "zh_Hant")
# QQ 群指向的是上游社区，fork 没有自己的群，跟着改名就指错了。
L10N_SKIP_KEYS = {
    "aboutPageQQGroupOne",
    "aboutPageQQGroupTwo",
    "aboutPageQQGroupThree",
}
ARB_ENTRY = re.compile(
    r'^\s*"(?P<key>[^"@][^"]*)"\s*:\s*"(?P<value>[^"]*)"\s*,?\s*$', re.MULTILINE
)


def build_l10n_edits(label: str) -> list[tuple[str, str, str, int]]:
    """通知栏标题、关于页和全部报错文案的名字都来自 arb，只改 manifest 与 MaterialApp.title 盖不住。"""
    edits: list[tuple[str, str, str, int]] = []
    keys: set[str] = set()
    for lang in L10N_LANGS:
        arb_rel = f"lib/l10n/app_{lang}.arb"
        renamed = 0
        for match in ARB_ENTRY.finditer((REPO_ROOT / arb_rel).read_text(encoding="utf-8")):
            key, value = match.group("key"), match.group("value")
            if key in L10N_SKIP_KEYS or "Kelivo" not in value:
                continue
            renamed += 1
            keys.add(key)
            edits.append(
                (
                    arb_rel,
                    f'"{key}": "{value}"',
                    f'"{key}": "{value.replace("Kelivo", label)}"',
                    1,
                )
            )
        if renamed < 20:
            raise SystemExit(
                f"::error::{arb_rel} 只匹配到 {renamed} 处含 Kelivo 的文案，"
                f"上游可能改了写法（期望 50 处以上）"
            )

    # 生成物 app_localizations_*.dart 是提交在仓库里的实体文件，gen-l10n 在 build 时不
    # 保证重跑，不改这里运行时仍是旧名字。zh 的三个类（zh / zh_Hans / zh_Hant）同在一个
    # 文件里，同一段文案会出现多次，所以按内容去重、只要求至少命中一处。
    for dart_rel in ("lib/l10n/app_localizations_en.dart", "lib/l10n/app_localizations_zh.dart"):
        dart_text = (REPO_ROOT / dart_rel).read_text(encoding="utf-8")
        seen: set[str] = set()
        for key in sorted(keys):
            # 带占位符的 key 生成的是方法而非 getter，按「声明到第一个分号」切块两种都覆盖。
            for declared in re.finditer(rf"\bString (?:get )?{re.escape(key)}\b", dart_text):
                start = declared.start()
                end = dart_text.index(";", start)
                block = dart_text[start:end]
                if "Kelivo" not in block or block in seen:
                    continue
                seen.add(block)
                edits.append((dart_rel, block, block.replace("Kelivo", label), -1))
    return edits


def scan_forbidden() -> list[str]:
    hits: list[str] = []
    for rel in (
        GRADLE,
        MANIFEST,
        MAIN_DART,
        ABOUT_PAGE,
        BROWSER_PAGE,
        NOTIFICATION_SERVICE,
        TRAY_CONTROLLER,
    ):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for needle in FORBIDDEN:
                if needle in line:
                    hits.append(f"{rel}:{lineno}: {needle}")
    for lang in L10N_LANGS:
        rel = f"lib/l10n/app_{lang}.arb"
        for match in ARB_ENTRY.finditer((REPO_ROOT / rel).read_text(encoding="utf-8")):
            if match.group("key") in L10N_SKIP_KEYS:
                continue
            if re.search(r"Kelivo(?!\.)", match.group("value")):
                hits.append(f"{rel}: {match.group('key')}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.label):
        print(
            f"::error::--label 只允许 A-Za-z0-9._-（它进 APK 文件名与下载 URL）：{args.label!r}",
            file=sys.stderr,
        )
        return 1

    edits = build_edits(args.app_id, args.label) + build_l10n_edits(args.label)
    problems: list[str] = []
    for rel, old, new, want in edits:
        path = REPO_ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: 文件不存在")
            continue
        got = path.read_text(encoding="utf-8").count(old)
        if want < 0:
            # -1：同一段文案在 zh 文件里会出现多次，判据只要求命中过。
            if got < 1:
                problems.append(f"{rel}: 未命中: {old[:70]}")
        elif got != want:
            problems.append(f"{rel}: 期望 {want} 处、实际 {got} 处: {old}")

    if problems:
        print("::error::fork 身份改写的前置校验未通过：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    if args.dry_run:
        for rel, old, new, _ in edits:
            print(f"[dry-run] {rel}\n    - {old}\n    + {new}")
        return 0

    for rel, old, new, _ in edits:
        path = REPO_ROOT / rel
        path.write_text(
            path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
        )
        print(f"  {rel}: 已改写")

    hits = scan_forbidden()
    if hits:
        print("::error::改写后仍残留上游身份：", file=sys.stderr)
        for h in hits:
            print(f"  - {h}", file=sys.stderr)
        return 1

    print(f"已改写为 fork 身份：appId={args.app_id} label={args.label}（仅工作区，不入库）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
