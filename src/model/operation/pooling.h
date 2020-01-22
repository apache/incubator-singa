/*********************************************************
*
* Licensed to the Apache Software Foundation (ASF) under one
* or more contributor license agreements.  See the NOTICE file
* distributed with this work for additional information
* regarding copyright ownership.  The ASF licenses this file
* to you under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License.  You may obtain a copy of the License at
*
*   http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
* KIND, either express or implied.  See the License for the
* specific language governing permissions and limitations
* under the License.
*
************************************************************/
#ifndef SINGA_MODEL_OPERATION_POOLING_H_
#define SINGA_MODEL_OPERATION_POOLING_H_

#include "singa/core/tensor.h"
#include <string>

#ifdef USE_MKLDNN
#include <mkldnn.hpp>
#endif // USE_MKLDNN

#ifdef USE_CUDNN
#include "../layer/cudnn_utils.h"
#include <cudnn.h>
#endif

namespace singa {

class PoolingHandle {
public:
  PoolingHandle(const Tensor &input, const std::vector<int> &kernel_size,
                const std::vector<int> &stride, const std::vector<int> &padding,
                const bool is_max = true);
  ~PoolingHandle();

  int kernel_w;
  int pad_w;
  int stride_w;
  int kernel_h;
  int pad_h;
  int stride_h;

  int batchsize;
  int channels;
  int height;
  int width;

  int pooled_height;
  int pooled_width;

  bool is_max_pooling;

#ifdef USE_MKLDNN
  mkldnn::memory::data_type dtype;
  mkldnn::memory::dims x_dims;
  mkldnn::memory::dims y_dims;
  mkldnn::memory::dims s_dims;
  mkldnn::memory::dims k_dims;
  mkldnn::memory::dims p_dims;
  mkldnn::algorithm pooling_algo;
  const mkldnn::memory::desc *x_md = nullptr;
  const mkldnn::memory::desc *y_md = nullptr;
  const mkldnn::pooling_forward::desc *pool_fwd_d = nullptr;
  const mkldnn::pooling_forward::primitive_desc *pool_fwd_pd = nullptr;
  const mkldnn::memory::primitive_desc *pool_ws_d = nullptr;
  const mkldnn::memory *ws_mem = nullptr;
#endif // USE_MKLDNN
};

#ifdef USE_MKLDNN

Tensor CpuPoolingForward(const PoolingHandle &ph, const Tensor &x);
Tensor CpuPoolingBackward(const PoolingHandle &ph, const Tensor &dy,
                          const Tensor &x, const Tensor &y);

#endif // USE_MKLDNN

#ifdef USE_CUDNN
class CudnnPoolingHandle : public PoolingHandle {
public:
  CudnnPoolingHandle(const Tensor &input, const std::vector<int> &kernel_size,
                     const std::vector<int> &stride,
                     const std::vector<int> &padding, const bool is_max = true);
  ~CudnnPoolingHandle();

  cudnnTensorDescriptor_t x_desc = nullptr;
  cudnnTensorDescriptor_t y_desc = nullptr;
  cudnnPoolingDescriptor_t pool_desc = nullptr;
  cudnnNanPropagation_t nan_prop = CUDNN_PROPAGATE_NAN;
};

Tensor GpuPoolingForward(const CudnnPoolingHandle &cph, const Tensor &x);

Tensor GpuPoolingBackward(const CudnnPoolingHandle &cph, const Tensor &dy,
                          const Tensor &x, const Tensor &y);

#endif // USE_CUDNN

} // namespace singa

#endif // SINGA_MODEL_OPERATION_POOLING_H_
