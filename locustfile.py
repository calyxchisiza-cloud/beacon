import os

from locust import HttpUser, between, task


SDK_KEY = os.environ.get("BEACON_SDK_KEY", "")


class Evaluator(HttpUser):
    wait_time = between(0.01, 0.05)

    @task
    def evaluate(self):
        self.client.post(
            "/sdk/v1/evaluate",
            headers={"Authorization": f"Bearer {SDK_KEY}"},
            json={"user": {"key": "user-1", "attributes": {}}, "flag": "payment"},
        )
