# saddogs_database/repositories/rescues.py

from datetime import date
from typing import Optional

from supabase import create_client


class RescueRepository:
    def __init__(self, url: str, key: str):
        self.client = create_client(url, key)

    def get_all(self):
        response = (
            self.client.table("rescues")
            .select("*")
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    def get_latest_count(self, rescue_name: str, island: str) -> Optional[int]:
        response = (
            self.client.table("rescues")
            .select("total_dogs")
            .eq("rescue_name", rescue_name)
            .eq("island", island)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data
        if not data:
            return None

        return data[0]["total_dogs"]

    def save_count(self, rescue_name: str, island: str, count: int):
        data = {
            "rescue_name": rescue_name,
            "island": island,
            "total_dogs": count,
        }

        return self.client.table("rescues").insert(data).execute()

    def get_rescues_missing_for_date(
        self,
        known_pairs: list[tuple[str, str]],  # [(rescue_name, island), ...]
        for_date: date | None = None,
    ) -> list[tuple[str, str]]:
        """Return (rescue_name, island) pairs from known_pairs with no row today."""
        from datetime import date as date_type

        for_date = for_date or date_type.today()
        start = f"{for_date}T00:00:00"
        end = f"{for_date}T23:59:59"

        response = (
            self.client.table("rescues")
            .select("rescue_name, island")
            .gte("created_at", start)
            .lte("created_at", end)
            .execute()
        )

        scraped_today = {(row["rescue_name"], row["island"]) for row in response.data}

        return [pair for pair in known_pairs if pair not in scraped_today]
        return [pair for pair in known_pairs if pair not in scraped_today]
