import requests
import json
import time

API_URL = "http://localhost:8000/process-event"

def test_process_event():
    payload = {
        "entity_label": "Google",
        "content": "Google just announced a breakthrough in quantum computing that could significantly speed up AI training.",
        "source_type": "News",
        "is_user": False,
        "raw_url": "https://example.com/quantum-news"
    }

    print(f"🚀 Sending test event to {API_URL}...")
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print("✅ Success! Event processed.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Failed with status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Give the API a second to be fully ready if just started
    test_process_event()
