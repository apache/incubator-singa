/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "./dense.h"
#include "singa/model/layer.h"
#include <vector>

namespace singa {
using std::vector;

Dense::~Dense() {
  // delete weight_;
  // delete bias_;
}
void Dense::Setup(const Shape& in_sample, const LayerConf &conf) {
  Layer::Setup(in_sample, conf);
  auto dense_conf = conf.dense_conf();
  CHECK_EQ(in_sample.size(), 1u);
  vdim_ = in_sample.at(0);
  hdim_ = dense_conf.num_output();
  transpose_ = dense_conf.transpose();
  if (transpose_)
    weight_.Reshape(Shape{vdim_, hdim_});
  else
    weight_.Reshape(Shape{hdim_, vdim_});
  bias_.Reshape(Shape{hdim_});
  param_values_.push_back(&weight_);
  param_values_.push_back(&bias_);
  for (auto specs: conf.param())
    param_specs_.push_back(specs);
}

/// \copydoc Layer::Forward(int flag, const Tensor&)
const Tensor Dense::Forward(int flag, const Tensor &input) {
  CHECK(buf_.empty());
  Tensor output;
  CHECK_EQ(input.nDim(), 2u);
  if (transpose_)  // use the transposed version of weight_ for computing
    output = Mult(input, weight_);
  else
    output = Mult(input, weight_.T());
  AddRow(bias_, &output);
  if (flag & kTrain)
    buf_.push(input);
  return output;
}

/// \copydoc Layer::Backward(int, const Tensor&, const Tensor&);
const std::pair<Tensor, vector<Tensor>> Dense::Backward(int flag,
                                                        const Tensor &grad) {
  vector<Tensor> param_grad;
  CHECK(!buf_.empty());
  Tensor src_data = buf_.top();
  buf_.pop();
  Tensor db, dw, dx;
  db.ResetLike(bias_);
  dw.ResetLike(weight_);
  dx.ResetLike(src_data);
  SumRows(grad, &db);
  if (transpose_) {
    dx = Mult(grad, weight_.T());
    dw = Mult(src_data.T(), grad);
  } else {
    dx = Mult(grad, weight_);
    dw = Mult(grad.T(), src_data);
  }
  param_grad.push_back(dw);
  param_grad.push_back(db);
  return std::make_pair(dx, param_grad);
}

void Dense::ToDevice(std::shared_ptr<Device> device) {
  Layer::ToDevice(device);
  weight_.ToDevice(device);
  bias_.ToDevice(device);
}
} // namespace singa
