"""
认证模块单元测试。

测试用户注册、登录、Token 验证、CSRF Token 等功能。
"""

import pytest
from fastapi.testclient import TestClient


class TestRegister:
    """注册接口测试"""

    def test_register_success(self, client):
        """测试正常注册"""
        response = client.post("/api/auth/register", json={
            "phone": "13900139000",
            "name": "新用户",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "注册成功"
        assert data["data"]["phone"] == "13900139000"
        assert data["data"]["name"] == "新用户"
        assert "id" in data["data"]

    def test_register_duplicate_phone(self, client, test_user):
        """测试重复手机号注册"""
        response = client.post("/api/auth/register", json={
            "phone": "13800138000",  # test_user 的手机号
            "name": "另一个用户",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "已注册" in data["message"]

    def test_register_invalid_phone_short(self, client):
        """测试手机号过短"""
        response = client.post("/api/auth/register", json={
            "phone": "1380013800",  # 10 位
            "name": "测试",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_invalid_phone_long(self, client):
        """测试手机号过长"""
        response = client.post("/api/auth/register", json={
            "phone": "138001380001",  # 12 位
            "name": "测试",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_password_too_short(self, client):
        """测试密码过短"""
        response = client.post("/api/auth/register", json={
            "phone": "13900139000",
            "name": "测试",
            "password": "12345",  # 5 位
        })
        assert response.status_code == 422

    def test_register_empty_name(self, client):
        """测试空用户名"""
        response = client.post("/api/auth/register", json={
            "phone": "13900139000",
            "name": "",
            "password": "password123",
        })
        assert response.status_code == 422


class TestLogin:
    """登录接口测试"""

    def test_login_success(self, client, test_user):
        """测试正常登录"""
        response = client.post("/api/auth/login", json={
            "phone": "13800138000",
            "password": "test123456",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "登录成功"
        assert "token" in data["data"]
        assert data["data"]["token_type"] == "Bearer"
        assert data["data"]["user"]["phone"] == "13800138000"
        assert data["data"]["user"]["name"] == "测试用户"

    def test_login_wrong_password(self, client, test_user):
        """测试错误密码"""
        response = client.post("/api/auth/login", json={
            "phone": "13800138000",
            "password": "wrongpassword",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "错误" in data["message"]

    def test_login_nonexistent_phone(self, client):
        """测试不存在的手机号"""
        response = client.post("/api/auth/login", json={
            "phone": "19999999999",
            "password": "test123456",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_login_invalid_phone(self, client):
        """测试无效手机号格式"""
        response = client.post("/api/auth/login", json={
            "phone": "13800",
            "password": "test123456",
        })
        assert response.status_code == 422


class TestTokenValidation:
    """Token 验证测试"""

    def test_valid_token_access_protected(self, client, auth_headers):
        """测试有效 Token 访问受保护接口"""
        response = client.get("/api/stats/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_invalid_token(self, client):
        """测试无效 Token"""
        response = client.get("/api/stats/dashboard", headers={
            "Authorization": "Bearer invalid_token_here"
        })
        assert response.status_code == 401

    def test_missing_token(self, client):
        """测试缺少 Token"""
        response = client.get("/api/stats/dashboard")
        assert response.status_code == 403

    def test_expired_token(self, client):
        """测试过期 Token"""
        from datetime import timedelta
        from app.core.security import create_access_token

        # 创建一个已过期的 token
        expired_token = create_access_token(
            data={"sub": "1", "role": "user"},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get("/api/stats/dashboard", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert response.status_code == 401


class TestCSRFToken:
    """CSRF Token 测试"""

    def test_get_csrf_token(self, client):
        """测试获取 CSRF Token"""
        response = client.get("/api/auth/csrf-token")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "csrf_token" in data["data"]
        assert len(data["data"]["csrf_token"]) == 32

    def test_csrf_tokens_are_unique(self, client):
        """测试 CSRF Token 唯一性"""
        response1 = client.get("/api/auth/csrf-token")
        response2 = client.get("/api/auth/csrf-token")
        token1 = response1.json()["data"]["csrf_token"]
        token2 = response2.json()["data"]["csrf_token"]
        assert token1 != token2
