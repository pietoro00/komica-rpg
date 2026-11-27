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
  motion/               ← 跟遊戲無關的小工具：手機鏡頭動靜偵測器（/motion/）。
                          只有 /motion* 的標頭允許鏡頭（camera=(self)）和 blob: 影片，其他頁面維持全擋
  source/
    tools/
      content_db.py     ← 角色、技能、道具、敵人、敵群、商店、任務、圖鑑說明
      content_extra.py  ← 討論板（BOARDS）、隊伍雜談（SKITS）、跳串點、章節卡
      build_content.py  ← 地圖、NPC、所有劇情腳本、結局；內建檢查器
      make_assets.py    ← 所有像素圖
      sim.js            ← 戰鬥平衡模擬器
      sync_web.sh       ← 一鍵：產生資料與圖片 → 複製到網站根目錄
    KomicaRPG/          ← C# 專案（Engine/*.cs、Pages/GameView.razor、wwwroot/）；全自動模式在 Engine/Game.Auto.cs
    tests/              ← Playwright 測試腳本
```

## 3. 修改流程

1. 改劇情／資料：編輯 `source/tools/` 裡的 Python。
2. 在 repo 根目錄執行 `sh source/tools/sync_web.sh`。它會跑檢查器（引用錯誤、走不到的 NPC、站在牆上的人都會報錯），再把 `game.json` 和圖片同步到根目錄和 C# 的 `wwwroot/`。
3. 改引擎：**`game.js` 和 C#（`Game.cs`、`Game.Battle.cs`、`Game.Menus.cs`、`Game.Auto.cs`、`GameView.razor`）一定要同步改**；CSS 在 `index.html` 和 `source/KomicaRPG/wwwroot/css/game.css` 各一份，也要同步。C# 的 JS 輔助程式（長按、全螢幕、縮放）在 `source/KomicaRPG/wwwroot/index.html`。
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
- **手寫對話框**：`game.json` 的 `hand` 列出的說話者（目前是黃毛），對話框會變成筆記紙、每個字歪一點。腳本也可以用 `["hand", 說話者, 台詞…]`（build_content.py 的 `hand()`）讓單句用手寫字，目前用在生日卡片和精華區的三段舊回應。設定裡的「對話字體：手寫」會讓所有對話都用手寫字（記在裝置上）。
- **目標箭頭**（自己玩時，設定可關）：用全自動的路線計算只找主線（`autoComputePlan({arrow:true,noTravel:true})`，不聊天、不買東西、不跳串），目標在畫面裡就在頭上顯示 ▼，在畫面外就貼著邊緣指方向；別張地圖的目標會指向該走的出口或船夫。狀態沒變不重算。
- **本次冒險紀錄**：全破的結局卡下方列出戰鬥場數、打倒的怪物、寶箱、完成的支線、善行、步數、全自動被推回來的次數（`S.stats`，跟著存檔）。
- **全自動模式**（開新串時選「全自動」，或在「設定」打開；跟著存檔）：電腦幫玩家玩到結局。
  - 開啟時難度自動改成簡單；戰鬥中倒下的同伴在回合結束時復活並補滿 HP／MP（不會全滅）。
  - 找下一步的方式是「預演」：把每個看得到的人的腳本在狀態複本上跑一次。會設新旗標、給道具、開／完成任務、開戰、入隊、去沒去過的地方的，就是要去找的人；台詞跟上次聽過的不一樣（`autoSeen`），就是有新對話，只在同一張地圖裡順便聊。
  - 優先順序：這張地圖上的事 → 目前目標（`goal` 文字裡出現的地圖名稱、或設定目標時所在的地圖）與頭上有「！」的人 → 其他支線與寶箱 → 不在目標裡的魔王戰 → 結局。最後一條是為了不讓它跳過劇情先打魔王。
  - 選項的選法：善行（karma）最優先，其次是會讓劇情前進的；不逛照燒攤、不搭船回頭。**新寫的選項，好的那個要有 karma 或旗標**，全自動才會選它。
  - 跨地圖路線把傳送點、船夫（腳本裡只有對話和 `warp` 的 NPC）、跳串一起算最短路。會被 `unflag` 的旗標（外來種的男女切換）不算進度。
  - 經過有商店的人時，會買得起又比較好的裝備；背包有更好的裝備就自動換上。
  - 速度：進行中按 → 加速 ×2／×3／×4、← 減速（設定的「自動速度」也能切換）；倍率會套用到走路、對話、戰鬥動畫。對話每句停 500＋110ms×字數，看板一則一則往下捲、每則停 600～900＋70ms×字數。按「選單」暫停，點左上角 AUTO 關閉。
  - 「全自動範圍：只跑主線」：只做目前目標地圖裡的事與頭上有「！」的主線，略過會接／推進／交付支線（腳本裡有 `quest`）的人和閒聊，裝備照買；找不到路才退回全部。只跑主線通常會是普通結局（真結局要靠支線的善行）。

### 除錯 API（瀏覽器主控台）

`KDBG.warp(map,x,y)`、`flag`、`give`、`level`、`join`、`battle(troop)`、`run(script)`、`speed(倍率)`、`god(1)`、`mons(false)`（關掉明雷怪，腳本化測試要用）、`closeUI()`、`auto(true/false)`、`autoTargets()`（全自動模式現在想去哪些地方）、`S`（狀態）、`D`（資料）。

## 5. 內容規則（請遵守）

- 用語要像 K 島（乙、閱、華生、詳細希望、自重、無視、+1、精華、XX你好XX再見……），但**不放下流、性暗示、政治梗**。
- 劇情主題：匿名的惡意與匿名的溫柔，「回應」就是島的生命。
- **島上名人**是以公開流傳的梗為靈感的虛構角色：
  - 武將與廚：生日哥（綜合村）、照燒貓（流浪攤販）、智障神、放矢哥（新番鎮）、易經廚（綜合村）、西瓜哥（釣魚港）。
  - 塗鴉角落的塗鴉廚（塗鴉廚是一群人，每個人畫一個自己的角色來說話）：黃毛、星芳（美術館 1F）、外來種（新番鎮）、獨眼／雀斑（綜合村）、驚恐醬（捏他平原）、汪醬→獅子老大（釣魚港）、慕內（惡搞谷）。
  - 只用口頭禪和行為梗，不用真名、ID、照片或傳聞；
  - 每個人都要有被理解或改變的結局，不做純嘲弄；
  - **不要加入「綜合武將」裡的真人**：那些大多是被貼照片、被肉搜的普通人。後期武將、牽涉精神疾病或自殺嘲諷的廚、有性癖成分的改圖魔人與 R-18 塗鴉廚、牽涉家人照片的名人，都不要用；
  - 「關於這個網站」裡的虛構角色聲明要保留，新增角色時把名字加進去。
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

其他測試：t9（長按移動）、t11（四方向走路圖）、t14（游標）、t16（全螢幕）、t18（四人 HP 顯示）、t19（開場指示）、t20（明雷與難度）、t21b（明雷遇敵場數）、t24（智障神實戰）、t25（補 MP 道具選對象時顯示 MP）、t27（島上名人與塗鴉角落的每條支線）、t28（箭頭、變速、看板、手寫、冒險紀錄）。

```sh
python3 source/tests/t26.py 6 0.02        # 全自動模式：從標題選「全自動」什麼都不按，應該在幾分鐘內打到真結局、所有任務完成
python3 source/tests/t26.py 6 0.02 main   # 只跑主線：約一半時間到結局（anon），不接支線
python3 source/tests/t28.py               # 目標箭頭、→／← 變速、看板依字數停留、手寫字、冒險紀錄
```

改了劇情或地圖之後一定要跑 t26：它會抓到「全自動卡住」（新的人物沒有可以前進的條件、選項好壞分不出來、魔王被提早打掉）。

注意事項：
- 測試的截圖會寫到 `/tmp`。
- 同時開太多個瀏覽器測試時，t9 這類跟時間有關的測試可能因為太慢而失敗，單獨重跑即可。

## 7. 待辦與已知事項

- **C# 版需要在 Visual Studio 2022 建置確認**（安裝「ASP.NET 與網頁程式開發」工作負載）。這是目前最大的未知數。
- 部署設定用了 `skip_app_build: true`，因為 repo 裡有 `.sln`，不加的話 Azure 可能會嘗試編譯 C# 專案。
- `staticwebapp.config.json` 擋掉了 `/source/*`，原始碼不會出現在網站上，但 repo 本身是公開的。若把 repo 改成私人，「關於這個網站」裡的原始碼連結要改掉。
- 曾有玩家回報：四人隊伍時戴爾的 HP 看不到（已修），以及開場找不到會館（已加強指示、「！」提示、易經廚卜卦）。
- 戰鬥壓力測試（bfuzz）偶爾會印出 BATTLE STUCK：那是測試本身的收尾只按 Enter，游標停在灰掉的技能上時動不了，不是遊戲卡住。換個 seed 重跑即可。
