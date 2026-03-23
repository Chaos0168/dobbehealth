"""
tools/booking.py

MCP Tools: book_appointment, cancel_appointment
Called by LLM after confirming availability.
Creates the appointment in PostgreSQL + triggers Google Calendar.
"""
import asyncpg
import os
import httpx
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/dobbeai")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")


def register(mcp: FastMCP):

    @mcp.tool()
    async def book_appointment(
        doctor_name: str,
        patient_user_id: str,
        date_str: str,
        time_str: str,
        reason: str = "General consultation",
    ) -> str:
        """
        Book an appointment for a patient with a doctor.

        Args:
            doctor_name: Doctor's name e.g. 'Dr. Ahuja'
            patient_user_id: UUID of the patient (from JWT token context)
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format e.g. '09:00' or '14:30'
            reason: Reason for visit e.g. 'fever', 'checkup'

        Returns:
            Confirmation message with appointment details.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            # Resolve doctor
            doctor = await conn.fetchrow("""
                SELECT d.id, u.name, u.email
                FROM doctors d JOIN users u ON d.user_id = u.id
                WHERE LOWER(u.name) LIKE LOWER($1)
                LIMIT 1
            """, f"%{doctor_name}%")

            if not doctor:
                return f"Doctor '{doctor_name}' not found."

            # Resolve patient
            patient = await conn.fetchrow(
                "SELECT id, name, email FROM users WHERE id = $1",
                patient_user_id
            )
            if not patient:
                return "Patient not found."

            # Parse date and time
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            # Get slot duration from availability config
            day_name = appt_date.strftime("%A").lower()
            slot_config = await conn.fetchrow("""
                SELECT slot_duration_minutes FROM availability_slots
                WHERE doctor_id = $1 AND day_of_week = $2
            """, doctor["id"], day_name)

            duration = slot_config["slot_duration_minutes"] if slot_config else 30
            end_dt = start_dt + timedelta(minutes=duration)

            # Check slot is still free (race condition protection)
            conflict = await conn.fetchrow("""
                SELECT id FROM appointments
                WHERE doctor_id = $1 AND appointment_date = $2
                  AND start_time = $3 AND status != 'cancelled'
            """, doctor["id"], appt_date, start_dt.time())

            if conflict:
                return f"Sorry, the {time_str} slot with Dr. {doctor['name']} on {date_str} was just taken. Please check availability again."

            # Create appointment
            appt_id = await conn.fetchval("""
                INSERT INTO appointments
                    (doctor_id, patient_id, appointment_date, start_time, end_time, reason, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'scheduled')
                RETURNING id
            """,
                doctor["id"], patient_user_id,
                appt_date, start_dt.time(), end_dt.time(),
                reason
            )

            # Trigger Google Calendar (non-blocking — we store event_id if it works)
            try:
                from services.gcalendar import create_calendar_event
                event_id = await create_calendar_event(
                    summary=f"Appointment: {patient['name']} with {doctor['name']}",
                    description=f"Reason: {reason}",
                    start=start_dt,
                    end=end_dt,
                    attendee_emails=[patient["email"], doctor["email"]],
                )
                await conn.execute(
                    "UPDATE appointments SET google_event_id = $1 WHERE id = $2",
                    event_id, appt_id
                )
            except Exception as e:
                # Calendar failure should not block the booking
                print(f"[Calendar] Non-fatal error: {e}")

            # Send confirmation email automatically (non-blocking)
            email_status = ""
            try:
                from mcp_server.tools.email_tool import _build_email_html
                html = _build_email_html(
                    patient_name=patient["name"],
                    doctor_name=doctor["name"],
                    appointment_date=appt_date.strftime("%A, %B %d, %Y"),
                    appointment_time=start_dt.strftime("%I:%M %p"),
                    reason=reason,
                )
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {RESEND_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": f"DOBBE Health <{FROM_EMAIL}>",
                            "to": [patient["email"]],
                            "subject": f"Appointment Confirmed - {doctor['name']} on {appt_date.strftime('%B %d, %Y')}",
                            "html": html,
                        },
                        timeout=15,
                    )
                if resp.status_code in (200, 201):
                    await conn.execute("UPDATE appointments SET email_sent = true WHERE id = $1", appt_id)
                    email_status = f"Confirmation email sent to {patient['email']}."
                else:
                    email_status = f"Email could not be sent (status {resp.status_code})."
                    print(f"[Email] Resend error: {resp.text}")
            except Exception as e:
                email_status = "Email could not be sent."
                print(f"[Email] Error: {e}")

            return (
                f"Appointment booked!\n"
                f"  Doctor: {doctor['name']}\n"
                f"  Patient: {patient['name']}\n"
                f"  Date: {appt_date.strftime('%A, %B %d, %Y')}\n"
                f"  Time: {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}\n"
                f"  Reason: {reason}\n"
                f"  Appointment ID: {appt_id}\n"
                f"  {email_status}"
            )
        finally:
            await conn.close()

    @mcp.tool()
    async def cancel_appointment(appointment_id: str) -> str:
        """
        Cancel an existing appointment by its ID.

        Args:
            appointment_id: UUID of the appointment to cancel
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            appt = await conn.fetchrow("""
                SELECT a.id, u.name as patient_name, d_user.name as doctor_name,
                       a.appointment_date, a.start_time, a.google_event_id
                FROM appointments a
                JOIN users u ON a.patient_id = u.id
                JOIN doctors d ON a.doctor_id = d.id
                JOIN users d_user ON d.user_id = d_user.id
                WHERE a.id = $1
            """, appointment_id)

            if not appt:
                return f"Appointment {appointment_id} not found."

            await conn.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = $1",
                appointment_id
            )

            # Cancel Google Calendar event if exists
            if appt["google_event_id"]:
                try:
                    from services.gcalendar import delete_calendar_event
                    await delete_calendar_event(appt["google_event_id"])
                except Exception as e:
                    print(f"[Calendar] Cancel error: {e}")

            return (
                f"❌ Appointment cancelled.\n"
                f"  {appt['patient_name']} with Dr. {appt['doctor_name']}\n"
                f"  {appt['appointment_date']} at {appt['start_time']}"
            )
        finally:
            await conn.close()
