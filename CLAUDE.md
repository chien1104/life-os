# 🌻芊的工具檯（原名 Life OS 生活整理工具箱）：給 Claude Code 的專案說明

使用者：芊芊。全程使用繁體中文，回覆簡短直接；方向不清楚時先問，不要一次產出大量相似選項。

## 專案是什麼
- 單一檔案 App：`index.html`（HTML＋CSS＋JavaScript 全部在一個檔案）。
- 規格書：`docs/LifeOS_規格書_v2.2.md`（決策紀錄在第 12 章）。
- 測試：`tests/`（Playwright，Python）。
- **交接說明：`HANDOFF.md`**（目前狀態、已做決定、待辦）。開始工作前先讀。

## 一定要遵守的規則
1. 以現有 `index.html` 為基礎直接修改，不要從零重做；保留 UI、配色、字體、版面，不得擅自刪除功能。
2. 資料存在 localStorage `lifebox_v1`（備份 `lifebox_v1_backups`、圖片在 IndexedDB `lifeos_files`）。
   不得清除、覆蓋或重設使用者資料；改資料格式要用版本化 migration（目前 schemaVersion 6），先備份再遷移。
3. 不增加未確認的功能；不做假按鈕；沒有功能的不要放上畫面。
4. 不得把前端規則說成 AI 或雲端；不得宣稱未測試的為已測試。
5. 待辦：不用時間區塊排程，以彈性待辦為核心；未完成自動順延，保留原建立日與延期歷史，不重複建立；
   截止日與順延日分開，逾期只標示、不改原截止日。
6. 重要資料修改或刪除需要使用者確認。
7. API 金鑰不得放在前端。
8. 星光秘境：內容原創，不複製市售牌卡圖文；標示「娛樂與自我反思」。
   大天使神諭卡依真實天使傳統（名字原意、典籍出處）；星座運勢、個人星盤、盧恩符文、易經已依使用者要求移除，不要加回。
9. App 已完全移除 AI 與雲端同步（使用者決定），不要加回；所有資料只存在使用者自己的裝置。
10. 介面全站使用 emoji；財務帳戶類型包含「股票」。
11. 待辦區塊共 8 個：工作與事業、內容創作、財務、學習、生活、購物、朋友、家人（「工作」「事業」已合併，版本 6 遷移）。

## 測試
```
pip install playwright && python -m playwright install chromium
cd tests && npm install        # 月相比對用的 astronomy-engine
python t4d.py && python t5d.py && python t6e.py && python t7b.py && python t8.py
```
每次修改後全部跑過；目前共 236 項全部通過（t7b 改為「確認沒有 AI 與雲端同步」）。改版面時用 390px 與 360px 寬度截圖檢查。

## 發布
靜態網站（Netlify 或 GitHub Pages），`index.html` 放在根目錄。
不得加入任何廣告、品牌標誌或追蹤程式（使用者明確要求）。部署後要實際打開網址確認是新版、公開可看。
