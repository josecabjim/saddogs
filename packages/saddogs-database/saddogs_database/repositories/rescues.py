# saddogs_database/repositories/rescues.py

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
