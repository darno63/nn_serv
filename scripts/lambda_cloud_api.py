#!/usr/bin/env python3
"""Utility CLI for interacting with the Lambda Cloud REST API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib import error, parse, request

DEFAULT_BASE_URL = os.getenv("LAMBDA_API_BASE_URL", "https://cloud.lambda.ai")
API_TIMEOUT_SECONDS = 30
CONFIG_SEARCH_DIRS = [
    Path(__file__).resolve().parent.parent / "configs" / "lambda",
]
DEFAULT_USER_AGENT = "nn-serv-cli/0.1"


class LambdaApiClient:
    """Minimal Lambda Cloud API client using the standard library."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        if not api_key:
            raise ValueError("An API key is required; set LAMBDA_API_KEY or pass --api-key")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: Dict[str, Any] | None = None,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not path.startswith("/"):
            path = f"/{path}"
        url = f"{self.base_url}{path}"
        if params:
            query = parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": os.getenv("LAMBDA_API_USER_AGENT", DEFAULT_USER_AGENT),
        }

        data: bytes | None = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            error_payload = exc.read().decode("utf-8", "ignore")
            message = _extract_error_message(error_payload)
            raise SystemExit(f"API request failed ({exc.code}): {message}") from exc
        except error.URLError as exc:
            raise SystemExit(f"Failed to reach {url}: {exc.reason}") from exc

        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to decode response as JSON: {exc}") from exc


def _extract_error_message(raw_payload: str) -> str:
    if not raw_payload:
        return "<no error message returned>"
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return raw_payload.strip() or "<unparseable error response>"
    error_obj = payload.get("error", {})
    code = error_obj.get("code")
    message = error_obj.get("message", "<no error message>")
    if code:
        return f"{code}: {message}"
    return message


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interact with the Lambda Cloud REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              # List available instance types
              scripts/lambda_cloud_api.py list-instance-types

              # List persistent filesystems
              scripts/lambda_cloud_api.py list-filesystems

              # Launch an instance using config defaults
              scripts/lambda_cloud_api.py launch-instance --config wan2-instance

              # Override config values at runtime
              scripts/lambda_cloud_api.py launch-instance --config wan2-instance --region us-west-1

              # Terminate instances
              scripts/lambda_cloud_api.py terminate-instances i-123abc i-456def
            """
        ),
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LAMBDA_API_KEY"),
        help="Lambda Cloud API key (defaults to LAMBDA_API_KEY environment variable)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Lambda Cloud API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON responses instead of a human-readable summary",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_types = subparsers.add_parser("list-instance-types", help="Show available instance types")
    list_types.add_argument(
        "--region",
        help="Only display instance types that currently have capacity in the specified region",
    )
    list_types.add_argument(
        "--available-only",
        action="store_true",
        help="Hide instance types that presently have no regional capacity",
    )

    subparsers.add_parser("list-instances", help="List running instances")
    subparsers.add_parser("list-filesystems", help="List persistent filesystems")

    get_instance = subparsers.add_parser("get-instance", help="Fetch details for a single instance")
    get_instance.add_argument("instance_id")

    launch = subparsers.add_parser("launch-instance", help="Launch a new instance")
    launch.add_argument(
        "--config",
        help="Name or path of a YAML config with launch defaults (e.g., wan2-instance)",
    )
    launch.add_argument(
        "--region",
        help="Region code (overrides config)",
    )
    launch.add_argument(
        "--instance-type",
        help="Instance type slug (overrides config)",
    )
    launch.add_argument(
        "--ssh-key",
        action="append",
        dest="ssh_keys",
        help="Name of an SSH key to attach (repeatable). Overrides config values.",
    )
    launch.add_argument("--name", help="Optional friendly name for the instance")
    launch.add_argument("--hostname", help="Custom hostname to assign to the instance")
    launch.add_argument(
        "--tag",
        action="append",
        help="Instance tag in KEY=VALUE form (repeatable)",
    )
    launch.add_argument(
        "--user-data-file",
        help="Path to a cloud-init user-data file to apply on launch",
    )
    launch.add_argument(
        "--filesystem",
        action="append",
        dest="filesystems",
        help="Name of a persistent filesystem to attach using its default mount point (repeatable)",
    )
    launch.add_argument(
        "--filesystem-mount",
        action="append",
        dest="filesystem_mounts",
        help=(
            "Attach a filesystem by ID at a custom mount path, format FS_ID=/mount/path "
            "(repeatable; overrides default mount point)"
        ),
    )

    terminate = subparsers.add_parser("terminate-instances", help="Terminate one or more instances")
    terminate.add_argument("instance_ids", nargs="+", help="Instance IDs to terminate")

    list_keys = subparsers.add_parser("list-ssh-keys", help="List stored SSH keys")
    add_key = subparsers.add_parser("add-ssh-key", help="Upload an SSH public key")
    add_key.add_argument("--name", required=True, help="Name to assign to the SSH key")
    add_key.add_argument(
        "--public-key",
        help="Path to the public key file. If omitted, reads from stdin.",
    )
    add_key.add_argument(
        "--generate",
        action="store_true",
        help="Ask the API to generate a fresh SSH key pair (public/private).",
    )

    delete_key = subparsers.add_parser("delete-ssh-key", help="Delete an SSH key by ID")
    delete_key.add_argument("ssh_key_id")

    return parser


def cmd_list_instance_types(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    response = client.request("GET", "/api/v1/instance-types")
    if args.json:
        return response

    data = response.get("data", {})
    if not data:
        print("No instance types returned.")
        return {}

    for type_name, details in sorted(data.items()):
        all_regions = details.get("regions_with_capacity_available", [])
        selected_regions = all_regions
        region_label: str
        if args.region:
            selected_regions = [r for r in all_regions if r.get("name") == args.region]
            if args.available_only and not selected_regions:
                continue
            if selected_regions:
                region_label = ", ".join(r.get("name", "?") for r in selected_regions)
            else:
                region_label = f"No capacity in {args.region}"
        else:
            if args.available_only and not all_regions:
                continue
            region_label = ", ".join(r.get("name", "?") for r in all_regions) or "No capacity"

        info = details.get("instance_type", {})
        price_cents = info.get("price_cents_per_hour")
        price = f"${price_cents / 100:.2f}/hr" if price_cents is not None else "<unknown price>"
        description = info.get("description", "").strip()
        print(f"{type_name}: {price} — {description} | Regions: {region_label}")
    return {}


def cmd_list_instances(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    response = client.request("GET", "/api/v1/instances")
    if args.json:
        return response

    instances = response.get("data", [])
    if not instances:
        print("No running instances.")
        return {}

    for inst in instances:
        inst_type = inst.get("instance_type", {}).get("name", "<unknown>")
        region = inst.get("region", {}).get("name", "<unknown>")
        name = inst.get("name") or "<unnamed>"
        status = inst.get("status", {}).get("value") or inst.get("status", {}).get("name")
        print(
            f"{inst['id']}: {name} | {inst_type} | {region} | status={status} | ip={inst.get('ip')}"
        )
    return {}


def cmd_list_filesystems(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    response = client.request("GET", "/api/v1/file-systems")
    if args.json:
        return response

    filesystems = response.get("data", [])
    if not filesystems:
        print("No filesystems found.")
        return {}

    for fs in filesystems:
        region = fs.get("region", {}).get("name", "<unknown>")
        mount = fs.get("mount_point", "<unknown>")
        usage_bytes = fs.get("bytes_used")
        if usage_bytes is not None:
            usage_gib = usage_bytes / (1024**3)
            usage = f"{usage_gib:.1f} GiB used"
        else:
            usage = "usage unknown"
        status = "in-use" if fs.get("is_in_use") else "available"
        print(f"{fs['id']}: {fs.get('name','<unnamed>')} | {region} | mount={mount} | {usage} | {status}")
    return {}


def cmd_get_instance(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    response = client.request("GET", f"/api/v1/instances/{args.instance_id}")
    if args.json:
        return response

    inst = response.get("data", {})
    if not inst:
        print("Instance not found.")
        return {}

    print(json.dumps(inst, indent=2))
    return {}


def cmd_launch_instance(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    config_data: Dict[str, Any] = {}
    config_dir: Optional[Path] = None
    if args.config:
        config_data, config_dir = _load_launch_config(args.config)
    config_launch = config_data.get("launch", config_data)

    payload: Dict[str, Any] = {}

    region = args.region or config_launch.get("region") or config_launch.get("region_name")
    if not region:
        raise SystemExit(
            "Region is required. Provide --region or set 'region' in the config file."
        )
    payload["region_name"] = region

    instance_type = (
        args.instance_type
        or config_launch.get("instance_type")
        or config_launch.get("instance_type_name")
    )
    if not instance_type:
        raise SystemExit(
            "Instance type is required. Provide --instance-type or set 'instance_type' in the config file."
        )
    payload["instance_type_name"] = instance_type

    config_ssh = _ensure_list(
        config_launch.get("ssh_keys")
        or config_launch.get("ssh_key")
        or config_launch.get("ssh_key_names")
    )
    ssh_keys = args.ssh_keys or config_ssh
    if not ssh_keys:
        raise SystemExit(
            "At least one SSH key is required. Provide --ssh-key or set 'ssh_keys' in the config file."
        )
    payload["ssh_key_names"] = ssh_keys

    name = args.name or config_launch.get("name")
    if name:
        payload["name"] = name

    hostname = args.hostname or config_launch.get("hostname")
    if hostname:
        payload["hostname"] = hostname

    filesystem_names = _ensure_list(
        config_launch.get("filesystem_names")
        or config_launch.get("file_system_names")
        or config_launch.get("filesystem")
        or config_launch.get("filesystems")
    )
    if args.filesystems:
        filesystem_names.extend(args.filesystems)
    filesystem_names = _dedupe_preserve_order(filesystem_names)
    if filesystem_names:
        payload["file_system_names"] = filesystem_names

    config_mounts = _normalize_config_mounts(
        config_launch.get("filesystem_mounts")
        or config_launch.get("file_system_mounts")
    )
    cli_mounts = [
        _parse_filesystem_mount(item) for item in (args.filesystem_mounts or [])
    ]
    if config_mounts or cli_mounts:
        payload["file_system_mounts"] = config_mounts + cli_mounts

    config_tags = _normalize_config_tags(config_launch.get("tags"))
    cli_tags = [_parse_key_value(tag) for tag in (args.tag or [])]
    merged_tags = _merge_tags(config_tags, cli_tags)
    if merged_tags:
        payload["tags"] = merged_tags

    image = config_launch.get("image")
    if image:
        payload["image"] = image

    firewall_rulesets = _ensure_list(config_launch.get("firewall_rulesets"))
    if firewall_rulesets:
        payload["firewall_rulesets"] = firewall_rulesets

    user_data: Optional[str] = None
    if "user_data" in config_launch and config_launch["user_data"]:
        user_data = str(config_launch["user_data"])
    if config_launch.get("user_data_file"):
        user_data_path = _resolve_relative_path(
            config_launch["user_data_file"], config_dir
        )
        user_data = _read_file(str(user_data_path))
    if args.user_data_file:
        user_data = _read_file(args.user_data_file)
    if user_data:
        payload["user_data"] = user_data

    response = client.request("POST", "/api/v1/instance-operations/launch", payload=payload)
    if args.json:
        return response

    ids = response.get("data", {}).get("instance_ids", [])
    if ids:
        print("Launched instance IDs:")
        for instance_id in ids:
            print(f"  {instance_id}")
    else:
        print("No instance IDs returned; check the API response.")
    return {}


def cmd_terminate_instances(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    payload = {"instance_ids": args.instance_ids}
    response = client.request("POST", "/api/v1/instance-operations/terminate", payload=payload)
    if args.json:
        return response

    print("Termination request submitted for:")
    for instance_id in args.instance_ids:
        print(f"  {instance_id}")
    return {}


def cmd_list_ssh_keys(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    response = client.request("GET", "/api/v1/ssh-keys")
    if args.json:
        return response

    keys = response.get("data", [])
    if not keys:
        print("No SSH keys on account.")
        return {}

    for key in keys:
        print(f"{key['id']}: {key['name']} -> {key['public_key'][:45]}...")
    return {}


def cmd_add_ssh_key(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"name": args.name}
    if args.generate and args.public_key:
        raise SystemExit("--generate cannot be used with --public-key")
    if args.generate:
        # API generates key pair when public_key omitted and generate flag set via query param
        response = client.request(
            "POST",
            "/api/v1/ssh-keys",
            payload=payload,
            params={"generate": "true"},
        )
    else:
        public_key = _read_file(args.public_key) if args.public_key else sys.stdin.read()
        if not public_key.strip():
            raise SystemExit("Public key content is empty.")
        payload["public_key"] = public_key.strip()
        response = client.request("POST", "/api/v1/ssh-keys", payload=payload)

    if args.json:
        return response

    data = response.get("data", {})
    if "private_key" in data:
        print("Generated new SSH key pair. Save the private key securely:")
        print(data.get("private_key"))
    else:
        print(f"Uploaded SSH key '{data.get('name', args.name)}'.")
    return {}


def cmd_delete_ssh_key(client: LambdaApiClient, args: argparse.Namespace) -> Dict[str, Any]:
    response = client.request("DELETE", f"/api/v1/ssh-keys/{args.ssh_key_id}")
    if args.json:
        return response
    print(f"Deleted SSH key {args.ssh_key_id}.")
    return {}


def _load_launch_config(config_name: str) -> tuple[Dict[str, Any], Path]:
    candidates: List[Path] = []
    explicit_path = Path(config_name)
    if explicit_path.exists():
        candidates.append(explicit_path)

    if not explicit_path.suffix:
        for directory in CONFIG_SEARCH_DIRS:
            candidates.extend(
                [
                    directory / f"{config_name}.yaml",
                    directory / f"{config_name}.yml",
                ]
            )

    checked = []
    for path in candidates:
        if path.exists():
            try:
                import yaml  # type: ignore
            except ImportError as exc:  # pragma: no cover - dependency hint
                raise SystemExit(
                    "PyYAML is required for --config support. Install it with `pip install pyyaml`."
                ) from exc
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            if not isinstance(data, dict):
                raise SystemExit(f"Config file {path} must contain a mapping at the top level.")
            return data, path.parent.resolve()
        checked.append(str(path))

    search_hint = ", ".join(checked) if checked else str(explicit_path)
    raise SystemExit(f"Config file '{config_name}' not found. Checked: {search_hint}")


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        result: List[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                result.append(item)
            else:
                raise SystemExit(f"Expected string entries in list, found {type(item).__name__}")
        return result
    raise SystemExit(f"Expected string or list, got {type(value).__name__}")


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _resolve_relative_path(path_str: str, base_dir: Optional[Path]) -> Path:
    candidate = Path(path_str)
    if not candidate.is_absolute() and base_dir is not None:
        candidate = (base_dir / candidate).resolve()
    return candidate


def _parse_key_value(item: str) -> Dict[str, str]:
    if "=" not in item:
        raise SystemExit(f"Invalid tag '{item}'. Expected KEY=VALUE format.")
    key, value = item.split("=", 1)
    return {"key": key, "value": value}


def _parse_filesystem_mount(item: str) -> Dict[str, str]:
    if "=" not in item:
        raise SystemExit(f"Invalid filesystem mount '{item}'. Expected FS_ID=/mount/path format.")
    fs_id, mount_point = item.split("=", 1)
    mount_point = mount_point.strip()
    if not mount_point.startswith("/"):
        raise SystemExit(f"Mount point must be an absolute path: '{mount_point}'")
    return {"file_system_id": fs_id.strip(), "mount_point": mount_point}


def _normalize_config_mounts(value: Any) -> List[Dict[str, str]]:
    if value is None:
        return []
    mounts: List[Dict[str, str]] = []
    if isinstance(value, (list, tuple)):
        iterable = value
    else:
        iterable = [value]
    for item in iterable:
        if isinstance(item, str):
            mounts.append(_parse_filesystem_mount(item))
        elif isinstance(item, dict):
            if {"file_system_id", "mount_point"} <= item.keys():
                mounts.append(
                    {
                        "file_system_id": str(item["file_system_id"]),
                        "mount_point": str(item["mount_point"]),
                    }
                )
            elif {"name", "mount_point"} <= item.keys():
                mounts.append(
                    {
                        "file_system_id": str(item["name"]),
                        "mount_point": str(item["mount_point"]),
                    }
                )
            else:
                raise SystemExit(
                    "Filesystem mount dicts must include 'file_system_id' (or 'name') and 'mount_point'."
                )
        else:
            raise SystemExit(
                f"Unsupported filesystem mount entry of type {type(item).__name__}"
            )
    return mounts


def _normalize_config_tags(value: Any) -> List[Dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [{"key": str(key), "value": str(val)} for key, val in value.items()]
    if isinstance(value, (list, tuple)):
        normalized: List[Dict[str, str]] = []
        for item in value:
            if isinstance(item, dict) and {"key", "value"} <= item.keys():
                normalized.append({"key": str(item["key"]), "value": str(item["value"])})
            elif isinstance(item, str):
                normalized.append(_parse_key_value(item))
            else:
                raise SystemExit(
                    "Tag entries must be dicts with 'key'/'value' or strings in KEY=VALUE format."
                )
        return normalized
    if isinstance(value, str):
        return [_parse_key_value(value)]
    raise SystemExit(f"Unsupported tag format: {type(value).__name__}")


def _merge_tags(*tag_lists: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, str] = {}
    for tag_list in tag_lists:
        for entry in tag_list:
            merged[entry["key"]] = entry["value"]
    return [{"key": key, "value": value} for key, value in merged.items()]


def _read_file(path: str | None) -> str:
    if not path:
        raise ValueError("Path must be provided")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError as exc:
        raise SystemExit(f"Failed to read {path}: {exc}") from exc


COMMAND_HANDLERS = {
    "list-instance-types": cmd_list_instance_types,
    "list-instances": cmd_list_instances,
    "list-filesystems": cmd_list_filesystems,
    "get-instance": cmd_get_instance,
    "launch-instance": cmd_launch_instance,
    "terminate-instances": cmd_terminate_instances,
    "list-ssh-keys": cmd_list_ssh_keys,
    "add-ssh-key": cmd_add_ssh_key,
    "delete-ssh-key": cmd_delete_ssh_key,
}


def main(argv: Iterable[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    client = LambdaApiClient(api_key=args.api_key, base_url=args.base_url)
    handler = COMMAND_HANDLERS[args.command]
    result = handler(client, args)
    if args.json and result:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
