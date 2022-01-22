from __future__ import annotations
from dataclasses import dataclass

from eventcommand import get_command, EventCommand


class EventFunction:

    @dataclass
    class JumpRecord:
        from_index: int = -1
        from_pos: int = -1
        to_label: str = ''

    def __init__(self):
        self.data = bytearray()
        self.commands = []
        self.offsets = []

        self.labels = {}
        self.jumps = []

        self.pos = 0

    def from_bytearray(func_bytes: bytearray):
        ret = EventFunction()

        pos = 0
        while pos < len(func_bytes):
            cmd = get_command(func_bytes, pos)
            ret.add(cmd)
            pos += len(cmd)

        return ret

    def add(self, event_command):
        self.commands.append(event_command)
        self.offsets.append(self.pos)
        self.pos += len(event_command)
        self.data.extend(event_command.to_bytearray())

        return self

    def append(self, event_function):

        ins_pos = self.pos
        ins_index = len(self.commands)

        for label in event_function.labels:
            new_pos = event_function.labels[label] + ins_pos

            if label[0].isalpha():
                new_label = label
            else:
                new_label = f'[{new_pos:04X}]'

            self.labels[new_label] = new_pos

        for jump in event_function.jumps:
            jump.from_index += ins_index
            jump.from_pos += ins_pos

            if jump.to_label[0] == '[':
                old_pos = int(jump.to_label[1:-1])
                new_pos = old_pos + ins_pos
                jump.to_label = f'[{new_pos:04X}]'
            self.jumps.append(jump)

        for command in event_function.commands:
            self.add(command)

    @classmethod
    def if_do(cls, if_command: EventCommand,
              if_block: EventFunction):
        return EventFunction().add_if(if_command, if_block)

    @classmethod
    def if_else(cls, if_command: EventCommand,
                if_block: EventFunction,
                else_block: EventFunction):
        return EventFunction().add_if_else(if_command, if_block, else_block)

    @classmethod
    def while_do(cls, if_command: EventCommand,
                 while_block: EventFunction):
        return EventFunction().add_while(if_command, while_block)

    def __set_label(self, label: str, pos: int = None):
        if label in self.labels and label[0] != '[':
            print(f'Warning: Resetting label {label}.')

        if pos is None:
            pos = self.pos

        self.labels[label] = pos

    def __get_label(self, pos: int = None) -> str:
        if pos is None:
            pos = self.pos

        if pos in self.labels.values():
            label = next(label for label in self.labels
                         if self.labels[label] == pos)
            return label
        else:
            label = f'[{pos:04X}]'
            self.__set_label(label, pos)
            return label

    def set_label(self, label: str, pos: int = None):

        if not label[0].isalpha:
            raise SystemExit(
                'Error: User generated labels must begin with a letter.'
            )

        self.__set_label(label, pos)

    def jump_to_label(self, event_command: EventCommand, label: str):
        jump_cmds = (
            EventCommand.fwd_jump_commands +
            EventCommand.back_jump_commands
        )

        if event_command.command not in jump_cmds:
            raise SystemExit(
                f'Error: {event_command.cmd:02X} is not a jump command'
            )

        cmd_ind = len(self.commands)
        self.jumps.append(self.JumpRecord(cmd_ind, self.pos, label))

        self.add(event_command)
        # print(self.jumps)
        # input('here')
        return self

    # if (if command):
    #     if_block
    # rest of eventfunction
    def add_if(self, if_command, if_block: EventFunction):
        label = f'[{self.pos+len(if_block)+len(if_command):04X}]'
        self.jump_to_label(if_command, label)
        self.append(if_block)
        self.__set_label(label)

        return self

    #         if (if command):
    #             if_block
    #             goto label2
    #         else_block
    # label2:
    def add_if_else(self, if_command,
                    if_block: EventFunction,
                    else_block: EventFunction):

        if_block.add(EventCommand.jump_forward(0))
        self.add_if(if_command, if_block)

        jump_pos = self.pos - len(EventCommand.jump_forward(0))
        jump_ind = len(self.commands) - 1

        self.append(else_block)
        label = self.__get_label()

        self.jumps.append(self.JumpRecord(jump_ind, jump_pos, label))

        return self

    #  label1:  if(if_cmd):  (to label2)
    #               while_block
    #               jump label1
    #  label2:
    def add_while(self, if_command, while_block: EventFunction):

        start_label = f'[{self.pos:04X}]'
        self.set_label(start_label)
        while_block.add(EventCommand.jump_back(0))
        self.add_if(if_command, while_block)

        from_pos = self.pos - len(EventCommand.jump_back(0))
        from_index = len(self.commands) - 1

        self.jumps.append(
            self.JumpRecord(from_index, from_pos, start_label)
        )

        return self

    def __len__(self):
        return len(self.data)

    def __str__(self):
        ret = ''
        pos = 0

        self.resolve_jumps()
        reverse_labels = {pos: label for label, pos in self.labels.items()}
        jump_pos = [x.from_pos for x in self.jumps]

        indent_level = 0
        decr_indent_positions = []

        conditionals = EventCommand.fwd_jump_commands[:]
        conditionals.remove(0x10)

        for i in range(len(self.commands)):

            if pos in reverse_labels:
                # print(f'{pos} in label positions')
                label = reverse_labels[pos]
            else:
                # print(f'{pos} nope')
                label = ''

            label = label.ljust(8)

            if pos in jump_pos:
                index = jump_pos.index(pos)
                jump_label = self.jumps[index].to_label
                jump_label = f' (to: {jump_label})'
            else:
                jump_label = ''

            ret += label
            ret += ('    '*indent_level)
            ret += (f"[{self.offsets[i]:04X}]" + str(self.commands[i]))
            ret += jump_label
            ret += '\n'

            if self.commands[i].command in conditionals:
                indent_level += 1
                target = (
                    pos + len(self.commands[i]) +
                    self.commands[i].args[-1] - 1
                )
                decr_indent_positions.append(target)

            pos += len(self.commands[i])
            if pos in decr_indent_positions:
                indent_level -= 1
                decr_indent_positions.remove(pos)

        return ret

    def resolve_jumps(self):

        # print(self.jumps)
        # print(self.labels)
        # input()

        for jump_record in self.jumps:
            jump_record: self.JumpRecord
            command = self.commands[jump_record.from_index]
            cmd_id = command.command  # gross
            from_pos = jump_record.from_pos
            jump_label = jump_record.to_label

            to_pos = self.labels[jump_label]

            jump_length = (to_pos - (from_pos+len(command)))

            if jump_length == 0:
                print(
                    f'Error: jump from {from_pos} to {to_pos} '
                    f'(\'{jump_label}\') is zero.'
                )

            jump_cmds = \
                EventCommand.fwd_jump_commands + \
                EventCommand.back_jump_commands

            if cmd_id not in jump_cmds:
                raise SystemExit('JumpRecord does not point to a jump cmd')

            if cmd_id in EventCommand.back_jump_commands and jump_length > 0:
                raise SystemExit('Back jump jumps to forward label')

            if cmd_id in EventCommand.fwd_jump_commands and jump_length < 0:
                raise SystemExit('Fowrard jump jumps to backward label')

            jump_length = abs(jump_length + 1)
            command.args[-1] = jump_length
            self.data[from_pos+len(command)-1] = jump_length

    def get_bytearray(self):

        self.resolve_jumps()
        return self.data


def main():

    EC = EventCommand
    EF = EventFunction

    '''
    func = EF()

    func.add_if(
        EC.check_active_pc(0, 0),
        (
            EF()
            .add(EC.assign_val_to_mem(0, 0x7F0220, 1))
            .add(EC.change_location(0x85, 0x7, 0x8))
        )
    )
    func.add(EC.assign_val_to_mem(0x10, 0x7F0220, 1))

    print(func)

    func = EF()
    func.add_while(
        EC.check_active_pc(0, 0),
        (
            EF()
            .add(EC.replace_characters())
        )
    )
    func.add(EC.assign_val_to_mem(0x10, 0x7F0220, 1))

    print(func)
    '''

    func = EF()
    func.set_label('asdf')
    func.add(EC.replace_characters())
    func.add_if_else(
        EC.check_active_pc(0, 0),  # if
        (
            EF()  # if block
            .add(EC.assign_val_to_mem(0x10, 0x7F0220, 1))
        ),
        (  # else block
            EF()
            .add(EC.text_box(0))
            .jump_to_label(EC.jump_back(0), 'asdf')
        )
    )
    func.add(EC.change_location(0x50, 5, 5))

    print(func)

    input()

    func = EF()
    func.add(EC.assign_val_to_mem(0x0, 0x7F01DF, 1))
    replace_label = func.get_label()
    func.add(EC.replace_characters())

    error_string_index = 0
    func.add_if(
        EC.check_recruited_pc(0, 0),
        (
            EF()
            .add_if_else(
                EC.check_active_pc(0, 0),
                EF(),
                (
                    EF()
                    .add(EC.text_box(error_string_index))
                    .jump_to_label(EC.jump_back(0), replace_label)
                )
            )
        )
    )

    print(func)


if __name__ == '__main__':
    main()
