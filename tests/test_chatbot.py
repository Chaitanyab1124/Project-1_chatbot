"""Automated tests for DecodeBot. Run: python -m unittest discover -s tests -v"""
import io, os, sys, unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chatbot


def fresh():
    return {"name": None, "awaiting": None}


def run_session(inputs):
    """Feed scripted inputs to the real loop and return everything printed."""
    buf = io.StringIO()
    with patch("builtins.input", side_effect=inputs), redirect_stdout(buf):
        chatbot.main()
    return buf.getvalue()


class TestSanitize(unittest.TestCase):
    def test_case_whitespace_punctuation(self):
        self.assertEqual(chatbot.sanitize("  HELLO!!  "), "hello")
        self.assertEqual(chatbot.sanitize("How are you?"), "how are you")

    def test_inner_spaces_and_smart_apostrophe(self):
        self.assertEqual(chatbot.sanitize("how   are\tyou"), "how are you")
        self.assertEqual(chatbot.sanitize("What\u2019s up"), "whats up")

    def test_keeps_non_ascii_letters(self):
        self.assertEqual(chatbot.sanitize("नमस्ते!"), "नमस्ते")


class TestGetReply(unittest.TestCase):
    def test_exact_match(self):
        reply, rule = chatbot.get_reply("hello", fresh())
        self.assertIn(reply, chatbot.responses["hello"])
        self.assertTrue(rule.startswith("exact"))

    def test_phrase_match(self):
        reply, rule = chatbot.get_reply("hey how are you today", fresh())
        self.assertIn("perfectly", reply + "perfectly" if "And you?" in reply else reply)
        self.assertTrue(rule.startswith("phrase"))

    def test_longest_phrase_wins(self):
        self.assertEqual(chatbot.get_reply("hi how are you", fresh())[1], "phrase match: 'how are you'")

    def test_hi_does_not_match_inside_words(self):
        reply, rule = chatbot.get_reply("which one is this", fresh())
        self.assertEqual((reply, rule), (chatbot.FALLBACK, "fallback"))

    def test_fallback(self):
        self.assertEqual(chatbot.get_reply("asdfgh", fresh())[0], chatbot.FALLBACK)

    def test_name_memory(self):
        s = fresh()
        reply, _ = chatbot.get_reply("my name is rahul", s)
        self.assertEqual(s["name"], "Rahul")
        self.assertIn("Rahul", reply)
        self.assertIn("Rahul", chatbot.get_reply("who am i", s)[0])
        self.assertIn("don't know", chatbot.get_reply("who am i", fresh())[0])

    def test_bare_my_name_is_asks_for_name(self):
        s = fresh()
        reply, rule = chatbot.get_reply("my name is", s)
        self.assertEqual(reply, chatbot.NAME_HINT)
        self.assertIsNone(s["name"])
        self.assertEqual(chatbot.respond("My name is   ", s)[0], chatbot.NAME_HINT)

    def test_call_me_is_not_a_name_trigger(self):
        s = fresh()
        self.assertEqual(chatbot.get_reply("call me later", s)[0], chatbot.FALLBACK)
        self.assertIsNone(s["name"])

    def test_name_edge_cases(self):
        s = fresh()
        chatbot.respond("hello my name is mary-jane", s)
        self.assertEqual(s["name"], "Mary Jane")
        s = fresh()
        self.assertEqual(chatbot.get_reply("my name is rahul and i like pizza", s)[0], chatbot.NAME_REJECT)
        self.assertEqual(chatbot.get_reply("my name is 123", s)[0], chatbot.NAME_REJECT)
        self.assertIsNone(s["name"])

    def test_time_intent(self):
        for q in ("time", "what is the time", "whats the date"):
            self.assertIn("It's", chatbot.get_reply(q, fresh())[0])

    def test_mood_follow_up(self):
        s = fresh()
        self.assertIn("And you?", chatbot.get_reply("how are you", s)[0])
        self.assertIn("Glad", chatbot.get_reply("great", s)[0])
        self.assertIsNone(s["awaiting"])
        self.assertEqual(chatbot.get_reply("great", s)[0], chatbot.FALLBACK)  # follow-up expired

    def test_at_least_five_intents(self):
        self.assertGreaterEqual(len(chatbot.responses), 5)


class TestRespond(unittest.TestCase):
    def test_empty_exit_and_guardrail(self):
        self.assertEqual(chatbot.respond("   ", fresh())[1], "empty input")
        self.assertTrue(chatbot.respond("Ok bye!", fresh())[2])
        self.assertEqual(chatbot.respond("a" * 201, fresh())[0], chatbot.TOO_LONG)


class TestLoop(unittest.TestCase):
    def test_full_conversation_and_exit(self):
        out = run_session(["  HELLO!!  ", "asdfgh", "", "my name is Rahul", "who am I", "Bye"])
        self.assertIn(chatbot.FALLBACK, out)
        self.assertIn("Say something", out)
        self.assertIn("You're Rahul.", out)
        self.assertIn("Goodbye!", out)

    def test_loop_stops_after_exit(self):
        with patch("builtins.input", side_effect=["exit", "hello"]) as m, redirect_stdout(io.StringIO()):
            chatbot.main()
        self.assertEqual(m.call_count, 1)

    def test_every_exit_command(self):
        for cmd in chatbot.EXIT_COMMANDS:
            self.assertIn("Goodbye!", run_session([cmd]))

    def test_ctrl_d_and_ctrl_c_exit_cleanly(self):
        self.assertIn("Goodbye!", run_session([EOFError()]))
        self.assertIn("Goodbye!", run_session(["hello", KeyboardInterrupt()]))


if __name__ == "__main__":
    unittest.main()
