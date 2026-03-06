from setuptools import setup, find_packages

setup(
    name="omnisight",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pydantic-settings",
        "sqlalchemy",
        "psycopg2-binary",
        "openai",
        "pinecone",
        "google-cloud-pubsub",
        "streamlit",
        "pandas",
        "plotly",
        "fpdf2",
    ],
)
