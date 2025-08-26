import json
import csv

def load_ecs_data():
    with open('../react-app/public/ecs.json') as fil:
        ecs_data = json.load(fil)
        return ecs_data

def load_oeis_names():
    with open('oeis-names.txt', 'r') as fil:
        return dict(line.strip().rstrip('.').split(' ', 1) for line in fil)

def test_load_oeis_names():
    oeis_names = load_oeis_names()
    print(oeis_names['A000217'])

def get_oeis_ref(struc):
    for ref in struc['references']:
        if ref.startswith('EIS '):
            return ref[4:]
    return 'MISSING'

def missing_gf():
    ecs_data = load_ecs_data()
    missing = []
    for struc in ecs_data.values():
        if 'gf' not in struc:
            missing.append((struc['id'], get_oeis_ref(struc)))
    print(missing)
    return missing

def main():
    ecs_data = load_ecs_data()
    oeis_names = load_oeis_names()
    rows = []
    for entry in ecs_data.values():
        terms = entry.get('terms', [])
        ecs_id = entry.get('id', '')
        ecs_name = entry.get('name', '')
        ecs_desc = entry.get('description', '')
        for reference in entry.get('references', []):
            oeis_id = None
            if reference.startswith('EIS '):
                oeis_id = reference.replace('EIS ', '')
                full_oeis_id = 'A' + oeis_id[1:].zfill(6)
                oeis_name = oeis_names[full_oeis_id]
                if ecs_name == '' or ecs_name == 'FAIL':
                    entry['name'] = oeis_name
                if ecs_desc == '' or ecs_desc == 'FAIL':
                    entry['description'] = oeis_name
                break
        else:
            print(f"No EIS for {ecs_id}: {terms}")
        rows.append((ecs_id, oeis_id, ecs_desc, str(terms)[1:-1]))


    if rows:
        with open('ecs-oeis.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(('ECS ID', 'OEIS ID', 'Description', 'Terms'))
            writer.writerows(rows)
            print(f'Wrote {len(rows)} rows to ecs-oeis.csv')
    
    with open('ecs-augmented-with-oeis-names.json', 'w') as fp:
        json.dump(ecs_data, fp, indent=2) 



if __name__ == "__main__":
    missing_gf()
    # main()
    # test_load_oeis_names()
