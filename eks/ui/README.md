# Employee Directory UI

A colorful static web UI for the Flask employee API (`../app.py`), served by
nginx. nginx also reverse-proxies `/api/*` to the backend `python-app` service,
so the browser only ever talks to one origin — **no CORS setup needed** and only
the UI is exposed through the ALB.

```
browser ──▶ ALB (Ingress) ──▶ employee-ui (nginx :8080)
                                     ├─ /            → static index.html
                                     └─ /api/*       → python-app.dev:8080/*
```

## Files
| File | Purpose |
|------|---------|
| `index.html`     | The UI (add + list employees) |
| `nginx.conf`     | Static serving + `/api/` reverse proxy to the backend |
| `dockerfile`     | nginx:alpine image |
| `deployment.yaml`| Deployment (namespace `dev`) |
| `svc.yaml`       | ClusterIP Service (:80 → :8080) |
| `ingress.yaml`   | ALB Ingress for the AWS Load Balancer Controller |

## Build & push (adjust account/region/repo)
```bash
REPO=150390106962.dkr.ecr.eu-west-2.amazonaws.com/employee-ui
aws ecr get-login-password --region eu-west-2 \
  | docker login --username AWS --password-stdin 150390106962.dkr.ecr.eu-west-2.amazonaws.com

# create the repo once
aws ecr create-repository --repository-name employee-ui --region eu-west-2 || true

docker build -t $REPO:v1 -f dockerfile .
docker push $REPO:v1
```

## Deploy
```bash
kubectl apply -f deployment.yaml
kubectl apply -f svc.yaml
kubectl apply -f ingress.yaml

# get the ALB address (takes ~1-2 min to provision)
kubectl get ingress employee-ui -n dev -w
```

Open the `ADDRESS` shown for the ingress in your browser.

## Notes
- The backend never needs to be exposed publicly — keep `python-app`'s Service
  as `ClusterIP`. The UI reaches it in-cluster via the nginx proxy.
- If you rename the backend Service or namespace, update the `proxy_pass`
  target in `nginx.conf` (`python-app.dev.svc.cluster.local:8080`).
- The AWS Load Balancer Controller must already be installed in the cluster,
  and public subnets tagged `kubernetes.io/role/elb=1` for an
  `internet-facing` ALB.
