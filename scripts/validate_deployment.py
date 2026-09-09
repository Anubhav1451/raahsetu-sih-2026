"""Static deployment contract checks that do not require Docker or a cluster."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Deployment validation failed: {message}")


def main() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose.get("services", {})
    require({"backend", "frontend"} <= services.keys(), "Compose needs backend and frontend")
    for name in ("backend", "frontend"):
        require("no-new-privileges:true" in services[name].get("security_opt", []), f"{name} must block privilege escalation")

    resources = list(yaml.safe_load_all((ROOT / "deploy/k8s/base.yaml").read_text(encoding="utf-8")))
    deployments = {item["metadata"]["name"]: item for item in resources if item.get("kind") == "Deployment"}
    services_by_name = {item["metadata"]["name"]: item for item in resources if item.get("kind") == "Service"}
    require({"backend", "frontend"} <= deployments.keys(), "Kubernetes needs both deployments")
    require({"backend", "frontend"} <= services_by_name.keys(), "Kubernetes needs both services")
    for name, deployment in deployments.items():
        pod = deployment["spec"]["template"]["spec"]
        container = pod["containers"][0]
        require(pod.get("automountServiceAccountToken") is False, f"{name} must not mount a cluster token")
        require(pod.get("securityContext", {}).get("runAsNonRoot") is True, f"{name} must run as non-root")
        security = container.get("securityContext", {})
        require(security.get("allowPrivilegeEscalation") is False, f"{name} must block privilege escalation")
        require(security.get("capabilities", {}).get("drop") == ["ALL"], f"{name} must drop capabilities")
        require("readinessProbe" in container and "livenessProbe" in container, f"{name} needs health probes")
        require("requests" in container.get("resources", {}) and "limits" in container.get("resources", {}), f"{name} needs resource bounds")

    ingress_docs = list(yaml.safe_load_all((ROOT / "deploy/k8s/ingress.example.yaml").read_text(encoding="utf-8")))
    require(len(ingress_docs) == 1 and ingress_docs[0].get("kind") == "Ingress", "ingress template must parse")
    print("PASS: Compose and Kubernetes deployment contracts are structurally valid")


if __name__ == "__main__":
    main()
