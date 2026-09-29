"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

from typing import Any

from app.seed import SEED_ROWS

# 概览入口展示的中文模块名。
MODULE_LABELS = {
    "flight": "航班计划",
    "stand": "机位资源",
    "apron": "机坪巡查",
    "bridge": "廊桥对接",
    "deicing": "除冰作业",
    "fueling": "航油加注",
    "baggage": "行李装卸",
    "cargo": "货邮装载",
    "catering": "航空配餐",
    "shuttle": "摆渡接送",
    "towing": "航空器牵引",
    "loadsheet": "载重平衡",
    "permit": "通行证件",
    "gse": "保障车辆",
    "safety": "安全监察",
    "agreement": "保障协议",
    "settlement": "保障结算",
    "training": "资质培训",
    "drill": "应急演练",
}


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "label": MODULE_LABELS.get(name, name),
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}


store = Store()
