"""
tools/email_tool.py

MCP Tool: send_confirmation_email
Sends a beautiful HTML confirmation email to the patient via Resend.
Called by LLM after a successful booking.
"""
import os
from mcp.server.fastmcp import FastMCP

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "appointments@dobbeai.com")


def register(mcp: FastMCP):

    @mcp.tool()
    async def send_confirmation_email(
        patient_name: str,
        patient_email: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        reason: str = "General consultation",
    ) -> str:
        """
        Send a beautiful HTML confirmation email to the patient.

        Args:
            patient_name: Patient's full name
            patient_email: Patient's email address
            doctor_name: Doctor's full name
            appointment_date: Human-readable date e.g. 'Friday, March 21, 2026'
            appointment_time: Time e.g. '09:00 AM'
            reason: Reason for the visit

        Returns:
            Success or failure message.
        """
        import httpx

        html = _build_email_html(
            patient_name=patient_name,
            doctor_name=doctor_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"DOBBE Health <{FROM_EMAIL}>",
                        "to": [patient_email],
                        "subject": f"Appointment Confirmed - {doctor_name} on {appointment_date}",
                        "html": html,
                    },
                    timeout=15,
                )
            print(f"[Email] Resend status={resp.status_code} body={resp.text}")
            if resp.status_code in (200, 201):
                return f"✅ Confirmation email sent to {patient_email}"
            else:
                return f"⚠️ Email send failed (status {resp.status_code}): {resp.text}"
        except Exception as e:
            return f"⚠️ Email error: {str(e)}"


def _build_email_html(
    patient_name: str,
    doctor_name: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
) -> str:
    """
    Beautiful responsive HTML email template.
    Clean, professional, mobile-friendly.
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Appointment Confirmation</title>
</head>
<body style="margin:0;padding:0;background:#f4f7fb;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:40px 0;">
    <tr><td align="center">

      <!-- Card -->
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:600px;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%);
                     padding:40px 48px;text-align:center;">
            <p style="margin:0 0 8px;font-size:28px;">🏥</p>
            <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;
                       letter-spacing:-0.5px;">DOBBE Health</h1>
            <p style="margin:8px 0 0;color:#bfdbfe;font-size:14px;">
              Your appointment is confirmed
            </p>
          </td>
        </tr>

        <!-- Green success banner -->
        <tr>
          <td style="background:#dcfce7;padding:16px 48px;text-align:center;
                     border-bottom:1px solid #bbf7d0;">
            <p style="margin:0;color:#166534;font-size:15px;font-weight:600;">
              ✅ Booking Confirmed!
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px 48px;">

            <p style="margin:0 0 24px;color:#374151;font-size:16px;line-height:1.6;">
              Hi <strong>{patient_name}</strong>,<br/>
              Your appointment has been successfully scheduled. Here are your details:
            </p>

            <!-- Details card -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;
                          overflow:hidden;margin-bottom:32px;">
              <tr>
                <td style="padding:24px 28px;">
                  {_detail_row("👨‍⚕️", "Doctor", doctor_name)}
                  {_detail_row("📅", "Date", appointment_date)}
                  {_detail_row("⏰", "Time", appointment_time)}
                  {_detail_row("📋", "Reason", reason)}
                </td>
              </tr>
            </table>

            <!-- What to bring -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fefce8;border-radius:12px;border:1px solid #fef08a;
                          margin-bottom:32px;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 10px;color:#854d0e;font-weight:600;font-size:14px;">
                    📌 What to bring
                  </p>
                  <ul style="margin:0;padding-left:18px;color:#713f12;font-size:14px;line-height:2;">
                    <li>Government-issued ID</li>
                    <li>Previous medical records (if any)</li>
                    <li>Insurance card (if applicable)</li>
                    <li>Arrive 10 minutes early</li>
                  </ul>
                </td>
              </tr>
            </table>

            <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.6;">
              Need to cancel or reschedule? Simply reply to this email or
              log in to your DOBBE Health account.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e5e7eb;
                     padding:24px 48px;text-align:center;">
            <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;">
              This is an automated confirmation from <strong>DOBBE Health AI</strong>.<br/>
              © 2026 DOBBE Health. All rights reserved.
            </p>
          </td>
        </tr>

      </table>
      <!-- /Card -->

    </td></tr>
  </table>

</body>
</html>
"""


def _detail_row(icon: str, label: str, value: str) -> str:
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
      <tr>
        <td width="32" style="vertical-align:top;padding-top:2px;font-size:18px;">{icon}</td>
        <td>
          <p style="margin:0;color:#6b7280;font-size:12px;text-transform:uppercase;
                    letter-spacing:0.05em;font-weight:600;">{label}</p>
          <p style="margin:2px 0 0;color:#111827;font-size:15px;font-weight:600;">{value}</p>
        </td>
      </tr>
    </table>
    """
