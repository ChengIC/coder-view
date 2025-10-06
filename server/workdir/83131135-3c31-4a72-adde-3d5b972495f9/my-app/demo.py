from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# print(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# insert a new row
# new_row = {
#     'first_name': 'John',
# }
# supabase.table("demo-table").insert(new_row).execute()

# update a row in the table
# update_row = {
#     'first_name': 'Jane Smith',
# }
# supabase.table("demo-table").update(update_row).eq('id', 3).execute()

# # delete a row in the table
# supabase.table("demo-table").delete().eq('id', 3).execute()

# # select all rows from the table
# response = supabase.table("demo-table").select("*").execute()

# print(response)


# response = supabase.storage.from_("demo-bucket").get_public_url("rc.png")

# print(response)