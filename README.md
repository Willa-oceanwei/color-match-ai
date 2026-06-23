# color-match-ai

「色彩案例知識庫（Color Knowledge Base）」：樣品 → 拍照 → 上傳 → 找以前最像的相同料色板 → 顯示以前配方。

## Streamlit 實作架構 V1

V1 以單人可維護、未來不需要重建資料庫為原則，使用 Google Drive、Google Sheet、Streamlit、OpenCLIP 與本地向量檔建立相似色搜尋流程。

完整設計請參考：[Streamlit 系統「實作架構 V1」](docs/implementation-architecture-v1.md)。

## 已完成的 V1 程式架構

目前 repo 已具備可執行的 Streamlit V1 骨架：

- 上傳色板並自動寫入 `ColorBoard`。
- 自動判斷 `FormulaID` 是否存在於正式配方資料。
- 建立圖片向量並儲存到 `data/vectors/{Material}_vectors.pkl`。
- 上傳客戶樣品後搜尋同原料 Top 5。
- 在 UI 區分「正式配方」與「歷史案例 / 試樣」。

> 預設使用 `local` 儲存模式與 `color_stats` 輕量向量，方便先在本機 demo。正式上線時可在 `.env` 切換為 Google Sheet / Drive 與 OpenCLIP。

## 快速開始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## 設定檔

`.env.example` 提供 V1 所需環境變數：

- `COLOR_MATCH_STORAGE_BACKEND=local`：目前程式預設本地 CSV / 本地檔案 demo。
- `COLORBOARD_CSV_PATH=data/colorboard.csv`：ColorBoard 資料表。
- `FORMULA_CSV_PATH=data/formulas.csv`：正式配方查詢資料。
- `LOCAL_DRIVE_ROOT=data/drive`：本地模擬 Drive 根目錄。
- `VECTOR_DIR=data/vectors`：向量檔目錄。
- `EMBEDDING_BACKEND=color_stats`：輕量 demo 向量；可改為 `openclip`。
- `OPENCLIP_MODEL_NAME=ViT-B-32`、`OPENCLIP_PRETRAINED=openai`：OpenCLIP 設定。

## 主要檔案

```text
app.py                         Streamlit 入口
config.py                      環境變數與欄位設定
services/google_sheet.py       ColorBoard / 公式資料讀寫
services/google_drive.py       本地 Drive 寫入與路徑解析
services/formula_service.py    FormulaID 是否存在判斷
services/embedding_service.py  圖片向量建立與向量檔儲存
services/search_service.py     cosine similarity Top 5 搜尋
ui/upload_page.py              上傳色板頁
ui/search_page.py              相似色搜尋頁
ui/result_components.py        搜尋結果卡片
scripts/rebuild_vectors.py     批次重建向量
data/colorboard.csv            ColorBoard 範例資料
data/formulas.csv              正式配方範例資料
```

## 批次重建向量

若新增或替換色板圖片後需要重建向量，可執行：

```bash
python scripts/rebuild_vectors.py
```

目前範例 CSV 內的圖片檔不會提交到 repo；請先透過 Streamlit 上傳色板，或自行把圖片放到 `data/drive/{Material}/`。
