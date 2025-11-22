from typing import Optional

from django.http import HttpRequest
import re
from django.utils.text import slugify
from .models import SystemLog
from django.contrib.auth.models import User


def log_event(
    event_type: str,
    message: str,
    user: Optional[User] = None,
    request: Optional[HttpRequest] = None,
) -> None:
    """
    Central helper to create SystemLog entries.

    - If request is provided, it will auto-fill IP + user_agent.
    - If user is None and request.user is authenticated, it uses request.user.
    """

    ip_address = None
    user_agent = ""

    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

        if user is None and hasattr(request, "user") and request.user.is_authenticated:
            user = request.user

    if user is not None and not user.is_authenticated:
        user = None

    SystemLog.objects.create(
        event_type=event_type,
        message=message,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )



def clean_slug(text):
    text = slugify(text)          # applo-hospital
    text = re.sub(r'[-_]+', '', text)   # remove hyphens/underscores → applohospital
    return text
