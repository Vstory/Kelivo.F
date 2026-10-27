#!/usr/bin/env python3
"""CI 专用：把 runner 工作区改写成 fork 差异，仓库源码一行都不落库。

fork 包与上游原版要能同时安装、同时运行，包名与显示名必须错开。改写只作用于 CI 的
工作区 —— 包名一旦落进仓库，每次 rebase 上游都要撞冲突。逐项校验「期望的原文还在」，
上游改了写法就整体失败，不允许静默漏改。

除身份外，fork 想改的上游 UI 细节（目前是 MCP 自定义图标铺满头像）也走这里，
理由同上：源码保持与上游逐字一致，rebase 不用解冲突。

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
MCP_ICON = "lib/features/mcp/widgets/mcp_resolved_icon.dart"
MCP_AVATAR = "lib/features/mcp/widgets/mcp_server_avatar.dart"

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
        # 列表头像里用户自己填的 MCP 图标（URL / 文件）被 0.75 缩进，圆形 logo 四周留出一圈
        # 容器底色。内置 asset 图标与 emoji 保留缩进 —— 它们自带留白，铺满反而拥挤。
        (
            MCP_ICON,
            "                  width: widget.size * (widget.inset ? .75 : 1),\n"
            "                  height: widget.size * (widget.inset ? .75 : 1),",
            "                  width: widget.size,\n                  height: widget.size,",
            1,
        ),
        (
            MCP_ICON,
            "                width: widget.size * (widget.inset ? .65 : 1),\n"
            "                height: widget.size * (widget.inset ? .65 : 1),\n"
            "                theme: SvgTheme(",
            "                width: widget.size,\n"
            "                height: widget.size,\n"
            "                theme: SvgTheme(",
            1,
        ),
        # 铺满后图片自带的 0.2·size 圆角小于容器圆角（36dp tile 配 10dp），满色图四角会探出
        # 容器边缘；让容器自己裁一刀，形状回到容器圆角。
        (
            MCP_AVATAR,
            "            alignment: Alignment.center,\n            decoration: showBackground",
            "            alignment: Alignment.center,\n"
            "            clipBehavior: showBackground ? Clip.antiAlias : Clip.none,\n"
            "            decoration: showBackground",
            1,
        ),
    ]


FORBIDDEN = [
    'applicationId = "com.psyche.kelivo"',
    'android:label="Kelivo"',
    "title: 'Kelivo'",
    "versionCode = flutter.versionCode",
    "versionName = flutter.versionName",
    # asset 图标用的 .65 会留下，只有自定义图标这条 .75 必须消失。
    "widget.size * (widget.inset ? .75 : 1)",
]


def scan_forbidden() -> list[str]:
    hits: list[str] = []
    for rel in (GRADLE, MANIFEST, MAIN_DART, MCP_ICON):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for needle in FORBIDDEN:
                if needle in line:
                    hits.append(f"{rel}:{lineno}: {needle}")
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

    edits = build_edits(args.app_id, args.label)
    problems: list[str] = []
    for rel, old, new, want in edits:
        path = REPO_ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: 文件不存在")
            continue
        got = path.read_text(encoding="utf-8").count(old)
        if got != want:
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
