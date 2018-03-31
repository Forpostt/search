# encoding:utf-8

import sys
from libr.tree import Index, HashTable, parse_query, get

if __name__ == '__main__':
    url = []
    with open('./data/urls.txt', 'r') as u:
        for line in u:
            line = line.strip()
            url.append(line)
    
    coding = 'vb'
    with open('./data/encoding.txt', 'r') as f:
        coding = f.read()

    index = Index('./data/index.txt', coding)
    index.read()
    hash_table = HashTable('./data/index_dict.txt')
    hash_table.read()

    for line in sys.stdin:
        line = line.strip()
        root = parse_query(unicode(line, 'utf8').lower())
        root.post_prop(index, hash_table)
        res = get(root, len(url))
        print(line)
        print(len(res))
        for item in res:
            print(url[item])
