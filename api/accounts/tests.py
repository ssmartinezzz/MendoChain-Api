from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class UserListPermissionsTests(APITestCase):
    url = '/auth/users'

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.admin = User.objects.create_user(username='admin@test.com', password='pass12345!', is_staff=True)

    def test_anonymous_cannot_list_users(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_list_users(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class UserDetailPermissionsTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.other = User.objects.create_user(username='other@test.com', password='pass12345!')
        self.admin = User.objects.create_user(username='admin@test.com', password='pass12345!', is_staff=True)
        self.url = f'/auth/users/{self.user.pk}'

    def test_anonymous_cannot_read_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_user_cannot_read_user(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_update_user(self):
        self.client.force_authenticate(self.other)
        response = self.client.patch(self.url, {'first_name': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.first_name, 'Hacked')

    def test_other_user_cannot_delete_user(self):
        self.client.force_authenticate(self.other)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_user_can_update_themself(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(self.url, {'first_name': 'Santi'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Santi')

    def test_admin_can_read_any_user(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
