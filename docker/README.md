# Docker

| File | Purpose |
|------|---------|
| `Dockerfile.ci` | PR agent: Python, gcc, cmake, ninja, lcov/gcovr |
| `Dockerfile.jenkins` | optional local Jenkins controller |
| `docker-compose.yml` | `sil-ci` service + optional `jenkins` profile |

## Run the CI image locally

```bash
docker compose -f docker/docker-compose.yml run --rm sil-ci
```

That executes `scripts/run_local.sh` inside the image (build, GTest, pytest, SIL run, publish mock).

## Jenkins profile

```bash
docker compose -f docker/docker-compose.yml --profile jenkins up -d jenkins
```

See [docs/jenkins.md](../docs/jenkins.md).
