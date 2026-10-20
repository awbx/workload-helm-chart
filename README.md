# workload-helm-chart

[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/workload)](https://artifacthub.io/packages/search?repo=workload)

A generic Helm chart for deploying any containerised service on Kubernetes:
web apps, APIs, background workers and stateful services. Use the same chart
for every service and override only the values you need for each one.

```sh
helm install my-api oci://ghcr.io/awbx/charts/workload --version 2.1.0 \
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
| PodDisruptionBudget | `pdb.enabled: true` |
| PodMonitor or ServiceMonitor | `metrics.enabled: true` and the Prometheus Operator CRDs are installed |
| Anything else | `extraObjects` |

The defaults meet the `restricted`
[Pod Security Standard](https://kubernetes.io/docs/concepts/security/pod-security-standards/):
non-root, `RuntimeDefault` seccomp, no privilege escalation, all capabilities
dropped and no service account token. A typo in a value name fails
`helm install` instead of being silently ignored, because the chart ships a
`values.schema.json`.

### Verifying the signature

Every release is signed with [cosign](https://github.com/sigstore/cosign)
keyless signing from the release workflow:

```sh
cosign verify ghcr.io/awbx/charts/workload:2.1.0 \
  --certificate-identity-regexp '^https://github.com/awbx/workload-helm-chart/\.github/workflows/release\.yaml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Examples

Ready-to-use values files are in [`examples/`](https://github.com/awbx/workload-helm-chart/tree/main/examples):

- [`web-api.yaml`](https://github.com/awbx/workload-helm-chart/blob/main/examples/web-api.yaml): API behind an Ingress with TLS, probes, CPU autoscaling and env from a Secret
- [`gateway-api.yaml`](https://github.com/awbx/workload-helm-chart/blob/main/examples/gateway-api.yaml): frontend exposed through a Gateway API HTTPRoute
- [`stateful.yaml`](https://github.com/awbx/workload-helm-chart/blob/main/examples/stateful.yaml): single replica with a ReadWriteOnce volume, `Recreate` strategy, custom args and a fixed non-root user

```sh
helm install my-api oci://ghcr.io/awbx/charts/workload -f examples/web-api.yaml
```

A production-style service, using most features:

```yaml
image:
  repository: ghcr.io/example/api
  tag: "2.4.1"
service:
  port: 80
containerPort: 8080          # Service 80 -> container 8080
replicaCount: 3
probes:
  http:
    path: /healthz           # liveness + readiness on the http port
lifecycle:
  preStop:
    sleep:
      seconds: 5             # let the gateway stop routing first
pdb:
  enabled: true
  maxUnavailable: 1
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
metrics:
  enabled: true
  port: 9090
secretRefs:
  - api-env
  - name: api-db-credentials # created later by an operator
    optional: true
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
    semver: "2.x"
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
  targetRevision: 2.1.0
  helm:
    valuesObject:
      image:
        repository: ghcr.io/example/api
        tag: "2.4.1"
```

## Values

Values marked *pass-through* are copied into the manifest as written, using
the Kubernetes field of the same name. Default maps can be trimmed by setting
a key to `null`, for example `--set podSecurityContext.runAsNonRoot=null` or
`resources: null`. The metrics monitor is rendered only when the
`monitoring.coreos.com/v1` API exists; with `helm template`, pass
`--api-versions monitoring.coreos.com/v1`.

The tables below are generated from
[`values.schema.json`](https://github.com/awbx/workload-helm-chart/blob/main/charts/workload/values.schema.json),
which also validates every value at install time.

<!-- values:start -->

### Image and replicas

| Key | Default | Description |
|---|---|---|
| `image.repository` | `"docker.io/nginxinc/nginx-unprivileged"` | Image repository, including the registry. |
| `image.tag` | `"stable-alpine"` | Image tag. The chart `appVersion` when empty. |
| `image.digest` | `""` | Image digest (`sha256:...`). Wins over `tag`; use it for images whose data format depends on the exact version. |
| `image.pullPolicy` | `"IfNotPresent"` | Image pull policy. |
| `global.imagePullSecrets` | `[]` | Pull secret names (plain strings) shared across releases. When set, wins over `imagePullSecrets`. |
| `imagePullSecrets` | `[]` | Pull secrets for this release, as `- name: my-secret` entries. |
| `replicaCount` | `1` | Number of replicas. Ignored when `autoscaling.enabled` is true. |
| `revisionHistoryLimit` | `10` | Old ReplicaSets kept for `kubectl rollout undo`. |
| `strategy` | `{}` | Deployment update strategy. Use `type: Recreate` for pods holding a ReadWriteOnce volume. |
| `nameOverride` | `""` | Replaces the chart name (`workload`) in resource names. |
| `fullnameOverride` | `""` | Replaces the full resource name (`<release>-workload`). |

### Container

| Key | Default | Description |
|---|---|---|
| `command` | `[]` | Overrides the image `ENTRYPOINT`. |
| `args` | `[]` | Overrides the image `CMD`. |
| `env` | `[]` | Environment variables (pass-through), each with a `name` and a `value` or `valueFrom`. |
| `configMapRefs` | `[]` | ConfigMaps loaded with `envFrom`: a name, or `{name, optional}` for one that may not exist yet. |
| `secretRefs` | `[]` | Secrets loaded with `envFrom`: a name, or `{name, optional}` for one created later (e.g. by an operator). |
| `containerPort` | `""` | Port the container listens on, named `http`. `service.port` when empty. |
| `resources` | `{"requests": {"cpu": "50m", "memory": "64Mi"}}` | Container resources. Set to null for none. |
| `securityContext` | `{"allowPrivilegeEscalation": false, "capabilities": {"drop": ["ALL"]}}` | Security context of the main container (pass-through). Add capabilities back under `capabilities.add`. |
| `probes.http.path` | `""` | When set, renders HTTP liveness and readiness probes on this path. |
| `probes.http.port` | `"http"` | Port of the shortcut probes, by name or number. |
| `startupProbe` | `{}` | Startup probe (pass-through). |
| `livenessProbe` | `{}` | Liveness probe (pass-through). Wins over `probes.http`. |
| `readinessProbe` | `{}` | Readiness probe (pass-through). Wins over `probes.http`. |
| `lifecycle` | `{}` | Container lifecycle hooks, e.g. a `preStop` sleep so a gateway stops routing before shutdown. |
| `volumeMounts` | `[]` | Volume mounts of the main container (pass-through). |
| `initContainers` | `[]` | Init containers (pass-through, templated). |
| `extraContainers` | `[]` | Sidecar containers (pass-through, templated). |

### Pod

| Key | Default | Description |
|---|---|---|
| `podAnnotations` | `{}` | Pod annotations. |
| `podLabels` | `{}` | Extra pod labels. |
| `commonAnnotations` | `{}` | Annotations added to every resource and to the pod. |
| `podSecurityContext` | `{"runAsNonRoot": true, "seccompProfile": {"type": "RuntimeDefault"}}` | Pod security context (pass-through). The default meets the `restricted` Pod Security Standard; set a key to null to drop it. |
| `priorityClassName` | `""` | PriorityClass of the pod. |
| `terminationGracePeriodSeconds` | `30` | Seconds between SIGTERM and SIGKILL. |
| `volumes` | `[]` | Pod volumes (pass-through, templated), each with a `name`. |
| `nodeSelector` | `{}` | Node labels the pod must run on. |
| `tolerations` | `[]` | Tolerations (pass-through). |
| `affinity` | `{}` | Affinity rules (pass-through). |
| `topologySpreadConstraints` | `[]` | Spread constraints (pass-through). `labelSelector` defaults to this release's pods. |

### Service account

| Key | Default | Description |
|---|---|---|
| `serviceAccount.create` | `true` | Create a ServiceAccount for this release. |
| `serviceAccount.automount` | `false` | Mount the service account token into the pod. Only needed by applications that call the Kubernetes API. |
| `serviceAccount.annotations` | `{}` | ServiceAccount annotations, e.g. for cloud IAM roles. |
| `serviceAccount.name` | `""` | ServiceAccount name. The release fullname when creating, `default` when not. |

### Networking

| Key | Default | Description |
|---|---|---|
| `service.type` | `"ClusterIP"` | Service type. |
| `service.port` | `8080` | Service port. Also the container port unless `containerPort` is set. |
| `ingress.enabled` | `false` | Render an Ingress. |
| `ingress.className` | `""` | IngressClass name. |
| `ingress.annotations` | `{}` | Ingress annotations. |
| `ingress.hosts` | `[{"host": "chart-example.local", "paths": [{"path": "/", "pathType": "Prefix"}]}]` | Hosts, each with a list of `paths` (`path`, `pathType`). |
| `ingress.tls` | `[]` | TLS entries, each with `secretName` and `hosts`. |
| `httpRoute.enabled` | `false` | Render an HTTPRoute. |
| `httpRoute.annotations` | `{}` | HTTPRoute annotations. |
| `httpRoute.parentRefs` | `[{"name": "gateway", "sectionName": "http"}]` | Gateways to attach to (pass-through), each with a `name`. |
| `httpRoute.hostnames` | `["chart-example.local"]` | Hostnames the route matches. |
| `httpRoute.rules` | `[{"matches": [{"path": {"type": "PathPrefix", "value": "/"}}]}]` | Rules with `matches`, `filters`, `timeouts` and `backendRefs`. A rule without `backendRefs` targets this release's Service. |

### Scaling and availability

| Key | Default | Description |
|---|---|---|
| `autoscaling.enabled` | `false` | Render a HorizontalPodAutoscaler. |
| `autoscaling.minReplicas` | `1` | Minimum replicas. |
| `autoscaling.maxReplicas` | `10` | Maximum replicas. |
| `autoscaling.targetCPUUtilizationPercentage` | `80` | Average CPU utilisation target, as a percentage of requests. |
| `autoscaling.targetMemoryUtilizationPercentage` | unset | Average memory utilisation target, as a percentage of requests. Unset by default. |
| `pdb.enabled` | `false` | Render a PodDisruptionBudget. |
| `pdb.minAvailable` | `""` | Number or percentage of pods that must stay up. Wins over `maxUnavailable`. |
| `pdb.maxUnavailable` | `""` | Number or percentage of pods that may be down. `1` when neither is set. |

### Metrics

| Key | Default | Description |
|---|---|---|
| `metrics.enabled` | `false` | Render a PodMonitor or ServiceMonitor. |
| `metrics.kind` | `"PodMonitor"` | Kind of monitor. |
| `metrics.port` | `""` | Metrics port, added to the pod and Service as `metrics`. The `http` port is scraped when empty. |
| `metrics.path` | `"/metrics"` | Scrape path. |
| `metrics.interval` | `"30s"` | Scrape interval. |
| `metrics.scrapeTimeout` | `""` | Scrape timeout. The Prometheus default when empty. |
| `metrics.labels` | `{}` | Extra labels on the monitor, e.g. the one your Prometheus selects on. |

### Extra manifests

| Key | Default | Description |
|---|---|---|
| `extraObjects` | `[]` | Extra manifests, as objects or strings. Both are templated. |

<!-- values:end -->

## Upgrading from 1.x to 2.0

2.0 changes defaults. Review these before upgrading an existing release:

- **Pods run as non-root.** Images that need root fail to start with
  `container has runAsNonRoot and image will run as root`. Set
  `podSecurityContext.runAsUser` to the image's user, or
  `podSecurityContext.runAsNonRoot: null` to go back to the old behaviour.
- **All capabilities are dropped and privilege escalation is off.** Add back
  what you need under `securityContext.capabilities.add`.
- **The service account token is not mounted.** Set
  `serviceAccount.automount: true` for applications that call the Kubernetes API.
- **Pods request 50m CPU and 64Mi memory.** Set `resources` to your own values,
  or `resources: null` for none.
- **The default image is `nginx-unprivileged` on port 8080** (was `nginx`, with
  `service.port: 3000`). This only matters if you relied on the default image
  or port; set `service.port` explicitly.

## Development

```sh
helm lint charts/workload -f charts/workload/ci/all-features-values.yaml
helm template test charts/workload -f charts/workload/ci/all-features-values.yaml \
  --api-versions monitoring.coreos.com/v1
```

`charts/workload/ci/all-features-values.yaml` turns on every feature; CI lints
and validates it with every example.

Value descriptions and validation live in `charts/workload/values.schema.json`,
defaults in `charts/workload/values.yaml`. After changing either, run
`scripts/gen-docs.py`: it copies the defaults into the schema and regenerates
the values tables above. CI runs it with `--check` and fails when the files are
out of date or a value has no description.

## Releasing

Bump `version` in `charts/workload/Chart.yaml`, update
`artifacthub.io/changes`, and merge to `main`. The release workflow pushes the
chart to `oci://ghcr.io/awbx/charts/workload` and creates a GitHub release
tagged `workload-<version>`.

## License

[MIT](https://github.com/awbx/workload-helm-chart/blob/main/LICENSE)
