from .models import ChatMessage


def is_visit_card_save_request(message):
    normalized = str(message or "").replace(" ", "")
    return "저장" in normalized and (
        "카드" in normalized or "추천" in normalized
    )


def get_recent_user_requests(session, limit=8):
    recent_requests = []
    if session:
        messages = (
            session.messages.filter(role=ChatMessage.Role.USER)
            .only("content")
            .order_by("-created_at")
        )
        for chat_message in messages:
            content = chat_message.content.strip()
            if not content or is_visit_card_save_request(content):
                continue
            recent_requests.append(content)
            if len(recent_requests) == limit:
                break
    return list(reversed(recent_requests))
