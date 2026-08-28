#!/usr/bin/env -S bash -l
# Exit immediately if a command exits with a non-zero status
set -e

echo "Initializing environment..."
echo "The configured database is: $DB_HOST"

# Execute the container's main command (CMD)
exec /app/recenter_brain.py "$@"
