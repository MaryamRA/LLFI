#!/usr/bin/python

"""

%(prog)s takes a fault injection executable and executes it

Usage: %(prog)s <fault injection executable> <the same options that you use to run the excutable before>

       %(prog)s --help(-h): show help information

Prerequisite:
1. You need to be at the parent directory of the <fault injection executable> to invoke %(prog)s. This is to make it easier for LLFI to track the outputs generated by <fault injection executable>
2. (prog)s only checks recursively at the current directory for possible outputs, if your output is not under current directory, you need to store that output by yourself
3. You need to put your input files (if any) under current directory
4. You need to have 'input.yaml' under your current directory, which contains appropriate options for LLFI.
"""

# This script injects faults the program and produces output
# This script should be run after the profiling step

import sys, os, subprocess
import yaml
import time
import random
import shutil

runOverride = False
optionlist = []
timeout = 500

basedir = os.getcwd()
prog = os.path.basename(sys.argv[0])
fi_exe = ""

def usage(msg = None):
  retval = 0
  if msg is not None:
    retval = 1
    msg = "ERROR: " + msg
    print >> sys.stderr, msg
  print >> sys.stderr, __doc__ % globals()
  sys.exit(retval)


def parseArgs(args):
  global optionlist, fi_exe
  if args[0] == "--help" or args[0] == "-h":
    usage()

  fi_exe = os.path.realpath(args[0])
  optionlist = args[1:]

  if os.path.dirname(os.path.dirname(fi_exe)) != basedir:
    usage("You need to invoke %s at the parent directory of fault injection executable" %prog)

  # remove the directory prefix for input files, this is to make it easier for the program
  # to take a snapshot
  for index, opt in enumerate(optionlist):
    if os.path.isfile(opt):
      if os.path.realpath(os.path.dirname(opt)) != basedir:
        usage("File %s passed through option is not under current directory" % opt)
      else:
        optionlist[index] = os.path.basename(opt)


def checkInputYaml():
  global timeout, doc
  #Check for input.yaml's presence
  try:
    f = open(os.path.join(basedir, 'input.yaml'),'r')
  except:
    usage("No input.yaml file in the parent directory of fault injection executable")
    exit(1)

  #Check for input.yaml's correct formmating
  try:
    doc = yaml.load(f)
    f.close()
    if "kernelOption" in doc:
      for opt in doc["kernelOption"]:
        if opt=="forceRun":
          runOverride = True
          print "Kernel: Forcing run"
    if "timeOut" in doc:
      timeout = int(doc["timeOut"])
      assert timeout > 0, "The timeOut option must be greater than 0"
    else:
      print "Run fault injection executable with default timeout " + str(timeout)
  except:
    usage("input.yaml is not formatted in proper YAML (reminder: use spaces, not tabs)")
    exit(1)


################################################################################
def config():
  global inputdir, outputdir, errordir, stddir, llfi_stat_dir
  # config
  llfi_dir = os.path.dirname(fi_exe)
  inputdir = os.path.join(llfi_dir, "prog_input")
  outputdir = os.path.join(llfi_dir, "prog_output")
  errordir = os.path.join(llfi_dir, "error_output")
  stddir = os.path.join(llfi_dir, "std_output")
  llfi_stat_dir = os.path.join(llfi_dir, "llfi_stat_output")

  if not os.path.isdir(outputdir):
    os.mkdir(outputdir)
  if not os.path.isdir(errordir):
    os.mkdir(errordir)
  if not os.path.isdir(inputdir):
    os.mkdir(inputdir)
  if not os.path.isdir(stddir):
    os.mkdir(stddir)
  if not os.path.isdir(llfi_stat_dir):
    os.mkdir(llfi_stat_dir)


################################################################################
def execute( execlist):
  global outputfile
  print ' '.join(execlist)
  #get state of directory
  dirSnapshot()
  p = subprocess.Popen(execlist, stdout = subprocess.PIPE)
  elapsetime = 0
  while (elapsetime < timeout):
    elapsetime += 1
    time.sleep(1)
    #print p.poll()
    if p.poll() is not None:
      moveOutput()
      print "\t program finish", p.returncode
      print "\t time taken", elapsetime,"\n"
      outputFile = open(outputfile, "w")
      outputFile.write(p.communicate()[0])
      outputFile.close()
      replenishInput() #for cases where program deletes input or alters them each run
      #inputFile.close()
      return str(p.returncode)
  #inputFile.close()
  print "\tParent : Child timed out. Cleaning up ... "
  p.kill()
  moveOutput()
  replenishInput()
  return "timed-out"

################################################################################
def storeInputFiles():
  global inputList
  inputList=[]
  for opt in optionlist:
    if os.path.isfile(opt):#stores all files in inputList and copy over to inputdir
      shutil.copy2(opt, os.path.join(inputdir, opt))
      inputList.append(opt)

################################################################################
def replenishInput():#TODO make condition to skip this if input is present
  for each in inputList:
    if not os.path.isfile(each):#copy deleted inputfiles back to basedir
      shutil.copy2(os.path.join(inputdir, each), each)

################################################################################
def moveOutput():
  #move all newly created files
  newfiles = [_file for _file in os.listdir(".")]
  for each in newfiles:
    if each not in dirBefore:
      fileSize = os.stat(each).st_size
      if fileSize == 0 and each.startswith("llfi"):
        #empty library output, can delete
        print each+ " is going to be deleted for having size of " + str(fileSize)
        os.remove(each)
      else:
        flds = each.split(".")
        newName = '.'.join(flds[0:-1])
        newName+='.'+run_id+'.'+flds[-1]
        if newName.startswith("llfi"):
          os.rename(each, os.path.join(llfi_stat_dir, newName))
        else:
          os.rename(each, os.path.join(outputdir, newName))

################################################################################
def dirSnapshot():
  #snapshot of directory before each execute() is performed
  global dirBefore
  dirBefore = [_file for _file in os.listdir(".")]

################################################################################
def readCycles():
  global totalcycles
  profinput= open("llfi.stat.prof.txt","r")
  while 1:
    line = profinput.readline()
    if line.strip():
      if line[0] == 't':
        label, totalcycles = line.split("=")
        break
  profinput.close()

################################################################################
def checkValues(key, val, var1 = None,var2 = None,var3 = None,var4 = None):
  #preliminary input checking for fi options
  #also checks for fi_bit usage by non-kernel users
  #optional var# are used for fi_bit's case only
  if key =='run_number':
    assert isinstance(val, int)==True, key+" must be an integer in input.yaml"
    assert int(val)>0, key+" must be greater than 0 in input.yaml"

  elif key == 'fi_type':
    pass

  elif key == 'fi_cycle':
    assert isinstance(val, int)==True, key+" must be an integer in input.yaml"
    assert int(val) >= 0, key+" must be greater than or equal to 0 in input.yaml"
    assert int(val) <= int(totalcycles), key +" must be less than or equal to "+totalcycles.strip()+" in input.yaml"

  elif key == 'fi_index':
    assert isinstance(val, int)==True, key+" must be an integer in input.yaml"
    assert int(val) >= 0, key+" must be greater than or equal to 0 in input.yaml"

  elif key == 'fi_reg_index':
    assert isinstance(val, int)==True, key+" must be an integer in input.yaml"
    assert int(val) >= 0, key+" must be greater than or equal to 0 in input.yaml"

  elif key == 'fi_bit':
    assert isinstance(val, int)==True, key+" must be an integer in input.yaml"
    assert int(val) >= 0, key+" must be greater than or equal to 0 in input.yaml"

    if runOverride:
      pass
    elif var1 > 1 and (var2 or var3) and var4:
      user_input = raw_input("\nWARNING: Injecting into the same cycle(index), bit multiple times "+
                  "is redundant as it would yield the same result."+
                  "\nTo turn off this warning, please see Readme "+
                  "for kernel mode.\nDo you wish to continue anyway? (Y/N)\n ")
      if user_input.upper() =="Y":
        pass
      else:
        exit(1)

################################################################################
def main(args):
  global optionlist, outputfile, totalcycles,run_id

  parseArgs(args)
  checkInputYaml()
  config()

  # get total num of cycles
  readCycles()
  storeInputFiles()

  #Set up each config file and its corresponding run_number
  try:
    rOpt = doc["runOption"]
  except:
    print "ERROR: Please include runOption in input.yaml."
    exit(1)

  if not os.path.isfile(fi_exe):
    print "ERROR: The executable "+ fi_exe+" does not exist."
    print "Please build the executables with create-executables.\n"
    exit(1)
  else:
    print "======Fault Injection======"
    for ii, run in enumerate(rOpt):
      print "---FI Config #"+str(ii)+"---"

      if "numOfRuns" not in run["run"]:
        print ("ERROR: Must include a run number per fi config in input.yaml.")
        exit(1)

      run_number=run["run"]["numOfRuns"]
      checkValues("run_number", run_number)

      # reset all configurations
      if 'fi_type' in locals():
        del fi_type
      if 'fi_cycle' in locals():
        del fi_cycle
      if 'fi_index' in locals():
        del fi_index
      if 'fi_reg_index' in locals():
        del fi_reg_index
      if 'fi_bit' in locals():
        del fi_bit

      #write new fi config file according to input.yaml
      if "fi_type" in run["run"]:
        fi_type=run["run"]["fi_type"]
        checkValues("fi_type",fi_type)
      if "fi_cycle" in run["run"]:
        fi_cycle=run["run"]["fi_cycle"]
        checkValues("fi_cycle",fi_cycle)
      if "fi_index" in run["run"]:
        fi_index=run["run"]["fi_index"]
        checkValues("fi_index",fi_index)
      if "fi_reg_index" in run["run"]:
        fi_reg_index=run["run"]["fi_reg_index"]
        checkValues("fi_reg_index",fi_reg_index)
      if "fi_bit" in run["run"]:
        fi_bit=run["run"]["fi_bit"]
        checkValues("fi_bit",fi_bit,run_number,fi_cycle,fi_index,fi_reg_index)

      if ('fi_cycle' not in locals()) and 'fi_index' in locals():
        print ("\nINFO: You choose to inject faults based on LLFI index, "
               "this will inject into every runtime instruction whose LLFI "
               "index is %d\n" % fi_index)

      need_to_calc_fi_cycle = True
      if ('fi_cycle' in locals()) or 'fi_index' in locals():
        need_to_calc_fi_cycle = False

      # fault injection
      for index in range(0, run_number):
        run_id = str(ii)+"-"+str(index)
        outputfile = stddir + "/std_outputfile-" + "run-"+run_id
        errorfile = errordir + "/errorfile-" + "run-"+run_id
        execlist = [fi_exe]

        if need_to_calc_fi_cycle:
          fi_cycle = random.randint(0, int(totalcycles) - 1)

        ficonfig_File = open("llfi.config.fi.txt", 'w')
        if 'fi_cycle' in locals():
          ficonfig_File.write("fi_cycle="+str(fi_cycle)+'\n')
        elif 'fi_index' in locals():
          ficonfig_File.write("fi_index="+str(fi_index)+'\n')

        if 'fi_type' in locals():
          ficonfig_File.write("fi_type="+fi_type+'\n')
        if 'fi_reg_index' in locals():
          ficonfig_File.write("fi_reg_index="+str(fi_reg_index)+'\n')
        if 'fi_bit' in locals():
          ficonfig_File.write("fi_bit="+str(fi_bit)+'\n')
        ficonfig_File.close()

        execlist.extend(optionlist)
        ret = execute(execlist)
        if ret == "timed-out":
          error_File = open(errorfile, 'w')
          error_File.write("Program hang\n")
          error_File.close()
        elif int(ret) < 0:
          error_File = open(errorfile, 'w')
          error_File.write("Program crashed, terminated by the system, return code " + ret + '\n')
          error_File.close()
        elif int(ret) > 0:
          error_File = open(errorfile, 'w')
          error_File.write("Program crashed, terminated by itself, return code " + ret + '\n')
          error_File.close()

################################################################################

if __name__=="__main__":
  if len(sys.argv) == 1:
    usage('Must provide the fault injection executable and its options')
    exit(1)
  main(sys.argv[1:])
