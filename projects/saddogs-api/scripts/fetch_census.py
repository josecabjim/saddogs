import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def fetch_all():
    resp = supabase.table("census").select("*").execute()
    print("status:", getattr(resp, "status_code", None))
    print("error:", getattr(resp, "error", None))
    print("data:", getattr(resp, "data", None))
    return resp


if __name__ == "__main__":
    fetch_all()
