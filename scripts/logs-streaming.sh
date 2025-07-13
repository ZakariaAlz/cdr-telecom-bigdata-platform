#!/bin/bash
echo "📦 Showing logs for streaming services..."
podman-compose -f docker-compose-streaming.yml logs -f
