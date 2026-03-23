"""
services/calendar.py — Google Calendar API integration
Creates/deletes calendar events when appointments are booked/cancelled.
"""
import os
import json
from datetime import datetime
from typing import Optional

_BASE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", os.path.join(_BASE, "google_credentials.json"))
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", os.path.join(_BASE, "google_token.json"))


def _get_service():
    """Get an authenticated Google Calendar service object"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError(
                "Google Calendar token not found. "
                "Run: cd backend && python services/auth_calendar.py"
            )

    return build("calendar", "v3", credentials=creds)


async def create_calendar_event(
    summary: str,
    description: str,
    start: datetime,
    end: datetime,
    attendee_emails: list[str],
    calendar_id: str = "primary",
) -> Optional[str]:
    """
    Create a Google Calendar event and return the event ID.
    Run in a thread pool executor since the Google client is synchronous.
    """
    import asyncio

    def _create():
        service = _get_service()
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "attendees": [{"email": e} for e in attendee_emails],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }
        result = service.events().insert(calendarId=calendar_id, body=event, sendUpdates="all").execute()
        return result.get("id")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _create)


async def delete_calendar_event(event_id: str, calendar_id: str = "primary") -> None:
    """Delete (cancel) a Google Calendar event"""
    import asyncio

    def _delete():
        service = _get_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _delete)
