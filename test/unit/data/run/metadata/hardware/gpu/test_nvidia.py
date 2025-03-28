"""
@author: cunyue
@file: test_nvidia.py
@time: 2024/12/5 13:27
@description: 测试NVIDIA GPU信息采集
"""

import pynvml
import pytest

from swanlab.data.run.metadata.hardware.gpu.nvidia import GpuCollector


try:
    pynvml.nvmlInit()
    count = pynvml.nvmlDeviceGetCount()
    max_gpu_mem = pynvml.nvmlDeviceGetMemoryInfo(pynvml.nvmlDeviceGetHandleByIndex(0)).total >> 20
except Exception:  # noqa
    count = 0
    max_gpu_mem = 0

@pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
def test_before_impl():
    collector = GpuCollector(count, max_gpu_mem)
    collector.before_collect_impl()
    assert len(collector.handles) == count


@pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
def test_after_impl():
    collector = GpuCollector(count, max_gpu_mem)
    collector.after_collect_impl()
    assert len(collector.handles) == 0


class TestGpuCollector:
    collector = GpuCollector(count, max_gpu_mem)

    def setup_class(self):
        self.collector.before_collect_impl()

    def teardown_class(self):
        self.collector.after_collect_impl()

    @pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
    def test_get_mem(self):
        # 获取handle
        idx = 0
        mem = self.collector.get_gpu_mem_pct(idx=idx)
        assert mem['name'] == "GPU 0 Memory Allocated (%)"
        assert mem['config'].y_range == (0, 100)
        assert mem['config'].metric_name == "GPU 0"
        assert 100 >= mem['value'] >= 0

    @pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
    def test_get_mem_value(self):
        # 获取handle
        idx = 0
        mem = self.collector.get_gpu_mem_value(idx=idx)
        assert mem['name'] == "GPU 0 Memory Allocated (MB)"
        assert mem['config'].y_range == (0, max_gpu_mem)
        assert mem['config'].metric_name == "GPU 0"
        assert mem['value'] >= 0

    @pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
    def test_get_utils(self):
        # 获取handle
        idx = 0
        utils = self.collector.get_gpu_util(idx=idx)
        assert utils['name'] == "GPU 0 Utilization (%)"
        assert utils['config'].y_range == (0, 100)
        assert utils['config'].metric_name == "GPU 0"
        assert 100 >= utils['value'] >= 0

    @pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
    def test_get_temp(self):
        # 获取handle
        idx = 0
        temp = self.collector.get_gpu_temp(idx=idx)
        assert temp['name'] == "GPU 0 Temperature (℃)"
        assert temp['config'].y_range is None
        assert temp['config'].metric_name == "GPU 0"
        assert temp['value'] >= 0
        assert temp['config'].metric_name == "GPU 0"

    @pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
    def test_get_power(self):
        # 获取handle
        idx = 0
        power = self.collector.get_gpu_power(idx=idx)
        assert power['name'] == "GPU 0 Power Usage (W)"
        assert power['config'].y_range is None
        assert power['config'].metric_name == "GPU 0"
        assert power['value'] >= 0
        assert power['config'].metric_name == "GPU 0"

    @pytest.mark.skipif(count == 0, reason="No NVIDIA GPU found")
    def test_get_mem_time(self):
        # 获取handle
        idx = 0
        time = self.collector.get_gpu_mem_time(idx=idx)
        assert time['name'] == "GPU 0 Time Spent Accessing Memory (%)"
        assert time['config'].y_range == (0, 100)
        assert time['config'].metric_name == "GPU 0"
        assert 100 >= time['value'] >= 0
        assert time['config'].metric_name == "GPU 0"
