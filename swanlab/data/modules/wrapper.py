#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
@DATE: 2024/6/3 15:39
@File: wrapper.py
@IDE: pycharm
@Description:
    包装器
"""
from typing import Union, List, Optional

from swanlab.error import DataTypeError
from swanlab.toolkit import ParseResult, ParseErrorInfo, MediaType, ChartReference
from .custom_charts import Echarts
from .line import Line


class DataWrapper:
    """
    数据包装器，负责解析数据，返回相应的数据类型

    一个数据包装器对应swanlab.log字典内的一个key的值
    """

    def __init__(
        self,
        key: str,
        data: Union[List[Line], List[MediaType]],
        reference: ChartReference = "STEP",
    ):
        """
        :param key: key名称，为编码前的名称
        :param data: log的数据
        """
        self.__key = key
        self.__data = data
        self.__error = None
        self.__result: Optional[ParseResult] = None
        self.__reference = reference
        # 保证data内所有数据类型相同，否则返回TypeError
        t = self.__data[0].__class__
        for i in self.__data:
            if i.__class__ != t:
                raise TypeError(f"All data in DataWrapper must be the same type, got {t} and {i.__class__}")

    @property
    def is_line(self) -> bool:
        """
        是否是Line类型
        """
        return isinstance(self.__data[0], Line) and len(self.__data) == 1

    @property
    def is_custom(self) -> bool:
        """
        是否是自定义类型（比如 ECharts）
        """
        return all(isinstance(i, Echarts) for i in self.__data)

    @property
    def type(self):
        """
        数据类型
        """
        return self.__data[0].__class__

    @property
    def parsed(self) -> bool:
        """
        是否已经解析过数据
        """
        return self.__result is not None or self.__error is not None

    @property
    def error(self) -> Optional[ParseErrorInfo]:
        """
        解析时候的错误信息
        """
        return self.__error

    def get_class(self):
        """
        获取数据类型的类名
        """
        return self.__data[0].__class__

    def parse(self, **kwargs) -> Optional[ParseResult]:
        """
        将数据解析成对应的数据类型
        :param kwargs: 传入的参数,必须包含step
        """
        if self.parsed:
            return self.__result
        result = ParseResult(reference=self.__reference)
        result.step = kwargs["step"]  # 挂载step
        d = self.__data[0]
        result.section = d.get_section()
        result.chart = d.get_chart()
        # ---------------------------------- 特别处理Line类型 ----------------------------------

        # [Line]
        if self.type == Line:
            if len(self.__data) > 1:
                self.__error = ParseErrorInfo("float", "list(Line)", result.chart)
            else:
                d.inject(**kwargs)
                try:
                    result.float, _ = d.parse()
                except DataTypeError as e:
                    self.__error = ParseErrorInfo(e.expected, e.got, result.chart)
            self.__result = result
            return self.__result

        # ---------------------------------- 处理其他类型 ----------------------------------
        # [MediaType]
        data, buffers, more = [], [], []
        for i in self.__data:
            try:
                i.inject(**kwargs)
                d, r = i.parse()
            except DataTypeError as e:
                self.__error = ParseErrorInfo(e.expected, e.got, result.chart)
                return None
            data.append(d)
            buffers.append(r)
            more.append(i.get_more())
        result.strings = data
        # 过滤掉空列表
        result.buffers = self.__filter_list(buffers)
        result.more = self.__filter_list(more)
        self.__result = result
        return self.__result

    @staticmethod
    def __filter_list(li: List):
        """
        如果li长度大于0且如果l内部不全是None，返回l，否则返回None
        """
        if len(li) > 0 and any(i is not None for i in li):
            return li
        return None

    @classmethod
    def create_duplicate_error(cls) -> ParseErrorInfo:
        """
        快捷创建一个重复错误
        """
        return ParseErrorInfo(None, None, None, duplicated=True)
