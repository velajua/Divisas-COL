import json
import argparse
import json
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


TOKEN_KEY = "META_PAGE_ACCESS_TOKEN"
USER_TOKEN_KEY = "META_USER_ACCESS_TOKEN"
INSTAGRAM_USER_ID_KEY = "INSTAGRAM_USER_ID"
APP_ID_KEY = "INSTAGRAM_APP_ID"
APP_SECRET_KEY = "INSTAGRAM_APP_SECRET"
META_APP_ID_KEY = "META_APP_ID"
META_APP_SECRET_KEY = "META_APP_SECRET"
APP_TOKEN_KEY = "META_APP_ACCESS_TOKEN"
EXPIRES_AT_KEY = "META_PAGE_ACCESS_TOKEN_EXPIRES_AT"
USER_EXPIRES_AT_KEY = "META_USER_ACCESS_TOKEN_EXPIRES_AT"
REFRESH_THRESHOLD = timedelta(days=10)
GRAPH_BASE_URL = "https://graph.facebook.com"
OAUTH_URL = f"{GRAPH_BASE_URL}/oauth/access_token"


DEBUG = False

def mask_value(value):
    if not value:
        return "<missing>"
    value = str(value)
    if len(value) <= 4:
        return f"***{value}"
    return f"***{value[-4:]}"

def debug_env(env, keys):
    if not DEBUG:
        return
    print("DEBUG env values used:", file=sys.stderr)
    for key in keys:
        print(f"  {key}={mask_value(env.get(key))}", file=sys.stderr)

def safe_params(params):
    safe = {}
    for key, value in params.items():
        if "token" in key.lower() or "secret" in key.lower():
            safe[key] = mask_value(value)
        else:
            safe[key] = value
    return safe

def parse_dotenv(path):
    values = {}
    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def set_dotenv_values(path, values):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    output = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue

        key, _value = line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in remaining:
            output.append(f"{normalized_key}={remaining.pop(normalized_key)}")
        else:
            output.append(line)

    for key, value in remaining.items():
        output.append(f"{key}={value}")

    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def parse_expiration(value):
    clean_value = value.strip()
    if clean_value.isdigit():
        return datetime.fromtimestamp(int(clean_value), tz=timezone.utc)

    parsed = datetime.fromisoformat(clean_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_json(url, params):
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", method="GET")

    if DEBUG:
        print(f"DEBUG request URL: {url}", file=sys.stderr)
        print(f"DEBUG request params: {safe_params(params)}", file=sys.stderr)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")

            if DEBUG:
                print(f"DEBUG response status: {response.status}", file=sys.stderr)

            return json.loads(body)

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            error = payload.get("error", {})
            message = error.get("message") or body
            error_type = error.get("type")
            error_code = error.get("code")
            error_subcode = error.get("error_subcode")
            trace_id = error.get("fbtrace_id")

            raise RuntimeError(
                "Meta Graph API failed: "
                f"HTTP={exc.code}, "
                f"type={error_type}, "
                f"code={error_code}, "
                f"subcode={error_subcode}, "
                f"fbtrace_id={trace_id}, "
                f"message={message}, "
                f"url={url}, "
                f"params={safe_params(params)}"
            ) from exc

        except json.JSONDecodeError:
            raise RuntimeError(
                f"Meta Graph API HTTP {exc.code}: {body or exc.reason}; "
                f"url={url}; params={safe_params(params)}"
            ) from exc


def get_token_expiration(token, app_token):
    payload = get_json(
        f"{GRAPH_BASE_URL}/debug_token",
        {
            "input_token": token,
            "access_token": app_token,
        },
    )
    data = payload.get("data") or {}
    if not data.get("is_valid"):
        raise RuntimeError(f"{TOKEN_KEY} is not valid.")
    expires_at = data.get("expires_at")
    if not expires_at:
        return None
    return parse_expiration(str(expires_at))


def exchange_long_lived_user_token(user_token, app_id, app_secret):
    payload = get_json(
        OAUTH_URL,
        {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": user_token,
        },
    )
    if "access_token" not in payload or "expires_in" not in payload:
        raise RuntimeError("Long-lived user token response did not include access_token and expires_in.")
    return payload


def refresh_page_access_token(user_token, instagram_user_id, app_token):
    pages = []
    payload = get_json(
        f"{GRAPH_BASE_URL}/me/accounts",
        {
            "fields": "id,name,access_token,instagram_business_account",
            "access_token": user_token,
        },
    )
    pages.extend(payload.get("data", []))

    if not pages:
        page_ids, instagram_ids = debug_token_targets(user_token, app_token)
        for page_id in page_ids:
            page = get_json(
                f"{GRAPH_BASE_URL}/{page_id}",
                {
                    "fields": "id,name,access_token,instagram_business_account",
                    "access_token": user_token,
                },
            )
            if "instagram_business_account" not in page and instagram_user_id in instagram_ids:
                page["instagram_business_account"] = {"id": instagram_user_id}
            pages.append(page)

    for page in pages:
        instagram_account = page.get("instagram_business_account") or {}
        if str(instagram_account.get("id")) == str(instagram_user_id) and page.get("access_token"):
            return page["access_token"]
    raise RuntimeError(f"No Page token found for {INSTAGRAM_USER_ID_KEY}={instagram_user_id}.")


def debug_token_targets(user_token, app_token):
    payload = get_json(
        f"{GRAPH_BASE_URL}/debug_token",
        {
            "input_token": user_token,
            "access_token": app_token,
        },
    )
    page_ids = []
    instagram_ids = []
    for scope in payload.get("data", {}).get("granular_scopes", []):
        targets = scope.get("target_ids") or []
        if scope.get("scope", "").startswith("pages_"):
            page_ids.extend(target for target in targets if target not in page_ids)
        if scope.get("scope", "").startswith("instagram_"):
            instagram_ids.extend(target for target in targets if target not in instagram_ids)
    return page_ids, instagram_ids


def should_refresh(expires_at, now):
    return expires_at - now < REFRESH_THRESHOLD


def get_app_credentials(env):
    app_id = env.get(META_APP_ID_KEY) or env.get(APP_ID_KEY)
    app_secret = env.get(META_APP_SECRET_KEY) or env.get(APP_SECRET_KEY)
    return app_id, app_secret


def run(
    env_path=None,
    today=None,
    now=None,
    force=False,
    get_token_expiration=get_token_expiration,
    exchange_long_lived_user_token=exchange_long_lived_user_token,
    refresh_page_access_token=refresh_page_access_token,
):
    current_date = today or date.today()
    if current_date.weekday() != 0 and not force:
        return 0

    env_path = Path(env_path or ".env")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    env = parse_dotenv(env_path)
    debug_env(
        env,
        [
            TOKEN_KEY,
            USER_TOKEN_KEY,
            INSTAGRAM_USER_ID_KEY,
            APP_ID_KEY,
            APP_SECRET_KEY,
            META_APP_ID_KEY,
            META_APP_SECRET_KEY,
            APP_TOKEN_KEY,
            EXPIRES_AT_KEY,
            USER_EXPIRES_AT_KEY,
        ],
    )
    token = env.get(TOKEN_KEY)
    if not token:
        print(f"Missing {TOKEN_KEY} in {env_path}.", file=sys.stderr)
        return 1

    expires_at_value = env.get(EXPIRES_AT_KEY)
    if expires_at_value:
        try:
            expires_at = parse_expiration(expires_at_value)
        except ValueError as exc:
            print(f"Invalid {EXPIRES_AT_KEY}: {exc}", file=sys.stderr)
            return 1
    else:
        app_token = env.get(APP_TOKEN_KEY)
        if not app_token:
            print(f"Missing {APP_TOKEN_KEY} in {env_path}.", file=sys.stderr)
            return 1
        try:
            expires_at = get_token_expiration(token, app_token)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if expires_at is None:
            return 0

    if not should_refresh(expires_at, now):
        return 0

    user_token = env.get(USER_TOKEN_KEY)
    instagram_user_id = env.get(INSTAGRAM_USER_ID_KEY)
    app_token = env.get(APP_TOKEN_KEY)
    if not user_token:
        print(f"Missing {USER_TOKEN_KEY} in {env_path}.", file=sys.stderr)
        return 1
    if not instagram_user_id:
        print(f"Missing {INSTAGRAM_USER_ID_KEY} in {env_path}.", file=sys.stderr)
        return 1
    if not app_token:
        print(f"Missing {APP_TOKEN_KEY} in {env_path}.", file=sys.stderr)
        return 1

    try:
        user_expires_at = get_token_expiration(user_token, app_token)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if user_expires_at is not None:
        app_id, app_secret = get_app_credentials(env)
        if not app_id or not app_secret:
            print(f"Missing app id/app secret credentials to extend {USER_TOKEN_KEY}.", file=sys.stderr)
            return 1
        try:
            exchanged = exchange_long_lived_user_token(user_token, app_id, app_secret)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        user_token = exchanged["access_token"]
        user_expires_at = now + timedelta(seconds=int(exchanged["expires_in"]))

    try:
        new_token = refresh_page_access_token(user_token, instagram_user_id, app_token)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        new_expires_at = get_token_expiration(new_token, app_token)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if new_expires_at is not None:
        print(
            f"Refusing to save short-lived {TOKEN_KEY}; fetched token expires at {new_expires_at.isoformat()}.",
            file=sys.stderr,
        )
        return 1
    values = {
        USER_TOKEN_KEY: user_token,
        TOKEN_KEY: new_token,
        EXPIRES_AT_KEY: "",
    }
    if user_expires_at is not None:
        values[USER_EXPIRES_AT_KEY] = user_expires_at.isoformat()
    set_dotenv_values(
        env_path,
        values,
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Verify and refresh the configured Meta user access token.")
    parser.add_argument("--force", action="store_true", help="Run today even when it is not Monday.")
    args = parser.parse_args()
    raise SystemExit(run(force=args.force))


if __name__ == "__main__":
    main()
