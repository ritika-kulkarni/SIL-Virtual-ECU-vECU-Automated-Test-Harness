# Jenkins setup

## Job

Create a Multibranch Pipeline (or a plain Pipeline) pointed at this repo. The root `Jenkinsfile` uses a `dockerfile` agent (`docker/Dockerfile.ci`), so the Jenkins host needs Docker available to agents.

Stages, roughly:

1. Checkout  
2. `pip install -e ".[dev]"`  
3. Python unit tests  
4. CMake + GTest for `vecu/`  
5. `sil-harness run` (reuses the build)  
6. Coverage HTML  
7. Publish to Artifactory  
8. Archive `artifacts/**` and attach the HTML report

## Credentials

Only needed when `config/harness.yaml` has `artifactory.mode: http`.

| Jenkins ID | Env vars | Purpose |
|------------|----------|---------|
| `artifactory-sil` | `ARTIFACTORY_USER`, `ARTIFACTORY_PASSWORD` | HTTP PUT to Artifactory |

With `mode: mock` (default), publish just copies into `artifacts/artifactory/` — no credentials.

## Local Jenkins (optional)

```bash
docker compose -f docker/docker-compose.yml --profile jenkins up -d jenkins
```

Then open http://localhost:8080 and wire the job to your clone. Mounting `docker.sock` lets the controller start the CI image; treat that as a lab convenience, not production hardening.

## WSL notes

- Run the Docker agent from WSL2 with Docker Desktop integration on.
- CANoe itself is Windows-only; keep Linux agents on `backend: python` and reserve a Windows node if you need COM.

## Gates

`sil-harness run` exits `2` when quality gates fail (pass rate / coverage). Thresholds are in `config/harness.yaml` under `thresholds:`. Use `--no-gate` only for local debugging.
