import json

from app_factory import build_orchestrator
from config import AppConfig


def main() -> None:
    orchestrator = build_orchestrator()

    while True:
        user_query = input("Enter User Prompt: ").strip()

        if user_query.lower() in {"exit", "quit"} or not user_query:
            print("Exiting CLI.")
            break

        final_decision, model_response = orchestrator.handle(user_query)

        print("\n=== FINAL ROUTE DECISION ===")
        print(json.dumps({
            "route": final_decision.route.value,
            "source": final_decision.source,
            "metadata": final_decision.metadata,
            "model_id": model_response.model_id,
            "usage": model_response.usage,
            "region": AppConfig.AWS_REGION,
        }, indent=2))

        print("\n=== MODEL RESPONSE ===")
        print(model_response.text)
        print()


if __name__ == "__main__":
    main()
