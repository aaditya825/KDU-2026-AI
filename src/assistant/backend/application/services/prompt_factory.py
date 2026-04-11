from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class PromptFactory:
    """Build prompts for the assistant's active routes."""

    _communication_style_map = {
        "neutral": "Use a neutral, direct tone.",
        "friendly": "Use a friendly, approachable tone.",
        "technical": "Use a technical, precise tone.",
        "child_friendly": "Use simple, child-friendly language and examples.",
    }
    _expertise_level_map = {
        "beginner": "Assume the user is a beginner and avoid jargon unless you explain it.",
        "general": "Assume the user has general familiarity and keep explanations balanced.",
        "expert": "Assume the user is expert and include useful detail without oversimplifying.",
    }
    _response_length_map = {
        "short": "Keep the response brief.",
        "medium": "Keep the response moderately concise.",
        "detailed": "Provide a detailed response.",
    }

    def build_general_text_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a practical assistant.\n"
                    "{behavior_instruction}\n"
                    "{accuracy_guardrails}\n"
                    "{output_semantics}\n"
                    "User name: {user_name}\n"
                    "{communication_style_instruction}\n"
                    "{expertise_instruction}\n"
                    "{response_length_instruction}",
                ),
                MessagesPlaceholder("history"),
                ("human", "{message}"),
            ]
        )
        return prompt.partial(
            behavior_instruction=self.build_behavior_instruction("general_text"),
            accuracy_guardrails=self.build_route_guardrails("general_text"),
            output_semantics=self.build_schema_alignment_instruction("general_text"),
            user_name="User",
            communication_style_instruction=self.build_communication_style_instruction(
                "neutral"
            ),
            expertise_instruction=self.build_expertise_instruction("general"),
            response_length_instruction=self.build_response_length_instruction("medium"),
        )

    def build_weather_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a practical weather assistant.\n"
                    "{behavior_instruction}\n"
                    "{accuracy_guardrails}\n"
                    "{output_semantics}\n"
                    "User name: {user_name}\n"
                    "{communication_style_instruction}\n"
                    "{expertise_instruction}\n"
                    "{response_length_instruction}",
                ),
                MessagesPlaceholder("history"),
                (
                    "human",
                    "User: {user_name}\n"
                    "Question: {message}\n"
                    "Location: {location}\n"
                    "Temperature (C): {temperature_c}\n"
                    "Condition: {condition}",
                ),
            ]
        )
        return prompt.partial(
            behavior_instruction=self.build_behavior_instruction("weather_text"),
            accuracy_guardrails=self.build_route_guardrails("weather_text"),
            output_semantics=self.build_schema_alignment_instruction("weather_text"),
            user_name="User",
            communication_style_instruction=self.build_communication_style_instruction(
                "neutral"
            ),
            expertise_instruction=self.build_expertise_instruction("general"),
            response_length_instruction=self.build_response_length_instruction("medium"),
        )

    def build_weather_tool_call_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a weather tool-calling assistant. "
                    "You must call the get_current_weather tool exactly once using the provided resolved_location. "
                    "Do not answer in natural language before the tool call.",
                ),
                (
                    "human",
                    "User: {user_name}\n"
                    "Original question: {message}\n"
                    "resolved_location: {resolved_location}",
                ),
            ]
        )

    def build_image_analysis_system_prompt(
        self,
        *,
        user_name: str,
        communication_style: str,
        expertise_level: str,
        preferred_response_length: str,
    ) -> str:
        return "\n".join(
            [
                "You are a practical image-analysis assistant.",
                self.build_behavior_instruction("image_text"),
                self.build_route_guardrails("image_text"),
                self.build_schema_alignment_instruction("image_text"),
                f"User name: {user_name}.",
                self.build_communication_style_instruction(communication_style),
                self.build_expertise_instruction(expertise_level),
                self.build_response_length_instruction(preferred_response_length),
            ]
        )

    def build_behavior_instruction(self, route: str) -> str:
        if route == "weather_text":
            return (
                "Answer only the weather question being asked and prioritize factual accuracy over style."
            )
        if route == "image_text":
            return (
                "Describe visible content conservatively and prioritize observable facts over interpretation."
            )
        return (
            "Answer only what was asked. If something is uncertain, state uncertainty briefly. "
            "Do not invent context not present in the request or history. Prioritize correctness over style."
        )

    def build_route_guardrails(self, route: str) -> str:
        if route == "weather_text":
            return (
                "Use only the supplied location, temperature_c, and condition fields. "
                "Do not mention forecasts, humidity, wind, causes, or other weather attributes unless they were supplied."
            )
        if route == "image_text":
            return (
                "Describe only visible content. Do not identify people, brands, intent, or hidden context unless clearly visible. "
                "If something is unclear, say that it is unclear."
            )
        return (
            "Do not make unsupported certainty claims or invent facts beyond the request and available history."
        )

    def build_schema_alignment_instruction(self, route: str) -> str:
        if route == "weather_text":
            return (
                "Keep answer consistent with the structured output schema: answer should be a concise weather response, "
                "summary should be short and directly derived from condition, and location/temperature_c must match the supplied data."
            )
        if route == "image_text":
            return (
                "Keep answer consistent with the structured output schema: answer is the user-facing result, "
                "description is a one-sentence visible scene description, summary is short, and objects must contain only concrete visible objects."
            )
        return (
            "Keep answer consistent with the structured output schema and do not introduce fields or claims not supported by the request."
        )

    def build_communication_style_instruction(self, communication_style: str) -> str:
        normalized = self.normalize_communication_style(communication_style)
        return self._communication_style_map[normalized]

    def build_expertise_instruction(self, expertise_level: str) -> str:
        normalized = self.normalize_expertise_level(expertise_level)
        return self._expertise_level_map[normalized]

    def build_response_length_instruction(self, preferred_response_length: str) -> str:
        normalized = self.normalize_response_length(preferred_response_length)
        return self._response_length_map[normalized]

    def normalize_communication_style(self, communication_style: str) -> str:
        value = communication_style.strip().lower()
        return value if value in self._communication_style_map else "neutral"

    def normalize_expertise_level(self, expertise_level: str) -> str:
        value = expertise_level.strip().lower()
        return value if value in self._expertise_level_map else "general"

    def normalize_response_length(self, preferred_response_length: str) -> str:
        value = preferred_response_length.strip().lower()
        return value if value in self._response_length_map else "medium"
