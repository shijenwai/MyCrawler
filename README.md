# crawl4Ai

一個基於 Python 的異步網頁爬蟲工具，使用 `crawl4ai` 套件快速爬取靜態文件網站並將內容保存為 Markdown。

## 功能
- 支援多站點配置，集中管理要爬取的文件網站
- 動態輸入自訂網址並可選擇爬取深度
- 自動清除舊有輸出資料夾以避免冗餘資料
- 爬取過程中顯示分層日誌，清晰了解每層爬取進度
- 成功後將自訂網址自動寫入 `config.py`
- 結果以 Markdown 格式輸出到 `result/` 資料夾

## 安裝
```bash
git clone <repository_url>
cd crawl4Ai
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

## 使用方法
執行主程式：
```bash
python main.py
```
1. 選擇預設站點或「自訂網址」
2. 輸入要爬取的網址（若選擇自訂）
3. 輸入爬取深度（0 表示單頁）
4. 以 Markdown 格式輸出到 `result/<output_subdir>/`

## 設定
- 所有預設站點配置位於 `config.py`
- 可手動新增、移除或修改配置

## 版本
詳細變更請參考 [CHANGELOG.md](CHANGELOG.md)

## 貢獻
歡迎提交 issue 或 pull request，共同改進此專案！ 