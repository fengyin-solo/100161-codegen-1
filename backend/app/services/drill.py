"""应急演练业务规则：演练计划登记、三段状态流转与评估补录都收在这里。

状态只有三段，按顺序流转，且评估后允许退回上一段重新评估：
待实施 --开始演练--> 演练中 --提交评估--> 已评估 --退回重新评估--> 演练中
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "drill"

REQUIRED_FIELDS = ["演练科目", "参演单位", "计划日期", "组织人"]
LIST_FIELDS = [
    "演练编号",
    "演练科目",
    "参演单位",
    "计划日期",
    "组织人",
    "评估结论",
    "发现问题",
    "演练状态",
]
STATUS_PENDING = "待实施"
STATUS_RUNNING = "演练中"
STATUS_ASSESSED = "已评估"
STATUS_ORDER = [STATUS_PENDING, STATUS_RUNNING, STATUS_ASSESSED]


def _clean(values: dict[str, Any], field: str) -> str:
    return str(values.get(field) or "").strip()


def _parse_plan_date(raw: str) -> date | None:
    """计划日期只接受 YYYY-MM-DD；非法格式返回 None，由调用方给出可读提示。"""
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


class DrillService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = list(store.rows(MODULE))
        if keyword:
            rows = [
                row
                for row in rows
                if keyword in str(row.get("演练科目", ""))
                or keyword in str(row.get("参演单位", ""))
                or keyword in str(row.get("演练编号", ""))
            ]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        rows.sort(key=lambda row: (not bool(row.get("pending")), -int(row.get("id", 0))))
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """登记演练计划；校验不通过时不写数据，返回可读的失败原因。"""
        for field in REQUIRED_FIELDS:
            if not _clean(values, field):
                return None, f"{field}为必填项，请补充后再登记"

        raw_date = _clean(values, "计划日期")
        plan_date = _parse_plan_date(raw_date)
        if plan_date is None:
            return None, f"计划日期「{raw_date}」格式不正确，请使用YYYY-MM-DD"
        if plan_date < date.today():
            return None, f"计划日期{raw_date}早于当天，只能登记今天及以后的演练计划"

        rows = store.rows(MODULE)
        entry: dict[str, Any] = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "演练编号": f"DRIL-{len(rows) + 1:04d}",
            "演练科目": _clean(values, "演练科目"),
            "参演单位": _clean(values, "参演单位"),
            "计划日期": raw_date,
            "组织人": _clean(values, "组织人"),
            "评估结论": "",
            "发现问题": "",
            "status": STATUS_PENDING,
            "pending": True,
            "abnormal": False,
        }
        rows.append(entry)
        return entry, ""

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"演练计划 {entry_id} 不存在或已删除"

        if action == "开始演练":
            return self._start(entry)
        if action == "提交评估":
            return self._submit_evaluation(entry, values or {})
        if action == "退回重新评估":
            return self._reopen(entry)
        return None, f"动作「{action}」不属于应急演练可执行范围"

    def _start(self, entry: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        if entry["status"] != STATUS_PENDING:
            return None, f"演练计划当前为「{entry['status']}」，只有待实施计划才能开始演练"
        entry["status"] = STATUS_RUNNING
        return entry, "演练已开始，可在结束后补录评估结论"

    def _submit_evaluation(
        self,
        entry: dict[str, Any],
        values: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str]:
        if entry["status"] == STATUS_ASSESSED:
            # 重复评估不允许直接覆盖：退回上一段（演练中），计划重新进入待办清单，
            # 由组织人调整评估结论后再次提交。
            entry["status"] = STATUS_RUNNING
            entry["pending"] = True
            return None, "该演练计划已评估，不能重复提交评估；已退回演练中，请调整评估结论后重新评估"
        if entry["status"] != STATUS_RUNNING:
            return None, f"演练计划当前为「{entry['status']}」，只有演练中的计划才能提交评估"

        conclusion = _clean(values, "评估结论")
        if not conclusion:
            # 结论空缺时不允许标记完成；状态保持演练中，计划仍留在待办清单。
            return None, "评估结论为空，演练不能标记完成，请补充评估结论后再提交"

        issues = _clean(values, "发现问题")
        entry["评估结论"] = conclusion
        entry["发现问题"] = issues
        entry["status"] = STATUS_ASSESSED
        entry["pending"] = False
        entry["abnormal"] = bool(issues)
        return entry, "演练评估已提交，计划状态更新为已评估"

    def _reopen(self, entry: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        if entry["status"] != STATUS_ASSESSED:
            return None, f"演练计划当前为「{entry['status']}」，只有已评估计划才能退回重新评估"
        entry["status"] = STATUS_RUNNING
        entry["pending"] = True
        return entry, "已退回演练中，可修改评估结论与发现问题后重新提交"

    def overview_section(self) -> dict[str, Any]:
        """概览入口的应急演练数据：与演练计划入口读的是同一张表，结论天然同一份。"""
        rows = store.rows(MODULE)

        def in_status(name: str) -> list[dict[str, Any]]:
            return [row for row in rows if row.get("status") == name]

        assessed = in_status(STATUS_ASSESSED)
        return {
            "module": MODULE,
            "counts": [
                {"label": "待实施", "value": len(in_status(STATUS_PENDING))},
                {"label": "演练中", "value": len(in_status(STATUS_RUNNING))},
                {"label": "已评估", "value": len(assessed)},
            ],
            "todo": [
                self._snapshot(row)
                for row in rows
                if row.get("pending") and row.get("status") in STATUS_ORDER
            ],
            "assessed": [self._snapshot(row) for row in assessed],
        }

    @staticmethod
    def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row.get("id"),
            "演练编号": row.get("演练编号", ""),
            "演练科目": row.get("演练科目", ""),
            "参演单位": row.get("参演单位", ""),
            "计划日期": row.get("计划日期", ""),
            "组织人": row.get("组织人", ""),
            "评估结论": row.get("评估结论", ""),
            "发现问题": row.get("发现问题", ""),
            "status": row.get("status", ""),
            "pending": bool(row.get("pending")),
            "abnormal": bool(row.get("abnormal")),
        }
