"""Simple Supabase Auth REST calls using the publishable key."""
import httpx
from fastapi import HTTPException, Request, Response
from .config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, COOKIE_SECURE, require

ACCESS = 'fc_access'
REFRESH = 'fc_refresh'


def supabase(path: str, *, payload=None, token: str = '') -> dict:
    """Call Supabase Auth. GET when payload is None, POST otherwise."""
    require('SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY')
    headers = {'apikey': SUPABASE_PUBLISHABLE_KEY}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        with httpx.Client(timeout=20) as client:
            if payload is None:
                result = client.get(f'{SUPABASE_URL}/auth/v1/{path}', headers=headers)
            else:
                result = client.post(
                    f'{SUPABASE_URL}/auth/v1/{path}', headers=headers, json=payload
                )
        body = result.json()
        if result.is_error:
            detail = (
                body.get('msg')
                or body.get('message')
                or body.get('error_description')
                or 'Authentication failed'
            )
            raise HTTPException(401 if result.status_code < 500 else 502, detail)
        return body
    except httpx.RequestError as error:
        raise HTTPException(502, 'Could not reach Supabase Auth') from error
    except ValueError as error:
        raise HTTPException(502, 'Invalid response from Supabase Auth') from error


def set_session(response: Response, session: dict) -> None:
    """Store tokens in HttpOnly cookies."""
    options = {'httponly': True, 'secure': COOKIE_SECURE, 'samesite': 'lax', 'path': '/'}
    response.set_cookie(
        ACCESS,
        session['access_token'],
        max_age=session.get('expires_in', 3600),
        **options,
    )
    response.set_cookie(
        REFRESH,
        session['refresh_token'],
        max_age=60 * 60 * 24 * 30,
        **options,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(ACCESS, path='/')
    response.delete_cookie(REFRESH, path='/')


def current_user(request: Request, response: Response) -> dict:
    """Verify the access token with Supabase; refresh it when expired."""
    access = request.cookies.get(ACCESS)
    refresh = request.cookies.get(REFRESH)
    if not access and not refresh:
        raise HTTPException(401, 'Please sign in')
    if access:
        try:
            return supabase('user', token=access)
        except HTTPException as error:
            if error.status_code != 401:
                raise
    if refresh:
        try:
            session = supabase(
                'token?grant_type=refresh_token',
                payload={'refresh_token': refresh},
            )
            user = supabase('user', token=session['access_token'])
            set_session(response, session)
            return user
        except (HTTPException, KeyError):
            pass
    clear_session(response)
    raise HTTPException(401, 'Session expired. Please sign in again')
