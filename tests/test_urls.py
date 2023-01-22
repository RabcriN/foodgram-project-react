
URLS = ['/admin/', '/api/', '/api/users/']


class TestUrls:

    def test_urls(self, user_client):
        try:
            for url in URLS:
                response = user_client.get(url)
        except Exception as e:
            assert False, f'''Страница {url} работает неправильно. Ошибка: `{e}`'''
        if response.status_code in (301, 302):
            response = user_client.get(url)
        assert response.status_code != 404, f'Страница {url} не найдена, проверьте этот адрес в *urls.py*'

    def test_auth(self, client):
        response = client.get('/api/users/me/')
        assert response.status_code == 401, f'Проверьте права и авторизацию!'
