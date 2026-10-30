-- DISPATCHGRID / ELECTROGRID Migration: 003_payments_and_invoices.sql
-- Additive migration for payments, damaged_components, and invoices tables

CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_reference VARCHAR(64) UNIQUE NOT NULL,
    job_id UUID NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customer_profiles(id) ON DELETE SET NULL,
    technician_id UUID REFERENCES public.technician_profiles(id) ON DELETE SET NULL,
    work_started_at TIMESTAMPTZ NOT NULL,
    work_completed_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL,
    base_amount_paise INTEGER NOT NULL DEFAULT 50000,
    additional_blocks INTEGER NOT NULL DEFAULT 0,
    additional_amount_paise INTEGER NOT NULL DEFAULT 0,
    labour_total_paise INTEGER NOT NULL DEFAULT 50000,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    payment_method VARCHAR(32) NOT NULL DEFAULT 'CASH',
    payment_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    razorpay_order_id VARCHAR(128),
    razorpay_payment_id VARCHAR(128),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_by VARCHAR(128),
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.damaged_components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
    payment_id UUID REFERENCES public.payments(id) ON DELETE SET NULL,
    component_name VARCHAR(255) NOT NULL,
    damage_description TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    photo_url TEXT,
    price_status VARCHAR(64) NOT NULL DEFAULT 'Price to be confirmed',
    estimated_part_amount_paise INTEGER,
    remarks TEXT,
    reported_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(64) UNIQUE NOT NULL,
    payment_id UUID NOT NULL REFERENCES public.payments(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customer_profiles(id) ON DELETE SET NULL,
    technician_id UUID REFERENCES public.technician_profiles(id) ON DELETE SET NULL,
    customer_name VARCHAR(255) NOT NULL,
    technician_name VARCHAR(255) NOT NULL,
    service_description TEXT NOT NULL,
    invoice_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    duration_minutes INTEGER NOT NULL,
    labour_amount_paise INTEGER NOT NULL,
    additional_amount_paise INTEGER NOT NULL,
    parts_amount_paise INTEGER,
    total_paid_paise INTEGER NOT NULL,
    payment_method VARCHAR(32) NOT NULL,
    payment_status VARCHAR(32) NOT NULL DEFAULT 'PAID',
    pdf_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_payments_job_id ON public.payments(job_id);
CREATE INDEX IF NOT EXISTS ix_payments_customer_id ON public.payments(customer_id);
CREATE INDEX IF NOT EXISTS ix_payments_status ON public.payments(payment_status);
CREATE INDEX IF NOT EXISTS ix_damaged_components_job_id ON public.damaged_components(job_id);
CREATE INDEX IF NOT EXISTS ix_invoices_payment_id ON public.invoices(payment_id);
CREATE INDEX IF NOT EXISTS ix_invoices_job_id ON public.invoices(job_id);
CREATE INDEX IF NOT EXISTS ix_invoices_number ON public.invoices(invoice_number);

