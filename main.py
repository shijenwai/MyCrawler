import asyncio
import re
import os
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler
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

    choice = -1
    while True:
        try:
            choice_input = input(f"請輸入選項編號 (1-{len(SITES)}): ")
            choice = int(choice_input) - 1
            if 0 <= choice < len(SITES):
                break
            else:
                print("輸入無效，請重新輸入。")
        except ValueError:
            print("輸入的不是數字，請重新輸入。")

    selected_site = SITES[choice]
    base_domain = selected_site["base_domain"]
    initial_url = selected_site["initial_url"]
    output_subdir = selected_site["output_subdir"]

    # 根據選擇的網站設定專用的輸出子目錄
    current_output_dir = os.path.join(BASE_OUTPUT_DIR, output_subdir)
    if not os.path.exists(current_output_dir):
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

    urls_to_crawl_initially = {initial_url}
    all_found_urls = set() # 用於收集所有從 Markdown 中找到的合格 URL
    processed_urls = set() # 追蹤已處理的 URL，避免重複爬取

    async with AsyncWebCrawler() as crawler:
        # 第一輪：爬取初始 URL
        for url in list(urls_to_crawl_initially): # 使用 list 複製，因集合可能在迭代中修改
            if url in processed_urls:
                continue
            
            print(f"開始爬取: {url}")
            processed_urls.add(url)
            try:
                result = await crawler.arun(url=url)
                if result and hasattr(result, 'markdown') and result.markdown:
                    filename = sanitize_filename(url) # 這裡的 sanitize_filename 可能需要感知 crawl_scope_prefix 來產生更簡潔的檔名
                    filepath = os.path.join(current_output_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(result.markdown)
                    print(f"Markdown 內容已儲存到: {filepath}")

                    # 從已儲存的 Markdown 內容中提取連結
                    # 更新正則，使其更通用地捕獲以 base_domain 開頭的連結
                    pattern = r'\(' + f'({re.escape(base_domain)}[^)\s]*)' + r'\)'
                    markdown_links = re.findall(pattern, result.markdown)

                    for md_link_match in markdown_links:
                        full_url = md_link_match.strip()
                        # 移除 URL fragment
                        full_url = urljoin(full_url, urlparse(full_url).path)


                        if full_url not in processed_urls and full_url not in all_found_urls:
                            # 確保連結是我們感興趣的域名和定義的路徑前綴下的
                            if full_url.startswith(crawl_scope_prefix):
                                print(f"從 Markdown 找到合格連結: {full_url}")
                                all_found_urls.add(full_url)
                            # else:
                            #     print(f"忽略連結 (不在範圍 {crawl_scope_prefix}): {full_url}")
                else:
                    print(f"警告: 頁面 {url} 未獲取到 Markdown 內容或爬取失敗。")
            except Exception as e:
                print(f"爬取頁面 {url} 過程中發生錯誤: {e}")

        # 第二輪：爬取從 Markdown 中找到的新連結
        urls_for_second_pass = list(all_found_urls - processed_urls) # 只爬取尚未處理的新連結

        if urls_for_second_pass:
            print(f"\n將開始爬取 {len(urls_for_second_pass)} 個從 Markdown 找到的新頁面...")
        
        for i, url in enumerate(urls_for_second_pass):
            if url in processed_urls:
                continue

            print(f"\n開始爬取 (第二輪: {i+1}/{len(urls_for_second_pass)}): {url}")
            processed_urls.add(url)
            try:
                result = await crawler.arun(url=url)
                if result and hasattr(result, 'markdown') and result.markdown:
                    filename = sanitize_filename(url) # 同上，檔名生成可優化
                    filepath = os.path.join(current_output_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(result.markdown)
                    print(f"Markdown 內容已儲存到: {filepath}")
                    # 理論上這裡也可以再從新爬取的頁面提取連結，形成遞歸爬取
                    # 但為了簡單起見，目前只做兩層 (初始層 + 從初始層 Markdown 提取的連結)
                else:
                    print(f"警告: 頁面 {url} 未獲取到 Markdown 內容或爬取失敗。")
            except Exception as e:
                print(f"爬取頁面 {url} 過程中發生錯誤: {e}")

    if not all_found_urls and len(processed_urls) <= len(urls_to_crawl_initially):
         print(f"\n爬取完成。只處理了初始頁面，未從其 Markdown 中找到新的合格連結。檔案已儲存到 {current_output_dir} 資料夾。")
    elif not urls_for_second_pass and all_found_urls:
        print(f"\n爬取完成。處理了初始頁面並從其 Markdown 中找到連結 ({len(all_found_urls)} 個)，但所有這些連結都已在第一輪處理或不符合進一步爬取條件。檔案已儲存到 {current_output_dir} 資料夾。")
    else:
        print(f"\n爬取完成 ({len(processed_urls)} 個頁面)。Markdown 檔案已儲存到 {current_output_dir} 資料夾。")

if __name__ == "__main__":
    asyncio.run(main_crawl()) 