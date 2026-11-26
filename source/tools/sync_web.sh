#!/bin/sh
# 重新產生遊戲資料與圖片，並同步到網站根目錄（repo 根目錄的 data/ 與 img/）
# 用法：在 repo 根目錄執行  sh source/tools/sync_web.sh
set -e
cd "$(dirname "$0")"
python3 build_content.py ../KomicaRPG/wwwroot/data/game.json
python3 make_assets.py ../KomicaRPG/wwwroot/img
cp ../KomicaRPG/wwwroot/data/game.json ../../data/game.json
cp ../KomicaRPG/wwwroot/img/*.png ../../img/
echo "synced to web root"
