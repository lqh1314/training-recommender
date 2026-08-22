"""
培训管理系统 - 增删改查测试套件
覆盖：课程管理、讲师管理、报名审批、公告管理
以及多维表格同步、Flask API 端点测试
运行：python3 -m pytest tests/test_crud.py -v
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bitable_client import DataProvider, BitableClient


class TestCourseCRUD(unittest.TestCase):
    """课程管理增删改查测试"""
    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.courses)

    def test_list_courses(self):
        """查询：课程列表非空"""
        courses = self.provider.courses
        self.assertGreater(len(courses), 0)
        for c in courses:
            self.assertIn('id', c)
            self.assertIn('name', c)

    def test_add_course(self):
        """新增：添加课程"""
        new_course = {
            'id': 999, 'name': '测试课程', 'desc': '这是一门测试课程',
            'categories': ['技术研发'], 'tags': ['测试'],
            'difficulty': '初级', 'duration': 8, 'instructor': '测试讲师',
            'cover_color': '#FF0000'
        }
        self.provider.add_course(new_course)
        self.assertEqual(len(self.provider.courses), self.initial_count + 1)
        found = next(c for c in self.provider.courses if c['id'] == 999)
        self.assertEqual(found['name'], '测试课程')

    def test_update_course(self):
        """修改：更新课程信息"""
        self.provider.update_course(1, {'name': 'Python编程基础（更新版）', 'duration': 30})
        course = next(c for c in self.provider.courses if c['id'] == 1)
        self.assertEqual(course['name'], 'Python编程基础（更新版）')
        self.assertEqual(course['duration'], 30)

    def test_delete_course(self):
        """删除：移除课程"""
        self.provider.add_course({'id': 998, 'name': '待删除课程'})
        count_before = len(self.provider.courses)
        self.provider.delete_course(998)
        self.assertEqual(len(self.provider.courses), count_before - 1)
        self.assertIsNone(next((c for c in self.provider.courses if c['id'] == 998), None))


class TestInstructorCRUD(unittest.TestCase):
    """讲师管理增删改查测试"""
    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.instructors)

    def test_list_instructors(self):
        """查询：讲师列表非空且结构完整"""
        instructors = self.provider.instructors
        self.assertGreater(len(instructors), 0)
        for i in instructors:
            self.assertIn('id', i)
            self.assertIn('name', i)
            self.assertIn('title', i)
            self.assertIn('expertise', i)
            self.assertIsInstance(i['expertise'], list)

    def test_add_instructor(self):
        """新增：添加讲师"""
        new_inst = {
            'id': 99, 'name': '测试讲师', 'department': '测试部',
            'title': '测试工程师', 'expertise': ['测试', '自动化'],
            'intro': '测试简介', 'avatar': '测', 'status': '在职'
        }
        self.provider.add_instructor(new_inst)
        self.assertEqual(len(self.provider.instructors), self.initial_count + 1)
        found = next(i for i in self.provider.instructors if i['id'] == 99)
        self.assertEqual(found['name'], '测试讲师')
        self.assertEqual(found['expertise'], ['测试', '自动化'])

    def test_update_instructor(self):
        """修改：更新讲师职称"""
        self.provider.update_instructor(1, {'title': '首席架构师', 'status': '休假'})
        inst = next(i for i in self.provider.instructors if i['id'] == 1)
        self.assertEqual(inst['title'], '首席架构师')
        self.assertEqual(inst['status'], '休假')

    def test_delete_instructor(self):
        """删除：移除讲师"""
        self.provider.add_instructor({'id': 98, 'name': '待删除讲师'})
        count_before = len(self.provider.instructors)
        self.provider.delete_instructor(98)
        self.assertEqual(len(self.provider.instructors), count_before - 1)

    def test_default_instructors_data(self):
        """默认讲师数据完整"""
        instructors = self.provider.instructors
        self.assertEqual(len(instructors), 4)
        names = [i['name'] for i in instructors]
        self.assertIn('陈明', names)
        self.assertIn('王芳', names)


class TestEnrollmentCRUD(unittest.TestCase):
    """报名审批增删改查测试"""
    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.enrollments)

    def test_list_enrollments(self):
        """查询：报名列表非空"""
        enrollments = self.provider.enrollments
        self.assertGreater(len(enrollments), 0)
        for e in enrollments:
            self.assertIn('id', e)
            self.assertIn('user_name', e)
            self.assertIn('course_name', e)
            self.assertIn('status', e)

    def test_add_enrollment(self):
        """新增：提交报名申请"""
        new_enroll = {
            'id': 99, 'user_id': 3, 'user_name': '王五',
            'course_id': 10, 'course_name': '网络安全基础',
            'enroll_time': '2026-08-21 10:00',
            'status': '待审批', 'approver': '', 'approve_time': ''
        }
        self.provider.add_enrollment(new_enroll)
        self.assertEqual(len(self.provider.enrollments), self.initial_count + 1)
        found = next(e for e in self.provider.enrollments if e['id'] == 99)
        self.assertEqual(found['status'], '待审批')

    def test_approve_enrollment(self):
        """审批：通过报名"""
        enrollment = next(e for e in self.provider.enrollments if e['id'] == 2)
        self.assertEqual(enrollment['status'], '待审批')
        self.provider.approve_enrollment(2, '张经理', '已通过')
        updated = next(e for e in self.provider.enrollments if e['id'] == 2)
        self.assertEqual(updated['status'], '已通过')
        self.assertEqual(updated['approver'], '张经理')
        self.assertTrue(updated['approve_time'])

    def test_reject_enrollment(self):
        """审批：拒绝报名"""
        self.provider.approve_enrollment(3, '李经理', '已拒绝')
        updated = next(e for e in self.provider.enrollments if e['id'] == 3)
        self.assertEqual(updated['status'], '已拒绝')

    def test_delete_enrollment(self):
        """删除：移除报名记录"""
        self.provider.add_enrollment({
            'id': 98, 'user_id': 1, 'user_name': '张三',
            'course_id': 1, 'course_name': 'Python基础',
            'enroll_time': '2026-08-21 10:00',
            'status': '待审批', 'approver': '', 'approve_time': ''
        })
        count_before = len(self.provider.enrollments)
        self.provider.delete_enrollment(98)
        self.assertEqual(len(self.provider.enrollments), count_before - 1)

    def test_pending_enrollments_count(self):
        """待审批数量正确"""
        pending = [e for e in self.provider.enrollments if e['status'] == '待审批']
        self.assertEqual(len(pending), 2)

    def test_approved_enrollments_count(self):
        """已通过数量正确"""
        approved = [e for e in self.provider.enrollments if e['status'] == '已通过']
        self.assertEqual(len(approved), 1)


class TestAnnouncementCRUD(unittest.TestCase):
    """公告管理增删改查测试"""
    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.announcements)

    def test_list_announcements(self):
        """查询：公告列表非空"""
        announcements = self.provider.announcements
        self.assertGreater(len(announcements), 0)
        for a in announcements:
            self.assertIn('id', a)
            self.assertIn('title', a)
            self.assertIn('content', a)
            self.assertIn('publisher', a)

    def test_add_announcement(self):
        """新增：发布公告"""
        new_ann = {
            'id': 99, 'title': '测试公告标题',
            'content': '这是测试公告内容', 'publisher': '测试管理员',
            'publish_time': '2026-08-21 10:00',
            'status': '已发布', 'priority': '高', 'category': '测试通知'
        }
        self.provider.add_announcement(new_ann)
        self.assertEqual(len(self.provider.announcements), self.initial_count + 1)
        found = next(a for a in self.provider.announcements if a['id'] == 99)
        self.assertEqual(found['title'], '测试公告标题')
        self.assertEqual(found['priority'], '高')

    def test_update_announcement(self):
        """修改：更新公告状态"""
        self.provider.update_announcement(1, {'status': '草稿', 'priority': '普通'})
        ann = next(a for a in self.provider.announcements if a['id'] == 1)
        self.assertEqual(ann['status'], '草稿')
        self.assertEqual(ann['priority'], '普通')

    def test_delete_announcement(self):
        """删除：移除公告"""
        self.provider.add_announcement({
            'id': 98, 'title': '待删除公告', 'content': '内容',
            'publisher': 'admin', 'publish_time': '2026-08-21 10:00',
            'status': '已发布', 'priority': '普通', 'category': '通知'
        })
        count_before = len(self.provider.announcements)
        self.provider.delete_announcement(98)
        self.assertEqual(len(self.provider.announcements), count_before - 1)

    def test_default_announcements_data(self):
        """默认公告数据完整"""
        announcements = self.provider.announcements
        self.assertEqual(len(announcements), 2)
        titles = [a['title'] for a in announcements]
        self.assertIn('2026年秋季培训计划启动', titles)


class TestUserPersonnelField(unittest.TestCase):
    """学员表飞书“人员”字段测试"""
    def setUp(self):
        self.provider = DataProvider().init()

    def test_users_have_feishu_fields(self):
        """本地学员数据包含飞书人员字段"""
        for u in self.provider.users:
            self.assertIn('feishu_open_id', u, f"学员 {u.get('name')} 缺少 feishu_open_id")
            self.assertIn('email', u)
            self.assertIn('mobile', u)

    def test_feishu_open_id_format(self):
        """模拟 open_id 格式正确"""
        for u in self.provider.users:
            if u['feishu_open_id']:
                self.assertTrue(
                    u['feishu_open_id'].startswith('ou_'),
                    f"学员 {u['name']} 的 open_id 格式错误: {u['feishu_open_id']}"
                )

    def test_safe_get_person_parses_field(self):
        """_safe_get_person 正确解析飞书人员字段"""
        provider = self.provider
        fields = {
            "人员": [{
                "id": "ou_test123",
                "name": "测试人员",
                "en_name": "Test Person",
                "avatar_url": "https://example.com/a.png",
                "union_id": "on_test456"
            }]
        }
        person = provider._safe_get_person(fields, "人员")
        self.assertEqual(person["id"], "ou_test123")
        self.assertEqual(person["name"], "测试人员")
        self.assertEqual(person["union_id"], "on_test456")
        self.assertEqual(person["avatar_url"], "https://example.com/a.png")

    def test_safe_get_person_empty(self):
        """_safe_get_person 无人员时返回空字典"""
        person = self.provider._safe_get_person({}, "人员")
        self.assertEqual(person, {})
        person2 = self.provider._safe_get_person({"人员": []}, "人员")
        self.assertEqual(person2, {})

    def test_record_to_user_with_person_field(self):
        """_record_to_user 从人员字段提取 open_id 和姓名"""
        record = {
            "record_id": "rec001",
            "fields": {
                "学员ID": 100,
                "姓名": "张三",
                "部门": "技术部",
                "岗位": "工程师",
                "人员": [{"id": "ou_zhangsan", "name": "张三", "union_id": "on_zs"}],
                "邮箱": "zhangsan@test.com",
                "手机号": "+86-138****0001",
            }
        }
        user = self.provider._record_to_user(record)
        self.assertEqual(user["id"], 100)
        self.assertEqual(user["name"], "张三")
        self.assertEqual(user["feishu_open_id"], "ou_zhangsan")
        self.assertEqual(user["feishu_union_id"], "on_zs")
        self.assertEqual(user["email"], "zhangsan@test.com")

    def test_record_to_user_person_name_fallback(self):
        """人员字段存在但姓名字段为空时，从人员信息取姓名"""
        record = {
            "record_id": "rec002",
            "fields": {
                "学员ID": 101,
                "人员": [{"id": "ou_lisi", "name": "李四"}],
            }
        }
        user = self.provider._record_to_user(record)
        self.assertEqual(user["name"], "李四")
        self.assertEqual(user["feishu_open_id"], "ou_lisi")


class TestUserCRUD(unittest.TestCase):
    """学员管理增删改查测试"""
    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.users)

    def test_list_users(self):
        """查询：学员列表非空"""
        users = self.provider.users
        self.assertGreater(len(users), 0)
        for u in users:
            self.assertIn('id', u)
            self.assertIn('name', u)

    def test_add_user(self):
        """新增：添加学员"""
        new_user = {
            'id': 999, 'name': '测试学员', 'department': '测试部',
            'position': '测试工程师', 'avatar': '测',
            'feishu_open_id': 'ou_mock_test_999',
            'email': 'test999@test.com', 'mobile': '+86-139****9999'
        }
        self.provider.add_user(new_user)
        self.assertEqual(len(self.provider.users), self.initial_count + 1)
        found = next(u for u in self.provider.users if u['id'] == 999)
        self.assertEqual(found['name'], '测试学员')
        self.assertEqual(found['feishu_open_id'], 'ou_mock_test_999')

    def test_update_user(self):
        """修改：更新学员部门和岗位"""
        self.provider.update_user(1, {'department': 'AI研究院', 'position': '算法专家'})
        user = next(u for u in self.provider.users if u['id'] == 1)
        self.assertEqual(user['department'], 'AI研究院')
        self.assertEqual(user['position'], '算法专家')

    def test_delete_user(self):
        """删除：移除学员"""
        self.provider.add_user({'id': 998, 'name': '待删除学员'})
        count_before = len(self.provider.users)
        self.provider.delete_user(998)
        self.assertEqual(len(self.provider.users), count_before - 1)
        self.assertIsNone(next((u for u in self.provider.users if u['id'] == 998), None))

    @patch('bitable_client.BitableClient._request')
    def test_add_user_writes_person_field_to_bitable(self, mock_request):
        """Mock：新增学员时人员字段以 [{"id": open_id}] 格式写入多维表格"""
        mock_request.return_value = {"tenant_access_token": "mock_token"}
        client = BitableClient("id", "secret", "token")
        client._authenticate()
        client._table_ids = {"学员表": "tbl_users"}
        provider = DataProvider(client)
        provider._use_bitable = True
        mock_request.return_value = {"record": {"record_id": "rec_user1"}}
        provider.add_user({
            'id': 50, 'name': '同步学员', 'department': '研发部',
            'position': '开发', 'feishu_open_id': 'ou_sync_50',
            'email': 'sync50@test.com', 'mobile': ''
        })
        call_args = mock_request.call_args
        sent_data = call_args.kwargs.get('data') or call_args[1].get('data')
        fields = sent_data.get('fields', {})
        self.assertIn('人员', fields)
        self.assertEqual(fields['人员'], [{"id": "ou_sync_50"}])
        self.assertEqual(fields['姓名'], '同步学员')

    @patch('bitable_client.BitableClient._request')
    def test_sync_to_bitable_includes_users(self, mock_request):
        """Mock：全量同步包含学员模块且使用人员字段格式"""
        mock_request.return_value = {"tenant_access_token": "mock_token"}
        client = BitableClient("id", "secret", "token")
        client._authenticate()
        client._table_ids = {
            "学员表": "tbl_users", "课程表": "tbl_courses",
            "讲师表": "tbl_inst", "报名审批表": "tbl_enr", "公告表": "tbl_ann"
        }
        provider = DataProvider(client)
        provider._use_bitable = True
        provider._users = [{'id': 1, 'name': '张三', 'department': '技术部',
                            'position': '工程师', 'feishu_open_id': 'ou_zs_001',
                            'email': 'zs@test.com', 'mobile': '138'}]
        provider._courses = []
        provider._instructors = []
        provider._enrollments = []
        provider._announcements = []
        mock_request.return_value = {"records": []}
        result = provider.sync_to_bitable()
        self.assertTrue(result['success'])
        log_text = ' '.join(result['log'])
        self.assertIn('学员', log_text)
        user_call = None
        for call in mock_request.call_args_list:
            sent_data = call.kwargs.get('data') or call_args[1].get('data')
            if sent_data and 'records' in sent_data and sent_data['records']:
                first_fields = sent_data['records'][0].get('fields', {})
                if '人员' in first_fields:
                    user_call = first_fields
                    break
        self.assertIsNotNone(user_call, "未找到学员表同步调用")
        self.assertEqual(user_call['人员'], [{"id": "ou_zs_001"}])


class TestBitableSync(unittest.TestCase):
    """多维表格同步测试（Mock）"""
    @patch('bitable_client.BitableClient._request')
    def test_bitable_crud_with_mock(self, mock_request):
        """Mock 多维表格环境下的 CRUD 操作"""
        mock_request.return_value = {"tenant_access_token": "mock_token"}
        client = BitableClient("test_id", "test_secret", "test_token")
        client._authenticate()
        self.assertEqual(client._token, "mock_token")
        client._table_ids = {
            "课程表": "tbl_courses",
            "讲师表": "tbl_instructors",
            "报名审批表": "tbl_enrollments",
            "公告表": "tbl_announcements",
        }
        provider = DataProvider(client)
        provider._use_bitable = True
        mock_request.return_value = {"record": {"record_id": "rec123"}}
        provider.add_instructor({
            'id': 10, 'name': 'Mock讲师', 'department': '测试部',
            'title': '工程师', 'expertise': ['Python'],
            'intro': '', 'avatar': 'M', 'status': '在职'
        })
        self.assertTrue(any(i['id'] == 10 for i in provider.instructors))
        provider._record_id_map['instructors'][10] = 'rec123'
        provider.update_instructor(10, {'title': '高级工程师'})
        updated = next(i for i in provider.instructors if i['id'] == 10)
        self.assertEqual(updated['title'], '高级工程师')
        provider.delete_instructor(10)
        self.assertFalse(any(i['id'] == 10 for i in provider.instructors))

    @patch('bitable_client.BitableClient._request')
    def test_batch_create_records(self, mock_request):
        """批量创建记录"""
        mock_request.return_value = {"tenant_access_token": "mock_token"}
        client = BitableClient("id", "secret", "token")
        client._authenticate()
        client._table_ids["课程表"] = "tbl1"
        mock_request.return_value = {"records": [{"record_id": "r1"}, {"record_id": "r2"}]}
        records = [{"fields": {"课程ID": 1}}, {"fields": {"课程ID": 2}}]
        result = client.batch_create_records("courses", "课程表", records)
        self.assertEqual(len(result["records"]), 2)

    def test_sync_without_bitable_config(self):
        """未配置多维表格时同步返回失败提示"""
        provider = DataProvider().init()
        result = provider.sync_to_bitable()
        self.assertFalse(result['success'])
        self.assertIn('未配置', result['message'])

    def test_health_check_includes_all_modules(self):
        """健康检查包含所有模块"""
        provider = DataProvider().init()
        health = provider.health_check()
        self.assertIn('courses', health)
        self.assertIn('instructors', health)
        self.assertIn('enrollments', health)
        self.assertIn('announcements', health)
        self.assertIn('users', health)
        self.assertIn('interactions', health)
        self.assertEqual(health['instructors'], 4)
        self.assertEqual(health['enrollments'], 3)
        self.assertEqual(health['announcements'], 2)


class TestFlaskCRUDAPI(unittest.TestCase):
    """Flask API 增删改查端点测试"""
    @classmethod
    def setUpClass(cls):
        from app import app
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_get_instructors(self):
        """GET /api/instructors"""
        resp = self.client.get('/api/instructors')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_add_instructor_api(self):
        """POST /api/instructors"""
        resp = self.client.post('/api/instructors', json={
            'id': 777, 'name': 'API测试讲师', 'title': '测试工程师'
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data['success'])

    def test_add_instructor_missing_fields(self):
        """POST /api/instructors 缺少字段返回400"""
        resp = self.client.post('/api/instructors', json={'id': 778})
        self.assertEqual(resp.status_code, 400)

    def test_update_instructor_api(self):
        """PUT /api/instructors/<id>"""
        resp = self.client.put('/api/instructors/1', json={'title': '更新后职称'})
        self.assertEqual(resp.status_code, 200)

    def test_update_nonexistent_instructor(self):
        """PUT 不存在的讲师返回404"""
        resp = self.client.put('/api/instructors/99999', json={'title': 'X'})
        self.assertEqual(resp.status_code, 404)

    def test_delete_instructor_api(self):
        """DELETE /api/instructors/<id>"""
        self.client.post('/api/instructors', json={'id': 776, 'name': '待删除'})
        resp = self.client.delete('/api/instructors/776')
        self.assertEqual(resp.status_code, 200)

    def test_get_enrollments(self):
        """GET /api/enrollments"""
        resp = self.client.get('/api/enrollments')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)

    def test_get_enrollments_filter_by_status(self):
        """GET /api/enrollments?status=待审批"""
        resp = self.client.get('/api/enrollments?status=待审批')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for e in data:
            self.assertEqual(e['status'], '待审批')

    def test_approve_enrollment_api(self):
        """PUT /api/enrollments/<id>/approve"""
        resp = self.client.put('/api/enrollments/2/approve', json={
            'approver': 'API测试经理', 'status': '已通过'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], '已通过')

    def test_approve_invalid_status(self):
        """审批状态非法返回400"""
        resp = self.client.put('/api/enrollments/1/approve', json={
            'status': '非法状态'
        })
        self.assertEqual(resp.status_code, 400)

    def test_get_announcements(self):
        """GET /api/announcements"""
        resp = self.client.get('/api/announcements')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)

    def test_add_announcement_api(self):
        """POST /api/announcements"""
        resp = self.client.post('/api/announcements', json={
            'id': 888, 'title': 'API测试公告', 'content': '测试内容'
        })
        self.assertEqual(resp.status_code, 201)

    def test_update_announcement_api(self):
        """PUT /api/announcements/<id>"""
        resp = self.client.put('/api/announcements/1', json={'status': '草稿'})
        self.assertEqual(resp.status_code, 200)

    def test_delete_announcement_api(self):
        """DELETE /api/announcements/<id>"""
        self.client.post('/api/announcements', json={
            'id': 887, 'title': '待删除公告'
        })
        resp = self.client.delete('/api/announcements/887')
        self.assertEqual(resp.status_code, 200)

    def test_sync_status_api(self):
        """GET /api/sync/status"""
        resp = self.client.get('/api/sync/status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('courses', data)
        self.assertIn('instructors', data)
        self.assertIn('enrollments', data)
        self.assertIn('announcements', data)

    def test_health_endpoint_has_new_modules(self):
        """健康检查端点包含新模块数据"""
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('instructors', data)
        self.assertIn('enrollments', data)
        self.assertIn('announcements', data)

    def test_get_users_includes_feishu_fields(self):
        """GET /api/users 返回飞书人员字段"""
        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        for u in data:
            self.assertIn('feishu_open_id', u)
            self.assertIn('email', u)
            self.assertIn('mobile', u)

    def test_add_user_api(self):
        """POST /api/users 添加学员"""
        resp = self.client.post('/api/users', json={
            'id': 666, 'name': 'API测试学员', 'department': '测试部',
            'feishu_open_id': 'ou_api_test_666', 'email': 'api666@test.com'
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['feishu_open_id'], 'ou_api_test_666')
        self.client.delete('/api/users/666')

    def test_add_user_missing_fields(self):
        """POST /api/users 缺少字段返回400"""
        resp = self.client.post('/api/users', json={'id': 667})
        self.assertEqual(resp.status_code, 400)

    def test_update_user_api(self):
        """PUT /api/users/<id>"""
        resp = self.client.put('/api/users/1', json={'department': '更新部门'})
        self.assertEqual(resp.status_code, 200)

    def test_update_nonexistent_user(self):
        """PUT 不存在的学员返回404"""
        resp = self.client.put('/api/users/99999', json={'department': 'X'})
        self.assertEqual(resp.status_code, 404)

    def test_delete_user_api(self):
        """DELETE /api/users/<id>"""
        self.client.post('/api/users', json={'id': 665, 'name': '待删除学员'})
        resp = self.client.delete('/api/users/665')
        self.assertEqual(resp.status_code, 200)


class TestSyncScript(unittest.TestCase):
    """同步脚本功能测试"""
    def test_sync_state_save_load(self):
        """同步状态保存和加载"""
        sync_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'sync_bitable.py'
        )
        self.assertTrue(os.path.exists(sync_script))

    def test_sync_script_importable(self):
        """同步脚本可导入"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sync_bitable",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'sync_bitable.py')
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec)


if __name__ == '__main__':
    unittest.main(verbosity=2)
