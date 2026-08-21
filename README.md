# 培训管理系统 - 智能推荐引擎

基于 GitHub 开源推荐系统项目（Surprise、recommender-systems 等）学习实现的企业培训智能推荐功能。

## 功能特性

### 5 种推荐算法

| 算法 | 说明 | 适用场景 |
|------|------|----------|
| **混合推荐** | 加权融合 User-CF + Item-CF + Content + Popular | 默认推荐，效果最优 |
| **用户协同过滤 (User-CF)** | 找到兴趣相似的学员，推荐他们学过的课程 | 有一定学习记录的用户 |
| **物品协同过滤 (Item-CF)** | 基于已学课程，推荐内容相似的课程 | 有明确学习方向的用户 |
| **基于内容推荐** | 根据课程分类/标签/难度匹配用户偏好 | 兴趣明确的用户 |
| **热门推荐** | 基于学习人数和评分推荐全局热门课程 | 新用户冷启动 |

### 核心能力

- **冷启动处理**：新用户自动切换为内容推荐 + 热门推荐策略
- **隐式反馈建模**：综合学习进度、评分、收藏/分享等行为计算偏好分数
- **用户画像**：自动从学习历史中提取偏好分类和兴趣标签
- **实时更新**：记录学习行为后推荐结果即时刷新
- **推荐可解释**：每个推荐都附带理由（"相似学员在学"、"与已学课程相似"等）
- **算法对比**：一键对比 5 种算法的推荐结果差异
- **热门惩罚**：Item-CF 中对热门课程/活跃用户做惩罚，提升推荐多样性

## 技术栈

- **后端**：Python 3 + Flask
- **前端**：原生 HTML/CSS/JavaScript（零依赖）
- **算法**：纯 Python 实现（余弦相似度、改进余弦相似度、min-max 归一化）

## 快速开始

```bash
# 安装依赖
pip install flask

# 启动服务
python app.py

# 访问 http://localhost:5000
```

## 项目结构

```
training-recommender/
├── app.py              # Flask 应用 & REST API
├── recommender.py      # 推荐引擎核心（5种算法实现）
├── data.py             # 模拟数据（24门课程、10位学员、学习行为）
├── templates/
│   └── index.html      # 前端页面
└── static/
    ├── style.css       # 样式
    └── app.js          # 前端交互逻辑
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/users` | GET | 获取所有学员 |
| `/api/courses` | GET | 获取所有课程 |
| `/api/recommend/<user_id>` | GET | 获取推荐结果（参数: algorithm, top_n） |
| `/api/profile/<user_id>` | GET | 获取学员画像和已学课程 |
| `/api/interact` | POST | 记录学习行为（实时更新推荐） |
| `/api/compare/<user_id>` | GET | 对比所有算法推荐结果 |

## 算法原理

### 1. 协同过滤 (Collaborative Filtering)

参考 GitHub 开源项目 Surprise 的协同过滤思想：

- **User-CF**：计算用户间余弦相似度，取 Top-K 相似用户的评分加权平均
- **Item-CF**：计算课程间相似度（改进余弦相似度 + 热门惩罚），基于用户已学课程推荐

### 2. 基于内容推荐 (Content-Based)

- 课程特征：分类（one-hot）+ 标签（权重 0.8）+ 难度（one-hot）
- 用户偏好：从学习历史加权聚合，按行为强度归一化
- 相似度：用户偏好向量与课程特征向量的余弦相似度

### 3. 混合推荐 (Hybrid)

对各算法分数做 min-max 归一化后加权融合：
- 正常用户：User-CF 30% + Item-CF 30% + Content 25% + Popular 15%
- 冷启动用户：Content 40% + Popular 60%

## 学习来源

本项目参考了以下 GitHub 开源项目：

- [NicolasHug/Surprise](https://github.com/NicolasHug/Surprise) - Python 推荐系统库
- [zhistaredu/StarTraining](https://github.com/zhistaredu/StarTraining) - 企业培训系统
- [roncoo/roncoo-education](https://github.com/roncoo/roncoo-education) - 在线教育系统
