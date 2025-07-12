from envparse import Env
import os

env = Env()


class LokiConfig:
    LOKI_URL = env.str("LOKI_UR", default="http://localhost:3100")


loki_conf = LokiConfig()
