"""Checkout paths shared by the offline data commands."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "fin"
