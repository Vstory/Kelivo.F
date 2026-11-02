#!/usr/bin/env python3
"""关于页加一条指回 fork 仓库的入口。

上游关于页只有一条指向 Chevey339/kelivo 的 GitHub 行；构建包再加一条指回 fork 仓库。
移动端与桌面端各一套行组件（_iosNavRow / _DeskNavRow），两边都要插。
"""

from __future__ import annotations

from _common import apply, parse_args

ABOUT_PAGE = "lib/features/settings/pages/about_page.dart"
ABOUT_PANE = "lib/desktop/setting/about_pane.dart"
FORK_REPO_URL = "https://github.com/Vstory/Kelivo.F"


def build_edits(label: str):
    return [
        # 锚点连带下一行的 aboutPageSystem 一起匹配，单看 _iosDivider 会在同文件里命中多处。
        (
            ABOUT_PAGE,
            "              _iosDivider(context),\n"
            "              _iosNavRow(\n"
            "                context,\n"
            "                icon: Lucide.Phone,\n"
            "                label: l10n.aboutPageSystem,",
            "              _iosNavRow(\n"
            "                context,\n"
            "                icon: Lucide.GitFork,\n"
            f"                label: '{label}',\n"
            f"                onTap: () => _openUrl('{FORK_REPO_URL}'),\n"
            "              ),\n"
            "              _iosDivider(context),\n"
            "              _iosNavRow(\n"
            "                context,\n"
            "                icon: Lucide.Phone,\n"
            "                label: l10n.aboutPageSystem,",
            1,
        ),
        (
            ABOUT_PANE,
            "                  const _DeskRowDivider(),\n"
            "                  _DeskInfoRow(\n"
            "                    icon: lucide.Lucide.Phone,\n"
            "                    label: l10n.aboutPageSystem,",
            "                  _DeskNavRow(\n"
            "                    icon: lucide.Lucide.GitFork,\n"
            f"                    label: '{label}',\n"
            "                    onTap: () =>\n"
            f"                        _openUrl('{FORK_REPO_URL}'),\n"
            "                  ),\n"
            "                  const _DeskRowDivider(),\n"
            "                  _DeskInfoRow(\n"
            "                    icon: lucide.Lucide.Phone,\n"
            "                    label: l10n.aboutPageSystem,",
            1,
        ),
    ]


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(build_edits(args.label), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
