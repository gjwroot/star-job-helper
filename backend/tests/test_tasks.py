"""
任务模块单元测试。

测试任务模板获取、创建、用户任务创建和步骤完成等功能。
"""

import json
import pytest


class TestTaskTemplates:
    """任务模板测试"""

    def test_get_templates(self, client, auth_headers, test_template):
        """测试获取任务模板列表"""
        response = client.get("/api/tasks/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        # 验证模板结构
        template = data["data"][0]
        assert "id" in template
        assert "name" in template
        assert "steps" in template
        assert isinstance(template["steps"], list)

    def test_get_templates_requires_auth(self, client):
        """测试获取模板需要认证"""
        response = client.get("/api/tasks/templates")
        assert response.status_code == 403

    def test_create_template_as_counselor(self, client, counselor_headers):
        """测试辅导员创建模板"""
        response = client.post("/api/tasks/templates", headers=counselor_headers, json={
            "name": "新模板",
            "steps": ["步骤A", "步骤B"],
            "icon": "star",
            "is_public": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "新模板"
        assert data["data"]["steps"] == ["步骤A", "步骤B"]

    def test_create_template_as_user_forbidden(self, client, auth_headers):
        """测试普通用户不能创建模板"""
        response = client.post("/api/tasks/templates", headers=auth_headers, json={
            "name": "新模板",
            "steps": ["步骤A"],
        })
        assert response.status_code == 403

    def test_create_template_empty_steps(self, client, counselor_headers):
        """测试创建模板步骤不能为空"""
        response = client.post("/api/tasks/templates", headers=counselor_headers, json={
            "name": "空模板",
            "steps": [],
        })
        assert response.status_code == 422


class TestUserTasks:
    """用户任务测试"""

    def test_create_user_task(self, client, auth_headers, test_template):
        """测试创建用户任务"""
        response = client.post("/api/tasks/my", headers=auth_headers, json={
            "template_id": test_template.id,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["template_id"] == test_template.id
        assert data["data"]["status"] == "in_progress"
        assert data["data"]["completed_steps"] == []

    def test_create_user_task_invalid_template(self, client, auth_headers):
        """测试使用不存在的模板创建任务"""
        response = client.post("/api/tasks/my", headers=auth_headers, json={
            "template_id": 99999,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_get_my_tasks_empty(self, client, auth_headers):
        """测试获取空任务列表"""
        response = client.get("/api/tasks/my", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] == []

    def test_get_my_tasks_with_tasks(self, client, auth_headers, test_template):
        """测试获取有任务时的列表"""
        # 先创建一个任务
        client.post("/api/tasks/my", headers=auth_headers, json={
            "template_id": test_template.id,
        })
        # 获取任务列表
        response = client.get("/api/tasks/my", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1


class TestToggleStep:
    """步骤完成/取消测试"""

    def _create_task(self, client, auth_headers, template_id):
        """辅助方法：创建用户任务"""
        response = client.post("/api/tasks/my", headers=auth_headers, json={
            "template_id": template_id,
        })
        return response.json()["data"]["id"]

    def test_toggle_step_complete(self, client, auth_headers, test_template):
        """测试完成步骤"""
        task_id = self._create_task(client, auth_headers, test_template.id)

        response = client.post(
            f"/api/tasks/{task_id}/step",
            headers=auth_headers,
            json={"step_index": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert 0 in data["data"]["completed_steps"]

    def test_toggle_step_uncomplete(self, client, auth_headers, test_template):
        """测试取消步骤"""
        task_id = self._create_task(client, auth_headers, test_template.id)

        # 先完成步骤
        client.post(f"/api/tasks/{task_id}/step", headers=auth_headers, json={"step_index": 0})
        # 再取消
        response = client.post(
            f"/api/tasks/{task_id}/step",
            headers=auth_headers,
            json={"step_index": 0},
        )
        data = response.json()
        assert data["code"] == 0
        assert 0 not in data["data"]["completed_steps"]

    def test_toggle_all_steps_completes_task(self, client, auth_headers, test_template):
        """测试完成所有步骤后任务自动完成"""
        task_id = self._create_task(client, auth_headers, test_template.id)

        # 完成所有 3 个步骤
        for i in range(3):
            response = client.post(
                f"/api/tasks/{task_id}/step",
                headers=auth_headers,
                json={"step_index": i},
            )

        # 最后一个步骤的响应应该显示任务已完成
        data = response.json()
        assert data["data"]["status"] == "completed"
        assert data["data"]["completed_at"] is not None

    def test_toggle_step_invalid_task(self, client, auth_headers):
        """测试操作不存在的任务"""
        response = client.post(
            "/api/tasks/99999/step",
            headers=auth_headers,
            json={"step_index": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_toggle_step_negative_index(self, client, auth_headers, test_template):
        """测试负数步骤索引"""
        task_id = self._create_task(client, auth_headers, test_template.id)

        response = client.post(
            f"/api/tasks/{task_id}/step",
            headers=auth_headers,
            json={"step_index": -1},
        )
        assert response.status_code == 422
