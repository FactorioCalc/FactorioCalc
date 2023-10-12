import math
from unittest import TestCase

from .fracs import *

class TestFracNonFinite(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assume_positive_zero_token = assume_positive_zero.set(True)
        cls.allow_nans_token = allow_nans.set(True)

    @classmethod
    def tearDownClass(cls):
        assume_positive_zero.reset(cls.assume_positive_zero_token)
        allow_nans.reset(cls.allow_nans_token)

    def assertEq(self, a, b):
        if b is NaN:
            self.assertIs(a,b)
        else:
            self.assertEqual(a,b)

    def test_inf_creation(self):
        self.assertEq(Frac(1,0),         Inf)
        self.assertEq(Frac(-1,0),       -Inf)
        self.assertEq(Frac(2,0),         Inf)
        self.assertEq(Frac(-2,0),       -Inf)
        self.assertEq(frac('inf'),       Inf)
        self.assertEq(frac('-inf'),     -Inf)
        self.assertEq(frac('infinity'),  Inf)
        self.assertEq(frac('Infinity'),  Inf)
        self.assertEq(frac('INF'),       Inf)

    def test_nan_creation(self):
        self.assertEq(frac('nan'), NaN)
        self.assertEq(frac('NaN'), NaN)

    def test_non_finite_addition(self):
        for v1 in (Inf, -Inf):
            for v2 in (0,1,frac(1,2),-1,frac(-1,2), v1):
                self.assertEq(v1 + v2, v1)
                self.assertEq(v2 + v1, v1)
        for v in (0,1,frac(1,2),-1,frac(-1,2), Inf, -Inf, NaN):
            self.assertEq(v + NaN, NaN)
            self.assertEq(NaN + v, NaN)
            self.assertEq(v - NaN, NaN)
            self.assertEq(NaN - v, NaN)
        self.assertEq(Inf - Inf, NaN)

    def test_non_finate_mul(self):
        self.assertEq(Inf * Inf, Inf)
        self.assertEq(-Inf * -Inf, Inf)
        self.assertEq(Inf * -Inf, -Inf)
        self.assertEq(Inf * 1, Inf)
        self.assertEq(Inf * -1, -Inf)
        self.assertEq(Inf * 0, NaN)
        self.assertEq(-Inf * 0, NaN)
        self.assertEq(NaN * NaN, NaN)
        self.assertEq(NaN * 1, NaN)
        self.assertEq(1 * NaN, NaN)
        self.assertEq(NaN * frac(1,2), NaN)

    def test_non_finate_div(self):
        self.assertEq(div(1, 0), Inf)
        self.assertEq(div(-1, 0), -Inf)
        self.assertEq(div(0, 0), NaN)
        self.assertEq(div(Inf, Inf),  NaN)
        self.assertEq(div(1, Inf), 0)
        self.assertEq(div(-1, Inf), 0)
        self.assertEq(div(NaN, 1), NaN)
        self.assertEq(div(1, NaN), NaN)

class TestFrac(TestCase):
    def test_decimal_string_conv(self):
        self.assertEqual(frac('1.5'), frac(3,2))
        self.assertEqual(frac('0.5'), frac(1,2))
        self.assertEqual(frac('-0.5'), frac(-1,2))
        self.assertEqual(frac('-1.5'), frac(-3,2))
        self.assertEqual(frac('1.33'), frac(133,100))

    def test_trunc(self):
        self.assertEqual(int(frac('1.5')), 1)
        self.assertEqual(int(frac('0.5')), 0)
        self.assertEqual(int(frac('-0.5')), 0)
        self.assertEqual(int(frac('-1.5')), -1)
        self.assertEqual(math.trunc(frac('1.5')), 1)
        self.assertEqual(math.trunc(frac('0.5')), 0)
        self.assertEqual(math.trunc(frac('-0.5')), 0)
        self.assertEqual(math.trunc(frac('-1.5')), -1)

    def test_floor(self):
        self.assertEqual(math.floor(frac('1.5')), 1)
        self.assertEqual(math.floor(frac('0.5')), 0)
        self.assertEqual(math.floor(frac('-0.5')), -1)
        self.assertEqual(math.floor(frac('-1.5')), -2)

    def test_ceil(self):
        self.assertEqual(math.ceil(frac('1.5')), 2)
        self.assertEqual(math.ceil(frac('0.5')), 1)
        self.assertEqual(math.ceil(frac('-0.5')), 0)
        self.assertEqual(math.ceil(frac('-1.5')), -1)

