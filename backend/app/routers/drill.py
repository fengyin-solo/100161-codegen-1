"""应急演练接口：维护演练计划、状态流转与评估结论。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.drill import DrillService

router = APIRouter(prefix="/api/drill", tags=["应急演练"])

service = DrillService()


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按演练科目、参演单位或组织人检索"),
    status: str | None = Query(default=None, description="待实施、演练中、已评估"),
    pending_only: bool = Query(default=False, description="是否只看待办清单"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按关键字与状态过滤演练计划；待办数据仍从同一份计划记录读取。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(
        keyword=keyword, status=status, pending_only=pending_only, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出应急演练清单：返回当前全量计划及评估信息。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "drill", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条演练计划及同一份评估结论。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"演练计划 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记演练计划；校验失败时返回可读原因，不生成待办记录。"""
    entry, message = service.create_entry(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """执行开始演练、提交评估、变更评估；失败时保留计划并回到待办清单。"""
    entry, message, ok = service.run_action(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=ok, message=message, entry=entry)
