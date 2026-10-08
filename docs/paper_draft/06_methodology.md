## Deployment

- Database: PostgreSQL hosted on Neon (cloud-native, serverless Postgres)
- Pipeline: containerized via Docker, 6 services, each independently buildable
- CI: GitHub Actions builds all service images on every push to main
- Application: Streamlit app deployed to Streamlit Community Cloud, publicly accessible
- Disposable test database pattern used for safe runtime validation (Day 9) without risk to production data