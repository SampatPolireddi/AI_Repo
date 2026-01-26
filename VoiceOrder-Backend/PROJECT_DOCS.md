# House of Biryani - Voice Agent Project Documentation

## 1. Project Overview
This project serves as the backend infrastructure for **Biryani Bot**, an AI voice agent for "House of Biryani & Kebabs". The system allows customers to place orders via voice, handles complex menu pricing, validates delivery addresses via Google Maps, and generates finalized order tickets.

**Tech Stack:**
*   **Language:** Python 3.11+
*   **API Framework:** FastAPI (for Webhooks)
*   **Voice AI Platform:** Ultravox (Agent & Telephony)
*   **External APIs:** Google Maps Platform (Address Validation)
*   **Tunneling:** ngrok (Localhost exposure)

---

## 2. Project Structure

```bash
HouseOfBiryani/
├── main.py              # Entry point: FastAPI server & Webhook logic
├── tools.py             # Core Logic: Pricing, Menu Search, Address Validation
├── latestMenu.json      # Database: Full menu with prices, variations, and metadata
├── latestMenu.md        # Knowledge Base: Text version for RAG (optional utilization)
└── .env                 # Secrets: API Keys (Google Maps, Ultravox)
```

---

## 3. Core Functions (`tools.py`)

### `get_price(item_name, quantity, dish_type)`
*   **Purpose:** Calculates the price for a specific line item.
*   **Logic:**
    *   Searches `latestMenu.json` for `item_name`.
    *   Handles flat prices (e.g., "$12.99").
    *   Handles **Price Options** (e.g., `gravy` vs `dry`).
    *   Handles **Variations** (e.g., `plain`, `butter`, `garlic` for Naans).
*   **Returns:** Total float value (Unit Price * Quantity).

### `calculate_order(cart_items)`
*   **Purpose:** Computes the grand total and generates a receipt.
*   **Input:** Dictionary of items.
    *   Format: `{"Item Name": [Quantity, "Style/Type", "Notes"]}`
*   **Returns:** Dictionary with `total_price` and a detailed `breakdown` list.

### `validate_delivery_address(address_txt)`
*   **Purpose:** Determines if a customer is within the delivery zone.
*   **Logic:**
    *   Calls **Google Maps Address Validation API**.
    *   Checks `dpvConfirmation` to ensure the house number exists.
    *   Validates Zip Code against a whitelist (`75034`, `75035`, etc.).
*   **Returns:** `valid` (bool), `status`, and `message`.

### `customer_details(first_name, last_name, phone, address, cart_items)`
*   **Purpose:** Finalizes the order.
*   **Logic:**
    *   Validates phone number format (10 digits).
    *   Generates a random 3-digit **Order ID**.
    *   Creates a `customer_record` combining contact info + full order details.
*   **Returns:** Success message and Order ID.

---

## 4. API Endpoints (`main.py`)

### `POST /webhook`
This is the single entry point for the Ultravox Agent. It uses **Duck Typing** (inspecting payload keys) to route requests to the correct tool function.

| Payload Keys Detected | Mapped Function |
| :--- | :--- |
| `cart_items` (no `first_name`) | `tools.calculate_order` |
| `address_txt` | `tools.validate_delivery_address` |
| `first_name` + `cart_items` | `tools.customer_details` |
| `item_name` + `quantity` | `tools.get_price` (Debug tool) |

---

## 5. External Integrations

### Google Maps API
*   **Service:** Address Validation API
*   **Usage:** exact verification of US addresses and Zip code filtering.
*   **Key:** stored in `.env` as `GOOGLE_MAPS_API_KEY`.

### Ultravox
*   **Role:** The "Frontend" AI that talks to the customer.
*   **Connection:** Ultravox sends tool calls as HTTP POST requests to the `ngrok` URL, which forwards them to `main.py`.
