FROM postgres:15

WORKDIR /db

COPY init.sql .

RUN apt-get update && apt-get install -y gettext-base

RUN envsubst < /db/init.sql > /docker-entrypoint-initdb.d/init.sql

RUN cat <<EOF > /etc/postgresql/postgresql.conf
hba_file = '/etc/postgresql/pg_hba.conf'
listen_addresses = '*'
port = 
archive_mode = on
archive_command = 'cp %p /oracle/pg_data/archive/%f'
max_wal_senders = 10
wal_level = replica
wal_log_hints = on
log_replication_commands = on
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql/'
log_filename = 'postgresql-15-main.log'
log_timezone = 'Europe/Moscow'
EOF

RUN cat <<EOF > /etc/postgresql/pg_hba.conf
local all postgres peer
host all all 0.0.0.0/0 password
host replication repl_user 0.0.0.0/0 scram-sha-256
EOF

ENTRYPOINT [ "bash", "-c", "docker-entrypoint.sh -c config_file=/etc/postgresql/postgresql.conf"]