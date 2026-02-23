docker compose exec -it openclaw-gateway bash
docker compose exec -it openclaw-gateway node dist/index.js tui
docker compose exec -it openclaw-gateway node dist/index.js configure
docker compose exec -it openclaw-gateway node dist/index.js chennels add


