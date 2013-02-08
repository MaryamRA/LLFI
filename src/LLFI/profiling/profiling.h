//This pass is run after the transform pass for inserting hooks for fault injection 
#ifndef PROFILING_H
#define PROFILING_H

#include "llvm/Constants.h"
#include "llvm/DerivedTypes.h"
#include "llvm/GlobalValue.h"
#include "llvm/Pass.h"
#include "llvm/Function.h"
#include "llvm/Module.h"
#include "llvm/Support/CFG.h"
#include "llvm/Support/InstIterator.h"
#include "llvm/Support/InstVisitor.h"
#include "llvm/Support/Debug.h"
#include "llvm/Instruction.h"
#include "llvm/Instructions.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/LLVMContext.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Analysis/PostDominators.h"
#include "llvm/Analysis/Dominators.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Support/CommandLine.h"
//////////////////////////////////////////
//#include "../filter/filter.h"
#include <iostream>
#include <fstream>
#include <list>
#include <map>
#include <vector>
#include <stack>
#include <algorithm>
#include <set>
#include <string>
//////////////////////////////////////////

//----------Parameter types-------------
#define INTEGER  1
#define ARRAY 2
#define STRUCT 3
#define POINTER 4
#define FLOAT 5
#define DOUBLE 6
//--------------------------------------

//----------Fault information-----------
#define ONE_BIT_FLAG_POS 0
#define INCLUSIVE_FLAG_POS 1
#define LOWERBOUND_POS 2
#define UPPERBOUND_POS 3
//-------------------------------------- //this part is useless here, it should be used in faultinjection and fi_random.c, just write here

using namespace llvm;
using namespace std;
//might extend with profiling for defs of branches
static cl::opt<char> profileoption("profileoption", cl::desc("The profiling is done for option: branch (b) or all instructions(a) or defs of branches(d) or backward Slice(s)!"), cl::value_desc("profileoption"));

namespace
{
	class ProfilingPass:public FunctionPass {
		public:
			ProfilingPass() : FunctionPass(ID) {}
			virtual bool doInitialization(Module &M);
			virtual bool doFinalization(Module &M);
			virtual bool runOnFunction(Function &F);	
			static char ID; // Pass identification, replacement for typeid
			//Instruction* insertPrintStatement(Instruction *I);
			
		private:
			enum optiontype {BRANCH, DEF, ALL, BACKWARD_SLICE};
			bool is_used_by_branch(Instruction *I);
			Instruction* getFI(Instruction *I);
//			uint64_t getStaticId(Instruction *I); //get the static id of the fault injection hook for I
// 			bool is_in_funcavoidlist(string funcname);
 			bool is_injectFaultFuncCall(Instruction *I);
 			bool filter(Instruction *I);
			std::string Filename, ErrorInfo;
			std::string Filenameptrvar;

			//------------------------FOR filter USE-------------------------
			map<string, set<unsigned int> > map_func_argu; //Qining
			map<string, vector<int> > map_func_fault_range; //Qining
			map<string, set<unsigned int> > map_func_fault_type; //Qining
			//---------------------------------------------------------------
  };
}
char ProfilingPass::ID=0;

#endif
