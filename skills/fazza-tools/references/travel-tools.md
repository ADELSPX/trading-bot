# Travel & Booking Tools

## Flights: LetsFG
- **Repo:** github.com/LetsFG/LetsFG
- **Install:** `pip install letsfg`
- **Features:** 200+ connectors, 400+ airlines, CLI/Python SDK/MCP
- **Free:** Search is 100% free. Unlock/Book requires API key.
- **Saves vs Google Flights:** ~$20-50 per flight (verified)
- **Commands:**
  - `letsfg search LHR BCN 2026-06-15`
  - `letsfg search LON JFK 2026-06-15 --mode fast`
  - `letsfg search LHR JFK 2026-06-15 --cabin C` (business)

## Hotels: openbnb (Airbnb MCP)
- **Repo:** github.com/openbnb-org/mcp-server-airbnb
- **Install:** `npx -y @openbnb/mcp-server-airbnb`
- **Features:** City/region search, dates, guests, property type, price filters

## Hotels: hotels_mcp (Booking.com)
- **Repo:** github.com/esakrissa/hotels_mcp_server
- **Requires:** RapidAPI key for Booking.com API
- **Features:** Search destinations, get hotels with pricing/ratings/photos

## All-in-One Travel: mcp_travelassistant
- **Repo:** github.com/skarlekar/mcp_travelassistant
- **6 MCP servers:** flights + hotels + events + weather + geocoding + finance
- **Takes natural language request, returns full itinerary**
- **Requires:** SerpAPI key (free tier available)

## When to Use
- Research flight prices: LetsFG CLI
- Full trip planning: mcp_travelassistant
- Airbnb search: openbnb MCP
- Hotel search: hotels_mcp

## Pitfall
- flight-goat (Shubham Saboo's tool) is NOT publicly available
- Use LetsFG as the superior open-source alternative
