CREATE TABLE IF NOT EXISTS users (
  user_id STRING PRIMARY KEY,
  email STRING,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
  user_id STRING PRIMARY KEY,
  refresh_token_enc STRING,
  updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS conversations (
  conversation_id STRING PRIMARY KEY,
  user_id STRING,
  title STRING,
  state STRING DEFAULT 'idle',
  latest_plan_id STRING,
  pending_goal STRING,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS messages (
  message_id STRING PRIMARY KEY,
  conversation_id STRING,
  user_id STRING,
  role STRING,
  content STRING,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS plans (
  plan_id STRING PRIMARY KEY,
  conversation_id STRING,
  user_id STRING,
  goal STRING,
  start_date DATE,
  num_days INTEGER,
  minutes_per_day INTEGER,
  plan_json VARIANT,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS deployments (
  deployment_id STRING PRIMARY KEY,
  user_id STRING,
  conversation_id STRING,
  plan_id STRING,
  tasklist_id STRING,
  tasklist_title STRING,
  created_count INTEGER DEFAULT 0,
  updated_count INTEGER DEFAULT 0,
  deployed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  last_synced_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS deployed_tasks (
  deployment_id STRING,
  user_id STRING,
  conversation_id STRING,
  plan_id STRING,
  source_task_key STRING,
  google_task_id STRING,
  due_date DATE,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (deployment_id, source_task_key)
);

CREATE TABLE IF NOT EXISTS agent_traces (
  trace_id STRING PRIMARY KEY,
  plan_id STRING,
  conversation_id STRING,
  user_id STRING,
  agent_name STRING,
  prompt STRING,
  response STRING,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
