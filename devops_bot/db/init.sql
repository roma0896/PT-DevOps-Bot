CREATE DATABASE db_bot;

\c db_bot;

CREATE TABLE IF NOT EXISTS emails (id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL);

CREATE TABLE IF NOT EXISTS phones (id SERIAL PRIMARY KEY, phone VARCHAR(20) NOT NULL);

CREATE USER repl_user REPLICATION LOGIN PASSWORD 'toor';

SELECT pg_create_physical_replication_slot('replication_slot');

CREATE TABLE hba ( lines text );
COPY hba FROM '/var/lib/postgresql/data/pg_hba.conf';
INSERT INTO hba (lines) VALUES ('host replication all 0.0.0.0/0 md5');
COPY hba TO '/var/lib/postgresql/data/pg_hba.conf';
SELECT pg_reload_conf();