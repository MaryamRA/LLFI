#include "FaultInjector.h"
#include "FaultInjectorManager.h"

class noOpen_API: public FaultInjector {
 public:
  virtual void injectFault(long llfi_index, unsigned size, unsigned fi_bit,
                      char *buf) {
       
                     close(*buf);
  }
};


static RegisterFaultInjector X("noOpen_API", new noOpen_API());

