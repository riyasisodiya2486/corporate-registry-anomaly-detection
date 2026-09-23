CREATE TABLE IF NOT EXISTS cleaned_entities (
    entity_id SERIAL PRIMARY KEY,
    raw_id INTEGER REFERENCES raw_companies(raw_id),
    cin TEXT,
    company_name_raw TEXT,
    company_name_normalized TEXT,
    address_raw TEXT,
    address_normalized TEXT,
    pincode TEXT,
    company_status TEXT,
    company_category TEXT,
    company_sub_category TEXT,
    authorized_capital NUMERIC,
    paidup_capital NUMERIC,
    date_of_registration DATE,
    nic_code TEXT,
    cleaned_at TIMESTAMP DEFAULT NOW()
);