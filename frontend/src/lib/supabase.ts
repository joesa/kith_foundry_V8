import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://mnrijzampgecdloxzkbm.supabase.co";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ucmlqemFtcGdlY2Rsb3h6a2JtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzMTc3MDMsImV4cCI6MjA3MDg5MzcwM30.klSbM3Vbn8cuABRv7HB9LDx3490dd1eRCIgH2IKnKMg";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
