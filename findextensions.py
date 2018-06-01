import os
import argparse

# define the inputs and help for the findextensions command
findextensions_parser = argparse.ArgumentParser()
findextensions_parser.add_argument("path", help='local path to target git repository', nargs='?', default="TryGlobal")

# return the argparse where required
def get_argparse():
    return findextensions_parser

## 
# Find all files in folders and sub-folders of the path
# Locate unique file extensions (.txt, .jpg etc) and
# return that unique list
##
def get_extensions(path):
    extensions = []
    for p, sd, files in os.walk(path):
        for name in files:
            filename, extension = os.path.splitext(name)
            extension = extension[1:]
            # keep list unique the "and extension" drops out
            # the empty string "" succinctly
            if extension not in extensions and extension:
                extensions.append(extension)

    return sorted(extensions)
