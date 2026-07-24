import httpx

from app.config import settings


class ChatwootApiError(Exception):
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Chatwoot API error {status_code}: {payload}")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.chatwoot_base_url,
        headers={"api_access_token": settings.chatwoot_api_access_token},
        timeout=10,
    )


def _accounts_path(suffix: str) -> str:
    return f"/api/v1/accounts/{settings.chatwoot_account_id}{suffix}"


async def _request(method: str, path: str, **kwargs) -> dict:
    async with _client() as client:
        response = await client.request(method, path, **kwargs)
    if response.is_error:
        raise ChatwootApiError(response.status_code, response.json())
    return response.json()


async def find_or_create_contact(igsid: str, name: str | None) -> dict:
    """POST contacts — devuelve contact_id y source_id de la sesión.

    A diferencia de /conversations y /messages, Chatwoot envuelve la
    respuesta de /contacts en payload.contact."""
    response = await _request(
        "POST",
        _accounts_path("/contacts"),
        json={
            "inbox_id": settings.chatwoot_inbox_id_comentarios,
            "name": name or igsid,
            "identifier": igsid,
        },
    )
    return response["payload"]["contact"]


async def create_conversation(source_id: str, contact_id: int) -> dict:
    return await _request(
        "POST",
        _accounts_path("/conversations"),
        json={
            "source_id": source_id,
            "inbox_id": settings.chatwoot_inbox_id_comentarios,
            "contact_id": contact_id,
        },
    )


async def create_message(conversation_id: int, content: str, message_type: str = "incoming") -> dict:
    return await _request(
        "POST",
        _accounts_path(f"/conversations/{conversation_id}/messages"),
        json={"content": content, "message_type": message_type},
    )


async def create_private_note(conversation_id: int, content: str) -> dict:
    return await _request(
        "POST",
        _accounts_path(f"/conversations/{conversation_id}/messages"),
        json={"content": content, "message_type": "outgoing", "private": True},
    )


async def resolve_conversation(conversation_id: int) -> dict:
    return await _request(
        "POST",
        _accounts_path(f"/conversations/{conversation_id}/toggle_status"),
        json={"status": "resolved"},
    )
