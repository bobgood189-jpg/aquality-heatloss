"""Shared helpers for handlers."""
from ..config import OWNER_USERNAME, OWNER_ID
from .. import storage
from ..i18n import DEFAULT_LANG


async def get_lang(state, user_id=None):
    """Resolve the user's language: FSM cache → DB → default."""
    data = await state.get_data()
    if data.get("lang"):
        return data["lang"]
    if user_id is not None:
        lang = storage.get_user_lang(user_id)
        if lang:
            await state.update_data(lang=lang)
            return lang
    return DEFAULT_LANG


def is_owner(user):
    if user is None:
        return False
    if OWNER_ID and user.id == OWNER_ID:
        return True
    if OWNER_USERNAME and (user.username or "").lower() == OWNER_USERNAME.lower():
        return True
    return False
