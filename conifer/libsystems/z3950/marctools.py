"""
  MARC utlities
  Public Domain 2007 public.resource.org

  Author: Joel Hardi <joel@hardi.org>
"""

class locToUTF8(object):
    "Changes text from LOC into unicode, using replace() method"

    dict = {}
    charmap = {}

    def __init__(self):
        "Sets self.dict and search character index self.charmap"
        self.dict = {
            "\X20":"\u0020", # "HARD SPACE - represented by a space"
            "\XC2\XA1":"\u00A1", # "INVERTED EXCLAMATION MARK"
            "\XC2\XA3":"\u00A3", # "BRITISH POUND / POUND SIGN"
            "\XC2\XA9":"\u00A9", # "COPYRIGHT SIGN"
            "\XC2\XAE":"\u00AE", # "PATENT MARK / REGISTERED SIGN"
            "\XC2\XB0":"\u00B0", # "DEGREE SIGN"
            "\XC2\XB1":"\u00B1", # "PLUS OR MINUS / PLUS-MINUS SIGN"
            "\XC2\XB7":"\u00B7", # "MIDDLE DOT"
            "\XC2\XBF":"\u00BF", # "INVERTED QUESTION MARK"
            "\XC3\X86":"\u00C6", # "UPPERCASE DIGRAPH AE / LATIN CAPITAL LIGATURE AE"
            "\XC3\X98":"\u00D8", # "UPPERCASE SCANDINAVIAN O / LATIN CAPITAL LETTER O WITH STROKE"
            "\XC3\X9E":"\u00DE", # "UPPERCASE ICELANDIC THORN / LATIN CAPITAL LETTER THORN (Icelandic)"
            "\XC3\XA6":"\u00E6", # "LOWERCASE DIGRAPH AE / LATIN SMALL LIGATURE AE"
            "\XC3\XB0":"\u00F0", # "LOWERCASE ETH / LATIN SMALL LETTER ETH (Icelandic)"
            "\XC3\XB8":"\u00F8", # "LOWERCASE SCANDINAVIAN O / LATIN SMALL LETTER O WITH STROKE"
            "\XC3\XBE":"\u00FE", # "LOWERCASE ICELANDIC THORN / LATIN SMALL LETTER THORN (Icelandic)"
            "\XC4\X90":"\u0110", # "UPPERCASE D WITH CROSSBAR / LATIN CAPITAL LETTER D WITH STROKE"
            "\XC4\X91":"\u0111", # "LOWERCASE D WITH CROSSBAR / LATIN SMALL LETTER D WITH STROKE"
            "\XC4\XB1":"\u0131", # "LOWERCASE TURKISH I / LATIN SMALL LETTER DOTLESS I"
            "\XC5\X81":"\u0141", # "UPPERCASE POLISH L / LATIN CAPITAL LETTER L WITH STROKE"
            "\XC5\X82":"\u0142", # "LOWERCASE POLISH L / LATIN SMALL LETTER L WITH STROKE"
            "\XC5\X92":"\u0152", # "UPPERCASE DIGRAPH OE / LATIN CAPITAL LIGATURE OE"
            "\XC5\X93":"\u0153", # "LOWERCASE DIGRAPH OE / LATIN SMALL LIGATURE OE"
            "\XC6\XA0":"\u01A0", # "UPPERCASE O-HOOK / LATIN CAPITAL LETTER O WITH HORN"
            "\XC6\XA1":"\u01A1", # "LOWERCASE O-HOOK / LATIN SMALL LETTER O WITH HORN"
            "\XC6\XAF":"\u01AF", # "UPPERCASE U-HOOK / LATIN CAPITAL LETTER U WITH HORN"
            "\XC6\XB0":"\u01B0", # "LOWERCASE U-HOOK / LATIN SMALL LETTER U WITH HORN"
            "\XCA\XB9":"\u02B9", # "SOFT SIGN, PRIME / MODIFIER LETTER PRIME"
            "\XCA\XBA":"\u02BA", # "HARD SIGN, DOUBLE PRIME / MODIFIER LETTER DOUBLE PRIME"
            "\XCA\XBB":"\u02BB", # "AYN / MODIFIER LETTER TURNED COMMA"
            "\XCA\XBE":"\u02BE", # "ALIF / MODIFIER LETTER RIGHT HALF RING"
            "\XCC\X80":"\u0300", # "GRAVE / COMBINING GRAVE ACCENT (Varia)"
            "\XCC\X81":"\u0301", # "ACUTE / COMBINING ACUTE ACCENT (Oxia)"
            "\XCC\X82":"\u0302", # "CIRCUMFLEX / COMBINING CIRCUMFLEX ACCENT"
            "\XCC\X83":"\u0303", # "TILDE / COMBINING TILDE"
            "\XCC\X84":"\u0304", # "MACRON / COMBINING MACRON"
            "\XCC\X86":"\u0306", # "BREVE / COMBINING BREVE (Vrachy)"
            "\XCC\X87":"\u0307", # "SUPERIOR DOT / COMBINING DOT ABOVE"
            "\XCC\X88":"\u0308", # "UMLAUT, DIAERESIS / COMBINING DIAERESIS (Dialytika)"
            "\XCC\X89":"\u0309", # "PSEUDO QUESTION MARK / COMBINING HOOK ABOVE"
            "\XCC\X8A":"\u030A", # "CIRCLE ABOVE, ANGSTROM / COMBINING RING ABOVE"
            "\XCC\X8B":"\u030B", # "DOUBLE ACUTE / COMBINING DOUBLE ACUTE ACCENT"
            "\XCC\X8C":"\u030C", # "HACEK / COMBINING CARON"
            "\XCC\X90":"\u0310", # "CANDRABINDU / COMBINING CANDRABINDU"
            "\XCC\X93":"\u0313", # "HIGH COMMA, CENTERED / COMBINING COMMA ABOVE (Psili)"
            "\XCC\X95":"\u0315", # "HIGH COMMA, OFF CENTER / COMBINING COMMA ABOVE RIGHT"
            "\XCC\X9C":"\u031C", # "RIGHT CEDILLA / COMBINING LEFT HALF RING BELOW"
            "\XCC\XA3":"\u0323", # "DOT BELOW / COMBINING DOT BELOW"
            "\XCC\XA4":"\u0324", # "DOUBLE DOT BELOW / COMBINING DIAERESIS BELOW"
            "\XCC\XA5":"\u0325", # "CIRCLE BELOW / COMBINING RING BELOW"
            "\XCC\XA6":"\u0326", # "LEFT HOOK (COMMA BELOW) / COMBINING COMMA BELOW"
            "\XCC\XA7":"\u0327", # "CEDILLA / COMBINING CEDILLA"
            "\XCC\XA8":"\u0328", # "RIGHT HOOK, OGONEK / COMBINING OGONEK"
            "\XCC\XAE":"\u032E", # "UPADHMANIYA / COMBINING BREVE BELOW"
            "\XCC\XB2":"\u0332", # "UNDERSCORE / COMBINING LOW LINE"
            "\XCC\XB3":"\u0333", # "DOUBLE UNDERSCORE / COMBINING DOUBLE LOW LINE"
            "\XE2\X84\X93":"\u2113", # "SCRIPT SMALL L"
            "\XE2\X84\X97":"\u2117", # "SOUND RECORDING COPYRIGHT"
            "\XE2\X99\XAD":"\u266D", # "MUSIC FLAT SIGN"
            "\XE2\X99\XAF":"\u266F", # "MUSIC SHARP SIGN"
            "\XEF\XB8\XA0":"\uFE20", # "LIGATURE, FIRST HALF / COMBINING LIGATURE LEFT HALF"
            "\XEF\XB8\XA1":"\uFE21", # "LIGATURE, SECOND HALF / COMBINING LIGATURE RIGHT HALF"
            "\XEF\XB8\XA2":"\uFE22", # "DOUBLE TILDE, FIRST HALF / COMBINING DOUBLE TILDE LEFT HALF"
            "\XEF\XB8\XA3":"\uFE23", # "DOUBLE TILDE, SECOND HALF / COMBINING DOUBLE TILDE RIGHT HALF"
        }

        # build self.charmap to map each first char of a search string to a list of its search strings
        firstchars = []
        self.charmap = {}
        for i in self.dict.iterkeys():
            if firstchars.count(i[0]) == 0:
                firstchars.append(i[0])
                self.charmap[i[0]] = []
            self.charmap[i[0]].append(i)

    def replace(self, str):
        "Given string str, returns unicode string with correct character replcements"
        searchchars = []
        # build subset of search/replace pairs to use based on if first char of search appears in str
        prev = range(0,3)
        for c in str:
            prev[0] = prev[1]
            prev[1] = prev[2]
            prev[2] = c
            if self.charmap.has_key(c):
                if searchchars.count(c) == 0:
                    searchchars.append(c)
            elif ord(c) > 127 and prev.count(c) == 0:
                str = str.replace(c, '\\X%x' % ord(c))

        # perform search/replaces
        for c in searchchars:
            for i in self.charmap[c]:
                str = str.replace(i, self.dict[i])

        return unicode(str, 'raw-unicode-escape')
