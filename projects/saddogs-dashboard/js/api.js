import { SUPABASE_URL, SUPABASE_KEY, ABSOLUTE_START } from './config.js';

const { createClient } = window.supabase;
export const db = createClient(SUPABASE_URL, SUPABASE_KEY);

export async function fetchAllData() {
  const [{ data: census, error: censusError }, { data: rescues, error: rescuesError }] = await Promise.all([
    db.from("census")
      .select("*")
      .gte("created_at", ABSOLUTE_START)
      .order("created_at", { ascending: true }),

    db.from("rescues")
      .select("*")
      .gte("created_at", ABSOLUTE_START)
      .order("created_at", { ascending: true }),
  ]);

  if (censusError) throw censusError;
  if (rescuesError) throw rescuesError;

  return { census, rescues };
}