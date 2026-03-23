"""
tools/availability.py

MCP Tool: check_availability
Queries PostgreSQL for open time slots for a given doctor on a given date.
The LLM calls this when the user asks "Is Dr. Ahuja free tomorrow?"
"""
import asyncpg
import os
from datetime import datetime, date, time, timedelta
from mcp.server.fastmcp import FastMCP

# Direct asyncpg connection (MCP server is its own process, no shared SQLAlchemy)
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/dobbeai")


async def _get_conn():
    # asyncpg uses postgres:// not postgresql+asyncpg://
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "")
    # parse user:pass@host:port/db
    return await asyncpg.connect(f"postgresql://{url}" if not url.startswith("postgres") else DB_URL.replace("+asyncpg", ""))


def register(mcp: FastMCP):

    @mcp.tool()
    async def list_doctors() -> str:
        """
        Returns a list of all available doctors with their specializations.
        Call this when the user hasn't specified a doctor yet.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            rows = await conn.fetch("""
                SELECT u.name, d.specialization
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                ORDER BY u.name
            """)
            if not rows:
                return "No doctors available."
            result = "Available doctors:\n"
            for r in rows:
                result += f"  • {r['name']} ({r['specialization']})\n"
            return result
        finally:
            await conn.close()

    @mcp.tool()
    async def check_availability(doctor_name: str, date_str: str) -> str:
        """
        Check available appointment slots for a doctor on a specific date.

        Args:
            doctor_name: Doctor's name e.g. 'Dr. Ahuja' or 'Ahuja'
            date_str: Date in YYYY-MM-DD format e.g. '2026-03-21'

        Returns:
            List of available time slots, or a message if none available.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            # Resolve doctor by name (partial match)
            doctor = await conn.fetchrow("""
                SELECT d.id, u.name, d.specialization
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                WHERE LOWER(u.name) LIKE LOWER($1)
                LIMIT 1
            """, f"%{doctor_name}%")

            if not doctor:
                return f"No doctor found matching '{doctor_name}'. Try list_doctors to see who's available."

            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_name = appt_date.strftime("%A").lower()

            # Get doctor's working hours for that day
            slot_config = await conn.fetchrow("""
                SELECT start_time, end_time, slot_duration_minutes
                FROM availability_slots
                WHERE doctor_id = $1 AND day_of_week = $2
            """, doctor["id"], day_name)

            if not slot_config:
                return f"Dr. {doctor['name']} does not work on {appt_date.strftime('%A')}s."

            # Get already booked slots for that day
            booked = await conn.fetch("""
                SELECT start_time FROM appointments
                WHERE doctor_id = $1
                  AND appointment_date = $2
                  AND status NOT IN ('cancelled')
            """, doctor["id"], appt_date)

            booked_times = {r["start_time"] for r in booked}

            # Generate all possible slots
            duration = slot_config["slot_duration_minutes"]
            current = datetime.combine(appt_date, slot_config["start_time"])
            end = datetime.combine(appt_date, slot_config["end_time"])
            available = []

            while current + timedelta(minutes=duration) <= end:
                if current.time() not in booked_times:
                    available.append(current.strftime("%I:%M %p"))
                current += timedelta(minutes=duration)

            if not available:
                return f"No available slots for Dr. {doctor['name']} on {date_str}. All slots are booked."

            return (
                f"Available slots for Dr. {doctor['name']} ({doctor['specialization']}) "
                f"on {appt_date.strftime('%A, %B %d, %Y')}:\n"
                + "\n".join(f"  • {s}" for s in available)
            )
        finally:
            await conn.close()

    @mcp.tool()
    async def get_patient_appointments(patient_user_id: str) -> str:
        """
        Get all upcoming and recent appointments for a patient.

        Args:
            patient_user_id: The UUID of the patient (available in context)

        Returns:
            List of the patient's appointments with doctor, date, time and status.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            rows = await conn.fetch("""
                SELECT a.id, a.appointment_date, a.start_time, a.status, a.reason,
                       u.name AS doctor_name, d.specialization
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                JOIN users u ON d.user_id = u.id
                WHERE a.patient_id = (
                    SELECT id FROM users WHERE id::text = $1
                )
                ORDER BY a.appointment_date DESC, a.start_time DESC
                LIMIT 10
            """, patient_user_id)

            if not rows:
                return "You have no appointments on record."

            result = "Your appointments:\n"
            for r in rows:
                dt = r['appointment_date'].strftime('%A, %B %d, %Y')
                tm = r['start_time'].strftime('%I:%M %p') if r['start_time'] else ''
                result += f"  • [ID: {r['id']}] {dt} at {tm} — {r['doctor_name']} ({r['specialization']}) — {r['status'].upper()} — Reason: {r['reason']}\n"
            return result
        finally:
            await conn.close()
