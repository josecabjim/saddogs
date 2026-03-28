# saddogs_database/client.py

import os

from .repositories.census import CensusRepository
from .repositories.rescues import RescueRepository


class DatabaseClient:
    def __init__(self):
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

        self.rescues = RescueRepository(url, key)
        self.census = CensusRepository(url, key)
