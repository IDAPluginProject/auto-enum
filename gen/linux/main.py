from parse_manpages import parse
from resolve import resolve_enums
from compress import compress
import overrides
import os
import json

extra_enums = json.load(open(os.path.join(os.path.dirname(__file__), "extra_enums.json")))

enums = parse()
filtered_enums = {}
for func_name, func in overrides.custom.items():
    if func_name in enums:
        enums[func_name]["args"].update(func["args"])
        if "prefix" in func:
            enums[func_name]["prefix"] = func["prefix"]
    else:
        enums[func_name] = func
    enums[func_name]["pre_resolved"] = False
for func_name, func in enums.items():
    if any(header in func["prefix"] for header in overrides.disallow_headers):
        continue
    if func["pre_resolved"]:
        if func_name == "access":
            func["args"]["type"] = func["args"]["mode"]
        filtered_enums[func_name] = func
        continue
    remapped_args = {}
    for arg_name, enum_vals in func["args"].items():
        remapped_enum_vals = []
        for enum_val in enum_vals:
            if enum_val in overrides.additional_headers:
                func["prefix"] += overrides.additional_headers[enum_val]
            if enum_val in overrides.replacement_headers:
                func["prefix"] = overrides.replacement_headers[enum_val]
            if enum_val in overrides.remap_value:
                enum_val = overrides.remap_value[enum_val]
            if enum_val is not None:
                remapped_enum_vals.append(enum_val)
        if func_name in overrides.remap:
            if arg_name in overrides.remap[func_name]:
                arg_name = overrides.remap[func_name][arg_name]
        if arg_name:
            remapped_args[arg_name] = remapped_enum_vals
    if func_name in overrides.remap:
        if "rename" in overrides.remap[func_name]:
            for name in overrides.remap[func_name]["rename"]:
                filtered_enums[name] = {
                    "prefix": func["prefix"],
                    "args": remapped_args,
                    "pre_resolved": func["pre_resolved"]
                }
            continue
    filtered_enums[func_name] = {
        "prefix": func["prefix"],
        "args": remapped_args,
        "pre_resolved": func["pre_resolved"]
    }
enums = resolve_enums(filtered_enums)
if not os.path.isdir("generated"):
    os.mkdir("generated")
if not os.path.isdir("generated/functions"):
    os.mkdir("generated/functions")
compress(enums, extra_enums, "generated")