import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

import requests


DEFAULT_GRAPH_VERSION = "v24.0"
BOGOTA_TZ = ZoneInfo("America/Bogota")
DEFAULT_PORT = 8765
DEFAULT_CONTAINER_POLL_SECONDS = 20
DEFAULT_CONTAINER_TIMEOUT_SECONDS = 360
DEFAULT_POST_PAUSE_SECONDS = 10
DEFAULT_META_RETRY_ATTEMPTS = 3
DEFAULT_META_RETRY_SLEEP_SECONDS = 5
DEFAULT_META_CALL_COOLDOWN_SECONDS = 30
DEFAULT_META_COOLDOWN_CALLS = 5
DEFAULT_META_COOLDOWN_SECONDS = 180
REQUIRED_ENV = {
    "INSTAGRAM_USER_ID": "Instagram professional account ID, usually instagram_business_account.id.",
    "META_PAGE_ACCESS_TOKEN": "Page access token with instagram_content_publish permission.",
}
LEGACY_ENV_LABELS = {
    "Nombre de la app de Instagram": "INSTAGRAM_APP_NAME",
    "Identificador de la app de Instagram": "INSTAGRAM_APP_ID",
    "Clave secreta de la app de Instagram": "INSTAGRAM_APP_SECRET",
    "Token del Usuario": "META_USER_ACCESS_TOKEN",
    "Token de la app": "META_APP_ACCESS_TOKEN",
    "Token de acceso": "META_APP_ACCESS_TOKEN",
}
META_CALL_COUNT = 0


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def set_dotenv_values(path, values):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    remaining = dict(values)
    output = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}")
                continue
        output.append(line)
    if remaining:
        if output and output[-1].strip():
            output.append("")
        for key, value in remaining.items():
            output.append(f"{key}={value}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def normalize_dotenv(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    output = []
    seen = set()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        key = LEGACY_ENV_LABELS.get(stripped)
        if key:
            value_index = index + 1
            while value_index < len(lines) and not lines[value_index].strip():
                value_index += 1
            value = lines[value_index].strip() if value_index < len(lines) else ""
            if key not in seen:
                output.append(f"{key}={value}")
                seen.add(key)
            index = value_index + 1 if value_index < len(lines) else index + 1
            continue
        if stripped and not stripped.startswith("#") and "=" in stripped:
            seen.add(stripped.split("=", 1)[0].strip())
        output.append(line)
        index += 1

    defaults = {
        "SITE_BASE_URL": "https://divisascol.com",
        "META_GRAPH_VERSION": DEFAULT_GRAPH_VERSION,
        "INSTAGRAM_USER_ID": "",
        "META_PAGE_ACCESS_TOKEN": "",
    }
    if output and output[-1].strip():
        output.append("")
    for key, value in defaults.items():
        if key not in seen:
            output.append(f"{key}={value}")
            seen.add(key)
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def repo_root():
    return Path(__file__).resolve().parent


def read_domain(root):
    domain_file = root / "domain_name.txt"
    if not domain_file.exists():
        return None
    value = domain_file.read_text(encoding="utf-8").strip()
    return value.rstrip("/") if value else None


def get_base_url(root):
    return (os.environ.get("SITE_BASE_URL") or read_domain(root) or "").rstrip("/")


def latest_manifest(root):
    cards_root = root / "instagram_cards"
    manifests = sorted(cards_root.glob("*/manifest.json"))
    if not manifests:
        raise FileNotFoundError("No manifest found under instagram_cards/YYYY-MM-DD/manifest.json")
    return manifests[-1]


def latest_publish_manifest(root):
    cards_root = root / "instagram_cards"
    manifests = sorted(cards_root.glob("*/public/publish-manifest.json"))
    if not manifests:
        raise FileNotFoundError(
            "No publish manifest found under instagram_cards/YYYY-MM-DD/public/publish-manifest.json. "
            "Run `python instagram_publish.py prepare` first."
        )
    return manifests[-1]


def default_date_label():
    return datetime.now(BOGOTA_TZ).date().isoformat()


def publish_manifest_for_date(root, date_label):
    selected_date = date_label or default_date_label()
    manifest = root / "instagram_cards" / selected_date / "public" / "publish-manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(
            f"Missing publish manifest for {selected_date}: {manifest}. "
            "Run `python generate_instagram_cards.py` for that date first."
        )
    return manifest


def resolve_manifest(root, value):
    if value:
        path = Path(value)
        return path if path.is_absolute() else root / path
    return latest_manifest(root)


def resolve_publish_manifest(root, value):
    if value:
        path = Path(value)
        return path if path.is_absolute() else root / path
    return latest_publish_manifest(root)


def load_manifest(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_publish_state(path):
    if not path.exists():
        return {"published_groups": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        return {"published_groups": []}
    published_groups = state.get("published_groups") or []
    if not isinstance(published_groups, list):
        published_groups = []
    return {"published_groups": [str(group) for group in published_groups if str(group)]}


def save_publish_state(path, state):
    payload = {
        "published_groups": list(dict.fromkeys(state.get("published_groups", []))),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_caption(root, card):
    description_path = card.get("description_path")
    if not description_path:
        return ""
    path = root / description_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def target_name(card):
    source = Path(card["path"])
    return source.with_suffix(".jpg").name


def render_svg_to_png(source, destination):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Missing dependency: install with `pip install -r requirements.txt`.") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
            page.goto(source.resolve().as_uri(), wait_until="load")
            png_bytes = page.screenshot(full_page=False, type="png")
            browser.close()
        from PIL import Image
        from io import BytesIO
        image = Image.open(BytesIO(png_bytes)).convert("RGB")
        image.save(destination, format="JPEG", quality=92, optimize=True)
    except Exception as exc:
        raise RuntimeError(
            "Could not render SVG with Playwright. Run `python -m playwright install chromium` once."
        ) from exc


def prepare(args):
    root = repo_root()
    load_dotenv(root / ".env")
    manifest_path = resolve_manifest(root, args.manifest)
    manifest = load_manifest(manifest_path)
    base_url = (args.base_url or get_base_url(root)).rstrip("/")
    if not base_url:
        raise RuntimeError("Set SITE_BASE_URL in .env or add domain_name.txt.")

    date_label = manifest.get("date") or manifest_path.parent.name
    public_dir = root / "instagram_cards" / date_label / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    posts = []
    for index, card in enumerate(manifest.get("cards", []), start=1):
        source = root / card["path"]
        if not source.exists():
            raise FileNotFoundError(f"Missing card file: {source}")

        png_path = public_dir / target_name(card)
        if source.suffix.lower() == ".svg":
            render_svg_to_png(source, png_path)
        else:
            shutil.copyfile(source, png_path)

        relative_url = f"/{png_path.name}"
        posts.append(
            {
                "index": index,
                "type": card.get("type"),
                "city": card.get("city"),
                "title": card.get("title"),
                "source_path": card["path"],
                "public_path": str(png_path.relative_to(root).as_posix()),
                "image_url": urljoin(base_url + "/", relative_url.lstrip("/")),
                "caption": read_caption(root, card),
            }
        )

    publish_manifest = {
        "date": date_label,
        "source_manifest": str(manifest_path.relative_to(root).as_posix()),
        "posts": posts,
    }
    output_path = public_dir / "publish-manifest.json"
    output_path.write_text(
        json.dumps(publish_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Prepared {len(posts)} image posts.")
    print(f"Serve this folder while publishing: {public_dir.relative_to(root).as_posix()}")
    print(f"Publish manifest: {output_path.relative_to(root).as_posix()}")


def validate_config():
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    base_url = get_base_url(repo_root())
    if not base_url:
        missing.append("SITE_BASE_URL or domain_name.txt")
    if missing:
        print("Missing Instagram publishing config:")
        for key in missing:
            detail = REQUIRED_ENV.get(key, "Public base URL for hosted card images.")
            print(f"- {key}: {detail}")
        return False
    print("Instagram publishing config is present.")
    print(f"- INSTAGRAM_USER_ID: {'*' * 6}{os.environ['INSTAGRAM_USER_ID'][-4:]}")
    print(f"- META_PAGE_ACCESS_TOKEN: present")
    print(f"- SITE_BASE_URL: {base_url}")
    return True


def graph_url(path):
    version = os.environ.get("META_GRAPH_VERSION", DEFAULT_GRAPH_VERSION).strip() or DEFAULT_GRAPH_VERSION
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


def meta_error_payload(response):
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    return error if isinstance(error, dict) else None


def is_non_retryable_meta_error(error):
    if not isinstance(error, dict):
        return False
    code = error.get("code")
    subcode = error.get("error_subcode")
    if code == 4 and subcode == 2207051:
        return True
    message = str(error.get("message") or "").lower()
    return "request limit reached" in message or "application request limit reached" in message


def post_with_meta_retry(url, **kwargs):
    global META_CALL_COUNT
    META_CALL_COUNT += 1
    time.sleep(DEFAULT_META_CALL_COOLDOWN_SECONDS)
    if META_CALL_COUNT % DEFAULT_META_COOLDOWN_CALLS == 0:
        print(
            f"Cooling down before Meta call {META_CALL_COUNT}: sleeping {DEFAULT_META_COOLDOWN_SECONDS} seconds."
        )
        time.sleep(DEFAULT_META_COOLDOWN_SECONDS)
    last_response = None
    attempts = DEFAULT_META_RETRY_ATTEMPTS
    for attempt in range(1, attempts + 1):
        response = requests.post(url, **kwargs)
        last_response = response
        if response.ok:
            return response
        error = meta_error_payload(response)
        if is_non_retryable_meta_error(error):
            response.raise_for_status()
        if attempt < attempts:
            time.sleep(DEFAULT_META_RETRY_SLEEP_SECONDS)
    if last_response is not None:
        last_response.raise_for_status()
    raise RuntimeError("Meta request failed without a response.")


def create_container(ig_user_id, token, image_url, caption):
    response = post_with_meta_retry(
        graph_url(f"{ig_user_id}/media"),
        data={
            "image_url": image_url,
            "caption": sanitize_caption(caption),
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["id"]


def publish_container(ig_user_id, token, creation_id):
    response = post_with_meta_retry(
        graph_url(f"{ig_user_id}/media_publish"),
        data={
            "creation_id": creation_id,
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def create_carousel_container(ig_user_id, token, children, caption):
    response = post_with_meta_retry(
        graph_url(f"{ig_user_id}/media"),
        json={
            "media_type": "CAROUSEL",
            "children": children,
            "caption": sanitize_caption(caption),
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    print(f"Carousel container response: {json.dumps(redacted_token_debug(payload), ensure_ascii=False)}")
    return payload["id"]


def create_carousel_item_container(ig_user_id, token, image_url):
    response = post_with_meta_retry(
        graph_url(f"{ig_user_id}/media"),
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["id"]


def media_container_status(container_id, token):
    response = requests.get(
        graph_url(container_id),
        params={
            "fields": "status_code,status",
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def wait_for_container_finished(
    container_id,
    token,
    timeout_seconds=DEFAULT_CONTAINER_TIMEOUT_SECONDS,
    poll_seconds=DEFAULT_CONTAINER_POLL_SECONDS,
):
    deadline = time.time() + timeout_seconds
    last_status = None
    current_poll_seconds = poll_seconds
    while time.time() < deadline:
        status = media_container_status(container_id, token)
        last_status = status
        code = status.get("status_code")
        if code == "FINISHED":
            print(f"Container {container_id} finished.")
            return
        if code == "ERROR":
            raise RuntimeError(f"Container {container_id} failed: {status}")
        time.sleep(current_poll_seconds)
        current_poll_seconds = min(current_poll_seconds + poll_seconds, 60)
    raise RuntimeError(f"Container {container_id} did not finish. Last status: {last_status}")


def group_key_for_post(post):
    explicit_group = str(post.get("group") or "").strip()
    if explicit_group:
        return explicit_group.lower()
    name = Path(post.get("public_path") or post.get("source_path") or "").name
    stem = Path(name).stem
    return stem.split("-", 1)[0] if stem else "post"


def group_posts_for_instagram(posts):
    groups = []
    by_key = {}
    for post in posts:
        key = group_key_for_post(post)
        if key not in by_key:
            by_key[key] = {
                "key": key,
                "caption": post.get("caption", ""),
                "posts": [],
                "single": key == "newsletter",
            }
            groups.append(by_key[key])
        elif not by_key[key]["caption"] and post.get("caption"):
            by_key[key]["caption"] = post.get("caption", "")
        by_key[key]["posts"].append(post)
    for group in groups:
        if len(group["posts"]) == 1:
            group["single"] = True
    return groups


def split_oversized_groups(groups, max_items=10):
    split_groups = []
    for group in groups:
        posts = group["posts"]
        if len(posts) <= max_items:
            split_groups.append(group)
            continue
        for index in range(0, len(posts), max_items):
            chunk = posts[index : index + max_items]
            chunk_group = dict(group)
            suffix = index // max_items + 1
            chunk_group["key"] = f"{group['key']}-{suffix}"
            chunk_group["posts"] = chunk
            chunk_group["single"] = len(chunk) == 1
            split_groups.append(chunk_group)
    return split_groups


def sanitize_caption(caption, max_length=2200, max_hashtags=30):
    text = str(caption or "").strip()
    if not text:
        return ""
    tokens = re.split(r"(\s+)", text)
    hashtag_count = 0
    kept = []
    for token in tokens:
        if token.startswith("#"):
            hashtag_count += 1
            if hashtag_count > max_hashtags:
                continue
        kept.append(token)
    text = "".join(kept).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def publish(args):
    root = repo_root()
    load_dotenv(root / ".env")
    if not args.dry_run and not validate_config():
        return 2

    manifest_path = resolve_publish_manifest(root, args.manifest)
    manifest = load_manifest(manifest_path)
    posts = manifest.get("posts", [])
    if args.limit:
        posts = posts[: args.limit]
    if not posts:
        raise RuntimeError("No posts found in publish manifest. Run `python instagram_publish.py prepare` first.")

    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")

    for post in posts:
        label = post.get("city") or post.get("title") or post.get("source_path") or post["image_url"]
        print(f"Posting {post['index']}: {label}")
        if not post.get("image_url"):
            message = "Missing image_url. Run `python instagram_publish.py serve` and keep it running before publishing."
            if args.dry_run:
                print(f"DRY RUN skipped: {message}")
                continue
            raise RuntimeError(message)
        if args.dry_run:
            print(f"DRY RUN image_url={post['image_url']}")
            continue
        creation_id = create_container(ig_user_id, token, post["image_url"], post.get("caption", ""))
        print(f"Created container {creation_id}")
        if args.wait_seconds:
            time.sleep(args.wait_seconds)
        result = publish_container(ig_user_id, token, creation_id)
        print(f"Published media {result.get('id', '(no id returned)')}")

    return 0


def latest_public_dir(root):
    manifests = sorted((root / "instagram_cards").glob("*/public/publish-manifest.json"))
    if not manifests:
        raise FileNotFoundError("Run `python instagram_publish.py prepare` first.")
    return manifests[-1].parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


def run_http_server(directory, port):
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def wait_for_tunnel_url(process, timeout_seconds=90):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        line = process.stdout.readline()
        if line:
            print(line.rstrip())
            url = extract_tunnel_url(line)
            if url:
                return url
        elif process.poll() is not None:
            break
        else:
            time.sleep(0.2)
    raise RuntimeError("Tunnel did not print a public URL.")


def extract_tunnel_url(line):
    match = re.search(r"https://[a-zA-Z0-9.-]+\.(?:trycloudflare\.com|loca\.lt)", line)
    return match.group(0) if match else None


def cloudflared_path(root):
    bundled = root / "cf_exe" / "cloudflared.exe"
    return str(bundled) if bundled.exists() else "cloudflared"


def tunnel_command(root, port):
    return [
        cloudflared_path(root),
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
        "--no-autoupdate",
    ]


def serve(args):
    root = repo_root()
    public_dir = Path(args.dir) if args.dir else latest_public_dir(root)
    if not public_dir.is_absolute():
        public_dir = root / public_dir
    if not public_dir.exists():
        raise FileNotFoundError(f"Missing public image directory: {public_dir}")

    server = run_http_server(public_dir, args.port)
    local_url = f"http://127.0.0.1:{args.port}"
    print(f"Serving {public_dir.relative_to(root).as_posix()} at {local_url}")

    tunnel = None
    try:
        if args.local_only:
            print("Local-only mode. Meta cannot fetch localhost; use this only to inspect files.")
            while True:
                time.sleep(3600)
        tunnel = subprocess.Popen(
            tunnel_command(root, args.port),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(root),
        )
        public_url = wait_for_tunnel_url(tunnel)
        manifest_path = public_dir / "publish-manifest.json"
        if manifest_path.exists():
            manifest = load_manifest(manifest_path)
            for post in manifest.get("posts", []):
                post["image_url"] = urljoin(public_url + "/", Path(post["public_path"]).name)
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            print(f"Updated manifest image URLs: {manifest_path.relative_to(root).as_posix()}")
        print(f"Public base URL: {public_url}")
        print("Keep this command running while you publish.")
        while True:
            if tunnel.poll() is not None:
                raise RuntimeError("Tunnel stopped.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping temporary server.")
    finally:
        if tunnel and tunnel.poll() is None:
            tunnel.terminate()
        server.shutdown()
    return 0


def update_manifest_urls(manifest_path, public_url):
    manifest = load_manifest(manifest_path)
    for post in manifest.get("posts", []):
        post["image_url"] = urljoin(public_url + "/", Path(post["public_path"]).name)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def wait_for_public_image(image_url, timeout_seconds=120):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(image_url, timeout=15)
            content_type = response.headers.get("content-type", "").lower()
            if response.ok and content_type.startswith("image/") and response.content:
                print(f"Verified public image URL: {image_url} ({content_type}, {len(response.content)} bytes)")
                return
            last_error = f"HTTP {response.status_code} {content_type} {response.text[:120]!r}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(3)
    raise RuntimeError(f"Public image URL never became image/*: {image_url}. Last error: {last_error}")


def prepare_group_container(group, ig_user_id, token):
    posts = group["posts"]
    if group["single"]:
        post = posts[0]
        creation_id = create_container(ig_user_id, token, post["image_url"], group.get("caption", ""))
        print(f"Created {group['key']} image container {creation_id}")
        return {"group": group, "creation_id": creation_id, "kind": "media"}

    child_ids = []
    for post in posts:
        child_id = create_carousel_item_container(ig_user_id, token, post["image_url"])
        child_ids.append(child_id)
        print(f"Created {group['key']} carousel item {child_id}")
        wait_for_container_finished(child_id, token)
    carousel_id = create_carousel_container(ig_user_id, token, child_ids, group.get("caption", ""))
    if not carousel_id or carousel_id == "0":
        raise RuntimeError(f"Meta returned invalid carousel container ID: {carousel_id}")
    print(f"Created {group['key']} carousel container {carousel_id}")
    wait_for_container_finished(carousel_id, token)
    return {"group": group, "creation_id": carousel_id, "kind": "carousel"}


def publish_prepared_group(prepared_group, ig_user_id, token):
    group = prepared_group["group"]
    result = publish_container(ig_user_id, token, prepared_group["creation_id"])
    print(f"Published {group['key']} {prepared_group['kind']} {result.get('id', '(no id returned)')}")
    return result


def should_publish_group(group):
    return bool(group.get("single"))


def publish_groups(groups, ig_user_id, token):
    prepared_groups = []
    for group in groups:
        prepared_groups.append(prepare_group_container(group, ig_user_id, token))
    results = []
    for index, prepared_group in enumerate(prepared_groups):
        group = prepared_group["group"]
        if not should_publish_group(group):
            print(f"Prepared {group['key']} carousel container {prepared_group['creation_id']} (skipping final publish)")
            continue
        results.append(publish_prepared_group(prepared_group, ig_user_id, token))
        if index < len(prepared_groups) - 1:
            print(f"Waiting {DEFAULT_POST_PAUSE_SECONDS}s before next post.")
            time.sleep(DEFAULT_POST_PAUSE_SECONDS)
    return results


def publish_group(group, ig_user_id, token):
    prepared_group = prepare_group_container(group, ig_user_id, token)
    if not should_publish_group(group):
        print(f"Prepared {group['key']} carousel container {prepared_group['creation_id']} (skipping final publish)")
        return prepared_group
    return publish_prepared_group(prepared_group, ig_user_id, token)


def filter_unpublished_groups(groups, state):
    published = set(state.get("published_groups", []))
    return [group for group in groups if group["key"] not in published]


def select_groups(groups, requested_groups):
    if not requested_groups:
        return groups
    wanted = {group.strip().lower() for group in requested_groups if group.strip()}
    return [group for group in groups if group["key"].lower() in wanted]


def prioritize_newsletter(groups):
    newsletter = [group for group in groups if group["key"].lower() == "newsletter"]
    others = [group for group in groups if group["key"].lower() != "newsletter"]
    return newsletter + others


def run_serve_publish(args):
    root = repo_root()
    load_dotenv(root / ".env")
    if not validate_config():
        return 2

    manifest_path = publish_manifest_for_date(root, args.date)
    public_dir = manifest_path.parent
    server = run_http_server(public_dir, DEFAULT_PORT)
    print(f"Serving {public_dir.relative_to(root).as_posix()} at http://127.0.0.1:{DEFAULT_PORT}")
    tunnel = None
    try:
        tunnel = subprocess.Popen(
            tunnel_command(root, DEFAULT_PORT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(root),
        )
        public_url = wait_for_tunnel_url(tunnel)
        manifest = update_manifest_urls(manifest_path, public_url)
        print(f"Updated manifest image URLs: {manifest_path.relative_to(root).as_posix()}")
        print(f"Public base URL: {public_url}")

        posts = manifest.get("posts", [])
        if not posts:
            raise RuntimeError(f"No posts in {manifest_path}")
        wait_for_public_image(posts[0]["image_url"])
        groups = split_oversized_groups(group_posts_for_instagram(posts))
        state_path = public_dir / "publish-state.json"
        if args.reset_state and state_path.exists():
            state_path.unlink()
            print(f"Reset publish state: {state_path.relative_to(root).as_posix()}")
        state = load_publish_state(state_path)
        groups_to_publish = filter_unpublished_groups(groups, state)
        groups_to_publish = select_groups(groups_to_publish, args.group)
        groups_to_publish = prioritize_newsletter(groups_to_publish)
        if args.group:
            requested = ", ".join(args.group)
            print(f"Requested group filter: {requested}")
        skipped = len(groups) - len(groups_to_publish)
        if skipped:
            print(f"Skipping {skipped} already published group(s) from publish-state.json.")
        print(f"Publishing {len(groups_to_publish)} Instagram post group(s).")
        ig_user_id = os.environ["INSTAGRAM_USER_ID"]
        token = os.environ["META_PAGE_ACCESS_TOKEN"]
        prepared_groups = []
        for group in groups_to_publish:
            print(f"Preparing group {group['key']} with {len(group['posts'])} image(s).")
            prepared_groups.append(prepare_group_container(group, ig_user_id, token))
        for index, prepared_group in enumerate(prepared_groups):
            group = prepared_group["group"]
            print(f"Publishing group {group['key']} with {len(group['posts'])} image(s).")
            publish_prepared_group(prepared_group, ig_user_id, token)
            state["published_groups"].append(group["key"])
            save_publish_state(state_path, state)
            if index < len(prepared_groups) - 1:
                print(f"Waiting {DEFAULT_POST_PAUSE_SECONDS}s before next post.")
                time.sleep(DEFAULT_POST_PAUSE_SECONDS)
        return 0
    finally:
        if tunnel and tunnel.poll() is None:
            tunnel.terminate()
        server.shutdown()


def validate(_args):
    root = repo_root()
    load_dotenv(root / ".env")
    return 0 if validate_config() else 2


def redacted_token_debug(data):
    if isinstance(data, dict):
        return {
            key: (
                "***REDACTED***"
                if re.search(r"(token|secret)", str(key), re.IGNORECASE)
                else redacted_token_debug(value)
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redacted_token_debug(item) for item in data]
    return data


def debug_token(_args):
    root = repo_root()
    load_dotenv(root / ".env")
    user_token = os.environ.get("META_USER_ACCESS_TOKEN")
    if not user_token:
        print("Missing META_USER_ACCESS_TOKEN in .env.")
        return 2
    app_token = (
        os.environ.get("META_APP_ACCESS_TOKEN")
        or os.environ.get("FACEBOOK_APP_ACCESS_TOKEN")
        or os.environ.get("APP_ACCESS_TOKEN")
    )

    checks = {
        "me": ("me", {"fields": "id,name"}),
        "permissions": ("me/permissions", {}),
        "accounts": (
            "me/accounts",
            {"fields": "id,name,tasks,access_token,instagram_business_account"},
        ),
    }
    for label, (path, params) in checks.items():
        request_params = dict(params)
        request_params["access_token"] = user_token
        response = requests.get(graph_url(path), params=request_params, timeout=60)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        print(f"\n## {label} HTTP {response.status_code}")
        print(json.dumps(redacted_token_debug(payload), ensure_ascii=False, indent=2))
    if app_token:
        response = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": user_token,
                "access_token": app_token,
            },
            timeout=60,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        print(f"\n## debug_token HTTP {response.status_code}")
        print(json.dumps(redacted_token_debug(payload), ensure_ascii=False, indent=2))
    else:
        print("\n## debug_token skipped")
        print("Add META_APP_ACCESS_TOKEN=APP_ID|APP_TOKEN to .env to inspect granular_scopes.")
    return 0


def normalize_env(_args):
    env_path = repo_root() / ".env"
    normalize_dotenv(env_path)
    print("Normalized .env to NAME=VALUE format.")
    return 0


def discover(args):
    root = repo_root()
    env_path = root / ".env"
    load_dotenv(env_path)
    token = os.environ.get("META_USER_ACCESS_TOKEN")
    if not token:
        print("Missing META_USER_ACCESS_TOKEN in .env.")
        return 2

    response = requests.get(
        graph_url("me/accounts"),
        params={
            "fields": "id,name,access_token,instagram_business_account",
            "access_token": token,
        },
        timeout=60,
    )
    response.raise_for_status()
    pages = response.json().get("data", [])
    if not pages:
        page_ids, instagram_ids = debug_token_targets(token)
        if page_ids:
            print("No Pages returned by /me/accounts; using debug_token page targets.")
        for page_id in page_ids:
            page_response = requests.get(
                graph_url(page_id),
                params={
                    "fields": "id,name,access_token,instagram_business_account",
                    "access_token": token,
                },
                timeout=60,
            )
            if not page_response.ok:
                print(f"- page_id={page_id} HTTP {page_response.status_code}: {page_response.text}")
                continue
            page = page_response.json()
            if "instagram_business_account" not in page and instagram_ids:
                page["instagram_business_account"] = {"id": instagram_ids[0]}
            pages.append(page)
    if not pages:
        print("No Facebook Pages returned for META_USER_ACCESS_TOKEN.")
        print("Regenerate the token with pages_show_list, pages_read_engagement, instagram_basic, instagram_content_publish.")
        return 2

    matches = []
    for page in pages:
        ig_account = page.get("instagram_business_account") or {}
        has_ig = bool(ig_account.get("id"))
        has_page_token = bool(page.get("access_token"))
        print(
            f"- {page.get('name')} page_id={page.get('id')} "
            f"instagram_user_id={ig_account.get('id') or '(not connected)'} "
            f"page_token={'present' if has_page_token else 'missing'}"
        )
        if has_ig and has_page_token:
            matches.append(page)

    if not args.write_env:
        print("Run with --write-env to save the first connected Page token and Instagram ID to .env.")
        return 0
    if not matches:
        print("No Page had both a Page access token and connected Instagram professional account.")
        return 2
    selected = matches[0]
    ig_account = selected["instagram_business_account"]
    set_dotenv_values(
        env_path,
        {
            "META_PAGE_ACCESS_TOKEN": selected["access_token"],
            "INSTAGRAM_USER_ID": ig_account["id"],
        },
    )
    print(f"Saved META_PAGE_ACCESS_TOKEN and INSTAGRAM_USER_ID for Page: {selected.get('name')}")
    return 0


def debug_token_targets(user_token):
    app_token = (
        os.environ.get("META_APP_ACCESS_TOKEN")
        or os.environ.get("FACEBOOK_APP_ACCESS_TOKEN")
        or os.environ.get("APP_ACCESS_TOKEN")
    )
    if not app_token:
        return [], []
    response = requests.get(
        "https://graph.facebook.com/debug_token",
        params={"input_token": user_token, "access_token": app_token},
        timeout=60,
    )
    if not response.ok:
        return [], []
    page_ids = []
    instagram_ids = []
    for scope in response.json().get("data", {}).get("granular_scopes", []):
        targets = scope.get("target_ids") or []
        if scope.get("scope", "").startswith("pages_"):
            page_ids.extend(target for target in targets if target not in page_ids)
        if scope.get("scope", "").startswith("instagram_"):
            instagram_ids.extend(target for target in targets if target not in instagram_ids)
    return page_ids, instagram_ids


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Temporarily serve generated Instagram card images and publish them as grouped posts."
    )
    parser.add_argument(
        "--date",
        help="Date folder to publish from instagram_cards/YYYY-MM-DD/public. Defaults to today in Bogota.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Delete publish-state.json for the selected date before publishing.",
    )
    parser.add_argument(
        "--group",
        action="append",
        help="Only publish the named group key. Can be repeated, for example --group medellin.",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    try:
        result = run_serve_publish(args)
    except requests.HTTPError as exc:
        error = meta_error_payload(exc.response) if exc.response is not None else None
        if error and is_non_retryable_meta_error(error):
            print(
                "Meta API error: "
                f"{exc.response.status_code} {exc.response.text}",
                file=sys.stderr,
            )
        else:
            print(f"Meta API error: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
