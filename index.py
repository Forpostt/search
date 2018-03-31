# coding:utf-8

from libr.docreader import DocumentStreamReader, parse_command_line
from libr.doc2words import extract_words
from libr.codings import *
from operator import itemgetter
import itertools


def write_index(term_dict, index_path, index_dict_path, coding):
    index = open(index_path, 'w')  
        
    compress = compress_vb
    if coding == 's9':
        compress = compress_s9

    size = 0
    for key, val in term_dict.items():
        in_bytes = compress(val, sort=True)
        index.write(in_bytes)
        term_dict[key] = (size, len(in_bytes))
        size += len(in_bytes)

    write_index_dict(index_dict_path, term_dict)                 
    index.close()

    
def write_index_dict(index_dict_path, term_dict):
    N = 20000
    hash_table = [[] for _ in range(N)]
    for key, val in term_dict.items():
        ind = (hash(key) % (1 << 31)) % N
        hash_table[ind].append([hash(key) % (1 << 31), val[0], val[1]])
        
    for i in range(N):
        item = sorted(hash_table[i], key=itemgetter(0))        
        hash_table[i] = compress_vb(list(itertools.chain.from_iterable(item)))
    
    with open(index_dict_path, 'w') as f:
        f.write(struct.pack('Q', N))
        for i in range(N):
            f.write(struct.pack('Q', len(hash_table[i])))
        for i in range(N):
            f.write(hash_table[i])        


def make_term_dict(reader, url_path):
    url = open(url_path, 'w')
    term_dict = {}
    
    for i, doc in enumerate(reader):
        url.write(doc.url + '\n')
        words = extract_words(doc.text)
        for word in words:
            urls = term_dict.get(word, 0)
            if urls == 0:
                term_dict[word] = [i]
            elif urls[-1] != i:
                urls.append(i)
    
    url.close()
    return term_dict


if __name__ == '__main__':
    command_line = parse_command_line().files
    coding = 'vb'
    if command_line[0] == 'simple9':
        coding = 's9'
        
    reader = DocumentStreamReader(command_line[1:])
    
    url_path = './data/urls.txt'
    term_dict = make_term_dict(reader, url_path)
    
    index_path = './data/index.txt'
    index_dict_path = './data/index_dict.txt'
    write_index(term_dict, index_path, index_dict_path, coding)
    
    with open('./data/encoding.txt', 'w') as f:
        f.write(coding)