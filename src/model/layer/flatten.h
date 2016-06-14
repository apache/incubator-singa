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
#ifndef SRC_MODEL_LAYER_FLATTEN_H_
#define SRC_MODEL_LAYER_FLATTEN_H_
#include <utility>
#include <string>
#include <vector>
#include "singa/model/layer.h"

namespace singa {
class Flatten : public Layer {
 public:
  /// \copydoc Layer::layer_type();
  const std::string layer_type() const override { return "Flatten"; }

  /// \copydoc Layer::Setup(const LayerConf&);
  void Setup(const LayerConf &conf) override;

  /// \copydoc Layer::Forward(int flag, const Tensor&);
  const Tensor Forward(int flag, const Tensor &input) override;

  /// \copydoc Layer::Backward(int, const Tensor&, const Tensor&);
  const std::pair<Tensor, vector<Tensor> > Backward(
      int flag, const Tensor &grad) override;

  const int Axis() const { return axis_; }
  const Shape input_shape() const { return input_shape_; }
  const Shape output_shape() const { return output_shape_; }

 protected:
  /// flatten layer reshape the input to 2D, one from 0 to axis_-1, one from
  /// axis_ to end.
  /// if axis_ is 0, reshape the input to 1D.
  int axis_;
  Shape input_shape_, output_shape_;
};
}      // namespace singa
#endif // SRC_MODEL_LAYER_FLATTEN_H_
