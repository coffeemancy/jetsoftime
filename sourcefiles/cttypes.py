import inspect
import typing

import byteops
import ctenums
import ctrom

ValFilter = typing.Callable[[typing.Any, int], int]
IntBase = typing.TypeVar('IntBase', bound=int)

class BytesProp(property):
    '''
    Implement masked byte getter/setters as an extension of property.  This
    allows for introspection of these types of properties.
    '''
    def __init__(self, start_idx: int, num_bytes: int, mask: int,
                 byteorder: str = 'little',
                 ret_type: IntBase = int,
                 input_filter: ValFilter = lambda self, val: val,
                 output_filter: ValFilter = lambda self, val: val):

        def getter(self) -> ret_type:
            val = self.get_masked_range(start_idx, num_bytes, mask,
                                        byteorder)
            val = output_filter(self, val)
            return ret_type(val)

        def setter(self, val: ret_type):
            val = int(val)
            val = input_filter(self, val)
            self.set_masked_range(start_idx, num_bytes, mask, val,
                                  byteorder)

        property.__init__(self, getter, setter)


def bytes_prop(start_idx: int, num_bytes: int, mask: int,
               byteorder: str = 'little',
               ret_type: IntBase = int,
               input_filter: ValFilter = lambda self, val: val,
               output_filter: ValFilter = lambda self, val: val):
    '''
    Returns a property for getting/setting a masked range in BinaryData.

    Parameters:
      - start_idx, num_bytes: Get the bytes in 
        range(start_idx, start_idx+num_bytes)
      - mask: integer with contiguous set bits.  Only the portion of the data
        corresponding to the set bits of mask are gotten/set.
      - byteorder: Indicates how range(start_idx, start_idx+num_bytes) should
        be interpreted before applying mask.
      - ret_type: Type to return (derives from int)
      - input_filter: Method for massaging input when setting.  Assumed to be
          a method of BinaryData, so it is self, val -> val.
      - output_filter: Method for massaging output when getting.  Similar to
          input_filter.
    '''
    def getter(self) -> ret_type:
        val = self.get_masked_range(start_idx, num_bytes, mask,
                                    byteorder)
        val = output_filter(self, val)
        return ret_type(val)

    def setter(self, val: ret_type):
        val = int(val)
        val = input_filter(self, val)
        self.set_masked_range(start_idx, num_bytes, mask, val,
                              byteorder)

    return property(getter, setter)


def byte_prop(index, mask, byteorder: str = 'little',
              ret_type: IntBase = int,
              input_filter: ValFilter = lambda self, val: val,
              output_filter: ValFilter = lambda self, val: val):
    '''
    Special case of a bytes_prop that uses only one byte.
    '''
    return bytes_prop(index, 1, mask, byteorder, ret_type,
                      input_filter, output_filter)


class BinaryData(bytearray):
    SIZE = None

    @classmethod
    def do_bytesprop_bookkeeping(cls):
        '''
        Dummy classmethod for inspecting BytesProp objects.
        '''

        def is_bytesprop(x):
            return isinstance(x, BytesProp)

        bytes_props = [
            name for (name, value)
            in inspect.getmembers(cls, is_bytesprop)
        ]

        if bytes_props:
            print(bytes_props)


    def __init__(self, *args, **kwargs):
        bytearray.__init__(self, *args, **kwargs)
        self.validate_data(self)

        self.do_bytesprop_bookkeeping()


    @classmethod
    def validate_data(cls, data: bytes):
        if data.SIZE is not None and len(data) != cls.SIZE:
            raise ValueError(
                f'Given data has length {len(data)} (Needs {cls.SIZE}).'
            )

    @staticmethod
    def get_minimal_shift(mask: int):
        '''
        Find the minimal N such that (mask/2^N % 1) != 0.
        '''

        # Put the binary string in reverse, and chop off the '0b' from the
        # start.
        try:
            return bin(mask)[:1:-1].index('1')
        except ValueError as orig:  # Give a more reasonable ValueError
            raise ValueError('Mask must be nonzero.') from orig

    def get_masked_range(self, start_idx: int, num_bytes: int, mask: int,
                         byteorder: str = 'little') -> int:
        '''
        Return the bytes in range(start_idx, start_idx+num_bytes) with
        mask applied.

        Param mask must have contiguous bytes set
        '''
        val = int.from_bytes(self[start_idx:start_idx+num_bytes], byteorder)
        val &= mask
        val >>= self.get_minimal_shift(mask)
        return val

    def set_masked_range(self, start_idx: int, num_bytes: int, mask: int,
                         val: int, byteorder: str = 'little'):
        '''
        Set the bytes in range(start_idx, start_idx+num_bytes) corresponding
        to bits set in mask to val.

        Param mask must have contiguous bytes set.
        '''
        shift = self.get_minimal_shift(mask)
        max_val = mask >> shift  # assuming contiguous mask

        if not 0 <= val <= max_val:
            raise ValueError(
                f'Value must be in range({max_val+1:0{2*num_bytes}X})'
            )

        inv_mask = (1 << (num_bytes*8)) - mask - 1
        cur_val = int.from_bytes(self[start_idx: start_idx+num_bytes],
                                 byteorder)
        cur_val &= inv_mask
        cur_val |= (val << shift)

        self[start_idx:start_idx+num_bytes] = \
            cur_val.to_bytes(num_bytes, byteorder)

    def __str__(self):
        ret_str = f'{self.__class__.__name__}: '
        ret_str += ' '.join(f'{x:02X}' for x in self)
        return ret_str


class TestBin(BinaryData):

    # filter for constraining values to range(0, 8)
    def test_filter(self, val):
        new_val = sorted([0, val, 0x7])[1]
        if new_val != val:
            print(f'Clamped to {new_val}')
        return new_val

    # A bogus example where the middle eight bits of the first two bytes are
    # encoding an item_id.
    # When setting the property, the input is increased by 1 by test_filter
    test_prop = bytes_prop(0, 2, 0x0FF0,
                           byteorder='big',
                           ret_type=ctenums.ItemID)

    # mimicking Rythrix's battle speed property
    test2 = byte_prop(0, 0xE0, input_filter=test_filter)

    # mimicking Rythyrix's stereo audio property
    # filters negate the values so set means False and unset means True
    stereo_audio = byte_prop(0, 0x10,
                             ret_type=bool,
                             input_filter=lambda self, val: not val,
                             output_filter=lambda self, val: not val)

    test3 = BytesProp(2, 1, 0x0F)


T = typing.TypeVar('T', bound='PointedBinaryRecord')

class PointedBinaryRecord(BinaryData):
    '''
    A class for binary data that exists as fixed-length records in a block on
    the rom which also has a pointer on the rom.
    '''
    DATA_PTR = None  # Address on the ROM where the pointer to the data is

    @classmethod
    def get_data_start_from_ctrom(cls, ct_rom: ctrom.CTRom):
        rom = ct_rom.rom_data
        rom.seek(cls.DATA_PTR)
        rom_ptr = int.from_bytes(rom.read(3), 'little')
        file_ptr = byteops.to_file_ptr(rom_ptr)

        return file_ptr

    @classmethod
    def get_record_from_ctrom(cls: typing.Type[T], ct_rom: ctrom.CTRom,
                              record_id: int) -> T:
        data_st = cls.get_data_start_from_ctrom(ct_rom)
        record_st = data_st + record_id*cls.SIZE
        ct_rom.rom_data.seek(record_st)
        data = ct_rom.rom_data.read(cls.SIZE)
        return cls(data)


class ControlHeader(PointedBinaryRecord):
    pass
    

class PCTechControlHeader(ControlHeader):
    SIZE = 0xB
    DATA_PTR = 0x01CBA1


def main():

    test = TestBin(b'\x00\x00')
    print(test.test3)
    test.test3 = 5
    print(test.test3)
    print(test)


if __name__ == '__main__':
    main()
