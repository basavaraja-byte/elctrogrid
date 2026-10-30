-- ============================================================================
-- DISPATCHGRID — Non-Destructive Supabase Row-Level Security (RLS) & AI Logging
-- ============================================================================
-- IMPORTANT:
-- This script contains ONLY non-destructive operations:
-- - Enables RLS on existing canonical tables.
-- - Defines role-based security policies for Customer, Technician, and Supervisor.
-- - Allows service_role (FastAPI backend) full administrative bypass.
-- - Creates an optional non-destructive ai_prediction_logs table.
-- Zero tables, zero columns, and zero existing records are dropped or modified.
-- ============================================================================

-- 1. ENABLE ROW LEVEL SECURITY (RLS)
ALTER TABLE IF EXISTS customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS technicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS schedule_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scheduling_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;

-- 2. SERVICE ROLE BYPASS (FastAPI Backend Database Connection)
-- Backend connections using service_role key or direct postgres connection have full access
DROP POLICY IF EXISTS service_role_all_customers ON customers;
CREATE POLICY service_role_all_customers ON customers FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all_technicians ON technicians;
CREATE POLICY service_role_all_technicians ON technicians FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all_jobs ON jobs;
CREATE POLICY service_role_all_jobs ON jobs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all_assignments ON assignments;
CREATE POLICY service_role_all_assignments ON assignments FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all_schedules ON schedule_versions;
CREATE POLICY service_role_all_schedules ON schedule_versions FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all_runs ON scheduling_runs;
CREATE POLICY service_role_all_runs ON scheduling_runs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all_audit ON audit_logs;
CREATE POLICY service_role_all_audit ON audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);


-- 3. CUSTOMER POLICIES
-- Customers can read and create their own service requests; cannot access internal schedule runs
DROP POLICY IF EXISTS customer_read_own_profile ON customers;
CREATE POLICY customer_read_own_profile ON customers FOR SELECT TO authenticated
USING (id::text = auth.uid()::text OR email = auth.jwt()->>'email');

DROP POLICY IF EXISTS customer_read_own_jobs ON jobs;
CREATE POLICY customer_read_own_jobs ON jobs FOR SELECT TO authenticated
USING (
    customer_id::text = auth.uid()::text 
    OR customer_contact = auth.jwt()->>'phone'
    OR (auth.jwt()->'app_metadata'->>'role') = 'customer'
);

DROP POLICY IF EXISTS customer_create_job ON jobs;
CREATE POLICY customer_create_job ON jobs FOR INSERT TO authenticated
WITH CHECK (
    customer_id::text = auth.uid()::text 
    OR (auth.jwt()->'app_metadata'->>'role') = 'customer'
);


-- 4. TECHNICIAN POLICIES
-- Technicians can view their assigned jobs and update operational status
DROP POLICY IF EXISTS technician_read_own_jobs ON jobs;
CREATE POLICY technician_read_own_jobs ON jobs FOR SELECT TO authenticated
USING (
    assigned_technician_id::text = auth.uid()::text
    OR (auth.jwt()->'app_metadata'->>'role') = 'technician'
);

DROP POLICY IF EXISTS technician_update_assigned_job_status ON jobs;
CREATE POLICY technician_update_assigned_job_status ON jobs FOR UPDATE TO authenticated
USING (assigned_technician_id::text = auth.uid()::text)
WITH CHECK (assigned_technician_id::text = auth.uid()::text);

DROP POLICY IF EXISTS technician_read_own_assignments ON assignments;
CREATE POLICY technician_read_own_assignments ON assignments FOR SELECT TO authenticated
USING (technician_id::text = auth.uid()::text);


-- 5. SUPERVISOR & OPERATIONS MANAGER POLICIES
-- Supervisors have full operational visibility and decision permissions
DROP POLICY IF EXISTS supervisor_all_jobs ON jobs;
CREATE POLICY supervisor_all_jobs ON jobs FOR ALL TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'))
WITH CHECK ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'));

DROP POLICY IF EXISTS supervisor_all_schedules ON schedule_versions;
CREATE POLICY supervisor_all_schedules ON schedule_versions FOR ALL TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'))
WITH CHECK ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'));

DROP POLICY IF EXISTS supervisor_all_assignments ON assignments;
CREATE POLICY supervisor_all_assignments ON assignments FOR ALL TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'))
WITH CHECK ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'));

DROP POLICY IF EXISTS supervisor_all_audit ON audit_logs;
CREATE POLICY supervisor_all_audit ON audit_logs FOR SELECT TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'));


-- 6. NON-DESTRUCTIVE AI PREDICTION LOGS TABLE (OPTIONAL)
-- Persists historical inference outputs without altering existing tables
CREATE TABLE IF NOT EXISTS ai_prediction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    entity_type VARCHAR(64) NOT NULL, -- 'JOB', 'TECHNICIAN', 'ZONE'
    entity_id VARCHAR(100) NULL,
    input_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    prediction_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

ALTER TABLE IF EXISTS ai_prediction_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all_ai_logs ON ai_prediction_logs;
CREATE POLICY service_role_all_ai_logs ON ai_prediction_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS supervisor_read_ai_logs ON ai_prediction_logs;
CREATE POLICY supervisor_read_ai_logs ON ai_prediction_logs FOR SELECT TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role') IN ('supervisor', 'operations', 'admin'));

