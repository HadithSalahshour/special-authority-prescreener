import os
import unittest
from unittest.mock import patch

from sa_checker.local_llm import ollama_url


class LocalOnlyTests(unittest.TestCase):
    def test_default_ollama_endpoint_is_loopback(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ollama_url(), "http://127.0.0.1:11434")

    def test_remote_ollama_endpoint_is_rejected(self):
        with patch.dict(os.environ, {"SA_OLLAMA_URL": "https://example.com"}):
            with self.assertRaisesRegex(RuntimeError, "localhost"):
                ollama_url()


if __name__ == "__main__":
    unittest.main()
