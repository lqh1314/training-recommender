"""
培训管理系统 - 飞书多维表格对接模块
支持将课程、学员、学习记录、讲师、报名审批、公告数据存储在飞书多维表格中。
未配置飞书凭证时自动回退到本地内存数据（data.py）。

环境变量配置：
    FEISHU_APP_ID       飞书应用 App ID
    FEISHU_APP_SECRET   飞书应用 App Secret
    BITABLE_APP_TOKEN   多维表格 App Token
    BITABLE_TABLE_COURSES       课程表 ID（可选，默认自动查找）
    BITABLE_TABLE_USERS         学员表 ID（可选）
    BITABLE_TABLE_INTERACTIONS  学习记录表 ID（可选）
    BITABLE_TABLE_INSTRUCTORS   讲师表 ID（可选）
    BITABLE_TABLE_ENROLLMENTS   报名审批表 ID（可选）
    BITABLE_TABLE_ANNOUNCEMENTS 公告表 ID（可选）
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from urllib import request, parse, error
from datetime import datetime

logger = logging.getLogger(__name__)

FEISHU_BASE = "https://open.feishu.cn/open-apis"
TOKEN_URL = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
BITABLE_LIST_URL = f"{FEISHU_BASE}/bitable/v1/apps/{{app_token}}/tables"
BITABLE_RECORDS_URL = f"{FEISHU_BASE}/bitable/v1/apps/{{app_token}}/tables/{{table_id}}/records"
BITABLE_RECORDS_BATCH_URL = f"{FEISHU_BASE}/bitable/v1/apps/{{app_token}}/tables/{{table_id}}/records/batch_create"
BITABLE_RECORDS_SEARCH_URL = f"{FEISHU_BASE}/bitable/v1/apps/{{app_token}}/tables/{{table_id}}/records/search"


class BitableClient:
    """飞书多维表格客户端"""

    def __init__(self, app_id: str = None, app_secret: str = None,
                 app_token: str = None):
        self.app_id = app_id or os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET", "")
        self.app_token = app_token or os.environ.get("BITABLE_APP_TOKEN", "")
        self._token = None
        self._table_ids = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret and self.app_token)

    def _request(self, url: str, method: str = "GET",
                 data: dict = None, params: dict = None,
                 retry_auth: bool = True) -> dict:
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 401 and retry_auth:
                logger.info("飞书 token 过期，自动刷新")
                self._token = None
                self._authenticate()
                return self._request(url, method, data, params, retry_auth=False)
            raise RuntimeError(f"飞书 API 请求失败 [{e.code}]: {err_body}")
        code = result.get("code", -1)
        if code != 0:
            raise RuntimeError(f"飞书 API 业务错误: code={code}, msg={result.get('msg')}")
        return result.get("data", {})

    def _authenticate(self):
        if self._token:
            return
        result = self._request(
            TOKEN_URL, method="POST",
            data={"app_id": self.app_id, "app_secret": self.app_secret},
            retry_auth=False
        )
        self._token = result.get("tenant_access_token")
        if not self._token:
            raise RuntimeError("获取 tenant_access_token 失败")
        logger.info("飞书多维表格认证成功")

    def connect(self) -> bool:
        if not self.is_configured:
            logger.info("未配置飞书凭证，使用本地数据")
            return False
        self._authenticate()
        self._list_tables()
        logger.info("多维表格连接成功，app_token=%s", self.app_token[:8] + "...")
        return True

    def _list_tables(self) -> List[dict]:
        url = BITABLE_LIST_URL.format(app_token=self.app_token)
        result = self._request(url)
        tables = result.get("items", [])
        for t in tables:
            self._table_ids[t["name"]] = t["table_id"]
        return tables

    def _resolve_table_id(self, table_key: str, table_name: str) -> str:
        env_var = f"BITABLE_TABLE_{table_key.upper()}"
        table_id = os.environ.get(env_var, "")
        if table_id:
            return table_id
        if not self._table_ids:
            self._list_tables()
        table_id = self._table_ids.get(table_name)
        if not table_id:
            raise RuntimeError(
                f"未找到数据表「{table_name}」，请在多维表格中创建该表，"
                f"或设置环境变量 {env_var}"
            )
        return table_id

    def list_records(self, table_key: str, table_name: str,
                     page_size: int = 100) -> List[dict]:
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_URL.format(app_token=self.app_token, table_id=table_id)
        all_items = []
        page_token = None
        while True:
            params = {"page_size": min(page_size, 500)}
            if page_token:
                params["page_token"] = page_token
            result = self._request(url, params=params)
            all_items.extend(result.get("items", []))
            if not result.get("has_more"):
                break
            page_token = result.get("page_token")
        return all_items

    def create_record(self, table_key: str, table_name: str, fields: dict) -> dict:
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_URL.format(app_token=self.app_token, table_id=table_id)
        return self._request(url, method="POST", data={"fields": fields})

    def batch_create_records(self, table_key: str, table_name: str,
                             records: List[dict]) -> dict:
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_BATCH_URL.format(app_token=self.app_token, table_id=table_id)
        result = {"records": []}
        for i in range(0, len(records), 500):
            batch = records[i:i + 500]
            resp = self._request(url, method="POST", data={"records": batch})
            result["records"].extend(resp.get("records", []))
        return result

    def update_record(self, table_key: str, table_name: str,
                      record_id: str, fields: dict) -> dict:
        table_id = self._resolve_table_id(table_key, table_name)
        url = f"{BITABLE_RECORDS_URL.format(app_token=self.app_token, table_id=table_id)}/{record_id}"
        return self._request(url, method="PUT", data={"fields": fields})

    def delete_record(self, table_key: str, table_name: str, record_id: str) -> bool:
        table_id = self._resolve_table_id(table_key, table_name)
        url = f"{BITABLE_RECORDS_URL.format(app_token=self.app_token, table_id=table_id)}/{record_id}"
        self._request(url, method="DELETE")
        return True

    def search_records(self, table_key: str, table_name: str,
                       filter_conditions: list) -> List[dict]:
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_SEARCH_URL.format(app_token=self.app_token, table_id=table_id)
        body = {"filter": {"conjunction": "and", "conditions": filter_conditions}}
        result = self._request(url, method="POST", data=body)
        return result.get("items", [])


class DataProvider:
    """
    数据提供者：统一封装本地数据和多维表格数据。
    优先使用多维表格，未配置时回退到 data.py。
    支持模块：课程、学员、学习记录、讲师、报名审批、公告。
    """

    TABLE_NAMES = {
        "courses": "课程表",
        "users": "学员表",
        "interactions": "学习记录表",
        "instructors": "讲师表",
        "enrollments": "报名审批表",
        "announcements": "公告表",
    }

    def __init__(self, client: BitableClient = None):
        self.client = client or BitableClient()
        self._use_bitable = False
        self._courses = []
        self._users = []
        self._interactions = []
        self._instructors = []
        self._enrollments = []
        self._announcements = []
        self._record_id_map = {
            "courses": {}, "users": {}, "interactions": {},
            "instructors": {}, "enrollments": {}, "announcements": {},
        }

    def init(self):
        self._use_bitable = self.client.connect()
        if self._use_bitable:
            self._load_from_bitable()
        else:
            self._load_from_local()
        logger.info(
            "数据加载完成: %d门课程, %d位学员, %d条交互, %d位讲师, %d条报名, %d条公告",
            len(self._courses), len(self._users), len(self._interactions),
            len(self._instructors), len(self._enrollments), len(self._announcements)
        )
        return self

    def _load_from_local(self):
        """从本地 data.py 加载（深拷贝避免污染全局数据）"""
        import copy
        from data import COURSES, USERS, INTERACTIONS
        self._courses = copy.deepcopy(COURSES)
        self._users = copy.deepcopy(USERS)
        self._interactions = copy.deepcopy(INTERACTIONS)
        self._instructors = self._default_instructors()
        self._enrollments = self._default_enrollments()
        self._announcements = self._default_announcements()

    def _load_from_bitable(self):
        loaders = [
            ("courses", self._record_to_course),
            ("users", self._record_to_user),
            ("interactions", self._record_to_interaction),
            ("instructors", self._record_to_instructor),
            ("enrollments", self._record_to_enrollment),
            ("announcements", self._record_to_announcement),
        ]
        for key, converter in loaders:
            try:
                records = self.client.list_records(key, self.TABLE_NAMES[key])
                items = []
                for r in records:
                    items.append(converter(r))
                    rid = r.get("record_id", "")
                    id_field = converter(r).get("id")
                    if rid and id_field is not None:
                        self._record_id_map[key][id_field] = rid
                setattr(self, f"_{key}", items)
                logger.info("从多维表格加载 %s: %d 条", key, len(items))
            except RuntimeError as e:
                logger.warning("加载 %s 失败: %s，使用本地默认数据", key, e)
                fallback = getattr(self, f"_default_{key}")
                setattr(self, f"_{key}", fallback())

    def _safe_get(self, fields: dict, key: str, default=None):
        val = fields.get(key, default)
        if isinstance(val, list) and val:
            if isinstance(val[0], dict) and "text" in val[0]:
                return "".join(item.get("text", "") for item in val)
            return val[0]
        return val if val is not None else default

    def _record_to_course(self, record: dict) -> dict:
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "课程ID", 0) or 0),
            "name": str(self._safe_get(f, "课程名称", "")),
            "desc": str(self._safe_get(f, "课程描述", "")),
            "categories": self._parse_list(self._safe_get(f, "分类", "")),
            "tags": self._parse_list(self._safe_get(f, "标签", "")),
            "difficulty": str(self._safe_get(f, "难度", "初级")),
            "duration": int(self._safe_get(f, "时长(小时)", 0) or 0),
            "instructor": str(self._safe_get(f, "讲师", "")),
            "cover_color": str(self._safe_get(f, "封面色", "#3B82F6")),
        }

    def _record_to_user(self, record: dict) -> dict:
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "学员ID", 0) or 0),
            "name": str(self._safe_get(f, "姓名", "")),
            "department": str(self._safe_get(f, "部门", "")),
            "position": str(self._safe_get(f, "岗位", "")),
            "avatar": str(self._safe_get(f, "头像", "")),
        }

    def _record_to_interaction(self, record: dict) -> dict:
        f = record.get("fields", {})
        return {
            "user_id": int(self._safe_get(f, "学员ID", 0) or 0),
            "course_id": int(self._safe_get(f, "课程ID", 0) or 0),
            "progress": float(self._safe_get(f, "学习进度", 0) or 0),
            "rating": int(self._safe_get(f, "评分", 0) or 0),
            "behavior_weight": float(self._safe_get(f, "行为权重", 0) or 0),
        }

    def _record_to_instructor(self, record: dict) -> dict:
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "讲师ID", 0) or 0),
            "name": str(self._safe_get(f, "姓名", "")),
            "department": str(self._safe_get(f, "部门", "")),
            "title": str(self._safe_get(f, "职称", "")),
            "expertise": self._parse_list(self._safe_get(f, "专长领域", "")),
            "intro": str(self._safe_get(f, "简介", "")),
            "avatar": str(self._safe_get(f, "头像", "")),
            "status": str(self._safe_get(f, "状态", "在职")),
        }

    def _record_to_enrollment(self, record: dict) -> dict:
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "报名ID", 0) or 0),
            "user_id": int(self._safe_get(f, "学员ID", 0) or 0),
            "user_name": str(self._safe_get(f, "学员姓名", "")),
            "course_id": int(self._safe_get(f, "课程ID", 0) or 0),
            "course_name": str(self._safe_get(f, "课程名称", "")),
            "enroll_time": str(self._safe_get(f, "报名时间", "")),
            "status": str(self._safe_get(f, "审批状态", "待审批")),
            "approver": str(self._safe_get(f, "审批人", "")),
            "approve_time": str(self._safe_get(f, "审批时间", "")),
        }

    def _record_to_announcement(self, record: dict) -> dict:
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "公告ID", 0) or 0),
            "title": str(self._safe_get(f, "标题", "")),
            "content": str(self._safe_get(f, "内容", "")),
            "publisher": str(self._safe_get(f, "发布人", "")),
            "publish_time": str(self._safe_get(f, "发布时间", "")),
            "status": str(self._safe_get(f, "状态", "已发布")),
            "priority": str(self._safe_get(f, "优先级", "普通")),
            "category": str(self._safe_get(f, "分类", "通知")),
        }

    @staticmethod
    def _parse_list(value) -> list:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            for sep in ["、", ",", "，", ";", "；"]:
                value = value.replace(sep, ",")
            return [v.strip() for v in value.split(",") if v.strip()]
        return []

    def _default_instructors(self) -> list:
        return [
            {"id": 1, "name": "陈明", "department": "技术研发部", "title": "高级架构师",
             "expertise": ["Java", "微服务", "架构设计"], "intro": "10年Java开发经验",
             "avatar": "陈", "status": "在职"},
            {"id": 2, "name": "王芳", "department": "技术研发部", "title": "前端技术专家",
             "expertise": ["Vue", "React", "JavaScript"], "intro": "8年前端开发经验",
             "avatar": "王", "status": "在职"},
            {"id": 3, "name": "孙博士", "department": "数据科学部", "title": "AI研究员",
             "expertise": ["机器学习", "Python", "数据分析"], "intro": "机器学习博士",
             "avatar": "孙", "status": "在职"},
            {"id": 4, "name": "刘洋", "department": "技术研发部", "title": "全栈工程师",
             "expertise": ["React", "Node.js", "性能优化"], "intro": "全栈开发专家",
             "avatar": "刘", "status": "在职"},
        ]

    def _default_enrollments(self) -> list:
        return [
            {"id": 1, "user_id": 1, "user_name": "张三", "course_id": 3,
             "course_name": "Vue3 前端开发", "enroll_time": "2026-08-15 10:30",
             "status": "已通过", "approver": "王经理", "approve_time": "2026-08-15 14:00"},
            {"id": 2, "user_id": 2, "user_name": "李四", "course_id": 7,
             "course_name": "机器学习入门", "enroll_time": "2026-08-18 09:00",
             "status": "待审批", "approver": "", "approve_time": ""},
            {"id": 3, "user_id": 5, "user_name": "周婷", "course_id": 6,
             "course_name": "React 进阶指南", "enroll_time": "2026-08-19 11:20",
             "status": "待审批", "approver": "", "approve_time": ""},
        ]

    def _default_announcements(self) -> list:
        return [
            {"id": 1, "title": "2026年秋季培训计划启动",
             "content": "秋季培训计划现已开放报名，涵盖技术、管理、安全等多个方向，请各位同事积极报名。",
             "publisher": "人力资源部", "publish_time": "2026-08-01 09:00",
             "status": "已发布", "priority": "高", "category": "培训通知"},
            {"id": 2, "title": "新员工入职培训安排",
             "content": "本月新员工入职培训定于8月25日举行，请各部门协调好工作。",
             "publisher": "人力资源部", "publish_time": "2026-08-10 14:00",
             "status": "已发布", "priority": "普通", "category": "入职培训"},
        ]

    @property
    def courses(self) -> List[dict]:
        return self._courses

    @property
    def users(self) -> List[dict]:
        return self._users

    @property
    def interactions(self) -> List[dict]:
        return self._interactions

    @property
    def instructors(self) -> List[dict]:
        return self._instructors

    @property
    def enrollments(self) -> List[dict]:
        return self._enrollments

    @property
    def announcements(self) -> List[dict]:
        return self._announcements

    # ===== CRUD：课程管理 =====

    def add_course(self, course: dict) -> bool:
        self._courses.append(course)
        if self._use_bitable:
            self.client.create_record("courses", self.TABLE_NAMES["courses"], {
                "课程ID": course["id"], "课程名称": course["name"],
                "课程描述": course.get("desc", ""),
                "分类": "、".join(course.get("categories", [])),
                "标签": "、".join(course.get("tags", [])),
                "难度": course.get("difficulty", "初级"),
                "时长(小时)": course.get("duration", 0),
                "讲师": course.get("instructor", ""),
                "封面色": course.get("cover_color", "#3B82F6"),
            })
        return True

    def update_course(self, course_id: int, updates: dict) -> bool:
        for c in self._courses:
            if c["id"] == course_id:
                c.update(updates)
                break
        if self._use_bitable:
            rid = self._record_id_map["courses"].get(course_id)
            if rid:
                field_map = {"name": "课程名称", "desc": "课程描述",
                             "difficulty": "难度", "duration": "时长(小时)",
                             "instructor": "讲师"}
                fields = {field_map[k]: v for k, v in updates.items() if k in field_map}
                if fields:
                    self.client.update_record("courses", self.TABLE_NAMES["courses"], rid, fields)
        return True

    def delete_course(self, course_id: int) -> bool:
        self._courses = [c for c in self._courses if c["id"] != course_id]
        if self._use_bitable:
            rid = self._record_id_map["courses"].pop(course_id, None)
            if rid:
                self.client.delete_record("courses", self.TABLE_NAMES["courses"], rid)
        return True

    # ===== CRUD：讲师管理 =====

    def add_instructor(self, instructor: dict) -> bool:
        self._instructors.append(instructor)
        if self._use_bitable:
            self.client.create_record("instructors", self.TABLE_NAMES["instructors"], {
                "讲师ID": instructor["id"], "姓名": instructor["name"],
                "部门": instructor.get("department", ""),
                "职称": instructor.get("title", ""),
                "专长领域": "、".join(instructor.get("expertise", [])),
                "简介": instructor.get("intro", ""),
                "状态": instructor.get("status", "在职"),
            })
        return True

    def update_instructor(self, instructor_id: int, updates: dict) -> bool:
        for i in self._instructors:
            if i["id"] == instructor_id:
                i.update(updates)
                break
        if self._use_bitable:
            rid = self._record_id_map["instructors"].get(instructor_id)
            if rid:
                field_map = {"name": "姓名", "department": "部门", "title": "职称",
                             "intro": "简介", "status": "状态"}
                fields = {field_map[k]: v for k, v in updates.items() if k in field_map}
                if fields:
                    self.client.update_record("instructors", self.TABLE_NAMES["instructors"], rid, fields)
        return True

    def delete_instructor(self, instructor_id: int) -> bool:
        self._instructors = [i for i in self._instructors if i["id"] != instructor_id]
        if self._use_bitable:
            rid = self._record_id_map["instructors"].pop(instructor_id, None)
            if rid:
                self.client.delete_record("instructors", self.TABLE_NAMES["instructors"], rid)
        return True

    # ===== CRUD：报名审批 =====

    def add_enrollment(self, enrollment: dict) -> bool:
        self._enrollments.append(enrollment)
        if self._use_bitable:
            self.client.create_record("enrollments", self.TABLE_NAMES["enrollments"], {
                "报名ID": enrollment["id"],
                "学员ID": enrollment.get("user_id", 0),
                "学员姓名": enrollment.get("user_name", ""),
                "课程ID": enrollment.get("course_id", 0),
                "课程名称": enrollment.get("course_name", ""),
                "报名时间": enrollment.get("enroll_time", ""),
                "审批状态": enrollment.get("status", "待审批"),
            })
        return True

    def approve_enrollment(self, enrollment_id: int, approver: str,
                           status: str = "已通过") -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for e in self._enrollments:
            if e["id"] == enrollment_id:
                e["status"] = status
                e["approver"] = approver
                e["approve_time"] = now
                break
        if self._use_bitable:
            rid = self._record_id_map["enrollments"].get(enrollment_id)
            if rid:
                self.client.update_record("enrollments", self.TABLE_NAMES["enrollments"], rid, {
                    "审批状态": status, "审批人": approver, "审批时间": now
                })
        return True

    def delete_enrollment(self, enrollment_id: int) -> bool:
        self._enrollments = [e for e in self._enrollments if e["id"] != enrollment_id]
        if self._use_bitable:
            rid = self._record_id_map["enrollments"].pop(enrollment_id, None)
            if rid:
                self.client.delete_record("enrollments", self.TABLE_NAMES["enrollments"], rid)
        return True

    # ===== CRUD：公告管理 =====

    def add_announcement(self, announcement: dict) -> bool:
        self._announcements.append(announcement)
        if self._use_bitable:
            self.client.create_record("announcements", self.TABLE_NAMES["announcements"], {
                "公告ID": announcement["id"], "标题": announcement["title"],
                "内容": announcement.get("content", ""),
                "发布人": announcement.get("publisher", ""),
                "发布时间": announcement.get("publish_time", ""),
                "状态": announcement.get("status", "已发布"),
                "优先级": announcement.get("priority", "普通"),
                "分类": announcement.get("category", "通知"),
            })
        return True

    def update_announcement(self, announcement_id: int, updates: dict) -> bool:
        for a in self._announcements:
            if a["id"] == announcement_id:
                a.update(updates)
                break
        if self._use_bitable:
            rid = self._record_id_map["announcements"].get(announcement_id)
            if rid:
                field_map = {"title": "标题", "content": "内容", "status": "状态",
                             "priority": "优先级", "category": "分类"}
                fields = {field_map[k]: v for k, v in updates.items() if k in field_map}
                if fields:
                    self.client.update_record("announcements", self.TABLE_NAMES["announcements"], rid, fields)
        return True

    def delete_announcement(self, announcement_id: int) -> bool:
        self._announcements = [a for a in self._announcements if a["id"] != announcement_id]
        if self._use_bitable:
            rid = self._record_id_map["announcements"].pop(announcement_id, None)
            if rid:
                self.client.delete_record("announcements", self.TABLE_NAMES["announcements"], rid)
        return True

    # ===== 学习记录 =====

    def add_interaction(self, user_id: int, course_id: int,
                        progress: float, rating: int,
                        behavior_weight: float) -> bool:
        self._interactions.append({
            "user_id": user_id, "course_id": course_id,
            "progress": progress, "rating": rating,
            "behavior_weight": behavior_weight
        })
        if self._use_bitable:
            self.client.create_record(
                "interactions", self.TABLE_NAMES["interactions"],
                {"学员ID": user_id, "课程ID": course_id,
                 "学习进度": progress, "评分": rating,
                 "行为权重": behavior_weight}
            )
        return True

    # ===== 同步与健康检查 =====

    def sync_to_bitable(self) -> dict:
        if not self._use_bitable:
            return {"success": False, "message": "多维表格未配置，无法同步"}
        sync_log = []
        modules = [
            ("courses", "课程", lambda c: {
                "课程ID": c["id"], "课程名称": c["name"],
                "课程描述": c.get("desc", ""),
                "分类": "、".join(c.get("categories", [])),
                "标签": "、".join(c.get("tags", [])),
                "难度": c.get("difficulty", "初级"),
                "时长(小时)": c.get("duration", 0),
                "讲师": c.get("instructor", ""),
            }),
            ("instructors", "讲师", lambda i: {
                "讲师ID": i["id"], "姓名": i["name"],
                "部门": i.get("department", ""),
                "职称": i.get("title", ""),
                "专长领域": "、".join(i.get("expertise", [])),
                "简介": i.get("intro", ""),
                "状态": i.get("status", "在职"),
            }),
            ("enrollments", "报名审批", lambda e: {
                "报名ID": e["id"], "学员ID": e.get("user_id", 0),
                "学员姓名": e.get("user_name", ""),
                "课程ID": e.get("course_id", 0),
                "课程名称": e.get("course_name", ""),
                "报名时间": e.get("enroll_time", ""),
                "审批状态": e.get("status", "待审批"),
                "审批人": e.get("approver", ""),
            }),
            ("announcements", "公告", lambda a: {
                "公告ID": a["id"], "标题": a["title"],
                "内容": a.get("content", ""),
                "发布人": a.get("publisher", ""),
                "发布时间": a.get("publish_time", ""),
                "状态": a.get("status", "已发布"),
                "优先级": a.get("priority", "普通"),
                "分类": a.get("category", "通知"),
            }),
        ]
        for key, label, converter in modules:
            items = getattr(self, f"_{key}")
            if not items:
                sync_log.append(f"{label}: 无数据")
                continue
            try:
                records = [{"fields": converter(item)} for item in items]
                self.client.batch_create_records(key, self.TABLE_NAMES[key], records)
                sync_log.append(f"{label}: 成功同步 {len(items)} 条")
            except Exception as e:
                sync_log.append(f"{label}: 同步失败 - {e}")
        return {"success": True, "log": sync_log, "sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def health_check(self) -> dict:
        return {
            "data_source": "feishu_bitable" if self._use_bitable else "local_memory",
            "bitable_configured": self.client.is_configured,
            "courses": len(self._courses),
            "users": len(self._users),
            "interactions": len(self._interactions),
            "instructors": len(self._instructors),
            "enrollments": len(self._enrollments),
            "announcements": len(self._announcements),
        }
