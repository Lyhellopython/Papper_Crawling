import requests
import time
import os
from datetime import datetime, date
from bs4 import BeautifulSoup
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

# 导入JSON存储工具函数
from .json_storage import (
    init_json_file,
    get_all_papers,
    get_papers_by_date_and_keyword,
    get_papers_by_date_keyword_source,
    add_papers_batch,
    toggle_paper_collection,
    get_collected_papers,
    get_paper_by_identifier
)

# ========== 通用爬虫配置 ==========
COMMON_CONFIG = {
    "delay": 1,
    "retry_times": 3,
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
}

# 日志文件路径
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "crawl_logs.log")


# ========== 日志函数 ==========
def write_log(content):
    """写入日志到文件"""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            log_content = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {content}\n"
            f.write(log_content)
    except Exception as e:
        print(f"日志写入失败：{str(e)}")


def read_logs():
    """读取日志最后100行"""
    if not os.path.exists(LOG_PATH):
        return ["日志文件尚未生成"]
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-100:] if len(lines) > 100 else lines
    except Exception as e:
        return [f"日志读取失败：{str(e)}"]


# ========== 各网站爬虫实现（可扩展） ==========
def crawl_arxiv(keyword=""):
    """爬取arXiv CS领域论文（适配最新结构）"""
    url = f"https://arxiv.org/list/cs/new"
    session = requests.Session()
    html_content = None

    # 1. 发起请求
    write_log(f"开始爬取arXiv：{url}")
    for retry_idx in range(COMMON_CONFIG["retry_times"]):
        try:
            response = session.get(
                url,
                headers=COMMON_CONFIG["headers"],
                timeout=15,
                verify=True
            )
            response.raise_for_status()
            html_content = response.text
            write_log(f"arXiv请求成功（第{retry_idx + 1}次）")
            break
        except Exception as e:
            write_log(f"arXiv请求失败（第{retry_idx + 1}次）：{str(e)}")
            time.sleep(2 ** (retry_idx + 1))

    if not html_content:
        write_log("arXiv爬取失败：所有请求重试均失败")
        return []

    # 2. 解析页面
    soup = BeautifulSoup(html_content, "html.parser")
    paper_list_dl = soup.find("dl", id="articles")
    if not paper_list_dl:
        write_log("arXiv爬取失败：未找到论文列表容器")
        return []

    paper_dt_list = paper_list_dl.find_all("dt")
    write_log(f"arXiv找到 {len(paper_dt_list)} 个论文条目")
    parsed_papers = []
    current_date = date.today().strftime("%Y-%m-%d")

    for idx, dt_elem in enumerate(paper_dt_list):
        try:
            dd_elem = dt_elem.find_next("dd")
            if not dd_elem:
                continue

            # 解析字段
            title_elem = dd_elem.find("div", class_="list-title mathjax")
            title = title_elem.text.strip().replace("Title:", "").strip() if title_elem else "无标题"

            authors_elem = dd_elem.find("div", class_="list-authors")
            authors = authors_elem.text.strip().replace("Authors:", "").strip() if authors_elem else "未知作者"

            abstract_elem = dd_elem.find("div", class_="list-abstract mathjax")
            abstract = abstract_elem.text.strip().replace("Abstract:", "").strip() if abstract_elem else "无摘要"

            link_elem = dt_elem.find("a", href=True)
            url = "https://arxiv.org" + link_elem["href"] if link_elem else ""

            doi_elem = dd_elem.find("div", class_="list-doi")
            doi = doi_elem.text.strip().replace("DOI:", "").strip() if doi_elem else ""

            # 构造通用格式论文数据
            paper = {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": url,
                "doi": doi,
                "publish_date": current_date,
                "source": "arxiv",  # 标记来源
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_collected": False
            }
            parsed_papers.append(paper)
            write_log(f"arXiv解析第{idx + 1}篇论文成功：{title[:50]}")
        except Exception as e:
            write_log(f"arXiv解析第{idx + 1}篇论文失败：{str(e)}")
            continue

    write_log(f"arXiv爬取完成：共解析 {len(parsed_papers)} 篇有效论文")
    return parsed_papers


def crawl_ieee(keyword=""):
    """爬取IEEE Xplore论文（示例，需根据实际页面调整）"""
    # 注意：IEEE需要处理反爬/分页，此处为简化示例
    url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={keyword}"
    session = requests.Session()
    html_content = None

    write_log(f"开始爬取IEEE Xplore：{url}")
    for retry_idx in range(COMMON_CONFIG["retry_times"]):
        try:
            response = session.get(
                url,
                headers=COMMON_CONFIG["headers"],
                timeout=15,
                verify=True
            )
            response.raise_for_status()
            html_content = response.text
            write_log(f"IEEE请求成功（第{retry_idx + 1}次）")
            break
        except Exception as e:
            write_log(f"IEEE请求失败（第{retry_idx + 1}次）：{str(e)}")
            time.sleep(2 ** (retry_idx + 1))

    if not html_content:
        write_log("IEEE爬取失败：所有请求重试均失败")
        return []

    # 2. 解析页面（需根据IEEE实际HTML结构调整，此处为示例）
    soup = BeautifulSoup(html_content, "html.parser")
    paper_items = soup.find_all("div", class_="List-results-items")  # 示例class，需替换为实际
    parsed_papers = []
    current_date = date.today().strftime("%Y-%m-%d")

    for idx, item in enumerate(paper_items):
        try:
            # 解析IEEE论文字段（示例，需根据实际调整）
            title_elem = item.find("h2", class_="title")
            title = title_elem.text.strip() if title_elem else "无标题"

            authors_elem = item.find("div", class_="authors")
            authors = authors_elem.text.strip() if authors_elem else "未知作者"

            abstract_elem = item.find("div", class_="abstract")
            abstract = abstract_elem.text.strip() if abstract_elem else "无摘要"

            link_elem = item.find("a", href=True)
            url = "https://ieeexplore.ieee.org" + link_elem["href"] if link_elem else ""

            doi_elem = item.find("span", class_="doi")
            doi = doi_elem.text.strip().replace("DOI: ", "") if doi_elem else ""

            # 构造通用格式
            paper = {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": url,
                "doi": doi,
                "publish_date": current_date,
                "source": "ieee",  # 标记来源
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_collected": False
            }
            parsed_papers.append(paper)
            write_log(f"IEEE解析第{idx + 1}篇论文成功：{title[:50]}")
        except Exception as e:
            write_log(f"IEEE解析第{idx + 1}篇论文失败：{str(e)}")
            continue

    write_log(f"IEEE爬取完成：共解析 {len(parsed_papers)} 篇有效论文")
    return parsed_papers


# ========== 统一爬取入口 ==========
def crawl_papers(source, keyword=""):
    """
    统一爬取入口
    :param source: 爬取来源（arxiv/ieee/all）
    :param keyword: 爬取关键词（部分网站支持）
    :return: 爬取的论文列表
    """
    all_crawled_papers = []
    # 爬取指定来源
    if source == "arxiv" or source == "all":
        arxiv_papers = crawl_arxiv(keyword)
        all_crawled_papers.extend(arxiv_papers)
    if source == "ieee" or source == "all":
        ieee_papers = crawl_ieee(keyword)
        all_crawled_papers.extend(ieee_papers)
    # 可添加更多来源（springer/sciencedirect等）
    return all_crawled_papers


# ========== Django视图函数 ==========
def index(request):
    """首页：支持选择爬取来源"""
    init_json_file()
    all_papers = get_all_papers()
    total_paper_count = len(all_papers)
    today = date.today().strftime("%Y-%m-%d")
    today_paper_count = len([p for p in all_papers if p.get("publish_date") == today])

    # 处理爬取请求
    if request.method == "POST" and request.POST.get("action") == "crawl":
        source = request.POST.get("source", "arxiv")  # 爬取来源
        keyword = request.POST.get("crawl_keyword", "").strip()  # 爬取关键词

        # 执行爬取
        crawled_papers = crawl_papers(source, keyword)
        # 批量添加（自动去重）
        added_count = add_papers_batch(crawled_papers)

        # 提示用户
        messages.success(
            request,
            f"爬取完成！共获取 {len(crawled_papers)} 篇论文，新增 {added_count} 篇（已自动去重）"
        )
        return redirect("index")

    context = {
        "total_papers": total_paper_count,
        "today_papers": today_paper_count,
        "today": today,
        "sources": ["arxiv", "ieee", "all"]  # 可选爬取来源
    }
    return render(request, "paper_app/index.html", context)


def paper_list(request):
    """论文列表：支持日期+关键词+来源筛选"""
    init_json_file()
    # 获取筛选参数
    filter_date = request.GET.get("date", "").strip()
    filter_keyword = request.GET.get("keyword", "").strip()
    filter_source = request.GET.get("source", "").strip()  # 新增来源筛选

    # 组合筛选
    papers = get_papers_by_date_keyword_source(filter_date, filter_keyword, filter_source)

    context = {
        "papers": papers,
        "selected_date": filter_date,
        "input_keyword": filter_keyword,
        "selected_source": filter_source,
        "all_sources": ["arxiv", "ieee"]  # 所有可选来源
    }
    return render(request, "paper_app/papers.html", context)


def collect_paper(request):
    """收藏/取消收藏论文"""
    if request.method == "POST":
        paper_identifier = request.POST.get("paper_id", "").strip()
        is_collected = request.POST.get("is_collected", "false").lower() == "true"
        success = toggle_paper_collection(paper_identifier, is_collected)
        return JsonResponse({
            "success": success,
            "message": "收藏成功" if is_collected else "取消收藏成功"
        })
    return JsonResponse({"success": False, "message": "仅支持POST请求"}, status=405)


def my_collections(request):
    """我的收藏：汇总所有来源的收藏论文"""
    init_json_file()
    collected_papers = get_collected_papers()
    context = {
        "papers": collected_papers,
        "page_title": "我的收藏"
    }
    return render(request, "paper_app/my_collections.html", context)


def logs(request):
    """爬取日志"""
    log_content = read_logs()
    context = {
        "logs": log_content
    }
    return render(request, "paper_app/logs.html", context)