"""Fractions with less overhead."""

import decimal
from decimal import Decimal
import numbers
import operator
import re
import math

from .contextvars_ import ContextVar

__all__ = ['Frac', 'frac', 'div', 'Inf', 'NaN', 'Invalid',
           'frac_from_float_exact', 'frac_from_float_round', 'as_integer_ratio',
           'trunc', 'ceil', 'floor', 'isfinite', 'isinf', 'isnan',
           'assume_positive_zero', 'allow_nans']

assume_positive_zero = ContextVar('fracs.assume_positive_zero', default = False)
allow_nans = ContextVar('fracs.assume_positive_zero', default = False)

def frac(num = 0, den = None, *, float_conv_method = 'if int'):
    """return a fraction that automatically convertes to an int when applicable

    :param num: a number of any type or string, the string may be an int,
      decimal, or a fraction of the form 'num/den'.

    :param den: denominator of fraction, may be an `int` or `Frac`.  If defined
      `num` must also be an `int` or `Frac`.

    :param float_conv_method: one of `disallow`, `if int`, `exact`, or `round`

    :returns: `Frac` or an int

    """
    if den is None:
        if isinstance(num, (int, Frac, NanType)):
            return num

        elif isinstance(num, str):
            # Handle construction from strings.  Adopted from python fractions.py
            m = _RATIONAL_FORMAT.fullmatch(num)
            if m is None:
                raise ValueError(f'invalid literal for fraction: {num!r}')
            if m.group('nan') is not None:
                num = NaN
            elif m.group('inf') is not None:
                num = Inf
            else:
                num = int(m.group('num') or '0')
                denom = m.group('denom')
                if denom:
                    den = int(denom)
                else:
                    den = 1
                    decimal = m.group('decimal')
                    if decimal:
                        scale = 10**len(decimal)
                        num = num * scale + int(decimal)
                        den *= scale
                    exp = m.group('exp')
                    if exp:
                        exp = int(exp)
                        if exp >= 0:
                            num *= 10**exp
                        else:
                            den *= 10**-exp
            if m.group('sign') == '-':
                num = -num
            if den is None: # special value
                return num

        elif isinstance(num, float):
            if float_conv_method == 'disallow':
                raise ValueError('conversion from float to fraction disallowed')
            elif float_conv_method == 'if int':
                if not num.is_integer():
                    raise ValueError('conversion from non-integer float to fraction disallowed')
                return int(num)
            elif float_conv_method == 'exact':
                return frac_from_float_exact(num)
            elif float_conv_method == 'round':
                return frac_from_float_round(num)
            else:
                raise ValueError(f'unknown value for float_conv_method: {float_conv_method!r}')

        elif isinstance(num, Decimal):
            return frac_from_decimal(num)

        else:
            try:
                return tuple.__new__(Frac, (num.numerator, num.denominator))
            except AttributeError:
                pass
            raise TypeError(f"cannot convert '{type(num).__qualname__}' to 'Frac'")

    return div(frac(num), den)

def frac_from_real(other):
    try:
        return frac(*other.as_integer_ratio())
    except:
        pass
    try:
        if math.isinf(other):
            return Frac(1 if other > 0 else -1, 0)
        elif math.isnan(other):
            return NaN
    except:
        pass
    raise TypeError

frac_from_decimal = frac_from_real
frac_from_float_exact = frac_from_real

def frac_from_float_round(other, precision = 15):
    other *= 10 ** precision
    num = round(other)
    return div(num, 10 ** precision)

class Rational(numbers.Number):
    """Abstract base class that includes `int` and `Frac`.

    Differes from `numbers.Rational` in that it is not also a `numbers.Real`.

    To avoid confusion with `numbers.Rational`, it is not exported by default.

    """
    __slots__ = ()
Rational.register(numbers.Rational)

class Frac(tuple,Rational):
    """Streamlined fraction implementation.

    Frac is similar to `fractions.Fraction` except with less overhead.  In the
    general case the speedup is around 2.  When mixing fractions with
    integers, and especially with special values (i.e. 0, 1 and -1), the
    speedup is significantly higher.  Frac differs in several ways from
    Fraction and therefore is not intended to be used as a drop in
    replacement.

    Unlike Fraction, Frac does not freely mix with floats.  For this reason it is
    not a `numbers.Rational`.

    Frac operators will return an int if the denominator is 1.  For this
    reason, Frac's shoud be created with the `frac` or `div` function.  Also,
    to avoid unexpected floats the division operator is not supported and
    instead the previous mentioned `div` function should be used.

    Infinity and NaN is supported.  NaN is a special type with a single value.
    So to test for NaN, it is acceptable to use ``x is NaN``.

    ``hash(Frac)`` is supported, but for speed it is only compatible with
    itself.  The automatic conversion to integers means that
    ``hash(frac(2)) == hash(2)``.  However, ``hash(frac(1,2)) != hash(0.5)``
    and ``hash(frac(1,2)) != hash(fractions.Fraction(1,2))``

    Compression operations will return `Invalid` if either argument is a NaN.
    Attempting to convert `Invalid` to a bool will raise a `ValueError`.  This
    prevents accidental comparasion with NaN and allows NaN to be used as an
    unknown in a limited sense.  If you want the traditional behavior use
    ``(x == y) is True``.  If you want NaN to represent an unknown use
    ``(x == y) is not False``.

    To minimize overhead, Frac is implemented as a tuple, but this should be
    considered an implemenation detail.

    Frac defines `numerator` and `denominator` and uses duck typing so it will
    accept a `Fraction` in operators but will not automatically convert to a
    `Fraction`.

    Format specifiers are also supported.  If the type character is empty it will
    be formated as <num>/<den> otherwise it will be converted to a `Decimal` and
    then formatted.  Trailing zeros are significant when the type
    character is 'g'.  For example, '1.500' represents a fraction close to 3/2
    while '1.5' represents the exact fraction 3/2.

    """
    __slots__ = ()

    def __new__(cls, num, den):
        """construct Frac directly, prefer `frac` function instead"""
        assert(den > 1 or den == 0)
        assert(den != 0 or num != 0)
        g = math.gcd(num,den)
        if g > 1:
            num = num // g
            den = den // g
        return tuple.__new__(cls, (num, den))

    numerator   = property(operator.itemgetter(0))
    numerator.__doc__ = None

    denominator = property(operator.itemgetter(1))
    denominator.__doc__ = None

    def __eq__(self,other):
        try:
            return self[0] == other.numerator and self[1] == other.denominator
        except AttributeError:
            return NotImplemented

    # because we are inheriting from tuple (for performance) we have to define
    # __ne__ otherwise the tuple __ne__ will be used which is not what we want
    def __ne__(self,other):
        try:
            return self[0] != other.numerator or self[1] != other.denominator
        except AttributeError:
            return NotImplemented

    def __compare(op):
        def cmp(self, other):
            try:
                if other.numerator == 0:
                    res = self
                else:
                    res = _add(self[0], self[1], -other.numerator, other.denominator)
            except AttributeError:
                pass
            else:
                return op(res[0], 0)
            if isinstance(other, tuple):
                raise TypeError
            return NotImplemented
        cmp.__doc__ = None
        return cmp

    __lt__ = __compare(operator.lt)
    __le__ = __compare(operator.le)
    __gt__ = __compare(operator.gt)
    __ge__ = __compare(operator.ge)

    __hash__ = tuple.__hash__

    def as_str(self, sign = ''):
        if self[1] == 0:
            if self[0] < 0:
                return '-Inf'
            elif self[0] > 0:
                return ' Inf' if sign == ' ' else '+Inf' if sign == '+' else 'Inf'
        else:
            return ('{:%sn}/{}' % sign).format(self[0], self[1])

    __str__ = as_str

    def __repr__(self):
        if self[1] == 0:
            if self[0] < 0:
                return '-Inf'
            elif self[0] > 0:
                return 'Inf'
        else:
            return '{}({}, {})'.format(type(self).__name__, self[0], self[1])

    def __format__(self, spec):
        if spec == '':
            return str(self)
        else:
            m = _FORMAT_SPEC.fullmatch(spec)
            if m is None:
                raise ValueError(f'Invalid literal for Frac format spec: {spec!r}')
            fill_align, sign, width, precision, type_ = m.groups()
            if type_ == '' or type_ == 's' or self[1] == 0:
                return format(self.as_str(sign), f'{fill_align}{width}s')
            elif precision:
                return format(_FORMAT_CONTEXT.divide(self.numerator,self.denominator), spec)
            else:
                return format(_FORMAT_CONTEXT_9.divide(self.numerator,self.denominator), spec)


    def __pos__(self):
        return self

    def __neg__(self):
        if self[0] == 0:
            return self
        else:
            return tuple.__new__(Frac, (-self[0], self[1]))

    def __abs__(self):
        if self[0] >= 0:
            return self
        else:
            return tuple.__new__(Frac, (-self[0], self[1]))

    def __trunc__(self):
        if self[0] >= 0:
            return self[0] // self[1]
        else:
            return -(-self[0] // self[1])

    def __ceil__(self):
        div, rem = divmod(self[0], self[1])
        return div if rem == 0 else div + 1

    def __floor__(self):
        return self[0] // self[1]

    def __float__(self):
        if self[1] == 0:
            if self[0] > 0:
                return math.inf
            elif self[0] < 0:
                return -math.inf
        return self[0] / self[1]

    def __add__(self, other):
        try:
            if other.numerator == 0:
                return self
            res = _add(self[0], self[1], other.numerator, other.denominator)
            if res[1] == 1:
                return res[0]
            if res[0] == 0 == res[1]:
                return _nan()
            return tuple.__new__(Frac,res)
        except AttributeError:
            return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        try:
            if other.numerator == 0:
                return self
            res = _add(self[0], self[1], -other.numerator, other.denominator)
            if res[1] == 1:
                return res[0]
            if res[0] == 0 == res[1]:
                return _nan()
            else:
                return tuple.__new__(Frac,res)
        except AttributeError:
            return NotImplemented

    def __rsub__(self, other):
        try:
            if other.numerator == 0:
                return tuple.__new__(Frac,(-self[0], self[1]))
            res = _add(other.numerator, other.denominator, -self[0], self[1])
            if res[1] == 1:
                return res[0]
            if res[0] == 0 == res[1]:
                return _nan()
            return tuple.__new__(Frac,res)
        except AttributeError:
            return NotImplemented

    def __mul__(self, other):
        try:
            if other.denominator == 1:
                if other == 1:
                    return self
                elif other == 0 and self[1] != 0:
                    return other
                elif other == -1:
                    return tuple.__new__(Frac, (-self[0], self[1]))
            res = _mul(self[0], self[1], other.numerator, other.denominator)
            if res[1] == 1:
                return res[0]
            if res[0] == 0 == res[1]:
                return _nan()
            return tuple.__new__(Frac,res)
        except AttributeError:
            return NotImplemented

    __rmul__  = __mul__

    def __truediv__(self, other):
        """unimplemented, use `div` function instead"""
        raise NotImplementedError('use div function instead')

    def __rtruediv__(self, other):
        """unimplemented, use `div` function instead"""
        raise NotImplementedError('use div function instead')

    def __copy__(self):
        return self

    def __deepcopy__(self, _):
        return self

class NanType(numbers.Number):
    __slots__= ()

    def __new__(cls):
        return NaN

    def __copy__(self):
        return self
    def __deepcopy__(self, _):
        return self

    def __repr__(self):
        return 'NaN'

    def _cmp(self, other):
        return Invalid

    __eq__ = _cmp
    __ne__ = _cmp
    __lt__ = _cmp
    __le__ = _cmp
    __gt__ = _cmp
    __ge__ = _cmp

    def _unop(self):
        return self

    __pos__ = _unop
    __neg__ = _unop
    __abs__ = _unop

    def _invalidConv(self):
        raise ValueError("attempt to convert NaN to an integer")

    __trunc__ = _invalidConv
    __ceil__ = _invalidConv
    __floor__ = _invalidConv

    def __float__(self):
        return math.nan

    def _binop(self, other):
        return self

    __add__ = _binop
    __radd__ = _binop
    __sub__ = _binop
    __rsub__ = _binop
    __mul__ = _binop
    __rmul__ = _binop
    __truediv__ = _binop
    __rtruediv__ = _binop

Inf = tuple.__new__(Frac, (1, 0))
NaN = object.__new__(NanType)

def div(num, den):
    """equivalent to ``num/den`` but returns a `Frac` or `int` instead of a `float`."""
    if num is NaN or den is NaN:
        return _nan()
    if den.denominator == 1:
        if den == 1:
            return num
        if den == 0:
            if assume_positive_zero.get():
                if num.numerator > 0:
                    return Inf
                elif num.numerator == 0:
                    return NaN
                else:
                    return -Inf
            if allow_nans.get():
                return NaN
            else:
                raise ZeroDivisionError
        if num.denominator == 1:
            num = num.numerator
            if num == 0:
                return _nan() if den == 0 else num
            if den < 0:
                num = -num
                den = -den
            g = math.gcd(num,den)
            if g > 1:
                num = num // g
                den = den // g
            if den == 1:
                return num
            return tuple.__new__(Frac, (num, den))
    den_num, den_den = den.numerator, den.denominator
    if den_num < 0:
        den_num = -den_num
        den_den = -den_den
    res = _mul(num.numerator, num.denominator, den_den, den_num)
    if res[1] == 1:
        return res[0]
    if res[0] == 0 == res[1]:
        return _nan()
    return tuple.__new__(Frac, (res))

def diva(*args):
    """args[0] / args[1] / args[2] / ..."""
    itr = iter(args)
    num = next(itr)
    for den in itr:
        num = div(num, den)
    return num

def as_integer_ratio(num):
    try:
        return (num.numerator, num.denominator)
    except AttributeError:
        pass
    return num.as_integer_ratio()

trunc = math.trunc
ceil = math.ceil
floor = math.floor

def isfinite(num):
    try:
        return num is not NaN and num.denominator != 0
    except AttributeError:
        pass
    return math.isfinite(num)

def isinf(num):
    try:
        return num is not NaN and num.denominator == 0
    except AttributeError:
        pass
    return math.isinf(num)

def isnan(num):
    if num is NaN:
        return True
    if isinstance(num, Frac):
        return False
    return math.isnan(num)

class InvalidType:
    __slots__ = ()
    def __new__(cls):
        return self
    def __bool__(self):
        raise ValueError('attempt to convert comparisons with NaN to bool')
    def __repr__(self):
        return 'Invalid'
    def __copy__(self):
        return self
    def __deepcopy__(self, _):
        return self

Invalid = object.__new__(InvalidType)

class NotANumberError(ArithmeticError):
    pass

#
# Internal helper functions and constants
#

def _nan():
    if allow_nans.get():
        return NaN
    else:
        raise NotANumberError

def _add(na, da, nb, db):
    assert(da >= 0 and db >= 0)
    # adopted from fractions.py with modification to handle Inf, -Inf and NaN
    if da == db:
        if da == 0:
            if na == nb:
                return na, 0
            else:
                return 0, 0
        num = na + nb
        den = da
        if den == 1:
            return num, den
        g = math.gcd(num, den)
        if g > 1:
            num = num // g
            den = den // g
        return num,den
    g = math.gcd(da, db)
    if g <= 1:
        return na * db + da * nb, da * db
    s = da // g
    t = na * (db // g) + nb * s
    g2 = math.gcd(t, g)
    if g2 == 1:
        assert(s * db >= 0)
        return t, s * db
    assert(s * (db // g2) >= 0)
    return t // g2, s * (db // g2)

def _mul(na, da, nb, db):
    assert(da >= 0 and db >= 0)
    # copied from python fractions.py
    g1 = math.gcd(na, db)
    if g1 > 1:
        na //= g1
        db //= g1
    g2 = math.gcd(nb, da)
    if g2 > 1:
        nb //= g2
        da //= g2
    return na * nb, db * da

# adopted from python fractions.py
_RATIONAL_FORMAT = re.compile(r"""
    \A\s*                        # optional whitespace at the start, then
    (?P<sign>[-+]?)              # an optional sign, then
    (?:
      (?P<nan>nan) | (?P<inf>inf|infinity) # specials
      |                          # or
      (?=\d|\.\d)                # lookahead for digit or .digit
      (?P<num>\d*)               # numerator (possibly empty)
      (?:                        # followed by
         (?:/(?P<denom>\d+))?    # an optional denominator
         |                       # or
         (?:\.(?P<decimal>\d*))? # an optional fractional part
         (?:E(?P<exp>[-+]?\d+))? # and optional exponent
      )
    )
    \s*\Z                      # and optional whitespace to finish
""", re.VERBOSE | re.IGNORECASE)

_FORMAT_SPEC = re.compile(r"""
    (.??[<>=^]|) # fill and align
    ([+\-\ ]?)   # sign
    \#?
    \0?
    ([0-9]*)     # width
    [_,]?
    (\.[0-9]+|)  # precision
    (.?)         # type
""", re.VERBOSE | re.ASCII)

_FORMAT_CONTEXT_9 = decimal.Context(prec = 9, rounding=decimal.ROUND_HALF_EVEN)
_FORMAT_CONTEXT = decimal.Context(prec = 28, rounding=decimal.ROUND_HALF_EVEN)
