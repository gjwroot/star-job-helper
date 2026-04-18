"""
测试配置和公共 fixtures。

使用临时文件 SQLite 数据库，每个测试函数使用独立的数据库。
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.core.security import hash_password, create_access_token


def _create_test_engine():
    """创建独立的测试数据库引擎"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine, db_path


def override_get_db_factory(SessionLocal):
    """创建数据库会话依赖覆盖工厂"""
    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    return _override


@pytest.fixture(scope="function")
def client():
    """获取测试客户端，每个测试函数使用独立的临时数据库"""
    import app.database as db_module

    # 创建独立的测试数据库
    test_engine, db_path = _create_test_engine()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # 创建所有表
    Base.metadata.create_all(bind=test_engine)

    # 替换生产引擎
    original_engine = db_module.engine
    db_module.engine = test_engine

    from main import app
    app.dependency_overrides[get_db] = override_get_db_factory(TestSessionLocal)

    # 提供 db_session 给其他 fixture 使用
    db = TestSessionLocal()

    with TestClient(app) as c:
        # 将 db_session 附加到 client 对象上，供其他 fixture 使用
        c.db_session = db
        yield c

    app.dependency_overrides.clear()
    db_module.engine = original_engine
    db.close()

    # 清理临时数据库文件
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def db_session(client):
    """获取测试数据库会话（与 client 共享同一个数据库）"""
    return client.db_session


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    from app.models.user import User

    user = User(
        phone="13800138000",
        name="测试用户",
        hashed_password=hash_password("test123456"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_counselor(db_session):
    """创建测试辅导员"""
    from app.models.user import User

    user = User(
        phone="13800138001",
        name="测试辅导员",
        hashed_password=hash_password("test123456"),
        role="counselor",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """获取认证请求头"""
    token = create_access_token(data={"sub": str(test_user.id), "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def counselor_headers(test_counselor):
    """获取辅导员认证请求头"""
    token = create_access_token(data={"sub": str(test_counselor.id), "role": test_counselor.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_template(db_session, test_counselor):
    """创建测试任务模板"""
    import json
    from app.models.task import TaskTemplate

    template = TaskTemplate(
        name="测试模板",
        icon="clipboard",
        steps=json.dumps(["步骤一", "步骤二", "步骤三"], ensure_ascii=False),
        created_by=test_counselor.id,
        is_public=True,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template
