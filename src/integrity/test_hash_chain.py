from hash_chain import (
    hash_all_entities,
    log_audit_action,
    verify_chain_integrity,
)

from sqlalchemy import create_engine, text


engine = create_engine(
    "postgresql://admin:admin123@localhost:5432/registry"
)


# Step 1: Build the hash chain over the real cleaned data
hash_all_entities()


# Step 2: Verify the untampered chain
print("\n--- Verifying untampered chain ---")
verify_chain_integrity("record_hashes")


# Step 3: Reset audit log for a clean demonstration
with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE audit_log RESTART IDENTITY"))
    conn.commit()


# Step 4: Log two audit actions
log_audit_action(
    "flagged",
    cluster_id=1,
    reviewer="system"
)

log_audit_action(
    "reviewed_confirmed",
    cluster_id=1,
    reviewer="Yashika"
)

print("\n--- Verifying audit_log chain ---")
verify_chain_integrity("audit_log")


# Step 5: Deliberately tamper with row 5
print("\n--- Deliberately tampering with row 5 ---")

with engine.connect() as conn:
    conn.execute(
        text("""
            UPDATE record_hashes
            SET record_hash = 'TAMPERED'
            WHERE hash_id = 5
        """)
    )
    conn.commit()


# Step 6: Verify again
print("--- Re-verifying after tampering ---")
verify_chain_integrity("record_hashes")