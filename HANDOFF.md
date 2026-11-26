# 交接文件：糟糕島物語 ～無名氏與最後的回應～

給接手這個專案的人（或新的 Claude 對話）。**開始改東西之前請先讀完這份文件。**

- 線上網址：https://red-dune-00b73a510.6.azurestaticapps.net/
- 推到 `main` 就會由 GitHub Actions 自動部署到 Azure Static Web Apps（約 1 分鐘）。
- 目前版本：頁面最下方的版本號（`index.html` 裡的 `class="ver"`），每次發佈請 +1。

---

## 1. 這是什麼

以 K 島（Komica／糟糕島）為舞台的網頁 JRPG。同一份遊戲資料有兩個引擎：

| | 位置 | 說明 |
|---|---|---|
| 網頁版（玩家實際玩的） | repo 根目錄：`index.html`、`game.js`、`data/game.json`、`img/` | 純 HTML/JS，沒有任何外部資源 |
| C# 版（Visual Studio 2022 / Blazor WebAssembly） | `source/KomicaRPG.sln`、`source/KomicaRPG/` | **從來沒有在 Visual Studio 編譯過**（開發環境沒有 .NET SDK），只做過靜態檢查 |

劇情、地圖、道具、敵人全部是資料，寫在 Python 裡，產生成 `game.json`；圖片也是 Python 用程式畫的 16×16 像素圖。

## 2. 資料夾

```
/                       ← 網站根目錄（直接部署）
  index.html            ← 版面、CSS、操作說明、「關於這個網站」
  game.js               ← 網頁版引擎
  data/game.json        ← 產生出來的檔案，不要手改
  img/*.png             ← 產生出來的檔案，不要手改
  staticwebapp.config.json ← 安全性標頭、no-cache、擋掉 /source/*
  source/
    tools/
      content_db.py     ← 角色、技能、道具、敵人、敵群、商店、任務、圖鑑說明
      content_extra.py  ← 討論板（BOARDS）、隊伍雜談（SKITS）、跳串點、章節卡
      build_content.py  ← 地圖、NPC、所有劇情腳本、結局；內建檢查器
      make_assets.py    ← 所有像素圖
      sim.js            ← 戰鬥平衡模擬器
      sync_web.sh       ← 一鍵：產生資料與圖片 → 複製到網站根目錄
    KomicaRPG/          ← C# 專案（Engine/*.cs、Pages/GameView.razor、wwwroot/）
    tests/              ← Playwright 測試腳本
```

## 3. 修改流程

1. 改劇情／資料：編輯 `source/tools/` 裡的 Python。
2. 在 repo 根目錄執行 `sh source/tools/sync_web.sh`。它會跑檢查器（引用錯誤、走不到的 NPC、站在牆上的人都會報錯），再把 `game.json` 和圖片同步到根目錄和 C# 的 `wwwroot/`。
3. 改引擎：**`game.js` 和 C#（`Game.cs`、`Game.Battle.cs`、`Game.Menus.cs`、`GameView.razor`）一定要同步改**；CSS 在 `index.html` 和 `source/KomicaRPG/wwwroot/css/game.css` 各一份，也要同步。C# 的 JS 輔助程式（長按、全螢幕、縮放）在 `source/KomicaRPG/wwwroot/index.html`。
4. 跑測試（見第 6 節）。
5. `index.html` 版本號 +1，commit、push。

### 劇情腳本格式（build_content.py）

腳本是指令陣列：`say`、`nar`、`IF(cond, then, else)`、`choice((文字, 腳本), …)`、`F("flag")`、`give`、`take`、`gold`、`goal`、`quest(id, "open"/"done")`、`karma(n)`、`battle(troop)`、`join`、`heal`、`inn`、`shop`、`warp`、`save`、`ending`、`call`、`chapter`、`board`。

條件字串：`flag:x`、`!flag:x`、`item:x>=n`、`karma>=n`、`gold>=n`、`party:x`，用 `&` 和 `|` 組合（不支援括號）。

NPC：`ent(id, sprite, x, y, script, show=條件, mark=條件)`。`mark` 成立時頭上會出現「！」提示。

對話可用 `{item:道具id}`（持有數量）和 `{goal}`（目前目標）。

## 4. 遊戲系統重點與數值

- **明雷遇敵**：野外怪物看得到。數量是可走格數 ÷ 45，限 3～9 隻；靠近 6 格內會追，每 300ms 走一格（玩家 140ms）。打贏的怪要離開地圖才會重生；無視後 4 秒不追；每場戰鬥結束後 1.5 秒無敵。
- **明雷戰獎勵**：經驗值與 K 幣 ×1.8（`MON_REWARD` / `MonReward`），用來補回比舊暗雷少的戰鬥場數。魔王戰不加成。
- **簡單模式**（跟著存檔）：敵人 HP ×0.7、我方受到傷害 ×0.6、經驗值與 K 幣 ×1.5、無視必成功、怪物少 3 隻、追蹤距離 3 格且較慢。
- **集氣「推」**：滿了可以放合體技（神串降臨、全島推爆）。
- **善行值（karma）**：真結局需要 karma ≥ 5 且原諒雪見；其他結局是 real／anon。
- **經驗曲線**：mul 10、pow 2.2。
- **魔王 HP**：捏他魔 980、釣魚王 1850、失落之圖 2800、名牌團長 4500、署名者雪見 4000、無貌者 9200／7800、隱藏魔王智障神 980。
- **其他**：存檔在 localStorage；換地圖會自動存檔。有全螢幕模式（F 鍵；手機上按鍵會半透明疊在畫面上），以及長按連續移動。

### 除錯 API（瀏覽器主控台）

`KDBG.warp(map,x,y)`、`flag`、`give`、`level`、`join`、`battle(troop)`、`run(script)`、`speed(倍率)`、`god(1)`、`mons(false)`（關掉明雷怪，腳本化測試要用）、`closeUI()`、`S`（狀態）、`D`（資料）。

## 5. 內容規則（請遵守）

- 用語要像 K 島（乙、閱、華生、詳細希望、自重、無視、+1、精華、XX你好XX再見……），但**不放下流、性暗示、政治梗**。
- 劇情主題：匿名的惡意與匿名的溫柔，「回應」就是島的生命。
- **島上名人**（生日哥、照燒貓、智障神、易經廚、放矢哥、西瓜哥、塗鴉廚）是以公開流傳的梗為靈感的虛構角色：
  - 只用口頭禪和行為梗，不用真名、ID、照片或傳聞；
  - 每個人都要有被理解或改變的結局，不做純嘲弄；
  - 「關於這個網站」裡的虛構角色聲明要保留。
- 不使用外部資源（CSP 限制 `'self'`），不加廣告或追蹤碼。

## 6. 測試

需要 Python 3、Playwright（Chromium）、Node.js。

```sh
python3 -m http.server 8765           # 在 repo 根目錄啟動
python3 source/tests/t4.py true       # 完整流程跑到真結局（也可用 real、anon）
python3 source/tests/t6.py            # 討論板、雜談、圖鑑、跳串等功能
python3 source/tests/t23.py           # 島上名人三條支線
python3 source/tests/fuzz.py 1 2500   # 隨機操作壓力測試（開著明雷怪，含不變量檢查）
python3 source/tests/bfuzz.py 11 25   # 戰鬥壓力測試
python3 source/tests/audit.py         # 資料完整性：引用、旗標、圖片
python3 source/tests/csp_server.py &  # 帶安全性標頭的伺服器（8766），然後：
python3 source/tests/t7.py            # 確認 CSP 沒有違規
node source/tools/sim.js data/game.json   # 魔王勝率模擬
```

其他測試：t9（長按移動）、t11（四方向走路圖）、t14（游標）、t16（全螢幕）、t18（四人 HP 顯示）、t19（開場指示）、t20（明雷與難度）、t21b（明雷遇敵場數）、t24（智障神實戰）。

注意事項：
- 測試的截圖會寫到 `/tmp`。
- 同時開太多個瀏覽器測試時，t9 這類跟時間有關的測試可能因為太慢而失敗，單獨重跑即可。

## 7. 待辦與已知事項

- **C# 版需要在 Visual Studio 2022 建置確認**（安裝「ASP.NET 與網頁程式開發」工作負載）。這是目前最大的未知數。
- 部署設定用了 `skip_app_build: true`，因為 repo 裡有 `.sln`，不加的話 Azure 可能會嘗試編譯 C# 專案。
- `staticwebapp.config.json` 擋掉了 `/source/*`，原始碼不會出現在網站上，但 repo 本身是公開的。若把 repo 改成私人，「關於這個網站」裡的原始碼連結要改掉。
- 曾有玩家回報：四人隊伍時戴爾的 HP 看不到（已修），以及開場找不到會館（已加強指示、「！」提示、易經廚卜卦）。
