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
