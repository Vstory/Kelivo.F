#!/usr/bin/env python3
"""l10n 文案：通知栏标题、关于页名字与全部报错文案都来自 arb，改这一层才盖得住。

生成物 app_localizations_*.dart 是提交在仓库里的实体文件，gen-l10n 在 build 时不保证
重跑，所以 arb 与生成物两处都要改，否则运行时仍是旧名字。
"""

from __future__ import annotations

import re

from _common import REPO_ROOT, apply, fail, parse_args

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


def build_edits(label: str):
    edits = []
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
            fail(
                f"{arb_rel} 只匹配到 {renamed} 处含 Kelivo 的文案，"
                f"上游可能改了写法（期望 50 处以上）"
            )

    # zh 的三个类（zh / zh_Hans / zh_Hant）同在一个文件里，同一段文案会出现多次，
    # 所以按内容去重、只要求至少命中一处。
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


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(build_edits(args.label), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
