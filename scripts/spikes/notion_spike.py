
import os
import requests
from dotenv import load_dotenv

# Load the Notion API token from .env
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")

if not NOTION_API_KEY:
    raise RuntimeError("NOTION_API_KEY is missing from .env")

BASE_URL = "https://api.notion.com/v1"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}

# Step 1: Search for the sandbox page
response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json={"query": "Agentic RAG Sandbox"},
    timeout=30,
)

if not response.ok:
    print("Notion API error:", response.status_code)
    print(response.text)
    raise SystemExit(1)

pages = [
    item for item in response.json().get("results", [])
    if item.get("object") == "page"
]

if not pages:
    print("Page not found. Check that it is shared with your integration.")
    raise SystemExit(1)

page = pages[0]
page_id = page["id"]

print("SUCCESS: Connected to Notion!")
print("Page ID:", page_id)

# Step 2: Retrieve the page content
content_response = requests.get(
    f"{BASE_URL}/blocks/{page_id}/children",
    headers=headers,
    timeout=30,
)

if not content_response.ok:
    print("Content retrieval error:", content_response.status_code)
    print(content_response.text)
    raise SystemExit(1)

blocks = content_response.json().get("results", [])

print("\nRetrieved page content:")

for block in blocks:
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})
    rich_text = block_data.get("rich_text", [])

    text = "".join(
        item.get("plain_text", "")
        for item in rich_text
    )

    if text:
        print("-", text)

print("\nNotion connectivity test completed.")