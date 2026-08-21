"""
培训管理系统 - 智能推荐引擎
基于 GitHub 开源项目 Surprise / recommender-systems 学习实现

支持算法：
1. 基于用户的协同过滤 (User-CF)
2. 基于物品的协同过滤 (Item-CF)
3. 基于内容的推荐 (Content-Based)
4. 热门推荐 (Popularity)
5. 混合推荐 (Hybrid) - 加权融合
"""

import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class RecommendationEngine:
    """智能推荐引擎"""

    def __init__(self, users: List[dict], courses: List[dict],
                 interactions: List[dict]):
        self.users = {u['id']: u for u in users}
        self.courses = {c['id']: c for c in courses}
        self.interactions = interactions

        # 用户-课程评分矩阵 (隐式反馈: 学习进度+评分+行为权重)
        self.user_course_matrix = self._build_matrix()

        # 用户已学习课程集合
        self.user_learned = defaultdict(set)
        for inter in interactions:
            self.user_learned[inter['user_id']].add(inter['course_id'])

        # 课程-用户倒排表
        self.course_users = defaultdict(set)
        for inter in interactions:
            self.course_users[inter['course_id']].add(inter['user_id'])

        # 课程内容向量 (类别+标签+难度 one-hot)
        self.course_content_vectors = self._build_content_vectors()

        # 用户偏好向量 (从学习历史聚合)
        self.user_preference_vectors = self._build_user_preferences()

        # 预计算课程相似度 (Item-CF)
        self.item_similarity = self._compute_item_similarity()

        # 预计算用户相似度 (User-CF)
        self.user_similarity = self._compute_user_similarity()

        # 课程热门度分数
        self.course_popularity = self._compute_popularity()

    def _build_matrix(self) -> Dict[int, Dict[int, float]]:
        """构建用户-课程评分矩阵（隐式反馈转评分）"""
        matrix = defaultdict(dict)
        for inter in self.interactions:
            uid = inter['user_id']
            cid = inter['course_id']
            # 综合评分 = 显式评分*0.5 + 学习进度*0.3 + 行为权重*0.2
            score = (
                inter.get('rating', 0) * 0.5
                + inter.get('progress', 0) * 0.3
                + inter.get('behavior_weight', 0) * 0.2
            )
            # 取最大值（多次交互取最强信号）
            if cid not in matrix[uid] or score > matrix[uid][cid]:
                matrix[uid][cid] = round(score, 2)
        return dict(matrix)

    def _build_content_vectors(self) -> Dict[int, Dict[str, float]]:
        """构建课程内容特征向量（类别+标签+难度）"""
        vectors = {}
        for cid, course in self.courses.items():
            vec = defaultdict(float)
            for cat in course.get('categories', []):
                vec[f'cat_{cat}'] = 1.0
            for tag in course.get('tags', []):
                vec[f'tag_{tag}'] = 0.8
            vec[f'diff_{course.get("difficulty", "中级")}'] = 1.0
            vectors[cid] = dict(vec)
        return vectors

    def _build_user_preferences(self) -> Dict[int, Dict[str, float]]:
        """基于学习历史构建用户偏好向量"""
        prefs = {}
        for uid in self.users:
            pref = defaultdict(float)
            learned = self.user_learned.get(uid, set())
            if not learned:
                prefs[uid] = {}
                continue
            for cid in learned:
                weight = self.user_course_matrix.get(uid, {}).get(cid, 0.5)
                for feat, val in self.course_content_vectors.get(cid, {}).items():
                    pref[feat] += val * weight
            # 归一化
            total = sum(pref.values()) or 1
            prefs[uid] = {k: round(v / total, 4) for k, v in pref.items()}
        return prefs

    @staticmethod
    def _cosine_similarity(vec_a: Dict, vec_b: Dict) -> float:
        """余弦相似度"""
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0
        dot = sum(vec_a[k] * vec_b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _compute_item_similarity(self) -> Dict[int, Dict[int, float]]:
        """计算课程间相似度（Item-CF，带热门惩罚）"""
        sim = defaultdict(dict)
        course_ids = list(self.course_users.keys())
        for i, c1 in enumerate(course_ids):
            for c2 in course_ids[i + 1:]:
                users1 = self.course_users[c1]
                users2 = self.course_users[c2]
                common = users1 & users2
                if not common:
                    # 也用内容相似度补充
                    content_sim = self._cosine_similarity(
                        self.course_content_vectors.get(c1, {}),
                        self.course_content_vectors.get(c2, {})
                    )
                    if content_sim > 0.3:
                        s = content_sim * 0.5  # 纯内容相似度降权
                        sim[c1][c2] = round(s, 4)
                        sim[c2][c1] = round(s, 4)
                    continue
                # 改进的余弦相似度：对热门用户惩罚
                num = sum(
                    1 / math.log(1 + len(self.course_users_of(u)))
                    for u in common
                )
                den = math.sqrt(len(users1) * len(users2))
                s = num / den if den > 0 else 0
                # 混合内容相似度
                content_sim = self._cosine_similarity(
                    self.course_content_vectors.get(c1, {}),
                    self.course_content_vectors.get(c2, {})
                )
                s = 0.7 * s + 0.3 * content_sim
                sim[c1][c2] = round(s, 4)
                sim[c2][c1] = round(s, 4)
        return dict(sim)

    def course_users_of(self, uid):
        """获取用户学习的课程数量（辅助方法）"""
        return self.user_learned.get(uid, set())

    def _compute_user_similarity(self) -> Dict[int, Dict[int, float]]:
        """计算用户间相似度（User-CF）"""
        sim = defaultdict(dict)
        user_ids = list(self.user_course_matrix.keys())
        for i, u1 in enumerate(user_ids):
            for u2 in user_ids[i + 1:]:
                s = self._cosine_similarity(
                    self.user_course_matrix[u1],
                    self.user_course_matrix[u2]
                )
                if s > 0:
                    sim[u1][u2] = round(s, 4)
                    sim[u2][u1] = round(s, 4)
        return dict(sim)

    def _compute_popularity(self) -> Dict[int, float]:
        """计算课程热门度分数"""
        pop = {}
        max_learners = max(
            (len(us) for us in self.course_users.values()), default=1
        )
        for cid in self.courses:
            learners = len(self.course_users.get(cid, set()))
            avg_rating = 0
            ratings = [
                i.get('rating', 0) for i in self.interactions
                if i['course_id'] == cid and i.get('rating', 0) > 0
            ]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
            # 热门度 = 学习人数归一化*0.6 + 平均评分*0.4
            pop[cid] = round(
                (learners / max_learners) * 0.6 + (avg_rating / 5) * 0.4, 4
            )
        return pop

    def recommend_user_cf(self, user_id: int, top_n: int = 8) -> List[dict]:
        """基于用户的协同过滤推荐"""
        learned = self.user_learned.get(user_id, set())
        similar_users = self.user_similarity.get(user_id, {})
        if not similar_users:
            return []

        scores = defaultdict(float)
        sim_sum = defaultdict(float)
        for other_uid, sim in sorted(
            similar_users.items(), key=lambda x: -x[1]
        )[:20]:
            for cid, rating in self.user_course_matrix.get(other_uid, {}).items():
                if cid in learned:
                    continue
                scores[cid] += sim * rating
                sim_sum[cid] += abs(sim)

        results = []
        for cid, score in scores.items():
            if sim_sum[cid] > 0:
                final_score = score / sim_sum[cid]
                results.append({
                    'course_id': cid,
                    'score': round(final_score, 3),
                    'reason': f'与你兴趣相似的 {len([1 for u in similar_users if cid in self.user_learned.get(u, set())])} 位学员也在学',
                    'algorithm': 'user_cf'
                })
        results.sort(key=lambda x: -x['score'])
        return results[:top_n]

    def recommend_item_cf(self, user_id: int, top_n: int = 8) -> List[dict]:
        """基于物品的协同过滤推荐"""
        learned = self.user_learned.get(user_id, set())
        if not learned:
            return []

        scores = defaultdict(float)
        best_source = {}  # 记录每个推荐课程最相似的已学课程
        for learned_cid in learned:
            user_rating = self.user_course_matrix.get(user_id, {}).get(
                learned_cid, 0.5
            )
            for other_cid, sim in self.item_similarity.get(learned_cid, {}).items():
                if other_cid in learned:
                    continue
                contribution = sim * user_rating
                scores[other_cid] += contribution
                if other_cid not in best_source or contribution > best_source[other_cid][1]:
                    best_source[other_cid] = (learned_cid, contribution)

        results = []
        for cid, score in scores.items():
            source_name = self._get_course_name(best_source[cid][0])
            results.append({
                'course_id': cid,
                'score': round(score, 3),
                'reason': f'与你已学课程《{source_name}》内容相似',
                'algorithm': 'item_cf'
            })
        results.sort(key=lambda x: -x['score'])
        return results[:top_n]

    def recommend_content_based(self, user_id: int, top_n: int = 8) -> List[dict]:
        """基于内容的推荐"""
        learned = self.user_learned.get(user_id, set())
        pref = self.user_preference_vectors.get(user_id, {})
        if not pref:
            return self.recommend_popular(top_n)

        results = []
        for cid, course in self.courses.items():
            if cid in learned:
                continue
            content_vec = self.course_content_vectors.get(cid, {})
            score = self._cosine_similarity(pref, content_vec)
            if score > 0:
                # 找出匹配的特征
                matched_cats = [
                    k.replace('cat_', '') for k in pref
                    if k in content_vec and k.startswith('cat_')
                ]
                matched_tags = [
                    k.replace('tag_', '') for k in pref
                    if k in content_vec and k.startswith('tag_')
                ]
                reasons = []
                if matched_cats:
                    reasons.append(f'匹配你偏好的分类：{"、".join(matched_cats[:2])}')
                if matched_tags:
                    reasons.append(f'包含你关注的标签：{"、".join(matched_tags[:2])}')
                results.append({
                    'course_id': cid,
                    'score': round(score, 3),
                    'reason': '；'.join(reasons) if reasons else '符合你的学习偏好',
                    'algorithm': 'content_based'
                })
        results.sort(key=lambda x: -x['score'])
        return results[:top_n]

    def recommend_popular(self, top_n: int = 8) -> List[dict]:
        """热门推荐"""
        results = []
        for cid, pop in self.course_popularity.items():
            course = self.courses[cid]
            learners = len(self.course_users.get(cid, set()))
            results.append({
                'course_id': cid,
                'score': round(pop, 3),
                'reason': f'{learners} 人已学习，热门课程',
                'algorithm': 'popular'
            })
        results.sort(key=lambda x: -x['score'])
        return results[:top_n]

    def recommend_hybrid(self, user_id: int, top_n: int = 8) -> List[dict]:
        """
        混合推荐（加权融合）
        权重：User-CF 0.3 + Item-CF 0.3 + Content 0.25 + Popular 0.15
        冷启动用户：Content 0.4 + Popular 0.6
        """
        learned = self.user_learned.get(user_id, set())
        is_cold_start = len(learned) < 2

        if is_cold_start:
            weights = {'content_based': 0.4, 'popular': 0.6}
        else:
            weights = {
                'user_cf': 0.30,
                'item_cf': 0.30,
                'content_based': 0.25,
                'popular': 0.15
            }

        all_scores = defaultdict(float)
        all_reasons = defaultdict(list)

        recs_map = {
            'user_cf': self.recommend_user_cf(user_id, 20),
            'item_cf': self.recommend_item_cf(user_id, 20),
            'content_based': self.recommend_content_based(user_id, 20),
            'popular': self.recommend_popular(20)
        }

        # 对每个算法的分数做 min-max 归一化后再加权
        for algo, recs in recs_map.items():
            if algo not in weights or not recs:
                continue
            w = weights[algo]
            scores_list = [r['score'] for r in recs]
            s_min, s_max = min(scores_list), max(scores_list)
            s_range = s_max - s_min if s_max > s_min else 1
            for r in recs:
                cid = r['course_id']
                if cid in learned:
                    continue
                norm_score = (r['score'] - s_min) / s_range  # 归一化到 0-1
                all_scores[cid] += norm_score * w
                if r['reason'] and len(all_reasons[cid]) < 2:
                    all_reasons[cid].append(r['reason'])

        results = []
        for cid, score in all_scores.items():
            results.append({
                'course_id': cid,
                'score': round(score, 3),
                'reason': '；'.join(all_reasons[cid][:2]) if all_reasons[cid] else '综合推荐',
                'algorithm': 'hybrid'
            })
        results.sort(key=lambda x: -x['score'])
        return results[:top_n]

    def _get_course_name(self, cid: int) -> str:
        return self.courses.get(cid, {}).get('name', '未知课程')

    def get_user_profile(self, user_id: int) -> dict:
        """获取用户画像摘要"""
        user = self.users.get(user_id, {})
        learned = self.user_learned.get(user_id, set())
        pref = self.user_preference_vectors.get(user_id, {})

        # Top 偏好分类
        cat_scores = {
            k.replace('cat_', ''): v for k, v in pref.items()
            if k.startswith('cat_')
        }
        top_cats = sorted(cat_scores.items(), key=lambda x: -x[1])[:3]

        tag_scores = {
            k.replace('tag_', ''): v for k, v in pref.items()
            if k.startswith('tag_')
        }
        top_tags = sorted(tag_scores.items(), key=lambda x: -x[1])[:5]

        total_learning = sum(
            i.get('progress', 0) for i in self.interactions
            if i['user_id'] == user_id
        )

        return {
            'user': user,
            'learned_count': len(learned),
            'total_progress': round(total_learning, 1),
            'top_categories': [c for c, _ in top_cats],
            'top_tags': [t for t, _ in top_tags],
            'is_cold_start': len(learned) < 2
        }

    def record_interaction(self, user_id: int, course_id: int,
                           progress: float = 0, rating: int = 0,
                           behavior_weight: float = 0):
        """记录用户学习行为并更新模型"""
        # 检查是否已有记录
        existing = None
        for inter in self.interactions:
            if inter['user_id'] == user_id and inter['course_id'] == course_id:
                existing = inter
                break

        if existing:
            existing['progress'] = max(existing.get('progress', 0), progress)
            if rating > 0:
                existing['rating'] = rating
            existing['behavior_weight'] = max(
                existing.get('behavior_weight', 0), behavior_weight
            )
        else:
            self.interactions.append({
                'user_id': user_id,
                'course_id': course_id,
                'progress': progress,
                'rating': rating,
                'behavior_weight': behavior_weight
            })
            self.user_learned[user_id].add(course_id)
            self.course_users[course_id].add(user_id)

        # 重建矩阵和偏好
        self.user_course_matrix = self._build_matrix()
        self.user_preference_vectors = self._build_user_preferences()
        self.item_similarity = self._compute_item_similarity()
        self.user_similarity = self._compute_user_similarity()
        self.course_popularity = self._compute_popularity()
