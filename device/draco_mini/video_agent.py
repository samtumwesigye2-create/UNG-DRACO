import os
import signal
import subprocess
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class AgentConfig:
    server: str = os.getenv("DRACO_SERVER", "http://127.0.0.1:8000")
    unit_id: str = os.getenv("DRACO_UNIT_ID", "draco-mini-001")
    device_token: str = os.getenv("DRACO_DEVICE_TOKEN", "")
    width: int = int(os.getenv("DRACO_VIDEO_WIDTH", "1280"))
    height: int = int(os.getenv("DRACO_VIDEO_HEIGHT", "720"))
    fps: int = int(os.getenv("DRACO_VIDEO_FPS", "30"))
    bitrate: int = int(os.getenv("DRACO_VIDEO_BITRATE", "2500000"))


class DracoMiniAgent:
    def __init__(self, config: AgentConfig):
        self.config=config; self.process=None
        self.client=httpx.Client(base_url=config.server,timeout=15,headers={"Authorization":f"Bearer {config.device_token}"})

    def register(self):
        response=self.client.post("/api/draco/v1/video/devices/connect",json={"unit_id":self.config.unit_id,"capabilities":["video","snapshot","recording","pan_tilt"]})
        response.raise_for_status(); return response.json()

    def start_camera(self, ingest_url: str):
        cmd=["rpicam-vid","-t","0","--width",str(self.config.width),"--height",str(self.config.height),"--framerate",str(self.config.fps),"--codec","h264","--bitrate",str(self.config.bitrate),"--inline","-o",ingest_url]
        self.process=subprocess.Popen(cmd)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM); self.process.wait(timeout=5)
        self.client.close()

    def run(self):
        delay=1
        while True:
            try:
                registration=self.register(); self.start_camera(registration["ingest_url"]); self.process.wait(); delay=1
            except (httpx.HTTPError,KeyError,OSError,subprocess.SubprocessError):
                time.sleep(delay); delay=min(delay*2,30)


if __name__=="__main__":
    DracoMiniAgent(AgentConfig()).run()
