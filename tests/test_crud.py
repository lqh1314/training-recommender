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
        courses = self.provider.courses
        self.assertGreater(len(courses), 0)
        for c in courses:
            self.assertIn('id', c)
            self.assertIn('name', c)

    def test_add_course(self):
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
        self.provider.update_course(1, {'name': 'Python编程基础（更新版）', 'duration': 30})
        course = next(c for c in self.provider.courses if c['id'] == 1)
        self.assertEqual(course['name'], 'Python编程基础（更新版）')
        self.assertEqual(course['duration'], 30)

    def test_delete_course(self):
        self.provider.add_course({'id': 998, 'name': '待删除课程', 'desc': '', 'categories': [], 'tags': [], 'difficulty': '初级', 'duration': 0, 'instructor': '', 'cover_color': '#3B82F6'})
        count_before = len(self.provider.courses)
        self.provider.delete_course(998)
        self.assertEqual(len(self.provider.courses), count_before - 1)


class TestInstructorCRUD(unittest.TestCase):
    """讲师管理增删改查测试"""

    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.instructors)

    def test_list_instructors(self):
        instructors = self.provider.instructors
        self.assertGreater(len(instructors), 0)
        for i in instructors:
            self.assertIn('id', i)
            self.assertIn('name', i)
            self.assertIn('title', i)
            self.assertIn('expertise', i)
            self.assertIsInstance(i['expertise'], list)

    def test_add_instructor(self):
        new_inst = {
            'id': 99, 'name': '测试讲师', 'department': '测试部',
            'title': '测试工程师', 'expertise': ['测试', '自动化'],
            'intro': '测试简介', 'avatar': '测', 'status': '在职'
        }
        self.provider.add_instructor(new_inst)
        self.assertEqual(len(self.provider.instructors), self.initial_count + 1)
        found = next(i for i in self.provider.instructors if i['id'] == 99)
        self.assertEqual(found['name'], '测试讲师')

    def test_update_instructor(self):
        self.provider.update_instructor(1, {'title': '首席架构师', 'status': '休假'})
        inst = next(i for i in self.provider.instructors if i['id'] == 1)
        self.assertEqual(inst['title'], '首席架构师')
        self.assertEqual(inst['status'], '休假')

    def test_delete_instructor(self):
        self.provider.add_instructor({'id': 98, 'name': '待删除讲师', 'department': '', 'title': '', 'expertise': [], 'intro': '', 'avatar': '', 'status': '在职'})
        count_before = len(self.provider.instructors)
        self.provider.delete_instructor(98)
        self.assertEqual(len(self.provider.instructors), count_before - 1)

    def test_default_instructors_data(self):
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
        enrollments = self.provider.enrollments
        self.assertGreater(len(enrollments), 0)
        for e in enrollments:
            self.assertIn('id', e)
            self.assertIn('user_name', e)
            self.assertIn('course_name', e)
            self.assertIn('status', e)

    def test_add_enrollment(self):
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
        enrollment = next(e for e in self.provider.enrollments if e['id'] == 2)
        self.assertEqual(enrollment['status'], '待审批')
        self.provider.approve_enrollment(2, '张经理', '已通过')
        updated = next(e for e in self.provider.enrollments if e['id'] == 2)
        self.assertEqual(updated['status'], '已通过')
        self.assertEqual(updated['approver'], '张经理')
        self.assertTrue(updated['approve_time'])

    def test_reject_enrollment(self):
        self.provider.approve_enrollment(3, '李经理', '已拒绝')
        updated = next(e for e in self.provider.enrollments if e['id'] == 3)
        self.assertEqual(updated['status'], '已拒绝')

    def test_delete_enrollment(self):
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
        pending = [e for e in self.provider.enrollments if e['status'] == '待审批']
        self.assertEqual(len(pending), 2)

    def test_approved_enrollments_count(self):
        approved = [e for e in self.provider.enrollments if e['status'] == '已通过']
        self.assertEqual(len(approved), 1)


class TestAnnouncementCRUD(unittest.TestCase):
    """公告管理增删改查测试"""

    def setUp(self):
        self.provider = DataProvider().init()
        self.initial_count = len(self.provider.announcements)

    def test_list_announcements(self):
        announcements = self.provider.announcements
        self.assertGreater(len(announcements), 0)
        for a in announcements:
            self.assertIn('id', a)
            self.assertIn('title', a)
            self.assertIn('content', a)
            self.assertIn('publisher', a)

    def test_add_announcement(self):
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
        self.provider.update_announcement(1, {'status': '草稿', 'priority': '普通'})
        ann = next(a for a in self.provider.announcements if a['id'] == 1)
        self.assertEqual(ann['status'], '草稿')
        self.assertEqual(ann['priority'], '普通')

    def test_delete_announcement(self):
        self.provider.add_announcement({
            'id': 98, 'title': '待删除公告', 'content': '内容',
            'publisher': 'admin', 'publish_time': '2026-08-21 10:00',
            'status': '已发布', 'priority': '普通', 'category': '通知'
        })
        count_before = len(self.provider.announcements)
        self.provider.delete_announcement(98)
        self.assertEqual(len(self.provider.announcements), count_before - 1)

    def test_default_announcements_data(self):
        announcements = self.provider.announcements
        self.assertEqual(len(announcements), 2)
        titles = [a['title'] for a in announcements]
        self.assertIn('2026年秋季培训计划启动', titles)


class TestBitableSync(unittest.TestCase):
    """多维表格同步测试（Mock）"""

    @patch('bitable_client.BitableClient._request')
    def test_bitable_crud_with_mock(self, mock_request):
        mock_request.return_value = {"tenant_access_token": "mock_token"}
        client = BitableClient("test_id", "test_secret", "test_token")
        client._authenticate()
        self.assertEqual(client._token, "mock_token")

        client._table_ids = {
            "课程表": "tbl_courses", "讲师表": "tbl_instructors",
            "报名审批表": "tbl_enrollments", "公告表": "tbl_announcements",
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
        mock_request.return_value = {"tenant_access_token": "mock_token"}
        client = BitableClient("id", "secret", "token")
        client._authenticate()
        client._table_ids["课程表"] = "tbl1"
        mock_request.return_value = {"records": [{"record_id": "r1"}, {"record_id": "r2"}]}
        records = [{"fields": {"课程ID": 1}}, {"fields": {"课程ID": 2}}]
        result = client.batch_create_records("courses", "课程表", records)
        self.assertEqual(len(result["records"]), 2)

    def test_sync_without_bitable_config(self):
        provider = DataProvider().init()
        result = provider.sync_to_bitable()
        self.assertFalse(result['success'])
        self.assertIn('未配置', result['message'])

    def test_health_check_includes_all_modules(self):
        provider = DataProvider().init()
        health = provider.health_check()
        self.assertIn('courses', health)
        self.assertIn('instructors', health)
        self.assertIn('enrollments', health)
        self.assertIn('announcements', health)
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
        resp = self.client.get('/api/instructors')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_add_instructor_api(self):
        resp = self.client.post('/api/instructors', json={'id': 777, 'name': 'API测试讲师', 'title': '测试工程师'})
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.get_json()['success'])

    def test_add_instructor_missing_fields(self):
        resp = self.client.post('/api/instructors', json={'id': 778})
        self.assertEqual(resp.status_code, 400)

    def test_update_instructor_api(self):
        resp = self.client.put('/api/instructors/1', json={'title': '更新后职称'})
        self.assertEqual(resp.status_code, 200)

    def test_update_nonexistent_instructor(self):
        resp = self.client.put('/api/instructors/99999', json={'title': 'X'})
        self.assertEqual(resp.status_code, 404)

    def test_delete_instructor_api(self):
        self.client.post('/api/instructors', json={'id': 776, 'name': '待删除'})
        resp = self.client.delete('/api/instructors/776')
        self.assertEqual(resp.status_code, 200)

    def test_get_enrollments(self):
        resp = self.client.get('/api/enrollments')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_get_enrollments_filter_by_status(self):
        resp = self.client.get('/api/enrollments?status=待审批')
        self.assertEqual(resp.status_code, 200)
        for e in resp.get_json():
            self.assertEqual(e['status'], '待审批')

    def test_approve_enrollment_api(self):
        resp = self.client.put('/api/enrollments/2/approve', json={'approver': 'API测试经理', 'status': '已通过'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], '已通过')

    def test_approve_invalid_status(self):
        resp = self.client.put('/api/enrollments/1/approve', json={'status': '非法状态'})
        self.assertEqual(resp.status_code, 400)

    def test_get_announcements(self):
        resp = self.client.get('/api/announcements')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_add_announcement_api(self):
        resp = self.client.post('/api/announcements', json={'id': 888, 'title': 'API测试公告', 'content': '测试内容'})
        self.assertEqual(resp.status_code, 201)

    def test_update_announcement_api(self):
        resp = self.client.put('/api/announcements/1', json={'status': '草稿'})
        self.assertEqual(resp.status_code, 200)

    def test_delete_announcement_api(self):
        self.client.post('/api/announcements', json={'id': 887, 'title': '待删除公告'})
        resp = self.client.delete('/api/announcements/887')
        self.assertEqual(resp.status_code, 200)

    def test_sync_status_api(self):
        resp = self.client.get('/api/sync/status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('courses', data)
        self.assertIn('instructors', data)
        self.assertIn('enrollments', data)
        self.assertIn('announcements', data)

    def test_health_endpoint_has_new_modules(self):
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('instructors', data)
        self.assertIn('enrollments', data)
        self.assertIn('announcements', data)


class TestSyncScript(unittest.TestCase):
    """同步脚本功能测试"""

    def test_sync_script_exists(self):
        sync_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'sync_bitable.py'
        )
        self.assertTrue(os.path.exists(sync_script))

    def test_sync_script_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sync_bitable",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'sync_bitable.py')
        )
        self.assertIsNotNone(spec)


if __name__ == '__main__':
    unittest.main(verbosity=2)
