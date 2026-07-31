#!/bin/sh
# Fix pg_hba.conf to allow scram-sha-256 from all hosts
cat > /var/lib/postgresql/data/pg_hba.conf << 'EOF'
local all all trust
host all all 0.0.0.0/0 scram-sha-256
host all all ::/0 scram-sha-256
EOF
# Set the password fresh (stored as scram-sha-256)
psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
# Reload config
pg_ctl reload -D /var/lib/postgresql/data
