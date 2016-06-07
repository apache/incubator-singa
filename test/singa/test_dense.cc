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
#include "../src/model/layer/dense.h"
#include "gtest/gtest.h"
#include "singa_config.h"

using singa::Dense;
TEST(Dense, Setup) {
  Dense dense;
  EXPECT_EQ("Dense", dense.layer_type());

  singa::LayerConf conf;
  singa::DenseConf *denseconf = conf.mutable_dense_conf();
  denseconf->set_num_input(2);
  denseconf->set_num_output(3);
  denseconf->set_transpose(false);
  dense.Setup(conf);

  EXPECT_EQ(3u, dense.num_output());
  EXPECT_EQ(2u, dense.num_input());
}
#ifdef USE_CBLAS
TEST(Dense, ForwardCpp) {
  Dense dense;

  singa::LayerConf conf;
  singa::DenseConf *denseconf = conf.mutable_dense_conf();
  denseconf->set_num_input(2);
  denseconf->set_num_output(3);
  denseconf->set_transpose(false);
  dense.Setup(conf);

  const size_t batchsize = 3, vdim = 2, hdim = 3;
  const float x[batchsize * vdim] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f};
  singa::Tensor in(singa::Shape{batchsize, vdim});
  in.CopyDataFromHostPtr(x, batchsize * vdim);

  // set weight
  const float we[hdim * vdim] = {1.0f, 1.0f, 1.0f, 2.0f, 0.0f, 1.0f};
  singa::Tensor weight(singa::Shape{hdim, vdim});
  weight.CopyDataFromHostPtr(we, hdim * vdim);

  const float bia[hdim] = {1.0f, 1.0f, 1.0f};
  singa::Tensor bias(singa::Shape{hdim});
  bias.CopyDataFromHostPtr(bia, hdim);

  dense.set_weight(weight);
  dense.set_bias(bias);

  singa::Tensor out1 = dense.Forward(singa::kTrain, in);
  singa::CppCPU host(0, 1);
  const float *outptr1 = out1.data<const float *>();
  EXPECT_EQ(9u, out1.Size());
  for (int i = 0; i < 3; i++)
    for (int j = 0; j < 3; j++)
      EXPECT_FLOAT_EQ((x[i * 2 + 0] * we[j * 2 + 0] +
                       x[i * 2 + 1] * we[j * 2 + 1] + bia[j]),
                      outptr1[i * 3 + j]);
}
#endif  // USE_CBLAS
#ifdef USE_CUDA
TEST(Dense, BackwardCpp) {
  Dense dense;

  singa::LayerConf conf;
  singa::DenseConf *denseconf = conf.mutable_dense_conf();
  denseconf->set_num_input(2);
  denseconf->set_num_output(3);
  denseconf->set_transpose(false);
  dense.Setup(conf);

  const size_t batchsize = 3, vdim = 2, hdim = 3;
  const float x[batchsize * vdim] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f};
  singa::CudaGPU cuda(0, 1);
  singa::Tensor in(singa::Shape{batchsize, vdim});
  in.CopyDataFromHostPtr(x, batchsize * vdim);

  // set weight
  const float we[hdim * vdim] = {1.0f, 1.0f, 1.0f, 2.0f, 0.0f, 1.0f};
  singa::Tensor weight(singa::Shape{hdim, vdim});
  weight.CopyDataFromHostPtr(we, hdim * vdim);

  const float bia[hdim] = {1.0f, 1.0f, 1.0f};
  singa::Tensor bias(singa::Shape{hdim});
  bias.CopyDataFromHostPtr(bia, hdim);

  dense.set_weight(weight);
  dense.set_bias(bias);

  singa::Tensor out1 = dense.Forward(singa::kTrain, in);

  // grad
  const float dy[batchsize * hdim] = {1.0f, 1.0f, 1.0f, 2.0f, 2.0f,
                                      2.0f, 3.0f, 3.0f, 3.0f};
  singa::Tensor grad(singa::Shape{batchsize, hdim});
  grad.CopyDataFromHostPtr(dy, batchsize * hdim);

  const auto ret = dense.Backward(singa::kTrain, grad);
  singa::CppCPU host(0, 1);
  singa::Tensor in_grad = ret.first;
  singa::Tensor dweight = ret.second.at(0);
  singa::Tensor dbias = ret.second.at(1);
  const float *dx = in_grad.data<const float *>();
  EXPECT_EQ(6u, in_grad.Size());
  for (int i = 0; i < 3; i++)
    for (int j = 0; j < 2; j++)
      EXPECT_FLOAT_EQ(
          (dy[i * 3 + 0] * we[0 * 2 + j] + dy[i * 3 + 1] * we[1 * 2 + j] +
           dy[i * 3 + 2] * we[2 * 2 + j]),
          dx[i * 2 + j]);
  const float *dweightx = dweight.data<const float *>();
  EXPECT_EQ(6u, dweight.Size());
  for (int i = 0; i < 3; i++)
    for (int j = 0; j < 2; j++)
      EXPECT_FLOAT_EQ(
          (dy[0 * 3 + i] * x[0 * 2 + j] + dy[1 * 3 + i] * x[1 * 2 + j] +
           dy[2 * 3 + i] * x[2 * 2 + j]),
          dweightx[i * 2 + j]);
  const float *dbiasx = dbias.data<const float *>();
  EXPECT_EQ(3u, dbias.Size());
  for (int i = 0; i < 3; i++)
    EXPECT_FLOAT_EQ((dy[0 * 3 + i] + dy[1 * 3 + i] + dy[2 * 3 + i]), dbiasx[i]);
}
#endif

#ifdef USE_CUDA
TEST(Dense, ForwardCuda) {
  Dense dense;

  singa::LayerConf conf;
  singa::DenseConf *denseconf = conf.mutable_dense_conf();
  denseconf->set_num_input(2);
  denseconf->set_num_output(3);
  denseconf->set_transpose(false);
  dense.Setup(conf);

  const size_t batchsize = 3, vdim = 2, hdim = 3;
  const float x[batchsize * vdim] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f};
  singa::CudaGPU cuda(0, 1);
  singa::Tensor in(singa::Shape{batchsize, vdim}, &cuda);
  in.CopyDataFromHostPtr(x, batchsize * vdim);

  // set weight
  const float we[hdim * vdim] = {1.0f, 1.0f, 1.0f, 2.0f, 0.0f, 1.0f};
  singa::Tensor weight(singa::Shape{hdim, vdim}, &cuda);
  weight.CopyDataFromHostPtr(we, hdim * vdim);

  const float bia[hdim] = {1.0f, 1.0f, 1.0f};
  singa::Tensor bias(singa::Shape{hdim}, &cuda);
  bias.CopyDataFromHostPtr(bia, hdim);

  dense.set_weight(weight);
  dense.set_bias(bias);

  singa::Tensor out1 = dense.Forward(singa::kTrain, in);
  singa::CppCPU host(0, 1);
  out1.ToDevice(&host);
  const float *outptr1 = out1.data<const float *>();
  EXPECT_EQ(9u, out1.Size());
  for (int i = 0; i < 3; i++)
    for (int j = 0; j < 3; j++)
      EXPECT_FLOAT_EQ((x[i * 2 + 0] * we[j * 2 + 0] +
                       x[i * 2 + 1] * we[j * 2 + 1] + bia[j]),
                      outptr1[i * 3 + j]);
}
TEST(Dense, BackwardCuda) {
  Dense dense;

  singa::LayerConf conf;
  singa::DenseConf *denseconf = conf.mutable_dense_conf();
  denseconf->set_num_input(2);
  denseconf->set_num_output(3);
  denseconf->set_transpose(false);
  dense.Setup(conf);

  const size_t batchsize = 3, vdim = 2, hdim = 3;
  const float x[batchsize * vdim] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f};
  singa::CudaGPU cuda(0, 1);
  singa::Tensor in(singa::Shape{batchsize, vdim}, &cuda);
  in.CopyDataFromHostPtr(x, batchsize * vdim);

  // set weight
  const float we[hdim * vdim] = {1.0f, 1.0f, 1.0f, 2.0f, 0.0f, 1.0f};
  singa::Tensor weight(singa::Shape{hdim, vdim}, &cuda);
  weight.CopyDataFromHostPtr(we, hdim * vdim);

  const float bia[hdim] = {1.0f, 1.0f, 1.0f};
  singa::Tensor bias(singa::Shape{hdim}, &cuda);
  bias.CopyDataFromHostPtr(bia, hdim);

  dense.set_weight(weight);
  dense.set_bias(bias);

  singa::Tensor out1 = dense.Forward(singa::kTrain, in);

  // grad
  const float dy[batchsize * hdim] = {1.0f, 1.0f, 1.0f, 2.0f, 2.0f,
                                      2.0f, 3.0f, 3.0f, 3.0f};
  singa::Tensor grad(singa::Shape{batchsize, hdim}, &cuda);
  grad.CopyDataFromHostPtr(dy, batchsize * hdim);

  const auto ret = dense.Backward(singa::kTrain, grad);
  singa::CppCPU host(0, 1);
  singa::Tensor in_grad = ret.first;
  singa::Tensor dweight = ret.second.at(0);
  singa::Tensor dbias = ret.second.at(1);
  in_grad.ToDevice(&host);
  const float *dx = in_grad.data<const float *>();
  EXPECT_EQ(6u, in_grad.Size());
  for (int i = 0; i < 3; i++)
    for (int j = 0; j < 2; j++)
      EXPECT_FLOAT_EQ(
          (dy[i * 3 + 0] * we[0 * 2 + j] + dy[i * 3 + 1] * we[1 * 2 + j] +
           dy[i * 3 + 2] * we[2 * 2 + j]),
          dx[i * 2 + j]);
  dweight.ToDevice(&host);
  const float *dweightx = dweight.data<const float *>();
  EXPECT_EQ(6u, dweight.Size());
  for (int i = 0; i < 3; i++)
    for (int j = 0; j < 2; j++)
      EXPECT_FLOAT_EQ(
          (dy[0 * 3 + i] * x[0 * 2 + j] + dy[1 * 3 + i] * x[1 * 2 + j] +
           dy[2 * 3 + i] * x[2 * 2 + j]),
          dweightx[i * 2 + j]);
  dbias.ToDevice(&host);
  const float *dbiasx = dbias.data<const float *>();
  EXPECT_EQ(3u, dbias.Size());
  for (int i = 0; i < 3; i++)
    EXPECT_FLOAT_EQ((dy[0 * 3 + i] + dy[1 * 3 + i] + dy[2 * 3 + i]), dbiasx[i]);
}
#endif
