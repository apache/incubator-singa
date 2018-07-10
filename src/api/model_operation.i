%module model_operation

%include "config.i"
%include "std_vector.i"
%include "std_string.i"
%{
#include "../src/model/operation/convolution.h"
#include "../src/model/operation/pooling.h"
%}
namespace singa {

class ConvHandle {
 public:
  ConvHandle(const Tensor &input, const std::vector<size_t>& kernel_size,
             const std::vector<size_t>& stride, const std::vector<size_t>& padding,
             const size_t in_channels, const size_t out_channels,
             const bool bias);
  bool bias_term;
  size_t batchsize;
};

Tensor CpuConvForward(const Tensor &x, Tensor &W,  Tensor &b, const ConvHandle &ch);

Tensor CpuConvBackwardx(const Tensor &dy, Tensor &W, const Tensor &x, const ConvHandle &ch);

Tensor CpuConvBackwardW(const Tensor &dy, const Tensor &x, const Tensor &W, const ConvHandle &ch);

Tensor CpuConvBackwardb(const Tensor &dy, const Tensor &b, const ConvHandle &ch);


class PoolingHandle {
 public:
  PoolingHandle(const Tensor &input, const std::vector<size_t>& kernel_size,
                const std::vector<size_t>& stride, const std::vector<size_t>& padding,
                const bool ceil_mode = false, const std::string pooling_method = "MAX");

  size_t batchsize;

  size_t pooled_height;
  size_t pooled_width;
};

#if USE_CUDNN
class CudnnConvHandle: public ConvHandle {
 public:
  CudnnConvHandle(const Tensor &input, const std::vector<size_t>& kernel_size,
                  const std::vector<size_t>& stride, const std::vector<size_t>& padding,
                  const size_t in_channels, const size_t out_channels,
                  const bool bias, const size_t workspace_byte_limit = 1024 * 1024 * 1024,
                  const std::string& prefer = "fastest");
  bool bias_term;
  size_t batchsize;
};

Tensor GpuConvForward(const Tensor &x, const Tensor &W, const Tensor &b, const CudnnConvHandle &cch);

Tensor GpuConvBackwardx(const Tensor &dy, const Tensor &W, const Tensor &x, const CudnnConvHandle &cch);

Tensor GpuConvBackwardW(const Tensor &dy, const Tensor &x, const Tensor &W, const CudnnConvHandle &cch);

Tensor GpuConvBackwardb(const Tensor &dy, const Tensor &b, const CudnnConvHandle &cch);


class CudnnPoolingHandle : public PoolingHandle {
 public:
  CudnnPoolingHandle(const Tensor &input, const std::vector<size_t>& kernel_size,
                     const std::vector<size_t>& stride, const std::vector<size_t>& padding,
                     const bool ceil_mode = false, const std::string pooling_method = "MAX",
                     const bool NaN_prop = false);

  size_t batchsize;
  
  size_t pooled_height;
  size_t pooled_width;
};

Tensor GpuPoolingForward(const Tensor &x, const CudnnPoolingHandle &cph);

Tensor GpuPoolingBackward(const Tensor &dy, const Tensor& x, const Tensor& y,
                          const CudnnPoolingHandle &cph);

#endif  // USE_CUDNN

}  //namespace singa
