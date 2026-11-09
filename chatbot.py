"""
DecodeLabs - Project 1: Rule-Based AI Chatbot
Architecture: Input -> Process -> Output (IPO model)
Run:  python chatbot.py
"""

import random
import re
import unicodedata
from datetime import datetime

# ---------- KNOWLEDGE BASE (key = intent phrase, value = possible replies) ----------
responses = {
    "hello": ["Hi there!", "Hello! How can I help?"],
    "hi": ["Hey!", "Hi! What's up?"],
    "hey": ["Hey there!", "Hey! Good to see you."],
    "namaste": ["Namaste! How can I help?"],
    "good morning": ["Good morning! Hope your day starts well."],
    "good afternoon": ["Good afternoon! What can I do for you?"],
    "good evening": ["Good evening! How can I help?"],
    "how are you": ["I'm running perfectly, thanks!", "All systems operational!"],
    "your name": ["I'm DecodeBot, your first rule-based AI."],
    "who are you": ["I'm DecodeBot, a rule-based chatbot. Every reply comes from a rule."],
    "what can you do": ["I follow if-else rules to chat with you. Try 'help'."],
    "who made you": ["I was built as DecodeLabs Project 1 - a rule-based chatbot."],
    "joke": ["Why do programmers prefer dark mode? Because light attracts bugs.",
             "There are 10 kinds of people: those who understand binary and those who don't."],
    "help": ["Try: hello, how are you, your name, time, joke, my name is <name>, who am i, or bye."],
    "thanks": ["You're welcome!", "Anytime!"],
    "thank you": ["You're welcome!", "Happy to help!"],
}

EXIT_COMMANDS = {"exit", "quit", "bye", "goodbye", "good bye", "bye bye", "ok bye", "okay bye", "see you", "see ya"}
TIME_INTENTS = {"time", "date", "what time is it", "what is the time", "whats the time",
                "current time", "what is the date", "whats the date", "todays date",
                "what is todays date", "what day is it"}
WHO_AM_I = {"who am i", "whats my name", "what is my name", "do you know my name"}
ASK_BACK = {"how are you"}          # intents after which the bot waits for a mood reply
GOOD_MOODS = {"good", "great", "fine", "well", "okay", "ok", "awesome", "happy", "not bad"}
BAD_MOODS = {"bad", "sad", "tired", "sick", "not good", "terrible", "stressed"}

FALLBACK = "I do not understand. Type 'help' to see what I know."
EMPTY_REPLY = "Say something, I'm listening!"
TOO_LONG = "That message is too long for me. Please keep it under 200 characters."
NAME_HINT = "I'd love to know your name. Try: my name is Rahul."
NAME_REJECT = "Please give just your name (up to 3 words), e.g. 'my name is Rahul'."
MAX_INPUT_LEN = 200
_NAME_RE = re.compile(r"(?:^|\s)my name is(?:\s+(.*))?$")


# ---------- PHASE 1: INPUT & SANITIZATION ----------
def sanitize(text):
    """Lowercase, trim, drop apostrophes, turn other punctuation into spaces, collapse spaces."""
    text = text.lower().replace("'", "").replace("\u2019", "").replace("\u2018", "")
    text = "".join(c if (c.isspace() or unicodedata.category(c)[0] in "LMN") else " " for c in text)
    return " ".join(text.split())


def title_case(name):
    return " ".join(w[:1].upper() + w[1:] for w in name.split())


# ---------- PHASE 2: PROCESS (logic) ----------
def time_reply():
    now = datetime.now()
    ampm = "AM" if now.hour < 12 else "PM"
    return (f"It's {now.hour % 12 or 12}:{now.minute:02d} {ampm} on "
            f"{now.strftime('%A')}, {now.day} {now.strftime('%B %Y')}.")


def get_reply(clean, state):
    """Return (reply, rule_used). `state` holds the user's name and any pending follow-up."""
    awaiting, state["awaiting"] = state.get("awaiting"), None

    # Nested condition: the bot asked "and you?", so read this message as a mood
    if awaiting == "mood":
        if clean in GOOD_MOODS:
            return "Glad to hear it! Anything I can help with?", "follow-up: good mood"
        if clean in BAD_MOODS:
            return "Sorry to hear that. Type 'joke' if you want a smile.", "follow-up: bad mood"

    # Name memory
    m = _NAME_RE.search(clean)
    if m:
        raw_name = m.group(1)
        if not raw_name:
            return NAME_HINT, "name memory: missing name"
        if len(raw_name.split()) > 3 or len(raw_name) > 30 or not any(c.isalpha() for c in raw_name):
            return NAME_REJECT, "name memory: rejected"
        state["name"] = title_case(raw_name)
        return f"Nice to meet you, {state['name']}!", "name memory"
    if clean in WHO_AM_I:
        name = state.get("name")
        return (f"You're {name}." if name else "I don't know your name yet."), "name recall"

    # Dynamic intent: time / date
    if clean in TIME_INTENTS:
        return time_reply(), "time intent"

    # 1. Exact match: O(1) dictionary lookup
    options, key, rule = responses.get(clean), clean, f"exact match: '{clean}'"

    # 2. Whole-word phrase match, longest key first ("hello how are you" -> "how are you")
    if not options:
        padded = f" {clean} "
        for k in sorted(responses, key=len, reverse=True):
            if f" {k} " in padded:
                options, key, rule = responses[k], k, f"phrase match: '{k}'"
                break

    if options:
        reply = random.choice(options)
        if key in ASK_BACK:
            reply += " And you?"
            state["awaiting"] = "mood"
        return reply, rule

    # 3. Fallback (hybrid hook: this is where an LLM could be called in a later project)
    return FALLBACK, "fallback"


def respond(raw, state):
    """One full IPO pass. Returns (reply, rule, done)."""
    if len(raw) > MAX_INPUT_LEN:
        return TOO_LONG, "guardrail: input too long", False
    clean = sanitize(raw)
    if clean == "":
        return EMPTY_REPLY, "empty input", False
    if clean in EXIT_COMMANDS:
        return "Goodbye!", "exit command: break", True
    reply, rule = get_reply(clean, state)
    return reply, rule, False


# ---------- PHASE 3: OUTPUT + CONTINUOUS LOOP ----------
def main():
    print("DecodeBot: Hi! Type 'exit' to quit.")
    state = {"name": None, "awaiting": None}

    while True:
        try:
            raw_input = input("You: ")
        except (EOFError, KeyboardInterrupt):   # Ctrl+D / Ctrl+C: leave cleanly
            print("\nDecodeBot: Goodbye!")
            break

        reply, _rule, done = respond(raw_input, state)
        print("DecodeBot:", reply)
        if done:
            break


if __name__ == "__main__":
    main()
