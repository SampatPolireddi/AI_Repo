# VoiceOrder Backend 🎙️🍔

A robust, voice-enabled AI agent backend designed for restaurants. This system powers a voice assistant capable of taking complex food orders, handling menu variations, validating delivery addresses, and finalizing customer tickets.

## 🚀 Features

*   **Intelligent Order Taking:** Handles complex queries like "Butter Chicken with Garlic Naan" and manages modifications (e.g., "make it spicy").
*   **Dynamic Pricing:** Automatically calculates sub-totals, taxes, and prices options (e.g., Gravy vs. Dry) and variations (Plain vs. Butter Naan).
*   **Delivery Validation:** Integrates with **Google Maps API** to verify delivery addresses and check against serviceable usage zones (Zip Codes).
*   **Webhook Architecture:** Built with **FastAPI** to serve as a lightweight, fast, and scalable webhook for tools like **Ultravox**.
*   **Duck Typing Dispatch:** Smartly detects tool intent based on payload structure, simplifying the API surface.

## 🛠️ Tech Stack

*   **Framework:** Python 3.11 + FastAPI
*   **Tools:** Pydantic, Uvicorn
*   **Integrations:** Google Maps Platform, Ultravox SDK
*   **Deployment:** Docker-ready (or run locally via ngrok)

## 📂 Project Structure

```bash
VoiceOrder-Backend/
├── main.py              # Webhook entry point & tool dispatch logic
├── tools.py             # Core business logic (pricing, validation, cart mgmt)
├── latestMenu.json      # Structured menu database
├── requirements.txt     # Python dependencies
└── .env.example         # Template for environment variables
```

## ⚡ Quick Start

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd VoiceOrder-Backend
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Environment:**
    Copy `.env.example` to `.env` and add your keys:
    ```bash
    cp .env.example .env
    # Add GOOGLE_MAPS_API_KEY
    ```

4.  **Run the Server:**
    ```bash
    uvicorn main:app --reload
    ```

5.  **Expose to Internet (for Webhooks):**
    ```bash
    ngrok http 8000
    ```
    Use the generated URL in your AI Agent configuration.

## 🔗 API Integration

The system exposes a single smart endpoint: `POST /webhook`. It accepts a JSON payload and automatically routes it to the specific function based on the arguments provided (e.g., if `cart_items` is present, it calculates the order total).

---
*Built for the future of AI-driven dining.*
