"""
培训管理系统 - 智能推荐服务
Flask Web 应用，提供推荐 API 和页面
"""

from flask import Flask, jsonify, request, render_template
from data import USERS, COURSES, INTERACTIONS
from recommender import RecommendationEngine

app = Flask(__name__)

# 初始化推荐引擎
engine = RecommendationEngine(USERS, COURSES, INTERACTIONS)

ALGORITHM_MAP = {
    'hybrid': ('混合推荐（智能融合）', engine.recommend_hybrid),
    'user_cf': ('基于用户的协同过滤', engine.recommend_user_cf),
    'item_cf': ('基于物品的协同过滤', engine.recommend_item_cf),
    'content': ('基于内容的推荐', engine.recommend_content_based),
    'popular': ('热门推荐', engine.recommend_popular),
}


def enrich_course(course_id: int, score: float, reason: str, algorithm: str) -> dict:
    """补充课程详情"""
    course = engine.courses.get(course_id, {})
    learners = len(engine.course_users.get(course_id, set()))
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
        'reason': reason,
        'algorithm': algorithm,
    }


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


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
        for u in USERS
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
        for c in COURSES
    ])


@app.route('/api/recommend/<int:user_id>')
def recommend(user_id):
    """获取推荐结果"""
    algo = request.args.get('algorithm', 'hybrid')
    top_n = request.args.get('top_n', 8, type=int)

    if algo not in ALGORITHM_MAP:
        return jsonify({'error': f'不支持的算法: {algo}'}), 400

    algo_name, algo_func = ALGORITHM_MAP[algo]

    # 热门推荐不需要 user_id
    if algo == 'popular':
        raw_recs = algo_func(top_n)
    else:
        raw_recs = algo_func(user_id, top_n)

    recommendations = [
        enrich_course(r['course_id'], r['score'], r['reason'], r['algorithm'])
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
    profile = engine.get_user_profile(user_id)
    learned_courses = []
    for cid in engine.user_learned.get(user_id, set()):
        course = engine.courses.get(cid, {})
        inter = next(
            (i for i in INTERACTIONS
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
    data = request.get_json()
    user_id = data.get('user_id')
    course_id = data.get('course_id')
    progress = data.get('progress', 0)
    rating = data.get('rating', 0)
    behavior_weight = data.get('behavior_weight', 0.5)

    if not user_id or not course_id:
        return jsonify({'error': '缺少 user_id 或 course_id'}), 400

    engine.record_interaction(user_id, course_id, progress, rating, behavior_weight)
    return jsonify({'success': True, 'message': '学习行为已记录，推荐已更新'})


@app.route('/api/compare/<int:user_id>')
def compare_algorithms(user_id):
    """对比不同算法的推荐结果"""
    top_n = request.args.get('top_n', 5, type=int)
    results = {}
    for algo_key, (algo_name, algo_func) in ALGORITHM_MAP.items():
        if algo_key == 'popular':
            raw = algo_func(top_n)
        else:
            raw = algo_func(user_id, top_n)
        results[algo_key] = {
            'name': algo_name,
            'courses': [
                enrich_course(r['course_id'], r['score'], r['reason'], r['algorithm'])
                for r in raw
            ]
        }
    return jsonify(results)


if __name__ == '__main__':
    print("=" * 60)
    print("  培训管理系统 - 智能推荐引擎")
    print("  访问 http://localhost:5000 查看效果")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
