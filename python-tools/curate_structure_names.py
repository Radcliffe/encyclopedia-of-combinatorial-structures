import argparse
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
STRUCTURES_DIR = PROJECT_DIR / 'structures'
WEB_DATA_PATH = PROJECT_DIR / 'react-app' / 'public' / 'ecs.json'


DESCRIPTION_BASED_NAMES = {
    'Arrangements',
    'Balls and Urns',
    'Binomial coefficients',
    'Cycles Set',
    'Cycles set',
    'Cycles set without fixed point',
    'Functional graphs',
    'Hierarchies',
    'Integer partition',
    'Labeled mobile',
    'Mobiles',
    'Non-planar trees',
    'Pairs of cycles',
    'Pairs of sequences',
    'Pairs of sets',
    'Planar trees',
    'Set partitions',
    'Stirling numbers of the second kind',
    'Trees',
    'Unlabeled plane binary trees',
    'k-gonal numbers',
    'maps',
}


EXPLICIT_NAMES = {
    15: 'Set partitions with nonempty blocks (Bell numbers)',
    16: 'Set partitions with blocks of size at least 2',
    17: 'Set partitions with blocks of size at most 2 (involutions)',
    18: 'Set partitions with blocks of size at most 3',
    19: 'Set partitions with blocks of size at most 4',
    23: 'Fixed-point-free involutions',
    24: 'Permutations of order dividing 3',
    25: 'Permutations of order dividing 4',
    26: 'Permutations of order dividing 5',
    27: 'Fixed-point-free permutations of order dividing 3',
    28: 'Fixed-point-free permutations of order dividing 4',
    29: 'Fixed-point-free permutations of order dividing 5',
    30: 'Permutations with at least two cycles',
    31: 'Permutations with exactly two cycles',
    32: 'Permutations with exactly three cycles',
    33: 'Permutations with exactly four cycles',
    35: 'Partial permutations (arrangements)',
    37: 'Connected functional graphs',
    39: 'Idempotent maps (trees of height at most 1)',
    52: 'Unlabeled plane binary trees counted by leaves',
    55: 'Unlabeled plane binary trees counted by all nodes',
    57: 'Rooted non-plane unlabeled trees',
    64: 'Injective partial maps',
    66: 'Increasing injective partial maps',
    67: 'Partial maps',
    69: "Hierarchies (Schroeder's fourth problem)",
    72: 'Ball placements: indistinguishable balls, distinguishable urns',
    73: 'Ball placements: distinguishable balls, indistinguishable urns',
    74: 'Ball placements: indistinguishable balls and urns',
    202: 'Denumerant for coin values 1, 1, 2, 5, 10, 20 (duplicate of ECS 201)',
    448: 'Partitions into parts 2 and 3',
    653: 'Powers of 2 times Catalan numbers: a(n) = 2^n C(n-1)',
    669: 'Factorial-weighted powers of 2 times Catalan numbers',
    707: 'Sets of rooted ternary structures',
    712: 'Structures with EGF: -(1/3) LambertW(-3x)',
    730: 'Sets of rooted quaternary structures',
    759: 'Labeled pairs of sequences of cycles',
    765: 'Cycles of rooted cycles',
    771: 'Rooted cycles of cycles',
    775: 'Sequences of pairs of cycles',
    776: 'Power sets of pairs of sequences',
    779: 'Rooted power sets of cycles',
    780: 'Cycles of rooted sequences',
    783: 'Rooted sequences of recursively defined cycles',
    786: 'Pairs of cycles of sequences',
    787: 'Pairs of cycles of cycles',
    788: 'Cycles of pairs of sequences',
    789: 'Cycles of pairs of cycles',
    791: 'Products of cycles and cycles of cycles',
    793: 'Unions of cycles and cycles of cycles',
    795: 'Sequences of rooted cycles',
    796: 'Cycles of rooted power sets',
    821: 'Cycles of rooted sets',
    828: 'Rooted sequences of atomic cycles',
    840: 'Nonempty sets of rooted power sets',
    843: 'Sets of nonempty sequences of rooted sets',
    850: 'Power sets of nonempty sequences of rooted power sets',
    855: 'Rooted ordered set partitions',
    857: 'Nonempty sequences of rooted sets',
    865: 'Rooted set partitions',
    866: 'Power sets of nonempty sets of rooted power sets',
    867: 'Nonempty sets of rooted sequences',
    869: 'Sequences of nonempty sets of rooted sequences',
}


def capitalize(text):
    return text[:1].upper() + text[1:]


def proposed_name(structure):
    ecs_id = structure['id']
    old_name = structure['name']
    description = structure['description'].strip()

    if ecs_id in EXPLICIT_NAMES:
        return EXPLICIT_NAMES[ecs_id]

    if old_name == 'Denumerant':
        match = re.fullmatch(
            r'number of ways to make n cents with coins of (.+) cents',
            description,
            flags=re.IGNORECASE,
        )
        if match:
            denominations = ', '.join(match.group(1).split())
            return f'Denumerant for coin values {denominations}'

    if old_name == 'Arithmetic sequence':
        formula = re.sub(r'(\d+)\s+n', r'\1n', description)
        return f'Arithmetic sequence a(n) = {formula}'

    if old_name == 'Constant sequence':
        match = re.fullmatch(r"All (\d+)'s", description)
        if match:
            return f'Constant sequence a(n) = {match.group(1)}'

    if 345 <= ecs_id <= 350 and old_name == 'Stirling numbers of the second kind':
        return f'Stirling numbers of the second kind S(n, {ecs_id - 343})'

    if 351 <= ecs_id <= 361 and old_name == 'Integer partition':
        return f'Integer partitions into at most {ecs_id - 349} parts'

    if 362 <= ecs_id <= 370 and old_name == 'Lists':
        return f'Power sum a(n) = 1^n + ... + {ecs_id - 360}^n'

    if old_name == 'A simple grammar' and description != 'A simple grammar':
        return capitalize(description)

    if old_name in DESCRIPTION_BASED_NAMES:
        return capitalize(description)

    return old_name


def structure_files():
    return sorted(STRUCTURES_DIR.glob('*/*.json'))


def collect_changes():
    changes = []
    for path in structure_files():
        with open(path) as file:
            structure = json.load(file)
        new_name = proposed_name(structure)
        if new_name != structure['name']:
            changes.append((path, structure['id'], structure['name'], new_name))
    return changes


def replace_name_in_structure(path, old_name, new_name):
    text = path.read_text()
    old_field = f'"name": {json.dumps(old_name, ensure_ascii=False)}'
    new_field = f'"name": {json.dumps(new_name, ensure_ascii=False)}'
    if text.count(old_field) != 1:
        raise ValueError(f'Expected exactly one name field in {path}')
    path.write_text(text.replace(old_field, new_field, 1))


def update_web_data(changes):
    with open(WEB_DATA_PATH) as file:
        web_data = json.load(file)
    for _, ecs_id, old_name, new_name in changes:
        record = web_data[str(ecs_id)]
        if record['name'] != old_name:
            raise ValueError(f'Unexpected web name for ECS {ecs_id}: {record["name"]}')
        record['name'] = new_name
    with open(WEB_DATA_PATH, 'w', encoding='utf-8') as file:
        json.dump(web_data, file, indent=2)
        file.write('\n')


def main():
    parser = argparse.ArgumentParser(
        description='Replace generic ECS names with clear, evidence-based names.',
    )
    parser.add_argument(
        '--write',
        action='store_true',
        help='Apply changes to canonical structure files and the web dataset.',
    )
    args = parser.parse_args()

    changes = collect_changes()
    for _, ecs_id, old_name, new_name in changes:
        print(f'ECS {ecs_id}: {old_name} -> {new_name}')
    print(f'{len(changes)} names would be changed.')

    if args.write:
        for path, _, old_name, new_name in changes:
            replace_name_in_structure(path, old_name, new_name)
        update_web_data(changes)
        print('Changes written.')


if __name__ == '__main__':
    main()
