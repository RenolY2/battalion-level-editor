import re
import os
import struct


def int32(x):
    return struct.unpack("I", x)[0]


def write_int32(x, f):
    f.write(struct.pack("I", x))


def read_string(f, pos, end=b"\x00"):
    res = ""
    startindex = f.tell()

    f.seek(pos)
    endindex = 0

    if len(end) == 1:
        while f.read(1) != end:
            endindex += 1
    elif len(end) == 2:
        last = None
        while True:
            curr = f.read(1)

            if last is not None:
                if (last+curr) != end:
                    endindex += 1
                else:
                    break

            last = curr

    f.seek(pos)
    res = f.read(endindex)
    f.seek(startindex)
    return res


class Message(object):
    def __init__(self, strings, audioplaytime):
        self.strings = strings
        self.playtime = audioplaytime

    def set_path(self, audiopath):
        self.strings[0] = bytes(audiopath, encoding="ascii")

    def get_path(self, raw=False):
        if not raw:
            return str(self.strings[0], encoding="ascii")
        else:
            return self.strings[0]

    def set_name(self, name):
        self.strings[1] = bytes(name, encoding="ascii")

    def get_name(self, raw=False):
        if not raw:
            return str(self.strings[1], encoding="ascii")
        else:
            return self.strings[1]

    def set_message(self, message):
        self.strings[3] = bytes(message, encoding="utf-16-le")

    def get_message(self, raw=False):
        if not raw:
            msg = self.strings[3]
            msg = str(msg, encoding="utf-16-le")
            #sometimes this character is used as an apostrophe despite not being a valid
            #unicode character, so we need to fix it to a valid character.
            msg = msg.replace("\x92", "'")

            return msg
        else:
            return self.strings[3]


class BWLanguageFile(object):
    def __init__(self, f):
        #data = f.read()
        self.magic = int32(f.read(4))
        self.message_slots = int32(f.read(4))
        self.unknown = f.read(8)
        self.messages = []

        #print(hex(self.magic), self.message_slots)

        for i in range(self.message_slots):
            slot_magic = int32(f.read(4))
            integers = []

            playtime = 0.0

            assert slot_magic == 0x7F7F7F
            for j in range(0x34 // 4):
                value = f.read(4)
                if j == 4:
                    playtime = struct.unpack("f", value)[0]

                integers.append(int32(value))

            content = read_string(f, integers[6], b"\x00"+b"\x00")
            if len(content) % 2 == 1:
                content += b"\x00"

            self.messages.append(Message([read_string(f, integers[0]),
                                          read_string(f, integers[1]),
                                          read_string(f, integers[2]),
                                          content], playtime))

    def get_message(self, id):
        return self.messages[id]

    def write(self, f):
        magic = 0x05A177
        message_slots = len(self.messages)

        write_int32(magic, f)
        write_int32(message_slots, f)
        write_int32(0, f)  # The total size goes here
        write_int32(0, f)  # Unused?

        for i in range(message_slots):
            write_int32(0x7F7F7F, f)
            f.write(0x34*b"\x00")  # Data will go here later

        index = f.tell()

        for i, msg in enumerate(self.messages):
            f.seek(index)

            meta_offset = 0x10 + i*0x38

            filepath = msg.get_path(raw=True)
            filename = msg.get_name(raw=True)
            msg_content = msg.get_message(raw=True)

            start_path = f.tell()
            f.write(filepath)
            f.write(b"\x00\x00")

            start_filename = f.tell()
            f.write(filename)
            f.write(b"\x00\x00")

            start_unused = f.tell()
            f.write(b"\x00\x00")

            start_content = f.tell()
            f.write(msg_content)
            f.write(b"\x00\x00")

            index = f.tell()

            f.seek(meta_offset+4)
            write_int32(start_path, f)
            write_int32(start_filename, f)
            write_int32(start_unused, f)
            f.seek(4, os.SEEK_CUR)
            f.write(struct.pack("f", msg.playtime))
            f.seek(4, os.SEEK_CUR)
            write_int32(start_content, f)

        size = index
        print(size, f.tell())
        f.seek(0x8)
        write_int32(size, f)

if __name__ == "__main__":
    inputfile = "c1_OnPatrolEnglish.str"
    outputfile = "test.str"
    #inputfile = "c1_WindbreakRidgeJapanese.str"

    with open(inputfile, "rb") as f:
        #data = f.read()
        lang = BWLanguageFile(f)
    """
    # Example code for dumping all strings from the strings file
    with open("out.txt", "w") as f:
        for i, msg in enumerate(lang.messages):
            path = msg.get_path()
            filename = msg.get_name()
            content = msg.get_message()

            f.write("ID: {0} '{1}' '{2}' ".format(i, path, filename))

            content = msg.get_message()
            f.write(content)

            f.write("\n")
    """
    # Example of changing the first
    msg = lang.get_message(0)
    print(msg.get_message())
    msg.set_message("You have been choosen to write a very long message. Did you know that BW has lots of unused stuff? ")


    with open(outputfile, "wb") as f:
        lang.write(f)



