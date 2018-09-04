from pytest import (
    fixture,
    raises,
    mark
)
from medmij_oauth.server import (
    Server,
    validation,
    InMemoryDataStore
)

from medmij_oauth.exceptions import OAuthException

from .util import (
    ret_true,
    ret_false,
    create_get_test_ocl
)

from datetime import datetime

@fixture
def server(request):
    return Server(
        data_store=InMemoryDataStore(),
        get_ocl=create_get_test_ocl(),
        is_known_zg=ret_true,
        zg_resource_available=ret_true
    )


def get_oauth_session(server):
    state = 'abcdef12345'
    redirect_uri = 'https://oauthclient.local/oauth/cb'
    scope = 1
    client_id = 'oauthclient.local'
    response_type = 'code'

    valid_params = {
        'state': state,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'client_id': client_id,
        'response_type': response_type
    }

    return server.create_oauth_session(valid_params)


from medmij_oauth.server import (
    Server,
    InMemoryDataStore
)

def test_create_oauth_session_valid(server):
    state = 'abcdef12345'
    redirect_uri = 'https://oauthclient.local/oauth/cb'
    scope = 1
    client_id = 'oauthclient.local'
    response_type = 'code'

    valid_params = {
        'state': state,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'client_id': client_id,
        'response_type': response_type
    }

    oauth_session = server.create_oauth_session(valid_params)

    assert oauth_session.state == valid_params['state']
    assert oauth_session.redirect_uri == valid_params['redirect_uri']
    assert oauth_session.scope == valid_params['scope']
    assert oauth_session.client_id == valid_params['client_id']
    assert oauth_session.response_type == valid_params['response_type']

def test_create_oauth_session_invalid(server):
    state = 'abcdef12345'
    redirect_uri = 'https://oauthclient.local/oauth/cb'
    scope = 1
    client_id = 'oauthclient.local'
    response_type = 'code'

    invalid_params = {
        'state': state,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'client_id': 'unknown',
        'response_type': response_type
    }

    with raises(OAuthException) as ex_info:
        server.create_oauth_session(invalid_params)

    assert ex_info.value.error == 'invalid_client' \
        and ex_info.value.error_description == 'client unknown'

    invalid_params = {
        'state': state,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'client_id': client_id,
        'response_type': 'foo'
    }

    with raises(OAuthException) as ex_info:
        server.create_oauth_session(invalid_params)

    assert ex_info.value.error == 'unsupported_response_type' \
        and ex_info.value.error_description == 'Only "code" response_type supported'

def test_handle_auth_grant(server):
    oauth_session = get_oauth_session(server)
    oauth_session, redirect_url = server.handle_auth_grant(oauth_session.id, True)

    assert oauth_session.authorization_granted
    assert oauth_session.authorization_code
    assert oauth_session.authorization_code_expiration > datetime.now()
    assert redirect_url == f'{oauth_session.redirect_uri}?code={oauth_session.authorization_code}&state={oauth_session.state}&expires_in=900&token_type=bearer'

    oauth_session = get_oauth_session(server)

    with raises(OAuthException) as ex_info:
        server.handle_auth_grant(oauth_session.id, False)

    assert ex_info.value.error == 'access_denied'
    assert ex_info.value.error_description == 'Authorization denied'
    assert ex_info.value.redirect == True

    with raises(ValueError) as ex_info:
        server.handle_auth_grant('fake', True)

    assert str(ex_info.value) == 'Not a valid oauth_session_id'

def test_redeem_authorization_code_valid(server):
    oauth_session = get_oauth_session(server)

    oauth_session, _ = server.handle_auth_grant(oauth_session.id, True)

    request_params = {
        'code': oauth_session.authorization_code,
        'client_id': oauth_session.client_id,
        'redirect_uri': oauth_session.redirect_uri,
        'grant_type': 'authorization_code'
    }

    _ = server.redeem_authorization_code(request_params)

    oauth_session = server.data_store.get_oauth_session_by_id(oauth_session.id)

    assert oauth_session.authorization_code is None
    assert oauth_session.access_token
    assert oauth_session.access_token_expiration > datetime.now()

def test_redeem_authorization_code_invalid(server):
    oauth_session = get_oauth_session(server)

    oauth_session, _ = server.handle_auth_grant(oauth_session.id, True)

    request_params = {
        'code': oauth_session.authorization_code,
        'client_id': oauth_session.client_id,
        'redirect_uri': oauth_session.redirect_uri,
        'grant_type': 'authorization_code'
    }

    with raises(OAuthException) as ex_info:
        server.redeem_authorization_code({**request_params, **{'code': 'fake'}})

    assert ex_info.value.error == 'invalid_grant' \
        and ex_info.value.error_description == 'Invalid authorization token'

    with raises(OAuthException) as ex_info:
        server.redeem_authorization_code({**request_params, **{'client_id': ''}})

    assert ex_info.value.error == 'invalid_client' \
        and ex_info.value.error_description == 'client_id not associated with this authorization_token'

    with raises(OAuthException) as ex_info:
        server.redeem_authorization_code({**request_params, **{'redirect_uri': ''}})

    assert ex_info.value.error == 'invalid_request' \
        and ex_info.value.error_description == 'Invalid redirect_uri'

    with raises(OAuthException) as ex_info:
        server.redeem_authorization_code({**request_params, **{'grant_type': ''}})

    assert ex_info.value.error == 'unsupported_grant_type' \
        and ex_info.value.error_description == '"authorization_code" in only supported grant_type'

def test_redirect_url_validation():
    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri(None)

    assert ex_info.value.error_description == 'redirect_uri required'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('')

    assert ex_info.value.error_description == 'redirect_uri required'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('https://')

    assert ex_info.value.error_description == 'redirect_uri must be FQDN'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('http://example.com/auth?destination=account')

    assert ex_info.value.error_description == 'redirect_uri schema must be https'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('https://example.com/auth?destination=account')

    assert ex_info.value.error_description == 'redirect_uri can\'t contain query parameters'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('https://example.com/auth?#test')

    assert ex_info.value.error_description == 'redirect_uri can\'t contain fragment'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('https://example.com/auth', 'test.com')

    assert ex_info.value.error_description == 'redirect_uri must be in client domain'

    with raises(OAuthException) as ex_info:
        validation.validate_redirect_uri('https://example.com/auth', '')

    assert ex_info.value.error_description == 'redirect_uri must be in client domain'

    validation.validate_redirect_uri('https://localhost', 'localhost')
    validation.validate_redirect_uri('https://example.com/auth', 'example.com')