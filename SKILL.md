---
name: "agent-router"
description: "AI 智能提示词增强器：根据用户输入关键词自动路由到 skills/<agent>/ 下的标准 Skill，注入 Skill 内容强化提示词。"
rules:
  # ── Python 编程 ──
  - keywords: ["Python", "程序", "代码", "脚本", "编程", "函数", "类", "模块", "PyQt", "Tkinter", "CustomTkinter", "pyinstaller", "nuitka"]
    agents: ["python-agent"]
  - keywords: ["AI", "GPT", "LLM", "大模型", "人工智能", "机器学习", "深度学习", "神经网络", "Agent"]
    agents: ["python-agent"]
  - keywords: ["Web", "前端", "HTML", "CSS", "JavaScript", "网站", "前端开发", "后端", "React", "Vue", "Node"]
    agents: ["python-agent"]
  - keywords: ["数据分析", "可视化", "图表", "统计", "数据挖掘", "数据科学", "pandas", "numpy"]
    agents: ["python-agent"]
  - keywords: ["数据库", "SQL", "MySQL", "PostgreSQL", "数据存储", "Redis", "MongoDB", "DuckDB", "SQLite"]
    agents: ["python-agent"]
  - keywords: ["API", "REST", "微服务", "接口", "后端", "FastAPI", "Django", "Flask", "OpenAPI"]
    agents: ["python-agent"]
  - keywords: ["Docker", "容器", "Kubernetes", "K8s", "部署", "运维", "CI", "CD"]
    agents: ["python-agent"]
  - keywords: ["测试", "单元测试", "自动化测试", "pytest", "测试用例"]
    agents: ["python-agent"]
  - keywords: ["安全", "加密", "认证", "权限", "网络安全", "漏洞"]
    agents: ["python-agent"]
  - keywords: ["Git", "版本控制", "代码管理", "协作", "GitHub", "提交"]
    agents: ["python-agent"]

  # ── 媒体内容创作 ──
  - keywords: ["短视频", "抖音", "快手", "TikTok", "视频号", "竖屏", "Vlog", "vlog"]
    agents: ["short-video-agent"]
  - keywords: [ "文案", "软文", "推文", "长篇", "博客", "blog"]
    agents: ["media-agent"]
  - keywords: ["标题", "题目", "开头", "选题", "吸睛"]
    agents: ["media-agent"]
  - keywords: ["小红书笔记", "种草文案", "小红书文案", "好物测评", "素人笔记", "小红书", "小红书标题", "RedNote", "朋友圈"]
    agents: ["xiaohongshu-agent"]
  - keywords: ["脚本", "口播", "剧本", "台词", "旁白", "解说", "视频脚本", "分镜", "运镜", "短视频剧本", "口播稿"]
    agents: ["short-video-agent"]
  - keywords: ["直播", "带货", "话术", "卖货", "直播间", "主播"]
    agents: ["media-agent", "short-video-agent"]
  - keywords: ["SEO", "搜索", "排名", "关键词优化", "搜索引擎", "收录"]
    agents: ["media-agent"]
  - keywords: ["公众号", "订阅号", "粉丝", "涨粉", "运营", "新媒体"]
    agents: ["media-agent"]
  - keywords: ["封面", "配图", "图片", "排版", "设计", "视觉", "配色"]
    agents: ["media-agent"]
  - keywords: ["故事", "叙事", "情感", "人设", "IP", "个人品牌"]
    agents: ["media-agent"]
  - keywords: ["热点", "追热点", "时事", "流量", "热搜"]
    agents: ["media-agent"]
  - keywords: ["知识科普", "教程", "教学视频", "干货", "解说", "旁白", "剧情", "搞笑", "段子", "创意", "挑战", "反转"]
    agents: ["short-video-agent"]

  # ── 医疗健康 ──
  - keywords: ["医疗", "健康", "医疗器械", "保健品", "药品", "医生", "患者", "疾病", "诊断", "治疗", "科普", "健康科普", "血压计", "血糖仪", "临床", "医学科普", "术后", "康复", "养生", "说明书", "用户手册", "患者教育", "临床试验", "学术", "论文"]
    agents: ["medical-agent"]

  # ── AI 生图 ──
  - keywords: ["生图", "图片生成", "AI绘画", "Midjourney", "MidJourney", "Stable Diffusion", "DALL-E", "提示词工程", "文生图", "AI 绘画", "AI绘画", "Prompt", "ComfyUI", "SD", "MJ", "negative prompt"]
    agents: ["ai-image-agent"]
  # ── 头条 → 媒体创作 + 头条-agent ──
  - keywords: ["头条", "今日头条"]
    agents: "头条-agent"]
  # ── 爆款热门 → 媒体创作 + 爆款写作Skill ──
  - keywords: ["爆款", "高点击率", "十万+", "自媒体写作", "热点"]
    agents: [ "爆款写作Skill-agent"]
  # ── 公众号 → 媒体创作 ──
  - keywords: ["公众号"]
    agents: ["公众号-agent"]
  # ── 阴间滤镜/暗黑元素 ──
  - keywords: ["阴间滤镜", "阴间风格", "阴森滤镜", "暗黑滤镜", "暗黑元素", "黑暗滤镜", "暗黑风格", "黑暗色调"]
    agents: ["阴间滤镜-agent"]
  # ── Agency Agents 中文版 ──
  - keywords: ["agent", "智能体", "专家角色", "agent team"]
    agents: ["agency-agents-zh"]
  # ── 默认 ──
  - default: true
    agents: ["python-agent", "media-agent"]
---

# Agent Router Skill

## 标准 Skill 系统说明

本程序遵循 **标准 Skill 规范**：

- 每个 Skill 是 `skills/<skill-name>/` 目录
- Skill 目录内含 `SKILL.md`（必须带 YAML frontmatter）
- frontmatter 至少包含：`name`、`description`
- Skill 内部可包含可选的 `rules:` 块做关键词 → 文件路由
- 没有 `rules:` 的"纯 Skill"，会直接用 SKILL.md 的正文作为提示词增强内容

## 路由工作流

1. 用户输入 → 关键词提取（jieba/正则）
2. 关键词匹配本文件 `rules:` → 路由到具体 Skill
3. 加载 `skills/<skill>/SKILL.md`，按其 `rules:` 选择子文件；若无 rules，直接注入正文
4. 将子文件内容追加到用户提示词，输出最终 Prompt

## 扩展新 Skill

在 `skills/` 下新建一个子目录，至少放一个 `SKILL.md`：

```markdown
---
name: my-skill
description: "这个 Skill 做什么，什么时候调用它。"
---

# My Skill

具体的角色定义、工作流程、指南、示例等...
```

如需更精细的路由，可以在 `rules:` 中声明：

```markdown
---
name: my-skill
description: "..."
rules:
  - keywords: ["关键词1", "关键词2"]
    files: ["子文件.md"]
  - default: true
    files: ["默认.md"]
---
```

然后在本文件追加一条 `agents: ["my-skill"]` 的路由规则。









