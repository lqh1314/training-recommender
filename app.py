"""
培训管理系统 - 智能推荐服务
Flask Web 应用，提供推荐 API 和页面
支持飞书多维表格数据源和本地内存数据自动切换
"""
import os
import json
import logging
from datetime import datetime
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

MAX_TOP_N = 20


def enrich_course(course_id: int, score: float, reason: str,
                  algorithm: str, user_id: int = None) -> dict:
    course = engine.courses.get(course_id, {})
    learners = len(engine.course_users.get(course_id, set()))
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
    if user_id not in engine.users:
        return None, (jsonify({'error': f'学员不存在: {user_id}'}), 404)
    return engine.users[user_id], None


def validate_course(course_id: int):
    return course_id in engine.courses


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health')
def health():
    return jsonify(data_provider.health_check())


@app.route('/api/users')
def get_users():
    return jsonify([
        {
            'id': u['id'], 'name': u['name'],
            'department': u['department'], 'position': u['position'],
            'avatar': u['avatar'],
            'learned_count': len(engine.user_learned.get(u['id'], set()))
        }
        for u in data_provider.users
    ])


@app.route('/api/courses')
def get_courses():
    return jsonify([
        {
            'id': c['id'], 'name': c['name'], 'desc': c['desc'],
            'categories': c['categories'], 'tags': c['tags'],
            'difficulty': c['difficulty'], 'duration': c['duration'],
            'instructor': c['instructor'], 'cover_color': c['cover_color'],
            'learners': len(engine.course_users.get(c['id'], set()))
        }
        for c in data_provider.courses
    ])


@app.route('/api/recommend/<int:user_id>')
def recommend(user_id):
    _, err = validate_user(user_id)
    if err:
        return err
    algo = request.args.get('algorithm', 'hybrid')
    top_n = request.args.get('top_n', 8, type=int)
    top_n = max(1, min(top_n, MAX_TOP_N))
    if algo not in ALGORITHM_MAP:
        return jsonify({'error': f'不支持的算法: {algo}'}), 400
    algo_name, algo_func = ALGORITHM_MAP[algo]
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
        'user_id': user_id, 'algorithm': algo,
        'algorithm_name': algo_name, 'profile': profile,
        'recommendations': recommendations
    })


@app.route('/api/profile/<int:user_id>')
def get_profile(user_id):
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
            'id': cid, 'name': course.get('name', ''),
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
    _, err = validate_user(user_id)
    if err:
        return err
    path = ai.generate_learning_path(user_id)
    return jsonify(path)


@app.route('/api/chat', methods=['POST'])
def chat():
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
    return jsonify({'user_id': user_id, 'message': message, 'reply': reply})


# ===== 讲师管理 API =====

@app.route('/api/instructors', methods=['GET'])
def get_instructors():
    return jsonify(data_provider.instructors)


@app.route('/api/instructors', methods=['POST'])
def add_instructor():
    data = request.get_json(silent=True) or {}
    if not data.get('id') or not data.get('name'):
        return jsonify({'error': '缺少必填字段: id, name'}), 400
    instructor = {
        'id': int(data['id']), 'name': data['name'],
        'department': data.get('department', ''),
        'title': data.get('title', ''),
        'expertise': data.get('expertise', []),
        'intro': data.get('intro', ''),
        'avatar': data.get('avatar', data['name'][0]),
        'status': data.get('status', '在职'),
    }
    data_provider.add_instructor(instructor)
    return jsonify({'success': True, 'instructor': instructor}), 201


@app.route('/api/instructors/<int:instructor_id>', methods=['PUT'])
def update_instructor(instructor_id):
    data = request.get_json(silent=True) or {}
    if not any(i['id'] == instructor_id for i in data_provider.instructors):
        return jsonify({'error': f'讲师不存在: {instructor_id}'}), 404
    data_provider.update_instructor(instructor_id, data)
    return jsonify({'success': True})


@app.route('/api/instructors/<int:instructor_id>', methods=['DELETE'])
def delete_instructor(instructor_id):
    if not any(i['id'] == instructor_id for i in data_provider.instructors):
        return jsonify({'error': f'讲师不存在: {instructor_id}'}), 404
    data_provider.delete_instructor(instructor_id)
    return jsonify({'success': True})


# ===== 报名审批 API =====

@app.route('/api/enrollments', methods=['GET'])
def get_enrollments():
    status_filter = request.args.get('status')
    enrollments = data_provider.enrollments
    if status_filter:
        enrollments = [e for e in enrollments if e['status'] == status_filter]
    return jsonify(enrollments)


@app.route('/api/enrollments', methods=['POST'])
def add_enrollment():
    data = request.get_json(silent=True) or {}
    if data.get('id') is None or data.get('user_id') is None or data.get('course_id') is None:
        return jsonify({'error': '缺少必填字段: id, user_id, course_id'}), 400
    user_id = int(data['user_id'])
    course_id = int(data['course_id'])
    _, err = validate_user(user_id)
    if err:
        return err
    if not validate_course(course_id):
        return jsonify({'error': f'课程不存在: {course_id}'}), 404
    user = engine.users[user_id]
    course = engine.courses[course_id]
    enrollment = {
        'id': int(data['id']), 'user_id': user_id,
        'user_name': user['name'], 'course_id': course_id,
        'course_name': course['name'],
        'enroll_time': data.get('enroll_time', datetime.now().strftime('%Y-%m-%d %H:%M')),
        'status': '待审批', 'approver': '', 'approve_time': '',
    }
    data_provider.add_enrollment(enrollment)
    return jsonify({'success': True, 'enrollment': enrollment}), 201


@app.route('/api/enrollments/<int:enrollment_id>/approve', methods=['PUT'])
def approve_enrollment(enrollment_id):
    data = request.get_json(silent=True) or {}
    status_val = data.get('status', '已通过')
    approver = data.get('approver', '管理员')
    if status_val not in ('已通过', '已拒绝'):
        return jsonify({'error': 'status 必须为 已通过 或 已拒绝'}), 400
    if not any(e['id'] == enrollment_id for e in data_provider.enrollments):
        return jsonify({'error': f'报名记录不存在: {enrollment_id}'}), 404
    data_provider.approve_enrollment(enrollment_id, approver, status_val)
    return jsonify({'success': True, 'status': status_val})


@app.route('/api/enrollments/<int:enrollment_id>', methods=['DELETE'])
def delete_enrollment(enrollment_id):
    if not any(e['id'] == enrollment_id for e in data_provider.enrollments):
        return jsonify({'error': f'报名记录不存在: {enrollment_id}'}), 404
    data_provider.delete_enrollment(enrollment_id)
    return jsonify({'success': True})


# ===== 公告管理 API =====

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    return jsonify(data_provider.announcements)


@app.route('/api/announcements', methods=['POST'])
def add_announcement():
    data = request.get_json(silent=True) or {}
    if not data.get('id') or not data.get('title'):
        return jsonify({'error': '缺少必填字段: id, title'}), 400
    announcement = {
        'id': int(data['id']), 'title': data['title'],
        'content': data.get('content', ''),
        'publisher': data.get('publisher', '管理员'),
        'publish_time': data.get('publish_time', datetime.now().strftime('%Y-%m-%d %H:%M')),
        'status': data.get('status', '已发布'),
        'priority': data.get('priority', '普通'),
        'category': data.get('category', '通知'),
    }
    data_provider.add_announcement(announcement)
    return jsonify({'success': True, 'announcement': announcement}), 201


@app.route('/api/announcements/<int:announcement_id>', methods=['PUT'])
def update_announcement(announcement_id):
    data = request.get_json(silent=True) or {}
    if not any(a['id'] == announcement_id for a in data_provider.announcements):
        return jsonify({'error': f'公告不存在: {announcement_id}'}), 404
    data_provider.update_announcement(announcement_id, data)
    return jsonify({'success': True})


@app.route('/api/announcements/<int:announcement_id>', methods=['DELETE'])
def delete_announcement(announcement_id):
    if not any(a['id'] == announcement_id for a in data_provider.announcements):
        return jsonify({'error': f'公告不存在: {announcement_id}'}), 404
    data_provider.delete_announcement(announcement_id)
    return jsonify({'success': True})


# ===== 数据同步 API =====

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    result = data_provider.sync_to_bitable()
    return jsonify(result)


@app.route('/api/sync/status', methods=['GET'])
def sync_status():
    health = data_provider.health_check()
    state_file = os.path.join(os.path.dirname(__file__), '.sync_state.json')
    last_sync = None
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                last_sync = json.load(f).get('last_sync')
        except (json.JSONDecodeError, IOError):
            pass
    health['last_sync'] = last_sync
    return jsonify(health)


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
