# Deploy Runbook

## Normal flow (automatic)

Push to `main` triggers CI:
1. Backend lint (ruff)
2. Backend tests (pytest + Postgres + Redis)
3. Frontend build (Next.js)
4. Deploy job: SSH → git pull → alembic upgrade → docker compose build & restart → health check
5. Email notification on success/failure

## Manual deploy (if CI is down)

```bash
ssh root@188.245.85.248
cd /opt/invention-index-8
git pull origin main
docker compose exec backend alembic upgrade head
docker compose up -d --build backend worker beat frontend
```

Wait 30s, then verify:

```bash
curl -s http://localhost:8080/health | python3 -m json.tool
curl -sI https://inventionindex8.com | head -3
```

## Rollback

If the latest deploy breaks production:

```bash
ssh root@188.245.85.248
cd /opt/invention-index-8
git log --oneline -3  # find the last known-good commit
git checkout <good-commit-hash>
docker compose up -d --build backend worker beat frontend
```

## Deploy key setup

1. Generate a fresh key pair (do NOT reuse personal keys):
   ```bash
   ssh-keygen -t ed25519 -C "ci-deploy@inventionindex8.com" -f ~/.ssh/id_ed25519_ci_deploy
   ```

2. Add public key to Hetzner:
   ```bash
   cat ~/.ssh/id_ed25519_ci_deploy.pub | ssh root@188.245.85.248 "cat >> /root/.ssh/authorized_keys"
   ```

3. Add private key to GitHub Secrets:
   - `DEPLOY_KEY`: contents of `~/.ssh/id_ed25519_ci_deploy`
   - `DEPLOY_HOST`: `188.245.85.248`
   - `RESEND_API_KEY`: your Resend API key for deploy notifications

## Troubleshooting

### Frontend 502 / MODULE_NOT_FOUND

Root cause: `npm install` was run on the host (Ubuntu), creating `frontend/node_modules/` with native binaries incompatible with the Alpine container.

Fix:
```bash
rm -rf /opt/invention-index-8/frontend/node_modules
docker compose down frontend
docker compose up -d --build frontend
```

### Worker unhealthy / deepseek_api_key not configured

The `DEEPSEEK_API_KEY` in `app.env` was a placeholder (`sk-REPLACE_WITH_YOUR_KEY`).

Fix:
```bash
python3 -c "f=open('/opt/invention-index-8/app.env');l=f.readlines();f.close();l[53]='DEEPSEEK_API_KEY=your-real-key\n';f=open('/opt/invention-index-8/app.env','w');f.writelines(l);f.close()"
docker compose up -d --force-recreate worker
```

### Alembic migration conflicts

If `alembic upgrade head` fails:
```bash
docker compose exec backend alembic current   # check current revision
docker compose exec backend alembic history   # view migration chain
docker compose exec backend alembic upgrade +1 # step one at a time
```
