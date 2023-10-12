import factoriocalc
from factoriocalc import *
from types import MethodType
import json
import unittest
from .common import *

class JsonRoundtripTest:
    __slots__ = ('factory')
    def __init__(self, factory):
        self.factory = factory

    def __get__(self, instance, cls = None):
        if instance is None:
            return self
        return MethodType(self, instance)

    def __call__(self, outer):
        factory = self.factory()
        recipeCache = {}
        jsonObj = toJsonObj(factory, recipeCache)
        jsonStr = json.dumps(jsonObj)
        newJsonObj = json.loads(jsonStr)
        newFactory = fromJsonObj(newJsonObj, recipeCache)
        outer.assertEqual(factory, newFactory)

@unittest.skip('broken')
class JsonRoundtripTests(unittest.TestCase):
    testScienceAndMall = JsonRoundtripTest(lambda: bpBook().find('science+mall').convert())

    testScience2 = JsonRoundtripTest(lambda: bpBook().find('science2').convert())

    testScience3 = JsonRoundtripTest(lambda: bpBook().find('science3').convert())

    testPlasticAndSulfer = JsonRoundtripTest(lambda: bpBook().find('plastic+sulfer').convert())

    testOilStuff = JsonRoundtripTest(lambda: bpBook().find('oil-stuff+lds').convert())

    testCircuits3 = JsonRoundtripTest(lambda: bpBook().find('circuits3').convert())

    testPlastic = JsonRoundtripTest(lambda: bpBook().find('plastic').convert())

    testNuclear = JsonRoundtripTest(lambda: bpBook().find('nuclear').convert())

    testOilStuffBox = JsonRoundtripTest(lambda: Box(
        bpBook().find('oil-stuff+lds').convert()[0],
        priorities = {rcp.solid_fuel_from_petroleum_gas: -1},
        outputTouchups = {itm.plastic_bar: None}))

    testScience3Box = JsonRoundtripTest(lambda: Box(
        bpBook().find('science3').convert()[0],
        inputs = science3inputs,
        priorities = {itm.military_science_pack: -1}))

    #testScience3Box2 = JsonRoundtripTest(lambda: Box(
    #    bpBook().find('science3').convert()[0] + 20 * rcp._combined_research(),
    #    inputs = science3inputs))

    testScience3Summarize = JsonRoundtripTest(lambda: bpBook().find('science3').convert().summarize())

    testScienceB = JsonRoundtripTest(science3Boxed)
