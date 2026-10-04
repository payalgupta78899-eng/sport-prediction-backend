import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_register_success():
    response = client.post("/api/v1/auth/register", json={
        "username": "testuser1",
        "email"   : "test1@gmail.com",
        "password": "Test1234"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "testuser1"


def test_register_duplicate_username():
    client.post("/api/v1/auth/register", json={
        "username": "dupuser",
        "email"   : "dup1@gmail.com",
        "password": "Test1234"
    })
    response = client.post("/api/v1/auth/register", json={
        "username": "dupuser",
        "email"   : "dup2@gmail.com",
        "password": "Test1234"
    })
    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


def test_login_success():
    client.post("/api/v1/auth/register", json={
        "username": "loginuser",
        "email"   : "login@gmail.com",
        "password": "Test1234"
    })
    response = client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "Test1234"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password():
    response = client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "WrongPass1"
    })
    assert response.status_code == 401


def test_protected_route_without_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_protected_route_with_token():
    client.post("/api/v1/auth/register", json={
        "username": "meuser",
        "email"   : "me@gmail.com",
        "password": "Test1234"
    })
    login = client.post("/api/v1/auth/login", json={
        "username": "meuser",
        "password": "Test1234"
    })
    token    = login.json()["access_token"]
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "meuser"
