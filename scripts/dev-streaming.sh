#!/bin/bash

echo "🚀 Starting Streaming Stack with Podman Compose..."
cd "$(dirname "$0")/../streaming" || exit 1

# Optional cleanup before starting
echo "🧼 Cleaning dangling containers (if any)..."
podman-compose -f docker-compose-streaming.yml down --volumes

# Build and start
echo "🔧 Building & launching containers..."
podman-compose -f docker-compose-streaming.yml up -d --build

# Wait a few seconds for network stabilization
echo "⏳ Waiting for services to initialize..."
sleep 10

# Health check summary
echo "📋 Current running containers:"
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

echo "✅ Streaming environment is now running!"
