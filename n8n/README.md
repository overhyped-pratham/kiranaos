# KiranaOS n8n + WhatsApp Business Cloud Integration

This directory contains the ready-to-import n8n workflow for **KiranaOS — Zero-Click Store Operator**.

## Workflow Architecture

```text
Customer WhatsApp
       │
       ▼
WhatsApp Cloud API
       │
       ▼
n8n Webhook Trigger (`/webhook/kiranaos-whatsapp-webhook`)
       │
       ▼
Normalize Message (`phone`, `message`, `idempotency_key`)
       │
       ▼
HTTP Request: POST `http://localhost:8000/agent/run`
       │
       ├──► status == "confirmed" ──────────► Send Customer WhatsApp Order Receipt
       │                                         │
       │                                         ▼
       │                                     Any Low Stock Events?
       │                                         │
       │                                         └──► Alert Merchant WhatsApp
       │
       ├──► status == "pending_approval" ───► Send Merchant WhatsApp Approval Alert
       │
       └──► status == "needs_clarification" ─► Send Clarification Options / Alternatives
```

## How to Import & Run in n8n

1. **Install and Start n8n**:
   ```bash
   npx n8n
   # or via docker:
   # docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n
   ```
2. Open n8n web UI: `http://localhost:5678`
3. Click **Workflows** → **Import from File...**
4. Select `kiranaos_n8n_whatsapp_workflow.json`.
5. Configure WhatsApp Credentials in n8n:
   - In Meta Developer Portal, obtain:
     - `WHATSAPP_PHONE_NUMBER_ID`
     - `WHATSAPP_ACCESS_TOKEN`
   - In n8n, add a WhatsApp credential or set environment variables.
6. Activate the workflow!

## Idempotency Protection

Each incoming WhatsApp message contains a unique `wamid` or `message_id`. This ID is mapped to `idempotency_key`.
If Meta retries a webhook for an already processed order, KiranaOS intercepts the duplicate key:
- Returns the committed order without modifying inventory.
- Prevents double billing and stock leakage.
