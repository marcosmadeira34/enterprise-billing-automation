-- =============================================================================
-- EBA — Inicialização do banco de dados
-- Executado automaticamente pelo PostgreSQL na primeira inicialização
-- =============================================================================

-- Banco de teste (para CI e testes locais)
CREATE DATABASE eba_test
    WITH
    OWNER = eba_user
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- Extensões obrigatórias
\c eba_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- Criptografia
CREATE EXTENSION IF NOT EXISTS "unaccent";     -- Busca sem acentos
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Busca por similaridade (trigrams)

\c eba_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

