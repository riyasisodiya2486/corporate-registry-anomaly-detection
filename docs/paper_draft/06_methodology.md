## Deployment

- Database: PostgreSQL hosted on Neon (cloud-native, serverless Postgres)
- Pipeline: containerized via Docker, 6 services, each independently buildable
- CI: GitHub Actions builds all service images on every push to main
- Application: Streamlit app deployed to Streamlit Community Cloud, publicly accessible
- Disposable test database pattern used for safe runtime validation (Day 9) without risk to production data

- Deployment initially failed on Python 3.14 because pinned packages (numpy 2.2.6, psycopg2-binary 2.9.9) had no Python 3.14 wheels and were built from source; fixed by app-specific, unpinned dependencies.