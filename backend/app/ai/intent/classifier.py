import re
from enum import Enum
from typing import Tuple, Dict, Any


class AssistantIntent(str, Enum):
    RESUME_QUESTION = "resume_question"
    BULLET_REWRITE = "bullet_rewrite"
    ATS_QUESTION = "ats_question"
    SKILL_QUESTION = "skill_question"
    JOB_MATCH_QUESTION = "job_match_question"
    GENERAL_CHAT = "general_chat"


class IntentClassifier:
    """
    Robust multi-signal intent classifier.
    Accurately separates resume questions, ATS inquiries, skill audits,
    job match explanations, bullet point refactorings, and general chat.
    """

    # Common greetings and conversational courtesies
    GREETINGS = {
        "hello", "hi", "hey", "greetings", "good morning", "good afternoon",
        "good evening", "thanks", "thank you", "thx", "appreciate it", "bye",
        "goodbye", "help", "can you help me", "can you help", "who are you",
        "what can you do",
    }

    # Action verbs commonly starting bullet points
    BULLET_ACTION_VERBS = {
        "developed", "architected", "engineered", "built", "created", "designed",
        "implemented", "maintained", "spearheaded", "led", "managed", "deployed",
        "optimized", "automated", "refactored", "integrated", "configured",
        "orchestrated", "collaborated", "assisted", "worked", "conducted",
        "analyzed", "established", "streamlined", "enhanced", "resolved",
        "programmed", "coded", "delivered", "executed", "oversaw", "supervised"
    }

    @classmethod
    def classify(cls, message: str) -> Tuple[AssistantIntent, Dict[str, Any]]:
        """
        Classifies user message into AssistantIntent and returns metadata.
        """
        raw = message.strip()
        cleaned = raw.lower().rstrip(".?! ")
        words = re.findall(r"\b\w+\b", cleaned)

        # 1. Check for General Chat (simple greetings or polite phrases)
        if cleaned in cls.GREETINGS or (len(words) <= 3 and any(w in cls.GREETINGS for w in words) and "resume" not in cleaned and "bullet" not in cleaned):
            return AssistantIntent.GENERAL_CHAT, {"reason": "greeting_or_courtesy"}

        # 2. Check for explicit bullet rewrite instructions
        # e.g., "Improve this bullet: Developed a Python API", "Make this ATS friendly: ...", "Rewrite this: ..."
        rewrite_prefixes = [
            r"^(?:please\s+)?(?:improve|rewrite|refactor|enhance|polish|fix)\s+(?:this\s+)?(?:bullet|line|point|statement|achievement|experience)\b(?:\s*[:\-])?\s*(.*)",
            r"^(?:please\s+)?make\s+(?:this\s+)?(?:bullet\s+)?ats(?:\s*|-)(?:friendly|optimized|ready)\b(?:\s*[:\-])?\s*(.*)",
            r"^(?:rewrite|improve|refactor)\s+this\b(?:\s*[:\-])?\s*(.*)",
        ]
        for pattern in rewrite_prefixes:
            match = re.match(pattern, raw, flags=re.IGNORECASE)
            if match:
                extracted_bullet = match.group(1).strip()
                return AssistantIntent.BULLET_REWRITE, {
                    "reason": "explicit_rewrite_command",
                    "extracted_bullet": extracted_bullet if extracted_bullet else raw
                }

        # 3. Check for inquiry / question phrasing
        # Words or syntactic markers indicating asking for guidance, advice, or evaluation
        is_question_syntax = (
            "?" in raw
            or any(cleaned.startswith(qw) for qw in (
                "what", "how", "why", "which", "where", "can i", "should i",
                "could i", "am i", "do i", "is my", "are my", "will",
                "tell me", "give me", "show me", "check my", "review my",
                "analyze my", "evaluate my", "suggest", "what should", "what i"
            ))
            or bool(re.search(r"\b(what|how|why|which|should i|can i|do i|how to)\b", cleaned))
        )

        # 4. Check for ATS Inquiries
        ats_keywords = ["ats", "applicant tracking", "ats score", "ats compatibility", "ats friendly"]
        has_ats_reference = any(k in cleaned for k in ats_keywords)

        if has_ats_reference:
            # If the user asks a question about ATS score or optimization:
            if is_question_syntax or "score" in cleaned or "low" in cleaned or "high" in cleaned or "pass" in cleaned:
                return AssistantIntent.ATS_QUESTION, {"reason": "ats_inquiry"}

        # 5. Check for Skill Inquiries
        skill_keywords = ["skill", "skills", "tech stack", "technologies", "languages", "tools", "competencies", "learn", "upskill", "study"]
        has_skill_reference = any(k in cleaned for k in skill_keywords)

        if has_skill_reference and (is_question_syntax or "missing" in cleaned or "gap" in cleaned or "have" in cleaned or "learn" in cleaned or "next" in cleaned):
            return AssistantIntent.SKILL_QUESTION, {"reason": "skill_inquiry"}

        # 6. Check for Job Match Inquiries
        job_match_keywords = ["job match", "match score", "match percentage", "fit for this job", "matched to this job", "low match", "job description", "match rate"]
        if any(k in cleaned for k in job_match_keywords) and (is_question_syntax or "why" in cleaned or "score" in cleaned or "%" in cleaned):
            return AssistantIntent.JOB_MATCH_QUESTION, {"reason": "job_match_inquiry"}

        # 7. Check for General Resume Questions
        resume_keywords = ["resume", "cv", "experience", "education", "project", "projects", "summary", "weakest", "weakness", "strength", "improve", "improvement"]
        if is_question_syntax or any(k in cleaned for k in resume_keywords):
            # Check if this could actually be a standalone bullet point:
            # Standalone bullet points typically start with a past action verb and lack question markers
            first_word = words[0] if words else ""
            if not is_question_syntax and first_word in cls.BULLET_ACTION_VERBS and len(words) >= 4 and "resume" not in cleaned:
                return AssistantIntent.BULLET_REWRITE, {
                    "reason": "action_verb_bullet_statement",
                    "extracted_bullet": raw
                }
            return AssistantIntent.RESUME_QUESTION, {"reason": "resume_advice_question"}

        # 8. Check for Standalone Bullet Points without prefixes
        # e.g., "Developed a Python API", "Worked on backend development", "Created a React application"
        first_word = words[0] if words else ""
        if first_word in cls.BULLET_ACTION_VERBS or (len(words) >= 2 and words[0] == "worked" and words[1] == "on"):
            return AssistantIntent.BULLET_REWRITE, {
                "reason": "action_verb_bullet_statement",
                "extracted_bullet": raw
            }

        # 9. Fallback based on question indicators or general guidance
        if is_question_syntax:
            return AssistantIntent.RESUME_QUESTION, {"reason": "general_career_question"}

        # Default fallback to general resume question rather than blindly rewriting
        return AssistantIntent.RESUME_QUESTION, {"reason": "default_guidance"}
