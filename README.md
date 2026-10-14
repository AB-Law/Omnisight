# Omnisight

Automated OSINT platform tracking Companies and Usernames across public web sources.

## Tech Stack
- **Backend**: Python (FastAPI)
- **Database**: PostgreSQL (GCE e2-micro / Docker local)
- **Intelligence**: Azure OpenAI (GPT-4o mini, Embeddings)
- **Vector Cache**: Pinecone
- **Messaging**: GCP Pub/Sub
- **Frontend**: Streamlit
- **Infrastructure**: Terraform

## Local Setup
1. Clone the repo.
2. Ensure Docker is installed.
3. Create a `.env` file (see `.env.example`).
4. Run `docker compose up`.
