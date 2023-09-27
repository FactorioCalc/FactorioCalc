import factoriocalc
from factoriocalc import *
from types import MethodType
import json
import unittest
from .common import *

class SummarizeTest:
    __slots__ = ('factory')
    def __init__(self, factory):
        self.factory = factory

    def __get__(self, instance, cls = None):
        if instance is None:
            return self
        return MethodType(self, instance)

    def __call__(self, outer):
        factory = self.factory()
        res = factory.summarize()
        outer.assertEqual(factory.flows(), res.flows())

class SummarizeTests(unittest.TestCase):

    testScience = SummarizeTest(lambda: bpBook().find('science3').convert()[0])

    testScienceB = SummarizeTest(science3Boxed)

    testOilStuff = SummarizeTest(lambda: bpBook().find('oil-stuff+lds').convert()[0])
