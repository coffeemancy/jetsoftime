# Most of the underlying data about how CT encodes strings is due to
# https://bisqwit.iki.fi/jutut/ctcset.html

from __future__ import annotations

import pickle

from byteops import get_value_from_bytes, print_bytes


class Node:

    def __init__(self):
        self.held_substring = None
        self.held_substring_index = None
        self.children = dict()

    def print_tree(self):

        for key in self.children.keys():
            print(f"following {key:02X}")
            self.children[key].print_tree()

        if len(self.children.keys()) == 0:
            print(f"leaf: index = {self.held_substring_index} "
                  f"subsring = {self.held_substring}")


# Note: This is not really a Huffman tree.  It's just an organizational tree
# structure for holding the compression substrings.
class CTHuffmanTree:

    def __init__(self, substrings: list[bytearray]):
        self.root = Node()

        self.substrings = substrings

        for index, substring in enumerate(substrings):
            self.add_substring(substring, index)

    def add_substring(self, substring: bytearray, index: int):
        self.__add_substring_r(self.root, substring, index, 0)

    def __add_substring_r(self,
                          node: Node,
                          substring: bytearray,
                          substring_index: int,
                          cur_pos: int = 0):

        if cur_pos == len(substring):
            node.held_substring = substring
            node.held_substring_index = substring_index
        else:
            cur_byte = substring[cur_pos]
            if cur_byte in node.children.keys():
                self.__add_substring_r(node.children[cur_byte],
                                       substring,
                                       substring_index, cur_pos+1)
            else:
                node.children[cur_byte] = Node()
                self.__add_substring_r(node.children[cur_byte],
                                       substring,
                                       substring_index, cur_pos+1)

    def compress(self, string: bytearray):

        ret_string = bytearray()

        pos = 0
        while pos < len(string):
            (ind, length) = self.match(string, pos)
            # print(ind, length)
            if ind is not None:
                if ind in range(0, 0x7F):
                    # substr = string[pos:pos+length]
                    # print('matched ' + CTString.ct_bytes_to_ascii(substr))
                    # string[pos:pos+length] = [ind + 0x21]
                    ret_string.append(ind+0x21)
                # Index 0x7F is '...', but this is not actually used.
                # Instead, '...' is represented by 0xF1
                elif ind == 0x7F:
                    ret_string.append(0xF1)
                pos += length
            else:
                ret_string.append(string[pos])
                pos += 1

        return ret_string

    def match(self, string: bytearray, pos: int):

        return self.match_r(string, pos, self.root)

    # Traverse the tree character by character.  Find the first node with a
    # non-None substring on the way back.
    def match_r(self, string: bytearray, pos: int, node: Node):

        if pos == len(string):
            return node.held_substring_index, 0

        if string[pos] in node.children.keys():
            # print(f"searching child {string[pos]:02X}")
            (substr, match_len) = self.match_r(string,
                                               pos+1,
                                               node.children[string[pos]])

            if substr is not None:
                return substr, match_len + 1
            else:
                return node.held_substring_index, 0
        else:
            return node.held_substring_index, 0


# CTString extends bytearray because it is just a bytearray with a few extra
# methods for converting to python string and compression.
class CTString(bytearray):

    # This list might not be exactly right.  I need to encounter each keyword
    # in a flux file before I know exactly what name flux uses.

    # weirdness:
    # Bisqwit says 0x05 is line break and 0x06 is line break +3 spaces.
    # It looks like 0x06 is just the normal line break in scripts.
    # So I've made 0x06 match with TF's {linebreak}.
    # Bisquit's 'Pause and dialog emptying' is TF's {page break}
    keywords = [
        'null', 'unused 0x01', 'unused 0x02', 'delay',
        'unused 0x04', 'linebreak+0', 'line break',
        'pause linebreak', 'pause linebreak+3',
        'empty dialog', 'page break+3',
        'full break', 'page break',
        'value8', 'value16', 'value32',
        'unused 0x10', 'prev substr', 'tech name',
        'crono', 'marle', 'lucca', 'robo', 'frog', 'ayla',
        'magus', 'crononick', 'pc1', 'pc2', 'pc3', 'nadia',
        'item', 'epoch'
    ]

    symbols = [
        '!', '?', '/', '\"1', '\"2', ':', '&', '(', ')', '\'', '.',
        ',', '=', '-', '+', '%', 'none', ' ', '{:heart:}', '...',
        '{:inf:}', '{:music:}'
    ]

    huffman_table = pickle.load(open('./pickles/huffman_table.pickle', 'rb'))
    huffman_tree = CTHuffmanTree(huffman_table)

    # There's nothing special that we do for CTStrings.
    # New behavior, no new data.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_str(cls, string: str, compress: bool = False):
        ct_str = cls()

        pos = 0

        while pos < len(str):

            (char, pos) = cls.get_token(string, pos)
            ct_str.append(char)

        if compress:
            ct_str = cls.huffman_tree.compress(ct_str)

        return ct_str

    @classmethod
    def get_token(cls, string: str, pos: int) -> (int, int):
        '''
        Gets the next byte of data for a ct string.  Returns that byte and the
        position of where the byte after begins.
        '''

        char = string[pos]
        # print(char, pos)
        if char.isupper():
            # Upper case chars are in range(0xA0, 0xBA)
            ct_char = (ord(char) - 0x41) + 0xA0
            length = 1
        elif char.islower():
            # Lower case chars are in range(0xBA, 0xD4)
            ct_char = (ord(char) - 0x61) + 0xBA
            length = 1
        elif char.isnumeric():
            # Digits are in range(0xD4, 0xDE)
            ct_char = (ord(char) - 0x30) + 0xD4
            length = 1
        elif char in CTString.symbols:
            # Symbols (see CTString.symbols) are in range(0xDE, 0xE
            ct_char = CTString.symbols.index(char) + 0xDE
            length = 1
        elif char == '{':
            # '{' marks the start of a keyword like Crono's name or an item.
            # CTString.keywords has all of these listed.

            # grab the keyword itself
            keyword = string[pos+1:].split('}')[0].lower()
            length = len(keyword) + 2  # keyword + {}

            if keyword in CTString.keywords:
                # keywords are in range(0, 21) so there's no shift
                ct_char = CTString.keywords.index(keyword)
                end = pos + length

                # Sometimes TF uses \r\n to stand for a CT linebreak.
                # Sometimes it throws it in there as formatting after a
                # '{linebreak}' in the ascii.  We need to strip out the
                # latter \r\n instances.

                # '\r\n' after a break char is a fake break
                break_chars = (5, 6, 7, 8, 10, 11, 12)

                if ct_char in break_chars and \
                   end+2 < len(string) and \
                   string[end:end+2] == '\r\n':
                    length += 2
            elif keyword in CTString.symbols:
                # quotation marks are in there too as {"1} and {"2}
                ct_char = CTString.symbols.index(keyword) + 0xDE
            else:
                print(f"unknown keyword \'{keyword}\'")
                exit()
        elif char == '\r' and pos+1 < len(string) and string[pos+1] == '\n':
            length = 2
            ct_char = 5
        else:
            print(f"unknown symbol \'{char}\'")
            exit()

        # print(f"char={char}, pos={pos}, ctchar={ct_char:02X}")
        # returning new position instead of length so that we can do things
        # like (char, pos) = get_token(str, pos) to update in a loop.
        return (ct_char, pos+length)

    @classmethod
    def from_ascii(cls, string: str):
        '''Turns an ascii string (+{keywords}) into a CTString.'''
        ret_str = CTString()

        pos = 0
        while pos < len(string):

            (char, pos) = cls.get_token(string, pos)
            ret_str.append(char)

        return ret_str

    def get_compressed(self):
        return CTString(CTString.huffman_tree.compress(self))

    def compress(self):
        self[:] = CTString(self.huffman_tree.compress(self))

    @classmethod
    def compress_bytearray(cls, array: bytearray):
        return cls(cls.huffman_tree.compress(array))

    @classmethod
    def ct_bytes_to_techname(cls, array: bytes):
        return CTString(array).to_ascii(techname=True)

    @classmethod
    def ct_bytes_to_ascii(cls, array: bytes):
        return CTString(array).to_ascii()

    def to_ascii(self, techname=False):
        '''Turns this CTString into a python string'''

        ret_str = ''

        pos = 0
        while pos < len(self):
            cur_byte = self[pos]

            if cur_byte in range(0, 0x21):
                # special symbols
                keyword = self.keywords[cur_byte]
                ret_str += f"{{{keyword}}}"
            elif cur_byte in range(0x21, 0xA0):
                if techname and cur_byte == 0x2F:
                    ret_str += '*'
                else:
                    x = self.huffman_table[cur_byte-0x21]
                    # print(f"substr: {x}")
                    x = CTString(x).to_ascii()
                    # print(f"substr: {x}")
                    ret_str += x
                    # ret_str += f"{{:subst {cur_byte:02X}:}}"
            elif cur_byte in range(0xA0, 0xBA):
                ret_str += chr(cur_byte-0xA0+0x41)
            elif cur_byte in range(0xBA, 0xD4):
                ret_str += chr(cur_byte-0xBA+0x61)
            elif cur_byte in range(0xD4, 0xDE):
                ret_str += f"{cur_byte-0xD4}"
            elif cur_byte in range(0xDE, 0xF4):
                ret_str += self.symbols[cur_byte-0xDE]
            elif cur_byte == 0xFF:
                # enemies edited in TF seem to get FFs in their names
                ret_str += ' '
            else:
                ret_str += '[:bad:]'
                print(f"Bad byte: {cur_byte:02X}")
                exit()

            pos += 1

        return ret_str


# This table is never changed by TF, so we should only have to read it once
# and pickle it.
def get_huffman_table(rom: bytearray) -> list[bytearray]:
    '''Pulls the substring table from the rom.'''
    ptr_table_addr = 0x1EFA00
    bank = (ptr_table_addr & 0xFF0000)

    huffman_table = []

    for i in range(128):
        ptr = ptr_table_addr + 2*i
        start = get_value_from_bytes(rom[ptr:ptr+2]) + bank

        substr_len = rom[start]
        substr_start = start+1
        substr_end = substr_start+substr_len

        huffman_table.append(rom[substr_start:substr_end])

    return huffman_table


def main():

    with open('./flux/normal-spekkio.flux', 'rb') as infile:
        # for now just hardcode to the start of flux's string handling
        infile.seek(0xCA1)
        string_data = infile.read()

    # num_strings = string_data[0]
    pos = 4  # There are some 00s that I don't see any point to

    cur_string_ind = 0
    while pos < len(string_data):
        print(f"Current string: {cur_string_ind:02X} at {pos+0xCA1:04X}")
        string_ind = string_data[pos]
        if string_ind != cur_string_ind:
            print(f"Expected {cur_string_ind:02X}, found {string_ind:02X}")
            exit()

        string_len = string_data[pos+1]
        pos += 2

        # The byte after the string length byte is optional.  If present, value
        # N means add 0x80*(N-1) to the length.  Being present means having
        # a value in the unprintable range (<0x20).
        if string_data[pos] < 0x20:
            string_len += 0x80*(string_data[pos]-1)
            pos += 1

        string_end = pos + string_len
        cur_string = string_data[pos:string_end]
        cur_string =\
            bytes([x for x in cur_string if x in range(0x20, 0x7F)])

        ct_str = CTString.from_ascii(cur_string.decode('ascii'))
        # print_bytes(ct_str, 16)
        ct_str.compress()
        # print_bytes(ct_str, 16)

        print(cur_string.decode('ascii'))
        print(ct_str.to_ascii())

        pos += string_len
        cur_string_ind += 1

    exit()

    htable = CTString.huffman_table
    htree = CTHuffmanTree(htable)

    for ind, substr in enumerate(htable):
        htree.add_substring(substr, ind)
        print(CTString.ct_bytes_to_ascii(substr))

    # htree.root.print_tree()

    print(' '.join(f"{x:02X}" for x in htree.root.children.keys()))

    x = CTString.from_ascii('Therethe')
    x.compress()

    print(x.to_ascii())

    '''
    with open('./roms/jets_test.sfc', 'rb') as infile:
        rom = infile.read()

    table = get_huffman_table(rom)

    with open('./pickles/huffman_table.pickle', 'wb') as outfile:
        pickle.dump(table, outfile)

    for x in table:
        print(ct_string_to_ascii(x))
    '''


if __name__ == '__main__':
    main()
