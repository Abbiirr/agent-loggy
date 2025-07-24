-- setup_database_ddl.sql
-- Simplified PostgreSQL DDL for agent_loggy



-- 1. Valid query keywords table
CREATE TABLE IF NOT EXISTS agent_loggy.valid_query_keywords (
    id SERIAL PRIMARY KEY,
    keyword     VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    context     TEXT,
    embedding   vector(384),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Valid domains table
CREATE TABLE IF NOT EXISTS agent_loggy.valid_domains (
    id SERIAL PRIMARY KEY,
    domain      VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    context     TEXT,
    embedding   vector(384),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Ignored logs table
CREATE TABLE IF NOT EXISTS agent_loggy.ignored_logs (
    id SERIAL PRIMARY KEY,
    method_name VARCHAR(255) NOT NULL,
    description TEXT,
    context     TEXT,
    embedding   vector(384),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Domain wise info table
CREATE TABLE IF NOT EXISTS agent_loggy.domain_wise_info (
    id             SERIAL PRIMARY KEY,
    domain         VARCHAR(100) NOT NULL,
    important_words TEXT[],
    ignored_words   TEXT[],
    description    TEXT,
    context        TEXT,
    embedding      vector(384),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain) REFERENCES agent_loggy.valid_domains(domain) ON DELETE CASCADE
);

-- 5. Method info table
CREATE TABLE IF NOT EXISTS agent_loggy.method_info (
    id           SERIAL PRIMARY KEY,
    method_name  VARCHAR(255) NOT NULL,
    domain       VARCHAR(100),
    description  TEXT,
    context      TEXT,
    embedding    vector(384),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain) REFERENCES agent_loggy.valid_domains(domain) ON DELETE SET NULL
);

-- 6. Prompts table
CREATE TABLE IF NOT EXISTS agent_loggy.prompts (
    id           SERIAL PRIMARY KEY,
    prompt_name  VARCHAR(255) NOT NULL UNIQUE,
    prompt       TEXT NOT NULL,
    description  TEXT,
    usage        TEXT,
    embedding    vector(384),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity indexes
CREATE INDEX idx_keywords_embedding      ON agent_loggy.valid_query_keywords USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_domains_embedding       ON agent_loggy.valid_domains        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_ignored_logs_embedding  ON agent_loggy.ignored_logs         USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_domain_info_embedding   ON agent_loggy.domain_wise_info     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_method_info_embedding   ON agent_loggy.method_info          USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_prompts_embedding       ON agent_loggy.prompts              USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Regular indexes for performance
CREATE INDEX idx_keywords_keyword       ON agent_loggy.valid_query_keywords(keyword);
CREATE INDEX idx_domains_domain         ON agent_loggy.valid_domains(domain);
CREATE INDEX idx_ignored_method_name    ON agent_loggy.ignored_logs(method_name);
CREATE INDEX idx_domain_info_domain     ON agent_loggy.domain_wise_info(domain);
CREATE INDEX idx_method_info_method     ON agent_loggy.method_info(method_name);
CREATE INDEX idx_method_info_domain     ON agent_loggy.method_info(domain);
CREATE INDEX idx_prompts_name           ON agent_loggy.prompts(prompt_name);

-- Timestamps indexes
CREATE INDEX idx_keywords_created_at    ON agent_loggy.valid_query_keywords(created_at DESC);
CREATE INDEX idx_domains_created_at     ON agent_loggy.valid_domains(created_at DESC);
CREATE INDEX idx_ignored_logs_created_at ON agent_loggy.ignored_logs(created_at DESC);
CREATE INDEX idx_domain_info_created_at ON agent_loggy.domain_wise_info(created_at DESC);
CREATE INDEX idx_method_info_created_at ON agent_loggy.method_info(created_at DESC);
CREATE INDEX idx_prompts_created_at     ON agent_loggy.prompts(created_at DESC);

-- Trigger function to auto‑update updated_at
CREATE OR REPLACE FUNCTION agent_loggy.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for each table
CREATE TRIGGER trg_valid_query_keywords_updated_at
  BEFORE UPDATE ON agent_loggy.valid_query_keywords
  FOR EACH ROW EXECUTE FUNCTION agent_loggy.update_updated_at_column();

CREATE TRIGGER trg_valid_domains_updated_at
  BEFORE UPDATE ON agent_loggy.valid_domains
  FOR EACH ROW EXECUTE FUNCTION agent_loggy.update_updated_at_column();

CREATE TRIGGER trg_ignored_logs_updated_at
  BEFORE UPDATE ON agent_loggy.ignored_logs
  FOR EACH ROW EXECUTE FUNCTION agent_loggy.update_updated_at_column();

CREATE TRIGGER trg_domain_wise_info_updated_at
  BEFORE UPDATE ON agent_loggy.domain_wise_info
  FOR EACH ROW EXECUTE FUNCTION agent_loggy.update_updated_at_column();

CREATE TRIGGER trg_method_info_updated_at
  BEFORE UPDATE ON agent_loggy.method_info
  FOR EACH ROW EXECUTE FUNCTION agent_loggy.update_updated_at_column();

CREATE TRIGGER trg_prompts_updated_at
  BEFORE UPDATE ON agent_loggy.prompts
  FOR EACH ROW EXECUTE FUNCTION agent_loggy.update_updated_at_column();

-- Optional view for method‑domain lookup
CREATE VIEW agent_loggy.method_domain_view AS
SELECT
  mi.id,
  mi.method_name,
  mi.domain,
  mi.description   AS method_description,
  vd.description   AS domain_description,
  mi.context,
  mi.created_at,
  mi.updated_at
FROM agent_loggy.method_info mi
LEFT JOIN agent_loggy.valid_domains vd
  ON mi.domain = vd.domain;
