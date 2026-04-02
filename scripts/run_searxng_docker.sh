#!/usr/bin/env bash
# Spin up your own SearXNG — unlimited meta-search across 70+ engines
docker run -d \
  --name searxng \
  --restart unless-stopped \
  -p 8888:8080 \
  -e SEARXNG_HOSTNAME=localhost \
  searxng/searxng:latest

echo "SearXNG running at http://localhost:8888"
echo "Set SEARXNG_URL=http://localhost:8888 in your .env"
