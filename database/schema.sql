-- ============================================================
-- DOBBE AI — Doctor Appointment Assistant
-- Database Schema
-- ============================================================

-- Enable UUID generation (Postgres extension)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ─────────────────────────────────────────────────────────────
-- TABLE: users
-- Stores both patients AND doctors (role field distinguishes them)
-- This is the base auth table for JWT login (Bonus feature)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,                  -- bcrypt hash, never plain text
    role          VARCHAR(10) NOT NULL CHECK (role IN ('patient', 'doctor')),
    phone         VARCHAR(20),
    created_at    TIMESTAMP DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────
-- TABLE: doctors
-- Extended info for users who are doctors
-- Links to the users table via user_id (one-to-one)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS doctors (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id        UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    specialization VARCHAR(100) NOT NULL,         -- e.g. "Cardiologist", "General"
    calendar_id    TEXT,                          -- Google Calendar ID for this doctor
    slack_user_id  TEXT                           -- Slack user ID for notifications
);


-- ─────────────────────────────────────────────────────────────
-- TABLE: availability_slots
-- Defines WHEN a doctor is available (their weekly schedule)
-- e.g. Dr. Ahuja is free every Monday 9AM–5PM
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS availability_slots (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id   UUID REFERENCES doctors(id) ON DELETE CASCADE,
    day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN
                    ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')),
    start_time  TIME NOT NULL,                    -- e.g. 09:00
    end_time    TIME NOT NULL,                    -- e.g. 17:00
    slot_duration_minutes INT DEFAULT 30          -- each appointment = 30 mins
);


-- ─────────────────────────────────────────────────────────────
-- TABLE: appointments
-- The core table — every booked appointment lives here
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id           UUID REFERENCES doctors(id) ON DELETE CASCADE,
    patient_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    appointment_date    DATE NOT NULL,
    start_time          TIME NOT NULL,
    end_time            TIME NOT NULL,
    status              VARCHAR(20) DEFAULT 'scheduled'
                            CHECK (status IN ('scheduled','completed','cancelled','rescheduled')),
    reason              TEXT,                     -- "fever", "checkup", "follow-up" etc.
    notes               TEXT,                     -- doctor's notes post-visit
    google_event_id     TEXT,                     -- Google Calendar event ID (for updates/deletes)
    email_sent          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────
-- TABLE: prompt_history
-- Stores every conversation turn (Bonus: prompt history tracking)
-- session_id groups all turns of a single conversation together
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prompt_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  TEXT NOT NULL,                    -- groups multi-turn conversations
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,                    -- the actual message text
    created_at  TIMESTAMP DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────
-- INDEXES — make common queries fast
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date
    ON appointments(doctor_id, appointment_date);

CREATE INDEX IF NOT EXISTS idx_appointments_patient
    ON appointments(patient_id);

CREATE INDEX IF NOT EXISTS idx_prompt_history_session
    ON prompt_history(session_id);

CREATE INDEX IF NOT EXISTS idx_availability_doctor
    ON availability_slots(doctor_id);
