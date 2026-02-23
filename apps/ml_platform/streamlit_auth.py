import os
import json
import base64
import requests
import streamlit as st
import streamlit.components.v1 as components


GATEWAY_API_URL_ENV = "GATEWAY_API_URL"
GATEWAY_API_TOKEN_ENV = "GATEWAY_API_TOKEN"
AUTH_COOKIE_NAME = "ml_platform_auth"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 8


def get_gateway_api_url() -> str:
    url = os.getenv(GATEWAY_API_URL_ENV)
    if not url:
        st.error("GATEWAY_API_URL is not set.")
        st.stop()
    return url


def _init_state() -> None:
    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None
    if "auth_username" not in st.session_state:
        st.session_state.auth_username = None
    if "skip_cookie_restore" not in st.session_state:
        st.session_state.skip_cookie_restore = False
    if "auth_password_input" not in st.session_state:
        st.session_state.auth_password_input = ""
    if "clear_password_next" not in st.session_state:
        st.session_state.clear_password_next = False
    if (not st.session_state.auth_token) and (not st.session_state.skip_cookie_restore):
        _restore_auth_cookie()


def _encode_cookie_payload(token: str, username: str | None) -> str:
    payload = {
        "token": token,
        "username": username or "",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_cookie_payload(raw_value: str) -> dict[str, str] | None:
    try:
        payload_bytes = base64.urlsafe_b64decode(raw_value.encode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        token = payload.get("token")
        username = payload.get("username", "")
        if not token:
            return None
        return {"token": str(token), "username": str(username)}
    except Exception:
        return None


def _set_auth_cookie(token: str, username: str | None) -> None:
    value = _encode_cookie_payload(token, username)
    script = f"""
    <script>
    document.cookie = '{AUTH_COOKIE_NAME}=' + encodeURIComponent('{value}') + '; path=/; max-age={AUTH_COOKIE_MAX_AGE}; SameSite=Lax';
    </script>
    """
    components.html(script, height=0)


def _clear_auth_cookie() -> None:
    script = f"""
    <script>
    // Clear by both Max-Age and Expires for broader browser behavior.
    document.cookie = '{AUTH_COOKIE_NAME}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax';
    </script>
    """
    components.html(script, height=0)


def _restore_auth_cookie() -> None:
    context = getattr(st, "context", None)
    cookies = getattr(context, "cookies", {}) if context else {}
    raw_value = cookies.get(AUTH_COOKIE_NAME)
    if not raw_value:
        return

    entry = _decode_cookie_payload(raw_value)
    if not entry:
        _clear_auth_cookie()
        return

    st.session_state.auth_token = entry.get("token") or None
    st.session_state.auth_username = entry.get("username") or None


def get_auth_token() -> str | None:
    _init_state()
    return st.session_state.auth_token or os.getenv(GATEWAY_API_TOKEN_ENV)


def auth_headers() -> dict:
    token = get_auth_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> tuple[str | None, str | None]:
    if not username or not password:
        return None, "Username and password are required."

    url = get_gateway_api_url()

    try:
        response = requests.post(
            f"{url}/auth/login",
            data={"username": username, "password": password},
            timeout=5,
        )
    except Exception as exc:
        return None, f"Gateway unreachable: {exc}"

    if response.status_code != 200:
        return None, f"Login failed ({response.status_code})."

    payload = response.json()
    if payload.get("error"):
        return None, payload["error"]

    token = payload.get("access_token")
    if not token:
        return None, "Login failed: missing token."

    return token, None


def login_sidebar() -> None:
    _init_state()

    with st.sidebar:
        st.subheader("Authentication")

        if st.session_state.auth_token:
            st.success(
                f"Logged in as {st.session_state.auth_username or 'user'}"
            )
            if st.button("Logout"):
                st.session_state.auth_token = None
                st.session_state.auth_username = None
                # Streamlit's st.context.cookies can reflect cookies captured at
                # connection time. Without this guard, a rerun may immediately
                # restore the old cookie and log the user back in.
                st.session_state.skip_cookie_restore = True
                _clear_auth_cookie()
                st.rerun()
        else:
            env_token = os.getenv(GATEWAY_API_TOKEN_ENV)
            if env_token:
                st.info(
                    "Using GATEWAY_API_TOKEN from environment. "
                    "Login to override."
                )

            username = st.text_input(
                "Username",
                value=st.session_state.auth_username or "user",
                key="auth_username_input",
            )
            if st.session_state.clear_password_next:
                st.session_state.auth_password_input = ""
                st.session_state.clear_password_next = False
            password = st.text_input(
                "Password",
                type="password",
                key="auth_password_input",
            )

            if st.button("Login"):
                token, error = _login(username, password)
                if token:
                    st.session_state.auth_token = token
                    st.session_state.auth_username = username
                    st.session_state.skip_cookie_restore = False
                    st.session_state.clear_password_next = True
                    _set_auth_cookie(token, username)
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error(error or "Login failed.")

        with st.expander("Test credentials"):
            st.code("admin / admin\nuser / user")


def require_auth() -> None:
    login_sidebar()
    if not get_auth_token():
        st.info("Please login to access protected routes.")
        st.stop()


def assert_response_ok(response, *, admin_only: bool = False) -> None:
    if response.status_code in (401, 403):
        if admin_only:
            st.error("Admin privileges required. Login with admin / admin.")
        else:
            st.error(
                "Authentication required. "
                "Login with user / user123 or admin / admin."
            )
        st.stop()

    if response.status_code != 200:
        st.error(response.text)
        st.stop()
