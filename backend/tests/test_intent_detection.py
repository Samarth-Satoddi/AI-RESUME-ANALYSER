import pytest
from app.ai.intent.classifier import IntentClassifier, AssistantIntent


def test_intent_detection_all_minimum_cases():
    cases = [
        ("What should I improve in my resume?", AssistantIntent.RESUME_QUESTION),
        ("What i improve in my resume", AssistantIntent.RESUME_QUESTION),
        ("How can I improve my resume?", AssistantIntent.RESUME_QUESTION),
        ("What skills do I have?", AssistantIntent.SKILL_QUESTION),
        ("What skills am I missing?", AssistantIntent.SKILL_QUESTION),
        ("Why is my ATS score low?", AssistantIntent.ATS_QUESTION),
        ("Developed a Python API", AssistantIntent.BULLET_REWRITE),
        ("Improve this bullet: Developed a Python API", AssistantIntent.BULLET_REWRITE),
        ("Make this ATS friendly: Built a React application", AssistantIntent.BULLET_REWRITE),
        ("Hello", AssistantIntent.GENERAL_CHAT),
    ]

    for user_input, expected_intent in cases:
        intent, meta = IntentClassifier.classify(user_input)
        assert intent == expected_intent, f"Input '{user_input}' failed: expected {expected_intent}, got {intent} (meta={meta})"


def test_intent_detection_additional_variations():
    assert IntentClassifier.classify("Why am I getting a low match for this job?")[0] == AssistantIntent.JOB_MATCH_QUESTION
    assert IntentClassifier.classify("Which section of my resume is weakest?")[0] == AssistantIntent.RESUME_QUESTION
    assert IntentClassifier.classify("How can I improve my experience section?")[0] == AssistantIntent.RESUME_QUESTION
    assert IntentClassifier.classify("Are my projects strong enough?")[0] == AssistantIntent.RESUME_QUESTION
    assert IntentClassifier.classify("What should I learn next?")[0] == AssistantIntent.SKILL_QUESTION
    assert IntentClassifier.classify("Worked on backend development")[0] == AssistantIntent.BULLET_REWRITE
    assert IntentClassifier.classify("Rewrite this: Worked on database management")[0] == AssistantIntent.BULLET_REWRITE
    assert IntentClassifier.classify("Hi")[0] == AssistantIntent.GENERAL_CHAT
    assert IntentClassifier.classify("Can you help me?")[0] == AssistantIntent.GENERAL_CHAT
