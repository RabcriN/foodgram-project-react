from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestUser(APITestCase):

    url = reverse('user-list')
    data = {
        'email': 'test@test.test',
        'username': 'Test',
        'first_name': 'Test',
        'last_name': 'Test',
        'password': 'TestPassword',
    }

    def test_create_user(self):
        """
        Ensure we can create a new User object.
        """
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'Test')

    def test_wrong_data_dont_create_user(self):
        """
        Ensure we can't create a new User object with wrong data.
        """
        data = self.data
        for key in data.keys():
            temp = data[key]
            data[key] = ''
            response = self.client.post(self.url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            data[key] = temp

    def test_create_users_with_same_emails(self):
        """
        Ensure we can't create users with same emails.
        """
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)

        new_data = {
            'email': 'test@test.test',
            'username': '1Test',
            'first_name': '1Test',
            'last_name': '1Test',
            'password': '1TestPassword',
        }
        response = self.client.post(self.url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

        new_data['email'] = 'another@email.ru'
        response = self.client.post(self.url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)

    def test_change_password(self):
        """
        Check possibility to change password
        """
        self.client.post(self.url, self.data, format='json')
        user = User.objects.get(username='Test')
        url = self.url + 'set_password/'
        wrong_data = {
            "new_password": "new_password",
            "current_password": "wrong_password"
        }
        response = self.client.post(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user)
        response = self.client.post(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        correct_data = {
            "new_password": "new_password",
            "current_password": "TestPassword"
        }
        response = self.client.post(url, correct_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
