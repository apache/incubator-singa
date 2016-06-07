/************************************************************
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
*************************************************************/
#ifndef SRC_CORE_TENSOR__MATH_KERNEL_H_
#define SRC_CORE_TENSOR__MATH_KERNEL_H_


#include "singa_config.h"
#ifdef USE_CUDA

/// TODO(wangwei) Clean the function APIs as commented in tensor_math.h
///  Add 'Context *ctx' as an argument of all cuda functions.
namespace singa {

// TODO(wangwei) make all function templates.
namespace cuda {
void sum(int n, const float *in, float *out);

void sum_row(int rows, int cols, int stride, const float *in, float *out);

void sum_col(int rows, int cols, int stride, const float *in, float *out);

void add_row(int rows, int cols, int stride, const float *in_row,
             const float *in_mat, float *out);

void add(int n, const float *a, const float *b, float *out);

void sub(int n, const float *a, const float *b, float *out);

void exp(int n, const float *in, float *out);

void log(int n, const float *in, float *out);

void sigmoid(int n, const float *in, float *out);

void sigmoid_grad(int n, const float *in, float *out);

void relu(int n, const float *in, float *out);

void relu_grad(int n, const float *in, float *out);

void tanh(int n, const float *in, float *out);

void tanh_grad(int n, const float *in, float *out);

void softplus(int n, const float *in, float *out);

void softplus_grad(int n, const float *in, float *out);

void square(int n, const float *in, float *out);

void square_grad(int n, const float *in, float *out);

void sqrt(int n, const float *in, float *out);

void pow(int n, const float *a, const float *b, float *out);

void mult(int n, const float *a, const float *b, float *out);

void mult(int n, const float *a, const float x, float *out);

void div(int n, const float *a, const float *b, float *out);

void set_value(int n, float v, float *out);

void threshold(int n, float alpha, const float *in, float *out);

// follow the consistency guide for math API
void Div(const size_t num, const float x, const float *in, float *out,
         cudaStream_t s);
void Set(const size_t num, const float x, float *out, cudaStream_t s);
void GT(size_t num, const float *in, const float x, float *out, cudaStream_t s);
void GE(size_t num, const float *in, const float x, float *out, cudaStream_t s);
void LT(size_t num, const float *in, const float x, float *out, cudaStream_t s);
void LE(size_t num, const float *in, const float x, float *out, cudaStream_t s);
}  // cuda

}  // namespace singa

#endif
#endif  // SRC_CORE_TENSOR__MATH_KERNEL_H_
