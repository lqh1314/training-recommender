"""
培训管理系统 - 模拟数据
包含课程、用户、学习行为数据
"""

# 课程数据（企业培训常见分类）
COURSES = [
    # 技术研发类
    {"id": 1, "name": "Python 编程基础", "desc": "从零开始学习 Python 编程语言，掌握核心语法和编程思维", "categories": ["技术研发"], "tags": ["Python", "编程", "入门", "后端"], "difficulty": "初级", "duration": 12, "instructor": "张明", "cover_color": "#3B82F6"},
    {"id": 2, "name": "Java Spring Boot 实战", "desc": "深入学习 Spring Boot 框架，构建企业级 Java 应用", "categories": ["技术研发"], "tags": ["Java", "Spring", "后端", "微服务"], "difficulty": "中级", "duration": 20, "instructor": "李工", "cover_color": "#EF4444"},
    {"id": 3, "name": "Vue3 前端开发", "desc": "掌握 Vue3 组合式 API，开发现代化前端应用", "categories": ["技术研发"], "tags": ["Vue", "前端", "JavaScript"], "difficulty": "中级", "duration": 16, "instructor": "王芳", "cover_color": "#10B981"},
    {"id": 4, "name": "MySQL 数据库优化", "desc": "数据库性能调优、索引优化、查询优化实战", "categories": ["技术研发"], "tags": ["MySQL", "数据库", "性能优化"], "difficulty": "高级", "duration": 10, "instructor": "赵强", "cover_color": "#F59E0B"},
    {"id": 5, "name": "Docker 容器化部署", "desc": "使用 Docker 实现应用容器化，掌握 DevOps 基础", "categories": ["技术研发"], "tags": ["Docker", "DevOps", "运维"], "difficulty": "中级", "duration": 8, "instructor": "陈伟", "cover_color": "#6366F1"},
    {"id": 6, "name": "React 进阶指南", "desc": "深入 React Hooks、状态管理和性能优化", "categories": ["技术研发"], "tags": ["React", "前端", "JavaScript"], "difficulty": "高级", "duration": 14, "instructor": "刘洋", "cover_color": "#06B6D4"},
    {"id": 7, "name": "机器学习入门", "desc": "了解机器学习基本概念，使用 scikit-learn 构建模型", "categories": ["技术研发", "数据科学"], "tags": ["机器学习", "Python", "AI", "数据分析"], "difficulty": "中级", "duration": 18, "instructor": "孙博士", "cover_color": "#8B5CF6"},
    {"id": 8, "name": "Git 版本控制", "desc": "Git 工作流、分支管理、团队协作最佳实践", "categories": ["技术研发"], "tags": ["Git", "协作", "工具"], "difficulty": "初级", "duration": 4, "instructor": "周杰", "cover_color": "#EC4899"},

    # 管理类
    {"id": 9, "name": "高效团队管理", "desc": "打造高绩效团队的管理方法论与实践", "categories": ["管理领导力"], "tags": ["团队管理", "领导力", "沟通"], "difficulty": "中级", "duration": 10, "instructor": "马总", "cover_color": "#F97316"},
    {"id": 10, "name": "项目管理 PMP 精讲", "desc": "PMP 知识体系详解，项目管理全流程", "categories": ["管理领导力"], "tags": ["项目管理", "PMP", "敏捷"], "difficulty": "中级", "duration": 24, "instructor": "林经理", "cover_color": "#14B8A6"},
    {"id": 11, "name": "敏捷开发 Scrum 实战", "desc": "Scrum 框架、敏捷 ceremonies、用户故事编写", "categories": ["管理领导力", "技术研发"], "tags": ["敏捷", "Scrum", "项目管理"], "difficulty": "初级", "duration": 8, "instructor": "黄教练", "cover_color": "#A855F7"},
    {"id": 12, "name": "OKR 目标管理", "desc": "制定有效 OKR，对齐团队目标，驱动结果达成", "categories": ["管理领导力"], "tags": ["OKR", "目标管理", "绩效"], "difficulty": "初级", "duration": 6, "instructor": "吴总监", "cover_color": "#0EA5E9"},

    # 职场素养
    {"id": 13, "name": "商务沟通与表达", "desc": "提升职场沟通能力，高效表达与演讲技巧", "categories": ["职场素养"], "tags": ["沟通", "演讲", "表达"], "difficulty": "初级", "duration": 8, "instructor": "郑老师", "cover_color": "#F43F5E"},
    {"id": 14, "name": "时间管理与效率提升", "desc": "掌握时间管理方法，提升工作效率", "categories": ["职场素养"], "tags": ["时间管理", "效率", "GTD"], "difficulty": "初级", "duration": 5, "instructor": "冯教练", "cover_color": "#22C55E"},
    {"id": 15, "name": "职场写作技巧", "desc": "邮件、报告、方案等职场文档写作规范", "categories": ["职场素养"], "tags": ["写作", "文档", "沟通"], "difficulty": "初级", "duration": 6, "instructor": "许编辑", "cover_color": "#64748B"},

    # 市场营销
    {"id": 16, "name": "数字营销实战", "desc": "SEO/SEM、社交媒体营销、内容营销策略", "categories": ["市场营销"], "tags": ["数字营销", "SEO", "社交媒体"], "difficulty": "中级", "duration": 12, "instructor": "韩营销", "cover_color": "#E11D48"},
    {"id": 17, "name": "数据分析与运营", "desc": "用数据驱动运营决策，掌握数据分析方法", "categories": ["市场营销", "数据科学"], "tags": ["数据分析", "运营", "Excel", "SQL"], "difficulty": "中级", "duration": 14, "instructor": "曹分析师", "cover_color": "#7C3AED"},
    {"id": 18, "name": "产品经理入门", "desc": "产品思维、需求分析、原型设计、产品规划", "categories": ["市场营销", "产品设计"], "tags": ["产品经理", "需求分析", "原型"], "difficulty": "初级", "duration": 16, "instructor": "沈产品", "cover_color": "#0891B2"},

    # 财务法务
    {"id": 19, "name": "非财务人员财务管理", "desc": "财务报表解读、预算管理、成本控制基础", "categories": ["财务法务"], "tags": ["财务", "报表", "预算"], "difficulty": "初级", "duration": 8, "instructor": "杨会计", "cover_color": "#65A30D"},
    {"id": 20, "name": "合同法务实务", "desc": "合同审查要点、法律风险防范、常见纠纷处理", "categories": ["财务法务"], "tags": ["法律", "合同", "风险"], "difficulty": "中级", "duration": 6, "instructor": "朱律师", "cover_color": "#DC2626"},

    # 人力资源
    {"id": 21, "name": "招聘与面试技巧", "desc": "结构化面试、人才识别、招聘流程优化", "categories": ["人力资源"], "tags": ["招聘", "面试", "人才"], "difficulty": "初级", "duration": 6, "instructor": "秦HR", "cover_color": "#0D9488"},
    {"id": 22, "name": "新员工入职培训", "desc": "公司文化、规章制度、办公系统使用指南", "categories": ["人力资源", "新员工"], "tags": ["入职", "企业文化", "制度"], "difficulty": "初级", "duration": 4, "instructor": "HR团队", "cover_color": "#3B82F6"},

    # 安全合规
    {"id": 23, "name": "信息安全意识", "desc": "网络安全基础、数据保护、社会工程学防范", "categories": ["安全合规"], "tags": ["信息安全", "数据保护", "合规"], "difficulty": "初级", "duration": 4, "instructor": "安全团队", "cover_color": "#475569"},
    {"id": 24, "name": "消防安全培训", "desc": "消防知识、应急疏散、灭火器使用实操", "categories": ["安全合规"], "tags": ["消防", "安全", "应急"], "difficulty": "初级", "duration": 3, "instructor": "安全员", "cover_color": "#B91C1C"},
]

# 用户数据
USERS = [
    {"id": 1, "name": "张三", "department": "技术研发部", "position": "后端开发工程师", "avatar": "张"},
    {"id": 2, "name": "李四", "department": "技术研发部", "position": "前端开发工程师", "avatar": "李"},
    {"id": 3, "name": "王五", "department": "产品部", "position": "产品经理", "avatar": "王"},
    {"id": 4, "name": "赵六", "department": "市场部", "position": "数字营销专员", "avatar": "赵"},
    {"id": 5, "name": "钱七", "department": "人力资源部", "position": "HRBP", "avatar": "钱"},
    {"id": 6, "name": "孙八", "department": "技术研发部", "position": "数据工程师", "avatar": "孙"},
    {"id": 7, "name": "周九", "department": "管理层", "position": "技术总监", "avatar": "周"},
    {"id": 8, "name": "吴十", "department": "财务部", "position": "财务分析师", "avatar": "吴"},
    {"id": 9, "name": "郑新", "department": "技术研发部", "position": "新入职员工", "avatar": "郑"},
    {"id": 10, "name": "陈晨", "department": "运营部", "position": "运营专员", "avatar": "陈"},
]

# 学习行为数据 (user_id, course_id, progress 0-1, rating 0-5, behavior_weight 0-1)
# behavior_weight: 收藏=0.8, 分享=0.6, 评论=0.7, 完成=1.0
INTERACTIONS = [
    # 张三 - 后端开发，学了很多Java/Python相关
    {"user_id": 1, "course_id": 2, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 1, "course_id": 1, "progress": 1.0, "rating": 4, "behavior_weight": 0.8},
    {"user_id": 1, "course_id": 4, "progress": 0.8, "rating": 5, "behavior_weight": 0.7},
    {"user_id": 1, "course_id": 5, "progress": 0.6, "rating": 4, "behavior_weight": 0.6},
    {"user_id": 1, "course_id": 8, "progress": 1.0, "rating": 4, "behavior_weight": 0.5},
    {"user_id": 1, "course_id": 11, "progress": 0.5, "rating": 3, "behavior_weight": 0.3},

    # 李四 - 前端开发
    {"user_id": 2, "course_id": 3, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 2, "course_id": 6, "progress": 0.9, "rating": 5, "behavior_weight": 0.9},
    {"user_id": 2, "course_id": 1, "progress": 0.7, "rating": 4, "behavior_weight": 0.5},
    {"user_id": 2, "course_id": 8, "progress": 1.0, "rating": 4, "behavior_weight": 0.6},
    {"user_id": 2, "course_id": 18, "progress": 0.4, "rating": 3, "behavior_weight": 0.3},

    # 王五 - 产品经理
    {"user_id": 3, "course_id": 18, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 3, "course_id": 11, "progress": 0.9, "rating": 4, "behavior_weight": 0.8},
    {"user_id": 3, "course_id": 13, "progress": 0.8, "rating": 4, "behavior_weight": 0.6},
    {"user_id": 3, "course_id": 17, "progress": 0.6, "rating": 4, "behavior_weight": 0.5},
    {"user_id": 3, "course_id": 12, "progress": 0.7, "rating": 3, "behavior_weight": 0.4},

    # 赵六 - 数字营销
    {"user_id": 4, "course_id": 16, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 4, "course_id": 17, "progress": 0.8, "rating": 4, "behavior_weight": 0.7},
    {"user_id": 4, "course_id": 13, "progress": 0.6, "rating": 4, "behavior_weight": 0.5},
    {"user_id": 4, "course_id": 14, "progress": 0.9, "rating": 5, "behavior_weight": 0.8},
    {"user_id": 4, "course_id": 15, "progress": 0.5, "rating": 3, "behavior_weight": 0.3},

    # 钱七 - HR
    {"user_id": 5, "course_id": 21, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 5, "course_id": 22, "progress": 1.0, "rating": 4, "behavior_weight": 0.8},
    {"user_id": 5, "course_id": 9, "progress": 0.7, "rating": 4, "behavior_weight": 0.6},
    {"user_id": 5, "course_id": 13, "progress": 0.8, "rating": 5, "behavior_weight": 0.7},
    {"user_id": 5, "course_id": 12, "progress": 0.5, "rating": 3, "behavior_weight": 0.4},

    # 孙八 - 数据工程师
    {"user_id": 6, "course_id": 7, "progress": 0.9, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 6, "course_id": 1, "progress": 1.0, "rating": 5, "behavior_weight": 0.9},
    {"user_id": 6, "course_id": 4, "progress": 0.8, "rating": 4, "behavior_weight": 0.7},
    {"user_id": 6, "course_id": 17, "progress": 1.0, "rating": 5, "behavior_weight": 0.8},
    {"user_id": 6, "course_id": 5, "progress": 0.4, "rating": 3, "behavior_weight": 0.3},

    # 周九 - 技术总监
    {"user_id": 7, "course_id": 9, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 7, "course_id": 10, "progress": 0.9, "rating": 5, "behavior_weight": 0.9},
    {"user_id": 7, "course_id": 11, "progress": 1.0, "rating": 4, "behavior_weight": 0.8},
    {"user_id": 7, "course_id": 12, "progress": 0.8, "rating": 4, "behavior_weight": 0.6},
    {"user_id": 7, "course_id": 2, "progress": 0.3, "rating": 3, "behavior_weight": 0.2},

    # 吴十 - 财务
    {"user_id": 8, "course_id": 19, "progress": 1.0, "rating": 5, "behavior_weight": 1.0},
    {"user_id": 8, "course_id": 20, "progress": 0.8, "rating": 4, "behavior_weight": 0.7},
    {"user_id": 8, "course_id": 14, "progress": 0.6, "rating": 4, "behavior_weight": 0.5},
    {"user_id": 8, "course_id": 15, "progress": 0.7, "rating": 3, "behavior_weight": 0.4},

    # 郑新 - 新员工（冷启动用户，只有2条记录）
    {"user_id": 9, "course_id": 22, "progress": 1.0, "rating": 4, "behavior_weight": 0.8},
    {"user_id": 9, "course_id": 23, "progress": 0.5, "rating": 0, "behavior_weight": 0.3},

    # 陈晨 - 运营
    {"user_id": 10, "course_id": 17, "progress": 0.8, "rating": 5, "behavior_weight": 0.8},
    {"user_id": 10, "course_id": 16, "progress": 0.7, "rating": 4, "behavior_weight": 0.6},
    {"user_id": 10, "course_id": 14, "progress": 0.9, "rating": 5, "behavior_weight": 0.7},
    {"user_id": 10, "course_id": 13, "progress": 0.6, "rating": 4, "behavior_weight": 0.5},
    {"user_id": 10, "course_id": 18, "progress": 0.5, "rating": 4, "behavior_weight": 0.4},
    {"user_id": 10, "course_id": 15, "progress": 0.8, "rating": 3, "behavior_weight": 0.5},
]
