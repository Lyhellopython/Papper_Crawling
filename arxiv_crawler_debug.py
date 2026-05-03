import requests
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup

# ========== 配置项 ==========
# 爬取目标URL（arxiv CS新论文）
CRAWL_URL = "https://arxiv.org/list/cs/new"
# 重试次数
RETRY_TIMES = 3
# 每次请求延迟（秒）
DELAY = 1
# 保存爬取结果的文件
RESULT_FILE = "debug_papers.json"
# 保存日志的文件
LOG_FILE = "crawler_debug.log"


# ========== 日志函数（控制台+文件双输出） ==========
def log(content):
    """打印日志并写入文件"""
    log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}"
    # 打印到控制台
    print(log_str)
    # 写入日志文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_str + "\n")


# ========== 核心爬取函数 ==========
# ========== 核心爬取函数（适配新结构） ==========
def crawl_arxiv_cs_papers():
    """爬取arxiv CS新论文（适配id="articles"的新结构）"""
    # 初始化会话和请求头（模拟真实浏览器，避免反爬）
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    # 1. 发起请求（带重试）
    log("开始请求arxiv页面...")
    html = None
    for i in range(RETRY_TIMES):
        try:
            response = session.get(CRAWL_URL, headers=headers, timeout=15)
            response.raise_for_status()  # 抛出HTTP错误（4xx/5xx）
            html = response.text
            log(f"第{i + 1}次请求成功，状态码：{response.status_code}")

            # 保存原始HTML到本地，方便调试
            with open("arxiv_raw.html", "w", encoding="utf-8") as f:
                f.write(html)
            log("已保存原始HTML到 arxiv_raw.html")
            break
        except requests.exceptions.HTTPError as e:
            log(f"第{i + 1}次请求失败（HTTP错误）：{e.response.status_code} - {e.response.text[:100]}")
        except requests.exceptions.ConnectionError:
            log(f"第{i + 1}次请求失败（连接错误）：网络不通或目标服务器不可达")
        except Exception as e:
            log(f"第{i + 1}次请求失败（其他错误）：{str(e)}")
        time.sleep(2 ** (i + 1))  # 指数退避（重试间隔翻倍）

    if not html:
        log("所有重试均失败，爬取终止")
        return []

    # 2. 解析HTML（适配id="articles"的新结构）
    log("开始解析HTML...")
    soup = BeautifulSoup(html, "html.parser")
    # 关键修改：用id="articles"找到论文列表父容器
    paper_list_container = soup.find("dl", id="articles")
    if not paper_list_container:
        log("❌ 未找到论文列表父容器（id=articles），页面结构可能已变化！")
        log(f"页面标题：{soup.title.text if soup.title else '无'}")
        log(f"页面前500字符：{html[:500]}")
        return []

    # 提取所有论文条目（每个dt对应一篇论文）
    paper_entries = paper_list_container.find_all("dt")
    log(f"找到 {len(paper_entries)} 个论文条目")
    if len(paper_entries) == 0:
        log("⚠️ 未找到任何论文条目，可能当日无新论文或选择器错误")
        return []

    # 3. 遍历解析每篇论文
    papers = []
    today = datetime.now().date()
    for idx, entry in enumerate(paper_entries):
        try:
            log(f"解析第 {idx + 1} 篇论文...")
            # 找到对应的dd标签（包含标题/作者/摘要）
            dd_elem = entry.find_next("dd")
            if not dd_elem:
                log(f"第 {idx + 1} 篇论文：未找到dd标签，跳过")
                continue

            # 解析核心字段（带容错，class和之前一致）
            # 标题
            title_elem = dd_elem.find("div", class_="list-title mathjax")
            title = title_elem.text.strip().replace("Title:", "").strip() if title_elem else "无标题"
            # 作者
            authors_elem = dd_elem.find("div", class_="list-authors")
            authors = authors_elem.text.strip().replace("Authors:", "").strip() if authors_elem else "未知作者"
            # 摘要
            abstract_elem = dd_elem.find("div", class_="mathjax")
            abstract = abstract_elem.text.strip().replace("Abstract:", "").strip() if abstract_elem else "无摘要"
            # 论文链接（从dt里的a标签取）
            link_elem = entry.find("a", href=True)
            paper_url = "https://arxiv.org" + link_elem["href"] if link_elem else ""
            # DOI（部分论文无）
            doi_elem = dd_elem.find("div", class_="list-doi")
            doi = doi_elem.text.strip().replace("DOI:", "").strip() if doi_elem else ""

            # 构造论文数据
            paper_data = {
                "id": idx + 1,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": paper_url,
                "doi": doi,
                "publish_date": today.strftime("%Y-%m-%d"),
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            papers.append(paper_data)
            log(f"✅ 第 {idx + 1} 篇论文解析成功：{title[:50]}...")

        except Exception as e:
            log(f"❌ 第 {idx + 1} 篇论文解析失败：{str(e)}")
            continue

    # 4. 保存结果到JSON文件
    log(f"解析完成，共成功解析 {len(papers)} 篇论文")
    if papers:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        log(f"✅ 爬取结果已保存到 {RESULT_FILE}")
    else:
        log("⚠️ 未解析到任何有效论文")

    return papers

# ========== 运行调试 ==========
if __name__ == "__main__":
    # 清空旧日志（可选）
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")

    # 执行爬取
    log("========== 开始arxiv爬取调试 ==========")
    result = crawl_arxiv_cs_papers()

    # 打印最终结果
    log("========== 爬取调试结束 ==========")
    log(f"最终爬取到 {len(result)} 篇有效论文")
    if result:
        log("前2篇论文预览：")
        for i in range(min(2, len(result))):
            log(f"论文{i + 1}标题：{result[i]['title']}")
            log(f"论文{i + 1}作者：{result[i]['authors']}")