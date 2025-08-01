#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
@DATE: 2024/4/26 16:03
@File: pytest_main.py
@IDE: pycharm
@Description:
    测试SwanLabRun主类
"""
import io
import json
import math
import os

import nanoid
import numpy as np
import pytest
import soundfile as sf
from PIL import Image as PILImage
from nanoid import generate

import swanlab
import tutils as T
from swanlab import Image, Audio, Text
from swanlab.data.modules import Line
from swanlab.data.run.main import SwanLabRun, get_run, SwanLabRunState, swanlog, get_url, get_project_url
from swanlab.env import SwanLabEnv
from tutils import TEMP_PATH
from tutils.setup import UseMockRunState


@pytest.fixture(scope="function", autouse=True)
def setup_function():
    """
    在当前测试文件下的每个测试函数执行前后执行
    """
    swanlog.disable_log()
    yield
    swanlog.enable_log()
    if get_run() is not None:
        get_run().finish()


class TestSwanLabRunInit:

    def test_before_init(self):
        run = get_run()
        assert run is None
        assert SwanLabRun.get_state() == SwanLabRunState.NOT_STARTED

    def test_after_init(self):
        os.environ[SwanLabEnv.MODE.value] = "disabled"
        with UseMockRunState():
            run = SwanLabRun()
            assert swanlog.proxied is False
            assert run is not None
            assert get_run().__str__() == run.__str__()
            _run = run.finish()
            assert get_run() is None
            assert _run.__str__() == run.__str__()
            assert SwanLabRunState.SUCCESS == _run.state

    def test_duplicate_init(self):
        os.environ[SwanLabEnv.MODE.value] = "disabled"
        with UseMockRunState():
            run = SwanLabRun()
            with pytest.raises(RuntimeError) as e:
                SwanLabRun()
            assert swanlog.proxied is False
            assert str(e.value) == "SwanLabRun has been initialized"
            assert run.__str__() == get_run().__str__()
            _run = run.finish()
            assert swanlog.proxied is False


class TestSwanLabRunState:
    """
    测试SwanLabRun的状态变化
    """

    @staticmethod
    def setup_method():
        os.environ[SwanLabEnv.MODE.value] = "disabled"

    def test_not_started(self):
        assert SwanLabRun.get_state() == SwanLabRunState.NOT_STARTED

    def test_running(self):
        with UseMockRunState():
            run = SwanLabRun()
            assert run.state == SwanLabRunState.RUNNING
            assert run.running is True

    def test_crashed(self):
        with UseMockRunState():
            run = SwanLabRun()
            run.finish(SwanLabRunState.CRASHED, error="error")
            assert run.state == SwanLabRunState.CRASHED
            assert run.crashed is True

    def test_success(self):
        with UseMockRunState():
            run = SwanLabRun()
            run.finish(SwanLabRunState.SUCCESS)
            assert run.state == SwanLabRunState.SUCCESS
            assert run.success is True


class TestSwanLabRunLog:
    """
    测试SwanLabRun的日志解析功能，不包含操作员，由于情况比较多，这里分情况测试
    1. 一开始正常输入，然后重复输入，然后输入新的key的重复的step
    2. 一开始输入错误的类型，然后正常输入
    3. 一开始输入正确的类型，然后输入错误的类型
    """

    @staticmethod
    def setup_method():
        os.environ[SwanLabEnv.MODE.value] = "disabled"

    # ---------------------------------- 返回的列信息将包含id ----------------------------------

    def test_log_column_with_id(self):
        """
        id为当前创建列前历史列数量
        """
        with UseMockRunState() as run_state:
            run = SwanLabRun()
            data = {"a": 1, "b": 2}
            ll = run.log(data)
            assert len(ll) == 2
            assert ll["a"].column_info.kid == "0"
            assert ll["b"].column_info.kid == "1"

    # ---------------------------------- 解析log数字/Line ----------------------------------
    def test_log_number_ok(self):
        with UseMockRunState():
            run = SwanLabRun()
            data = {"a": 1, "b": 0.1, "c": {"d": 2}, "math.nan": math.nan, "math.inf": math.inf}
            ll = run.log(data)
            assert len(ll) == 5
            # 都没有错误
            assert all([ll[k].is_error is False for k in ll])
            assert ll["a"].data == 1
            assert ll["b"].data == 0.1
            assert ll["c.d"].data == 2
            assert ll["math.nan"].data == Line.nan
            assert ll["math.inf"].data == Line.inf
            assert all([ll[k].column_info.chart_type == ll[k].column_info.chart_type.LINE for k in ll])
            # 没有其他多余的内容
            assert all([ll[k].buffers is None for k in ll])
            assert all([ll[k].data is not None for k in ll])
            # 没有指定step的话从0开始
            assert all([ll[k].metric_step == 0 for k in ll])
            ll2 = run.log(data, step=3)
            assert all(ll2[k].metric_step == 3 for k in ll2)
            # 重复的step会被忽略
            ll3 = run.log(data, step=3)
            assert all(ll3[k].is_error for k in ll3)
            assert all(ll3[k].error.duplicated for k in ll3)
            assert all(ll3[k].column_error is None for k in ll3)
            assert all(ll3[k].error is not None for k in ll3)
            # 如果是新的key的重复step，会被添加
            ll4 = run.log({"tmp": 1}, step=3)
            assert all(ll4[k].is_error is False for k in ll4)
            assert all(ll4[k].metric_step == 3 for k in ll4)

    def test_log_number_use_line(self):
        """
        使用Line类型log，本质上应该与数字类型一样，数字类型是Line类型的语法糖
        """
        with UseMockRunState():
            run = SwanLabRun()
            data = {
                "a": Line(1),
                "b": Line(0.1),
                "c": {"d": Line(2)},
                "math.nan": Line(math.nan),
                "math.inf": Line(math.inf),
            }
            ll = run.log(data)
            assert len(ll) == 5
            # line(1)和[line(1)]是一样的
            ll2 = run.log({"a": [Line(1)]})
            assert ll2["a"].data == ll["a"].data
            # Line类型不允许多个元素
            ll3 = run.log({"a": [Line(1), Line(2)]})
            assert ll3["a"].is_error is True
            assert ll3["a"].column_error is None
            assert ll3["a"].error.expected == 'float'

    def test_log_number_error_type(self):
        """
        使用错误的，不受支持的类型log
        """
        with UseMockRunState():
            run = SwanLabRun()
            data = {"a": "a", "b": [1], "c": 1}
            ll = run.log(data)
            assert len(ll) == 3
            # 前两个错误，最后一个正确
            assert ll["a"].is_error is True
            assert ll["b"].is_error is True
            assert ll["c"].is_error is False

            assert ll["a"].column_error is not None
            assert ll["b"].column_error is not None
            assert ll["c"].column_error is None

            assert ll["a"].column_error.expected == 'float'
            assert ll["b"].column_error.expected == 'float'
            assert ll["c"].data == 1

            assert ll["a"].error == ll['a'].column_error
            assert ll["b"].error == ll['b'].column_error

    # ---------------------------------- 解析log文字 ----------------------------------

    def test_log_text_ok(self):
        with UseMockRunState():
            run = SwanLabRun()
            data = {"a": Text("abc"), "b": Text("def")}
            ll = run.log(data)
            assert len(ll) == 2
            assert all([ll[k].is_error is False for k in ll])
            assert ll["a"].data == ["abc"]
            assert ll["b"].data == ["def"]
            assert all([ll[k].column_info.chart_type == ll[k].column_info.chart_type.TEXT for k in ll])
            assert all([ll[k].buffers is None for k in ll])
            assert all([ll[k].data is not None for k in ll])
            assert all([ll[k].metric_step == 0 for k in ll])
            ll2 = run.log(data, step=3)
            assert all(ll2[k].metric_step == 3 for k in ll2)
            # list
            ll3 = run.log({"a": [Text("abc"), Text("def")]})
            assert ll3["a"].data == ["abc", "def"]
            data = {"a": [Text("abc")] * 109}
            ll4 = run.log(data, step=4)
            assert ll4["a"].data == ["abc"] * 108

    # ---------------------------------- 解析log Audio ----------------------------------

    @staticmethod
    def check_audio(ll: dict, key: str):
        with UseMockRunState():
            assert len(ll[key].buffers) == 1
            buffer = ll[key].buffers[0]
            audio, _samplerate = sf.read(io.BytesIO(buffer.getvalue()))
            assert _samplerate == 5000
            # FIXME 一维的？
            assert len(audio.shape) == 1

    def test_log_audio_path(self):
        """
        通过路径添加音频
        """
        with UseMockRunState():
            run = SwanLabRun()
            # 正确的音频路径
            path = os.path.join(TEMP_PATH, "test.wav")
            samplerate = 5000
            sf.write(path, np.random.rand(1000), samplerate)
            data = {"a": Audio(path)}
            ll = run.log(data)
            self.check_audio(ll, "a")

    def test_log_audio_numpy(self):
        """
        通过numpy数组添加音频
        """
        with UseMockRunState():
            run = SwanLabRun()
            samplerate = 5000
            data = {"a": Audio(np.random.rand(1000), samplerate)}
            ll = run.log(data)
            self.check_audio(ll, "a")

    def test_log_audio_error(self):
        """
        错误的情况
        """
        with UseMockRunState():
            run = SwanLabRun()
            # 错误的路径
            with pytest.raises(ValueError):
                run.log({"a": Audio("error.wav")})
            # 错误的类型
            with pytest.raises(TypeError):
                run.log({"a": Audio(1)})  # noqa
            # 错误的矩阵编码类型
            with pytest.raises(TypeError):
                run.log({"a": Audio(np.random.rand(1000).astype(np.int8))})
            # 错误的矩阵维数
            with pytest.raises(TypeError):
                run.log({"a": Audio(np.random.rand(1000, 5))})

    # ---------------------------------- 图像 ----------------------------------
    @staticmethod
    def check_image(ll: dict, key: str):
        assert len(ll[key].buffers) == 1
        buffer = ll[key].buffers[0]
        image = PILImage.open(io.BytesIO(buffer.getvalue()))
        assert image.size == (100, 100)

    def test_log_image_path(self):
        """
        通过路径添加图像
        """
        with UseMockRunState():
            run = SwanLabRun()
            # 正确的图像路径
            path = os.path.join(TEMP_PATH, "test.png")
            PILImage.new("RGB", (100, 100)).save(path)
            data = {"a": Image(path)}
            ll = run.log(data)
            self.check_image(ll, "a")

    def test_log_image_numpy(self):
        """
        通过numpy数组添加图像
        """
        with UseMockRunState():
            run = SwanLabRun()
            data = {"a": Image(np.random.rand(100, 100, 3))}
            ll = run.log(data)
            self.check_image(ll, "a")

    # ---------------------------------- echarts ----------------------------------
    def test_log_echarts(self):
        with UseMockRunState():
            run = SwanLabRun()
            data = {"a": swanlab.echarts.Bar().add_xaxis(["X", "Y"]).add_yaxis("数值", [10, 20])}
            ll = run.log(data)
            assert len(ll['a'].buffers) == 1
            buffer = ll['a'].buffers[0]
            chart_data = json.loads(buffer.getvalue().decode("utf-8"))
            assert isinstance(chart_data, dict)

    # 其他类似...


class TestGetUrl:

    @pytest.mark.skipif(T.is_skip_cloud_test, reason="skip cloud test")
    def test_ok(self):
        """
        初始化一个实验
        """
        exp_name = generate()
        project_name = generate()
        swanlab.init(project=project_name, experiment_name=exp_name, mode="cloud")
        assert get_url() is not None and get_url() != ""

    def test_local(self):
        """
        本地模式
        """
        swanlab.init(mode="local")
        assert get_url() is None

    def test_before_init(self):
        """
        未初始化
        """
        assert get_url() is None


class TestGetProjectUrl:

    @pytest.mark.skipif(T.is_skip_cloud_test, reason="skip cloud test")
    def test_ok(self):
        """
        初始化一个实验
        """
        exp_name = generate()
        project_name = generate()
        swanlab.init(project=project_name, experiment_name=exp_name, mode="cloud")
        assert get_project_url() is not None and get_project_url() != ""
        assert get_project_url().endswith(project_name)

    def test_local(self):
        """
        本地模式
        """
        swanlab.init(mode="local")
        assert get_project_url() is None

    def test_before_init(self):
        """
        未初始化
        """
        assert get_project_url() is None


@pytest.mark.parametrize(
    "mode,run_id",
    [
        ("cloud", nanoid.generate('0123456789abcdefghijklmnopqrstuvwxyz', 21)),
        ("local", None),
        ("disabled", None),
        ("offline", None),
    ],
)
def test_run_id(mode, run_id):
    """
    测试获取当前运行的ID
    只有 cloud 模式能获取到运行ID，其他模式返回None
    """
    os.environ[SwanLabEnv.MODE.value] = mode
    with UseMockRunState() as state:
        state.store.run_id = run_id if mode == "cloud" else state.store.run_id
        run = SwanLabRun()
        assert run.id == run_id


def test_run_id_none():
    """
    测试在未初始化时获取运行ID
    """
    with UseMockRunState() as state:
        state.store.run_id = None
        with pytest.raises(AssertionError):
            SwanLabRun()
