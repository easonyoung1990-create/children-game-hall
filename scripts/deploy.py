#!/usr/bin/env python3
"""Update one game source file and publish it to the game server."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
UPDATE_TOOL = ROOT / "update_game.py"
MANIFEST = SITE_DIR / "games.json"


def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def update_local(game: str, source: Path, version: str) -> None:
    run([
        "python",
        str(UPDATE_TOOL),
        game,
        str(source),
        "--version",
        version,
        "--site",
        str(SITE_DIR),
    ])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def check_no_external(game: str) -> str:
    html = (SITE_DIR / "games" / game / "index.html").read_text(encoding="utf-8")
    bad = re.findall(r"(?:src|href)=\"(?:https?://|//)[^\"]+\"", html)
    if bad:
        raise RuntimeError(f"发现外部引用，不允许发布: {bad}")
    return sha256(SITE_DIR / "games" / game / "index.html")


def publish(game: str, host: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    local_game = SITE_DIR / "games" / game / "index.html"
    run(["scp", str(local_game), f"{host}:/tmp/{game}-new.html"])
    run(["scp", str(MANIFEST), f"{host}:/tmp/games.json"])
    backup = f"/var/www/games-hall/.rollback/{game}/{ts}"
    remote = (
        f"sudo mkdir -p {backup} && "
        f"sudo cp /var/www/games-hall/site/games/{game}/index.html {backup}/index.html && "
        f"sudo cp /var/www/games-hall/site/games.json {backup}/games.json && "
        f"sudo cp /tmp/{game}-new.html /var/www/games-hall/site/games/{game}/index.html && "
        f"sudo cp /tmp/games.json /var/www/games-hall/site/games.json"
    )
    run(["ssh", host, remote])
    return ts


def rollback(game: str, host: str, stamp: str | None) -> str:
    if not stamp:
        out = run(["ssh", host, f"ls -1 /var/www/games-hall/.rollback/{game} | tail -n 1"], capture_output=True)
        stamp = (out.stdout or "").strip()
    if not stamp:
        raise RuntimeError("未找到回滚快照")
    run(["ssh", host, f"sudo cp /var/www/games-hall/.rollback/{game}/{stamp}/index.html /var/www/games-hall/site/games/{game}/index.html"])
    run(["ssh", host, f"sudo cp /var/www/games-hall/.rollback/{game}/{stamp}/games.json /var/www/games-hall/site/games.json"])
    return stamp


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("game", choices=["kenton", "eddey", "backrooms"])
    p.add_argument("source", type=Path, help="新游戏 index.html 的源文件")
    p.add_argument("--version", required=True)
    p.add_argument("--host", default="eddey-tencent-sg")
    p.add_argument("--publish", action="store_true")
    p.add_argument("--rollback", default="", help="回滚到指定时间戳；空值时回滚到最近一次")
    args = p.parse_args()

    if args.rollback:
        done = rollback(args.game, args.host, args.rollback or None)
        print(f"已回滚：{args.game} -> {done}")
        return

    update_local(args.game, args.source, args.version)
    sha = check_no_external(args.game)
    print(f"本地更新完成：{args.game} sha256={sha}")
    if args.publish:
        stamp = publish(args.game, args.host)
        print(f"已发布到服务器。回滚快照：/var/www/games-hall/.rollback/{args.game}/{stamp}")


if __name__ == "__main__":
    main()
