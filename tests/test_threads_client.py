import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from threads_client import ThreadsClient


class StubClient(ThreadsClient):
    def __init__(self):
        super().__init__(access_token="test", sleep=lambda _: None, clock=lambda: 0)
        self.events = []
        self.statuses = iter(
            [
                {"status": "IN_PROGRESS"},
                {"status": "FINISHED"},
            ]
        )

    def create_container(self, *args, **kwargs):
        self.events.append(("create", args, kwargs))
        return "container-1"

    def get_container_status(self, container_id):
        self.events.append(("status", container_id))
        return next(self.statuses)

    def publish_container(self, container_id):
        self.events.append(("publish", container_id))
        return "thread-1"


class ThreadsClientTests(unittest.TestCase):
    def test_post_waits_for_finished_container(self):
        client = StubClient()
        result = client.post(
            "hello",
            image_url="https://example.com/card.png",
            alt_text="English card",
        )
        self.assertEqual(result, "thread-1")
        self.assertEqual([event[0] for event in client.events], ["create", "status", "status", "publish"])

    def test_failed_container_raises(self):
        client = StubClient()
        client.statuses = iter([{"status": "ERROR", "error_message": "bad image"}])
        with self.assertRaisesRegex(RuntimeError, "bad image"):
            client.wait_until_ready("container-1")


if __name__ == "__main__":
    unittest.main()
