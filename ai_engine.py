"""
培训管理系统 - AI 增强引擎
提供 AI 驱动的智能推荐理由、学习路径规划、学习助手功能
"""

from typing import Dict, List
from collections import defaultdict


class AIEngine:
    """AI 增强引擎"""

    def __init__(self, recommender):
        self.recommender = recommender

    def generate_recommendation_explanation(self, user_id: int, course_id: int,
                                           algorithm: str) -> str:
        """
        AI 生成个性化推荐理由
        综合学员画像、课程特征、行为数据生成自然语言解释
        """
        r = self.recommender
        user = r.users.get(user_id, {})
        course = r.courses.get(course_id, {})
        profile = r.get_user_profile(user_id)

        reasons = []

        # 1. 岗位匹配度分析
        position = user.get('position', '')
        dept = user.get('department', '')
        course_cats = course.get('categories', [])
        course_tags = course.get('tags', [])

        if self._position_matches_course(position, course_tags, course_cats):
            reasons.append(f"作为{position}，这门课直接匹配你的岗位技能需求")

        # 2. 学习历史关联
        learned = r.user_learned.get(user_id, set())
        if learned:
            best_sim = 0
            best_course_name = ''
            for lid in learned:
                sim = r.item_similarity.get(lid, {}).get(course_id, 0)
                if sim > best_sim:
                    best_sim = sim
                    best_course_name = r.courses.get(lid, {}).get('name', '')
            if best_sim > 0.15 and best_course_name:
                reasons.append(f"与你已学的《{best_course_name}》知识衔接紧密")

        # 3. 同事/相似学员行为
        similar_users = r.user_similarity.get(user_id, {})
        peer_count = 0
        for uid in similar_users:
            if course_id in r.user_learned.get(uid, set()):
                peer_count += 1
        if peer_count >= 2:
            reasons.append(f"{peer_count}位与你兴趣相似的同事都学习了这门课")

        # 4. 部门学习趋势
        dept_learners = [
            uid for uid in r.course_users.get(course_id, set())
            if r.users.get(uid, {}).get('department') == dept and uid != user_id
        ]
        if dept_learners:
            reasons.append(f"你们部门有{len(dept_learners)}位同事已学习")

        # 5. 技能缺口分析
        top_tags = profile.get('top_tags', [])
        course_new_tags = [t for t in course_tags if t not in top_tags]
        if course_new_tags and len(learned) > 2:
            reasons.append(f"能帮你拓展{ '、'.join(course_new_tags[:2]) }等新技能")

        # 6. 难度适配
        difficulty = course.get('difficulty', '中级')
        if difficulty == '初级' and len(learned) < 3:
            reasons.append("难度适合入门，建议优先学习")
        elif difficulty == '高级' and len(learned) >= 4:
            reasons.append("适合有基础后进阶提升")

        # 7. 课程热度
        learners = len(r.course_users.get(course_id, set()))
        if learners >= 4:
            avg_rating = self._get_avg_rating(course_id)
            if avg_rating >= 4.5:
                reasons.append(f"热门课程，{learners}人学习且评分{avg_rating:.1f}星")

        # 8. 冷启动用户
        if profile.get('is_cold_start'):
            if '新员工' in position or '入职' in str(course_tags):
                reasons.append("新员工必修课程，帮助快速融入")
            elif difficulty == '初级':
                reasons.append("适合新员工入门学习")

        if not reasons:
            reasons.append("综合你的学习偏好和行为数据推荐")

        return '；'.join(reasons[:3])

    def _position_matches_course(self, position: str, tags: list,
                                 categories: list) -> bool:
        """判断岗位是否与课程匹配"""
        position_keywords = {
            '后端': ['Java', 'Python', 'MySQL', 'Spring', 'Docker', '微服务', '后端', 'Git'],
            '前端': ['Vue', 'React', 'JavaScript', '前端'],
            '数据': ['数据分析', '机器学习', 'Python', 'SQL', 'Excel', 'AI'],
            '产品': ['产品经理', '需求分析', '原型', 'Scrum', '敏捷'],
            '营销': ['数字营销', 'SEO', '运营', '数据分析'],
            'HR': ['招聘', '面试', '人才', '入职', '团队管理'],
            '管理': ['团队管理', '领导力', 'PMP', 'OKR', '敏捷', 'Scrum'],
            '财务': ['财务', '预算', '报表', '合同'],
            '运营': ['数据分析', '运营', '数字营销', '内容'],
        }
        for keyword, related_tags in position_keywords.items():
            if keyword in position:
                if any(t in tags or any(t in c for c in categories) for t in related_tags):
                    return True
        return False

    def _get_avg_rating(self, course_id: int) -> float:
        """获取课程平均评分"""
        ratings = [
            i.get('rating', 0) for i in self.recommender.interactions
            if i['course_id'] == course_id and i.get('rating', 0) > 0
        ]
        return sum(ratings) / len(ratings) if ratings else 0

    def generate_learning_path(self, user_id: int) -> dict:
        """
        AI 学习路径规划
        根据学员岗位、已学课程、技能缺口，生成阶段化学习路径
        """
        r = self.recommender
        user = r.users.get(user_id, {})
        position = user.get('position', '')
        dept = user.get('department', '')
        learned = r.user_learned.get(user_id, set())
        profile = r.get_user_profile(user_id)

        path_template = self._get_path_template(position, dept)

        stages = []
        all_recommended = set()

        for stage_idx, stage in enumerate(path_template['stages']):
            stage_courses = []
            for cid in stage['course_ids']:
                if cid not in r.courses:
                    continue
                course = r.courses[cid]
                status = 'completed' if cid in learned else 'recommended'
                if status == 'recommended':
                    all_recommended.add(cid)
                stage_courses.append({
                    'id': cid,
                    'name': course['name'],
                    'duration': course['duration'],
                    'difficulty': course['difficulty'],
                    'cover_color': course['cover_color'],
                    'status': status,
                    'tags': course['tags'][:3]
                })

            if all(c['status'] == 'completed' for c in stage_courses) and stage_courses:
                recs = r.recommend_hybrid(user_id, 3)
                for rec in recs:
                    if rec['course_id'] not in learned and rec['course_id'] not in all_recommended:
                        c = r.courses[rec['course_id']]
                        stage_courses.append({
                            'id': rec['course_id'],
                            'name': c['name'],
                            'duration': c['duration'],
                            'difficulty': c['difficulty'],
                            'cover_color': c['cover_color'],
                            'status': 'recommended',
                            'tags': c['tags'][:3]
                        })
                        all_recommended.add(rec['course_id'])
                        break

            stages.append({
                'stage': stage_idx + 1,
                'title': stage['title'],
                'description': stage['description'],
                'courses': stage_courses
            })

        total_courses = sum(len(s['courses']) for s in stages)
        completed = sum(
            1 for s in stages for c in s['courses'] if c['status'] == 'completed'
        )
        progress = round(completed / total_courses * 100) if total_courses else 0

        total_hours = sum(
            c['duration'] for s in stages for c in s['courses']
            if c['status'] == 'recommended'
        )
        ai_advice = self._generate_path_advice(
            user, profile, progress, total_hours, stages
        )

        return {
            'user_name': user.get('name', ''),
            'direction': path_template['direction'],
            'direction_desc': path_template['description'],
            'stages': stages,
            'progress': progress,
            'completed': completed,
            'total': total_courses,
            'remaining_hours': total_hours,
            'ai_advice': ai_advice
        }

    def _get_path_template(self, position: str, dept: str) -> dict:
        """根据岗位获取学习路径模板"""
        if '后端' in position or '研发' in dept:
            return {
                'direction': '后端开发工程师成长路径',
                'description': '从编程基础到微服务架构的系统化学习路线',
                'stages': [
                    {'title': '基础夯实', 'description': '掌握编程语言和版本控制工具',
                     'course_ids': [1, 8]},
                    {'title': '框架与数据库', 'description': '学习主流框架和数据库优化',
                     'course_ids': [2, 4]},
                    {'title': 'DevOps与部署', 'description': '容器化部署和运维基础',
                     'course_ids': [5, 23]},
                    {'title': '进阶提升', 'description': '敏捷开发与AI技术探索',
                     'course_ids': [11, 7]},
                ]
            }
        elif '前端' in position:
            return {
                'direction': '前端开发工程师成长路径',
                'description': '从基础到高级前端技术的系统化学习路线',
                'stages': [
                    {'title': '基础夯实', 'description': '掌握编程语言和版本控制',
                     'course_ids': [1, 8]},
                    {'title': '框架精通', 'description': '深入学习主流前端框架',
                     'course_ids': [3, 6]},
                    {'title': '工程化与协作', 'description': '敏捷开发与团队协作',
                     'course_ids': [11, 18]},
                    {'title': '进阶提升', 'description': '数据分析与AI技术',
                     'course_ids': [17, 7]},
                ]
            }
        elif '产品' in position:
            return {
                'direction': '产品经理成长路径',
                'description': '从产品思维到项目管理的系统化学习路线',
                'stages': [
                    {'title': '产品基础', 'description': '产品思维与需求分析',
                     'course_ids': [18, 15]},
                    {'title': '敏捷管理', 'description': 'Scrum敏捷开发实践',
                     'course_ids': [11, 10]},
                    {'title': '沟通与目标', 'description': '沟通表达与目标管理',
                     'course_ids': [13, 12]},
                    {'title': '数据驱动', 'description': '数据分析与运营',
                     'course_ids': [17, 16]},
                ]
            }
        elif '数据' in position:
            return {
                'direction': '数据工程师成长路径',
                'description': '从编程基础到机器学习的系统化学习路线',
                'stages': [
                    {'title': '编程基础', 'description': 'Python编程与Git',
                     'course_ids': [1, 8]},
                    {'title': '数据库与分析', 'description': 'MySQL与数据分析',
                     'course_ids': [4, 17]},
                    {'title': '机器学习', 'description': 'ML入门与实战',
                     'course_ids': [7, 5]},
                    {'title': '综合提升', 'description': '管理与安全',
                     'course_ids': [11, 23]},
                ]
            }
        elif '营销' in position or '市场' in dept:
            return {
                'direction': '数字营销成长路径',
                'description': '从营销基础到数据驱动的系统化学习路线',
                'stages': [
                    {'title': '营销基础', 'description': '数字营销与内容写作',
                     'course_ids': [16, 15]},
                    {'title': '数据运营', 'description': '数据分析与运营',
                     'course_ids': [17, 14]},
                    {'title': '沟通表达', 'description': '商务沟通与表达',
                     'course_ids': [13, 18]},
                    {'title': '管理提升', 'description': '目标管理与团队',
                     'course_ids': [12, 9]},
                ]
            }
        elif 'HR' in position or '人力' in dept:
            return {
                'direction': 'HRBP成长路径',
                'description': '从招聘到组织发展的系统化学习路线',
                'stages': [
                    {'title': '招聘入门', 'description': '招聘面试与入职培训',
                     'course_ids': [21, 22]},
                    {'title': '沟通协作', 'description': '沟通表达与团队管理',
                     'course_ids': [13, 9]},
                    {'title': '目标管理', 'description': 'OKR与绩效管理',
                     'course_ids': [12, 14]},
                    {'title': '合规安全', 'description': '合同法务与安全',
                     'course_ids': [20, 23]},
                ]
            }
        elif '管理' in position or '总监' in position or dept == '管理层':
            return {
                'direction': '技术管理者成长路径',
                'description': '从技术到管理的系统化学习路线',
                'stages': [
                    {'title': '管理基础', 'description': '团队管理与沟通',
                     'course_ids': [9, 13]},
                    {'title': '项目管理', 'description': 'PMP与敏捷Scrum',
                     'course_ids': [10, 11]},
                    {'title': '目标驱动', 'description': 'OKR目标管理',
                     'course_ids': [12, 2]},
                    {'title': '技术视野', 'description': '了解技术趋势',
                     'course_ids': [7, 5]},
                ]
            }
        elif '财务' in position:
            return {
                'direction': '财务分析师成长路径',
                'description': '从财务基础到业务伙伴的学习路线',
                'stages': [
                    {'title': '财务基础', 'description': '财务管理入门',
                     'course_ids': [19, 15]},
                    {'title': '法务合规', 'description': '合同法务实务',
                     'course_ids': [20, 23]},
                    {'title': '效率提升', 'description': '时间管理与沟通',
                     'course_ids': [14, 13]},
                    {'title': '数据能力', 'description': '数据分析基础',
                     'course_ids': [17, 12]},
                ]
            }
        elif '运营' in position:
            return {
                'direction': '运营专员成长路径',
                'description': '从执行到策略的系统化学习路线',
                'stages': [
                    {'title': '运营基础', 'description': '数据分析与营销',
                     'course_ids': [17, 16]},
                    {'title': '效率工具', 'description': '时间管理与写作',
                     'course_ids': [14, 15]},
                    {'title': '沟通协作', 'description': '沟通与产品思维',
                     'course_ids': [13, 18]},
                    {'title': '进阶提升', 'description': '目标管理',
                     'course_ids': [12, 9]},
                ]
            }
        else:
            return {
                'direction': '新员工入职学习路径',
                'description': '从入职到胜任的系统化学习路线',
                'stages': [
                    {'title': '入职引导', 'description': '公司文化与制度',
                     'course_ids': [22, 23]},
                    {'title': '职业素养', 'description': '沟通与时间管理',
                     'course_ids': [13, 14]},
                    {'title': '技能入门', 'description': '根据岗位选择',
                     'course_ids': [1, 8]},
                    {'title': '持续成长', 'description': '团队协作',
                     'course_ids': [9, 12]},
                ]
            }

    def _generate_path_advice(self, user: dict, profile: dict,
                              progress: int, hours: int,
                              stages: list) -> str:
        """AI 生成学习路径建议"""
        name = user.get('name', '你')
        position = user.get('position', '')

        if progress == 100:
            return f"🎉 {name}，你已完成当前学习路径的所有课程！建议探索新领域或承担更具挑战性的项目。"
        elif progress >= 60:
            next_stage = None
            next_course = None
            for s in stages:
                todos = [c for c in s['courses'] if c['status'] == 'recommended']
                if todos:
                    next_stage = s
                    next_course = todos[0]
                    break
            if next_stage and next_course:
                return f"📈 {name}，你已完成{progress}%的学习路径，进展不错！建议进入「{next_stage['title']}」阶段，重点学习《{next_course['name']}》。"
        elif progress >= 20:
            return f"💪 {name}，你已完成{progress}%，继续保持！建议按阶段顺序学习，每天投入30-60分钟，预计{max(1, hours // 12)}周可完成剩余课程。"
        else:
            return f"🌱 {name}，欢迎开始学习！作为{position}，建议从第一阶段基础课程开始，循序渐进。完成入门课程后，推荐系统会更精准地为你推荐后续课程。"

    def chat(self, user_id: int, message: str) -> str:
        """
        AI 学习助手对话
        基于知识库和学员数据回答问题
        """
        r = self.recommender
        msg = message.lower().strip()
        user = r.users.get(user_id, {})
        name = user.get('name', '你')
        profile = r.get_user_profile(user_id)

        if any(k in msg for k in ['推荐', '学什么', '该学', '有什么课', '建议学']):
            recs = r.recommend_hybrid(user_id, 3)
            if recs:
                course_list = '、'.join(
                    f"《{r.courses[rec['course_id']]['name']}》" for rec in recs
                )
                return f"根据你的学习历史和岗位特点，我推荐：{course_list}。你可以在上方推荐区域查看详细推荐理由。"
            return "目前推荐数据不足，建议先完成几门入门课程。"

        if any(k in msg for k in ['路径', '规划', '路线', '怎么学', '学习计划']):
            path = self.generate_learning_path(user_id)
            return f"为你规划的方向是「{path['direction']}」，共{path['total']}门课，已完成{path['completed']}门。{path['ai_advice']}"

        if any(k in msg for k in ['进度', '学了多少', '学习情况', '我的学习']):
            learned_count = profile['learned_count']
            total_progress = profile['total_progress']
            cats = '、'.join(profile.get('top_categories', []))
            return f"{name}，你已学习{learned_count}门课程，累计{total_progress:.0f}小时。你最感兴趣的领域是：{cats}。"

        if any(k in msg for k in ['热门', '流行', '大家都在学', '最火']):
            pops = r.recommend_popular(3)
            course_list = '、'.join(
                f"《{r.courses[rec['course_id']]['name']}》" for rec in pops
            )
            return f"当前最热门的课程是：{course_list}。"

        if any(k in msg for k in ['岗位', '职位', '工作', '职业']):
            position = user.get('position', '')
            path = self.generate_learning_path(user_id)
            return f"作为{position}，建议的学习方向是「{path['direction']}」。{path['direction_desc']}。"

        if any(k in msg for k in ['技能', '标签', '兴趣', '偏好', '擅长']):
            tags = profile.get('top_tags', [])
            cats = profile.get('top_categories', [])
            return f"你的兴趣标签：{'、'.join(tags[:5])}；偏好分类：{'、'.join(cats[:3])}。多学习不同类型课程可以拓展技能树。"

        if any(k in msg for k in ['新员工', '刚来', '新入职', '新手']):
            recs = r.recommend_popular(3)
            course_list = '、'.join(
                f"《{r.courses[rec['course_id']]['name']}》" for rec in recs
            )
            return f"新员工建议先完成入职培训和信息安全课程，然后可以学习：{course_list}。随着学习记录增加，推荐会更精准。"

        if any(k in msg for k in ['算法', '怎么推荐', '推荐原理', '协同过滤', 'svd']):
            return ("系统使用了6种推荐算法：用户协同过滤、物品协同过滤、内容推荐、热门推荐、SVD矩阵分解（机器学习），"
                    "以及混合推荐（加权融合）。混合推荐中SVD占28%权重，能发现隐式兴趣关联。")

        if any(k in msg for k in ['你好', '您好', 'hi', 'hello', '在吗']):
            return f"你好{name}！我是你的AI学习助手，可以帮你推荐课程、规划学习路径、解答学习相关问题。试试问我「推荐什么课程」或「学习路径」。"

        if any(k in msg for k in ['帮助', '能做什么', '功能', 'help']):
            return ("我可以帮你：\n"
                    "1. 推荐课程 - 问「推荐什么课程」\n"
                    "2. 规划学习路径 - 问「学习路径」\n"
                    "3. 查询学习进度 - 问「我的学习情况」\n"
                    "4. 查看热门课程 - 问「热门课程」\n"
                    "5. 了解推荐算法 - 问「推荐原理」")

        return "我是AI学习助手，可以回答课程推荐、学习路径、学习进度等问题。试试问我「推荐什么课程」或「学习路径」，或输入「帮助」查看所有功能。"
