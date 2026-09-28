"""应急演练业务规则：计划登记、演练流转、评估补录与重新评估。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "drill"
REQUIRED_FIELDS = ["演练科目", "参演单位", "计划日期", "组织人"]
STATUS_PENDING = "待实施"
STATUS_RUNNING = "演练中"
STATUS_EVALUATED = "已评估"

CONCLUSION = "评估结论"
ISSUES = "发现问题"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _parse_plan_date(value: str) -> tuple[date | None, str]:
    try:
        return date.fromisoformat(value), ""
    except ValueError:
        return None, "计划日期格式无效，请使用 YYYY-MM-DD 格式"


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    result = dict(entry)
    result["计划状态"] = entry.get("status")
    return result


def _to_action_result(
    result: tuple[dict[str, Any] | None, str, bool]
) -> tuple[dict[str, Any] | None, str, bool]:
    entry, message, ok = result
    if entry is None:
        return None, message, ok
    return _public_entry(entry), message, ok


class DrillService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        pending_only: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [
                row
                for row in rows
                if keyword in str(row.get("演练科目", ""))
                or keyword in str(row.get("参演单位", ""))
                or keyword in str(row.get("组织人", ""))
            ]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if pending_only:
            rows = [row for row in rows if row.get("pending")]
        total = len(rows)
        start = max(page - 1, 0) * size
        return [_public_entry(row) for row in rows[start:start + size]], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return _public_entry(entry) if entry else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        missing = [field for field in REQUIRED_FIELDS if not _clean(values.get(field))]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}，该计划未放入待办清单"

        plan_date_text = _clean(values.get("计划日期"))
        plan_date, date_message = _parse_plan_date(plan_date_text)
        if plan_date is None:
            return None, date_message
        if plan_date < date.today():
            return None, "计划日期不能早于当天，请重新选择演练日期"

        rows = store.rows(MODULE)
        entry = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "演练科目": _clean(values.get("演练科目")),
            "参演单位": _clean(values.get("参演单位")),
            "计划日期": plan_date.isoformat(),
            "组织人": _clean(values.get("组织人")),
            CONCLUSION: "",
            ISSUES: "",
            "status": STATUS_PENDING,
            "pending": True,
            "abnormal": False,
        }
        rows.append(entry)
        return _public_entry(entry), "演练计划已登记，已放入待办清单"

    def run_action(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str, bool]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"演练计划 {entry_id} 不存在或已归档", False

        action = _clean(values.get("action"))
        if action == "开始演练":
            return _to_action_result(self._start(entry))
        if action == "提交评估":
            return _to_action_result(self._submit_evaluation(entry, values))
        if action == "变更评估":
            return _to_action_result(self._change_evaluation(entry, values))
        return None, f"动作「{action}」不属于应急演练可执行范围", False

    def _start(self, entry: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
        if entry.get("status") != STATUS_PENDING:
            entry["pending"] = True
            return entry, f"演练计划当前为「{entry.get('status')}」，不能重复开始，已保留在待办清单", False
        entry["status"] = STATUS_RUNNING
        entry["pending"] = True
        entry["abnormal"] = False
        return entry, "演练已开始", True

    def _submit_evaluation(
        self, entry: dict[str, Any], values: dict[str, Any]
    ) -> tuple[dict[str, Any], str, bool]:
        conclusion = _clean(values.get(CONCLUSION))
        if not conclusion:
            entry["pending"] = True
            return entry, "评估结论空缺时不允许标记完成，请补录评估结论后再提交", False
        if entry.get("status") != STATUS_RUNNING:
            entry["pending"] = True
            return entry, f"演练计划当前为「{entry.get('status')}」，不能重复评估，已放回待办清单", False

        entry[CONCLUSION] = conclusion
        entry[ISSUES] = _clean(values.get(ISSUES))
        entry["status"] = STATUS_EVALUATED
        entry["pending"] = False
        entry["abnormal"] = False
        return entry, "演练评估已提交", True

    def _change_evaluation(
        self, entry: dict[str, Any], values: dict[str, Any]
    ) -> tuple[dict[str, Any], str, bool]:
        if entry.get("status") != STATUS_EVALUATED:
            entry["pending"] = True
            return entry, f"演练计划当前为「{entry.get('status')}」，暂不能变更评估，已放回待办清单", False

        new_conclusion = _clean(values.get(CONCLUSION))
        if not new_conclusion:
            entry["pending"] = True
            return entry, "变更后的评估结论不能为空，请填写新的评估结论", False
        if new_conclusion == _clean(entry.get(CONCLUSION)):
            entry["pending"] = True
            return entry, "评估结论未发生变化，不能按重复评估提交；请修改结论后再退回重评", False

        entry[CONCLUSION] = new_conclusion
        if _clean(values.get(ISSUES)):
            entry[ISSUES] = _clean(values.get(ISSUES))
        entry["status"] = STATUS_RUNNING
        entry["pending"] = True
        entry["abnormal"] = False
        return entry, "评估结论已变更，计划已回到演练中，请重新评估", True
