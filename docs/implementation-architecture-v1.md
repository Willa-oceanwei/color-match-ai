# Streamlit 系統「實作架構 V1」

## 1. V1 目標與邊界

V1 的目標是建立一個可由單人維護、可立即在工廠試用的「色彩案例知識庫」。使用者上傳 ABS 等塑膠色板照片後，系統會從既有 ColorBoard 色板案例中找出最相近的 Top 5，並依據是否存在正式配方，顯示「完整配方」或「歷史色板案例」。

V1 不把 Google Sheet 當成複製版資料庫，而是維持兩層資料來源：

- **ColorBoard Sheet**：所有色板案例與 AI 搜尋索引的主資料，包含正式配方、試樣、失敗樣與參考樣。
- **色粉管理 Sheet**：正式配方的唯一真實來源（Single Source of Truth），只有當 ColorBoard 的 `FormulaID` 有值時才查詢。

## 2. 推薦專案目錄

```text
color-match-ai/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── docs/
│   └── implementation-architecture-v1.md
├── services/
│   ├── google_drive.py
│   ├── google_sheet.py
│   ├── formula_service.py
│   ├── embedding_service.py
│   └── search_service.py
├── ui/
│   ├── upload_page.py
│   ├── search_page.py
│   └── result_components.py
├── data/
│   ├── vectors/
│   │   ├── ABS_vectors.pkl
│   │   └── PP_vectors.pkl
│   └── cache/
├── tmp/
└── tests/
    ├── test_filename_parser.py
    ├── test_formula_lookup.py
    └── test_search_service.py
```

## 3. Google Sheet 設計

### 3.1 ColorBoard Sheet

建議檔名與分頁都使用 `ColorBoard`。此分頁是 AI 搜尋與歷史案例的核心資料表。

| 欄位 | 必填 | 範例 | 說明 |
| --- | --- | --- | --- |
| ID | 是 | `ABS_27706` | 色板唯一 ID，建議由 `Material_流水號或配方號` 組成。 |
| Material | 是 | `ABS` | 原料類型，用於限制搜尋範圍。 |
| ImagePath | 是 | `ABS/ABS_27706.jpg` | 相對路徑，不直接存 Google Drive URL。 |
| FormulaID | 否 | `27706` | 若有正式配方則填入；沒有正式配方可空白。 |
| FormulaMode | 是 | `EXISTING` / `MANUAL` | `EXISTING` 表示引用正式配方；`MANUAL` 表示手動留存案例。 |
| RecipeStatus | 是 | `OFFICIAL` / `TRIAL` / `FAILED` / `REFERENCE` | 色板案例狀態。 |
| EmbeddingStatus | 是 | `Y` / `N` | 是否已建立 CLIP 向量。 |
| Customer | 否 | `ABC` | 客戶名稱。 |
| ColorName | 否 | `牙白` | 顏色名稱。 |
| Pantone | 否 | `11-0601` | Pantone 或其他色號。 |
| CreateDate | 是 | `2026/06/23` | 建立日期。 |
| LastUpdate | 是 | `2026/06/23 15:25` | 最後更新時間，用於判斷是否需要重建向量。 |
| Remark | 否 | `霧面` | 備註。 |

### 3.2 色粉管理 Sheet

色粉管理不複製進 `ColorBoard`，而是作為正式配方的查詢來源。V1 只需要實作「用 `FormulaID` 查詢是否存在」與「回傳正式配方明細」兩個能力。

## 4. 核心流程

### 4.1 上傳色板並自動寫入 ColorBoard

1. 使用者在 Streamlit 選擇 `Material`。
2. 使用者上傳照片。
3. 使用者輸入或選擇：
   - `FormulaID`（可空白）
   - `RecipeStatus`
   - `Customer`
   - `ColorName`
   - `Pantone`
   - `Remark`
4. 系統依據 `FormulaID` 判斷配方是否存在：
   - 找得到：`FormulaMode = EXISTING`，預設 `RecipeStatus = OFFICIAL`。
   - 找不到或空白：`FormulaMode = MANUAL`，預設 `RecipeStatus = TRIAL`。
5. 系統產生 `ID` 與檔名：
   - 若有 `FormulaID`：`ABS_27706`。
   - 若無 `FormulaID`：`ABS_TRIAL_YYYYMMDD_HHMMSS`。
6. 照片上傳至 Google Drive：`{Material}/{ID}.jpg`。
7. 寫入 ColorBoard，並先標記 `EmbeddingStatus = N`。
8. 立即建立 CLIP 向量成功後，更新 `EmbeddingStatus = Y` 與向量檔。

### 4.2 自動判斷 FormulaID 是否存在

`formula_service.py` 負責查詢色粉管理 Sheet：

```python
def resolve_formula_mode(formula_id: str | None) -> dict:
    if not formula_id:
        return {"exists": False, "formula_mode": "MANUAL", "recipe_status": "TRIAL"}

    formula = lookup_formula_by_id(formula_id)
    if formula:
        return {"exists": True, "formula_mode": "EXISTING", "recipe_status": "OFFICIAL", "formula": formula}

    return {"exists": False, "formula_mode": "MANUAL", "recipe_status": "TRIAL"}
```

設計重點：`FormulaID` 不存在時不能擋住建檔，因為 ColorBoard 本來就允許保存非正式試樣。

### 4.3 CLIP 向量建立流程

V1 建議使用 OpenCLIP 產生影像向量，並以 `pickle` 或 `parquet` 儲存在 `data/vectors/{Material}_vectors.pkl`。

向量資料結構建議：

```python
{
    "material": "ABS",
    "model_name": "ViT-B-32/openai",
    "updated_at": "2026-06-23T15:25:00Z",
    "items": [
        {
            "id": "ABS_27706",
            "image_path": "ABS/ABS_27706.jpg",
            "formula_id": "27706",
            "recipe_status": "OFFICIAL",
            "embedding": [0.0123, -0.0045]
        }
    ]
}
```

向量建立策略：

- **單筆新增**：上傳色板後立即產生向量並 append 到對應原料的向量檔。
- **批次重建**：管理者按「重建向量」時，讀取 ColorBoard 中 `EmbeddingStatus = N` 或 `LastUpdate` 晚於向量更新時間的資料。
- **同原料搜尋**：搜尋 ABS 樣品時只載入 `ABS_vectors.pkl`，避免不同材料混在一起造成誤判。

### 4.4 Top 5 相似搜尋

搜尋流程：

1. 使用者選擇樣品 `Material`。
2. 上傳客戶樣品照片。
3. 系統建立查詢影像向量。
4. 載入 `{Material}_vectors.pkl`。
5. 使用 cosine similarity 計算相似度。
6. 回傳 Top 5。
7. 逐筆補資料：
   - 從 ColorBoard 取得色板資訊。
   - 若 `FormulaID` 存在且 `FormulaMode = EXISTING`，再查色粉管理 Sheet 補正式配方。
   - 若沒有正式配方，標記為歷史案例。

## 5. Streamlit UI V1

### 5.1 頁面一：上傳色板

功能：將新的色板案例寫入 ColorBoard 並建立向量。

UI 區塊：

- 基本資料：`Material`、`FormulaID`、`Customer`、`ColorName`、`Pantone`。
- 案例狀態：`RecipeStatus`，預設依 `FormulaID` 查詢結果自動決定。
- 照片上傳：支援 jpg、png。
- 預覽區：顯示即將寫入的 `ID`、`ImagePath`、`FormulaMode`。
- 儲存按鈕：完成 Google Drive 上傳、ColorBoard 寫入與向量建立。

### 5.2 頁面二：相似色搜尋

功能：客戶樣品照片上傳後回傳 Top 5。

UI 區塊：

- 搜尋條件：`Material`。
- 樣品照片上傳。
- Top 5 結果卡片：
  - 色板圖片。
  - 相似度。
  - `ID`、`Material`、`ColorName`、`Customer`、`Pantone`。
  - `RecipeStatus` 標籤。
  - 「有正式配方」或「僅歷史案例」狀態。

### 5.3 有配方 / 無配方結果 UI

#### 有正式配方

顯示：

- 綠色標籤：`正式配方`
- ColorBoard 基本資訊
- 色粉管理查回的配方明細
- 建議 CTA：`查看完整配方`、`複製配方編號`

#### 無正式配方

顯示：

- 黃色標籤：`歷史案例 / 試樣`
- ColorBoard 基本資訊
- 備註與照片
- 提醒文字：`此色板尚未存在於正式配方管理，請以歷史打樣紀錄參考。`
- 建議 CTA：`建立正式配方`、`標記為參考樣`

## 6. 主要 Python 模組責任

| 檔案 | 責任 |
| --- | --- |
| `app.py` | Streamlit 入口，控制頁面切換與全域設定。 |
| `config.py` | Google Sheet ID、Drive folder ID、模型名稱、向量檔路徑設定。 |
| `services/google_sheet.py` | 讀寫 ColorBoard 與色粉管理 Sheet。 |
| `services/google_drive.py` | 上傳、下載與組合圖片路徑。 |
| `services/formula_service.py` | 判斷 `FormulaID` 是否存在並回傳配方資料。 |
| `services/embedding_service.py` | 載入 OpenCLIP、圖片前處理、產生向量。 |
| `services/search_service.py` | 載入向量檔、計算相似度、回傳 Top 5。 |
| `ui/upload_page.py` | 上傳色板頁面。 |
| `ui/search_page.py` | 相似色搜尋頁面。 |
| `ui/result_components.py` | 結果卡片與有/無配方 UI 元件。 |

## 7. V1 開發順序

1. 建立 `config.py` 與 `.env` 設定讀取。
2. 完成 Google Sheet 讀取 ColorBoard。
3. 完成色粉管理 `FormulaID` 查詢。
4. 完成 Google Drive 圖片上傳與相對路徑規則。
5. 完成 OpenCLIP 單張圖片向量產生。
6. 完成向量檔儲存與載入。
7. 完成 Top 5 cosine similarity 搜尋。
8. 完成 Streamlit 搜尋頁。
9. 完成 Streamlit 上傳色板頁。
10. 補上批次重建向量功能。

## 8. V1 風險與保護規則

- 上傳照片前必須壓縮或限制尺寸，避免 Google Drive 與向量建立速度失控。
- `ID` 必須唯一；若 `ABS_27706` 已存在，系統應提示使用者更新既有資料或改用試樣 ID。
- Google Sheet 欄位名稱要固定，不建議常改欄位名。
- 搜尋結果必須限制同一種 `Material`，避免 ABS 與 PP 混搜。
- 沒有正式配方的案例不能被隱藏，因為它們可能是最有價值的現場經驗。
- 色粉管理 Sheet 是正式配方來源，V1 不做複製、不做雙向同步。

## 9. V1 完成定義

符合以下條件即可視為 V1 可上線試用：

- 可以上傳色板照片並自動寫入 ColorBoard。
- 可以判斷 `FormulaID` 是否存在於色粉管理。
- 可以為新色板建立 CLIP 向量。
- 可以上傳客戶樣品並搜尋同原料 Top 5。
- Top 5 結果可以清楚分辨「正式配方」與「歷史案例」。
- 即使色板沒有正式配方，也能被搜尋與顯示。
