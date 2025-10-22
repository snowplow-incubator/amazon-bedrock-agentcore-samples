from strands.tools import tool
from ddgs.exceptions import DDGSException, RatelimitException
from ddgs import DDGS
from strands_tools import retrieve
import boto3

MODEL_ID = "apac.anthropic.claude-3-7-sonnet-20250219-v1:0"

# System prompt defining the agent's role and capabilities
SYSTEM_PROMPT = """

You are a helpful Southeast Asia travel assistant for SEA Explorer, a travel website focused on Southeast Asian destinations. You have extensive knowledge about:

- Destinations: Thailand, Vietnam, Indonesia, Philippines, Malaysia, Singapore, Cambodia, Laos, Myanmar, Brunei
- Popular cities: Bangkok, Ho Chi Minh City, Hanoi, Bali, Manila, Kuala Lumpur, Singapore, Siem Reap, Chiang Mai, Penang, Yogyakarta, Luang Prabang
- Travel experiences: cooking classes, temple tours, island hopping, cultural experiences, food tours, adventure activities
- Practical information: visas, budgets, transportation, accommodation, safety, weather, best times to visit
- Local culture, food, customs, and etiquette
- Budget travel tips and backpacking routes
- Digital nomad information and remote work opportunities

Provide helpful, accurate, and engaging responses about Southeast Asian travel. Be conversational and friendly. If asked about destinations or experiences outside Southeast Asia, politely redirect the conversation back to SEA travel topics.

Keep responses concise but informative. Use bullet points or numbered lists when appropriate for better readability. Format your responses with emojis and clear sections when helpful.

You have access to the following tools:
1. get_destination_info() - For information about a specific destination
2. get_experience_info() - For information about a specific experience
3. web_search() - To access current technical documentation, or for updated information.
4. get_signals() - Access the users current behavioural signals

Always use the appropriate tool to get accurate, up-to-date information rather than making assumptions."""

@tool
def web_search(keywords: str, region: str = "us-en", max_results: int = 5) -> str:
    """Search the web for updated information.
    
    Args:
        keywords (str): The search query keywords.
        region (str): The search region: wt-wt, us-en, uk-en, ru-ru, etc..
        max_results (int | None): The maximum number of results to return.
    Returns:
        List of dictionaries with search results.
    
    """
    try:
        results = DDGS().text(keywords, region=region, max_results=max_results)
        return results if results else "No results found."
    except RatelimitException:
        return "Rate limit reached. Please try again later."
    except DDGSException as e:
        return f"Search error: {e}"
    except Exception as e:
        return f"Search error: {str(e)}"

@tool
def get_destination_info(destination: str) -> str:
    """
    Get information about a specific destination.

    Args:
        desination: The name of the destination (e.g., 'Bangkok')

    Returns:
        Formatted information about the destination including descriptions, ratings, highlights and tags

    """
    with open('destinations.json', 'r') as f:
        data = f.read()

    return json.dumps(
  {
    "id": 1,
    "name": "Bangkok",
    "country": "Thailand",
    "price": 150,
    "image": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?q=80&w=1950&ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "images_category": {
      "cultural_explorer": "https://images.unsplash.com/photo-1690299490301-2eb3865bee58?q=80&w=2069&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
      "family_fun": "https://images.unsplash.com/photo-1733150632166-8d8752da4ff6?q=80&w=2232&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
      "modern_urbanite": "https://images.unsplash.com/photo-1593103499244-6c882f0163cf?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
      "tranquil_seeker": "https://images.unsplash.com/photo-1591233244269-d8c4bcbbf1dd?q=80&w=987&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
      "culinary_tourist": "https://images.unsplash.com/photo-1506781961370-37a89d6b3095?q=80&w=1674&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    },
    "description": "Vibrant capital with street food, temples, and bustling markets",
    "descriptions": {
      "cultural_explorer": "Grand palaces, ancient temples, and rich history await. Discover the soul of Thailand's capital.",
      "family_fun": "Kids love the tuk-tuks, canal tours, and vibrant markets. A city of endless family adventures.",
      "culinary_tourist": "A street food paradise with an explosion of flavours. Authentic Thai cuisine at every turn.",
      "tranquil_seeker": "Find peace in serene temples, tranquil gardens, and riverside long-tail boat journeys.",
      "modern_urbanite": "A vibrant, non-stop metropolis with world-class nightlife, shopping, and cutting-edge art."
    },
    "rating": 4.5,
    "priceLevel": 2,
    "safety": 4,
    "weather": 3,
    "activities": 5,
    "familyFriendly": 4,
    "internet": 5,
    "cost": 5,
    "airQuality": 2,
    "leisure": 5,
    "food": 5,
    "culture": 5,
    "suitability": ["Local", "Expat", "Nomad"],
    "highlights": ["Street Food", "Temples", "Nightlife", "Shopping"],
    "tags": ["temples", "nightlife", "street-food", "shopping", "urban"]
  }
    )


@tool
def get_experience_info(experience: str) -> str:
    """
    Get detailed information on what experiences are available and what is involved

    Args:
        experience: Experience name
    Returns:
        Formatted experience information including experience length, tags
    """
    with open('experiences.json', 'r') as f:
        data = f.read()
    return data
print("✅ Experience tool ready")

@tool
def get_all_experiences() -> str:
    """
    Get detailed information on what experiences are available and what is involved

    Returns:
        Formatted experience information including experience length, tags
    """
    with open('experiences.json', 'r') as f:
        data = f.read()
    return data
print("✅ Experience tool ready")

import json
import snowplow_signals


API_URL = "https://example.signals.snowplowanalytics.com"
API_KEY = ""
API_KEY_ID = "3"
ORG_ID = ""

@tool
def get_signals() -> str:
    try:
        sp_signals = Signals(API_URL, API_KEY, API_KEY_ID, ORG_ID)
        response = sp_signals.get_service_attributes(
            name='travel_service',
            attribute_key='domain_sessionid',
            identifier=domain_sessionid
        )
        # TODO: subtract user id out
        # TODO: consider only returning non-None values
        print(f'signals returned: {response}')
        return json.dumps(response)
    except Exception as e:
        return f"Failed to get Signals: {e}"
        