# Demand Planning Workbench

一套可在本機執行的需求預測與情境規劃平台。系統將銷售資料驗證、時間序列回測、
模型選擇、預測區間、情境調整、執行稽核與報告輸出串成一條可重現的全端工作流。

本作品是獨立且可公開展示的通用專案，不依附特定企業、職缺或私有資料。預設 Demo
完全離線、零 API 費用；Git 只包含原創小型資料，公開大型資料需另行下載。

## 使用情境、輸入與輸出

| 項目 | 定義 |
|---|---|
| 使用情境 | 零售或消費品規劃人員產生短期 SKU／地點需求預測並比較營運情境 |
| CSV 輸入 | `date, sku_id, location_id, units`；可選 `price, promo, stockout` |
| 核心處理 | 驗證 → 日序列補齊 → rolling-origin 回測 → 模型選擇 → 預測區間 → 情境規則 → 稽核 |
| 輸出 | 基準與情境預測、WAPE／MASE／Bias、警示、CSV／JSON／HTML 報告及 SQLite 紀錄 |
| 失敗策略 | 拒絕不合法列；歷史不足時使用安全基線並明確標記；不將情境調整宣稱為因果效果 |

## 預定交付範圍

- 可擴充的預測模型與評測指標介面。
- Seasonal Naive、Moving Average、Croston-SBA 與 Linear Trend 實務基線。
- 多折 rolling-origin 回測、自動模型選擇及殘差式預測區間。
- 可版本化的 multiplier、additive 與 override 情境規則。
- FastAPI、SQLite、React／TypeScript 操作介面與 CLI。
- 單元、整合、API、端到端和前端測試。
- 可重現 Demo、效能基準、隱私掃描與 CI 定義。

完整操作方法與驗證結果會在 v1.0 完成後補入本文件。

## 公開資料邊界

正式資料評估採用 UCI Online Retail II（CC BY 4.0）。下載檔放在 `data/raw` 並由 Git
忽略；授權、轉換方式與限制見 `docs/DATASET.md`。公開資料記錄的是銷售而非未受缺貨
限制的潛在需求，因此本作品不把評估結果宣稱為真實需求或正式補貨建議。

## 授權

專案原始碼及原創範例資料採 MIT License。第三方套件與資料來源見
`THIRD_PARTY_NOTICES.md`。

