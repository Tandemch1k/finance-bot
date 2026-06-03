import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

from models import Transaction, Budget

DATA_FILE = "data.json"


def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"transactions": [], "budgets": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Transactions ──────────────────────────────────────────────────────────────

def add_transaction(user_id: int, type_: str, amount: float,
                    category: str, note: str, date: str) -> Transaction:
    data = _load()
    tx = Transaction(
        id=str(uuid.uuid4())[:8],
        user_id=user_id,
        type=type_,
        amount=amount,
        category=category,
        note=note,
        date=date,
    )
    data["transactions"].append(tx.to_dict())
    _save(data)
    return tx


def get_transactions(user_id: int,
                     month: Optional[str] = None) -> List[Transaction]:
    data = _load()
    txs = [Transaction.from_dict(t) for t in data["transactions"]
           if t["user_id"] == user_id]
    if month:
        txs = [t for t in txs if t.date.startswith(month)]
    return sorted(txs, key=lambda t: t.date, reverse=True)


def delete_transaction(user_id: int, tx_id: str) -> bool:
    data = _load()
    before = len(data["transactions"])
    data["transactions"] = [
        t for t in data["transactions"]
        if not (t["user_id"] == user_id and t["id"] == tx_id)
    ]
    if len(data["transactions"]) < before:
        _save(data)
        return True
    return False


# ── Budgets ───────────────────────────────────────────────────────────────────

def set_budget(user_id: int, category: str, amount: float, month: str) -> Budget:
    data = _load()
    # Upsert: remove existing for same user/category/month
    data["budgets"] = [
        b for b in data["budgets"]
        if not (b["user_id"] == user_id and
                b["category"] == category and
                b["month"] == month)
    ]
    budget = Budget(user_id=user_id, category=category,
                    amount=amount, month=month)
    data["budgets"].append(budget.to_dict())
    _save(data)
    return budget


def get_budgets(user_id: int, month: str) -> List[Budget]:
    data = _load()
    return [Budget.from_dict(b) for b in data["budgets"]
            if b["user_id"] == user_id and b["month"] == month]
