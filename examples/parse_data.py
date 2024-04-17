import argparse
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from gerritParse.gerritdataparser import GerritDataParser


def run(parser, fn_gerrit_data, fn_review_data):
    f = open(fn_gerrit_data, mode='r', encoding='utf-8')
    reviewdata = []
    count = 0
    print('=== Start processing Gerrit records ===')
    eof = False
    while not eof:
        line = f.readline()
        if not line:
            eof = True
            break

        if line.strip() == '':
            continue

        try:
            rec = json.loads(line)
        except Exception as e:
            raise RuntimeError('%s' % repr(e))

        if 'rowCount' in rec.keys():
            continue

        # assert 'status' in rec.keys(), 'Key status missing:\n%s' % json.dumps(rec, indent=4)
        # if rec['status'] not in parser.__status_wlist:
        #     continue

        count += 1
        data = parser.parse_record(rec)
        reviewdata.append(data)
        print('%s' % '.', end='')
        if count % 60 == 0:
            print('[%d processed]\n' % count, end='')
    f.close()
    if count % 60 > 0:
        print('[%d processed]\n' % count, end='')
    print('\n[Total %d processed]\n' % count)

    with open(fn_review_data, mode='w', encoding='utf-8') as f:
        json.dump(reviewdata, f, indent=4)


if __name__ == "__main__":
    fn_config = os.path.join(os.path.dirname(__file__), 'preference', 'rules_config.json')

    opt_parser = argparse.ArgumentParser(prog=sys.argv[0])
    opt_parser.add_argument("--ruleset", required=True, choices=['Tdd', '5GUP'], help="Name of rule set")
    opt_parser.add_argument("--raw_data", required=True, help="JSON file containing raw gerrit data")
    opt_parser.add_argument("--review_data", required=True, help="JSON file containing extracted review info")
    args = opt_parser.parse_args()

    gdp = GerritDataParser(fn_config, args.ruleset)
    run(gdp, args.raw_data, args.review_data)
