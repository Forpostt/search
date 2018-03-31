import re
from codings import *
from bisect import bisect_left
import mmap
import struct
import os

SPLIT_RGX = re.compile(r'\w+|[\(\)&\|!]', re.U)


def get(root, max_docid):
    res = []
    last_url = 0
    while 1:
        root.goto(last_url + 1)
        item = root.evaluate(max_docid)
        if item.end_of_search:
            break
        elif item.to_top:
            last_url = item.val - 1
        else:
            res.append(item.val)
            last_url = item.val

    return res


class HashTable:
    def __init__(self, path=None):
        self.path = path
        self.data = None
        self.dict = None

    def read(self):
        if self.path is not None:
            f = open(self.path, 'r')
            size = os.path.getsize(self.path)
            self.data = mmap.mmap(f.fileno(), size, prot=mmap.PROT_READ)
            n = struct.unpack('Q', self.data[0:8])[0]
            self.dict = [8 * (n + 1)]
            for i in range(n):
                self.dict.append(struct.unpack('Q', self.data[(i + 1) * 8:(i + 2) * 8])[0])
                self.dict[-1] += self.dict[-2]

    def get_index_params(self, key):
        key_hash = hash(key) % (1 << 31)
        dict_bias = self.dict[key_hash % (len(self.dict) - 1)]
        dict_end = self.dict[key_hash % (len(self.dict) - 1) + 1]

        hash_table = decompress_vb(self.data[dict_bias:dict_end])
        hash_list = hash_table[::3]
        item_index = bisect_left(hash_list, key_hash)

        if item_index == len(hash_list) or hash_table[3 * item_index] != key_hash:
            return None
        else:
            _, bias, size = hash_table[3 * item_index:3 * (item_index + 1)]
            return bias, size


class Index:
    def __init__(self, path=None, coding='vb'):
        self.path = path
        self.data = None
        self.coding = coding

    def read(self):
        f = open(self.path, 'r')
        size = os.path.getsize(self.path)
        self.data = mmap.mmap(f.fileno(), size, prot=mmap.PROT_READ)

    def get_post_list(self, bias, size):
        decompress = decompress_vb
        if self.coding == 's9':
            decompress = decompress_s9

        return decompress(self.data[bias:bias + size], sort=True)


class SearchObject:
    def __init__(self, to_top=False, end_of_search=False, val=-1):
        self.to_top = to_top
        self.end_of_search = end_of_search
        self.val = val

    def __eq__(self, other):
        if isinstance(other, SearchObject):
            return self.to_top == other.to_top and self.end_of_search == other.end_of_search and self.val == other.val
        else:
            return False


class QtreeTypeInfo:
    def __init__(self, value, op=False, bracket=False, term=False):
        self.value = value
        self.is_operator = op
        self.is_bracket = bracket
        self.is_term = term
        self.cur_docid_ind = 0

    def __repr__(self):
        return repr(self.value)

    def __eq__(self, other):
        if isinstance(other, QtreeTypeInfo):
            return self.value == other.value
        return self.value == other


class QTreeTerm(QtreeTypeInfo):
    def __init__(self, term):
        QtreeTypeInfo.__init__(self, term, term=True)
        self.post_list = []

    def goto(self, url):
        while self.cur_docid_ind < len(self.post_list) and self.post_list[self.cur_docid_ind] < url:
            self.cur_docid_ind += 1

    def evaluate(self, max_docid):
        if self.cur_docid_ind == len(self.post_list):
            return SearchObject(end_of_search=True)
        else:
            return SearchObject(val=self.post_list[self.cur_docid_ind])

    def post_prop(self, index, hash_table):
        item = hash_table.get_index_params(self.value)
        if item is not None:
            bias, size = item
            self.post_list = index.get_post_list(bias, size)


class QTreeOperator(QtreeTypeInfo):
    def __init__(self, op):
        QtreeTypeInfo.__init__(self, op, op=True)
        self.priority = get_operator_prio(op)
        self.left = None
        self.right = None

    def goto(self, url):
        self.docid_in = url
        if self.left is not None:
            self.left.goto(url)
        if self.right is not None:
            self.right.goto(url)

    def evaluate(self, max_docid):
        if self.value == '!':
            node = self.left if self.left is not None else self.right
            item = node.evaluate(max_docid)

            if item.val == self.docid_in:
                return SearchObject(to_top=True, val=self.docid_in + 1)

            if self.docid_in <= max_docid:
                return SearchObject(val=self.docid_in)
            else:
                return SearchObject(end_of_search=True)

        elif self.value == '|':
            left = self.left.evaluate(max_docid)
            right = self.right.evaluate(max_docid)

            if left.end_of_search:
                return right
            if right.end_of_search:
                return left

            if left.val < right.val:
                return left
            else:
                return right

        elif self.value == '&':
            left = self.left.evaluate(max_docid)
            right = self.right.evaluate(max_docid)

            if left.end_of_search or right.end_of_search:
                return SearchObject(end_of_search=True)

            if left == right:
                return left
            else:
                return SearchObject(to_top=True, val=max(left.val, right.val))

    def post_prop(self, index, hash_table):
        if self.left is not None:
            self.left.post_prop(index, hash_table)
        if self.right is not None:
            self.right.post_prop(index, hash_table)


class QTreeBracket(QtreeTypeInfo):
    def __init__(self, bracket):
        QtreeTypeInfo.__init__(self, bracket, bracket=True)


def get_operator_prio(s):
    if s == '|':
        return 0
    if s == '&':
        return 1
    if s == '!':
        return 2

    return None


def is_operator(s):
    return get_operator_prio(s) is not None


def tokenize_query(q):
    tokens = []
    for t in re.findall(SPLIT_RGX, q):
        if t == '(' or t == ')':
            tokens.append(QTreeBracket(t))
        elif is_operator(t):
            tokens.append(QTreeOperator(t))
        else:
            tokens.append(QTreeTerm(t))

    return tokens


def build_query_tree(tokens):
    if len(tokens) == 0:
        return None

    if len(tokens) == 1:
        return tokens[0]

    in_brackets = 0
    for i in range(len(tokens))[::-1]:
        if tokens[i].value == ')':
            in_brackets += 1

        if tokens[i].value == '(':
            in_brackets -= 1

        if in_brackets != 0:
            continue

        if tokens[i].is_operator and tokens[i].value != '!':
            break

    if i == 0 and tokens[i].value != '!':
        root = build_query_tree(tokens[1:-1])
        return root

    root = tokens[i]
    root.left = build_query_tree(tokens[:i])
    root.right = build_query_tree(tokens[i + 1:])

    return root


def parse_query(q):
    tokens = tokenize_query(q)
    return build_query_tree(tokens)
