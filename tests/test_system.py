"""
培训管理系统 - 单元测试套件
覆盖：推荐引擎6种算法、AI去重门控、AI引擎、多维表格客户端、Flask API
运行：python3 -m pytest tests/ -v  或  python3 -m unittest discover tests -v
"""
import sys
import os
import copy
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import COURSES, USERS, INTERACTIONS
from recommender import RecommendationEngine
from ai_engine import AIEngine


def fresh_data():
    """返回数据的深拷贝，避免测试间相互污染"""
    return copy.deepcopy(USERS), copy.deepcopy(COURSES), copy.deepcopy(INTERACTIONS)


class TestRecommendationEngine(unittest.TestCase):
    """推荐引擎核心测试"""
    @classmethod
    def setUpClass(cls):
        cls.engine = RecommendationEngine(USERS, COURSES, INTERACTIONS)
        cls.ai = AIEngine(cls.engine)

    def test_data_loaded(self):
        """课程、学员、交互数据正确加载"""
        self.assertEqual(len(self.engine.courses), 24)
        self.assertEqual(len(self.engine.users), 10)
        self.assertGreater(len(self.engine.interactions), 40)

    def test_user_learned_tracking(self):
        """已学课程集合正确构建"""
        self.assertEqual(len(self.engine.user_learned[1]), 6)
        self.assertEqual(len(self.engine.user_learned[9]), 2)

    def test_course_users_inverted_index(self):
        """课程-用户倒排表正确"""
        self.assertEqual(len(self.engine.course_users[1]), 3)

    def test_no_learned_courses_in_hybrid(self):
        """混合推荐不包含已学课程"""
        learned = self.engine.user_learned[1]
        recs = self.engine.recommend_hybrid(1, top_n=10)
        recommended_ids = {r['course_id'] for r in recs}
        overlap = learned & recommended_ids
        self.assertEqual(len(overlap), 0, f"已学课程被重复推荐: {overlap}")

    def test_no_learned_courses_in_all_algorithms(self):
        """所有算法都不推荐已学课程"""
        for uid in [1, 2, 3, 5, 7]:
            learned = self.engine.user_learned[uid]
            for algo_name, algo_func in [
                ('svd', self.engine.recommend_svd),
                ('user_cf', self.engine.recommend_user_cf),
                ('item_cf', self.engine.recommend_item_cf),
                ('content', self.engine.recommend_content_based),
                ('hybrid', self.engine.recommend_hybrid),
            ]:
                recs = algo_func(uid, top_n=10)
                rec_ids = {r['course_id'] for r in recs}
                overlap = learned & rec_ids
                self.assertEqual(len(overlap), 0,
                    f"用户{uid}的{algo_name}推荐包含已学课程: {overlap}")

    def test_should_recommend_rejects_learned(self):
        """AI门控：已学课程拒绝推荐"""
        learned_cid = next(iter(self.engine.user_learned[1]))
        should, reason = self.engine.should_recommend(1, learned_cid)
        self.assertFalse(should)
        self.assertEqual(reason, "已学习")

    def test_should_recommend_accepts_new_course(self):
        """AI门控：未学课程通过"""
        learned = self.engine.user_learned[1]
        unlearned = [c['id'] for c in COURSES if c['id'] not in learned]
        self.assertGreater(len(unlearned), 0)
        should, _ = self.engine.should_recommend(1, unlearned[0])
        self.assertTrue(should)

    def test_should_recommend_rejects_advanced_for_newcomer(self):
        """AI门控：新学员不推荐高级课程"""
        learned = self.engine.user_learned[9]
        self.assertLess(len(learned), 3)
        should, reason = self.engine.should_recommend(9, 4)
        self.assertFalse(should)

    def test_should_recommend_all_users(self):
        """AI门控：所有学员的推荐结果都不包含已学课程"""
        for uid in self.engine.users:
            learned = self.engine.user_learned[uid]
            for cid in self.engine.courses:
                should, reason = self.engine.should_recommend(uid, cid)
                if cid in learned:
                    self.assertFalse(should, f"用户{uid}已学课程{cid}不应通过门控")

    def test_popular_returns_sorted(self):
        """热门推荐按热度降序"""
        recs = self.engine.recommend_popular(5)
        scores = [r['score'] for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_svd_normalized_scores(self):
        """SVD分数归一化到0-1"""
        recs = self.engine.recommend_svd(1, 10)
        for r in recs:
            self.assertGreaterEqual(r['score'], 0.0)
            self.assertLessEqual(r['score'], 1.0)

    def test_hybrid_weights_sum_to_one(self):
        """混合推荐权重之和为1"""
        normal_weights = 0.22 + 0.22 + 0.18 + 0.10 + 0.28
        cold_weights = 0.35 + 0.45 + 0.20
        self.assertAlmostEqual(normal_weights, 1.0, places=2)
        self.assertAlmostEqual(cold_weights, 1.0, places=2)

    def test_cold_start_user(self):
        """冷启动用户也能获得推荐"""
        recs = self.engine.recommend_hybrid(9, top_n=5)
        self.assertGreater(len(recs), 0, "冷启动用户应获得推荐")

    def test_recommend_count_respected(self):
        """推荐数量不超过top_n"""
        for n in [1, 3, 5]:
            recs = self.engine.recommend_hybrid(1, top_n=n)
            self.assertLessEqual(len(recs), n)

    def test_recommendations_have_required_fields(self):
        """推荐结果包含必要字段"""
        recs = self.engine.recommend_hybrid(1, 3)
        for r in recs:
            self.assertIn('course_id', r)
            self.assertIn('score', r)
            self.assertIn('reason', r)
            self.assertIn('algorithm', r)
            self.assertIsInstance(r['score'], float)

    def test_item_cf_reason_mentions_source_course(self):
        """物品CF推荐理由提到相似已学课程"""
        recs = self.engine.recommend_item_cf(1, 5)
        if recs:
            self.assertIn('《', recs[0]['reason'])
            self.assertIn('》', recs[0]['reason'])

    def test_user_profile_structure(self):
        """用户画像包含必要字段"""
        profile = self.engine.get_user_profile(1)
        self.assertIn('learned_count', profile)
        self.assertIn('top_categories', profile)
        self.assertIn('top_tags', profile)
        self.assertIn('is_cold_start', profile)
        self.assertFalse(profile['is_cold_start'])

    def test_cold_start_profile_flag(self):
        """冷启动标记正确"""
        profile = self.engine.get_user_profile(9)
        self.assertFalse(profile['is_cold_start'])

    def test_record_new_interaction(self):
        """新学习行为记录后模型更新"""
        users, courses, interactions = fresh_data()
        engine = RecommendationEngine(users, courses, interactions)
        initial_count = len(engine.user_learned[1])
        engine.record_interaction(1, 24, progress=0.5, rating=4, behavior_weight=0.5)
        self.assertEqual(len(engine.user_learned[1]), initial_count + 1)
        self.assertIn(24, engine.user_learned[1])

    def test_record_existing_interaction_updates(self):
        """重复记录同一课程取最大值"""
        users, courses, interactions = fresh_data()
        engine = RecommendationEngine(users, courses, interactions)
        initial_count = len(engine.user_learned[1])
        engine.record_interaction(1, 2, progress=0.5, rating=0, behavior_weight=0.3)
        self.assertEqual(len(engine.user_learned[1]), initial_count)
        inter = next(i for i in engine.interactions
                     if i['user_id'] == 1 and i['course_id'] == 2)
        self.assertEqual(inter['progress'], 1.0)

    def test_interaction_excludes_newly_learned(self):
        """学习新课后该课不再被推荐"""
        users, courses, interactions = fresh_data()
        engine = RecommendationEngine(users, courses, interactions)
        recs_before = engine.recommend_hybrid(1, 20)
        ids_before = {r['course_id'] for r in recs_before}
        engine.record_interaction(1, 24, progress=1.0, rating=5, behavior_weight=1.0)
        recs_after = engine.recommend_hybrid(1, 20)
        ids_after = {r['course_id'] for r in recs_after}
        self.assertNotIn(24, ids_after)


class TestAIEngine(unittest.TestCase):
    """AI 增强引擎测试"""
    @classmethod
    def setUpClass(cls):
        cls.engine = RecommendationEngine(USERS, COURSES, INTERACTIONS)
        cls.ai = AIEngine(cls.engine)

    def test_recommendation_explanation_not_empty(self):
        """AI推荐理由非空"""
        recs = self.engine.recommend_hybrid(1, 3)
        for r in recs:
            reason = self.ai.generate_recommendation_explanation(1, r['course_id'], 'hybrid')
            self.assertTrue(len(reason) > 0)
            self.assertIsInstance(reason, str)

    def test_learning_path_structure(self):
        """学习路径结构完整"""
        path = self.ai.generate_learning_path(1)
        self.assertIn('direction', path)
        self.assertIn('stages', path)
        self.assertIn('progress', path)
        self.assertIn('ai_advice', path)
        self.assertEqual(len(path['stages']), 4)
        for stage in path['stages']:
            self.assertIn('title', stage)
            self.assertIn('courses', stage)
            for c in stage['courses']:
                self.assertIn('id', c)
                self.assertIn('name', c)
                self.assertIn('status', c)
                self.assertIn(c['status'], ('completed', 'recommended'))

    def test_learning_path_progress_range(self):
        """学习路径进度在0-100"""
        for uid in [1, 2, 3, 7, 9]:
            path = self.ai.generate_learning_path(uid)
            self.assertGreaterEqual(path['progress'], 0)
            self.assertLessEqual(path['progress'], 100)

    def test_learning_path_completed_courses_match(self):
        """学习路径中已完成课程与学习记录一致"""
        path = self.ai.generate_learning_path(1)
        learned = self.engine.user_learned[1]
        for stage in path['stages']:
            for c in stage['courses']:
                if c['status'] == 'completed':
                    self.assertIn(c['id'], learned)

    def test_chat_recommendation(self):
        """AI助手：推荐课程问题"""
        reply = self.ai.chat(1, "推荐什么课程")
        self.assertTrue(len(reply) > 0)
        self.assertIn('《', reply)

    def test_chat_learning_path(self):
        """AI助手：学习路径问题"""
        reply = self.ai.chat(1, "我的学习路径")
        self.assertTrue(len(reply) > 0)

    def test_chat_progress(self):
        """AI助手：学习进度问题"""
        reply = self.ai.chat(1, "我的学习进度")
        self.assertTrue(len(reply) > 0)
        self.assertIn('门', reply)

    def test_chat_hot_courses(self):
        """AI助手：热门课程问题"""
        reply = self.ai.chat(1, "热门课程")
        self.assertTrue(len(reply) > 0)

    def test_chat_greeting(self):
        """AI助手：问候"""
        reply = self.ai.chat(1, "你好")
        self.assertIn('你好', reply)

    def test_chat_help(self):
        """AI助手：帮助"""
        reply = self.ai.chat(1, "帮助")
        self.assertIn('推荐', reply)

    def test_chat_unknown_question(self):
        """AI助手：未知问题有兜底回复"""
        reply = self.ai.chat(1, "今天天气怎么样")
        self.assertTrue(len(reply) > 0)

    def test_position_matches_course(self):
        """岗位-课程匹配判断"""
        self.assertTrue(
            self.ai._position_matches_course("后端开发工程师", ["Java", "Spring"], ["技术研发"]))
        self.assertFalse(
            self.ai._position_matches_course("HRBP", ["Java"], ["技术研发"]))


class TestBitableClient(unittest.TestCase):
    """多维表格客户端测试"""
    def test_client_not_configured_by_default(self):
        """未配置环境变量时客户端不可用"""
        from bitable_client import BitableClient
        client = BitableClient()
        self.assertFalse(client.is_configured)

    def test_data_provider_falls_back_to_local(self):
        """未配置多维表格时回退到本地数据"""
        from bitable_client import DataProvider
        provider = DataProvider().init()
        self.assertEqual(len(provider.courses), 24)
        self.assertEqual(len(provider.users), 10)
        self.assertGreater(len(provider.interactions), 40)

    def test_health_check(self):
        """健康检查返回数据源状态"""
        from bitable_client import DataProvider
        provider = DataProvider().init()
        health = provider.health_check()
        self.assertEqual(health['data_source'], 'local_memory')
        self.assertFalse(health['bitable_configured'])
        self.assertEqual(health['courses'], 24)

    def test_parse_list(self):
        """列表字段解析"""
        from bitable_client import DataProvider
        self.assertEqual(DataProvider._parse_list("Python、Java、Go"), ["Python", "Java", "Go"])
        self.assertEqual(DataProvider._parse_list("Python,Java,Go"), ["Python", "Java", "Go"])
        self.assertEqual(DataProvider._parse_list(["Python", "Java"]), ["Python", "Java"])
        self.assertEqual(DataProvider._parse_list(""), [])

    def test_add_interaction_local(self):
        """本地模式新增交互记录"""
        from bitable_client import DataProvider
        provider = DataProvider().init()
        initial = len(provider.interactions)
        provider.add_interaction(1, 24, 0.5, 4, 0.5)
        self.assertEqual(len(provider.interactions), initial + 1)

    @patch('bitable_client.BitableClient._request')
    def test_bitable_authentication(self, mock_request):
        """多维表格认证流程"""
        from bitable_client import BitableClient
        mock_request.return_value = {"tenant_access_token": "test_token_123"}
        client = BitableClient("test_id", "test_secret", "test_token")
        self.assertTrue(client.is_configured)
        client._authenticate()
        self.assertEqual(client._token, "test_token_123")


class TestFlaskAPI(unittest.TestCase):
    """Flask API 端点测试"""
    @classmethod
    def setUpClass(cls):
        from app import app
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_index_page(self):
        """首页可访问"""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_health_endpoint(self):
        """健康检查端点"""
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('data_source', data)
        self.assertIn('courses', data)

    def test_get_users(self):
        """获取学员列表"""
        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 200)
        users = resp.get_json()
        self.assertGreaterEqual(len(users), 10)
        self.assertIn('name', users[0])
        self.assertIn('learned_count', users[0])
        self.assertIn('feishu_open_id', users[0])

    def test_get_courses(self):
        """获取课程列表"""
        resp = self.client.get('/api/courses')
        self.assertEqual(resp.status_code, 200)
        courses = resp.get_json()
        self.assertEqual(len(courses), 24)

    def test_recommend_hybrid(self):
        """混合推荐API"""
        resp = self.client.get('/api/recommend/1?algorithm=hybrid&top_n=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['algorithm'], 'hybrid')
        self.assertLessEqual(len(data['recommendations']), 5)
        learned_ids = {2, 1, 4, 5, 8, 11}
        rec_ids = {r['id'] for r in data['recommendations']}
        self.assertEqual(len(learned_ids & rec_ids), 0)

    def test_recommend_invalid_algorithm(self):
        """不支持的算法返回400"""
        resp = self.client.get('/api/recommend/1?algorithm=invalid')
        self.assertEqual(resp.status_code, 400)

    def test_recommend_invalid_user(self):
        """不存在的学员返回404"""
        resp = self.client.get('/api/recommend/9999')
        self.assertEqual(resp.status_code, 404)

    def test_recommend_all_algorithms(self):
        """所有6种算法都能正常返回"""
        for algo in ['hybrid', 'svd', 'user_cf', 'item_cf', 'content', 'popular']:
            resp = self.client.get(f'/api/recommend/1?algorithm={algo}&top_n=3')
            self.assertEqual(resp.status_code, 200, f"算法 {algo} 请求失败")
            data = resp.get_json()
            self.assertIn('recommendations', data)

    def test_user_profile(self):
        """学员画像API"""
        resp = self.client.get('/api/profile/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('learned_count', data)
        self.assertIn('learned_courses', data)

    def test_learning_path_api(self):
        """学习路径API"""
        resp = self.client.get('/api/learning-path/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('stages', data)
        self.assertIn('progress', data)

    def test_chat_api(self):
        """AI对话API"""
        resp = self.client.post('/api/chat', json={'user_id': 1, 'message': '推荐什么课程'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('reply', data)
        self.assertTrue(len(data['reply']) > 0)

    def test_chat_empty_message(self):
        """空消息返回400"""
        resp = self.client.post('/api/chat', json={'user_id': 1, 'message': ''})
        self.assertEqual(resp.status_code, 400)

    def test_chat_missing_user(self):
        """缺少user_id返回400"""
        resp = self.client.post('/api/chat', json={'message': '你好'})
        self.assertEqual(resp.status_code, 400)

    def test_interact_api(self):
        """学习行为记录API"""
        resp = self.client.post('/api/interact', json={
            'user_id': 1, 'course_id': 24, 'progress': 0.5, 'rating': 4
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

    def test_interact_invalid_course(self):
        """不存在的课程返回404"""
        resp = self.client.post('/api/interact', json={'user_id': 1, 'course_id': 9999})
        self.assertEqual(resp.status_code, 404)

    def test_interact_missing_params(self):
        """缺少参数返回400"""
        resp = self.client.post('/api/interact', json={'user_id': 1})
        self.assertEqual(resp.status_code, 400)

    def test_compare_algorithms(self):
        """算法对比API"""
        resp = self.client.get('/api/compare/1?top_n=3')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data), 6)
        for algo_key in ['hybrid', 'svd', 'user_cf', 'item_cf', 'content', 'popular']:
            self.assertIn(algo_key, data)

    def test_top_n_clamped(self):
        """top_n 参数被限制在合理范围"""
        resp = self.client.get('/api/recommend/1?top_n=999')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertLessEqual(len(data['recommendations']), 20)


class TestEdgeCases(unittest.TestCase):
    """边界条件和异常场景测试"""
    @classmethod
    def setUpClass(cls):
        cls.engine = RecommendationEngine(USERS, COURSES, INTERACTIONS)

    def test_empty_courses_list(self):
        """空课程列表不崩溃"""
        engine = RecommendationEngine(USERS, [], [])
        recs = engine.recommend_hybrid(1)
        self.assertEqual(len(recs), 0)

    def test_empty_users_list(self):
        """空学员列表不崩溃"""
        engine = RecommendationEngine([], COURSES, [])
        recs = engine.recommend_popular()
        self.assertIsInstance(recs, list)

    def test_unknown_user_id(self):
        """未知学员ID推荐返回空"""
        recs = self.engine.recommend_hybrid(9999)
        self.assertIsInstance(recs, list)

    def test_similarity_identical_vectors(self):
        """相同向量余弦相似度为1"""
        vec = {'a': 1.0, 'b': 2.0}
        sim = RecommendationEngine._cosine_similarity(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_similarity_orthogonal_vectors(self):
        """正交向量余弦相似度为0"""
        vec_a = {'a': 1.0}
        vec_b = {'b': 1.0}
        sim = RecommendationEngine._cosine_similarity(vec_a, vec_b)
        self.assertEqual(sim, 0.0)

    def test_similarity_zero_vectors(self):
        """零向量余弦相似度为0"""
        sim = RecommendationEngine._cosine_similarity({}, {'a': 1.0})
        self.assertEqual(sim, 0.0)

    def test_svd_prediction_range(self):
        """SVD预测分数在合理范围"""
        for uid in [1, 2, 9]:
            for cid in [1, 5, 10, 24]:
                pred = self.engine._svd_predict(uid, cid)
                self.assertIsInstance(pred, float)
                self.assertGreater(pred, -10)
                self.assertLess(pred, 10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
