// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.
#pragma once

#include "AllReduceAlgo.h"
#include "collectives.h"

namespace nccl {
namespace algorithms {

class AllReduceDdaNvsTreeIpcAlgo : public AllReduceAlgo {
 public:
  AllReduceDdaNvsTreeIpcAlgo(
      const void* sendbuff,
      void* recvbuff,
      size_t count,
      ncclDataType_t datatype,
      ncclRedOp_t op,
      ncclComm* comm,
      cudaStream_t stream,
      const DdaDeviceState* devStates_d,
      uintptr_t barrierFlag,
      int multiProcessorCount);
  ~AllReduceDdaNvsTreeIpcAlgo();

  ncclResult_t allReduce() override;

 private:
  template <typename T>
  ncclResult_t launchKernel();

  const void* sendbuff_{nullptr};
  void* recvbuff_{nullptr};
  size_t count_{0};
  ncclDataType_t datatype_{ncclInt8};
  ncclRedOp_t op_{ncclSum};
  ncclComm* comm_{nullptr};
  cudaStream_t stream_{nullptr};
  const DdaDeviceState* devStates_d_{nullptr};
  uintptr_t barrierFlag_{0};
  const int multiProcessorCount_{0};
};

} // namespace algorithms
} // namespace nccl