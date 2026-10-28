import sqlite3

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers(
  id TEXT PRIMARY KEY, name TEXT, phone_masked TEXT, email_masked TEXT,
  monthly_income REAL, credit_score INTEGER, consent_personalization INTEGER,
  preferred_language TEXT, city TEXT);
CREATE TABLE IF NOT EXISTS accounts(
  id TEXT PRIMARY KEY, customer_id TEXT, type TEXT, number_masked TEXT,
  balance REAL, currency TEXT DEFAULT 'INR');
CREATE TABLE IF NOT EXISTS transactions(
  id TEXT PRIMARY KEY, account_id TEXT, date TEXT, description TEXT,
  category TEXT, amount REAL, balance_after REAL);
CREATE TABLE IF NOT EXISTS cards(
  id TEXT PRIMARY KEY, customer_id TEXT, last4 TEXT, type TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS loans(
  id TEXT PRIMARY KEY, customer_id TEXT, type TEXT, principal REAL, emi REAL,
  outstanding REAL, rate REAL);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
