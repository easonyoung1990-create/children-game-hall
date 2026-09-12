# 两孩游戏发布仓库

本仓库只存放游戏发布源码与发布历史，独立于业务代码。

## 目录

- `site/`：网站静态内容（大厅与三款游戏）
- `update_game.py`：本地版本替换脚本（仅替换本地文件）
- `scripts/deploy.py`：本地更新 + 发布 + 回滚工具
- `validation.json`：上一轮静态检查与核验结果

## 版本更新与发布流程

1. 准备新游戏文件（单个 HTML）
2. 运行本地更新：
   ```bash
   python scripts/deploy.py kenton <新文件路径> --version v14 --publish
   ```
   可选参数：
   - `--host eddey-tencent-sg`（默认）
   - `--publish`（不加则仅本地更新，不发布）
3. `deploy.py` 会：
   - 调用 `update_game.py` 更新 `site/games/<game>/index.html`
   - 更新 `site/games.json` 的 `sha256/source/version`
   - 上传并发布到服务器同一地址：
     - 主页：`/`
     - 哥哥：`/games/kenton/`
     - 弟弟：`/games/eddey/`
     - 后室：`/games/backrooms/`
4. 发布会保留回滚目录：
   `/var/www/games-hall/.rollback/<game>/<时间戳>/`
   可按时间回滚：
   ```bash
   python scripts/deploy.py kenton dummy.html --version v14 --rollback <时间戳>
   ```

## 回滚

仅改某个游戏文件时，会同时备份该游戏旧 `index.html` 和当时的 `site/games.json`。
`--rollback latest` 会回到最近一次快照。

