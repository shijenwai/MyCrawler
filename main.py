import asyncio
import re
import os
import math
import shutil
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler
from crawl4ai import CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from config import SITES # 匯入網站設定

# 確保 result 資料夾存在
BASE_OUTPUT_DIR = "result" # 主輸出資料夾
if not os.path.exists(BASE_OUTPUT_DIR):
    os.makedirs(BASE_OUTPUT_DIR)

def sanitize_filename(url):
    """根據 URL 生成一個安全且可讀的檔案名。"""
    parsed_url = urlparse(url)
    # 取路徑部分，去除開頭的 /docs/，並將 / 替換為 _
    path_part = parsed_url.path
    # 移除 initial_url 的基本路徑部分，避免檔名太長
    # 這部分需要更通用的處理，暫時保留之前的邏輯，但未來可以優化
    # 例如，如果 initial_url 是 https://example.com/docs/project/
    # 那麼 /docs/project/page1 -> page1
    # 現在的邏輯: if path_part.startswith("/docs/"): path_part = path_part[len("/docs/"):]
    # 這對 facebook 的 /docs/whatsapp 是有效的，但對 crawl4ai 的 /core/ 等則不會作用
    # 為了保持現有 facebook 的檔名結構，暫不修改此處，但標記為可改進點

    filename = path_part.replace('/', '_').strip('_').lstrip('_') # lstrip 避免開頭是底線
    # 避免檔名太長或包含非法字元 (簡化處理)
    filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
    if not filename: # 如果處理後檔名為空，給一個預設值
        filename = "crawled_page"
    return f"{filename}.md"

async def main_crawl():
    print("請選擇要爬取的網站設定:")
    for i, site_config in enumerate(SITES):
        print(f"{i+1}. {site_config['name']}")
    print(f"{len(SITES)+1}. 自訂網址")

    choice = -1
    # 自訂網址寫入條目，待後續成功爬取後再加入
    custom_config_entry = None
    while True:
        try:
            choice_input = input(f"請輸入選項編號 (1-{len(SITES)+1}): ")
            choice = int(choice_input) - 1
            if 0 <= choice <= len(SITES):
                break
            else:
                print("輸入無效，請重新輸入。")
        except ValueError:
            print("輸入的不是數字，請重新輸入。")

    if choice < len(SITES):
        selected_site = SITES[choice]
        base_domain = selected_site["base_domain"]
        initial_url = selected_site["initial_url"]
        output_subdir = selected_site["output_subdir"]
    else:
        custom_url = input("請輸入要爬取的網址: ")
        parsed = urlparse(custom_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        initial_url = custom_url
        filename = sanitize_filename(custom_url)
        output_subdir = os.path.splitext(filename)[0]
        selected_site = {"name": f"自訂網址: {custom_url}"}
        # 暫不寫入 config.py，待爬取成功後再加入
        custom_config_entry = f"""    {{
        'name': '自訂網址: {custom_url}',
        'base_domain': '{base_domain}',
        'initial_url': '{initial_url}',
        'output_subdir': '{output_subdir}'
    }},
"""

    # 根據選擇的網站設定專用的輸出子目錄
    current_output_dir = os.path.join(BASE_OUTPUT_DIR, output_subdir)
    # 若已存在則清除舊資料
    if os.path.exists(current_output_dir):
        shutil.rmtree(current_output_dir)
    os.makedirs(current_output_dir)
    
    print(f"\n將爬取網站: {selected_site['name']}")
    print(f"初始 URL: {initial_url}")
    print(f"結果將儲存於: {current_output_dir}\n")

    # --- 計算爬取範圍的路徑前綴 ---
    parsed_initial_url = urlparse(initial_url)
    initial_path = parsed_initial_url.path
    
    path_prefix_to_crawl = ""
    if not initial_path or initial_path == '/' or initial_path.endswith('/'):
        # 如果 initial_url 本身是根路徑或目錄
        path_prefix_to_crawl = initial_path
    else:
        # 如果 initial_url 是個具體檔案，取其所在目錄
        path_prefix_to_crawl = os.path.dirname(initial_path)

    # 確保前綴以 / 結尾且是絕對路徑形式 (相對於 domain)
    if not path_prefix_to_crawl.endswith('/'):
        path_prefix_to_crawl += '/'
    if not path_prefix_to_crawl.startswith('/'): # dirname 可能返回 . 或相對路徑
        path_prefix_to_crawl = '/' + path_prefix_to_crawl.lstrip('/')

    # 完整的爬取 URL 前綴
    crawl_scope_prefix = urljoin(base_domain, path_prefix_to_crawl)
    # 如果 base_domain 已經包含了路徑，urljoin 可能產生非預期結果，直接使用 base_domain + path_prefix_to_crawl
    # 但通常 base_domain 是純域名，initial_url 帶路徑。
    # 確保 crawl_scope_prefix 以 / 結尾
    if not crawl_scope_prefix.endswith('/'):
        crawl_scope_prefix += '/'
    
    print(f"將爬取所有以 \"{crawl_scope_prefix}\" 開頭的連結。")
    # --- END 計算爬取範圍的路徑前綴 ---

    # 直接讓使用者輸入爬取深度
    while True:
        try:
            choice_depth = int(input("請輸入要爬幾層 (0 表示單頁): "))
            if choice_depth >= 0:
                break
            print("輸入無效，請重新輸入。")
        except ValueError:
            print("輸入的不是數字，請重新輸入。")

    async with AsyncWebCrawler() as crawler:
        config_crawl = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=choice_depth, include_external=False),
            verbose=True,
            stream=True
        )
        # 計算成功爬取次數並顯示分層日誌
        success_count = 0
        current_depth = -1
        async for result in await crawler.arun(initial_url, config=config_crawl):
            depth = result.metadata.get('depth', 0)
            if depth != current_depth:
                current_depth = depth
                print(f"第{current_depth}層開始...")
            if hasattr(result, 'markdown') and result.markdown:
                success_count += 1
                filename = sanitize_filename(result.url)
                filepath = os.path.join(current_output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)
                print(f"Markdown 已儲存: {filepath}")
            else:
                print(f"警告: {result.url} 無 Markdown 或爬取失敗。")
        # 自訂網址且爬取成功才寫入 config.py
        if custom_config_entry and success_count > 0:
            with open('config.py', 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for idx in range(len(lines)-1, -1, -1):
                if lines[idx].strip() == ']':
                    insert_idx = idx
                    break
            lines.insert(insert_idx, custom_config_entry)
            with open('config.py', 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print("自訂網址已成功加入 config.py")

if __name__ == "__main__":
    asyncio.run(main_crawl()) 