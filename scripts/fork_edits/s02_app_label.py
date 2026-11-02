#!/usr/bin/env python3
"""显示名：manifest label、MaterialApp.title、几处硬编码字面量、通知 ticker 与托盘 tooltip。

MaterialApp.title 经 Title widget 推成最近任务标题，与 application label 互不影响；
剩下的硬编码处（关于页顶部、浏览器起始页、通知栏滚动文案、托盘 tooltip）都不走 l10n，
漏改不会报错，只在界面上露出上游名。
"""

from __future__ import annotations

from _common import apply, parse_args

MANIFEST = "android/app/src/main/AndroidManifest.xml"
MAIN_DART = "lib/main.dart"
ABOUT_PAGE = "lib/features/settings/pages/about_page.dart"
BROWSER_PAGE = "lib/features/browser/pages/browser_page.dart"
NOTIFICATION_SERVICE = "lib/core/services/notification_service.dart"
TRAY_CONTROLLER = "lib/desktop/desktop_tray_controller.dart"


def build_edits(label: str):
    return [
        (MANIFEST, 'android:label="Kelivo"', f'android:label="{label}"', 1),
        (MAIN_DART, "title: 'Kelivo'", f"title: '{label}'", 6),
        # 移动端关于页顶部的应用名是硬编码字面量（桌面端用的是 l10n.aboutPageAppName）
        # ⇒ 只改 l10n 时手机上的「关于」仍顶着上游名字。连带 ValueKey 一起匹配，
        # 单改那一行字面量容易在别的 'Kelivo' 上误命中。
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
        (NOTIFICATION_SERVICE, "ticker: 'Kelivo',", f"ticker: '{label}',", 1),
        (
            TRAY_CONTROLLER,
            "await trayManager.setToolTip('Kelivo');",
            f"await trayManager.setToolTip('{label}');",
            1,
        ),
    ]


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(build_edits(args.label), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
