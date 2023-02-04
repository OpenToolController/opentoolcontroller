import re
import sys
from PyQt5 import QtWidgets, QtGui


#https://gist.github.com/jdreaver/0be2e44981159d0854f5
#https://jdreaver.com/posts/2014-07-28-scientific-notation-spin-box-pyside.html





# Regular expression to find floats. Match groups are the whole string, the
# whole coefficient, the decimal part of the coefficient, and the exponent
# part.
_float_re = re.compile(r'(([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')

def valid_float_string(string):
    match = _float_re.search(string)
    return match.groups()[0] == string if match else False

class FloatValidator(QtGui.QValidator):
    def validate(self, string, position):
        if valid_float_string(string):
            state = QtGui.QValidator.Acceptable
        elif string == "" or string[position-1] in 'e.-+':
            state = QtGui.QValidator.Intermediate
        else:
            state = QtGui.QValidator.Invalid
       
        return (state, string, position)

    def fixup(self, text):
        match = _float_re.search(text)
        return match.groups()[0] if match else ""


class PercentValidator(QtGui.QValidator):
    def validate(self, string, position):
        #print("validate: ", string, " - ", position)
        sub_string = string
        if string[-1] == "%":
            sub_string = string[:-1]

        if valid_float_string(sub_string):
            state = QtGui.QValidator.Acceptable
        elif sub_string == "" or sub_string[position-1] in 'e.-+':
            state = QtGui.QValidator.Intermediate
        else:
            state = QtGui.QValidator.Invalid
       
        return (state, string, position)



class ScientificDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimum(-sys.float_info.max)
        self.setMaximum(sys.float_info.max)
        self.validator = FloatValidator()
        self._display_scientific = False
        self._display_digits = 3 
        self.setDecimals(15)

    def setDisplayDigits(self, value):
        self._display_digits = value

    def displayDigits(self):
        return self._display_digits

    def setDisplayScientific(self, value):
        self._display_scientific = bool(value)
    
    def displayScientific(self):
        return self._display_scientific

    def validate(self, text, position):
        return self.validator.validate(text, position)

    def fixup(self, text):
        return self.validator.fixup(text)

    def valueFromText(self, text):
        return float(text)

    def textFromValue(self, value):
        if self._display_scientific:
            return format_scientific_float(value, self._display_digits)
        else:
            return format_float(value, self._display_digits)

    def stepBy(self, steps):
        text = self.cleanText()
        groups = _float_re.search(text).groups()
        decimal = float(groups[1])
        decimal += steps
        new_string = "{:g}".format(decimal) + (groups[3] if groups[3] else "")
        self.lineEdit().setText(new_string)

#The validator feels a bit hacky in this
#TODO make cleaner
class PercentDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimum(0)
        self.setMaximum(2.0)

        self.validator = PercentValidator()
        self.setDecimals(5)
        self.setSingleStep(.01)
        self.setSuffix("%")

    def validate(self, text, position):
        return self.validator.validate(text, position)


    def valueFromText(self, text):
        if text[-1] == "%":
            text = text[:-1]

        return float(text)/100.0

    def textFromValue(self, value):
        return "{0:0.1f}".format(value*100.0)


    
#def format_float(value):
#    """Modified form of the 'g' format specifier."""
#    string = "{:g}".format(value).replace("e+", "e")
#    string = re.sub("e(-?)0*(\d+)", r"e\1\2", string)
#    return string

def format_scientific_float(value, precision=2):
    string = "{0:0.{prec}e}".format(value, prec=precision)
    return string

def format_float(value, precision=2):
    string = "{0:0.{prec}f}".format(value, prec=precision)
    return string




def numeric(equation):
    try:
        if '+' in equation:
            y = equation.split('+')
            x = float(y[0])+float(y[1])
        elif '-' in equation:
            y = equation.split('-')
            x = float(y[0])-float(y[1])

        return x
    except:
        return None
