# workload-helm-chart

A generic Helm chart for deploying any containerised service on Kubernetes:
web apps, APIs, background workers and stateful services. Use the same chart
for every service and override only the values you need for each one.

```sh
helm install my-api oci://ghcr.io/awbx/charts/workload --version 1.0.0 \
  --set image.repository=ghcr.io/example/api --set image.tag=2.4.1
```

## What it renders

| Resource | When |
|---|---|
| Deployment | always |
| Service | always |
| ServiceAccount | `serviceAccount.create: true` (default) |
| Ingress | `ingress.enabled: true` |
| HTTPRoute (Gateway API) | `httpRoute.enabled: true` |
| HorizontalPodAutoscaler | `autoscaling.enabled: true` |

## Examples

Ready-to-use values files are in [`examples/`](examples):

- [`web-api.yaml`](examples/web-api.yaml): API behind an Ingress with TLS, probes, CPU autoscaling and env from a Secret
- [`gateway-api.yaml`](examples/gateway-api.yaml): frontend exposed through a Gateway API HTTPRoute
- [`stateful.yaml`](examples/stateful.yaml): single replica with a ReadWriteOnce volume, `Recreate` strategy and custom args

```sh
helm install my-api oci://ghcr.io/awbx/charts/workload -f examples/web-api.yaml
```

### Flux

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: workload
spec:
  interval: 1h
  url: oci://ghcr.io/awbx/charts/workload
  ref:
    semver: "1.x"
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: my-api
spec:
  interval: 10m
  chartRef:
    kind: OCIRepository
    name: workload
  values:
    image:
      repository: ghcr.io/example/api
      tag: "2.4.1"
```

### Argo CD

```yaml
source:
  repoURL: ghcr.io/awbx/charts
  chart: workload
  targetRevision: 1.0.0
  helm:
    valuesObject:
      image:
        repository: ghcr.io/example/api
        tag: "2.4.1"
```

## Values

See [`charts/workload/values.yaml`](charts/workload/values.yaml) for the full,
commented list. The most commonly used values:

| Key | Default | Description |
|---|---|---|
| `image.repository` | `nginx` | Container image |
| `image.tag` | chart `appVersion` | Image tag |
| `image.digest` | `""` | `sha256:...` digest; takes precedence over `tag` |
| `replicaCount` | `1` | Ignored when autoscaling is enabled |
| `strategy` | `{}` | Deployment strategy; use `type: Recreate` with RWO volumes |
| `service.type` | `ClusterIP` | Service type |
| `service.port` | `3000` | Service port, also the container port (`http`) |
| `command` / `args` | `[]` | Override the image entrypoint / command |
| `env` | `[]` | Extra environment variables |
| `configMapRefs` / `secretRefs` | `[]` | ConfigMap / Secret names loaded with `envFrom` |
| `startupProbe` / `livenessProbe` / `readinessProbe` | `{}` | Probes, passed through as-is |
| `resources` | `{}` | Container resources |
| `ingress.enabled` | `false` | Render an Ingress |
| `httpRoute.enabled` | `false` | Render a Gateway API HTTPRoute |
| `autoscaling.enabled` | `false` | Render an HPA (CPU and/or memory targets) |
| `volumes` / `volumeMounts` | `[]` | Pod volumes and container mounts |
| `initContainers` | `[]` | Init containers |
| `commonAnnotations` | `{}` | Annotations added to every resource |
| `global.imagePullSecrets` | `[]` | Pull secret names shared across releases |
| `imagePullSecrets` | `[]` | Pull secrets for this release |
| `nodeSelector` / `tolerations` / `affinity` | `{}` / `[]` / `{}` | Scheduling |

## Releasing

Bump `version` in `charts/workload/Chart.yaml` and merge to `main`. The
release workflow pushes the chart to `oci://ghcr.io/awbx/charts/workload`
and creates a GitHub release tagged `workload-<version>`.

## License

[MIT](LICENSE)
