"""
tools/reschedule.py

MCP Tool: reschedule_appointment
BONUS FEATURE — LLM-powered auto-rescheduling.
When a slot is unavailable, the agent calls this to find the next best slot
and offer it to the patient automatically.
"""
import asyncpg
import os
from datetime import datetime, date, timedelta
from mcp.server.fastmcp import FastMCP

DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/dobbeai")


def register(mcp: FastMCP):

    @mcp.tool()
    async def find_next_available_slot(
        doctor_name: str,
        preferred_date_str: str,
        preferred_time_of_day: str = "any",
        days_to_search: str = "7",
    ) -> str:
        """
        Find the next available appointment slot for a doctor, starting from a preferred date.
        Use this for auto-rescheduling when a preferred slot is unavailable.

        Args:
            doctor_name: Doctor's name
            preferred_date_str: Starting date to search from (YYYY-MM-DD)
            preferred_time_of_day: 'morning' (before 12), 'afternoon' (12-5), or 'any'
            days_to_search: How many days ahead to look (default "7")

        Returns:
            The next available slot details, or a message if nothing found.
        """
        days_int = int(days_to_search)
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            doctor = await conn.fetchrow("""
                SELECT d.id, u.name FROM doctors d
                JOIN users u ON d.user_id = u.id
                WHERE LOWER(u.name) LIKE LOWER($1)
                LIMIT 1
            """, f"%{doctor_name}%")

            if not doctor:
                return f"Doctor '{doctor_name}' not found."

            start_date = datetime.strptime(preferred_date_str, "%Y-%m-%d").date()

            for day_offset in range(days_int):
                check_date = start_date + timedelta(days=day_offset)
                day_name = check_date.strftime("%A").lower()

                slot_config = await conn.fetchrow("""
                    SELECT start_time, end_time, slot_duration_minutes
                    FROM availability_slots
                    WHERE doctor_id = $1 AND day_of_week = $2
                """, doctor["id"], day_name)

                if not slot_config:
                    continue  # doctor doesn't work this day

                # Get booked slots
                booked = await conn.fetch("""
                    SELECT start_time FROM appointments
                    WHERE doctor_id = $1 AND appointment_date = $2
                      AND status != 'cancelled'
                """, doctor["id"], check_date)

                booked_times = {r["start_time"] for r in booked}

                duration = slot_config["slot_duration_minutes"]
                current = datetime.combine(check_date, slot_config["start_time"])
                end = datetime.combine(check_date, slot_config["end_time"])

                while current + timedelta(minutes=duration) <= end:
                    slot_time = current.time()
                    slot_hour = current.hour

                    # Filter by time of day preference
                    if preferred_time_of_day == "morning" and slot_hour >= 12:
                        current += timedelta(minutes=duration)
                        continue
                    if preferred_time_of_day == "afternoon" and (slot_hour < 12 or slot_hour >= 17):
                        current += timedelta(minutes=duration)
                        continue

                    if slot_time not in booked_times:
                        return (
                            f"🔄 Next available slot found!\n"
                            f"  Doctor: Dr. {doctor['name']}\n"
                            f"  Date: {check_date.strftime('%A, %B %d, %Y')}\n"
                            f"  Time: {current.strftime('%I:%M %p')}\n"
                            f"  Date (YYYY-MM-DD): {check_date.isoformat()}\n"
                            f"  Time (HH:MM): {current.strftime('%H:%M')}\n\n"
                            f"Would you like me to book this slot?"
                        )
                    current += timedelta(minutes=duration)

            return (
                f"No available slots found for Dr. {doctor['name']} "
                f"in the next {days_to_search} days starting {preferred_date_str}. "
                "Try a longer search window or a different doctor."
            )
        finally:
            await conn.close()

    @mcp.tool()
    async def reschedule_appointment(
        appointment_id: str,
        new_date_str: str,
        new_time_str: str,
    ) -> str:
        """
        Reschedule an existing appointment to a new date and time.

        Args:
            appointment_id: UUID of the existing appointment
            new_date_str: New date in YYYY-MM-DD format
            new_time_str: New time in HH:MM format

        Returns:
            Confirmation of the reschedule.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            appt = await conn.fetchrow("""
                SELECT a.*, d.id as doc_id, u.name as patient_name,
                       d_user.name as doctor_name
                FROM appointments a
                JOIN users u ON a.patient_id = u.id
                JOIN doctors d ON a.doctor_id = d.id
                JOIN users d_user ON d.user_id = d_user.id
                WHERE a.id = $1
            """, appointment_id)

            if not appt:
                return f"Appointment {appointment_id} not found."

            new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
            new_start = datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M")
            day_name = new_date.strftime("%A").lower()

            # Get slot duration
            slot_config = await conn.fetchrow("""
                SELECT slot_duration_minutes FROM availability_slots
                WHERE doctor_id = $1 AND day_of_week = $2
            """, appt["doc_id"], day_name)
            duration = slot_config["slot_duration_minutes"] if slot_config else 30

            new_end = new_start + timedelta(minutes=duration)

            # Check new slot is free
            conflict = await conn.fetchrow("""
                SELECT id FROM appointments
                WHERE doctor_id = $1 AND appointment_date = $2
                  AND start_time = $3 AND status != 'cancelled'
                  AND id != $4
            """, appt["doc_id"], new_date, new_start.time(), appointment_id)

            if conflict:
                return f"The {new_time_str} slot on {new_date_str} is already taken."

            await conn.execute("""
                UPDATE appointments
                SET appointment_date = $1, start_time = $2, end_time = $3, status = 'rescheduled'
                WHERE id = $4
            """, new_date, new_start.time(), new_end.time(), appointment_id)

            return (
                f"✅ Appointment rescheduled!\n"
                f"  Patient: {appt['patient_name']}\n"
                f"  Doctor: Dr. {appt['doctor_name']}\n"
                f"  New Date: {new_date.strftime('%A, %B %d, %Y')}\n"
                f"  New Time: {new_start.strftime('%I:%M %p')}"
            )
        finally:
            await conn.close()
