import json

def load_ecs_data():
    with open('../react-app/public/ecs.json') as fil:
        ecs_data = json.load(fil)
        return ecs_data

def write_structure_file(structure: dict):
    filename = f'../structures/ecs_{structure['id']:04d}.json'
    with open(filename, 'w', newline='\n') as fil:
        json.dump(structure, fil, indent=4)

def main():
    ecs_data = load_ecs_data()
    for structure in ecs_data.values():
        write_structure_file(structure)


if __name__ == '__main__':
    main()