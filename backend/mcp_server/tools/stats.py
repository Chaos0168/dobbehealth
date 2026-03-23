"""
tools/stats.py

MCP Tools: get_appointment_stats, get_appointments_by_symptom
For the Doctor Dashboard — queries DB for summaries and reports.
"""
import asyncpg
import os
from datetime import datetime, date, timedelta
from mcp.server.fastmcp import FastMCP

DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/dobbeai")


def register(mcp: FastMCP):

    @mcp.tool()
    async def get_appointment_stats(
        doctor_user_id: str,
        period: str = "today",
    ) -> str:
        """
        Get appointment statistics for a doctor.

        Args:
            doctor_user_id: The user UUID of the doctor
            period: One of 'today', 'yesterday', 'tomorrow', 'this_week', or a date 'YYYY-MM-DD'

        Returns:
            Human-readable summary of appointment counts and details.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            # Resolve doctor_id from user_id
            doctor = await conn.fetchrow(
                "SELECT d.id, u.name FROM doctors d JOIN users u ON d.user_id = u.id WHERE u.id = $1",
                doctor_user_id
            )
            if not doctor:
                return "Doctor profile not found."

            today = date.today()

            if period == "today":
                start_date = end_date = today
                label = "today"
            elif period == "yesterday":
                start_date = end_date = today - timedelta(days=1)
                label = "yesterday"
            elif period == "tomorrow":
                start_date = end_date = today + timedelta(days=1)
                label = "tomorrow"
            elif period == "this_week":
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
                label = "this week"
            else:
                try:
                    start_date = end_date = datetime.strptime(period, "%Y-%m-%d").date()
                    label = period
                except ValueError:
                    return f"Invalid period '{period}'. Use: today, yesterday, tomorrow, this_week, or YYYY-MM-DD."

            rows = await conn.fetch("""
                SELECT
                    a.id,
                    u.name AS patient_name,
                    a.start_time,
                    a.end_time,
                    a.status,
                    a.reason,
                    a.appointment_date
                FROM appointments a
                JOIN users u ON a.patient_id = u.id
                WHERE a.doctor_id = $1
                  AND a.appointment_date BETWEEN $2 AND $3
                ORDER BY a.appointment_date, a.start_time
            """, doctor["id"], start_date, end_date)

            if not rows:
                return f"No appointments for Dr. {doctor['name']} {label}."

            total = len(rows)
            completed = sum(1 for r in rows if r["status"] == "completed")
            scheduled = sum(1 for r in rows if r["status"] == "scheduled")
            cancelled = sum(1 for r in rows if r["status"] == "cancelled")

            result = (
                f"Appointment Summary for {doctor['name']} - {label.capitalize()}\n"
                f"Total: {total} | Scheduled: {scheduled} | Completed: {completed} | Cancelled: {cancelled}\n\n"
                f"Details:\n"
            )

            for r in rows:
                result += (
                    f"  - {r['start_time'].strftime('%I:%M %p')} | "
                    f"{r['patient_name']} "
                    f"[{r['status']}]"
                    + (f" | {r['reason']}" if r['reason'] else "") + "\n"
                )

            return result
        finally:
            await conn.close()

    @mcp.tool()
    async def get_appointments_by_symptom(
        doctor_user_id: str,
        symptom: str,
        days_back: str = "30",
    ) -> str:
        """
        Find all appointments where patients had a specific symptom/reason.

        Args:
            doctor_user_id: The user UUID of the doctor
            symptom: Symptom to search for e.g. 'fever', 'cough', 'checkup'
            days_back: How many days back to look (default 30)

        Returns:
            List of matching appointments with patient names and dates.
        """
        conn = await asyncpg.connect(DB_URL.replace("+asyncpg", ""))
        try:
            doctor = await conn.fetchrow(
                "SELECT d.id, u.name FROM doctors d JOIN users u ON d.user_id = u.id WHERE u.id = $1",
                doctor_user_id
            )
            if not doctor:
                return "Doctor profile not found."

            since = date.today() - timedelta(days=int(days_back))
            rows = await conn.fetch("""
                SELECT u.name AS patient_name, a.appointment_date, a.start_time, a.status, a.reason
                FROM appointments a
                JOIN users u ON a.patient_id = u.id
                WHERE a.doctor_id = $1
                  AND a.appointment_date >= $2
                  AND LOWER(a.reason) LIKE LOWER($3)
                ORDER BY a.appointment_date DESC
            """, doctor["id"], since, f"%{symptom}%")

            if not rows:
                return f"No appointments with '{symptom}' found in the last {days_back} days."

            result = f"Appointments with symptom '{symptom}' (last {days_back} days):\n"
            for r in rows:
                result += (
                    f"  - {r['patient_name']} | "
                    f"{r['appointment_date'].strftime('%b %d')} "
                    f"at {r['start_time'].strftime('%I:%M %p')} "
                    f"[{r['status']}]\n"
                )
            result += f"\nTotal: {len(rows)} patient(s)"
            return result
        finally:
            await conn.close()
