import secrets
from medmij_oauth.client import DataStore
from .model import OAuthSession

class SQLAlchemyDataStore(DataStore):
    async def create_oauth_session(self, za_name, **kwargs):
        db_session = kwargs.get('db')

        oauth_session = OAuthSession(
            za_name=za_name,
            state=secrets.token_hex(16)
        )

        db_session.add(oauth_session)
        db_session.commit()

        return oauth_session

    async def get_oauth_session_by_id(self, oauth_session_id, **kwargs):
        db_session = kwargs.get('db')

        oauth_session = db_session.query(OAuthSession).filter(
            OAuthSession.id == oauth_session_id
        ).first()

        return oauth_session

    async def get_oauth_session_by_state(self, state, **kwargs):
        db_session = kwargs.get('db')

        oauth_session = db_session.query(OAuthSession).filter(
            OAuthSession.state == state
        ).first()

        return oauth_session

    def update_oauth_session(self, oauth_session, data, **kwargs):
        return super().update_oauth_session(oauth_session, data)

    async def save_oauth_session(self, oauth_session, **kwargs):
        db_session = kwargs.get('db')

        db_session.commit()

        return oauth_session
