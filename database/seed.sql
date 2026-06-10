-- DOBBE AI Demo Seed Data
-- Password hash = bcrypt("password123")

INSERT INTO users (name, email, password_hash, role, phone) VALUES
  ('Yakshika Batra', 'yakshika@patient.com', '$2b$12$.lHjbJRjBUK7jM4xyJv3VuH1/oGbXuYK6feuRXESabH75afgqK7.6', 'patient', '+91-9999999999'),
  ('Dr. Ahuja', 'dr.ahuja@hospital.com', '$2b$12$.lHjbJRjBUK7jM4xyJv3VuH1/oGbXuYK6feuRXESabH75afgqK7.6', 'doctor', '+91-8888888888')
ON CONFLICT (email) DO NOTHING;

INSERT INTO doctors (user_id, specialization)
SELECT id, 'General Physician' FROM users WHERE email = 'dr.ahuja@hospital.com'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO availability_slots (doctor_id, day_of_week, start_time, end_time, slot_duration_minutes)
SELECT d.id, t.day, '09:00', '17:00', 30
FROM doctors d JOIN users u ON u.id = d.user_id
CROSS JOIN (VALUES ('monday'),('tuesday'),('wednesday'),('thursday'),('friday')) AS t(day)
WHERE u.email = 'dr.ahuja@hospital.com'
ON CONFLICT DO NOTHING;
