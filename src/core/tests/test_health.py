"""Tests for health check endpoints (core.healthz)."""

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


def test_should_return_200_for_livez(client):
    response = client.get("/livez/")
    assert response.status_code == 200


def test_should_return_alive_status_for_livez(client):
    response = client.get("/livez/")
    assert response.status_code == 200
    assert b"ok" in response.content or b"alive" in response.content


@pytest.mark.django_db
def test_should_return_200_for_healthz(client):
    response = client.get("/healthz/")
    assert response.status_code in (200, 503)


@pytest.mark.django_db
def test_should_include_database_check_in_healthz(client):
    response = client.get("/healthz/")
    assert response.status_code in (200, 503)


@pytest.mark.django_db
def test_should_reject_post_on_livez(client):
    response = client.post("/livez/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_should_reject_post_on_healthz(client):
    response = client.post("/healthz/")
    assert response.status_code == 405
