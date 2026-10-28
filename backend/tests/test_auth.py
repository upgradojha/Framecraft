"""Auth tests prove cookies are secure and tokens are verified/refreshed."""

# Tests stub Supabase's remote Auth endpoints; live credentials are not needed.
from fastapi.testclient import TestClient
from app import main, auth


def test_login_cookie_me_refresh_logout(monkeypatch):
    # Fake one verified Supabase account and token exchange.
    user = {'id': '11111111-1111-1111-1111-111111111111', 'email': 'student@example.com'}
    calls = []

    def fake_auth(path, *, payload=None, token=''):
        calls.append((path, token))
        if path == 'token?grant_type=password':
            return {'user': user, 'access_token': 'access-123', 'refresh_token': 'refresh-123', 'expires_in': 3600}
        if path == 'user':
            if token == 'access-123': return user
            if token == 'access-456': return user
            raise auth.HTTPException(401, 'Expired')
        if path == 'token?grant_type=refresh_token':
            assert payload == {'refresh_token': 'refresh-123'}
            return {'access_token': 'access-456', 'refresh_token': 'refresh-456', 'expires_in': 3600}
        raise AssertionError(f'Unexpected endpoint: {path}')

    monkeypatch.setattr(auth, 'supabase', fake_auth)
    monkeypatch.setattr(main, 'supabase', fake_auth)
    with TestClient(main.app) as client:
        # An anonymous user is never accepted.
        assert client.get('/api/auth/me').status_code == 401
        signed_in = client.post('/api/auth/login', json={'email': user['email'], 'password': 'securepassword'})
        assert signed_in.status_code == 200
        # Cookie is HttpOnly so frontend JavaScript cannot read it.
        cookies = signed_in.headers.get_list('set-cookie')
        assert len(cookies) == 2 and all('httponly' in value.lower() for value in cookies)
        assert client.get('/api/auth/me').json()['user']['id'] == user['id']
        # Simulate an expired access cookie; refresh cookie must recover it.
        client.cookies.set('fc_access', 'expired')
        refreshed = client.get('/api/auth/me')
        assert refreshed.status_code == 200
        assert 'access-456' in refreshed.headers['set-cookie']
        # Logout must clear both cookies.
        assert client.post('/api/auth/logout').status_code == 200
        assert client.get('/api/auth/me').status_code == 401


def test_signup_with_confirmation_off(monkeypatch):
    user = {'id': '11111111-1111-1111-1111-111111111111', 'email': 'new@example.com'}

    def fake_auth(path, *, payload=None, token=''):
        assert path == 'signup' and payload['email'] == user['email']
        return {'user': user, 'access_token': 'access', 'refresh_token': 'refresh', 'expires_in': 3600}

    monkeypatch.setattr(main, 'supabase', fake_auth)
    with TestClient(main.app) as client:
        response = client.post('/api/auth/signup', json={'email': user['email'], 'password': 'password123'})
        assert response.status_code == 200
        assert not response.json()['needs_confirmation']
        assert 'fc_access' in response.cookies
