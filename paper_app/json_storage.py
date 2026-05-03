import json
import os
from datetime import datetime

# JSON文件路径：项目根目录下的papers.json
JSON_STORAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "papers.json")


def init_json_file():
    """初始化JSON存储文件（不存在则创建空列表）"""
    if not os.path.exists(JSON_STORAGE_PATH):
        try:
            with open(JSON_STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"初始化JSON文件失败：{str(e)}")


def get_all_papers():
    """读取所有论文数据（所有来源汇总）"""
    init_json_file()
    try:
        with open(JSON_STORAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # JSON文件损坏，重置为空列表
        with open(JSON_STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    except Exception as e:
        print(f"读取JSON文件失败：{str(e)}")
        return []


def get_papers_by_date(target_date):
    """按日期筛选论文（所有来源）"""
    all_papers = get_all_papers()
    return [p for p in all_papers if p.get("publish_date") == target_date]


def get_papers_by_source(source):
    """按来源筛选论文（如arxiv/ieee/springer）"""
    all_papers = get_all_papers()
    return [p for p in all_papers if p.get("source") == source]


def get_papers_by_keyword(keyword):
    """按关键词筛选论文（标题/摘要，所有来源）"""
    if not keyword or keyword.strip() == "":
        return get_all_papers()

    keyword_lower = keyword.strip().lower()
    all_papers = get_all_papers()
    filtered_papers = []
    for paper in all_papers:
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        if keyword_lower in title or keyword_lower in abstract:
            filtered_papers.append(paper)
    return filtered_papers


def get_papers_by_date_and_keyword(target_date, keyword):
    """组合筛选：日期 + 关键词（所有来源）"""
    keyword_papers = get_papers_by_keyword(keyword)
    if not target_date or target_date.strip() == "":
        return keyword_papers
    return [p for p in keyword_papers if p.get("publish_date") == target_date.strip()]


def get_papers_by_date_keyword_source(target_date, keyword, source):
    """组合筛选：日期 + 关键词 + 来源"""
    # 先筛选关键词和日期
    date_keyword_papers = get_papers_by_date_and_keyword(target_date, keyword)
    # 再筛选来源（source为空则不限制）
    if not source or source.strip() == "":
        return date_keyword_papers
    return [p for p in date_keyword_papers if p.get("source") == source.strip()]


def is_paper_exist(paper):
    """检查论文是否已存在（优先DOI，无则标题+来源去重）"""
    all_papers = get_all_papers()
    # 有DOI则按DOI去重（跨来源唯一）
    if paper.get("doi") and paper["doi"].strip():
        return any(p.get("doi") == paper["doi"] for p in all_papers)
    # 无DOI则按标题+来源去重（避免同一来源重复爬取）
    else:
        return any(
            p.get("title") == paper["title"] and p.get("source") == paper["source"]
            for p in all_papers
        )


def add_paper(paper):
    """添加单篇论文（自动去重），返回是否添加成功"""
    if is_paper_exist(paper):
        return False

    try:
        all_papers = get_all_papers()
        all_papers.append(paper)
        with open(JSON_STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(all_papers, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"添加论文到JSON失败：{str(e)}")
        return False


def add_papers_batch(papers):
    """批量添加论文（自动去重），返回添加成功的数量"""
    added_count = 0
    for paper in papers:
        if add_paper(paper):
            added_count += 1
    return added_count


def toggle_paper_collection(paper_identifier, is_collected):
    """切换论文收藏状态（支持多来源）"""
    init_json_file()
    try:
        all_papers = get_all_papers()
        for paper in all_papers:
            paper_id = paper.get("doi") or paper.get("title") + "_" + paper.get("source")
            if paper_id == paper_identifier:
                paper["is_collected"] = is_collected
                with open(JSON_STORAGE_PATH, "w", encoding="utf-8") as f:
                    json.dump(all_papers, f, ensure_ascii=False, indent=2)
                return True
        return False
    except Exception as e:
        print(f"切换收藏状态失败：{str(e)}")
        return False


def get_collected_papers():
    """获取所有已收藏的论文（所有来源）"""
    all_papers = get_all_papers()
    return [p for p in all_papers if p.get("is_collected", False) is True]


def get_paper_by_identifier(identifier):
    """通过唯一标识获取单篇论文（支持多来源）"""
    all_papers = get_all_papers()
    for paper in all_papers:
        paper_id = paper.get("doi") or paper.get("title") + "_" + paper.get("source")
        if paper_id == identifier:
            return paper
    return None