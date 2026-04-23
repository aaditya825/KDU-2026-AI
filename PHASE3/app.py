import json
import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_PATH = PROJECT_ROOT / "Phase1"

if str(PHASE1_PATH) not in sys.path:
    sys.path.insert(0, str(PHASE1_PATH))

from app_factory import build_orchestrator  # noqa: E402
from config import AppConfig  # noqa: E402


st.set_page_config(
    page_title="Routing Chat UI",
    page_icon="R",
    layout="wide",
)


@st.cache_resource
def get_orchestrator():
    return build_orchestrator()


def usage_value(usage: dict, key: str) -> str:
    value = usage.get(key)
    if value is None:
        return "Not available"
    return str(value)


def render_metadata(entry: dict) -> None:
    decision = entry["decision"]
    response = entry["response"]
    usage = response.get("usage", {})

    st.write("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Routing")
        st.metric("Route", decision["route"])
        st.metric("Route Source", decision["source"])
        with st.expander("Routing Details", expanded=False):
            st.json(decision["metadata"])

    with col2:
        st.subheader("Model & Usage")
        st.metric("Model Used", response["model_id"])
        st.metric("Input Tokens", usage_value(usage, "inputTokens"))
        st.metric("Output Tokens", usage_value(usage, "outputTokens"))
        st.metric("Total Tokens", usage_value(usage, "totalTokens"))
        with st.expander("Model Usage Payload", expanded=False):
            if usage:
                st.json(usage)
            else:
                st.write("Not available")


def main() -> None:
    st.title("Routing Chat UI")
    st.caption("Text-only UI backed by the routing pipeline in Phase1. Each prompt is handled independently.")

    with st.sidebar:
        st.subheader("Backend")
        st.write(f"Casual model: `{AppConfig.CASUAL_MODEL_ID}`")
        st.write(f"Complex model: `{AppConfig.COMPLEX_MODEL_ID}`")
        st.write(f"Router model: `{AppConfig.ROUTER_MODEL_ID}`")
        st.write(f"Embedding model: `{AppConfig.EMBED_MODEL_NAME}`")
        st.write(f"Semantic threshold: `{AppConfig.SEMANTIC_CONFIDENCE_THRESHOLD}`")
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    orchestrator = get_orchestrator()

    for entry in st.session_state.messages:
        with st.chat_message("user"):
            st.write(entry["query"])

        with st.chat_message("assistant"):
            st.write(entry["response"]["text"])
            render_metadata(entry)

    prompt = st.chat_input("Enter your prompt")

    if prompt:
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Routing and generating response..."):
                final_decision, model_response = orchestrator.handle(prompt)

            decision_payload = {
                "route": final_decision.route.value,
                "source": final_decision.source,
                "metadata": final_decision.metadata,
            }
            response_payload = {
                "model_id": model_response.model_id,
                "text": model_response.text,
                "usage": model_response.usage,
            }
            entry = {
                "query": prompt,
                "decision": decision_payload,
                "response": response_payload,
            }

            st.write(model_response.text)
            render_metadata(entry)
            st.session_state.messages.append(entry)

    with st.expander("Session Export", expanded=False):
        st.code(json.dumps(st.session_state.messages, indent=2))


if __name__ == "__main__":
    main()
