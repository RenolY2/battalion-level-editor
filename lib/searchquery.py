import re
import os
from pypeg2 import *
from numpy import float32

fieldnames = {}
autocomplete = []
autocompletebw2 = []

autocompletefull = []


def load_autocomplete(fpath):
    result = []
    fullnames = {}
    with open(fpath, "r") as f:
        for fieldname in f:
            fieldname = fieldname.strip()
            result.append(fieldname)

            wordlower = fieldname.lower()
            if wordlower in fullnames:
                fullnames[wordlower].append(fieldname)
            else:
                fullnames[wordlower] = [fieldname]

    return result, fullnames

currpath = __file__
currdir = os.path.dirname(currpath)

autocomplete, fieldnames = load_autocomplete(os.path.join(currdir, "fieldnames.txt"))
autocompletebw2, fieldnamesbw2 = load_autocomplete(os.path.join(currdir, "fieldnamesbw2.txt"))
autocompletevalues, valuenames = load_autocomplete(os.path.join(currdir, "values.txt"))
autocompletevaluesbw2, valuenamesbw2 = load_autocomplete(os.path.join(currdir, "valuesbw2.txt"))


class Field(List):
    grammar = Keyword("self"), optional(".", word, maybe_some(".", word))

    def evaluate(self, obj):
        if len(self) == 0:
            return [obj]
        else:
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

    def convert_bool(self):
        if self.lower() in ("true", "etrue"):
            return True
        elif self.lower() in ("false", "efalse"):
            return False
        else:
            raise ValueError("Value should be True or False")


class DecimalNumber(Keyword):
    regex = re.compile(r"\d+\.\d+")

    def convert(self):
        return float(self)


class Integer(Keyword):
    regex = re.compile(r"\d+")

    def convert(self):
        return int(self)


class EqualOperator(Keyword):
    grammar = Enum(K("="))
    regex = re.compile(r"[=]+")

    def action(self, a, b):
        return a == b

    @staticmethod
    def test():
        parse("=", EqualOperator)


class UnequalOperator(Keyword):
    grammar = Enum(K("!="))
    regex = re.compile(r"[!=]+")

    def action(self, a, b):
        return a != b

    @staticmethod
    def test():
        parse("!=", UnequalOperator)


class Less(Keyword):
    grammar = Enum(K("<"))
    regex = re.compile(r"[<]")

    def action(self, a, b):
        return a < b

    @staticmethod
    def test():
        parse("<", Less)


class LessEqual(Keyword):
    grammar = Enum(K("<="))
    regex = re.compile(r"[<=]+")

    def action(self, a, b):
        return a <= b

    @staticmethod
    def test():
        parse("<=", LessEqual)


class Greater(Keyword):
    grammar = Enum(K(">"))
    regex = re.compile(r"[>]")

    def action(self, a, b):
        return a > b

    @staticmethod
    def test():
        parse(">", Greater)


class GreaterEqual(Keyword):
    grammar = Enum(K(">="))
    regex = re.compile(r"[>=]+")

    def action(self, a, b):
        return a >= b

    @staticmethod
    def test():
        parse(">=", GreaterEqual)


class References(Keyword):
    grammar = Enum(K("references"))

    def action(self, a, b):
        return b.lower() in a.get_pointers()


class Contains(Keyword):
    grammar = Enum(K("contains"))

    def action(self, a, b):
        return b.lower() in a.lower()


class Excludes(Keyword):
    grammar = Enum(K("excludes"))

    def action(self, a, b):
        return b.lower() not in a.lower()


class And(Keyword):
    grammar = Enum(K("&"))
    regex = re.compile("[&]")

    def action(self, a, b):
        return a and b


class Or(Keyword):
    grammar = Enum(K("|"))
    regex = re.compile("[|]")

    def action(self, a, b):
        return a or b


class StringContentCheck(List):
    grammar = Field, maybe_some(whitespace), [Contains, Excludes, References], maybe_some(whitespace), Value

    def evaluate(self, obj):
        values = self[0].evaluate(obj)
        if len(values) == 0:
            return False
        else:
            result = False
            op = self[1]

            for val in values:
                try:
                    if isinstance(val, str) and not isinstance(op, References):
                        tmpresult = op.action(val, self[2])
                    elif isinstance(op, References):
                        tmpresult = op.action(val, self[2])
                    else:
                        tmpresult = False
                except ValueError:
                    tmpresult = False

                if tmpresult:
                    result = True
                    break

            return result

    def get_values(self, obj):
        return self[0].evaluate(obj)


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
                    if val is None and self[2].lower() in ("none", "0"):
                        tmpresult = op.action(val, None)
                    elif isinstance(val, bool):
                        tmpresult = op.action(val, self[2].convert_bool())
                    elif isinstance(val, int):
                        tmpresult = op.action(val, self[2].convert())
                    elif isinstance(val, (float, float32)):
                        tmpresult = op.action(val, float(self[2]))
                    else:
                        tmpresult = op.action(val, self[2])
                except ValueError:
                    tmpresult = False

                if tmpresult:
                    result = True
                    break

            return result

    def get_values(self, obj):
        return self[0].evaluate(obj)


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
                    if isinstance(val, str) and val.isdigit():
                        val = int(val)
                    if isinstance(val, int):
                        tmpresult = op.action(val, self[2].convert())
                    elif isinstance(val, (float, float32)):
                        tmpresult = op.action(val, float(self[2]))
                    else:
                        tmpresult = False
                except ValueError as err:
                    print(err)
                    tmpresult = False

                if tmpresult:
                    result = True
                    break

            return result

    def get_values(self, obj):
        return self[0].evaluate(obj)


class Comparison(List):
    grammar = [Equal, NumberCompare, StringContentCheck]

    def evaluate(self, obj):
        return self[0].evaluate(obj)

    def get_values(self, obj):
        return self[0].get_values(obj)


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

    def get_values(self, obj):
        values = []
        for unit in self:
            if hasattr(unit, "get_values"):
                values.extend(unit.get_values(obj))

        return values


class BracketedUnit(List):
    grammar = "(", AndOrUnit, ")"

    def evaluate(self, obj):
        return self[0].evaluate(obj)

    def get_values(self, obj):
        values = []
        for unit in self:
            if hasattr(unit, "get_values"):
                values.extend(unit.get_values(obj))

        return values

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


# Levenshtein distance implemented according to https://en.wikipedia.org/wiki/Levenshtein_distance
def tail(a):
    if len(a) == 1:
        return ""
    else:
        return a[1:]


def lev(a, b, currdistance=0):
    if currdistance > 5:
        return 9999

    if len(b) == 0:
        return len(a)
    elif len(a) == 0:
        return len(b)
    if a[0] == b[0]:
        return lev(tail(a), tail(b))
    else:
        return 1 + min(
                       lev(tail(a), b, currdistance+1),
                       lev(a, tail(b), currdistance+1),
                       lev(tail(a), tail(b), currdistance+1)
                       )


def simpledistance(a, b):
    if a not in b:
        return 999999
    else:
        return len(b) - len(a) + b.find(a)*2  # Prioritize matches happening earlier in the string


def find_best_fit(name, bw2=False, values=False, max=10):
    results = []
    namelower = name.lower()

    if bw2:
        if values:
            relevantfieldnames = valuenamesbw2
        else:
            relevantfieldnames = fieldnamesbw2
    else:
        if values:
            relevantfieldnames = valuenames
        else:
            relevantfieldnames = fieldnames

    for name in relevantfieldnames:
        dist = simpledistance(namelower, name)
        if dist < 100:
            for fullcase in relevantfieldnames[name]:
                results.append((fullcase, dist))

    results.sort(key=lambda x: x[1])

    return results[:max]


"""
for parser in [EqualOperator, UnequalOperator, Less, LessEqual, Greater, GreaterEqual]:
    parser.test()
    print(parser, "successful")

parse("self.d.a.b >= 25", NumberCompare)
testobject = TestObject()

fieldresult = parse("(self.a != 1 & self.a != 1) & self.a = 1 | self.a != 1", QueryGrammar)
print(fieldresult.evaluate(testobject))"""