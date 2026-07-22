import json
import sys
import os

def get_structures():
    for root, dirs, files in sorted(os.walk("../structures")):
        for file in sorted(files):
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                with open(file_path) as json_file:
                    data = json.load(json_file)
                    yield data

def convert_data_to_maple_code(data):
    spec = data["specification"]
    symbol = data["symbol"]
    max_size = len(data["terms"]) - 1
    labeled = ", labeled" if data["labeled"] else ""
    code = f"spec := [{symbol}, {spec}{labeled}]: seq(combstruct[count](spec, size = n), n = 0 ..{max_size});\n"
    return code

def convert_gf_to_maple_code(data):
    spec = data["specification"]
    labeled = "labeled" if data["labeled"] else "unlabeled"
    code = f"lprint(rhs(gfsolve({spec}, {labeled}, z)[1]))"
    return code

def write_maple_scripts():
    with open("maple_script.txt", "w") as out:
        for data in get_structures():
            code = convert_data_to_maple_code(data)
            out.write(code)
        out.write('quit;')

# Example for C++
#     def executeCpp():
#         # create a pipe to a child process
#         data, temp = os.pipe()
#         # write to STDIN as a byte object(convert string
#         # to bytes with encoding utf8)
#         os.write(temp, bytes("5 10\n", "utf-8"))
#         os.close(temp)
#
#         # store output of the program as a byte string in s
#         s = subprocess.check_output(
#             "g++ HelloWorld.cpp -o out2;./out2", stdin=data, shell=True)
#
#         # decode s to a normal string
#         print(s.decode("utf-8"))

def get_maple_outputs():
    current = ''
    with open("maple_output.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            current += ' ' + line
            if not current.endswith(','):
                terms = list(map(int, current.split(',')))
                yield terms
                current = ''

def validate_maple_output():
    for id_, (maple, ecs) in enumerate(zip(get_maple_outputs(), get_structures()), 1):
        assert id_ == ecs['id']
        print(f"{id_}: {maple} ")
        print(f"{id_}: {ecs['terms']}")
        assert maple == ecs['terms']


def main():
    validate_maple_output()


def get_oeis_reference(data):
    for ref in data["references"]:
        if ref.startswith('EIS '):
            oeis_id = ref[len('EIS '):]
            return oeis_id


def get_oeis_data(oeis_id):
    oeis_id = oeis_id.upper()
    prefix = oeis_id[:4]
    filename = f"../oeisdata/seq/{prefix}/{oeis_id}.seq"
    with open(filename) as text_file:
        s = ''
        for line in text_file:
            row = line.split(' ', maxsplit=3)
            if len(row) == 3 and row[0] in ('%S', '%T', '%U'):
                s += row[2]
        return list(map(int, s.split(',')))


def match_sequences(oeis_seq, ecs_seq):
    length = min(len(oeis_seq), len(ecs_seq))
    return oeis_seq[1:length] == ecs_seq[1:length]


def remove_zeros(seq):
    return list(filter(lambda x: x != 0, seq))


def fuzzy_match_sequences(oeis_seq, ecs_seq, ecs_id):
    oeis_seq = list(map(abs, remove_zeros(oeis_seq)))
    ecs_seq = remove_zeros(ecs_seq)
    return (
        match_sequences(oeis_seq, ecs_seq)  or
        match_sequences(oeis_seq[1:], ecs_seq) or
        match_sequences(oeis_seq, ecs_seq[1:]) or
        match_sequences(oeis_seq, ecs_seq[2:]) or
        match_sequences(oeis_seq[2:], ecs_seq) or
        match_sequences(oeis_seq[1:], ecs_seq[1:])
    )


def validate_sequences():
    bad_sequences = []
    for data in get_structures():
        ecs_id = data['id']
        oeis_id = get_oeis_reference(data)
        if oeis_id is None:
            print(f"ECS {ecs_id} skipped")
            continue
        seq1 = get_oeis_data(oeis_id)
        seq2 = data['terms']
        if not fuzzy_match_sequences(seq1, seq2, ecs_id):
            print(f"ECS {ecs_id} does not match {oeis_id}")
            print(f"{seq2=}")
            print('-'*120)
            bad_sequences.append(ecs_id)

    print(f"{len(bad_sequences)} sequences failed: {bad_sequences}")

if __name__ == "__main__":
    validate_sequences()


