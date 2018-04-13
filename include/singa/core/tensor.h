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

#ifndef SINGA_CORE_TENSOR_H_
#define SINGA_CORE_TENSOR_H_

#include <vector>
#include <tuple>
#include <memory>
#include <algorithm>

#include "singa/core/common.h"
#include "singa/core/device.h"
#include "singa/proto/core.pb.h"
#include "singa/utils/logging.h"

using std::vector;
using std::tuple;
using std::reverse;
namespace singa {

typedef vector<size_t> Shape;
/// hardcode the width of types defined in DataType
const size_t kDataWidth[] = {sizeof(float),  sizeof(float) / 2,
                             sizeof(int),    sizeof(char),
                             sizeof(double), sizeof(unsigned char)};
inline size_t SizeOf(DataType t) {
  static_assert(kNumDataType == sizeof(kDataWidth) / sizeof(size_t),
                "Num of data types not match num of data width");
  CHECK_GT(kNumDataType, t);
  return kDataWidth[t];
}

/// A Tensor instance is a multi-dimensional array resident on a Device
/// (default device is the host CPU). The internal data is allocated in lazy
/// manner.
/// Linear algebra, neural net and random operations are provided against
/// Tensor.
/// For all operations, if the result tensor is passed as an argument,
/// then it must be set up correctly (shape, device). Otherwise, runtime error
/// like SegmentFault would happen. Simply type/device check would be conducted.
class Tensor {
 public:
  ~Tensor();
  Tensor();
  explicit Tensor(Shape &&shape, DataType dtype = kFloat32);
  explicit Tensor(const Shape &shape, DataType dtype = kFloat32);

  Tensor(Shape &&shape, std::shared_ptr<Device> dev, DataType dtype = kFloat32);
  Tensor(const Shape &shape, std::shared_ptr<Device> dev, DataType dtype = kFloat32);

  /// Copy Tensor to share the internal data.  No deep copy.
  Tensor(const Tensor &from);
  /// Copy Tensor to share the internal data.  No deep copy. For 2 tensors sharing same block but different strides.
  Tensor(const Tensor &from, Shape &new_shape, vector<int> &new_strides);
  /// Copy Tensor to share the internal data.  No deep copy.
  Tensor(Tensor &&from);

  /// For functions in xx_math.cc to access the block.
  /// Users should not operate against Block directly.
  /// block_ is allocated in constructors.
  Block *block() const { return block_; }
  void SetBlock(Block *block);

  std::shared_ptr<Device> device() const { return device_; }

  /// return immutable Tensor values with given type.
  template <typename SType>
  const SType *data() const {
    return static_cast<const SType *>(block()->data());
  }

  /// used for swig code to convert Tensor into numpy array.
  /// It gets data into 'value'
  template <typename SType>
  void GetValue(SType *value, const size_t num) {
    CHECK(device_ == defaultDevice);
    const SType* ptr = data<SType>();
    for(size_t i = 0; i < num; i++) value[i] = ptr[i];
  }

  /// data type, including kFloat16, kFloat32, kInt
  const DataType data_type() const { return data_type_; }

  const Shape &shape() const { return shape_; }

  const size_t shape(const size_t idx) const {
    CHECK_LT(idx, shape_.size());
    return shape_.at(idx);
  }

  size_t nDim() const { return shape_.size(); }

  bool empty() const { return nDim() == 0; }

  //bool transpose() const { return transpose_; }
<<<<<<< HEAD
<<<<<<< HEAD
  bool transpose() const { return (strides_[0] != 1); }

=======
>>>>>>> e658bbf... Add files via upload
=======
  bool transpose() const { return (strides_[0] != 1); }

>>>>>>> dfdac84... Add files via upload
  const vector<int>& strides() const { return strides_; }

  const vector<int>& shape_multipliers() const { return shape_multipliers_; }

  /// return true if the content of the tensor is initialized
  bool initailized() const {
    return block_ != nullptr && block_->initialized();
  }

  /// return number of total elements
  size_t Size() const {
    if (block_ == nullptr) return 0u;
    CHECK_EQ(block_->size() % SizeOf(data_type_), 0u);
    return block_->size() / SizeOf(data_type_);
  }

  /// return memory size (i.e., Bytes)
  size_t MemSize() const { return block_->size(); }

  /// Reset the tensor shape, it may reallocate block, if MemSize() changes.
  void Reshape(const Shape &shape);
  void Reshape(Shape &&shape);

  /// Reset the shape, device, and data type as given tensor.
  /// If block size changes, then reallocate a new block. The previous block
  /// would
  /// be deleted.
  void ResetLike(const Tensor &t);

  /// Reset the data type, it would reallocate block if type changes.
  void AsType(const DataType type);

  /// Reset the device.
  /// If the target device is a diff device, then do deep data copy.
  void ToDevice(std::shared_ptr<Device> dev);

  /// Equivalent to ToDevice(host_dev).
  void ToHost();

  /// Set each element of the tensor to be x
  template <typename SType>
  void SetValue(const SType x);

  /// For init the tensor values, copy 'num' elements from 'src' to the internal
  /// memory with 'offset' (elements).
  template <typename SType>
  void CopyDataFromHostPtr(const SType *src, const size_t num,
                           const size_t offset = 0);

  /// Copy data from another Tensor which may be on a diff device.
  /// Meta data would not be copied!
  void CopyData(const Tensor &other);

  /// Deserialize data, shape and transpose from protobuf object.
  void FromProto(const singa::TensorProto &proto);

  /// Serialize data, shape and transpose to protobuf object.
  void ToProto(singa::TensorProto *proto) const;

  /// return an exactly the same Tensor with data been deep copied to the given
  /// device. If 'device' is nullptr, then clone it one the current device.
  Tensor Clone(std::shared_ptr<Device> device = nullptr) const;

  // Tensor operations

  /// Matrix transpose.  Valid only if shape.size() == 2.
  /// No data copy, just set the transpose_ filed of the returned tensor.
  Tensor T() const;

  Tensor Transpose() const;

  Tensor Transpose(Shape axes) const;

  /// Copy the meta info with data block shared.
  Tensor &operator=(const Tensor &in);

  /// Copy the meta info with data block shared.
  Tensor &operator=(Tensor &&in);

  Tensor &operator+=(const Tensor &in);
  // void operator+=(Tensor&& in);
  Tensor &operator-=(const Tensor &in);
  // void operator-=(Tensor&& in);
  Tensor &operator*=(const Tensor &in);
  // void operator*=(Tensor&& in);
  Tensor &operator/=(const Tensor &in);
  // void operator/=(Tensor&& in);

  // Scalar operations.

  /// SType is a scalar type
  template <typename SType>
  Tensor &operator+=(const SType x);

  /// SType is a scalar type
  template <typename SType>
  Tensor &operator-=(const SType x);

  /// SType is a scalar type
  template <typename SType>
  Tensor &operator*=(const SType x);

  /// SType is a scalar type
  template <typename SType>
  Tensor &operator/=(const SType x);

  /// Return average L1 norm
  float L1() const;
  /// Return average L2 norm
  float L2() const;

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 4aa09f1... Add files via upload
  //generate strides automatically if stride field is not passed
void Generate_Strides(){
    if(shape_.size()==0){
      strides_ = {1};
      return void();
    }
    strides_.clear();
    size_t dim = Size();
    int cumulative_product = 1;
<<<<<<< HEAD
<<<<<<< HEAD
    for (size_t n=0; n<shape_.size(); ++n) {
        cumulative_product = cumulative_product*shape_[n];
        strides_.push_back(dim/cumulative_product);
    }
    reverse(strides_.begin(), strides_.end());
=======
    for (int n=0; n<shape_.size(); ++n) {
=======
    for (size_t n=0; n<shape_.size(); ++n) {
>>>>>>> c17b2f5... Add files via upload
        cumulative_product = cumulative_product*shape_[n];
        strides_.push_back(dim/cumulative_product);
    }
<<<<<<< HEAD
    std::reverse(strides_.begin(), strides_.end());
>>>>>>> 4aa09f1... Add files via upload
=======
    reverse(strides_.begin(), strides_.end());
>>>>>>> e3fdfe3... Add files via upload
};

//generate shape multipliers
//for e.g. tensor of shape (3,3), stride (1,3) will have shape multipliers of (3,1)
//for e.g. tensor of shape (3,3), stride (3,1) will also have shape multipliers of (3,1)
//this means that the 3rd, 6th, and 9th index of the array will always be the starting element of their respective rows
//so we need to need use the inner stride when jumping from 1st->2nd element, and outer stride when jumping from 2nd->3rd
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
vector<int> Generate_Shape_Multipliers(Shape y_shape) {
=======
vector<int> Generate_Shape_Multipliers(Shape y_shape) const {
>>>>>>> 15489ad... updated Generate_Shape_Multipliers function to a const function
    if(y_shape.size()==0){
      return {1};
    }
    reverse(y_shape.begin(), y_shape.end());
    vector<int> shape_multipliers = {};
    int cumulative_product = 1;

    shape_multipliers.push_back(1);
    for (size_t n=0; n<(y_shape.size()-1); ++n) {
<<<<<<< HEAD
        cumulative_product = cumulative_product*y_shape[n];
        shape_multipliers.push_back(cumulative_product);
    }
    reverse(shape_multipliers.begin(), shape_multipliers.end());
    return shape_multipliers;
};

// ******************************************************************************************
// Some traversal operations (works on const declarations without modifying tensor variables)
// ******************************************************************************************

//generate a traversal_info vector based on the tensor's shape for the traverse_next function to work
vector<int> generate_traversal_info() const {
    vector<int> traversal_info = {};
    for(size_t n=0; n<(shape_.size()+2); ++n) {
      traversal_info.push_back(0);
    }
    return traversal_info;
};

//this function checks whether the next index falls on a special multiplier of the outer shape
//so the algorithm knows when to jump over/back to a starting element of the outer shape
//for e.g. in [[1,4,7], [2,5,8], [3,6,9]], elements 1,2,3 are the starting elements of their respective rows
//this additional check only has 1 loop for 2d matrix
//but runtime performance might degrade to O(nlog(n)) for higher dimensional tensors
int determine_order(int counter) const {
    for (size_t n=0; n<(shape_multipliers_.size()-1); ++n) {
        if((counter%shape_multipliers_[n])==0){
            return ((shape_multipliers_.size()) - 1 - n);
        }
    }
    return 0;
};

//this function updates the base indexes with the current index after every single traversal step, can be generalized beyond 2d cases
void update_base_index(std::vector<int>& traversal_info) const {
    for (int n=0; n<(traversal_info[shape_.size()+1]+1); ++n) {
        traversal_info[n] = traversal_info[shape_.size()];
    }
};

//function to traverse a const strided tensor object
//it requires an additional vector, traversal_info {0,0,0,0 ...}, comprising (shape_.size()+2) elements of 0
//for e.g. 2d matrix:
//index 0 and 1 store the base row and column index respectively
//index 2 stores the current index of the traversal
//index 3 stores the order of the traversal for e.g. if the order is 0, it means the next element can be navigated to using the innermost stride
void traverse_next(std::vector<int>& traversal_info, int counter) const {
    update_base_index(traversal_info);
    traversal_info[shape_.size()+1] = determine_order(counter);
    traversal_info[shape_.size()] = traversal_info[traversal_info[shape_.size()+1]]+strides_[traversal_info[shape_.size()+1]];
};

// ******************************************************************************************
// traversal operations end
// ******************************************************************************************
=======
=======
std::vector<int> Generate_Shape_Multipliers(std::vector<int> y_shape) {
    std::reverse(y_shape.begin(), y_shape.end());
    std::vector<int> shape_multipliers = {};
=======
vector<int> Generate_Shape_Multipliers(vector<int> y_shape) {
=======
vector<int> Generate_Shape_Multipliers(Shape y_shape) {
>>>>>>> 3b59660... Add files via upload
    reverse(y_shape.begin(), y_shape.end());
    vector<int> shape_multipliers = {};
>>>>>>> 8c632c2... Add files via upload
    int cumulative_product = 1;

    shape_multipliers.push_back(1);
    for (int n=0; n<(y_shape.size()-1); ++n) {
=======
>>>>>>> c17b2f5... Add files via upload
        cumulative_product = cumulative_product*y_shape[n];
        shape_multipliers.push_back(cumulative_product);
    }
    reverse(shape_multipliers.begin(), shape_multipliers.end());
    return shape_multipliers;
};

<<<<<<< HEAD
>>>>>>> 4aa09f1... Add files via upload
    // ************************
  // Some traversal operations (works on const declarations without modifying tensor variables)
  // ************************

  //this function checks whether the next index falls on a special multiplier of the outer shape
  //so the algorithm knows when to jump over/back to a starting element of the outer shape
  //for e.g. in [[1,4,7], [2,5,8], [3,6,9]], elements 1,2,3 are the starting elements of their respective rows
  //this additional check only has 1 loop for 2d matrix
  //but runtime performance might degrade to O(nlog(n)) for higher dimensional tensors
  int determine_order(int counter) const {
      for (size_t n=0; n<(shape_multipliers_.size()-1); ++n) {
          if((counter%shape_multipliers_[n])==0){
              return ((shape_multipliers_.size()) - 1 - n);
          }
      }
      return 0;
  };

  //this function updates the base indexes with the current index after every single traversal step, can be generalized beyond 2d cases
  void update_base_index(std::vector<int>& traversal_info) const {
      for (int n=0; n<(traversal_info[3]+1); ++n) {
          traversal_info[n] = traversal_info[2];
      }
  };

  //function to traverse a const strided tensor object
  //it requires an additional vector, traversal_info {0,0,0,0}, comprising 4 elements
  //index 0 and 1 store the base row and column index respectively (for 2d matrix)
  //index 2 stores the current index of the traversal
  //index 3 stores the order of the traversal for e.g. if the order is 0, it means the next element can be navigated to using the innermost stride
  void traverse_next(std::vector<int>& traversal_info, int counter) const {
      update_base_index(traversal_info);
      traversal_info[3] = determine_order(counter);
      traversal_info[2] = traversal_info[traversal_info[3]]+strides_[traversal_info[3]];
  };
>>>>>>> e658bbf... Add files via upload
=======
// ******************************************************************************************
// Some traversal operations (works on const declarations without modifying tensor variables)
// ******************************************************************************************

//generate a traversal_info vector based on the tensor's shape for the traverse_next function to work
vector<int> generate_traversal_info() const {
    vector<int> traversal_info = {};
    for(size_t n=0; n<(shape_.size()+2); ++n) {
      traversal_info.push_back(0);
    }
    return traversal_info;
};

//this function checks whether the next index falls on a special multiplier of the outer shape
//so the algorithm knows when to jump over/back to a starting element of the outer shape
//for e.g. in [[1,4,7], [2,5,8], [3,6,9]], elements 1,2,3 are the starting elements of their respective rows
//this additional check only has 1 loop for 2d matrix
//but runtime performance might degrade to O(nlog(n)) for higher dimensional tensors
int determine_order(int counter) const {
    for (size_t n=0; n<(shape_multipliers_.size()-1); ++n) {
        if((counter%shape_multipliers_[n])==0){
            return ((shape_multipliers_.size()) - 1 - n);
        }
    }
    return 0;
};

//this function updates the base indexes with the current index after every single traversal step, can be generalized beyond 2d cases
void update_base_index(std::vector<int>& traversal_info) const {
    for (int n=0; n<(traversal_info[shape_.size()+1]+1); ++n) {
        traversal_info[n] = traversal_info[shape_.size()];
    }
};

//function to traverse a const strided tensor object
//it requires an additional vector, traversal_info {0,0,0,0 ...}, comprising (shape_.size()+2) elements of 0
//for e.g. 2d matrix:
//index 0 and 1 store the base row and column index respectively
//index 2 stores the current index of the traversal
//index 3 stores the order of the traversal for e.g. if the order is 0, it means the next element can be navigated to using the innermost stride
void traverse_next(std::vector<int>& traversal_info, int counter) const {
    update_base_index(traversal_info);
    traversal_info[shape_.size()+1] = determine_order(counter);
    traversal_info[shape_.size()] = traversal_info[traversal_info[shape_.size()+1]]+strides_[traversal_info[shape_.size()+1]];
};

// ******************************************************************************************
// traversal operations end
// ******************************************************************************************
>>>>>>> cb9153a... Add files via upload

 protected:
  //bool transpose_ = false;
  DataType data_type_ = kFloat32;
  std::shared_ptr<Device> device_ = nullptr;
  /// Note: block_ is allocated in lazy manner to avoid frequent malloc/free.
  /// If you want to get an allocated Block, use block() instead of block_.
  Block *block_ = nullptr;
  Shape shape_ = {};
  vector<int> strides_ = {};
  vector<int> shape_multipliers_ = {};

}; //end of tensor class

typedef Shape::iterator ShapeIter;
inline size_t Product(const Shape &shape, int start = 0, size_t len = 0) {
  if (len == 0) len = shape.size();
  if (len == 0)
    return 0;
  CHECK_LE(len, shape.size());
  size_t v = 1;
  for (unsigned int i = start; i < len; i++) v *= shape[i];
  return v;
}

inline void CheckDataTypeAndLang(const Tensor &in1, const Tensor &in2) {
  CHECK_EQ(in1.data_type(), in2.data_type());
  CHECK_EQ(in1.device()->lang(), in2.device()->lang());
}

template <typename FromType, typename ToType>
ToType TypeCast(const FromType &x) {
  // TODO(wangwei) cast fp16; prevent some casts, e.g., float to char
  return static_cast<ToType>(x);
}

Tensor Reshape(const Tensor &in, const Shape &s);
Tensor Reshape(const Tensor &in, Shape &&s);

// For tensors with sparse content, e.g., missing columns or rows.
// class SparseTensor : public Tensor {};

/// Copy 'num' elements of src to dst.
/// The first 'src_offset' ('dst_offset') elements will be skipped.
void CopyDataToFrom(Tensor *dst, const Tensor &src, const size_t num,
                    const size_t dst_offset = 0, const size_t src_offset = 0);

// =============Element-wise operations====================================
Tensor Abs(const Tensor &in);
Tensor Exp(const Tensor &in);
Tensor Log(const Tensor &in);
Tensor ReLU(const Tensor &in);
Tensor Sigmoid(const Tensor &in);
Tensor Sign(const Tensor &in);
Tensor Sqrt(const Tensor &in);
Tensor Square(const Tensor &in);
Tensor Tanh(const Tensor &in);

void Abs(const Tensor &in, Tensor *out);
void Exp(const Tensor &in, Tensor *out);
void Log(const Tensor &in, Tensor *out);
void ReLU(const Tensor &in, Tensor *out);
void Sigmoid(const Tensor &in, Tensor *out);
void Sign(const Tensor &in, Tensor *out);
void Sqrt(const Tensor &in, Tensor *out);
void Square(const Tensor &in, Tensor *out);
void Tanh(const Tensor &in, Tensor *out);

/// Element-wise opeartion, out[i]=in[i]^x
template <typename SType>
Tensor Pow(const Tensor &in, const SType x);
/// Element-wise opeartion, out[i]=in[i]^x
template <typename SType>
void Pow(const Tensor &in, const SType x, Tensor *out);
/// Element-wise opeartion, out[i]=baes[i]^exp[i]
Tensor Pow(const Tensor &base, const Tensor &exp);
/// Element-wise opeartion, out[i]=baes[i]^exp[i]
void Pow(const Tensor &base, const Tensor &exp, Tensor *out);

/// Element-wise operation, out[i]= (in[i] < x) ? 1.f : 0.f
template <typename SType>
Tensor operator<(const Tensor &in, const SType x);
template <typename SType>
void LT(const Tensor &in, const SType x, Tensor *out);

/// Element-wise operation, out[i]= (in1[i] < in2[i]) ? 1.f : 0.f
Tensor operator<(const Tensor &in1, const Tensor& in2);
void LT(const Tensor &in1, const Tensor& in2, Tensor *out);

/// Element-wise operation, out[i]= (in[i] <= x) ? 1.f : 0.f
template <typename SType>
Tensor operator<=(const Tensor &in, const SType x);
template <typename SType>
void LE(const Tensor &in, const SType x, Tensor *out);

/// Element-wise operation, out[i]= (in1[i] <= in2[i]) ? 1.f : 0.f
Tensor operator<=(const Tensor &in1, const Tensor& in2);
void LE(const Tensor &in1, const Tensor& in2, Tensor *out);

/// Element-wise operation, out[i]= (in[i] > x) ? 1.f : 0.f
template <typename SType>
Tensor operator>(const Tensor &in, const SType x);
template <typename SType>
void GT(const Tensor &in, const SType x, Tensor *out);

/// Element-wise operation, out[i]= (in1[i] > in2[i]) ? 1.f : 0.f
Tensor operator>(const Tensor &in1, const Tensor& in2);
void GT(const Tensor &in1, const Tensor& in2, Tensor *out);


/// Element-wise operation, out[i]= (in[i] >= x) ? 1.f : 0.f
template <typename SType>
Tensor operator>=(const Tensor &in, const SType x);
template <typename SType>
void GE(const Tensor &in, const SType x, Tensor *out);

/// Element-wise operation, out[i]= (in1[i] >= in2[i]) ? 1.f : 0.f
Tensor operator>=(const Tensor &in1, const Tensor& in2);
void GE(const Tensor &in1, const Tensor& in2, Tensor *out);


Tensor operator+(const Tensor &lhs, const Tensor &rhs);
void Add(const Tensor &lhs, const Tensor &rhs, Tensor *out);
Tensor operator-(const Tensor &lhs, const Tensor &rhs);
void Sub(const Tensor &lhs, const Tensor &rhs, Tensor *out);
Tensor operator*(const Tensor &lhs, const Tensor &rhs);
void EltwiseMult(const Tensor &lhs, const Tensor &rhs, Tensor *out);
Tensor operator/(const Tensor &lhs, const Tensor &rhs);
void Div(const Tensor &lhs, const Tensor &rhs, Tensor *out);

template <typename SType>
Tensor operator+(const Tensor &in, const SType x);
template <typename SType>
void Add(const Tensor &in, const SType x, Tensor *out);

template <typename SType>
Tensor operator-(const Tensor &in, const SType x);
template <typename SType>
void Sub(const Tensor &in, const SType x, Tensor *out);

template <typename SType>
Tensor operator*(const Tensor &in, const SType x);
template <typename SType>
void EltwiseMult(const Tensor &in, const SType x, Tensor *out);

/// For each element e of Tensor 'in', compute e / x
template <typename SType>
Tensor operator/(const Tensor &in, const SType x);
/// For each element e of Tensor 'in', compute e / x into out
template <typename SType>
void Div(const Tensor &in, const SType x, Tensor *out);

/// For each element e of Tensor 'in', compute x/e
template <typename SType>
Tensor Div(const SType x, const Tensor &in);
/// For each element e of Tensor 'in', compute x/e into 'out'
template <typename SType>
void Div(const SType x, const Tensor &in, Tensor *out);

template <typename SType = float>
SType Sum(const Tensor &in);
// ============Matrix (row/column) operations==================================
/// Average elements in the Tensor, currently only support vector and matrix.
/// if 'axis' is 0, average all rows into a single row
/// if 'axis' is 1, average all columns into a single column
/// TODO(wangwei) support arbitrary Tensor like numpy.average
Tensor Average(const Tensor &in, const int axis);

/// Add column 'v' with each column of matrix M
void AddColumn(const Tensor &v, Tensor *M);
/// For each column 'c' of matrix out, do c=alpha*v + beta*c
template <typename SType>
void AddColumn(const SType alpha, const SType beta, const Tensor &v,
               Tensor *out);
/// Add row 'v' with each row of matrix M; write results into 'out'
void AddRow(const Tensor &v, Tensor *out);
/// For each row 'r' of matrix out, do r=alpha*v + beta*r
template <typename SType>
void AddRow(const SType alpha, const SType beta, const Tensor &v, Tensor *M);
/// Divide column 'v' by each column of matrix M; write results into 'out'
void DivColumn(const Tensor &v, Tensor *M);
/// Divide row 'v' by each row of matrix M; write results into 'out'
void DivRow(const Tensor &v, Tensor *M);
/// Multiply column 'v' and each column of matrix M; write results into 'out'
void MultColumn(const Tensor &v, Tensor *M);
/// Multiply row 'v' with each row of matrix M; write results into 'out'
void MultRow(const Tensor &v, Tensor *M);
/// Do softmax for each row. 'in' could be a 1-d or 2-d Tensor.
Tensor SoftMax(const Tensor &in);
/// Do softmax for each row. 'in' could be a 1-d or 2-d Tensor.
void SoftMax(const Tensor &in, Tensor *out);
/// Sub column 'v' by each column of matrix M
void SubColumn(const Tensor &v, Tensor *M);
/// Sub row 'v' by each row of matrix M; write results into 'out'
void SubRow(const Tensor &v, Tensor *M);
/// Sum all columns of matrix M into a single column as 'out'
void SumColumns(const Tensor &M, Tensor *out);
/// Sum all rows of matrix M into a single row as 'out'
void SumRows(const Tensor &M, Tensor *out);

/// Sum elements in the Tensor, currently only support vector and matrix.
/// if 'axis' is 0, sum all rows into a single row
/// if 'axis' is 1, sum all columns into a single column
/// TODO(wangwei) support arbitrary Tensor like numpy.sum
Tensor Sum(const Tensor &in, const int axis);

// ================Random operations==========================================
/// For each element x set x = 1 if random() < p; otherwise x = 1.
template <typename SType>
void Bernoulli(const SType p, Tensor *out);
/// Fill in Tensor 't' following Gaussian distribution.
template <typename SType>
void Gaussian(const SType mean, const SType std, Tensor *out);
/// Fill in Tensor 't' following uniform distribution.
template <typename SType>
void Uniform(const SType low, const SType high, Tensor *out);

// ================Blas operations============================================
// TODO(wangwei) make amax/amin/asum a member function of tensor

/// out = alpha*in + out
template <typename SType>
void Axpy(SType alpha, const Tensor &in, Tensor *out);

/// Do matrix vector multipication or matrix matrix multiplication depdending
/// on the Tensor shape.  result = A * B
Tensor Mult(const Tensor &A, const Tensor &B);
/// Do matrix vector multipication or matrix matrix multiplication depdending
/// on the Tensor shape.  C = A * B
void Mult(const Tensor &A, const Tensor &B, Tensor *C);
/// Do matrix vector multipication or matrix matrix multiplication depdending
/// on the Tensor shape. out = alpha lhs * rhs + beta * out
template <typename SType>
void Mult(const SType alpha, const Tensor &A, const Tensor &B, const SType beta,
          Tensor *C);

// *****************
// Misc.
// ****************
/// Compute the cross entropy loss given the prediction probability 'p' and
/// the target (ground truth) labels 't'. 'p' could be either a 1-d vector for
/// a single instance or a 2-d matrix for a batch of instances. t[i]
/// could be the ground truth label index or a label weighted
/// array of the i-th instance. For example, if there are 3 candidate labels for
/// each instance, t[i] could be 2 or [0, 0, 1]. If one instance could have
/// multiple labels, then t[i] could be [1, 0, 1].
/// The loss is computed into p.
<<<<<<< HEAD
<<<<<<< HEAD

//void ComputeCrossEntropy(const Tensor &p, const Tensor &t, Tensor *loss);

/// Compute the dx, given prediction probability 'p' (p=softmax(x)) and
/// the target (ground truth) labels 't'. 'p' and 't' are either 1-d vector
/// or 2-d matrix. 'grad' has the same shape as 'p'. dx is computed into p.

=======
=======

<<<<<<< HEAD
>>>>>>> cb9153a... Add files via upload
//void ComputeCrossEntropy(const Tensor &p, const Tensor &t, Tensor *loss);
=======
void ComputeCrossEntropy(const Tensor &p, const Tensor &t, Tensor *loss);
>>>>>>> 13227e7... re-enabled the entropy functions for testing

/// Compute the dx, given prediction probability 'p' (p=softmax(x)) and
/// the target (ground truth) labels 't'. 'p' and 't' are either 1-d vector
/// or 2-d matrix. 'grad' has the same shape as 'p'. dx is computed into p.
<<<<<<< HEAD
>>>>>>> 2d95dba... Add files via upload
=======

<<<<<<< HEAD
>>>>>>> cb9153a... Add files via upload
//void SoftmaxCrossEntropyBwd(const Tensor &t, Tensor *p);
=======
void SoftmaxCrossEntropyBwd(const Tensor &t, Tensor *p);
>>>>>>> 13227e7... re-enabled the entropy functions for testing


/// Return a tensor consisting of rows ([start, end)) from 'in'. It copies the
/// values from 'in'. 'in' ia a 2D Tensor.
Tensor CopyRows(const Tensor &in, const size_t start, const size_t end);
/// Alias of CopyRows
Tensor SliceRows(const Tensor &in, const size_t start, const size_t end);
/// Slice the input tensor along the give axis to generate a new tensor
Tensor SliceOn(const Tensor &in, const size_t start, const size_t end, int axis);
/// Return a tensor consisting of columns ([start, end)) from 'in'. It copies
/// the values from 'in'. 'in' is a  2D Tensor.
Tensor CopyColumns(const Tensor &in, const size_t start, const size_t end);
/// Alias of CopyColumns
Tensor SliceColumns(const Tensor &in, const size_t start, const size_t end);
/// Return a tensor which is vertically stacked from tensors in 'in'. Each
/// tensor in 'in' is a 2D tensor. Values are copied, no memory sharing.
Tensor ConcatenateRows(const vector<Tensor> &in);
/// Return a tensor concatenated of the input tensors along the give axis.
Tensor ConcatOn(const vector<Tensor> &in, int axis);
/// Alias name for function ConcatenateRows
Tensor ConcatRows(const vector<Tensor> &in);
/// Return a tensor which is horizontally stacked from tensors in 'in'. Each
/// tensor in 'in' is a 2D tensor. Values are copied, no memory sharing.
Tensor ConcatenateColumns(const vector<Tensor> &in);
/// Alias name for function ConcatenateColumns
Tensor ConcatColumns(const vector<Tensor> &in);
}  // namespace singa

#endif  // SINGA_CORE_TENSOR_H_
