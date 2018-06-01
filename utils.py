import subprocess
import hashlib
import os
import requests
import colorama
import click
import tempfile
import shutil
import itertools

from colorama import Fore, Back, Style
from tqdm import tqdm
from operator import itemgetter
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

# My classes
import globalvars

# Print error messages in RED. Brutal style
def print_error(msg):
    print(Fore.RED + msg + Style.RESET_ALL)

# return the sha1 hash of a file
def get_sha1_of_file(filename):
  h = hashlib.sha1()
  with open(filename, 'rb', buffering=0) as f:
    for b in iter(lambda : f.read(128*1024), b''):
      h.update(b)
  return h.hexdigest()

# Excute an OS command and get the output as a string
# Supresses stderr.
def exec_cmd_get_stdout(cmd):
   with open(os.devnull,"w") as devnull:
       output = subprocess.run(cmd,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=devnull,
                           universal_newlines=True)
   answer = output.stdout.strip()
   return answer

# Find the commit version of the file if possible
def find_commit_version(file_list, tmpdir):

    file = file_list[0]            
    commit_count= file_list[1]
    (local_folder, filename) = os.path.split(file)
    (meh, file_extension) = os.path.splitext(filename)
   
    # Ignore this file
    if file_extension in globalvars.ignore_extensions:
        return None

    tqdm.write("[*] Checking " + file + " : " + str(commit_count))
    
    #### TODO MEGA HACKY, this makes my relative path ../ go away to make it work
    # This only works if the local folder path is one directory higher than where git-version is
    # Mega horrible.
    folder = local_folder[3:]
    if "/" in folder:
      folder = folder[folder.find("/"):len(folder)]
    folder = folder + "/"

    #print("target_url: " + globalvars.target_url)

    url = ""
    # If the file is in the root of the git folder there was a bug meaning the wrong URL was accessed
    if folder.count("/") == 1:
        url = globalvars.target_url + "/" + filename
    else:
        url = globalvars.target_url + "/" + folder + filename

    tmpfolder = tmpdir + "/" + folder

    # Make all folders in path if they don't already exist
    if os.path.exists(tmpfolder) == False:
       os.makedirs(tmpfolder)

    tmpfile = tmpfolder + filename

    tqdm.write("[*] Trying URL: " + url)
    r = requests.get(url, verify=False)
    if r.status_code != 200:
       tqdm.write(Fore.RED + "[*] Failed to fetch file with error code: " + str(r.status_code) + Style.RESET_ALL)
       #tqdm.write("Ignoring files with extension '" + file_extension + "'" )
       #if file_extension not in globalvars.ignore_extensions and file_extension != "":
       #    globalvars.ignore_extensions.append(file_extension)
       #if click.confirm("Error code for file with extension '" + file_extension + "'. Ignore all files with that extension? "):
       #    globalvars.ignore_extensions.append(file_extension)
    else:
        open(tmpfile, 'wb').write(r.content)
        #print("[*] 200 OK, content saved to: " + tmpfile)

        # This is the sha1 of the file contents of the downloaded file
        downloaded_sha1 = get_sha1_of_file(tmpfile)
        # cmd is the full shell command to get the list of SHA1 hashes for commits
        cmd = "(cd " + local_folder + " ; git log " + filename + " | grep '^commit ' | cut -d \" \" -f 2)"
        # answer is a list of SHA1 hashes one per line
        answer = exec_cmd_get_stdout(cmd)

        lines = answer.split()
        count = 0
        found = False

        # We need to loop through the commit history, checkout each version, and compare hashes.
        for commit_sha1 in lines:
            count = count + 1

            real_repo_path = ""
            # If the file is in the root of the git folder there was a bug meaning the wrong folder is used in this command
            if folder.count("/") == 1:
                real_repo_path = filename
            else:
                real_repo_path = folder + filename
                
            # command reverts a file back to a pevious commit
            cmd = "(cd " + globalvars.repo_path + " ; git checkout " + commit_sha1 + " ./" + real_repo_path + ")"
            #print("\t" + cmd)
            # answer is not important here. If it errors stderr will be displayed. No errors == chill.
            answer = exec_cmd_get_stdout(cmd)

            # Coping with files in the root of the repo which triggered a bug
            repofile = ""
            if folder.count("/") == 1:
                repofile = globalvars.repo_path + "/" + filename
            else:
                repofile = globalvars.repo_path + folder + filename
          
            # calculate SHA1 of file from the repo                     
            repo_sha1 = get_sha1_of_file(repofile)

            # Check if we have a match
            if downloaded_sha1 == repo_sha1:
                # Get commit date
                cmd = "(cd " + globalvars.repo_path + "; git show -s --format=%cd " + commit_sha1 + " --date=format:'%Y-%b-%d %H:%M:%S' )"
                answer = exec_cmd_get_stdout(cmd)
                msg = (Fore.GREEN if count == 1 else Fore.RED) + "MATCH FOUND [" + str(count) + " of " + str(len(lines)) + "] commited on: " + answer + Style.RESET_ALL
                tqdm.write( msg )
                # We have a matched file which is outdated so add it to the evidence
                #if count != 1:
                globalvars.outdated_files.append([file, commit_sha1, count, len(lines), answer])
                found = True
                #return None

        if found == False:
            tqdm.write( "[*] File match NOT found. Possibly modified by user." )
            
      
    
