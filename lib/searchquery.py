from pypeg2 import *
import re


class Field(List):
    grammar = Keyword("self"), ".", word, maybe_some(".", word)

    def evaluate(self, obj):
        return self._evaluate_recursive(obj, self)

    def _evaluate_recursive(self, obj, remainingfields):
        values = []

        if hasattr(obj, remainingfields[0]):
            curr = getattr(obj, remainingfields[0])
        else:
            return values

        if isinstance(curr, list):
            if len(remainingfields) == 1:
                for val in curr:
                    values.append(val)
            else:
                for val in curr:
                    values.extend(self._evaluate_recursive(val, remainingfields[1:]))

        else:
            if len(remainingfields) == 1:
                values.append(curr)
            else:
                values.extend(self._evaluate_recursive(curr, remainingfields[1:]))

        return values


class Value(Keyword):
    regex = word

    def convert(self):
        return int(self)


class DecimalNumber(Keyword):
    regex = re.compile("\d+\.\d+")

    def convert(self):
        return float(self)


class Integer(Keyword):
    regex = re.compile("\d+")

    def convert(self):
        return int(self)


class EqualOperator(Keyword):
    grammar = Enum(K("="))
    regex = re.compile("[\=]+")

    def action(self, a, b):
        return a == b

    @staticmethod
    def test():
        parse("=", EqualOperator)


class UnequalOperator(Keyword):
    grammar = Enum(K("!="))
    regex = re.compile("[\!\=]+")

    def action(self, a, b):
        return a != b

    @staticmethod
    def test():
        parse("!=", UnequalOperator)


class Less(Keyword):
    grammar = Enum(K("<"))
    regex = re.compile("[\<]")

    def action(self, a, b):
        return a < b

    @staticmethod
    def test():
        parse("<", Less)


class LessEqual(Keyword):
    grammar = Enum(K("<="))
    regex = re.compile("[\<\=]+")

    def action(self, a, b):
        return a <= b

    @staticmethod
    def test():
        parse("<=", LessEqual)


class Greater(Keyword):
    grammar = Enum(K(">"))
    regex = re.compile("[\>]")

    def action(self, a, b):
        return a > b

    @staticmethod
    def test():
        parse(">", Greater)


class GreaterEqual(Keyword):
    grammar = Enum(K(">="))
    regex = re.compile("[\>\=]+")

    def action(self, a, b):
        return a >= b

    @staticmethod
    def test():
        parse(">=", GreaterEqual)


class And(Keyword):
    grammar = Enum(K("&"))
    regex = re.compile("[\&]")

    def action(self, a, b):
        return a and b


class Or(Keyword):
    grammar = Enum(K("|"))
    regex = re.compile("[\|]")

    def action(self, a, b):
        return a or b


class Equal(List):
    grammar = Field, maybe_some(whitespace), [EqualOperator, UnequalOperator], maybe_some(whitespace), [DecimalNumber, Value]

    def evaluate(self, obj):
        values = self[0].evaluate(obj)
        if len(values) == 0:
            return False
        else:
            result = False
            op = self[1]

            for val in values:
                try:
                    if isinstance(val, int):
                        tmpresult = op.action(val, self[2].convert())
                    elif isinstance(val, float):
                        tmpresult = op.action(val, float(self[2]))
                    else:
                        tmpresult = op.action(val, self[2])
                except ValueError:
                    tmpresult = False

                if tmpresult:
                    result = True
                    break

            return result


class NumberCompare(List):
    grammar = Field, maybe_some(whitespace), [UnequalOperator, EqualOperator, LessEqual, Less, GreaterEqual, Greater], maybe_some(whitespace), [DecimalNumber, Integer]

    def evaluate(self, obj):
        values = self[0].evaluate(obj)
        if len(values) == 0:
            return False
        else:
            result = False
            op = self[1]

            for val in values:
                try:
                    if isinstance(val, int):
                        tmpresult = op.action(val, self[2].convert())
                    elif isinstance(val, float):
                        tmpresult = op.action(val, float(self[2]))
                except ValueError as err:
                    print(err)
                    tmpresult = False

                if tmpresult:
                    result = True
                    break

            return result


class Comparison(List):
    grammar = [Equal, NumberCompare]

    def evaluate(self, obj):
        return self[0].evaluate(obj)


class AndOrUnit(List):
    grammar = Comparison, maybe_some(maybe_some(whitespace), [And, Or], maybe_some(whitespace), Comparison)

    def evaluate(self, obj):
        if len(self) == 1:
            return self[0].evaluate(obj)
        else:
            andunits = []
            currunit = []

            for unit in self:
                if isinstance(unit, Or):
                    andunits.append(currunit)
                    currunit = []
                elif not isinstance(unit, And):
                    currunit.append(unit)
            else:
                andunits.append(currunit)

            result = False
            for andunit in andunits:
                for unit in andunit:
                    tmpresult = unit.evaluate(obj)
                    if tmpresult is False:
                        break  # One statement in an AND group false = whole group is false
                else:
                    # All statements were true, so we don't need to evaluate the rest
                    result = True
                    break

            return result


class BracketedUnit(List):
    grammar = "(", AndOrUnit, ")"

    def evaluate(self, obj):
        return self[0].evaluate(obj)


class QueryGrammar(AndOrUnit):
    grammar = [BracketedUnit, AndOrUnit], maybe_some(maybe_some(whitespace), [And, Or], maybe_some(whitespace), [BracketedUnit, AndOrUnit])


"""tests = ["self.a.B.adsjaAKJD >= 25",
         "self.a.B.adsjaAKJD >= 25",
         "(self.a.B.adsjaAKJD >= 25)",
         "(self.a.B.adsjaAKJD != 25)",
         "(self.a.B.adsjaAKJD >= 25)",
         "self.a.B.adsjaAKJD >= 25 & self.a.B.adsjaAKJD >= 25",
         "(self.a.B.adsjaAKJD >= 25) & self.a.B.adsjaAKJD >= 25 & self.a.B.adsjaAKJD >= 40"]
for test in tests:
    try:
        a = parse(test, QueryGrammar)
        print(a)
    except Exception as err:
        print(err)
        raise"""


class TextObjectOther2(object):
    def __init__(self, b):
        self.b = b


class TestObjectOther(object):
    def __init__(self, a):
        self.a = [TextObjectOther2(10+a), TextObjectOther2(15+a), TextObjectOther2(20+a)]
        self.b = "Hello_There"


class TestObject(object):
    def __init__(self):
        self.a = 123
        self.b = "Hello"
        self.c = [1, 2, 3, 4]
        self.d = [TestObjectOther(1), TestObjectOther(3), TestObjectOther(5)]


def create_query(querytext):
    return parse(querytext, QueryGrammar)

"""
for parser in [EqualOperator, UnequalOperator, Less, LessEqual, Greater, GreaterEqual]:
    parser.test()
    print(parser, "successful")

parse("self.d.a.b >= 25", NumberCompare)
testobject = TestObject()

fieldresult = parse("(self.a != 1 & self.a != 1) & self.a = 1 | self.a != 1", QueryGrammar)
print(fieldresult.evaluate(testobject))"""