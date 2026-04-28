# Nursery Management and monitoring


* This document describes the nursery management frappe application. 
* See [baseline requirements](docs/BASELINE_REQUIREMENTS.md) for a list of original requirements. 
* The app has evolved since the baseline, so make sure you check out everyting in [AGENTS.md](./AGENTS.md) for further instructions. 

## Running the app

```console
# From repo root
$ sudo systemctl stop mariadb redis-server 
$ docker compose -f docker/step0_docker-compose.yml up -d
$ docker logs nursery_frappe --follow
```

Then go to `http://nursery.localhost:8000/app/species`
This assumes a few things. 
If it is the first time running the app, run
```console
$ docker/init.sh
```
See [docs/INSTALLATION.md](docs/INSTALLATION.md) for more details.


