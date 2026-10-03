# saddogs_database/repositories/census.py

from typing import Dict, Optional

from supabase import create_client


class CensusRepository:
    def __init__(self, url: str, key: str):
        self.client = create_client(url, key)

    def get_all(self):
        response = (
            self.client.table("census")
            .select("*")
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    def get_latest(self) -> Optional[Dict]:
        response = (
            self.client.table("census")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data
        return data[0] if data else None

    def save(self, data: Dict):
        return self.client.table("census").upsert(data).execute()

    def get_latest_clean(self) -> Optional[Dict]:
        """Most recent row ignoring needs_review rows."""
        response = (
            self.client.table("census")
            .select("*")
            .eq("needs_review", False)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data
        return data[0] if data else None

    def get_recent_needs_review(self, since_iso: str) -> list[Dict]:
        response = (
            self.client.table("census")
            .select("*")
            .eq("needs_review", True)
            .gte("created_at", since_iso)
            .execute()
        )
        return response.data or []
