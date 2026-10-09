from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import ActiveStatus, Department, Employee, EmployeeStatus
from app.schemas.department import DepartmentCreate, DepartmentNode, DepartmentUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/departments", tags=["departments"])


async def _validate_parent(session: AsyncSession, department_id: int | None, parent_id: int | None) -> None:
    if parent_id is None:
        return
    if department_id is not None and parent_id == department_id:
        raise BusinessError(20007, "DEPARTMENT_PARENT_INVALID", "部门不能将自身设为上级部门", 409)
    parent = await session.scalar(select(Department).where(Department.id == parent_id, Department.deleted_at.is_(None)))
    if parent is None:
        raise BusinessError(20008, "DEPARTMENT_PARENT_NOT_FOUND", "上级部门不存在", 404)
    if department_id is None:
        return
    seen: set[int] = {department_id}
    cursor = parent
    while cursor.parent_id is not None:
        if cursor.id in seen:
            raise BusinessError(20007, "DEPARTMENT_PARENT_INVALID", "部门层级不能形成循环", 409)
        seen.add(cursor.id)
        cursor = await session.get(Department, cursor.parent_id)
        if cursor is None:
            break


async def _validate_leader(session: AsyncSession, leader_id: int | None, department_id: int | None) -> None:
    if leader_id is None:
        return
    employee = await session.get(Employee, leader_id)
    if employee is None or employee.status != EmployeeStatus.ACTIVE:
        raise BusinessError(20009, "DEPARTMENT_LEADER_INVALID", "部门主管不存在或已离职", 409)
    if department_id is not None and employee.department_id != department_id:
        raise BusinessError(20009, "DEPARTMENT_LEADER_INVALID", "部门主管必须属于当前部门", 409)


def _build_tree(rows: list[Department]) -> list[dict]:
    nodes = {
        row.id: DepartmentNode(
            id=row.id,
            name=row.name,
            parent_id=row.parent_id,
            leader_id=row.leader_id,
            created_at=row.created_at,
        ).model_dump(mode="json")
        for row in rows
    }
    children: dict[int | None, list[dict]] = defaultdict(list)
    for node in nodes.values():
        children[node["parent_id"]].append(node)
    for parent_id, items in children.items():
        items.sort(key=lambda item: (item["name"], item["id"]))
        if parent_id is not None and parent_id in nodes:
            nodes[parent_id]["children"] = items
    return children[None]


@router.get("", summary="查询部门树")
async def list_departments(_: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    rows = list((await session.scalars(select(Department).where(Department.deleted_at.is_(None)).order_by(Department.name, Department.id))).all())
    return success(_build_tree(rows))


@router.post("", summary="新增部门")
async def create_department(payload: DepartmentCreate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    await _validate_parent(session, None, payload.parent_id)
    department = Department(name=payload.name.strip(), parent_id=payload.parent_id)
    session.add(department)
    await session.flush()
    if payload.leader_id is not None:
        await _validate_leader(session, payload.leader_id, department.id)
        department.leader_id = payload.leader_id
    await record_audit(session, actor_user_id=current_user.id, action="DEPARTMENT_CREATE", resource_type="department", resource_id=str(department.id), after={"name": department.name, "parent_id": department.parent_id, "leader_id": department.leader_id})
    await session.commit()
    return success({"id": department.id}, message="部门创建成功")


@router.put("/{department_id}", summary="编辑部门")
async def update_department(department_id: int, payload: DepartmentUpdate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    department = await session.scalar(select(Department).where(Department.id == department_id, Department.deleted_at.is_(None)))
    if department is None:
        raise BusinessError(20010, "DEPARTMENT_NOT_FOUND", "部门不存在", 404)
    before = {"name": department.name, "parent_id": department.parent_id, "leader_id": department.leader_id}
    if "parent_id" in payload.model_fields_set:
        await _validate_parent(session, department.id, payload.parent_id)
        department.parent_id = payload.parent_id
    if "name" in payload.model_fields_set and payload.name is not None:
        department.name = payload.name.strip()
    if "leader_id" in payload.model_fields_set and payload.leader_id is not None:
        await _validate_leader(session, payload.leader_id, department.id)
        department.leader_id = payload.leader_id
    elif "leader_id" in payload.model_fields_set:
        department.leader_id = None
    await record_audit(session, actor_user_id=current_user.id, action="DEPARTMENT_UPDATE", resource_type="department", resource_id=str(department.id), before=before, after={"name": department.name, "parent_id": department.parent_id, "leader_id": department.leader_id})
    await session.commit()
    return success(message="部门更新成功")


@router.delete("/{department_id}", summary="删除部门")
async def delete_department(department_id: int, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    department = await session.scalar(select(Department).where(Department.id == department_id, Department.deleted_at.is_(None)))
    if department is None:
        raise BusinessError(20010, "DEPARTMENT_NOT_FOUND", "部门不存在", 404)
    has_children = await session.scalar(select(Department.id).where(Department.parent_id == department_id, Department.deleted_at.is_(None)).limit(1))
    if has_children is not None:
        raise BusinessError(20001, "DEPARTMENT_HAS_CHILDREN", "部门存在下级部门，不能删除", 409)
    has_employees = await session.scalar(select(Employee.id).where(Employee.department_id == department_id, Employee.deleted_at.is_(None), Employee.status == EmployeeStatus.ACTIVE).limit(1))
    if has_employees is not None:
        raise BusinessError(20002, "DEPARTMENT_HAS_EMPLOYEES", "部门存在员工，不能删除", 409)
    from datetime import datetime, timezone
    department.deleted_at = datetime.now(timezone.utc)
    department.status = ActiveStatus.INACTIVE
    await record_audit(session, actor_user_id=current_user.id, action="DEPARTMENT_DELETE", resource_type="department", resource_id=str(department.id), before={"status": ActiveStatus.ACTIVE.value}, after={"status": ActiveStatus.INACTIVE.value})
    await session.commit()
    return success(message="部门删除成功")
