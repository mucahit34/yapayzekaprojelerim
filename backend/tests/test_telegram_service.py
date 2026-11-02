import pytest

from app.models import Asset, Project, Task, TaskStatus
from app.telegram.service import (
    CommandError,
    approve_task,
    create_project,
    find_project,
    list_projects,
    list_tasks,
)

pytestmark = pytest.mark.asyncio


async def test_create_project_has_empty_fail_closed_scope(db_session):
    project = await create_project(db_session, name="  Acme  ", actor="telegram:1")
    assert project.name == "Acme"
    assert project.scope_definition == {}


async def test_create_project_rejects_blank_name(db_session):
    with pytest.raises(CommandError):
        await create_project(db_session, name="   ", actor="telegram:1")


async def test_list_projects_excludes_archived(db_session):
    db_session.add_all(
        [
            Project(name="Aktif", scope_definition={}),
            Project(name="Arşivlenmiş", scope_definition={}, is_archived=True),
        ]
    )
    await db_session.commit()

    projects = await list_projects(db_session)
    names = {p.name for p in projects}
    assert names == {"Aktif"}


async def test_find_project_by_id(db_session):
    project = Project(name="Acme", scope_definition={})
    db_session.add(project)
    await db_session.commit()

    found = await find_project(db_session, project.id)
    assert found is not None
    assert found.id == project.id


async def test_find_project_by_id_prefix(db_session):
    # Bot kullanıcıya her zaman 8 karakterlik kısaltılmış ID gösterir
    # (bkz. bot.py `p.id[:8]`) — bu önek tek başına tam ID'yi bulabilmeli.
    project = Project(name="Acme", scope_definition={})
    db_session.add(project)
    await db_session.commit()

    found = await find_project(db_session, project.id[:8])
    assert found is not None
    assert found.id == project.id


async def test_find_project_by_unique_partial_name(db_session):
    db_session.add(Project(name="Acme Lojistik", scope_definition={}))
    await db_session.commit()

    found = await find_project(db_session, "lojistik")
    assert found is not None
    assert found.name == "Acme Lojistik"


async def test_find_project_ambiguous_name_returns_none(db_session):
    db_session.add_all(
        [
            Project(name="Acme Lojistik", scope_definition={}),
            Project(name="Acme Finans", scope_definition={}),
        ]
    )
    await db_session.commit()

    found = await find_project(db_session, "acme")
    assert found is None


async def test_approve_task_updates_status_and_actor(db_session):
    project = Project(name="Acme", scope_definition={})
    db_session.add(project)
    await db_session.flush()
    asset = Asset(project_id=project.id, asset_type="domain", identifier="acme.example")
    db_session.add(asset)
    await db_session.flush()
    task = Task(
        project_id=project.id,
        title="Port taraması",
        agent_role="asset_discovery",
        status=TaskStatus.AWAITING_APPROVAL,
    )
    db_session.add(task)
    await db_session.commit()

    approved = await approve_task(db_session, task_id=task.id, actor="telegram:42")
    assert approved.status == TaskStatus.PENDING
    assert approved.approved_by == "telegram:42"


async def test_approve_task_by_id_prefix(db_session):
    # /gorevler'in gösterdiği kısaltılmış ID ile /onayla çalışabilmeli.
    project = Project(name="Acme", scope_definition={})
    db_session.add(project)
    await db_session.flush()
    task = Task(
        project_id=project.id,
        title="Port taraması",
        agent_role="asset_discovery",
        status=TaskStatus.AWAITING_APPROVAL,
    )
    db_session.add(task)
    await db_session.commit()

    approved = await approve_task(db_session, task_id=task.id[:8], actor="telegram:42")
    assert approved.id == task.id


async def test_approve_task_not_found(db_session):
    with pytest.raises(CommandError):
        await approve_task(db_session, task_id="does-not-exist", actor="telegram:1")


async def test_approve_task_wrong_status(db_session):
    project = Project(name="Acme", scope_definition={})
    db_session.add(project)
    await db_session.flush()
    task = Task(
        project_id=project.id,
        title="Zaten onaylı",
        agent_role="asset_discovery",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()

    with pytest.raises(CommandError):
        await approve_task(db_session, task_id=task.id, actor="telegram:1")


async def test_list_tasks_for_project(db_session):
    project = Project(name="Acme", scope_definition={})
    db_session.add(project)
    await db_session.flush()
    db_session.add(
        Task(project_id=project.id, title="T1", agent_role="x", status=TaskStatus.PENDING)
    )
    await db_session.commit()

    tasks = await list_tasks(db_session, project)
    assert len(tasks) == 1
    assert tasks[0].title == "T1"
