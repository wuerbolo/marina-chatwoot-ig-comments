import httpx

from app.config import settings

GRAPH_BASE_URL = "https://graph.instagram.com"


class MetaApiError(Exception):
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Meta API error {status_code}: {payload}")


def _base_url() -> str:
    return f"{GRAPH_BASE_URL}/{settings.meta_graph_api_version}"


async def get_media(media_id: str) -> dict:
    """GET /{media-id}?fields=permalink,media_url,caption,media_type"""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{_base_url()}/{media_id}",
            params={
                "fields": "permalink,media_url,caption,media_type",
                "access_token": settings.ig_long_lived_access_token,
            },
        )
    if response.is_error:
        raise MetaApiError(response.status_code, response.json())
    return response.json()


async def send_private_reply(comment_id: str, message: str) -> dict:
    """POST /{comment-id}/private_replies"""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{_base_url()}/{comment_id}/private_replies",
            params={"access_token": settings.ig_long_lived_access_token},
            json={"message": message},
        )
    if response.is_error:
        raise MetaApiError(response.status_code, response.json())
    return response.json()
