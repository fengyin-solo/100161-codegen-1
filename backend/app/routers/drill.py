"""应急演练接口：登记演练计划，演练结束后补录评估结论与发现问题。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.drill import (
    LIST_FIELDS,
    STATUS_ORDER,
    DrillService,
)

router = APIRouter(prefix="/api/drill", tags=["应急演练"])

service = DrillService()


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按演练科目、参演单位或编号检索"),
    status: str | None = Query(default=None, description="待实施、演练中、已评估"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按科目与状态过滤应急演练计划；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if status and status not in STATUS_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"状态「{status}」不合法，只支持：{'、'.join(STATUS_ORDER)}",
        )
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出应急演练清单：返回全量计划与评估数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "drill", "fields": LIST_FIELDS, "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条演练计划明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"演练计划 {entry_id} 不存在或已删除")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记演练计划（科目、参演单位、计划日期、组织人）；不满足登记条件时说明原因。"""
    entry, message = service.create_entry(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="演练计划已登记，状态为待实施", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """开始演练、提交评估、退回重新评估；校验失败会拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
