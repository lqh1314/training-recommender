# 培训管理系统 - AI 智能推荐引擎

基于 GitHub 开源项目（Surprise、recommender-systems 等）学习实现的企业培训智能推荐系统。

## 核心功能

### 6 种推荐算法
| 算法 | 说明 |
|------|------|
| **AI 混合推荐** | 加权融合 5 种算法，SVD 占 28% 权重 |
| **SVD 矩阵分解** | 机器学习隐语义模型，梯度下降优化，发现隐式兴趣 |
| **用户协同过滤** | 余弦相似度找相似学员，加权评分推荐 |
| **物品协同过滤** | 改进余弦相似度 + 热门惩罚 + 内容相似度混合 |
| **内容推荐** | 课程分类/标签/难度特征向量 + 用户偏好余弦匹配 |
| **热门推荐** | 学习人数归一化 × 0.6 + 平均评分 × 0.4 |

### AI 增强功能
- **AI 智能推荐理由**：综合岗位匹配、学习历史、同事行为、技能缺口、课程热度等 8 个维度生成个性化推荐解释
- **AI 学习路径规划**：根据岗位自动生成 4 阶段成长路径，实时追踪进度并给出 AI 建议
- **AI 学习助手**：对话式交互，支持课程推荐、路径规划、进度查询、热门课程、算法原理等问答
- **冷启动处理**：新用户自动切换为内容推荐 + 热门推荐策略
- **实时更新**：学习/评分行为触发模型即时重训练

## 技术栈
- 后端：Python 3 + Flask
- 推荐算法：纯 Python 实现（SVD 梯度下降、协同过滤、余弦相似度）
- 前端：原生 HTML/CSS/JS 单页应用
- 数据：24 门课程、10 位学员、50+ 条学习行为

## 快速开始

```bash
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5000
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/recommend/<user_id>` | GET | 获取推荐结果（?algorithm=hybrid/svd/user_cf/item_cf/content/popular） |
| `/api/profile/<user_id>` | GET | 获取学员画像和已学课程 |
| `/api/interact` | POST | 记录学习行为，实时更新推荐 |
| `/api/compare/<user_id>` | GET | 6 种算法推荐结果对比 |
| `/api/learning-path/<user_id>` | GET | AI 学习路径规划 |
| `/api/chat` | POST | AI 学习助手对话 |

## 项目结构

```
├── app.py              # Flask 应用与 REST API
├── recommender.py      # 推荐引擎（6 种算法，含 SVD 机器学习）
├── ai_engine.py        # AI 增强引擎（推荐理由、学习路径、对话助手）
├── data.py             # 模拟数据
├── templates/index.html
├── static/style.css
├── static/app.js
├── requirements.txt
└── README.md
```
