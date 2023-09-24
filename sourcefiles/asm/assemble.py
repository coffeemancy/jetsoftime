'''
Module for assembling instructions into binary
'''
from __future__ import annotations
from dataclasses import dataclass
from typing import Union, List

from asm import instructions as inst
from asm.instructions import _BranchInstruction, _NormalInstruction


Instruction = Union[_BranchInstruction, _NormalInstruction]
ASMList = List[Union[Instruction, str]]
_AM = inst.AddressingMode


@dataclass
class SnippetRecord:
    offset: int
    data: Union[Instruction, str]


class ASMSnippet:
    '''
    Class for storing a list of instructions and labels and converting to
    binary.

    Notes:
      - This does not support insertion/deletion of instructions after the
        object has been created.  The idea is for this to be self-contained
        subroutine.
    '''

    def __init__(self, instruction_list: List[Union[Instruction, str]]):
        self._label_dict: dict[str, int] = {}
        self.instruction_list: List[SnippetRecord] = []

        cur_offset = 0
        prev_length = 0

        unresolved_jump_indices: List[int] = []

        for ind, instruction in enumerate(instruction_list):
            cur_offset += prev_length

            if isinstance(instruction, str):
                self._label_dict[instruction] = ind
                prev_length = 0
            else:
                if isinstance(instruction, _BranchInstruction):
                    unresolved_jump_indices.append(ind)
                prev_length = len(instruction)

            self.instruction_list.append(
                SnippetRecord(cur_offset, instruction)
            )

        self._resolve_jumps()

    def _resolve_jumps(self):
        cmd_starts = {
            record.offset: ind
            for ind, record in enumerate(self.instruction_list)
        }

        # TODO: properly find last command
        last_entry = self.instruction_list[-1]
        if isinstance(last_entry.data, str):
            end = last_entry.offset
        else:
            end = last_entry.offset + len(last_entry.data)

        for ind, record in enumerate(self.instruction_list):
            data = record.data
            if isinstance(data, _BranchInstruction):
                if data.label is not None:
                    label_index = self._label_dict[data.label]
                    label_offset = self.instruction_list[label_index].offset
                    jump_len = label_offset - \
                        (record.offset + len(record.data))
                    data.argument = jump_len

                if data.argument is None:
                    raise inst.InvalidArgumentException

                jump_target = record.offset + len(data) + data.argument
                if jump_target not in cmd_starts:
                    # Separating this because it's not perfect
                    # The idea is to allow jumps outside of the snippet's range but
                    # catch bad jumps within the range.
                    if jump_target >= 0 and jump_target <= end:
                        # print("ERROR:"+str(data)+f'{jump_target:04X}')
                        raise inst.InvalidArgumentException(
                            "Branch is not to the start of a command."
                        )

    def to_bytes(self) -> bytes:

        ret_b = b''.join(record.data.to_bytearray()
                         for record in self.instruction_list
                         if not isinstance(record.data, str))

        return ret_b

    def __str__(self) -> str:
        ret_str = ''
        for record in self.instruction_list:
            ret_str += f'[{record.offset:04X}]\t'

            data = record.data

            if isinstance(data, str):
                ret_str += str(data) + '\n'
            else:
                binary = data.to_bytearray()
                binary_str = ' '.join(f'{x:02X}' for x in binary)
                binary_str = binary_str.ljust(13, ' ')

                ret_str += binary_str
                if isinstance(data, _BranchInstruction):
                    ret_str += str(data)
                    if data.label is None:
                        if data.argument is None:
                            raise inst.InvalidArgumentException
                        target = record.offset + len(data) + \
                            data.argument
                        ret_str += f"(to: [{target:04X}])"
                    ret_str += '\n'
                else:
                    ret_str += str(record.data) + '\n'

        return ret_str


def assemble(instruction_list: List[Union[Instruction, str]]) -> bytes:
    '''
    Turns a list of instructions and labels and produces binary code.
    '''
    snippet = ASMSnippet(instruction_list)
    return snippet.to_bytes()


def main():
    pass


if __name__ == '__main__':
    main()
