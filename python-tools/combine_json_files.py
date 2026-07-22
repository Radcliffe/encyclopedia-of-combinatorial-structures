import json
import os
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
STRUCTURES_DIR = PROJECT_DIR / 'structures'
WEB_DATA_PATH = PROJECT_DIR / 'react-app' / 'public' / 'ecs.json'

# ## Example file:
# {
#     "id": 200,
#     "name": "Denumerant",
#     "description": "number of ways to make n cents with coins of 1 1 2 4 10 20 cents",
#     "specification": "{S = Prod(Sequence(Z),Sequence(Z),Sequence(Prod(Z,Z)),Sequence(Prod(Z,Z,Z,Z)),Sequence(Prod(Z,Z,Z,Z,Z,Z,Z,Z,Z,Z)),Sequence(Prod(Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z,Z)))}",
#     "labeled": false,
#     "symbol": "S",
#     "terms": [
#         1,
#         2,
#         4,
#         6,
#         10,
#         14,
#         20,
#         26,
#         35,
#         44,
#         57,
#         70,
#         88,
#         106,
#         130,
#         154,
#         185,
#         216,
#         255,
#         294,
#         344
#     ],
#     "references": [
#         "EIS A001307"
#     ],
#     "gf": "1/(-1+_x)^2/(_x^2-1)/(_x^4-1)/(_x^10-1)/(_x^20-1)",
#     "rec": "{-52307640-7484754*_n+120*_f(_n)+1080*_f(_n+2)-_n^5+480*_f(_n+1)-428225*_n^2+4800*_f(_n+6)+3840*_f(_n+5)+2880*_f(_n+4)+1920*_f(_n+3)-12245*_n^3-175*_n^4+5760*_f(_n+7)+6720*_f(_n+8)+7680*_f(_n+9)+8520*_f(_n+10)+9120*_f(_n+11)+9480*_f(_n+12)+9600*_f(_n+13)+9600*_f(_n+14)+9600*_f(_n+15)+9600*_f(_n+16)+9600*_f(_n+17)+9600*_f(_n+18)+9600*_f(_n+19)+9480*_f(_n+20)+9120*_f(_n+21)+8520*_f(_n+22)+7680*_f(_n+23)+6720*_f(_n+24)+5760*_f(_n+25)+4800*_f(_n+26)+3840*_f(_n+27)+2880*_f(_n+28)+1920*_f(_n+29)+1080*_f(_n+30)+480*_f(_n+31)+120*_f(_n+32), _f(0) = 1, _f(1) = 2, _f(2) = 4, _f(3) = 6, _f(4) = 10, _f(5) = 14, _f(6) = 20, _f(7) = 26, _f(8) = 35, _f(9) = 44, _f(10) = 57, _f(11) = 70, _f(12) = 88, _f(13) = 106, _f(14) = 130, _f(15) = 154, _f(16) = 185, _f(17) = 216, _f(18) = 255, _f(19) = 294, _f(20) = 344, _f(21) = 394, _f(22) = 456, _f(23) = 518, _f(24) = 595, _f(25) = 672, _f(26) = 765, _f(27) = 858, _f(28) = 970, _f(29) = 1082, _f(30) = 1216, _f(31) = 1350}",
#     "closedform": "Sum(1/80000*(1629*_alpha^9+854*_alpha^8+3517*_alpha^7+1302*_alpha^6+2525*_alpha^5-1290*_alpha^4+893*_alpha^3-1802*_alpha^2+381*_alpha-2314)*_alpha^(-1-_n),_alpha = RootOf(_Z^10+2*_Z^8+2*_Z^6+2*_Z^4+2*_Z^2+1))+Sum(1/16000*(7*_alpha^9+7*_alpha^7-16*_alpha^6-25*_alpha^5-32*_alpha^4-25*_alpha^3-32*_alpha^2-25*_alpha-16)*_alpha^(-_n-2)*(_n+1),_alpha =RootOf(_Z^10+2*_Z^8+2*_Z^6+2*_Z^4+2*_Z^2+1))+Sum(-1/200*(25*_alpha^7+28*_alpha^6-6*_alpha^4+15*_alpha^3+14*_alpha^2-15*_alpha-22)*_alpha^(-1-_n),_alpha = RootOf(_Z^8-_Z^6+_Z^4-_Z^2+1))+1/384000*(10*_n^3+570*_n^2+9515*_n+43605)*(-1)^(-_n)+1/192000*_n^5+19/38400*_n^4+127/7680*_n^3+8759/38400*_n^2+431957/384000*_n+111017/128000",
#     "equiv": "(1/200*exp(Complex(1)*arctan((-3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^3-2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)-RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153))/(3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^3+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)-1))*_n)/(-1+RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,-.951056516295153)))^2/(RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,-.951056516295153))^2-1)/(RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,-.951056516295153))^4-1)/RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,-.951056516295153))^30+1/200*exp(Complex(1)*arctan((-3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,.951056516295153)+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,.951056516295153)^3-2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,.951056516295153)-RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,.951056516295153))/(3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,.951056516295153)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^3+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,.951056516295153)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)-1))*_n)/(-1+RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,.951056516295153)))^2/(RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,.951056516295153))^2-1)/(RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,.951056516295153))^4-1)/RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374947,.951056516295153))^30+1/200*exp(Complex(1)*arctan((-3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374948)^2*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295157)+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295157)^3-2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374948)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295157)-RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295157))/(3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374948)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295157)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374948)^3+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295157)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374948)^2-RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374948)-1))*_n)/(-1+RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374948,-.951056516295157)))^2/(RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374948,-.951056516295157))^2-1)/(RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374948,-.951056516295157))^4-1)/RootOf(_Z^4+_Z^3+_Z^2+_Z+1,Complex(.309016994374948,-.951056516295157))^30)*_n*(RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^6+3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^4*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2+3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^4+RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^6+2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^5+4*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^3*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2+2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^4+3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^4+2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2-RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^4+4*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^3-4*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)*RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2+3*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)^2-RootOf(4096*_Z^12-5120*_Z^10+3840*_Z^8-1600*_Z^6-800*_Z^4+125,-.951056516295153)^2+2*RootOf(64*_Z^10+160*_Z^9+240*_Z^8+280*_Z^7+280*_Z^6+212*_Z^5+115*_Z^4+35*_Z^3-5*_Z^2-5*_Z-1,.309016994374947)+1)^(-1/2*ln(exp(-_n)))"
# }

# Counter({'id': 1075,
#          'name': 1075,
#          'description': 1075,
#          'specification': 1075,
#          'labeled': 1075,
#          'symbol': 1075,
#          'terms': 1075,
#          'references': 1075,
#          'gf': 1017,
#          'equiv': 938,
#          'rec': 867,
#          'closedform': 792})

def validate_json(struct):
    required_keys = {'id', 'name', 'description', 'specification', 'labeled', 'symbol', 'terms', 'references'}
    for key in required_keys:
        if key not in struct:
            raise ValueError(f"Missing required key: {key}")
    if not isinstance(struct['id'], int):
        raise ValueError("ID must be an integer")
    if not isinstance(struct['name'], str) or not struct['name']:
        raise ValueError("Name must be a non-empty string")
    if not isinstance(struct['description'], str) or not struct['description']:
        raise ValueError("Description must be a non-empty string")
    if not isinstance(struct['specification'], str) or not struct['specification']:
        raise ValueError("Specification must be a non-empty string")
    if not isinstance(struct['labeled'], bool):
        raise ValueError("Labeled must be a boolean")
    if not isinstance(struct['symbol'], str) or not struct['symbol']:
        raise ValueError("Symbol must be a non-empty string")
    if not isinstance(struct['terms'], list) or not all(isinstance(x, int) and x >= 0 for x in struct['terms']):
        raise ValueError("Terms must be a list of non-negative integers")
    optional_keys = {'gf', 'rec', 'closedform', 'equiv'}
    for key in struct:
        if key not in required_keys and key not in optional_keys:
            raise ValueError(f"Unexpected key: {key}")
    if 'references' in struct:
        if not isinstance(struct['references'], list) or not all(isinstance(x, str) and x for x in struct['references']):
            raise ValueError("References must be a list of non-empty strings")
    if 'gf' in struct and (not isinstance(struct['gf'], str) or not struct['gf']):
        raise ValueError("GF must be a non-empty string")
    if 'rec' in struct and (not isinstance(struct['rec'], str) or not struct['rec']):
        raise ValueError("Rec must be a non-empty string")
    if 'closedform' in struct and (not isinstance(struct['closedform'], str) or not struct['closedform']):
        raise ValueError("Closedform must be a non-empty string")
    if 'equiv' in struct and (not isinstance(struct['equiv'], str) or not struct['equiv']):
        raise ValueError("Equiv must be a non-empty string")


def encode_for_web(struct):
    """Return a web-safe record without changing the canonical record.

    JSON numbers are parsed as IEEE-754 doubles in browsers, so sequence terms
    outside JavaScript's safe-integer range must be serialized as strings.
    """
    encoded = struct.copy()
    encoded['terms'] = [str(term) for term in struct['terms']]
    return encoded


def decode_from_web(struct):
    """Return a canonical record with sequence terms restored to integers."""
    decoded = struct.copy()
    decoded['terms'] = [int(term) for term in struct['terms']]
    return decoded


def main():
    obj = {}
    web_obj = {}
    for dirpath, dirnames, filenames in sorted(os.walk(STRUCTURES_DIR)):
        for filename in sorted(filenames):
            fullpath = os.path.join(dirpath, filename)
            print(fullpath)
            struct = json.load(open(fullpath))
            validate_json(struct)
            key = str(struct['id'])
            obj[key] = struct
            web_obj[key] = encode_for_web(struct)
    with open(WEB_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(web_obj, f, indent=2)
        f.write('\n')
    convert_to_spreadsheet(obj)


def convert_to_spreadsheet(data):
    import pandas as pd

    records = []
    for key, struct in data.items():
        record = {
            'ID': struct['id'],
            'Name': struct['name'],
            'Description': struct['description'],
            'Specification': struct['specification'],
            'Labeled': struct['labeled'],
            'Symbol': struct['symbol'],
            'Terms': ', '.join(map(str, struct['terms'])),
            'References': '; '.join(struct.get('references', [])),
            'GF': struct.get('gf', ''),
            'Recurrence': struct.get('rec', ''),
            'Closed Form': struct.get('closedform', ''),
            'Equivalence': struct.get('equiv', ''),
        }
        records.append(record)

    df = pd.DataFrame(records)
    df = df.sort_values(by='ID')
    df.to_csv('ecs-new.csv', index=False)
    df.to_excel('ecs-new.xlsx', index=False)

if __name__ == '__main__':
    main()
