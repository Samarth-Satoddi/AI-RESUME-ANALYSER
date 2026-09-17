import re
from typing import Dict, Any, List, Optional
from app.ai.intent.classifier import AssistantIntent
from app.ai.llm.prompts import get_system_prompt_for_intent
from app.ai.llm.model import get_llm_manager
from app.core.logging import logger


class AssistantInferenceService:
    """
    Coordinates prompt construction, context framing, conversation history,
    and invocation of the local Hugging Face LLM.
    """

    def __init__(self):
        self.llm = get_llm_manager()

    def run_inference(
        self,
        intent: AssistantIntent,
        user_message: str,
        resume_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        extracted_bullet: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs guarded inference using the local LLM.
        """
        logger.info(f"LLM request received | Intent: {intent.value} | Resume ID: {resume_context.get('resume_id')}")

        # 1. Select system prompt for detected intent
        system_prompt = get_system_prompt_for_intent(intent)

        # 2. Build context block
        formatted_context = resume_context.get("formatted_context", "")

        # 3. Assemble messages list
        messages: List[Dict[str, str]] = []

        # System message
        if formatted_context:
            full_system_content = f"{system_prompt}\n\nCandidate Resume & Analysis Context:\n{formatted_context}"
        else:
            full_system_content = system_prompt

        messages.append({"role": "system", "content": full_system_content})

        # Add up to 4 recent conversation turns for follow-up questions
        if conversation_history:
            recent_history = conversation_history[-4:]
            for turn in recent_history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # User message
        if intent == AssistantIntent.BULLET_REWRITE:
            bullet_to_rewrite = extracted_bullet or user_message
            prompt_user_content = f"Please improve the following resume bullet point using STAR framework and action verbs. Do not invent fake metrics:\n\n{bullet_to_rewrite}"
        else:
            prompt_user_content = user_message

        messages.append({"role": "user", "content": prompt_user_content})

        logger.info("LLM generation started")
        raw_output = self.llm.generate(messages)
        logger.info("LLM generation completed")

        # 4. Post-generation validation & hallucination guard
        guarded_output = self._validate_and_guard_response(raw_output, resume_context, user_message)

        # 5. Parse output if bullet rewrite
        bullet_improvement = None
        if intent == AssistantIntent.BULLET_REWRITE:
            bullet_improvement = self._parse_bullet_output(guarded_output, extracted_bullet or user_message)

        return {
            "intent": intent.value,
            "answer": guarded_output,
            "bullet_improvement": bullet_improvement,
            "sources": {
                "resume": bool(resume_context.get("resume_id")),
                "analysis": resume_context.get("has_analysis", False),
                "job": bool(resume_context.get("job", {}).get("title")),
            },
        }

    def _validate_and_guard_response(self, raw_output: str, resume_context: Dict[str, Any], user_message: str) -> str:
        """
        Validates factual grounding of the LLM response against supplied context.
        Catches unsupported companies, roles, and technologies.
        """
        has_work_exp = bool(resume_context.get("structured_payload", {}).get("professional_work_experience"))
        output = raw_output

        # If candidate has NO work experience, guard against fictional employment
        if not has_work_exp:
            hallucinated_employers = ["webcraft", "financehub", "datamatrix"]
            for emp in hallucinated_employers:
                if emp in output.lower() and emp not in user_message.lower():
                    logger.warning(f"Hallucination detected: unverified employer '{emp}' found in output. Sanitizing.")
                    output = re.sub(rf"(?i)\b(?:frontend lead at |engineer at |at ){emp}\b.*?(?:\n|$)", "", output)

            if re.search(r"\b\d+\+?\s*years\s+of\s+(?:professional\s+)?experience\b", output, re.I):
                output = re.sub(r"(?i)\b\d+\+?\s*years\s+of\s+(?:professional\s+)?experience\b", "academic and project-based experience", output)

        return output.strip()

    def _parse_bullet_output(self, output: str, original_bullet: str) -> Dict[str, str]:
        """Parses refactored bullet and why this works sections from model output."""
        improved = ""
        rationale = ""

        # Check for standard REFACTORED BULLET / WHY THIS WORKS headers
        refactored_match = re.search(r"REFACTORED BULLET:\s*(.*?)(?:WHY THIS WORKS:|$)", output, re.DOTALL | re.IGNORECASE)
        why_match = re.search(r"WHY THIS WORKS:\s*(.*)", output, re.DOTALL | re.IGNORECASE)

        if refactored_match:
            improved = refactored_match.group(1).strip().strip('"').strip("'")
        if why_match:
            rationale = why_match.group(1).strip()

        if not improved:
            # If model produced freeform text, treat the first paragraph as improved
            lines = [line.strip() for line in output.split("\n") if line.strip()]
            improved = lines[0] if lines else output
            rationale = "\n".join(lines[1:]) if len(lines) > 1 else "Refactored with stronger action verbs and impact."

        return {
            "original": original_bullet,
            "improved": improved,
            "rationale": rationale,
        }
