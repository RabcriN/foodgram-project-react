import pytest
from users.models import User


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username='TestUser', password='1234567'
    )


@pytest.fixture
def user_client(user, client):
    client.force_login(user)
    return client


@pytest.fixture
def not_auth_user(user, client):
    return User.objects.create_user(
        username='Not_Auth', email='notauth@test.com', password='1234567',
        role='GUEST',
    )
