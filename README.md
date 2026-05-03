# Paper Crawler - 学术论文爬取与管理系统

一个基于 Django 的学术论文爬取与管理系统，支持从多个学术网站（arXiv、IEEE Xplore）自动爬取最新论文，并提供 Web 界面进行浏览、筛选和收藏。

## 功能特性

- **多源爬取**：支持 arXiv（CS 领域新论文）和 IEEE Xplore，可单独或全量爬取
- **智能去重**：基于 DOI 或标题+来源自动去重，避免重复存储
- **多维度筛选**：按日期、关键词、来源组合筛选论文
- **论文收藏**：支持收藏/取消收藏感兴趣的论文
- **爬取日志**：实时查看爬取过程日志，方便排查问题
- **JSON 存储**：使用 JSON 文件存储，无需配置数据库，开箱即用

## 技术栈

- **后端**：Python 3.x / Django 6.0
- **爬虫**：Requests + BeautifulSoup4
- **数据存储**：JSON 文件
- **前端**：Django Templates

## 项目结构

```
DjangoProject/
├── DjangoProject/          # 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── paper_app/              # 主应用
│   ├── views.py            # 视图函数（爬虫逻辑 + 页面渲染）
│   ├── models.py           # 数据模型
│   ├── urls.py             # 路由配置
│   ├── json_storage.py     # JSON 存储工具函数
│   ├── admin.py
│   └── templates/
│       └── paper_app/
│           ├── base.html           # 基础模板
│           ├── index.html          # 首页（爬取入口）
│           ├── papers.html         # 论文列表页
│           ├── my_collections.html # 我的收藏页
│           └── logs.html           # 日志查看页
├── arxiv_crawler_debug.py  # arXiv 爬虫独立调试脚本
├── papers.json             # 论文数据存储文件
├── crawl_logs.log          # 爬取日志文件
└── manage.py               # Django 管理入口
```

## 快速开始

### 1. 安装依赖

```bash
pip install django requests beautifulsoup4
```

### 2. 启动服务

```bash
python manage.py runserver
```

### 3. 访问页面

打开浏览器访问

- 首页：选择爬取来源并开始爬取
- 论文列表：`/papers/` - 按日期、关键词、来源筛选论文
- 我的收藏：`/my-collections/` - 查看已收藏论文
- 爬取日志：`/logs/` - 查看爬取过程日志

## 扩展说明

### 添加新的爬取源

在 `paper_app/views.py` 中添加新的爬虫函数（参考 `crawl_arxiv` 和 `crawl_ieee`），然后在 `crawl_papers` 函数中注册即可。每个爬虫返回统一格式的论文数据：

```python
{
    "title": "...",
    "authors": "...",
    "abstract": "...",
    "url": "...",
    "doi": "...",
    "publish_date": "YYYY-MM-DD",
    "source": "来源标识",
    "crawl_time": "YYYY-MM-DD HH:MM:SS",
    "is_collected": false
}
```

### 切换为数据库存储

编辑 `DjangoProject/settings.py`，取消数据库配置的注释，并创建相应的 Model 替换 `json_storage.py` 中的存储逻辑。

## 注意事项

- 爬虫设置了请求延迟和重试机制，请合理使用，避免对目标网站造成压力
- IEEE Xplore 页面结构可能变化，爬虫解析逻辑需根据实际页面调整
- JSON 文件存储适用于小规模数据，数据量大时建议迁移至数据库
