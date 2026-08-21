"""
培训管理系统 - 智能推荐服务
Flask Web 应用，提供推荐 API 和页面
支持飞书多维表格数据源和本地内存数据自动切换
"""
import logging
from flask import Flask, jsonify, request, render_template
from recommender import RecommendationEngine
from ai_engine import AIEngine
from bitable_client import DataProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化数据提供者（自动判断多维表格 or 本地数据）
data_provider = DataProvider().init()

# 初始化推荐引擎和 AI 引擎
engine = RecommendationEngine(
    data_provider.users,
    data_provider.courses,
    data_provider.interactions
)
ai = AIEngine(engine)

ALGORITHM_MAP = {
    'hybrid': ('混合推荐（AI 智能融合）', engine.recommend_hybrid),
    'svd': ('SVD 矩阵分解（机器学习）', engine.recommend_svd),
    'user_cf': ('基于用户的协同过滤', engine.recommend_user_cf),
    'item_cf': ('基于物品的协同过滤', engine.recommend_item_cf),
    'content': ('基于内容的推荐', engine.recommend_content_based),
    'popular': ('热门推荐', engine.recommend_popular),
}

MAX_TOP_N = 20  # 推荐数量上限


def enrich_course(course_id: int, score: float, reason: str,
                  algorithm: str, user_id: int = None) -> dict:
    """补充课程详情，并生成 AI 增强推荐理由"""
    course = engine.courses.get(course_id, {})
    learners = len(engine.course_users.get(course_id, set()))
    # AI 增强推荐理由（所有算法都生成）
    ai_reason = reason
    if user_id:
        ai_reason = ai.generate_recommendation_explanation(
            user_id, course_id, algorithm
        )
    return {
        'id': course_id,
        'name': course.get('name', ''),
        'desc': course.get('desc', ''),
        'categories': course.get('categories', []),
        'tags': course.get('tags', []),
        'difficulty': course.get('difficulty', ''),
        'duration': course.get('duration', 0),
        'instructor': course.get('instructor', ''),
        'cover_color': course.get('cover_color', '#3B82F6'),
        'learners': learners,
        'score': score,
        'reason': ai_reason,
        'algorithm': algorithm,
    }


def validate_user(user_id: int):
    """验证学员是否存在，返回 (user, error_response)"""
    if user_id not in engine.users:
        return None, (jsonify({'error': f'学员不存在: {user_id}'}), 404)
    return engine.users[user_id], None


def validate_course(course_id: int):
    """验证课程是否存在"""
    if course_id not in engine.courses:
        return False
    return True


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify(data_provider.health_check())


@app.route('/api/users')
def get_users():
    """获取所有用户"""
    return jsonify([
        {
            'id': u['id'],
            'name': u['name'],
            'department': u['department'],
            'position': u['position'],
            'avatar': u['avatar'],
            'learned_count': len(engine.user_learned.get(u['id'], set()))
        }
        for u in data_provider.users
    ])


@app.route('/api/courses')
def get_courses():
    """获取所有课程"""
    return jsonify([
        {
            'id': c['id'],
            'name': c['name'],
            'desc': c['desc'],
            'categories': c['categories'],
            'tags': c['tags'],
            'difficulty': c['difficulty'],
            'duration': c['duration'],
            'instructor': c['instructor'],
            'cover_color': c['cover_color'],
            'learners': len(engine.course_users.get(c['id'], set()))
        }
        for c in data_provider.courses
    ])


@app.route('/api/recommend/<int:user_id>')
def recommend(user_id):
    """获取推荐结果"""
    _, err = validate_user(user_id)
    if err:
        return err

    algo = request.args.get('algorithm', 'hybrid')
    top_n = request.args.get('top_n', 8, type=int)
    top_n = max(1, min(top_n, MAX_TOP_N))  # 限制范围

    if algo not in ALGORITHM_MAP:
        return jsonify({'error': f'不支持的算法: {algo}'}), 400

    algo_name, algo_func = ALGORITHM_MAP[algo]
    # 热门推荐不需要 user_id
    if algo == 'popular':
        raw_recs = algo_func(top_n)
    else:
        raw_recs = algo_func(user_id, top_n)

    recommendations = [
        enrich_course(r['course_id'], r['score'], r['reason'],
                      r['algorithm'], user_id)
        for r in raw_recs
    ]
    profile = engine.get_user_profile(user_id)
    return jsonify({
        'user_id': user_id,
        'algorithm': algo,
        'algorithm_name': algo_name,
        'profile': profile,
        'recommendations': recommendations
    })


@app.route('/api/profile/<int:user_id>')
def get_profile(user_id):
    """获取用户画像"""
    _, err = validate_user(user_id)
    if err:
        return err

    profile = engine.get_user_profile(user_id)
    learned_courses = []
    for cid in engine.user_learned.get(user_id, set()):
        course = engine.courses.get(cid, {})
        inter = next(
            (i for i in data_provider.interactions
             if i['user_id'] == user_id and i['course_id'] == cid),
            {}
        )
        learned_courses.append({
            'id': cid,
            'name': course.get('name', ''),
            'cover_color': course.get('cover_color', '#3B82F6'),
            'progress': inter.get('progress', 0),
            'rating': inter.get('rating', 0),
            'categories': course.get('categories', []),
            'tags': course.get('tags', []),
        })
    learned_courses.sort(key=lambda x: -x['progress'])
    profile['learned_courses'] = learned_courses
    return jsonify(profile)


@app.route('/api/interact', methods=['POST'])
def interact():
    """记录学习行为（实时更新推荐）"""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    course_id = data.get('course_id')

    if not user_id or not course_id:
        return jsonify({'error': '缺少 user_id 或 course_id'}), 400

    user_id, course_id = int(user_id), int(course_id)
    _, err = validate_user(user_id)
    if err:
        return err
    if not validate_course(course_id):
        return jsonify({'error': f'课程不存在: {course_id}'}), 404

    progress = max(0.0, min(1.0, float(data.get('progress', 0))))
    rating = max(0, min(5, int(data.get('rating', 0))))
    behavior_weight = max(0.0, min(1.0, float(data.get('behavior_weight', 0.5))))

    engine.record_interaction(user_id, course_id, progress, rating, behavior_weight)
    data_provider.add_interaction(user_id, course_id, progress, rating, behavior_weight)
    return jsonify({'success': True, 'message': '学习行为已记录，AI 推荐已更新'})


@app.route('/api/compare/<int:user_id>')
def compare_algorithms(user_id):
    """对比不同算法的推荐结果"""
    _, err = validate_user(user_id)
    if err:
        return err

    top_n = request.args.get('top_n', 5, type=int)
    top_n = max(1, min(top_n, MAX_TOP_N))
    results = {}
    for algo_key, (algo_name, algo_func) in ALGORITHM_MAP.items():
        if algo_key == 'popular':
            raw = algo_func(top_n)
        else:
            raw = algo_func(user_id, top_n)
        results[algo_key] = {
            'name': algo_name,
            'courses': [
                enrich_course(r['course_id'], r['score'], r['reason'],
                              r['algorithm'], user_id)
                for r in raw
            ]
        }
    return jsonify(results)


@app.route('/api/learning-path/<int:user_id>')
def learning_path(user_id):
    """AI 学习路径规划"""
    _, err = validate_user(user_id)
    if err:
        return err
    path = ai.generate_learning_path(user_id)
    return jsonify(path)


@app.route('/api/chat', methods=['POST'])
def chat():
    """AI 学习助手对话"""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    message = data.get('message', '').strip()

    if not user_id:
        return jsonify({'error': '缺少 user_id'}), 400
    user_id = int(user_id)
    _, err = validate_user(user_id)
    if err:
        return err
    if not message:
        return jsonify({'error': '请输入问题'}), 400

    reply = ai.chat(user_id, message)
    return jsonify({
        'user_id': user_id,
        'message': message,
        'reply': reply
    })


if __name__ == '__main__':
    print("=" * 60)
    print("  培训管理系统 - AI 智能推荐引擎")
    source = "飞书多维表格" if data_provider.client.is_configured else "本地内存数据"
    print(f"  数据源: {source}")
    print(f"  课程: {len(data_provider.courses)} 门  "
          f"学员: {len(data_provider.users)} 位  "
          f"交互: {len(data_provider.interactions)} 条")
    print("  访问 http://localhost:5000 查看效果")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
