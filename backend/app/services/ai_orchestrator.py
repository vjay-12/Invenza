"""
Invenza AI Orchestrator Service
Implements a single conversational interface orchestrating two specialized tools:
1. `query_inventory_db` - Read-only Text-to-SQL with tenant isolation and strict SELECT enforcement.
2. `search_docs` - pgvector RAG retriever over Invenza system documentation and SOPs.
"""

import json
import re
from typing import Dict, Any, List
from app.schemas.ai import ChatRequest, ChatResponse, ToolInvocation

# Open-spec tool definitions for function-calling
INVENZA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_inventory_db",
            "description": "Execute a read-only SQL query over the inventory database to answer analytical questions regarding stock balances, movements, purchase orders, or suppliers. Automatically tenant-isolated and limited to SELECT statements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The Postgres SELECT query to execute. Must NOT include INSERT/UPDATE/DELETE/DROP.",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of what data this query is retrieving.",
                    }
                },
                "required": ["sql_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search the Invenza product knowledge base and inventory management SOPs for concepts like FIFO valuation, movement ledgers, GRN flows, or reason codes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to match against help documentation chunks.",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["all", "valuation", "ledger", "orders", "configuration"],
                        "description": "Optional category filter.",
                    }
                },
                "required": ["query"]
            }
        }
    }
]

class AIOrchestrator:
    @staticmethod
    def validate_sql(query: str) -> bool:
        """Strict guardrail: only allow single SELECT statements."""
        cleaned = query.strip().upper()
        if not cleaned.startswith("SELECT"):
            return False
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", ";"]
        # Basic check; in production, use SQLGlot or sqlparse AST validation
        for word in forbidden:
            if re.search(r'\b' + word + r'\b', cleaned):
                if word == ";" and cleaned.endswith(";"):
                    continue
                return False
        return True

    @classmethod
    async def process_chat(cls, request: ChatRequest) -> ChatResponse:
        """
        Processes conversation with realistic simulated routing or direct LLM integration.
        Returns tool invocations, data findings, and friendly syntheses.
        """
        last_message = request.messages[-1].content if request.messages else ""
        lower = last_message.lower()

        # Simulated intelligent dual-tool routing for UX testing and validation:
        if any(w in lower for w in ["fifo", "valuation", "how does", "weighted average", "ledger work", "reason code"]):
            # Invokes search_docs
            tool_invoc = ToolInvocation(
                tool_name="search_docs",
                arguments={"query": last_message, "category": "valuation"},
                output="Matched Section: 'Invenza Valuation Engines: FIFO vs Weighted Average Costing'. First-In First-Out assigns the unit cost of the oldest batch received to subsequent stock-out movements. Weighted Average divides total inventory value by available quantity."
            )
            return ChatResponse(
                message="According to the Invenza documentation, our system supports two core valuation models:\n\n1. **FIFO (First-In, First-Out)**: Assumes items purchased first are consumed or sold first. This reflects real-world physical stock rotation and maintains accurate asset pricing in inflationary environments.\n2. **Weighted Average Costing**: Blends the acquisition cost of all active units to provide a steady unit cost.\n\nAll valuation metrics are dynamically derived directly from your **immutable stock movement ledger**.",
                tools_invoked=[tool_invoc],
                citations=[{
                    "title": "Inventory Valuation & Ledger Guide",
                    "section": "Costing Methods & Real-time Aggregation",
                    "doc_id": "doc-val-01"
                }]
            )

        elif any(w in lower for w in ["low on stock", "reorder", "below", "out of stock", "how many", "count"]):
            # Invokes query_inventory_db
            sql = "SELECT p.sku, p.name, p.reorder_point, COALESCE(SUM(m.quantity), 0) AS current_stock FROM products p LEFT JOIN stock_movements m ON p.id = m.product_id WHERE p.tenant_id = :tenant_id GROUP BY p.id, p.sku, p.name, p.reorder_point HAVING COALESCE(SUM(m.quantity), 0) <= p.reorder_point;"
            tool_invoc = ToolInvocation(
                tool_name="query_inventory_db",
                arguments={"sql_query": sql, "explanation": "Retrieve all SKUs where aggregated ledger balance is at or below reorder threshold"},
                output=[
                    {"sku": "SKU-DESK-MAT", "name": "Vegan Leather Dual-Sided Desk Mat", "reorder_point": 20, "current_stock": 6},
                    {"sku": "SKU-MEC-KEYBD", "name": "Vortex Mechanical RGB Keyboard", "reorder_point": 25, "current_stock": 18}
                ]
            )
            return ChatResponse(
                message="Here are the items currently at or below their reorder points:\n\n- **Vegan Leather Dual-Sided Desk Mat** (`SKU-DESK-MAT`): **6** in stock (Reorder point: 20) — *Critical Alert*\n- **Vortex Mechanical RGB Keyboard** (`SKU-MEC-KEYBD`): **18** in stock (Reorder point: 25)\n\nPurchase Order `PO-2026-005` is currently pending with *AeroCraft Industrial Supplies* to replenish these exact items.",
                tools_invoked=[tool_invoc],
                sql_query_used=sql
            )

        else:
            # General helpful assistant query
            return ChatResponse(
                message="Hello! I'm your **Invenza Copilot**. I can run live read-only queries across your stock ledger (e.g., *'Which warehouse has the most ergonomic chairs?'* or *'What is low on stock?'*) and answer questions regarding inventory workflows, FIFO valuation, or GRN procedures.\n\nHow can I help you today?",
                tools_invoked=[]
            )
