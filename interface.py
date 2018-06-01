import cmd2
import argparse
import os
import colorama
import click
import requests
import tempfile
import shutil
import itertools
import time
import ssl

#Import my classes
import findextensions
import set_repo_path
import utils
import globalvars

from cmd2 import Cmd, with_argparser, with_argument_list, with_category
from colorama import Fore, Back, Style
from tqdm import tqdm
from operator import itemgetter
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from tabulate import tabulate

#Dirty Global Variables - Moved to globals.py
#extensions = []
#files_and_commits = []
#repo_path = None
#target_url = None

# Print the commit history
def display_files_and_commits():

    if len(globalvars.files_and_commits) == 0:
        utils.print_error("No files and commit history currently. Use set_repo_path and then show_files_and_commit_count to set it")
        return None

    # Sort the results by total number of commits
    globalvars.files_and_commits = sorted(globalvars.files_and_commits, key=itemgetter(1), reverse=True)
    print("======= DISPLAYING FILES AND COMMITS =======")
    # If we get here then show the result
    print(tabulate(globalvars.files_and_commits, headers=['File','Total Commits']))
    print("============================================")

# Do the work of executing OS commands and getting commit history count
def check_file_commits(file, root):

   # We do not care about the .git folder and sub-folders. 
   if ".git" in root:
       return None
    
   full_path = os.path.join(root, file)        
   # cmd is the full shell command to get the number of commits a file has had
   cmd = "(cd " + root + " ; git log " + file + " | grep \"^commit \" | cut -d \" \" -f 2) | wc -l"
   # answer is the enumber of commits a file has had
   answer = utils.exec_cmd_get_stdout(cmd)
   # add answer to files and commit
   globalvars.files_and_commits.append([full_path, int(answer)])
   return "Done"

class Interface(cmd2.Cmd):
    """
    Interactive command prompt enabling you to fingerprint a web application version using git
    """

    prompt = Fore.BLUE + Back.MAGENTA + "Git-Fingerprint" + Style.RESET_ALL + "> "
    intro = """
    Find the specific commit version a target site is using a local git repository to guide you.\n
    Work-flow:
       set_repo_path              # set to local repo
       set_target_url             # set to target website
       set_files_and_commit_count # enumerate local repo to get commit count for each file
       fingerprint_verion         # download files from website and compare to local repo to fingerprint
    """
    CMD_CAT_GIT_VERSION = "Git Version Commands"

    def __init__(self):
        cmd2.Cmd.__init__(self) 

    @with_argparser(findextensions.get_argparse())
    @with_category(CMD_CAT_GIT_VERSION)
    def do_findextensions(self, args):
        """
        Lists unique file extensions within the cloned repository
        """

        # No arg supplied, and repo_path was not set. Cannot proceed
        if args.path == "TryGlobal" and globalvars.repo_path == None:
            findextensions.get_argparse().print_help()
            utils.print_error("No path supplied. Try setting a path to this or using 'set_repo_path'.")
            return None

        path = ""

        # A repo_path was already set, and no argument was supplied
        # use the repo_path
        if globalvars.repo_path != None and args.path == "TryGlobal":
            path = globalvars.repo_path

        # if args.path is not default use that
        if args.path != "TryGlobal":
            path = args.path

        #print("path being used: " + path)

        if os.path.exists(path) and os.path.isdir(path):
            globalvars.repo_path = path
 
            globalvars.extensions = findextensions.get_extensions(path)
            msg = "Found " + Fore.MAGENTA + "{0}" + Style.RESET_ALL + " extensions."
            print(msg.format(len(globalvars.extensions)))
            print("If you want to list them use 'show_extensions'")
        else:
            utils.print_error("Supplied path does not exist or is not a directory")

    # sets the local path to a repository if you
    # prefer that workflow
    @with_argparser(set_repo_path.get_argparse())
    @with_category(CMD_CAT_GIT_VERSION)
    def do_set_repo_path(self, args):
        """
        Sets the local path to a repository
        """
        if os.path.exists(args.path) and os.path.isdir(args.path):

            globalvars.repo_path = args.path
            print("[*] Local Repo Path set to: " + globalvars.repo_path)
        else:
            utils.print_error("Supplied path does not exist or is not a directory")

    # prints the current repo path
    @with_category(CMD_CAT_GIT_VERSION)
    def do_show_repo_path(self, args):
        """
        Shows the local path to the repository.
        """
        if globalvars.repo_path == None:
            print("Currently no repo path has been set. Use 'set_repo_path'")
        else:
            print(globalvars.repo_path)

    @with_category(CMD_CAT_GIT_VERSION)
    def do_show_extensions(self, args):
        """
        Shows file extensions currently known to exist in the local repo.
        Populate that with 'findextensions' command.
        """
 
        if len(globalvars.extensions) ==0:
            utils.print_error("Currently no extensions are set. Use \"findextensions\" to do that")

        msg = "Found " + Fore.MAGENTA + "{0}" + Style.RESET_ALL + " extensions."
        print(msg.format(len(globalvars.extensions)))

        for ex in globalvars.extensions:
            print(ex)


    @with_category(CMD_CAT_GIT_VERSION)
    def do_show_files_and_commit_count(self, args):
        """
        Shows files from local repo and their commit count.
        Populate that with 'set_files_and_commit_count'
        """
        if len(globalvars.files_and_commits) == 0:
            print("[*] No files and commit count data set. Use 'set_files_and_commit_count' first")
            return None
        else:
            # Print out the details
            display_files_and_commits()
            
    @with_category(CMD_CAT_GIT_VERSION)
    def do_set_files_and_commit_count(self, args):
        """
        Enumerates the local repository to find all files
        then determines how many commits each file has had.
        Relies on you having already executed 'set_repo_path'
        """
        
        if globalvars.repo_path == None:
            utils.print_error("No repo path currently set. Use 'set_repo_path'")
            return None

        # Check if the user wants to replace the data they already have or not
        if len(globalvars.files_and_commits) > 0:
            if not click.confirm("Previous data exists. Do you want to replace that? [Y/N]"):
                return None # They did not want to proceed
            
        # If we get here we are clearing existing data and starting again
        globalvars.files_and_commits = []

        print("[*] Running show_files_and_commit_count against: " + globalvars.repo_path)

        # pre-compute how many files there are in total
        filecounter = 0
        dircounter = 0
        for root, dirs, files in os.walk(globalvars.repo_path):
           # Ignore all ".git/" files as they are not versioned.
           if ".git" not in root:
              dircounter = dircounter + 1
              for filename in files:
                 filecounter += 1

        for root, dirs, files in tqdm(os.walk(globalvars.repo_path), total=dircounter):
           # Ignore all ".git/" files as they are not versioned.
           if ".git" not in root:
              tqdm.write("Checking Directory: " + root)
              # Do a bit of threading as a Drupal took ~5 minutes before
##              for file in files:
##                  tqdm.write(root + file)
##                  check_file_commits(file, root)
              with ThreadPoolExecutor(max_workers=20) as executor:
                 futures = [executor.submit(check_file_commits, file, root) for file in files]
                 for future in as_completed(futures):
                    res = future.result()
                                 
        # print the results
        display_files_and_commits()


    # define the inputs and help for the findextensions command
    set_target_url_parser = argparse.ArgumentParser()
    set_target_url_parser.add_argument("url", help='URL to root of target site. This is were the .git folder would be even if you cannot access it.')
    # This sets the target URL
    @with_argparser(set_target_url_parser) # TODO - Refactor to match cleaner class design someday
    @with_category(CMD_CAT_GIT_VERSION)
    def do_set_target_url(self, args):
        """
        Sets the target URL.
        """
        globalvars.target_url = args.url
        print("[*] Target URL set to: " + globalvars.target_url)
        # Todo - Check URL is valid and attempt to connect to the specified URL

    @with_category(CMD_CAT_GIT_VERSION)
    def do_show_target_url(self, args):
        """
        Displays the current target URL.
        """

        # Check if target URL has been set before
        if globalvars.target_url == None:
            utils.print_error("[*] Target URL is not currently set. Use 'set_target_url'.")
            return None

        # If we get here then we have a URL to show
        print("[*] Target URL set to: " + globalvars.target_url)
        

    # This does the actual business of fingerprinting the target
    @with_category(CMD_CAT_GIT_VERSION)
    def do_fingerprint_version(self, args):
        """
        This fingerprints the target application using git.
        Relies on these having been executed first:
        * set_repo_path
        * set_target_url
        * set_files_and_commit_count
        """
        
        # If we have no files and commits set we must run show_files_and_commits
        if len(globalvars.files_and_commits) == 0:
            utils.print_error("No files and commits history, you must run 'show_files_and_commits' to populate that.")
            return None
        # If we have no repo path set we cannot proceed
        if globalvars.repo_path == None:
            utils.print_error("No repo path currently set. Use 'set_repo_path'")
            return None
        if globalvars.target_url == None:
            utils.print_error("No target URL currently set. Use 'set_target_url'")
            return None
        
        print("[*] Doing the thing!")
        print("[*] Local Repo Path: " + globalvars.repo_path)
        print("[*] Remote Target URL: " + globalvars.target_url)

        # make a dir in /tmp
        tmpdir = tempfile.mkdtemp()
        print("[*] Created temp folder: " + tmpdir)

##        with ThreadPoolExecutor(max_workers=10) as executor:
##            futures = [executor.submit(utils.find_commit_version, file_list, tmpdir) for file_list in tqdm(sorted(globalvars.files_and_commits, key=itemgetter(1), reverse=True), total=len(globalvars.files_and_commits))]
##            for futures in as_completed(futures):
##                res = future.result();
        # for every file find out the commit version and add any outdated files to globalvars.outdated_files
        for file_list in tqdm(sorted(globalvars.files_and_commits, key=itemgetter(1), reverse=True), total=len(globalvars.files_and_commits)):
            utils.find_commit_version(file_list, tmpdir)        
        
        # Force repo back to most recent commit or that local repo is now trashed with outdated files.
        cmd = "(cd " + globalvars.repo_path + "; git reset --hard HEAD)"
        # Answer is not important here. It either errors (which we see) or it returns no input I want to show
        answer = utils.exec_cmd_get_stdout(cmd)
        print("[*] Reset Target Repo back to most recent commits")
                           
        # remove dir in /tmp
        shutil.rmtree(tmpdir)
        print("[*] Removed temp folder: " + tmpdir)

        print("======= DISPLAYING OUTDATED FILES =======")
        # Display Results
        if len(globalvars.outdated_files) != 0:
            # try to sort by the timestamp
            #for row in sorted(globalvars.outdated_files, key = itemgetter(4)):
            #    print(row)
            globalvars.outdated_files = sorted(globalvars.outdated_files, key = itemgetter(4))
            print(tabulate(globalvars.outdated_files, headers=['File','SHA1','File Commit','Total Commits','Timestamp']))
        print("========================================")

    def do_show_fingerprint_version(self, args):
        """
        Shows the results of fingerprint scanning again if you have already ran 'fingerprint_version'
        """
        if len(globalvars.outdated_files) !=0:
            globalvars.outdated_files = sorted(globalvars.outdated_files, key = itemgetter(4))
            print(tabulate(globalvars.outdated_files, headers=['File','SHA1','File Commit','Total Commits','Timestamp']))
        
    # enable path completion for commands that need it
    complete_findextensions = cmd2.Cmd.path_complete
    complete_set_repo_path = cmd2.Cmd.path_complete

if __name__ == '__main__':

    # a bit of art
    art = open("./art/ansihoodie.txt","r")
    for l in art:
        print(l.strip())
    print("==============================")
    print("Git-Fingerprint by cornerpirate of SecarmaLabs v0.1")
    print("==============================")
        
    app = Interface()
    app.cmdloop()

