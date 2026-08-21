#!/usr/bin/env python3
"""
培训管理系统 - 飞书多维表格定时同步脚本
每30分钟执行一次，将本地数据增量同步到飞书多维表格。

用法：
    python3 sync_bitable.py              # 执行增量同步
    python3 sync_bitable.py --full       # 执行全量同步
    python3 sync_bitable.py --status     # 查看同步状态

环境变量：
    FEISHU_APP_ID, FEISHU_APP_SECRET, BITABLE_APP_TOKEN
"""

import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bitable_client import DataProvider, BitableClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "sync.log"),
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger(__name__)

SYNC_STATE_FILE = os.path.join(os.path.dirname(__file__), ".sync_state.json")


def load_sync_state() -> dict:
    """加载上次同步状态"""
    if os.path.exists(SYNC_STATE_FILE):
        try:
            with open(SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"last_sync": None, "last_full_sync": None, "counts": {}}


def save_sync_state(state: dict):
    """保存同步状态"""
    with open(SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def incremental_sync(provider: DataProvider) -> dict:
    """
    增量同步：从多维表格拉取最新数据，合并到本地。
    对比各模块记录数，如有新增则更新本地缓存。
    """
    if not provider.client.is_configured:
        return {"success": False, "message": "多维表格未配置，跳过同步"}

    result = {"modules": {}, "sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    # 重新从多维表格加载所有数据
    provider._load_from_bitable()

    modules = {
        "courses": ("课程", len(provider.courses)),
        "instructors": ("讲师", len(provider.instructors)),
        "enrollments": ("报名审批", len(provider.enrollments)),
        "announcements": ("公告", len(provider.announcements)),
        "users": ("学员", len(provider.users)),
        "interactions": ("学习记录", len(provider.interactions)),
    }

    for key, (label, count) in modules.items():
        result["modules"][key] = {"label": label, "count": count}
        logger.info("增量同步 %s: %d 条", label, count)

    result["success"] = True
    return result


def full_sync(provider: DataProvider) -> dict:
    """全量同步：本地数据推送到多维表格"""
    result = provider.sync_to_bitable()
    return result


def show_status(provider: DataProvider):
    """显示当前同步状态"""
    state = load_sync_state()
    health = provider.health_check()

    print("=" * 50)
    print("  培训管理系统 - 多维表格同步状态")
    print("=" * 50)
    print(f"  数据源: {health['data_source']}")
    print(f"  多维表格已配置: {'是' if health['bitable_configured'] else '否'}")
    print(f"  上次同步: {state.get('last_sync', '从未')}")
    print(f"  上次全量同步: {state.get('last_full_sync', '从未')}")
    print("-" * 50)
    print(f"  课程: {health['courses']} 门")
    print(f"  讲师: {health['instructors']} 位")
    print(f"  报名审批: {health['enrollments']} 条")
    print(f"  公告: {health['announcements']} 条")
    print(f"  学员: {health['users']} 位")
    print(f"  学习记录: {health['interactions']} 条")
    print("=" * 50)


def main():
    """主入口"""
    provider = DataProvider().init()
    args = sys.argv[1:]

    if "--status" in args:
        show_status(provider)
        return

    if "--full" in args:
        logger.info("开始全量同步到飞书多维表格...")
        result = full_sync(provider)
        if result.get("success"):
            for log in result.get("log", []):
                logger.info("  %s", log)
            state = load_sync_state()
            state["last_full_sync"] = result["sync_time"]
            state["last_sync"] = result["sync_time"]
            save_sync_state(state)
            logger.info("全量同步完成: %s", result["sync_time"])
        else:
            logger.warning("全量同步失败: %s", result.get("message"))
        return

    # 默认：增量同步
    logger.info("开始增量同步（每30分钟）...")
    result = incremental_sync(provider)
    if result.get("success"):
        state = load_sync_state()
        state["last_sync"] = result["sync_time"]
        state["counts"] = {k: v["count"] for k, v in result["modules"].items()}
        save_sync_state(state)
        logger.info("增量同步完成: %s", result["sync_time"])
    else:
        logger.warning("增量同步跳过: %s", result.get("message"))


if __name__ == "__main__":
    main()
