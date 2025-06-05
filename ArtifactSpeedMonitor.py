from prometheus_client import start_http_server, Gauge, Histogram
import asyncio
import aiohttp
import time
import kubernetes
from kubernetes import client, config

class ArtifactSpeedMonitor:
    def __init__(self):
        self.download_speed = Gauge('artifact_download_speed_mbps', 
            'Download speed in MB/s', ['source', 'artifact_type'])
        self.download_time = Histogram('artifact_download_duration_seconds',
            'Time spent downloading artifacts', ['source', 'artifact_type'])
        self.file_size = Gauge('artifact_size_mb',
            'Size of artifacts in MB', ['source', 'artifact_type'])
        
        self.artifacts = {
            'weights': {
                'azure': 'https://sharkpublic.blob.core.windows.net/sharkpublic/sdxl/v1/model.safetensors',
                'aws': 'YOUR_AWS_URL/sdxl/v1/model.safetensors'
            },
            'mlir': {
                'azure': 'https://sharkpublic.blob.core.windows.net/sharkpublic/sdxl/v1/mlir_model.mlir',
                'aws': 'YOUR_AWS_URL/sdxl/v1/mlir_model.mlir'
            }
        }

    async def measure_download(self, url, source, artifact_type):
        async with aiohttp.ClientSession() as session:
            start = time.time()
            async with session.get(url) as response:
                content = await response.read()
            duration = time.time() - start
            size_mb = len(content) / (1024 * 1024)
            speed_mbps = size_mb / duration

            self.download_speed.labels(source=source, artifact_type=artifact_type).set(speed_mbps)
            self.download_time.labels(source=source, artifact_type=artifact_type).observe(duration)
            self.file_size.labels(source=source, artifact_type=artifact_type).set(size_mb)

    async def run_tests(self):
        while True:
            tasks = []
            for artifact_type, sources in self.artifacts.items():
                for source, url in sources.items():
                    tasks.append(self.measure_download(url, source, artifact_type))
            await asyncio.gather(*tasks)
            await asyncio.sleep(300)  # Test every 5 minutes

def main():
    config.load_incluster_config()
    start_http_server(8000)
    monitor = ArtifactSpeedMonitor()
    asyncio.run(monitor.run_tests())

if __name__ == "__main__":
    main()
