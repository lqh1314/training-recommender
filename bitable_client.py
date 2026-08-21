"""
培训管理系统 - 飞书多维表格对接模块
支持将课程、学员、学习记录、评价数据存储在飞书多维表格中。
未配置飞书凭证时自动回退到本地内存数据（data.py）。

环境变量配置：
    FEISHU_APP_ID       飞书应用 App ID
    FEISHU_APP_SECRET   飞书应用 App Secret
    BITABLE_APP_TOKEN   多维表格 App Token
    BITABLE_TABLE_COURSES     课程表 ID（可选，默认自动查找）
    BITABLE_TABLE_USERS       学员表 ID（可选）
    BITABLE_TABLE_INTERACTIONS 学习记录表 ID（可选）
"""
import os
import json
import logging
from typing import List, Dict, Optional, Any
from urllib import request, parse, error

logger = logging.getLogger(__name__)

FEISHU_BASE = "https://open.feishu.cn/open-apis"
TOKEN_URL = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
BITABLE_LIST_URL = f"{FEISHU_BASE}/bitable/v1/apps/{{app_token}}/tables"
BITABLE_RECORDS_URL = f"{FEISHU_BASE}/bitable/v1/apps/{{app_token}}/tables/{{table_id}}/records"
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
        """是否已配置飞书凭证"""
        return bool(self.app_id and self.app_secret and self.app_token)

    def _request(self, url: str, method: str = "GET",
                 data: dict = None, params: dict = None,
                 retry_auth: bool = True) -> dict:
        """发送 HTTP 请求到飞书 API"""
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        body = json.dumps(data).encode("utf-8") if data else None
        req = request.Request(url, data=body, headers=headers, method=method)

        try:
            with request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            # token 过期自动刷新一次
            if e.code == 401 and retry_auth:
                logger.info("飞书 token 过期，自动刷新")
                self._token = None
                self._authenticate()
                return self._request(url, method, data, params, retry_auth=False)
            raise RuntimeError(f"飞书 API 请求失败 [{e.code}]: {err_body}")

        # 飞书业务错误码
        code = result.get("code", -1)
        if code != 0:
            raise RuntimeError(f"飞书 API 业务错误: code={code}, msg={result.get('msg')}")
        return result.get("data", {})

    def _authenticate(self):
        """获取 tenant_access_token"""
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
        """连接并验证多维表格可访问性"""
        if not self.is_configured:
            logger.info("未配置飞书凭证，使用本地数据")
            return False
        self._authenticate()
        # 列出表格验证连通性
        self._list_tables()
        logger.info("多维表格连接成功，app_token=%s", self.app_token[:8] + "...")
        return True

    def _list_tables(self) -> List[dict]:
        """列出多维表格中的所有数据表"""
        url = BITABLE_LIST_URL.format(app_token=self.app_token)
        result = self._request(url)
        tables = result.get("items", [])
        for t in tables:
            self._table_ids[t["name"]] = t["table_id"]
        return tables

    def _resolve_table_id(self, table_key: str, table_name: str) -> str:
        """解析表 ID：优先环境变量，其次按名称查找"""
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

    # ===== 记录 CRUD =====

    def list_records(self, table_key: str, table_name: str,
                     page_size: int = 100, filter_expr: str = None) -> List[dict]:
        """列出数据表中的所有记录（自动分页）"""
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_URL.format(
            app_token=self.app_token, table_id=table_id
        )
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

    def create_record(self, table_key: str, table_name: str,
                      fields: dict) -> dict:
        """创建一条记录"""
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_URL.format(
            app_token=self.app_token, table_id=table_id
        )
        return self._request(url, method="POST", data={"fields": fields})

    def update_record(self, table_key: str, table_name: str,
                      record_id: str, fields: dict) -> dict:
        """更新一条记录"""
        table_id = self._resolve_table_id(table_key, table_name)
        url = f"{BITABLE_RECORDS_URL.format(app_token=self.app_token, table_id=table_id)}/{record_id}"
        return self._request(url, method="PUT", data={"fields": fields})

    def delete_record(self, table_key: str, table_name: str,
                      record_id: str) -> bool:
        """删除一条记录"""
        table_id = self._resolve_table_id(table_key, table_name)
        url = f"{BITABLE_RECORDS_URL.format(app_token=self.app_token, table_id=table_id)}/{record_id}"
        self._request(url, method="DELETE")
        return True

    def search_records(self, table_key: str, table_name: str,
                       filter_conditions: dict) -> List[dict]:
        """按条件搜索记录"""
        table_id = self._resolve_table_id(table_key, table_name)
        url = BITABLE_RECORDS_SEARCH_URL.format(
            app_token=self.app_token, table_id=table_id
        )
        body = {"filter": {"conjunction": "and", "conditions": filter_conditions}}
        result = self._request(url, method="POST", data=body)
        return result.get("items", [])


class DataProvider:
    """
    数据提供者：统一封装本地数据和多维表格数据。
    优先使用多维表格，未配置时回退到 data.py。
    """

    # 多维表格表名映射
    TABLE_NAMES = {
        "courses": "课程表",
        "users": "学员表",
        "interactions": "学习记录表",
    }

    def __init__(self, client: BitableClient = None):
        self.client = client or BitableClient()
        self._use_bitable = False
        self._courses = []
        self._users = []
        self._interactions = []

    def init(self):
        """初始化数据加载"""
        self._use_bitable = self.client.connect()
        if self._use_bitable:
            self._load_from_bitable()
        else:
            self._load_from_local()
        logger.info("数据加载完成: %d 门课程, %d 位学员, %d 条交互",
                    len(self._courses), len(self._users), len(self._interactions))
        return self

    def _load_from_local(self):
        """从本地 data.py 加载"""
        from data import COURSES, USERS, INTERACTIONS
        self._courses = COURSES
        self._users = USERS
        self._interactions = INTERACTIONS

    def _load_from_bitable(self):
        """从多维表格加载数据"""
        # 加载课程
        records = self.client.list_records("courses", self.TABLE_NAMES["courses"])
        self._courses = [self._record_to_course(r) for r in records]

        # 加载学员
        records = self.client.list_records("users", self.TABLE_NAMES["users"])
        self._users = [self._record_to_user(r) for r in records]

        # 加载学习记录
        records = self.client.list_records(
            "interactions", self.TABLE_NAMES["interactions"]
        )
        self._interactions = [self._record_to_interaction(r) for r in records]

    def _safe_get(self, fields: dict, key: str, default=None):
        """安全获取飞书多维表格字段值（文本字段可能是列表形式）"""
        val = fields.get(key, default)
        if isinstance(val, list) and val:
            # 飞书富文本字段: [{"text": "xxx", "type": "text"}]
            if isinstance(val[0], dict) and "text" in val[0]:
                return "".join(item.get("text", "") for item in val)
            return val[0]
        return val if val is not None else default

    def _record_to_course(self, record: dict) -> dict:
        """多维表格记录转课程字典"""
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "课程ID", 0)),
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
        """多维表格记录转学员字典"""
        f = record.get("fields", {})
        return {
            "id": int(self._safe_get(f, "学员ID", 0)),
            "name": str(self._safe_get(f, "姓名", "")),
            "department": str(self._safe_get(f, "部门", "")),
            "position": str(self._safe_get(f, "岗位", "")),
            "avatar": str(self._safe_get(f, "头像", "")),
        }

    def _record_to_interaction(self, record: dict) -> dict:
        """多维表格记录转学习交互字典"""
        f = record.get("fields", {})
        return {
            "user_id": int(self._safe_get(f, "学员ID", 0)),
            "course_id": int(self._safe_get(f, "课程ID", 0)),
            "progress": float(self._safe_get(f, "学习进度", 0) or 0),
            "rating": int(self._safe_get(f, "评分", 0) or 0),
            "behavior_weight": float(self._safe_get(f, "行为权重", 0) or 0),
        }

    @staticmethod
    def _parse_list(value) -> list:
        """解析逗号/顿号分隔的字符串为列表"""
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            for sep in ["、", ",", "，", ";", "；"]:
                value = value.replace(sep, ",")
            return [v.strip() for v in value.split(",") if v.strip()]
        return []

    # ===== 公开接口 =====

    @property
    def courses(self) -> List[dict]:
        return self._courses

    @property
    def users(self) -> List[dict]:
        return self._users

    @property
    def interactions(self) -> List[dict]:
        return self._interactions

    def add_interaction(self, user_id: int, course_id: int,
                        progress: float, rating: int,
                        behavior_weight: float) -> bool:
        """新增学习记录（同步到多维表格）"""
        self._interactions.append({
            "user_id": user_id, "course_id": course_id,
            "progress": progress, "rating": rating,
            "behavior_weight": behavior_weight
        })
        if self._use_bitable:
            self.client.create_record(
                "interactions", self.TABLE_NAMES["interactions"],
                {
                    "学员ID": user_id, "课程ID": course_id,
                    "学习进度": progress, "评分": rating,
                    "行为权重": behavior_weight
                }
            )
        return True

    def health_check(self) -> dict:
        """健康检查：返回数据源状态"""
        return {
            "data_source": "feishu_bitable" if self._use_bitable else "local_memory",
            "bitable_configured": self.client.is_configured,
            "courses": len(self._courses),
            "users": len(self._users),
            "interactions": len(self._interactions),
        }
