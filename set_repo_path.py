import argparse
import os

# define the inputs and help for the findextensions command
set_repo_path_parser = argparse.ArgumentParser()
set_repo_path_parser.add_argument("path", help='local path to target git repository')

# return the argparse where required
def get_argparse():
    return set_repo_path_parser
