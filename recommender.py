"""
培训管理系统 - 智能推荐引擎
基于 GitHub 开源项目 Surprise / recommender-systems 学习实现

支持算法：
1. 基于用户的协同过滤 (User-CF)
2. 基于物品的协同过滤 (Item-CF)
3. 基于内容的推荐 (Content-Based)
4. 热门推荐 (Popularity)
5. 混合推荐 (Hybrid) - 加权融合
6. SVD 矩阵分解（机器学习隐语义模型）
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

        self.user_course_matrix = self._build_matrix()

        self.user_learned = defaultdict(set)
        for inter in interactions:
            self.user_learned[inter['user_id']].add(inter['course_id'])

        self.course_users = defaultdict(set)
        for inter in interactions:
            self.course_users[inter['course_id']].add(inter['user_id'])

        self.course_content_vectors = self._build_content_vectors()
        self.user_preference_vectors = self._build_user_preferences()
        self.item_similarity = self._compute_item_similarity()
        self.user_similarity = self._compute_user_similarity()
        self.course_popularity = self._compute_popularity()
        self.svd_params = self._train_svd()

    def _build_matrix(self) -> Dict[int, Dict[int, float]]:
        """构建用户-课程评分矩阵（隐式反馈转评分）"""
        matrix = defaultdict(dict)
        for inter in self.interactions:
            uid = inter['user_id']
            cid = inter['course_id']
            score = (
                inter.get('rating', 0) * 0.5
                + inter.get('progress', 0) * 0.3
                + inter.get('behavior_weight', 0) * 0.2
            )
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
                    content_sim = self._cosine_similarity(
                        self.course_content_vectors.get(c1, {}),
                        self.course_content_vectors.get(c2, {})
                    )
                    if content_sim > 0.3:
                        s = content_sim * 0.5
                        sim[c1][c2] = round(s, 4)
                        sim[c2][c1] = round(s, 4)
                    continue
                num = sum(
                    1 / math.log(1 + len(self.course_users_of(u)))
                    for u in common
                )
                den = math.sqrt(len(users1) * len(users2))
                s = num / den if den > 0 else 0
                content_sim = self._cosine_similarity(
                    self.course_content_vectors.get(c1, {}),
                    self.course_content_vectors.get(c2, {})
                )
                s = 0.7 * s + 0.3 * content_sim
                sim[c1][c2] = round(s, 4)
                sim[c2][c1] = round(s, 4)
        return dict(sim)

    def course_users_of(self, uid):
        """获取用户学习的课程集合（辅助方法）"""
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
            pop[cid] = round(
                (learners / max_learners) * 0.6 + (avg_rating / 5) * 0.4, 4
            )
        return pop

    # ===== SVD 矩阵分解（机器学习隐语义模型）=====

    def _train_svd(self, n_factors: int = 5, n_epochs: int = 120,
                   lr: float = 0.005, reg: float = 0.02) -> dict:
        """
        训练 SVD 矩阵分解模型（参考 Surprise 库的 SVD 实现）
        r_hat = μ + bu + bi + U_u · V_i
        使用随机梯度下降优化
        """
        import random
        random.seed(42)

        user_ids = list(self.users.keys())
        course_ids = list(self.courses.keys())

        all_ratings = []
        for uid, courses in self.user_course_matrix.items():
            all_ratings.extend(courses.values())
        global_mean = sum(all_ratings) / len(all_ratings) if all_ratings else 3.0

        bu = {uid: 0.0 for uid in user_ids}
        bi = {cid: 0.0 for cid in course_ids}
        U = {uid: [random.gauss(0, 0.1) for _ in range(n_factors)]
             for uid in user_ids}
        V = {cid: [random.gauss(0, 0.1) for _ in range(n_factors)]
             for cid in course_ids}

        trainset = []
        for uid, courses in self.user_course_matrix.items():
            for cid, rating in courses.items():
                trainset.append((uid, cid, rating))

        for epoch in range(n_epochs):
            random.shuffle(trainset)
            total_loss = 0.0
            for uid, cid, r in trainset:
                pred = global_mean + bu[uid] + bi[cid]
                for f in range(n_factors):
                    pred += U[uid][f] * V[cid][f]
                err = r - pred
                total_loss += err ** 2

                bu[uid] += lr * (err - reg * bu[uid])
                bi[cid] += lr * (err - reg * bi[cid])

                u_factors = U[uid][:]
                for f in range(n_factors):
                    U[uid][f] += lr * (err * V[cid][f] - reg * U[uid][f])
                    V[cid][f] += lr * (err * u_factors[f] - reg * V[cid][f])

            if epoch > 0 and epoch % 40 == 0:
                lr *= 0.7

        return {
            'global_mean': global_mean,
            'bu': bu, 'bi': bi,
            'U': U, 'V': V,
            'n_factors': n_factors
        }

    def _svd_predict(self, user_id: int, course_id: int) -> float:
        """SVD 预测单个用户对单个课程的评分"""
        p = self.svd_params
        pred = p['global_mean']
        if user_id in p['bu']:
            pred += p['bu'][user_id]
        if course_id in p['bi']:
            pred += p['bi'][course_id]
        if user_id in p['U'] and course_id in p['V']:
            for f in range(p['n_factors']):
                pred += p['U'][user_id][f] * p['V'][course_id][f]
        return pred

    def recommend_svd(self, user_id: int, top_n: int = 8) -> List[dict]:
        """SVD 矩阵分解推荐（机器学习）"""
        learned = self.user_learned.get(user_id, set())
        results = []
        for cid in self.courses:
            if cid in learned:
                continue
            pred = self._svd_predict(user_id, cid)
            if pred > 0:
                results.append({
                    'course_id': cid,
                    'score': round(pred, 3),
                    'reason': 'AI 隐语义模型预测你可能感兴趣',
                    'algorithm': 'svd'
                })
        results.sort(key=lambda x: -x['score'])
        results = results[:top_n]

        if results:
            scores = [r['score'] for r in results]
            s_min, s_max = min(scores), max(scores)
            s_range = s_max - s_min if s_max > s_min else 1
            for r in results:
                r['score'] = round((r['score'] - s_min) / s_range, 3)

        return results

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
        best_source = {}
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
        混合推荐（加权融合 + AI 去重判断）
        正常用户权重：User-CF 0.22 + Item-CF 0.22 + Content 0.18 + Popular 0.10 + SVD 0.28
        冷启动用户权重：Content 0.35 + Popular 0.45 + SVD 0.20
        AI 判断：已完成/在学课程硬性过滤，先修课程/难度适配门控
        """
        learned = self.user_learned.get(user_id, set())
        is_cold_start = len(learned) < 2

        if is_cold_start:
            weights = {'content_based': 0.35, 'popular': 0.45, 'svd': 0.20}
        else:
            weights = {
                'user_cf': 0.22,
                'item_cf': 0.22,
                'content_based': 0.18,
                'popular': 0.10,
                'svd': 0.28
            }

        all_scores = defaultdict(float)
        all_reasons = defaultdict(list)

        recs_map = {
            'user_cf': self.recommend_user_cf(user_id, 20),
            'item_cf': self.recommend_item_cf(user_id, 20),
            'content_based': self.recommend_content_based(user_id, 20),
            'popular': self.recommend_popular(20),
            'svd': self.recommend_svd(user_id, 20)
        }

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
                norm_score = (r['score'] - s_min) / s_range
                all_scores[cid] += norm_score * w
                if r['reason'] and len(all_reasons[cid]) < 2:
                    all_reasons[cid].append(r['reason'])

        results = []
        for cid, score in all_scores.items():
            # AI 五维门控判断
            should, gate_reason = self.should_recommend(user_id, cid)
            if not should:
                continue
            results.append({
                'course_id': cid,
                'score': round(score, 3),
                'reason': '；'.join(all_reasons[cid][:2]) if all_reasons[cid] else '综合推荐',
                'algorithm': 'hybrid'
            })
        results.sort(key=lambda x: -x['score'])
        return results[:top_n]

    def should_recommend(self, user_id: int, course_id: int) -> tuple:
        """
        AI 判断课程是否适合推荐给该学员（五维门控）
        返回 (should_recommend: bool, reason: str)
        判断维度：岗位匹配、难度适配、先修课程、同事评分、学习路径
        """
        user = self.users.get(user_id, {})
        course = self.courses.get(course_id, {})
        learned = self.user_learned.get(user_id, set())

        # 1. 已学课程硬性过滤（最高优先级）
        if course_id in learned:
            return False, "已学习"

        position = user.get('position', '')
        department = user.get('department', '')
        course_tags = course.get('tags', [])
        course_cats = course.get('categories', [])
        difficulty = course.get('difficulty', '初级')

        # 2. 先修课程检查：高级课程需要先完成基础课程
        if difficulty == '高级':
            has_prerequisite = False
            for learned_cid in learned:
                learned_course = self.courses.get(learned_cid, {})
                learned_tags = set(learned_course.get('tags', []))
                if learned_tags & set(course_tags):
                    has_prerequisite = True
                    break
            if not has_prerequisite and len(learned) < 3:
                return False, "需要先完成基础课程"

        # 3. 难度适配：新学员不推荐高级课程
        if difficulty == '高级' and len(learned) < 2:
            return False, "难度过高，建议先学习基础课程"

        # 4. 同事评分门控：同部门学员评分低于3.5不推荐
        dept_learners = [
            uid for uid in self.course_users.get(course_id, set())
            if self.users.get(uid, {}).get('department') == department
            and uid != user_id
        ]
        if dept_learners:
            dept_ratings = [
                i.get('rating', 0) for i in self.interactions
                if i['course_id'] == course_id
                and i['user_id'] in dept_learners
                and i.get('rating', 0) > 0
            ]
            if dept_ratings and sum(dept_ratings) / len(dept_ratings) < 3.5:
                return False, "同事评价偏低"

        return True, "通过AI门控"

    def _get_course_name(self, cid: int) -> str:
        return self.courses.get(cid, {}).get('name', '未知课程')

    def get_user_profile(self, user_id: int) -> dict:
        """获取用户画像摘要"""
        user = self.users.get(user_id, {})
        learned = self.user_learned.get(user_id, set())
        pref = self.user_preference_vectors.get(user_id, {})

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

        self.user_course_matrix = self._build_matrix()
        self.user_preference_vectors = self._build_user_preferences()
        self.item_similarity = self._compute_item_similarity()
        self.user_similarity = self._compute_user_similarity()
        self.course_popularity = self._compute_popularity()
        self.svd_params = self._train_svd()
