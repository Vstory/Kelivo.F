#!/usr/bin/env python3
"""关于页版本行：彩蛋入口由「连点 7 次」改为「长按」。

连点阈值散落成两个字段 + 一个方法（计数、2 秒窗口、阈值常量），改成单次长按后这些
状态一并删掉，否则 dart analyze 的 unused_field / unused_element 会在 --fatal-infos 下报错。
长按手势落在行组件上：_TactileRow 之前只认 onTap，这里补 onLongPress 并让按下高亮也认它。
"""

from __future__ import annotations

from _common import REPO_ROOT, apply, fail, parse_args

ABOUT_PAGE = "lib/features/settings/pages/about_page.dart"

_STATE_FIELDS_OLD = """\
  int _versionTapCount = 0;
  DateTime? _lastVersionTap;
"""

_TAP_HANDLER_OLD = """\
  void _onVersionTap() {
    final now = DateTime.now();
    // Reset the counter if taps are spaced too far apart
    if (_lastVersionTap == null ||
        now.difference(_lastVersionTap!) > const Duration(seconds: 2)) {
      _versionTapCount = 0;
    }
    _lastVersionTap = now;
    _versionTapCount++;

    const threshold = 7;
    if (_versionTapCount < threshold) return;

    _versionTapCount = 0; // reset after unlock
    _showEasterEgg();
  }

"""

_ROW_COMMENT_OLD = "              // Version (tap 7x to unlock easter egg) — logic unchanged\n"
_ROW_COMMENT_NEW = "              // Version (long-press to unlock easter egg)\n"

_ROW_BINDING_OLD = "                onTap: _onVersionTap,\n"
_ROW_BINDING_NEW = "                onLongPress: _showEasterEgg,\n"

_TACTILE_FIELDS_OLD = """\
  const _TactileRow({
    required this.builder,
    this.onTap,
    this.pressedScale = 1.00,
    this.haptics = false,
  });
  final Widget Function(bool pressed) builder;
  final VoidCallback? onTap;
  final double pressedScale;
  final bool haptics;
"""

_TACTILE_FIELDS_NEW = """\
  const _TactileRow({
    required this.builder,
    this.onTap,
    this.onLongPress,
    this.pressedScale = 1.00,
    this.haptics = false,
  });
  final Widget Function(bool pressed) builder;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final double pressedScale;
  final bool haptics;
"""

_TACTILE_GESTURE_OLD = """\
    final child = widget.builder(_pressed);
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: widget.onTap == null ? null : (_) => _setPressed(true),
      onTapUp: widget.onTap == null ? null : (_) => _setPressed(false),
      onTapCancel: widget.onTap == null ? null : () => _setPressed(false),
      onTap: widget.onTap == null
          ? null
          : () {
              if (widget.haptics &&
                  context.read<SettingsProvider>().hapticsOnListItemTap) {
                Haptics.soft();
              }
              widget.onTap!.call();
            },
"""

_TACTILE_GESTURE_NEW = """\
    final child = widget.builder(_pressed);
    final pressable = widget.onTap != null || widget.onLongPress != null;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: pressable ? (_) => _setPressed(true) : null,
      onTapUp: pressable ? (_) => _setPressed(false) : null,
      onTapCancel: pressable ? () => _setPressed(false) : null,
      onTap: widget.onTap == null
          ? null
          : () {
              if (widget.haptics &&
                  context.read<SettingsProvider>().hapticsOnListItemTap) {
                Haptics.soft();
              }
              widget.onTap!.call();
            },
      onLongPress: widget.onLongPress == null
          ? null
          : () {
              _setPressed(false);
              widget.onLongPress!.call();
            },
"""

_NAV_ROW_OLD = """\
Widget _iosNavRow(
  BuildContext context, {
  required IconData icon,
  required String label,
  VoidCallback? onTap,
  String? detailText,
  Widget Function(BuildContext ctx)? detailBuilder,
}) {
  final cs = Theme.of(context).colorScheme;
  final interactive = onTap != null;
  return _TactileRow(
    onTap: onTap,
    pressedScale: 1.00, // list rows: color shift only, no scale
"""

_NAV_ROW_NEW = """\
Widget _iosNavRow(
  BuildContext context, {
  required IconData icon,
  required String label,
  VoidCallback? onTap,
  VoidCallback? onLongPress,
  String? detailText,
  Widget Function(BuildContext ctx)? detailBuilder,
}) {
  final cs = Theme.of(context).colorScheme;
  final interactive = onTap != null || onLongPress != null;
  return _TactileRow(
    onTap: onTap,
    onLongPress: onLongPress,
    pressedScale: 1.00, // list rows: color shift only, no scale
"""


def build_edits():
    return [
        (ABOUT_PAGE, _STATE_FIELDS_OLD, "", 1),
        (ABOUT_PAGE, _TAP_HANDLER_OLD, "", 1),
        (ABOUT_PAGE, _ROW_COMMENT_OLD, _ROW_COMMENT_NEW, 1),
        (ABOUT_PAGE, _ROW_BINDING_OLD, _ROW_BINDING_NEW, 1),
        (ABOUT_PAGE, _TACTILE_FIELDS_OLD, _TACTILE_FIELDS_NEW, 1),
        (ABOUT_PAGE, _TACTILE_GESTURE_OLD, _TACTILE_GESTURE_NEW, 1),
        (ABOUT_PAGE, _NAV_ROW_OLD, _NAV_ROW_NEW, 1),
    ]


def verify() -> None:
    text = (REPO_ROOT / ABOUT_PAGE).read_text(encoding="utf-8")
    for needle in ("_versionTapCount", "_lastVersionTap", "_onVersionTap"):
        if needle in text:
            fail(f"{ABOUT_PAGE} 改写后仍残留连点逻辑：{needle}")
    if "onLongPress: _showEasterEgg" not in text:
        fail(f"{ABOUT_PAGE} 未挂上长按入口")


def main() -> int:
    args = parse_args(__doc__.splitlines()[0])
    apply(build_edits(), dry_run=args.dry_run)
    if not args.dry_run:
        verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
