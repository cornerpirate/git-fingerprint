# git-fingerprint

Enumerate version information from a target using Git.

# What is this?

The blog post explaining the technique is available here:

[https://blog.secarma.co.uk/git-fingerprint-tool-release](https://blog.secarma.co.uk/git-fingerprint-tool-release)

This tool was publicly demonstrated at BSides Scotland 2018 along with a bunch of other techniques using Git with pentesting. The slides and video of that talk available here:

[https://blog.secarma.co.uk/labs/hacking-with-git-the-video](https://blog.secarma.co.uk/labs/hacking-with-git-the-video)

If you are interested.

# Installation

I have developed and tested this on a Kali VM. A trial installation was done in a clean VM using "Kali 2018.2" image from this URL:

[http://cdimage.kali.org/kali-2018.2/kali-linux-2018.2-amd64.iso](
http://cdimage.kali.org/kali-2018.2/kali-linux-2018.2-amd64.iso)

Your mileage will vary for any other version or OS.

## Pre-Reqs: OS Packages

Kali 2018.2 ships without python3’s pip so you need to install that:

```bash
apt-get install python3-pip
```
This was the only required OS package.

## Pre-Reqs: Python3 Modules

Only 3 modules were required in Kali 2018.2. To install those use “pip3 install” as shown below:

```bash
pip3 install cmd2
pip3 install tqdm
pip3 install gin
```

All other libraries had already been installed. If you want to use this on another base OS then you may also require these which can also be installed using pip3:

```
argparse
colorama
click
requests
tempfile
shutil
itertools
ssl
tabulate
```
## Usage

Launch the command prompt interface using the command below:

```bash
python3 interface.py
```

This will launch the CMD2 powered prompt which displays a usage workflow:

![Alt text](img/CommandPromptWithWorkflow.png?raw=true "Command Prompt with Workflow")

Follow the suggested workflow to fingerprint your target. 

## A note on paths

The path used to point to the local repository should be one directory higher than the "git-fingerprint" folder. Such that "../foldername/" is the path. This is so the URLs passed during downloading are correct. If you used "/tmp/foldername" then the download URL would include "/tmp/". 

I may address this later with a patch. For now save your target repository so that you have this folder structure:

```
..

  git-fingerprint
  
  foldername
```

So the target repository folder (foldername) is in the same parent folder as "git-fingerprint"

## I want a command LINE script!

You can have that because CMD2 supports commands via the command line. Specify each command, and its inputs, within quotes. 
For example, you can enumerate and show the file extensions within a repository using this command:

```bash
python3 interface.py "set_repo_path ../PhotoShow/" "findextensions" "show_extensions" "quit"
```

In the above "../PhotoShow/" was a valid git repository one folder higher than the git-fingerprint folder.
Commands execute one after the other. 

## Can I script it?

Yes you can. CMD2 ships with the "load" command which takes commands from a file and executes. 
For example, save your commands into a file "commands.txt". Then execute using "load commands.txt" either via the command prompt
or via the command line interfaces. The following shows the command line executing those commands:

```bash
python3 interface.py "load commands.txt"
```

## Getting Help

CMD2 gives you a built in "help" command. Type "help" and get a short summary as shown:

![Alt text](img/HelpCommand.png?raw=true "help command")

You can get more verbose help with "help -v":

![Alt text](img/HelpCommandVerbose.png?raw=true "help -v command")

You can get advanced help with each command using the "help <command>" syntax as shown:

![Alt text](img/SpecifigHelpCommand.png?raw=true "help for specific command")

If these do not solve your problem you can always try a ticket on GitHub or to tag me on Twitter @cornerpirate.


