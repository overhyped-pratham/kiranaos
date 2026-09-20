# KiranaOS — Zero-Click Store Operator
> Autonomous AI Store Operator for Neighborhood Kirana Stores. Powered by **LangGraph**, **Qwen2.5-3B-Instruct**, **BAAI/bge-m3**, **FastAPI**, **PostgreSQL / SQLite**, and **n8n WhatsApp Automation**.

---

## 1. Architecture Summary

KiranaOS is **not a chatbot**. It is an autonomous agentic store operator that receives natural-language grocery messages (English, Hindi, Hinglish), resolves products using multilingual semantic embeddings (BGE-M3 + Reranker), reads live database stock and pricing, checks availability invariants (`stock >= 0`), executes transactional database orders, updates inventory, triggers delivery dispatches, and handles edge cases (insufficient stock, unavailable products, merchant human-in-the-loop approvals).

```text
                    CUSTOMER
                       │
                       ▼
             WhatsApp / Web Chat Simulator
                       │
                       ▼
              ┌─────────────────┐
              │      n8n        │
              │ WhatsApp Layer  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  FastAPI Gateway│ (Port 8000)
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    LangGraph    │
              │ Agent Operator  │
              └────────┬────────┘
                       │
             ┌─────────┼──────────┐
             ▼         ▼          ▼
          Qwen      BGE-M3     Reranker
        Language    Product    Candidate
       Extraction  Retrieval   Ranking
             │         │          │
             └─────────┼──────────┘
                       ▼
              ┌─────────────────┐
              │  14 Backend     │
              │  Typed Tools    │
              └────────┬────────┘
                       │
                       ▼
             PostgreSQL / Supabase / SQLite
                       │
                       ▼
                      n8n
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          WhatsApp   Delivery   Alerts
          Customer   Service    Merchant
```

---

## 2. Repository Layout

```text
e:/slowbros/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── state.py                # Typed AgentState for LangGraph
│   │   │   └── graph.py                # LangGraph StateGraph (11 nodes)
│   │   ├── services/
│   │   │   ├── semantic_search.py      # BGE-M3 semantic retrieval & reranker
│   │   │   ├── llm_service.py          # Qwen2.5-3B structured intent parsing
│   │   │   ├── memory_service.py       # Customer history, memory & upselling
│   │   │   └── automation_service.py   # Downstream n8n webhooks & alerts
│   │   ├── tools/
│   │   │   └── store_tools.py          # 14 typed backend database tools
│   │   ├── routers/
│   │   │   ├── agent.py                # /agent/run, /agent/approve, /agent/runs
│   │   │   ├── inventory.py            # /inventory, /inventory/restock, /inventory/product/{id}
│   │   │   ├── orders.py               # /orders, /orders/pending-approvals
│   │   │   └── webhooks.py             # /webhook/whatsapp, /webhook/n8n
│   │   ├── config.py                   # App configuration & settings
│   │   ├── database.py                 # SQLAlchemy engine & session factory
│   │   ├── models.py                   # SQLAlchemy ORM models
│   │   ├── schemas.py                  # Pydantic v2 validation schemas
│   │   └── seed.py                     # Catalog seed script
│   ├── requirements.txt
│   ├── run_backend.py                  # Backend server launcher
│   └── .env                            # Environment configuration
├── n8n/
│   ├── kiranaos_n8n_whatsapp_workflow.json  # Ready-to-import n8n workflow
│   └── README.md                       # Setup guide for Meta WhatsApp Cloud API
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx              # System status & navigation
│   │   │   ├── ChatSimulator.jsx       # WhatsApp mobile UI with quick pills
│   │   │   ├── AgentTimeline.jsx       # Real-time LangGraph execution trace
│   │   │   ├── InventoryTable.jsx      # Live inventory with price/stock mutation
│   │   │   ├── OrdersView.jsx          # Database orders & item breakdowns
│   │   │   ├── ApprovalsView.jsx       # Merchant approval cards
│   │   │   └── JudgeSuite.jsx          # Automated test runner for all 13 scenarios
│   │   ├── services/api.js             # API client
│   │   ├── App.jsx                     # Main application layout
│   │   └── index.css                   # Tailwind styles
│   ├── package.json
│   └── vite.config.js
├── verify_judge.py                     # CLI verification suite (13 scenarios)
└── README.md
```

---

## 3. Database Schema

The database supports PostgreSQL / Supabase with automatic SQLite fallback.

* `products`: `id`, `name`, `brand`, `category`, `size`, `unit`, `price`, `stock`, `low_stock_threshold`, `aliases` (JSON), `active`. Enforces `CheckConstraint('stock >= 0')`.
* `customers`: `id`, `phone`, `name`, `default_address`, `preferences` (JSON).
* `orders`: `id` (`ORD-YYYYMMDD-XXX`), `customer_id`, `status` (`confirmed`, `pending_approval`, `rejected`, `delivered`), `subtotal`, `delivery_charge`, `total`, `idempotency_key`, `delivery_status`, `delivery_address`, `approval_reason`.
* `order_items`: `id`, `order_id`, `product_id`, `product_name`, `quantity`, `unit_price`, `line_total`.
* `inventory_logs`: `id`, `product_id`, `order_id`, `change_amount`, `previous_stock`, `new_stock`, `reason`, `timestamp`.
* `agent_runs`: `id`, `request_id`, `customer_id`, `status`, `events` (JSON array), `input_text`, `structured_intent` (JSON), `tool_calls` (JSON), `final_output` (JSON).
* `customer_preferences`: `id`, `customer_id`, `product_id`, `frequency`, `preferred_quantity`, `last_ordered_at`.
* `low_stock_events`: `id`, `product_id`, `stock_at_event`, `threshold`, `status`, `triggered_at`.
* `delivery_requests`: `id`, `order_id`, `address`, `status`, `delivery_partner`, `estimated_time`, `tracking_id`.

---

## 4. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agent/run` | Main entrypoint. Accepts customer query, executes LangGraph operator, returns order and audit trace. |
| `POST` | `/agent/approve` | Merchant approval endpoint. Resumes pending orders, deducts inventory, assigns delivery rider. |
| `GET` | `/agent/runs` | Returns recent agent runs with complete timeline events. |
| `GET` | `/agent/runs/{id}` | Returns single agent run trace. |
| `GET` | `/inventory` | List all active inventory items with live stock and unit prices. |
| `PATCH` | `/inventory/product/{id}` | **Live Mutation Endpoint**: Mutate stock (e.g. 50 → 0) or price (₹240 → ₹260) to test agent reaction. |
| `POST` | `/inventory/restock` | Restock an item and create audit record in `inventory_logs`. |
| `GET` | `/inventory/low-stock-events` | History of triggered low-stock alerts. |
| `GET` | `/orders` | List committed database orders. |
| `GET` | `/orders/pending-approvals` | List orders waiting for merchant human sign-off. |
| `GET` | `/webhook/whatsapp` | Meta WhatsApp Cloud API verification endpoint (`hub.challenge`). |
| `POST` | `/webhook/whatsapp` | Direct WhatsApp Cloud API incoming webhook receiver. |
| `POST` | `/webhook/delivery-mock` | Mock delivery partner endpoint for rider assignment. |
| `GET` | `/health` | Health check endpoint. |

---

## 5. LangGraph Operator Workflow

The agent runs an 11-node stateful workflow:

```text
START
  │
  ▼
parse_request               (Extract intent, customer profile, check idempotency)
  │
  ▼
extract_items               (Resolve items or reconstruct "usual samaan" memory)
  │
  ▼
resolve_products            (BGE-M3 semantic search + candidate reranker)
  │
  ▼
lookup_inventory_pricing    (Live database queries for stock and prices)
  │
  ▼
validate_availability       (Checks stock >= qty, detects shortages, checks approval rules)
  │
  ▼
calculate_order             (Strict database calculation: line_totals, subtotal, delivery, total)
  │
  ▼
create_order                (Transactional DB insert; ORD-YYYYMMDD-XXX)
  │
  ▼
update_inventory            (Atomic inventory deduction; stock cannot go negative)
  │
  ▼
post_order_automations      (Creates delivery request, checks low-stock thresholds, generates upsell)
  │
  ▼
generate_confirmation       (Authoritative confirmation from committed DB state; triggers n8n webhook)
  │
  ▼
persist_run                 (Saves complete audit trail to agent_runs)
  │
  ▼
END
```

---

## 6. The 14 Typed Backend Tools

1. `search_products(query, top_k)`
2. `get_product(product_id)`
3. `check_inventory(product_id, requested_quantity)`
4. `get_price(product_id)`
5. `get_customer(customer_id_or_phone)`
6. `get_customer_history(customer_id)`
7. `calculate_order(items, delivery_required)`
8. `create_order(customer_id, calculated_order, idempotency_key, delivery_address, status)`
9. `update_inventory(order_id)`
10. `create_delivery(order_id, address)`
11. `send_confirmation(order_id)`
12. `create_low_stock_alert(product_id)`
13. `save_customer_preference(customer_id, items)`
14. `log_agent_event(run_id, event_type, details)`

---

## 7. How to Run the Project

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm

### 1. Backend Setup & Run
```bash
# From repository root
cd e:/slowbros

# Install Python dependencies
py -3.12 -m pip install -r backend/requirements.txt

# Seed the database with catalog
py -3.12 -m backend.app.seed

# Start Backend Server (runs on http://localhost:8000)
py -3.12 backend/run_backend.py
```

### 2. Frontend Setup & Run
```bash
# In a new terminal
cd e:/slowbros/frontend

# Install dependencies
npm install

# Start Vite dev server (runs on http://localhost:5173)
npm run dev
```

### 3. Run Automated Judge Verification Suite
```bash
# Run all 13 hackathon scenarios
py -3.12 verify_judge.py
```

---

## 8. Live Demo Script for Judges

1. Open Dashboard: `http://localhost:5173`
2. **Scenario 1 (Happy Path)**:
   Click the preset chip **"Happy Path Order"**:
   *"Hi bhaiya, 2 packets Aashirvaad atta, 1 Fortune oil aur 3 Maggi bhej do. Ghar pe deliver kar dena."*
   - Watch the right-hand **Agent Execution Trace** render every tool call in real-time.
   - Switch to **Live Inventory** tab: Observe that Atta dropped by 2, Oil by 1, Maggi by 3.
   - Switch to **Committed Orders** tab: See the newly committed order with authoritative totals and delivery request.
3. **Scenario 2 (Dynamic Stock Mutation)**:
   - On the **Live Inventory** tab, click **Edit** on Maggi.
   - Set Stock to `0`.
   - Go back to WhatsApp Simulator, send: *"1 Maggi bhej do"*.
   - Notice the agent immediately refuses to order Maggi, marks it Out of Stock, and suggests available alternatives.
4. **Scenario 3 (Dynamic Price Mutation)**:
   - Click **Edit** on Aashirvaad Atta. Change price from ₹240 to `₹260`.
   - Send: *"1 packet Aashirvaad atta"*.
   - Notice the total is calculated as ₹260 + delivery, proving LLM has zero control over price calculation.
5. **Scenario 4 (Human Approval)**:
   - Click preset chip **"20 Maggi (Trigger Approval)"**.
   - Agent pauses in `pending_approval` state.
   - Switch to **Approvals** tab: Click **"Approve & Deduct Inventory"**.
   - Watch the workflow resume and complete the transaction.
6. **Scenario 5 (Automated Verification)**:
   - Click **Judge Verification** tab.
   - Click **"Run All Scenarios"** to execute all 13 test scenarios with live Pass/Fail verification!
