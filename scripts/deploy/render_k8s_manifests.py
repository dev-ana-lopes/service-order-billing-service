#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SENSITIVE_KEYS = {
    "APPROVAL_TOKEN_SECRET",
    "APPROVAL_TOKEN_SECRET_FILE",
    "DATABASE_URL",
    "JWT_SECRET",
    "JWT_SECRET_FILE",
    "SMTP_PASSWORD",
    "SMTP_PASSWORD_FILE",
    "SMTP_USERNAME",
    "TESTMAIL_API_KEY",
    "CUSTOMER_JWT_SECRET",
    "CUSTOMER_JWT_SECRET_FILE",
    "DD_API_KEY",
    "MERCADO_PAGO_ACCESS_TOKEN",
    "MERCADO_PAGO_ACCESS_TOKEN_FILE",
    "MONGODB_URL",
    "RABBITMQ_URL",
}
REQUIRED_SECRET_KEYS = {
    "APPROVAL_TOKEN_SECRET",
    "DATABASE_URL",
    "JWT_SECRET",
    "CUSTOMER_JWT_SECRET",
}
STATIC_MANIFESTS = (
    "namespace.yaml",
    "job-migrate.yaml",
    "deployment.yaml",
    "service.yaml",
    "hpa.yaml",
    "ingress.yaml",
)
IMAGE_MANIFESTS = ("job-migrate.yaml", "deployment.yaml")
IMAGE_PLACEHOLDER = "__API_IMAGE__"
LEGACY_IMAGE_PLACEHOLDER = "${API_IMAGE}"
IMAGE_PLACEHOLDER_PATTERNS = (
    re.compile(r"\$\{[^}]+\}"),
    re.compile(r"__.+__"),
    re.compile(r"<[^>]+>"),
)


def parse_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def yaml_quote(value: str) -> str:
    return json.dumps(value)


def is_placeholder_like_image(value: str) -> bool:
    if "PLACEHOLDER" in value.upper():
        return True
    return any(pattern.fullmatch(value) for pattern in IMAGE_PLACEHOLDER_PATTERNS)


def normalize_image_ref(image: str) -> str:
    normalized = image.strip()
    if not normalized:
        raise SystemExit("The --image value must be a non-empty container image reference.")
    if any(char.isspace() for char in normalized):
        raise SystemExit("The --image value must not contain whitespace.")
    if is_placeholder_like_image(normalized):
        raise SystemExit(
            "The --image value must be a rendered container image reference, not a placeholder."
        )
    return normalized


def extract_image_values(content: str) -> list[str]:
    image_values: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("image:"):
            image_values.append(stripped.partition(":")[2].strip())
    return image_values


def validate_rendered_manifest_images(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    unresolved_tokens = (IMAGE_PLACEHOLDER, LEGACY_IMAGE_PLACEHOLDER)

    if any(token in content for token in unresolved_tokens):
        raise SystemExit(
            f"Rendered manifest {path.name} still contains an unresolved image placeholder."
        )

    image_values = extract_image_values(content)
    if not image_values:
        raise SystemExit(f"Rendered manifest {path.name} does not contain an image field.")

    for image_value in image_values:
        if not image_value:
            raise SystemExit(f"Rendered manifest {path.name} contains an empty image field.")
        if is_placeholder_like_image(image_value):
            raise SystemExit(
                f"Rendered manifest {path.name} still contains an unresolved image value: "
                f"{image_value}"
            )


def write_manifest(
    path: Path,
    *,
    kind: str,
    name: str,
    namespace: str,
    section_name: str,
    values: dict[str, str],
) -> None:
    lines = [
        "apiVersion: v1",
        f"kind: {kind}",
        "metadata:",
        f"  name: {name}",
        f"  namespace: {namespace}",
        "type: Opaque" if kind == "Secret" else None,
        f"{section_name}:",
    ]
    for key in sorted(values):
        lines.append(f"  {key}: {yaml_quote(values[key])}")

    path.write_text(
        "\n".join(line for line in lines if line is not None) + "\n",
        encoding="utf-8",
    )


def render_static_manifests(
    source_dir: Path,
    output_dir: Path,
    *,
    namespace: str,
    image: str,
) -> None:
    for manifest_name in STATIC_MANIFESTS:
        content = (source_dir / manifest_name).read_text(encoding="utf-8")
        content = content.replace("namespace: service-order", f"namespace: {namespace}")
        content = content.replace("name: service-order\n", f"name: {namespace}\n", 1)
        content = content.replace(IMAGE_PLACEHOLDER, image)
        content = content.replace(LEGACY_IMAGE_PLACEHOLDER, image)

        manifest_path = output_dir / manifest_name
        manifest_path.write_text(content, encoding="utf-8")
        if manifest_name in IMAGE_MANIFESTS:
            validate_rendered_manifest_images(manifest_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Kubernetes manifests from an env file."
    )
    parser.add_argument("--env-file", required=True, help="Path to the K8S_APP_ENV file")
    parser.add_argument(
        "--output-dir", required=True, help="Directory to write manifests"
    )
    parser.add_argument("--image", required=True, help="Container image tag to deploy")
    parser.add_argument(
        "--namespace",
        default="service-order",
        help="Kubernetes namespace to render",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_path = Path(args.env_file)
    source_dir = Path(__file__).resolve().parents[2] / "k8s"
    output_dir = Path(args.output_dir)
    image = normalize_image_ref(args.image)
    output_dir.mkdir(parents=True, exist_ok=True)

    values = parse_env_file(env_path)
    values.setdefault("EMAIL_PROVIDER", "NOOP")
    values["MIGRATE_ON_STARTUP"] = "false"

    secret_values = {
        key: value
        for key, value in values.items()
        if key in SENSITIVE_KEYS and value.strip()
    }
    missing_secret_keys = sorted(REQUIRED_SECRET_KEYS - secret_values.keys())
    if missing_secret_keys:
        raise SystemExit(
            "Missing required secret keys in env file: " + ", ".join(missing_secret_keys)
        )

    config_values = {
        key: value
        for key, value in values.items()
        if key not in SENSITIVE_KEYS and value.strip()
    }

    render_static_manifests(
        source_dir,
        output_dir,
        namespace=args.namespace,
        image=image,
    )
    write_manifest(
        output_dir / "configmap.rendered.yaml",
        kind="ConfigMap",
        name="service-order-billing-service-config",
        namespace=args.namespace,
        section_name="data",
        values=config_values,
    )
    write_manifest(
        output_dir / "secret.rendered.yaml",
        kind="Secret",
        name="service-order-billing-service-secret",
        namespace=args.namespace,
        section_name="stringData",
        values=secret_values,
    )

    print(f"Rendered manifests into {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

