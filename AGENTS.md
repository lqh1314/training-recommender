# AGENTS.md - 培训管理系统 AI 协作规则

> 本文件指导 AI 在本项目中的自动行为。AI 读取本文件后应自动执行，无需用户手动指定技能。

## 项目概述

培训管理系统（training-recommender），基于 Flask + 飞书多维表格的 AI 智能推荐培训平台。
- 线上地址：https://saasuniversity.feishuapp.com/app/app_17c3jc9ap9m
- 妙搭编辑器：https://miaoda.feishu.cn/app/app_17c3jc9ap9m
- GitHub：https://github.com/lqh1314/training-recommender
- 本地启动：`python3 app.py`（端口 5000）
- 测试命令：`python3 -m pytest tests/ -v`

## 技术栈

- Python 3.12+, Flask >= 2.3.0
- 推荐算法：SVD 矩阵分解、用户/物品协同过滤、内容推荐、热门推荐、AI 混合推荐
- 数据源：飞书多维表格（优先）/ 本地 data.py（回退）
- 前端：Jinja2 模板（templates/index.html）

## 自动技能调用规则

以下技能在匹配场景时**必须自动加载并使用**，无需用户手动 `/` 指定：

| 触发场景 | 自动使用的技能 | 说明 |
|----------|---------------|------|
| 代码阅读、架构理解、调用链分析 | `doubao-coding-analyze-codebase` | 只读分析，不修改代码 |
| Bug 定位、报错修复、测试失败 | `doubao-coding-diagnose-and-fix-bugs` | 原因级修复，不绕过 |
| 新功能开发、API 端点新增 | `doubao-coding-develop-backend-features` | 后端功能开发 |
| 前端页面/交互修改 | `doubao-coding-develop-frontend-features` | 前端功能开发 |
| 编写/补充/修复测试 | `doubao-coding-develop-unit-tests` | 沿用 pytest 风格 |
| GitHub 操作（推送/PR/Issue） | `github-remote` | 先 tool_search 获取 schema |
| 定时任务/周期同步/提醒 | `doubao-cron-scheduler` | 先 get_current_time 锚定时间 |
| 多维表格/飞书生态操作 | `lark-base` / `lark-sheets` 等 | 按需加载 |

## 标准工作流（每次代码变更自动执行）

```
1. 分析需求 → 自动加载 doubao-coding-analyze-codebase
2. 编码实现 → 直接编辑文件（Edit/Write）
3. 编写测试 → 自动加载 doubao-coding-develop-unit-tests
4. 运行测试 → python3 -m pytest tests/ -v，必须全部通过
5. 修复失败 → 自动加载 doubao-coding-diagnose-and-fix-bugs
6. 推送到 GitHub → 自动加载 github-remote，push_files 到 main 分支
7. 汇报结果 → 列出变更文件、测试结果、commit 信息
```

## 代码规范

- Python 代码使用 4 空格缩进，中文注释
- 所有 API 端点必须有输入校验和错误处理
- 飞书多维表格字段名使用中文（如"课程名称"、"审批状态"）
- 新增模块必须在 `DataProvider.TABLE_NAMES` 注册表名
- 本地数据使用 `copy.deepcopy` 避免全局污染
- `json.dumps` 必须设置 `ensure_ascii=False`

## 测试规范

- 测试文件放在 `tests/` 目录，命名 `test_*.py`
- 每个新功能必须配套单元测试
- 测试间必须隔离，使用 `setUp` 初始化独立 DataProvider
- Mock 飞书 API 时手动设置 `client._table_ids`，避免多次调用 `_request` 返回值冲突
- 运行全部测试：`python3 -m pytest tests/ -v`

## 多维表格同步

- 定时同步脚本：`sync_bitable.py`
- 同步间隔：每 30 分钟（cron: `*/30 * * * *`）
- 同步模块：课程、讲师、报名审批、公告（4 个核心模块）
- 环境变量：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`BITABLE_APP_TOKEN`
- 未配置凭证时自动回退本地数据，不报错
- 同步状态文件：`.sync_state.json`，日志：`sync.log`

## 关键文件

| 文件 | 职责 |
|------|------|
| `app.py` | Flask 应用，所有 API 端点 |
| `recommender.py` | 推荐引擎（6 种算法 + should_recommend 门控） |
| `ai_engine.py` | AI 对话、学习路径、推荐解释 |
| `bitable_client.py` | 飞书多维表格客户端 + DataProvider（6 模块 CRUD） |
| `data.py` | 本地默认数据（24 课程 / 10 学员 / 48 交互） |
| `sync_bitable.py` | 定时同步脚本 |
| `tests/test_system.py` | 系统测试（推荐引擎 + AI + API） |
| `tests/test_crud.py` | CRUD 测试（4 模块 + 同步 + API） |

## AI 推荐门控规则

`should_recommend(user_id, course_id)` 五维门控，任一不通过则不推荐：
1. 已学课程不重复推荐（进度 >= 80%）
2. 难度匹配（新人不推荐高级课程）
3. 岗位/部门相关性
4. 课程类别多样性
5. 学习路径阶段匹配

## 注意事项

- 不要把密码、token、cookie 写入代码或 commit
- 推送前运行 `run_secret_scanning` 检查密钥泄露
- Flask 服务运行在 0.0.0.0:5000，debug=False
- 修改 app.py 后需重启 Flask 服务才能生效
