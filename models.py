from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


EXPENSE_CATEGORIES = [
    "🍔 Еда",
    "🚗 Транспорт",
    "🏠 Жильё",
    "💊 Здоровье",
    "🎮 Развлечения",
    "👗 Одежда",
    "📱 Связь",
    "✈️ Путешествия",
    "📚 Образование",
    "💼 Бизнес",
    "🎁 Подарки",
    "🔧 Прочее",
]

INCOME_CATEGORIES = [
    "💰 Зарплата",
    "🏢 Аренда",
    "📈 Инвестиции",
    "🤝 Комиссия",
    "🎲 Прочее",
]


@dataclass
class Transaction:
    id: str
    user_id: int
    type: str          # "income" | "expense"
    amount: float
    category: str
    note: str
    date: str          # ISO format: "2026-06-03"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(**data)


@dataclass
class Budget:
    user_id: int
    category: str
    amount: float
    month: str         # "2026-06"

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(**data)
