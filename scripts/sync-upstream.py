#!/usr/bin/env python3
# SCRIPT_VERSION=1.0.2    # 脚本版本(无模板上游, 独立维护; 内容变更 +1)
"""同步上游：fetch → 合并 → fork 锚点门禁 → 经统一操作器预演并推送 → 打印新 CI 链接。

裸跑即预演（只看计划和上游新增，不动仓库、不推远端）；真跑要显式 --yes。

推送一律交知识库统一操作器 `100_System/tools/github push`：它自带脏工作区 / 版本门禁 /
密钥扫描 / 远端比对，且预演与真跑走同一套前置检查 —— 本脚本不自己碰凭据，
也不复制那套检查（重复实现会让两边判据漂移）。

用法：
    python3 scripts/sync-upstream.py            # 预演
    python3 scripts/sync-upstream.py --yes      # 合并并推送
    python3 scripts/sync-upstream.py --yes --no-push
    python3 scripts/sync-upstream.py --yes --skip-anchors   # 上游只改文档时用

退出码：0 正常 / 2 工作区不干净或合并冲突 / 3 锚点门禁失败 / 4 找不到统一操作器 / 5 推送失败
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANCHOR_SCRIPT = REPO_ROOT / "scripts" / "ci-fork-identity.py"

# 操作器在知识库里，Kelivo.F 是独立仓库：找不到就报错并给手动命令，绝不退化成自己拼凭据
PKB_ROOT = Path(os.environ.get("PKB_ROOT", "/workspace/Personal-Knowledge-Base"))
GITHUB_TOOL = PKB_ROOT / "100_System" / "tools" / "github"


def log(message: str) -> None:
    print(message, file=sys.stderr)


def run(cmd: list[str], cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        text=True,
        capture_output=True,
        check=check,
    )


def git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return run(["git", *args], check=check)


def out(result: subprocess.CompletedProcess) -> str:
    return (result.stdout or "").strip()


def origin_slug() -> str:
    url = out(git("remote", "get-url", "origin"))
    match = re.search(r"[/:]([^/:]+/[^/]+?)(?:\.git)?$", url)
    if not match:
        log(f"::error::无法从 origin 解析 owner/name：{url!r}")
        raise SystemExit(2)
    return match.group(1)


def tool_entry() -> Path | None:
    # 操作器是包目录（python3 100_System/tools/github 走 __main__.py），也可能被装成单文件
    if GITHUB_TOOL.is_file():
        return GITHUB_TOOL
    if GITHUB_TOOL.is_dir() and (GITHUB_TOOL / "__main__.py").is_file():
        return GITHUB_TOOL
    return None


def require_tool() -> str:
    entry = tool_entry()
    if entry is None:
        log(f"::error::找不到统一操作器 {GITHUB_TOOL}")
        log("设 PKB_ROOT 指向知识库根，或手动推送：cd 到仓库后 `github push -C . -R <owner/name> --branch main`")
        raise SystemExit(4)
    return str(entry)


def tool(*args: str) -> subprocess.CompletedProcess:
    return run([sys.executable, require_tool(), *args])


def workspace_dirty() -> bool:
    return bool(out(git("status", "--porcelain")))


def report_plan(upstream_ref: str, branch: str) -> int:
    count = int(out(git("rev-list", "--count", f"HEAD..{upstream_ref}")) or 0)
    # 与上游比出的「领先」数含历轮合并提交，对判断该推什么没意义；推送看的是相对 origin
    origin_ref = f"origin/{branch}"
    has_origin = git("rev-parse", "--verify", "--quiet", origin_ref).returncode == 0
    ahead = int(out(git("rev-list", "--count", f"{origin_ref}..HEAD")) or 0) if has_origin else -1
    ahead_text = f"{ahead} 个待推送" if ahead >= 0 else "远端 ref 未知"
    if count == 0:
        log(f"上游 {upstream_ref} 无新提交；本地相对 {origin_ref}: {ahead_text}")
        return 0
    log(f"上游 {upstream_ref} 有 {count} 个新提交（本地相对 {origin_ref}: {ahead_text}）：")
    log(out(git("log", "--oneline", "--no-decorate", f"HEAD..{upstream_ref}")))
    log(f"规模：{out(git('diff', '--shortstat', f'HEAD...{upstream_ref}'))}")
    return count


def merge(upstream_ref: str) -> None:
    log(f"合并 {upstream_ref} …")
    result = git("merge", upstream_ref, "--no-edit")
    if result.returncode == 0:
        log(f"合并完成：{out(git('log', '-1', '--format=%h %s'))}")
        return
    conflicts = out(git("diff", "--name-only", "--diff-filter=U"))
    log("::error::合并失败，未自动 abort（改动还在工作区，可手工处理后再跑）")
    if conflicts:
        log("冲突文件：\n" + conflicts)
    else:
        log(result.stderr.strip() or "（无冲突文件，非冲突导致的失败）")
    raise SystemExit(2)


def check_anchors(skip: bool) -> None:
    if skip:
        log("跳过 fork 锚点门禁（--skip-anchors）")
        return
    log("fork 锚点门禁（ci-fork-identity.py --dry-run）…")
    result = run([sys.executable, str(ANCHOR_SCRIPT), "--dry-run"])
    if result.returncode != 0:
        log("::error::锚点门禁失败 —— 上游改了被锚定的写法，先去同步 scripts/fork_edits/")
        log((result.stderr or result.stdout)[-3000:])
        raise SystemExit(3)
    log("锚点门禁通过")


def push(slug: str, branch: str) -> None:
    log("推送预演 …")
    preview = tool("push", "-C", str(REPO_ROOT), "-R", slug, "--branch", branch, "--dry-run")
    text = f"{preview.stdout}{preview.stderr}"
    if preview.returncode != 0:
        log("::error::推送预演未通过：\n" + text.strip())
        raise SystemExit(5)
    log(text.strip())
    if "无需推送" in text:
        return
    log("真推 …")
    result = tool("push", "-C", str(REPO_ROOT), "-R", slug, "--branch", branch, "--yes")
    if result.returncode != 0:
        log("::error::推送失败：\n" + f"{result.stdout}{result.stderr}".strip())
        raise SystemExit(5)
    log(f"{result.stdout}{result.stderr}".strip())


def report_ci(slug: str) -> None:
    result = tool("run", "list", "-R", slug, "--limit", "3")
    print(f"{result.stdout}{result.stderr}".strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="upstream", help="上游 remote 名（缺省 upstream）")
    parser.add_argument("--upstream-branch", default="master", help="上游分支（缺省 master）")
    parser.add_argument("--branch", default=None, help="要推送的本地分支（缺省当前分支）")
    parser.add_argument("--yes", action="store_true", help="真跑：合并并推送（缺省只预演）")
    parser.add_argument("--no-push", action="store_true", help="只合并，不推送")
    parser.add_argument("--skip-anchors", action="store_true", help="跳过 fork 锚点门禁")
    args = parser.parse_args()

    if workspace_dirty():
        log("::error::工作区不干净，先提交或 stash：\n" + out(git("status", "--short")))
        return 2

    branch = args.branch or out(git("rev-parse", "--abbrev-ref", "HEAD"))
    upstream_ref = f"{args.remote}/{args.upstream_branch}"
    slug = origin_slug()

    log(f"分支 {branch} ← {upstream_ref}（远端 {slug}）")
    fetched = git("fetch", args.remote, args.upstream_branch, "--quiet")
    if fetched.returncode != 0:
        log("::error::fetch 失败：\n" + (fetched.stderr or "").strip())
        return 2

    if git("fetch", "origin", branch, "--quiet").returncode != 0:
        log(f"提示：fetch origin 失败，待推送数按现有 origin/{branch} ref 估算")

    pending = report_plan(upstream_ref, branch)

    if not args.yes:
        print(f"预演：{pending} 个上游提交待合并，推送目标 {slug}/{branch}；加 --yes 执行")
        return 0

    if pending:
        merge(upstream_ref)
    check_anchors(args.skip_anchors)

    if args.no_push:
        log("跳过推送（--no-push）")
        return 0

    push(slug, branch)
    report_ci(slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
