#!/bin/bash
echo "📦 Live logs for batch services (Press Ctrl+C to stop)..."
podman-compose -f docker-compose-batch.yml logs -f
