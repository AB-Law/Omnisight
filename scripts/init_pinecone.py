import os
import time
from pinecone import Pinecone, ServerlessSpec
from intelligence_api.core.config import settings

def init_pinecone():
    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX

    if not api_key:
        print("❌ PINECONE_API_KEY not found in .env")
        return

    pc = Pinecone(api_key=api_key)

    print(f"🌲 Checking Pinecone for index: '{index_name}'...")
    
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"🚀 Creating new serverless index: '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=1536, # Standard for text-embedding-3-small
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print("⏳ Waiting for index to be ready (this can take ~30s)...")
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(5)
        print(f"✅ Index '{index_name}' is ready!")
    else:
        print(f"✅ Index '{index_name}' already exists.")

def reset_pinecone():
    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX

    if not api_key:
        print("❌ PINECONE_API_KEY not found in .env")
        return

    pc = Pinecone(api_key=api_key)
    existing_indexes = [index.name for index in pc.list_indexes()]

    if index_name in existing_indexes:
        print(f"🗑️ Deleting Pinecone index '{index_name}'...")
        pc.delete_index(index_name)
        print("✅ Index deleted.")
    else:
        print(f"✅ Index '{index_name}' does not exist.")

if __name__ == "__main__":
    init_pinecone()
