import os
import requests
import json
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_hacker_news_ideas():
    print("Fetching top Ask/Show HN threads...")
    # Fetches active discussion IDs
    top_ids = requests.get("https://hacker-news.firebaseio.com/v0/askstories.json").json()
    
    ideas_raw_text = []
    # Inspect the top 12 active text items
    for idx in top_ids[:12]:
        story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{idx}.json").json()
        if story and "text" in story and "title" in story:
            ideas_raw_text.append(f"Title: {story['title']}\nText: {story['text']}")
            
    return "\n---\n".join(ideas_raw_text)

def process_ideas_with_ai(raw_text):
    print("Asking Gemini to extract structured business opportunities...")
    
    prompt = f"""
    Analyze the following social media discussions where people complain about problems or suggest software ideas.
    Extract the legitimate software startup or app opportunities. Filter out generic rants.
    
    Format the output strictly as a JSON array of objects. Do not wrap the JSON in markdown fences.
    Each object must match these exact keys:
    - title: A short 3-4 word descriptive app concept name.
    - core_pain_point: One clean sentence outlining the specific frustration.
    - industry_tag: A single relevant tag (e.g., SaaS, AI, Productivity, DevTools).
    - original_source: Set to 'Hacker News'

    Data:
    {raw_text}
    """
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    
    return json.loads(response.text)

def save_to_supabase(structured_ideas):
    print(f"Syncing {len(structured_ideas)} fresh ideas to Supabase...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates" 
    }
    
    response = requests.post(f"{SUPABASE_URL}/rest/v1/ideas", headers=headers, json=structured_ideas)
    if response.status_code in [200, 201]:
        print("Success! Database synced.")
    else:
        print(f"Database error: {response.text}")

if __name__ == "__main__":
    raw_data = fetch_hacker_news_ideas()
    if raw_data:
        clean_ideas = process_ideas_with_ai(raw_data)
        save_to_supabase(clean_ideas)
