CREATE TABLE IF NOT EXISTS raw_companies (
    raw_id SERIAL PRIMARY KEY,
    cin TEXT,
    company_name TEXT,
    company_status TEXT,
    company_category TEXT,
    company_sub_category TEXT,
    roc_code TEXT,
    registered_address TEXT,
    date_of_registration TEXT,
    authorized_capital TEXT,
    paidup_capital TEXT,
    principal_business_activity TEXT,
    loaded_at TIMESTAMP
);