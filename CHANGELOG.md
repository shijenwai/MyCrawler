# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2025-05-31
### Added
- 支援動態自訂網址選項，並僅在成功爬取後寫入 `config.py`
- 直接由使用者輸入爬取深度
- 自動清除舊有輸出資料夾並重建
- 爬取過程中顯示「第 X 層開始…」的分層日誌

### Changed
- 移除探索階段，只保留實際爬取流程

## [0.1.0] - 2025-05-30
### Added
- 基本網站選單與 `config.py` 的靜態設定
- Markdown 爬取及存檔功能
- 檔名清理 `sanitize_filename` 功能 