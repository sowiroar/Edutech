CREATE TABLE IF NOT EXISTS telemetry_sessions (
 id uuid PRIMARY KEY, context jsonb NOT NULL, started_at timestamptz NOT NULL,
 last_seen_at timestamptz NOT NULL DEFAULT now(), ended_at timestamptz, end_reason text
);
CREATE TABLE IF NOT EXISTS telemetry_events (
 event_id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES telemetry_sessions(id),
 occurred_at timestamptz NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
 type text NOT NULL, source text NOT NULL, data jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS telemetry_events_session_time ON telemetry_events(session_id,received_at,event_id);
CREATE INDEX IF NOT EXISTS telemetry_sessions_environment_time ON telemetry_sessions((context->>'environment'),started_at);
CREATE TABLE IF NOT EXISTS pricing_rates (
 id text PRIMARY KEY, provider text NOT NULL, model text NOT NULL, unit text NOT NULL,
 direction text NOT NULL, modality text NOT NULL, cached boolean NOT NULL DEFAULT false,
 effective_at timestamptz NOT NULL, usd_per_unit numeric NOT NULL CHECK(usd_per_unit>=0), source_url text NOT NULL,
 UNIQUE(provider,model,unit,direction,modality,cached,effective_at)
);
CREATE TABLE IF NOT EXISTS usage_ledger (
 event_id uuid NOT NULL REFERENCES telemetry_events(event_id), entry_index integer NOT NULL,
 session_id uuid NOT NULL REFERENCES telemetry_sessions(id), provider text NOT NULL, model text NOT NULL,
 purpose text NOT NULL, request_id text, attempt integer, unit text NOT NULL, direction text NOT NULL,
 modality text NOT NULL, cached boolean NOT NULL, quantity numeric NOT NULL CHECK(quantity>=0),
 accounting_source text NOT NULL, rate_id text REFERENCES pricing_rates(id), cost_usd numeric,
 cost_status text NOT NULL, PRIMARY KEY(event_id,entry_index)
);
CREATE INDEX IF NOT EXISTS usage_ledger_session ON usage_ledger(session_id);
