"""Project paths and database settings (read from environment / .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"

# Load order respects foreign keys (parents before children).
TABLES: tuple[str, ...] = (
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "returns",
)

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class DbSettings:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> DbSettings:
        password = os.getenv("POSTGRES_PASSWORD")
        if not password:
            raise RuntimeError("POSTGRES_PASSWORD is not set. Copy .env.example to .env first.")
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "summitbase"),
            user=os.getenv("POSTGRES_USER", "summitbase"),
            password=password,
        )

    def conninfo(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )
