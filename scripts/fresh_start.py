"""
fresh_start.py – Full reset: drops + recreates all DB tables, clears Pinecone, resets Pub/Sub.

Usage:
    python scripts/fresh_start.py
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligence_api.core.database import engine
from intelligence_api.domain.models import Base
from intelligence_api.core.config import settings


def reset_db():
    print("🗄️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("🗄️  Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅  Database reset complete.")


def clear_pinecone():
    print("📌  Clearing Pinecone index...")
    try:
        import pinecone

        pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX)
        index.delete(delete_all=True)
        print("✅  Pinecone index cleared.")
    except Exception as e:
        print(f"⚠️   Pinecone clear failed (continuing): {e}")


def reset_pubsub():
    print("📨  Resetting Pub/Sub subscriptions...")
    try:
        # Delegate to the existing reset_pubsub script which knows the correct config
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location(
            "reset_pubsub",
            os.path.join(os.path.dirname(__file__), "reset_pubsub.py"),
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        mod.reset_pubsub()
        print("✅  Pub/Sub reset complete.")
    except Exception as e:
        print(f"⚠️   Pub/Sub reset failed (continuing): {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Omnisight Full Reset")
    print("=" * 60)
    confirm = input(
        "\n⚠️  This will PERMANENTLY DELETE all data in the DB, Pinecone, and Pub/Sub.\n"
        "Type 'yes' to continue: "
    )
    if confirm.strip().lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

    reset_db()
    clear_pinecone()
    reset_pubsub()

    print("\n✨  Omnisight is reset and ready for a fresh start.")
