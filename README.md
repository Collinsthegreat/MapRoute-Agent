# MapRoute AI Agent for Telex.im

A production-ready AI agent that provides intelligent routing and directions through Telex.im messaging platform.

## Features

-  Real-time route calculation between any two locations
-  Smart location geocoding and validation
-  Async/await architecture for optimal performance
-  Automatic retry logic with exponential backoff
-  Comprehensive input validation and error handling
-  Structured logging for monitoring
-  Docker support for easy deployment
-  Full test coverage

## Architecture
```
maproute-agent/
├── app/              # FastAPI application
├── services/         # Business logic layer
├── models/           # Pydantic schemas
├── utils/            # Helper utilities
└── tests/            # Test suite
```

## Prerequisites

- Python 3.11+
- LocationIQ API key (free tier available)
- OpenRouteService API key (free tier available)

## Installation

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd maproute-agent
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

5. Run the application:
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

### Docker Deployment
```bash
docker build -t maproute-agent .
docker run -p 8000:8000 --env-file .env maproute-agent
```

## Configuration

Create a `.env` file with the following variables:
```env
OPENROUTESERVICE_API_KEY=your_key_here
LOCATIONIQ_API_KEY=your_key_here
APP_ENV=production
LOG_LEVEL=INFO
PORT=8000
```

## Usage

### Testing Locally
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "directions from Lagos to Abuja"}'
```

### Telex.im Integration

1. Deploy your agent to

 Usage & Testing
Local curl Test (simple JSON format)
curl -X POST http://127.0.0.1:8000/webhook \
-H "Content-Type: application/json" \
-d '{"message": {"kind":"message","role":"user","parts":[{"kind":"text","text":"directions from Paris, France to Lyon, France"}]}}'


Expected Output:

{
  "text": "🚗 Route from Paris, France to Lyon, France:\n📏 Distance: 463.78 km\n⏱️ Estimated time: 4 hours 56 min",
  "attachments": [
    {
      "type": "link",
      "url": "https://www.google.com/maps/dir/?api=1&origin=48.85,2.35&destination=45.75,4.83",
      "title": "📍 View on Google Maps"
    }
  ],
  "metadata": {
    "distance_km": 463.78,
    "duration_minutes": 296.4
  }
}

🤖 Telex.im Integration Guide
Step 1 — Get Access

In your HNG Slack channel, run:

/telex-invite your-email@example.com


You’ll get added to the Telex organization.

Step 2 — Deploy to a Public Endpoint

Deploy to Railway
 or Render
.
Example:

https://maproute-agent-production.up.railway.app/webhook

Step 3 — Register Your Agent on Telex.im

Create a workflow.json like:

{
  "active": true,
  "category": "productivity",
  "description": "AI agent that provides intelligent routing and directions",
  "name": "MapRoute Agent",
  "nodes": [
    {
      "id": "maproute_agent_node",
      "name": "MapRoute Agent",
      "type": "a2a/agent-node",
      "url": "https://maproute-agent-production.up.railway.app/webhook",
      "position": [500, 200]
    }
  ]
}

Step 4 — Test on Telex.im

Once your agent is registered:

Open your Telex workspace

Mention your agent: @MapRoute Agent

Send:

directions from Lagos to Abuja


View logs here:

https://api.telex.im/agent-logs/{channel-id}.txt

🧩 A2A Protocol Format

Request Example

{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message.process",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "directions from Paris, France to Lyon, France"
        }
      ]
    },
    "context": {
      "conversation_id": "conv-12345",
      "app_id": "app-001",
      "user_id": "user-001"
    }
  }
}


Response Example

{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "message": {
      "kind": "message",
      "role": "agent",
      "parts": [
        {
          "kind": "text",
          "text": "🚗 Route from Paris, France to Lyon, France:\n📏 Distance: 463.78 km\n⏱️ Estimated time: 4 hours 56 min"
        },
        {
          "kind": "data",
          "data": {
            "type": "link",
            "url": "https://www.google.com/maps/dir/?api=1&origin=48.85,2.35&destination=45.75,4.83",
            "title": "📍 View on Google Maps"
          }
        }
      ],
      "messageId": "msg_response"
    }
  }
}

 License

This project is licensed under the MIT License — free to modify and use for educational or production purposes.

 Author

Abuchi Nwajagu Collins
DevOps Engineer | Backend Engineer
