import base64
import html
import mimetypes
import uuid

import streamlit as st

from assistant.frontend.api_client import get_available_users, send_chat_message


def _inject_page_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top, rgba(59, 130, 246, 0.16), transparent 28%),
                linear-gradient(180deg, #0b1220 0%, #090f1a 100%);
        }

        .stApp [data-testid="stAppViewContainer"] {
            background: transparent;
        }

        .stApp .block-container {
            padding-bottom: 14rem;
        }

        .stApp [data-testid="stChatMessage"] {
            background: rgba(15, 23, 42, 0.84);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 18px 40px rgba(2, 6, 23, 0.24);
            backdrop-filter: blur(10px);
        }

        .stApp [data-testid="stVerticalBlock"]:has(> [data-testid="element-container"] .assistant-composer-anchor) {
            position: sticky;
            bottom: 0;
            z-index: 30;
            background: linear-gradient(180deg, rgba(9, 15, 26, 0) 0%, rgba(9, 15, 26, 0.92) 16%, rgba(9, 15, 26, 1) 100%);
            padding-top: 1rem;
            margin-top: 1rem;
        }

        .stApp [data-testid="stVerticalBlock"]:has(> [data-testid="element-container"] .assistant-composer-anchor) > div {
            background: rgba(15, 23, 42, 0.96);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 20px;
            padding: 1rem;
            box-shadow: 0 -18px 45px rgba(2, 6, 23, 0.34);
        }

        .assistant-image-card {
            width: fit-content;
            max-width: 100%;
            padding: 0.55rem;
            border-radius: 16px;
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.12);
            margin: 0.25rem 0 0.5rem 0;
        }

        .assistant-image-card img {
            display: block;
            border-radius: 12px;
            object-fit: cover;
        }

        .assistant-image-card.chat img {
            width: min(220px, 100%);
            max-height: 156px;
        }

        .assistant-image-card.composer img {
            width: min(140px, 100%);
            max-height: 96px;
        }

        .assistant-image-meta {
            margin-top: 0.35rem;
            font-size: 0.76rem;
            color: #cbd5e1;
        }

        .assistant-image-hint {
            margin-top: 0.2rem;
            font-size: 0.7rem;
            color: #94a3b8;
        }

        .assistant-settings-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: #cbd5e1;
            margin-bottom: 0.15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_image_data_uri(image_bytes: bytes, image_name: str | None) -> str:
    mime_type, _ = mimetypes.guess_type(image_name or "")
    resolved_mime_type = mime_type or "image/png"
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{resolved_mime_type};base64,{encoded}"


def _render_image_preview(
    image_bytes: bytes,
    image_name: str | None,
    *,
    variant: str,
) -> None:
    escaped_name = html.escape(image_name or "uploaded-image")
    image_data_uri = _build_image_data_uri(image_bytes, image_name)
    st.markdown(
        f"""
        <div class="assistant-image-card {variant}">
            <a href="{image_data_uri}" target="_blank" rel="noopener noreferrer">
                <img src="{image_data_uri}" alt="{escaped_name}" />
            </a>
            <div class="assistant-image-meta">{escaped_name}</div>
            <div class="assistant-image-hint">Click preview to open the full image.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("image_bytes"):
            _render_image_preview(
                message["image_bytes"],
                message.get("image_name"),
                variant="chat",
            )
        st.write(message["content"])
        if message.get("route") == "weather_text":
            weather_details = (
                f'Location: {message.get("location")} | '
                f'Temperature: {message.get("temperature_c")} degrees C'
            )
            st.caption(weather_details)
            if message.get("summary"):
                st.caption(f'Summary: {message["summary"]}')
        if message.get("route") == "image_text":
            if message.get("description"):
                st.caption(f'Description: {message["description"]}')
            if message.get("objects"):
                st.caption(f'Objects: {", ".join(message["objects"])}')
            if message.get("summary"):
                st.caption(f'Summary: {message["summary"]}')
        if message.get("model"):
            st.caption(f'Model: {message["model"]}')
        if message.get("error_type"):
            st.caption(
                f'Type: {message["error_type"]} | Retryable: {message["retryable"]}'
            )


def render_chat_page() -> None:
    _inject_page_styles()
    st.title("Assistant MVP")
    st.caption("Current slice: text, weather, memory, and image analysis")

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    if "composer_input_version" not in st.session_state:
        st.session_state.composer_input_version = 0

    if "available_users" not in st.session_state:
        users_payload = get_available_users()
        st.session_state.available_users = (
            users_payload["data"] if users_payload["ok"] else []
        )
        st.session_state.available_users_error = (
            None if users_payload["ok"] else users_payload["error"]["message"]
        )

    available_users = st.session_state.available_users
    if available_users:
        user_options = [user["user_id"] for user in available_users]
        default_index = user_options.index("default-user") if "default-user" in user_options else 0
        selected_user_id = st.sidebar.selectbox(
            "Active user",
            options=user_options,
            index=default_index,
            key="selected_user_id",
        )
        selected_user = next(
            user for user in available_users if user["user_id"] == selected_user_id
        )
        st.sidebar.caption(f'Name: {selected_user["name"]}')
        st.sidebar.caption(f'Location: {selected_user["location"]}')
    else:
        selected_user_id = "default-user"
        if st.session_state.get("available_users_error"):
            st.sidebar.error(st.session_state.available_users_error)
        st.sidebar.caption("Falling back to default-user.")

    for item in st.session_state.messages:
        _render_message(item)

    composer_container = st.container()
    with composer_container:
        st.markdown('<div class="assistant-composer-anchor"></div>', unsafe_allow_html=True)
        st.markdown("### Response Settings")
        settings_columns = st.columns(3)
        with settings_columns[0]:
            communication_style = st.selectbox(
                "Style",
                options=["neutral", "friendly", "technical", "child_friendly"],
                key="communication_style",
            )
        with settings_columns[1]:
            expertise_level = st.selectbox(
                "Expertise",
                options=["beginner", "general", "expert"],
                index=1,
                key="expertise_level",
            )
        with settings_columns[2]:
            preferred_response_length = st.selectbox(
                "Length",
                options=["short", "medium", "detailed"],
                index=1,
                key="preferred_response_length",
            )

        input_columns = st.columns([0.8, 4.6, 0.9])
        with input_columns[0]:
            with st.popover(":material/attach_file:", help="Upload an image"):
                uploaded_file = st.file_uploader(
                    "Upload image",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f'image_uploader_{st.session_state.uploader_key}',
                )
        with input_columns[1]:
            message = st.text_input(
                "Prompt",
                placeholder="Ask the assistant something",
                label_visibility="collapsed",
                key=f'composer_message_{st.session_state.composer_input_version}',
            )
        with input_columns[2]:
            send_clicked = st.button("Send", use_container_width=True, type="primary")

        if uploaded_file is not None:
            _render_image_preview(
                uploaded_file.getvalue(),
                uploaded_file.name,
                variant="composer",
            )

    if not send_clicked:
        return

    user_image_bytes = uploaded_file.getvalue() if uploaded_file is not None else None
    user_image_name = uploaded_file.name if uploaded_file is not None else None
    user_image_mime_type = uploaded_file.type if uploaded_file is not None else None

    if not message.strip() and user_image_bytes is None:
        st.warning("Enter a prompt or upload an image before sending.")
        return

    user_message = {
        "role": "user",
        "content": message,
        "image_bytes": user_image_bytes,
        "image_name": user_image_name,
    }
    st.session_state.messages.append(user_message)

    payload = send_chat_message(
        message=message,
        session_id=st.session_state.session_id,
        user_id=selected_user_id,
        communication_style=communication_style,
        expertise_level=expertise_level,
        preferred_response_length=preferred_response_length,
        image_bytes=user_image_bytes,
        image_mime_type=user_image_mime_type,
        image_name=user_image_name,
    )

    if payload["ok"]:
        response_data = payload["data"]
        assistant_message = {
            "role": "assistant",
            "content": response_data["answer"],
            "route": response_data.get("route"),
            "model": response_data.get("model"),
            "location": response_data.get("location"),
            "temperature_c": response_data.get("temperature_c"),
            "summary": response_data.get("summary"),
            "description": response_data.get("description"),
            "objects": response_data.get("objects"),
        }
    else:
        error = payload["error"]
        assistant_message = {
            "role": "assistant",
            "content": f'Error: {error["message"]}',
            "error_type": error["type"],
            "retryable": error["retryable"],
        }

    st.session_state.messages.append(assistant_message)
    st.session_state.uploader_key += 1
    st.session_state.composer_input_version += 1
    st.rerun()
