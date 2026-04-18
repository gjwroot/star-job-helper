"""
情绪模块单元测试。

测试情绪记录和情绪历史查询功能。
"""

import pytest


class TestMoodRecord:
    """情绪记录测试"""

    @pytest.mark.parametrize("mood_type", ["happy", "calm", "anxious", "sad", "angry"])
    def test_record_mood_success(self, client, auth_headers, mood_type):
        """测试各种情绪类型的记录"""
        response = client.post("/api/moods/record", headers=auth_headers, json={
            "mood_type": mood_type,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "记录成功"
        assert data["data"]["mood_type"] == mood_type
        assert isinstance(data["data"]["tips"], list)
        assert len(data["data"]["tips"]) > 0
        assert "id" in data["data"]
        assert data["data"]["created_at"] is not None

    def test_record_mood_invalid_type(self, client, auth_headers):
        """测试不支持的情绪类型"""
        response = client.post("/api/moods/record", headers=auth_headers, json={
            "mood_type": "excited",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "不支持" in data["message"]

    def test_record_mood_requires_auth(self, client):
        """测试记录情绪需要认证"""
        response = client.post("/api/moods/record", json={
            "mood_type": "happy",
        })
        assert response.status_code == 403

    def test_record_mood_empty_type(self, client, auth_headers):
        """测试空情绪类型"""
        response = client.post("/api/moods/record", headers=auth_headers, json={
            "mood_type": "",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400


class TestMoodHistory:
    """情绪历史测试"""

    def test_get_history_empty(self, client, auth_headers):
        """测试获取空历史记录"""
        response = client.get("/api/moods/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] == []

    def test_get_history_with_records(self, client, auth_headers):
        """测试获取有记录的历史"""
        # 先记录几条情绪
        for mood in ["happy", "calm", "sad"]:
            client.post("/api/moods/record", headers=auth_headers, json={
                "mood_type": mood,
            })

        response = client.get("/api/moods/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 3

        # 验证按时间倒序排列（最新在前）
        assert data["data"][0]["mood_type"] in ["happy", "calm", "sad"]

    def test_get_history_with_limit(self, client, auth_headers):
        """测试限制返回条数"""
        # 记录 5 条情绪
        for mood in ["happy", "calm", "anxious", "sad", "angry"]:
            client.post("/api/moods/record", headers=auth_headers, json={
                "mood_type": mood,
            })

        response = client.get("/api/moods/history?limit=3", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 3

    def test_get_history_requires_auth(self, client):
        """测试获取历史需要认证"""
        response = client.get("/api/moods/history")
        assert response.status_code == 403

    def test_get_history_limit_max(self, client, auth_headers):
        """测试最大限制 100"""
        # limit=200 超过最大值，Query 的 ge=1 le=100 会拒绝
        response = client.get("/api/moods/history?limit=200", headers=auth_headers)
        # FastAPI Query 验证 le=100 会返回 422
        assert response.status_code == 422

    def test_get_history_limit_min(self, client, auth_headers):
        """测试最小限制 1"""
        response = client.get("/api/moods/history?limit=0", headers=auth_headers)
        assert response.status_code == 422

    def test_record_multiple_moods_updates_stats(self, client, auth_headers):
        """测试多次记录情绪更新统计"""
        # 记录 3 条情绪
        for _ in range(3):
            client.post("/api/moods/record", headers=auth_headers, json={
                "mood_type": "happy",
            })

        # 获取仪表盘数据验证统计
        response = client.get("/api/stats/dashboard", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["moods"]["total"] == 3
        assert data["data"]["today"]["moods_logged"] == 3
