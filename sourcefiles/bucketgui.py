'''
Module for creating a frame with bucket settings.
'''

import tkinter as tk
import typing

import objectivehints as oh
import randosettings as rset

class BucketPage(tk.Frame):

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)

        # Pre-make the objective hint boxes so that there is no error
        # in enabling/disabling them
        frames = []
        self.num_objectives = tk.IntVar(value='5')
        self.num_objectives_needed = tk.IntVar(value='4')
        self.obj_hint_entries = []
        self.obj_hints = [tk.StringVar() for ind in range(8)]

        self.disable_non_bucket_go = tk.IntVar(value=0)
        self.objectives_win = tk.IntVar(value=0)

        for ind in range(8):
            frame = tk.Frame(self)
            tk.Label(frame, text=f'Obj {ind+1}:').pack(side=tk.LEFT)
            entry = tk.Entry(
                frame,

                textvariable=self.obj_hints[ind],
                width=40
            )
            self.obj_hint_entries.append(entry)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            frames.append(frame)

        frame = tk.Frame(self)
        tk.Label(frame, text='Number of Objectives: ').pack(
            side=tk.LEFT, anchor=tk.W)
        self.num_objectives_entry = tk.Entry(
            frame,
            width=2,
            textvariable=self.num_objectives,
            validate='focusout',
            validatecommand=self.validate_num_objs
        )
        self.num_objectives_entry.pack(side=tk.LEFT)
        frame.pack(anchor=tk.W)

        frame = tk.Frame(self)
        tk.Label(frame, text='Number of Required Objectives: ')\
          .pack(side=tk.LEFT)
        self.num_objectives_needed_entry = tk.Entry(
            frame,
            width=2,
            textvariable=self.num_objectives_needed,
            validate='focusout',
            validatecommand=self.validate_num_objs_needed
        )
        self.num_objectives_needed_entry.pack(side=tk.LEFT)
        frame.pack(anchor=tk.W)

        for frame in frames:
            frame.pack()

        checkframe = tk.Frame(self)
        self.disable_non_bucket_go_cb = tk.Checkbutton(
            checkframe,
            variable=self.disable_non_bucket_go
        )
        self.disable_non_bucket_go_cb.pack(side=tk.LEFT)
        tk.Label(
            checkframe,
            text='Disable Non-Bucket Go Modes'
        ).pack(side=tk.LEFT)
        checkframe.pack(anchor=tk.W)

        checkframe = tk.Frame(self)
        self.disable_non_bucket_go_cb = tk.Checkbutton(
            checkframe,
            variable=self.objectives_win
        )
        self.disable_non_bucket_go_cb.pack(side=tk.LEFT)
        tk.Label(
            checkframe,
            text='Objectives Auto-Win'
        ).pack(side=tk.LEFT)
        checkframe.pack(anchor=tk.W)

    def validate_hints(self) -> typing.Tuple[bool, str]:
        for ind, hint in enumerate(self.obj_hints):

            hint_str = hint.get()
            passed, msg = oh.is_hint_valid(hint_str)

            if not passed:
                return passed, f'Obj {ind+1}: {msg}' 

        return True, ''

    def get_bucket_settings(self) -> rset.BucketSettings:
        ret = rset.BucketSettings()
        ret.disable_other_go_modes = False
        ret.num_objectives = int(self.num_objectives.get())
        ret.num_objectives_needed = int(self.num_objectives_needed.get())
        ret.hints = ['' for ind in range(ret.num_objectives)]

        for ind, hint in enumerate(self.obj_hint_entries):
            if ind == ret.num_objectives:
                break
            ret.hints[ind] = hint.get()

        ret.disable_other_go_modes = bool(self.disable_non_bucket_go.get())
        ret.objectives_win = bool(self.objectives_win.get())

        return ret

    def load_bucket_settings(self, bucket_settings: rset.BucketSettings):
        bs = bucket_settings
        self.num_objectives.set(str(bs.num_objectives))
        self.num_objectives_needed.set(str(bs.num_objectives_needed))

        for ind, hint in enumerate(bs.hints):
            self.obj_hints[ind].set(hint)

        self.disable_non_bucket_go.set(bs.disable_other_go_modes)
        self.objectives_win.set(bs.objectives_win)
            
    def validate_num_objs(self):
        try:
            num_objs = int(self.num_objectives.get())
            if num_objs not in range(1, 9):
                raise ValueError
        except ValueError:
            self.num_objectives_entry.delete(0, tk.END)
            self.num_objectives.set(self.num_objectives_needed.get())
            self.num_objectives_entry.insert(
                0, self.num_objectives.get()
            )
            num_objs = int(self.num_objectives.get())
            tk.messagebox.showerror(
                'Error',
                'Number of Objectives Must be a number between 1 and 8'
            )

        num_needed = int(self.num_objectives_needed.get())
        if num_needed > num_objs:
            self.num_objectives_needed.set(str(num_objs))

        for ind in range(0, num_objs):
            self.obj_hint_entries[ind]['state'] = tk.NORMAL

        for ind in range(num_objs, 8):
            self.obj_hint_entries[ind]['state'] = tk.DISABLED

        return True

    def validate_num_objs_needed(self):
        num_objs = int(self.num_objectives.get())
        try:
            num_objs_needed = int(self.num_objectives_needed.get())
            if num_objs_needed not in range(1, 9) or \
               num_objs_needed > num_objs:
                raise ValueError

        except ValueError:
            self.num_objectives_needed_entry.delete(0, tk.END)
            self.num_objectives_needed.set(self.num_objectives.get())
            self.num_objectives_needed_entry.insert(
                0, self.num_objectives_needed.get()
            )
            tk.messagebox.showerror(
                'Error',
                'Number of Required Objectives must be a number between 1 '
                'and the number of objectives.'
            )
            return False

        return True
