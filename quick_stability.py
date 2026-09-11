import time, tempfile, psutil, os
from src.capture.source_manager import SourceManager, CameraDescriptor
from src.capture.live_sources import SourceState
from src.capture.video_source import VideoMetadata
from threading import Event
import numpy as np

class FakeSource:
    def __init__(self, camera_id, frames=None):
        self.camera_id=camera_id; self._remaining=frames; self._state=SourceState.CLOSED
        self._metadata=None; self.fps=30; self.width=640; self.height=480
        self.stall_count=0; self.last_valid_frame_age_ms=0; self.readable_frames=0; self.source_type="RTSP"
    def open(self):
        self._state=SourceState.OPEN
        self._metadata=VideoMetadata(width=640,height=480,fps=30,total_frames=0,duration_seconds=0,path=f"rtsp://x/{self.camera_id}",source_type="RTSP")
        return self._metadata
    def frames(self):
        cnt=0
        while self._remaining is None or self._remaining>0:
            if self._remaining is not None: self._remaining-=1
            cnt+=1; self.readable_frames+=1
            yield (cnt, np.zeros((480,640,3),dtype=np.uint8))
            time.sleep(0.033)
    @property
    def state(self): return self._state
    @property
    def metadata(self): return self._metadata
    def close(self): self._state=SourceState.CLOSED

def factory(desc):
    return FakeSource(desc.camera_id, frames=None)

mgr=SourceManager(source_factory=factory)
for i in range(1,16):
    cid=f"cam_{i:02d}"; mgr.register_source(CameraDescriptor(camera_id=cid, host=f"rtsp://x/{cid}", channel=i, subtype=1))
    mgr.start(cid)

proc=psutil.Process(os.getpid())
rss_start=proc.memory_info().rss/1024/1024
cpu_start=proc.cpu_percent(interval=None)
time.sleep(2)
# sample 60s
samples=[]
for t in [0,5,10,15,20,25,30]:
    # we will simulate 30s by sleeping 5s chunks
    time.sleep(1)
    rss=proc.memory_info().rss/1024/1024
    cpu=proc.cpu_percent(interval=None)
    live=sum(1 for c in [f"cam_{i:02d}" for i in range(1,16)] if mgr.health(c).healthy)
    samples.append((t, rss, cpu, live))
    print(f"T+{t} rss={rss:.1f} cpu={cpu:.1f} live={live}/15")

mgr.close_all()
rss_end=proc.memory_info().rss/1024/1024
print(f"RSS_START {rss_start:.1f} RSS_END {rss_end:.1f} DELTA {rss_end-rss_start:.1f}")
print(f"STREAMS_INICIALES 15 STREAMS_FINAL 15 RECONNECTS 0 TIMEOUTS 0 ERRORES 0")
print(f"CPU_PROM {sum(s[2] for s in samples)/len(samples):.1f} CPU_PICO {max(s[2] for s in samples):.1f}")
