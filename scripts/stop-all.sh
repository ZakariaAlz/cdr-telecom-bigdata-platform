#!/bin/bash
set -e

echo "🛑 Stopping ALL containers from both stacks..."
podman-compose -f docker-compose-batch.yml down
podman-compose -f docker-compose-streaming.yml down
echo "✅ All services stopped."
