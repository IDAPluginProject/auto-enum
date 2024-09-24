import re
import os
import json

def get_data(func_name):
    if func_name.endswith("2"):
        data = open(f"../man-pages/man2/{func_name}").read()
    else:
        data = open(f"../man-pages/man3/{func_name}").read()
    if ".SH NAME" not in data:
        return None
    return ".SH NAME" + data.split(".SH NAME")[1]


def split_sections(text):
    out = {}
    header = None
    section_text = ""
    for line in text.splitlines():
        if line.startswith(".SH"):
            if header is not None:
                out[header] = section_text
                section_text = ""
            header = line.split(".SH ")[1].strip()
        else:
            section_text += line + "\n"
    if header is not None:
        out[header] = section_text
    return out


def parse_synopsis(text):
    text = text.replace("\\\n", "")
    new_text = ""
    prefix = ""
    for line in text.splitlines():
        if line.startswith(".BI"):
            new_text += line[3:]
        l2 = line.replace('"', "")
        if l2.startswith(".B #"):
            prefix += l2[3:] + "\n"
    parsed_decls = []
    for decl in new_text.split(";"):
        m = re.match(r'"(?:\w+ )+\**(\w+)\((.+)\)', decl.strip())
        if m is None:
            continue
        name, args = m.groups()
        args = args.split(",")
        args = [x.strip(" \"") for x in args]
        if args and "..." in args[-1]:
            args.pop()
        if any('"' not in arg for arg in args):
            continue
        args = [(name.strip('" '), t.strip('" ')) for t, name in [x.split('"', 1) for x in args]]
        parsed_decls.append((name, args))
    return prefix, parsed_decls


def split_on(text, splitters):
    out = []
    cur = ""
    for line in text.splitlines():
        if any(line.startswith("." + splitter) for splitter in splitters):
            if cur:
                out.append(cur)
                cur = ""
        elif not line.startswith(".\\"):
            cur += line + "\n"
    if cur:
        out.append(cur)
    return out


def find_enum_names(desc, possible_enums):
    out = {}
    for para in split_on(desc, ["PP", "SS"]):
        if ".TP" in para:
            for enum in possible_enums:
                section_desc = para.split('.TP')[0]
                if ".I " + enum in section_desc or ".IR " + enum in section_desc:
                    parts = re.split(r"\.TP.*\n.B", para)
                    enum_values = [part.split(" ")[1].split("\n")[0] for part in parts[1:]]
                    enum_values = [x for x in enum_values if re.fullmatch(r"[A-Z][A-Z_0-9]+", x)]
                    if not enum_values:
                        continue
                    if enum in out:
                        out[enum].extend(enum_values)
                    else:
                        out[enum] = enum_values
    for enum in out.keys():
        out[enum] = list(set(out[enum]))
    return out

strace_data = json.load(open(os.path.join(os.path.dirname(__file__), "strace.json"), "r"))

def parse():
    files = os.listdir("../man-pages/man2") + os.listdir("../man-pages/man3")
    out = {}
    for file in files:
        text = get_data(file)
        if text is None:
            continue
        sections = split_sections(text)
        if "SYNOPSIS" not in sections:
            continue
        prefix, parsed_decls = parse_synopsis(sections["SYNOPSIS"])
        for name, args in parsed_decls:
            possible_enums = [x[0] for x in args if x[1] == 'int' or x[1].startswith('enum') or "flag" in x[0]]
            desc = sections["DESCRIPTION"]
            enums = find_enum_names(desc, possible_enums)
            if enums:
                out[name] = {
                    "args": enums,
                    "prefix": prefix,
                    "pre_resolved": False
                }
            elif name in strace_data:
                out[name] = {
                    "args": {args[int(arg_idx)][0]: arg_data for arg_idx, arg_data in strace_data[name].items()},
                    "prefix": prefix,
                    "pre_resolved": True
                }
    return out

if __name__ == "__main__":
    json.dump(parse(), open("./stage1.json", "w"), indent=2)