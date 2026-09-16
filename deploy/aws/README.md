# AURA AWS deployment notes

Production diagnosis jobs must use `DIAGNOSIS_EXECUTION=database`. This keeps
PyTorch and YOLO out of the Gunicorn web workers and lets a single durable
worker process the job.

## Install application and CPU inference dependencies

Run from `/srv/aura` with the virtual environment already created:

```bash
sudo dnf install -y mesa-libGL
bash deploy/aws/install_dependencies.sh
```

The installer uses the official PyTorch CPU wheel index, then installs the
application requirements. `ultralytics` is pinned to the version recorded in
`models/best.pt`.

## Install the diagnosis worker

```bash
sudo cp deploy/aws/aura-diagnosis-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aura-diagnosis-worker
```

The production environment file must include:

```dotenv
DIAGNOSIS_PROVIDER=hybrid
AURA_YOLO_WEIGHTS=/srv/aura/models/best.pt
AURA_YOLO_CONF=0.35
AURA_YOLO_DEVICE=cpu
DIAGNOSIS_EXECUTION=database
DIAGNOSIS_LEASE_SECONDS=300
DIAGNOSIS_MAX_ATTEMPTS=3
```

Verify both services after every deployment:

```bash
sudo systemctl status aura --no-pager
sudo systemctl status aura-diagnosis-worker --no-pager
sudo journalctl -u aura-diagnosis-worker -n 100 --no-pager
curl -fsS http://127.0.0.1:8000/health/
```
