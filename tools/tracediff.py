#!/usr/bin/python

#traceDiff.py
#  Author: Sam Coulter
#  This python script is part of the greater LLFI system.
#  This script will examine two tracing output files generated by running a program after
#  the LLFI traceInst pass has been performed.
#   Exec: traceDiff.py goldenTrace faultyTrace
#  Input: GoldenTrace/faultyTrace - Trace output files after running a traced program
#  Output: Trace Summary into Standard output, redirect with PIPE to save to file


import sys
import os
import subprocess
import glob
import difflib

class diffBlock:
  def __init__(self, header, start):
    #Split the block (diff) header into parts and store
    #@@ -1,5 +1,5 @@
    #    1,5  1,5   
    origHeader, newHeader = header.replace('@',' ').replace('+',' ').replace('-',' ').split()
    origsplit = origHeader.split(',')
    newsplit = newHeader.split(',')

    self.origStart = int(origsplit[0]) + start
    self.origLineStart = int(origsplit[0])
    if (len(origsplit) > 1):
      self.origEnd =  int(origsplit[1]) + start      
    else:
      self.origEnd = self.origStart

    self.newStart = int(newsplit[0]) + start
    self.newLineStart = int(newsplit[0])
    if (len(newsplit) > 1):
      self.newEnd = int(newsplit[1]) + start
    else:
      self.newEnd = self.newStart
    self.origLength = int(self.origEnd) - int(self.origStart) - 2
    self.newLength = int(self.newEnd) - int(self.newStart) - 2

    self.origLines = []
    self.newLines = []

    self.endLines = []
    self.firstLine = 0

    self.start = start

    self.preLine = None

  #print some info for debugging
  def printdebug(self):
    print self.origStart, "to", self.origEnd, "length", self.origLength
    for line in self.origLines:
      line.printself()
    print self.newStart, "to", self.newEnd, "length", self.newLength
    for line in self.newLines:
      line.printself()

  #print the block analysis summary
  def printSummary(self):  
    print "Difference detected at inst# (orig/new):", \
    self.origStart-1, "/", self.newStart-1     
    print "Pre Diff: ID:", self.preLine.ID, "OPCode:", self.preLine.OPCode, \
    "Value:", self.preLine.Value

    olcounter, nlcounter, lcounter = 0,0,0
    for oline, nline in zip(self.origLines[:], self.newLines[:]):
      if (oline.ID == nline.ID) and (oline.OPCode == nline.OPCode):
        print "Data Diff: ID:", oline.ID, \
        "OPCode:", oline.OPCode, "Value:", oline.Value, \
        "/", nline.Value
        lcounter = lcounter + 1
      else:
        break

    MAXCTRLFLOWTRACE = 10
    print "Ctrl Diff:"
    print " >Original Control Flow"
    if len(self.origLines)-lcounter == 0:
      print " -->Post Diff"
    else:
      olflow = [str(x.ID) for x in self.origLines[lcounter:lcounter+MAXCTRLFLOWTRACE]]
      print " ->", ' '.join(olflow)
      if lcounter+MAXCTRLFLOWTRACE < len(self.origLines):
        print "  Followed by", len(self.origLines) - (lcounter+MAXCTRLFLOWTRACE), "instructions"
      else:
        print " -->Post Diff"

    print " >New Control Flow"
    if len(self.newLines)-lcounter == 0:
      print " -->Post Diff"
    else:
      nlflow = [str(x.ID) for x in self.newLines[lcounter:lcounter+MAXCTRLFLOWTRACE]]
      print " ->", ' '.join(nlflow)
      if lcounter+MAXCTRLFLOWTRACE < len(self.newLines):
        print "  Followed by", len(self.newLines) - (lcounter+MAXCTRLFLOWTRACE), "instructions"
      else:
        print " -->Post Diff"

    for line in self.endLines:
      print "Post Diff:", ' '.join(str(line).split())


class diffLine:
  def __init__(self, rawLine):
    self.raw = rawLine
    elements = str(rawLine).split()
    #+ID: 14\tOPCode: sub\tValue: 1336d337
    assert (elements[0] in ["ID:","-ID:","+ID:"] and elements[2] == "OPCode:" and  \
      elements[4] == "Value:"), "DiffLine constructor called incorrectly"
    self.ID = int(elements[1])
    self.OPCode = str(elements[3])
    self.Value = str(elements[5])

  def printself(self):
    print self.ID, self.OPCode, self.Value

  def __str__(self):
    return self.raw

def traceDiff(argv, output = 0, configArgs = []):
  #save stdout so we can redirect it without mangling other python scripts
  oldSTDOut = sys.stdout
  
  if output != 0:
    sys.stdout = open(output, "w")
  if (len(argv) != 3):
    print "ERROR: running option: traceDiff <golden output> <faulty output>"
    exit(1)

  origFile = open(argv[1], 'r')
  origTrace = origFile.read()
  origFile.close()

  newFile = open(argv[2], 'r')
  newTrace = newFile.read()
  newFile.close()

  goldTraceLines = origTrace.split("\n")
  origTraceLines = origTrace.split("\n")
  newTraceLines =  newTrace.split("\n")

  #Examine Header of Trace File
  header = newTraceLines[0].split(' ')
  for i in range(0, len(header) - 1):
    keyword = header[i]
    if keyword == "#TraceStartInstNumber:":
    #Remove traces from golden trace that happened before fault injection point
      newTraceStartPoint = int(header[i+1])
      newTraceLines.pop(0)
      for i in range (0,newTraceStartPoint-1):
        origTraceLines.pop(0)

  diff = list(difflib.unified_diff(origTraceLines, newTraceLines, lineterm=''))

  if (diff):
    diff.pop(0) #Remove File Context lines from diff
    diff.pop(0)

    if "-printDiff" in configArgs:
      print '\n'.join(diff)
      print "**************"
      print "\n"

    i = 0
    while (i <= len(diff)-1):    
      if diff[i][0:3] in ["@@ "]:
        block = diffBlock(diff[i], newTraceStartPoint)
        block.preLine = diffLine(goldTraceLines[newTraceStartPoint+block.newLineStart-3])
        i=i+1
        while (diff[i][0:4] in ["-ID:","+ID:"," ID:"]):
          if (diff[i][0:4] == "-ID:"):
            block.origLines.append(diffLine(diff[i]))
          elif (diff[i][0:4] == "+ID:"):
            block.newLines.append(diffLine(diff[i]))
          elif (diff[i][0:4] == " ID:"):
            block.endLines.append(diffLine(diff[i][1:]))
          i = i + 1
          if i > len(diff)-1:
            break
        block.printSummary()
        print "\n"
      i = i + 1
      
  #restore stdout
  sys.stdout = oldSTDOut

if (__name__ == "__main__"):
  traceDiff(sys.argv)
