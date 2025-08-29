import json
import os


def main():
    obj = {}
    for dirpath, dirnames, filenames in sorted(os.walk('../structures')):
        for filename in sorted(filenames):
            fullpath = os.path.join(dirpath, filename)
            print(fullpath)
            struct = json.load(open(fullpath))
            key = str(struct['id'])
            obj[key] = struct
    with open('ecs-new.json', 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)


if __name__ == '__main__':
    main()
