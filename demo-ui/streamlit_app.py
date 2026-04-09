from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import requests
import streamlit as st
from requests import Response

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
MAX_LOG_ENTRIES = 10


@dataclass(slots=True)
class LoggedResponse:
    method: str
    url: str
    status_code: int
    duration_ms: int
    request_body: dict[str, Any] | None
    response_body: Any


def pretty(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, default=str)


def initialize_state() -> None:
    st.session_state.setdefault("api_base_url", DEFAULT_API_BASE_URL)
    st.session_state.setdefault("access_token", "")
    st.session_state.setdefault("refresh_token", "")
    st.session_state.setdefault("request_log", [])
    st.session_state.setdefault("example_email", "demo-user@example.com")
    st.session_state.setdefault("example_password", "StrongPass1!")
    st.session_state.setdefault("example_name", "Demo User")


def parse_response_body(response: Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def record_response(
    *,
    method: str,
    url: str,
    status_code: int,
    duration_ms: int,
    request_body: dict[str, Any] | None,
    response_body: Any,
) -> None:
    entry = LoggedResponse(
        method=method,
        url=url,
        status_code=status_code,
        duration_ms=duration_ms,
        request_body=request_body,
        response_body=response_body,
    )
    st.session_state.request_log.insert(0, entry)
    st.session_state.request_log = st.session_state.request_log[:MAX_LOG_ENTRIES]


def api_request(
    *,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    auth: bool = False,
    as_form: bool = False,
) -> Any:
    url = f"{st.session_state.api_base_url}{path}"
    headers: dict[str, str] = {}
    request_body = body.copy() if body else None

    if auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    started_at = perf_counter()
    if method == "GET":
        response = requests.get(url, headers=headers, timeout=15)
    elif as_form:
        response = requests.post(url, headers=headers, data=body, timeout=15)
    else:
        headers["Content-Type"] = "application/json"
        response = requests.request(method, url, headers=headers, json=body, timeout=15)
    duration_ms = round((perf_counter() - started_at) * 1000)

    response_body = parse_response_body(response)
    record_response(
        method=method,
        url=url,
        status_code=response.status_code,
        duration_ms=duration_ms,
        request_body=request_body,
        response_body=response_body,
    )
    return response, response_body


def render_sidebar() -> None:
    st.sidebar.header("Demo Settings")
    st.session_state.api_base_url = st.sidebar.text_input(
        "API Base URL",
        value=st.session_state.api_base_url,
        help="Default target is the local backend under /api/v1.",
    ).strip() or DEFAULT_API_BASE_URL

    if st.sidebar.button("Seed Example Values", use_container_width=True):
        st.session_state.example_email = "demo-user@example.com"
        st.session_state.example_password = "StrongPass1!"
        st.session_state.example_name = "Demo User"

    if st.sidebar.button("Clear Session", use_container_width=True):
        st.session_state.access_token = ""
        st.session_state.refresh_token = ""

    if st.sidebar.button("Clear Request Log", use_container_width=True):
        st.session_state.request_log = []

    st.sidebar.caption(
        "This demo runs outside the backend template runtime. It exists only to "
        "show the API behavior directly."
    )


def render_intro() -> None:
    st.markdown(
        """
        # FastAPI Production Template Demo
        Use this Streamlit app to exercise the backend directly:
        health checks, registration, login, refresh, current user, and admin access.
        """
    )
    st.info(
        "Run the backend first, then start this app with "
        "`streamlit run demo-ui/streamlit_app.py`."
    )


def render_system_section() -> None:
    st.subheader("Health And Version")
    col1, col2, col3 = st.columns(3)
    if col1.button("Liveness", use_container_width=True):
        _, body = api_request(method="GET", path="/health/live")
        st.session_state.system_output = pretty(body)
    if col2.button("Readiness", use_container_width=True):
        _, body = api_request(method="GET", path="/health/ready")
        st.session_state.system_output = pretty(body)
    if col3.button("Version", use_container_width=True):
        _, body = api_request(method="GET", path="/version")
        st.session_state.system_output = pretty(body)

    st.code(st.session_state.get("system_output", "No request yet."), language="json")


def render_register_and_login() -> None:
    left, right = st.columns(2)

    with left:
        st.subheader("Register")
        with st.form("register-form", clear_on_submit=False):
            register_email = st.text_input(
                "Email",
                value=st.session_state.example_email,
                key="register_email",
            )
            register_password = st.text_input(
                "Password",
                value=st.session_state.example_password,
                type="password",
                key="register_password",
            )
            register_name = st.text_input(
                "Full Name",
                value=st.session_state.example_name,
                key="register_name",
            )
            submitted = st.form_submit_button("Create User", use_container_width=True)

        if submitted:
            _, body = api_request(
                method="POST",
                path="/auth/register",
                body={
                    "email": register_email,
                    "password": register_password,
                    "full_name": register_name,
                },
            )
            st.session_state.register_output = pretty(body)

        st.code(st.session_state.get("register_output", "Waiting for submission."), language="json")

    with right:
        st.subheader("Login")
        with st.form("login-form", clear_on_submit=False):
            login_email = st.text_input(
                "Email",
                value=st.session_state.example_email,
                key="login_email",
            )
            login_password = st.text_input(
                "Password",
                value=st.session_state.example_password,
                type="password",
                key="login_password",
            )
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            response, body = api_request(
                method="POST",
                path="/auth/login",
                body={"username": login_email, "password": login_password},
                as_form=True,
            )
            if response.ok and isinstance(body, dict):
                st.session_state.access_token = body.get("access_token", "")
                st.session_state.refresh_token = body.get("refresh_token", "")
            st.session_state.login_output = pretty(body)

        st.code(st.session_state.get("login_output", "Waiting for submission."), language="json")


def render_session_section() -> None:
    st.subheader("Current Session")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Access Token")
        st.code(st.session_state.access_token or "No access token stored.", language="text")
    with col2:
        st.caption("Refresh Token")
        st.code(st.session_state.refresh_token or "No refresh token stored.", language="text")

    if st.button("Refresh Tokens", use_container_width=True):
        if not st.session_state.refresh_token:
            st.session_state.login_output = pretty({"message": "No refresh token stored."})
        else:
            response, body = api_request(
                method="POST",
                path="/auth/refresh",
                body={"refresh_token": st.session_state.refresh_token},
            )
            if response.ok and isinstance(body, dict):
                st.session_state.access_token = body.get("access_token", "")
                st.session_state.refresh_token = body.get("refresh_token", "")
            st.session_state.login_output = pretty(body)


def render_protected_section() -> None:
    left, right = st.columns(2)

    with left:
        st.subheader("Current User")
        if st.button("Load /auth/me", use_container_width=True):
            _, body = api_request(method="GET", path="/auth/me", auth=True)
            st.session_state.me_output = pretty(body)
        st.code(st.session_state.get("me_output", "No request yet."), language="json")

    with right:
        st.subheader("Admin Users")
        if st.button("Load /admin/users", use_container_width=True):
            _, body = api_request(method="GET", path="/admin/users", auth=True)
            st.session_state.admin_output = pretty(body)
        st.code(st.session_state.get("admin_output", "No request yet."), language="json")


def render_request_log() -> None:
    st.subheader("Request Log")
    if not st.session_state.request_log:
        st.caption("Requests you make from this page will appear here.")
        return

    for index, entry in enumerate(st.session_state.request_log, start=1):
        with st.expander(
            f"{index}. {entry.method} {entry.url} | {entry.status_code} | {entry.duration_ms}ms",
            expanded=(index == 1),
        ):
            st.caption("Request")
            st.code(pretty(entry.request_body or "No body"), language="json")
            st.caption("Response")
            st.code(pretty(entry.response_body), language="json")


def main() -> None:
    st.set_page_config(
        page_title="FastAPI Template Demo",
        page_icon="API",
        layout="wide",
    )
    initialize_state()
    render_sidebar()
    render_intro()
    render_system_section()
    render_register_and_login()
    render_session_section()
    render_protected_section()
    render_request_log()


if __name__ == "__main__":
    main()
