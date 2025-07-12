import json
import time
import requests
from loguru import logger
from threading import Timer
from queue import Queue, Empty
from urllib.parse import urljoin


class LokiHandler:
    def __init__(self, url, tags=None, batch_size=10, batch_interval=5):
        self.url = urljoin(url, "/loki/api/v1/push")
        self.tags = tags or {}
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.queue = Queue()
        self.batch = []
        self._start_timer()

    def _start_timer(self):
        self.timer = Timer(self.batch_interval, self._send_batch)
        self.timer.daemon = True
        self.timer.start()

    def _send_batch(self):
        if not self.batch:
            self._start_timer()
            return

        payload = {"streams": [{"stream": self.tags, "values": self.batch}]}

        try:
            response = requests.post(
                self.url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=3,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send logs to Loki: {e}")
        finally:
            self.batch = []
            self._start_timer()

    def write(self, message):
        try:
            record = message.record

            # Подготовка данных в формате Loki
            timestamp_ns = int(record["time"].timestamp() * 1e9)
            log_entry = [
                str(timestamp_ns),
                json.dumps(
                    {
                        "message": record["message"],
                        "level": record["level"].name,
                        "file": record["file"].name,
                        "line": record["line"],
                        **record.get("extra", {}),
                    }
                ),
            ]

            self.batch.append(log_entry)

            if len(self.batch) >= self.batch_size:
                self._send_batch()

        except Exception as e:
            logger.error(f"Error in LokiHandler: {e}")

    def stop(self):
        if self.timer:
            self.timer.cancel()
        if self.batch:
            self._send_batch()
