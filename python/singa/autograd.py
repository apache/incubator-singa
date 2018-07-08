#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from __future__ import division

from collections import Counter, deque
import numpy as np
import math

from .tensor import Tensor
from . import layer
from singa.proto import model_pb2
from . import singa_wrap as singa


CTensor = singa.Tensor
training = False


class Operation(object):
    '''
    An operation includes the forward and backward function of
    tensor calculation.

    Steps to add a specific operation Xxxx:
    1. create a subclass of Operation, name it as Xxxx
    2. override the forward() and backward(); The arguments of forward()
       and backward() should only include CTensor;
    '''

    def __call__(self, *xs):
        return self._do_forward(*xs)

    def _do_forward(self, *xs):
        '''
        Do not call this function from user code. It is called by __call__().

        Args:
            xs, Tensor instance(s)

        Returns:
            Tensor instance(s)
        '''
        # TODO add the pre hook
        assert all([isinstance(x, Tensor) for x in xs]), \
            'xs should include only Tensor instances'

        # need to do backward if any of its input arg needs gradient
        self.requires_grad = any([x.requires_grad for x in xs])

        self.src = []
        for x in xs:
            if x.stores_grad:
                # store the tensor whose gradient needs be returned in
                # backward(), e.g. if x is parameter
                self.src.append((x.creator, id(x), x, x.stores_grad))
            else:
                # for intermediate tensors, they will be released soon;
                # no need to store them --> use None
                self.src.append((x.creator, id(x), None, x.stores_grad))

        # get the CTensor (data) if the input arg is Tensor
        xs = tuple(x.data for x in xs)
        ys = self.forward(*xs)
        if not isinstance(ys, tuple):
            ys = (ys,)
        # create Tensor based on CTensor(data);
        # assume outputs are all Tensor instances
        ys = tuple(Tensor(device=y.device(),
                          data=y,
                          requires_grad=self.requires_grad,
                          creator=self) for y in ys)
        # map from python id to output index
        self.y_id2idx = {id(y): i for i, y in enumerate(ys)}
        # TODO add the post hook
        return ys

    def _do_backward(self, *dys):
        dxs = self.backward(*dys)
        if not isinstance(dxs, tuple):
            dxs = (dxs,)
        return dxs

    def forward(self, *xs):
        '''Forward propagation.

        Args:
            xs: input args consisting of only CTensors.

        Returns:
            CTensor instance(s)
        '''
        raise NotImplementedError

    def backward(self, *dys):
        ''' Backward propagation.

        Args:
            dys: input args consisting of only CTensors.

        Returns:
            CTensor instance(s)
        '''
        raise NotImplementedError

    def get_params(self):
        return []


class Dummy(Operation):
    '''Dummy operation whice serves as a placehoder for autograd

    Args:
        name(string): set it for debug
    '''

    def __init__(self, tensor, name=None):
        self.name = name
        self.src = []
        self.y_id2idx = {id(tensor): 0}
        self.requires_grad = False


class ReLU(Operation):

    def forward(self, x):
        '''
        Args:
            x(CTensor): input tensor

        Returns:
            a new CTensor whose element y = x if x >= 0; otherwise 0;
        '''
        if training:
            self.input = x
        return singa.ReLU(x)

    def backward(self, dy):
        '''
        Args:
            dy(CTensor): dL / dy

        Returns:
            dx(CTensor): dL / dx = dy if x >= 0; otherwise 0;
        '''
        dx = singa.GTFloat(self.input, 0.0)
        return singa.__mul__(dy, dx)


def relu(x):
    return ReLU()(x)[0]


class Matmul(Operation):
    '''For matrix multiplication'''

    def forward(self, x, w):
        '''Do forward propgation.

        Store the x(or w) if w(or x) requires gradient.

        Args:
            x (CTensor): matrix
            w (CTensor): matrix

        Returns:
            a CTensor for the result
        '''
        if training:
            self.input = (x, w)
        return singa.Mult(x, w)

    def backward(self, dy):
        '''
        Args:
            dy (CTensor): data for the dL / dy, L is the loss

        Returns:
            a tuple for (dx, dw)
        '''
        return singa.Mult(dy, self.input[1].T()), \
            singa.Mult(self.input[0].T(), dy)


def matmul(x, w):
    return Matmul()(x, w)[0]


class AddBias(Operation):
    '''
    Add Bias to each row / column of the Tensor, depending on the axis arg.
    '''

    def __init__(self, axis=0):
        '''
        To indicate the calculation axis, 0 for row, 1 for column.

        Args:
            axis: 0 or 1, default is 0.
        '''
        self.axis = axis

    def forward(self, x, b):
        '''
        Args:
            x: matrix.
            b: bias to be added.

        Return:
            the result Tensor
        '''
        if self.axis == 0:
            singa.AddRow(b, x)
        elif self.axis == 1:
            singa.AddColumn(b, x)
        return x

    def backward(self, dy):
        '''
        Args:
            dy (CTensor): data for the dL / dy, L is the loss.

        Return:
            a tuple for (db, dx), db is data for dL / db, dx is data
            for dL / dx.
        '''
        if self.axis == 0:
            return dy, singa.Sum(dy, 0)
        elif self.axis == 1:
            return dy, singa.Sum(dy, 0)


def add_bias(x, b, axis=0):
    return AddBias(axis)(x, b)[0]


class SoftMax(Operation):
    '''
    Apply SoftMax for each row of the Tensor or each column of the Tensor
    according to the parameter axis.
    '''

    def __init__(self, axis=0):
        self.axis = axis

    def forward(self, x):
        '''
        Args:
            x(data): the input 1d or 2d tensor

        Returns:
            the result Tensor
        '''
        if self.axis == 1:
            x = x.T()
        self.output = singa.SoftMax(x)
        if self.axis == 0:
            return self.output
        elif self.axis == 1:
            return self.output.T()

    def backward(self, dy):
        '''
        Args:
            dy (CTensor): data for the dL / dy, L is the loss

        Returns:
            dx (Ctensor): data for the dL / dx, L is the loss,
            x is the input of current Opertion
        '''
        # calculations are made on numpy array
        if self.axis == 1:
            dy = dy.T()
        grad = ctensor2numpy(dy)
        output = ctensor2numpy(self.output)
        out_1 = np.einsum('ki,ki->ki', grad, output)
        medium_out = np.einsum('ki,kj->kij', output, output)
        out_2 = np.einsum('kij,kj->ki', medium_out, grad)
        out = out_1 - out_2
        dx = CTensor(out_1.shape)
        dx.CopyFloatDataFromHostPtr(out.flatten())
        if self.axis == 0:
            return dx
        elif self.axis == 1:
            return dx.T()


def soft_max(x, axis=0):
    return SoftMax(axis)(x)[0]


class NLL(Operation):
    '''
    Calculte negative log likelihood loss for a batch of training data.

    '''

    def forward(self, x, t):
        '''
        Args:
            x (CTensor): 1d or 2d tensor, the prediction data(output)
                         of current network.
            t (CTensor): 1d or 2d tensor, the target data for training.

        Returns:
            loss (CTensor): scalar.
        '''
        loss = CTensor((1,))
        loss_data = -singa.SumAsFloat(singa.__mul__(t, singa.Log(x)))
        loss.SetFloatValue(loss_data / x.shape()[0])
        self.x = x
        self.t = t
        self.input = (x, t)
        return loss

    def backward(self, dy=1.0):
        '''
        Args:
            dy (float or CTensor): scalar, accumulate gradient from outside
                                of current network, usually equal to 1.0

        Returns:
            dx (CTensor): data for the dL /dx, L is the loss, x is the output
                          of current network. note that this is true for
                          dy = 1.0
        '''
        dx = singa.__div__(self.t, self.x)
        dx *= float(-1 / self.x.shape()[0])
        if isinstance(dy, float):
            # dtype of dy: float
            dx *= dy
            return dx, None
        elif isinstance(dy, CTensor):
            pass  # TODO, broadcast elementwise multiply seems not support


def nll(y, t):
    return NLL()(y, t)[0]


class SoftMaxCrossEntropy(Operation):

    def forward(self, x, t):
        self.p = singa.SoftMax(x)
        self.t = t
        loss = CTensor((1,), self.p.device())
        ret = singa.CrossEntropyFwd(self.p, t)
        loss.SetFloatValue(singa.SumAsFloat(ret) / x.shape()[0])
        return loss

    def backward(self, dy=1.0):
        return singa.SoftmaxCrossEntropyBwd(self.p, self.t), None


def softmax_cross_entropy(x, t):
    # x is the logits and t is the ground truth; both are 2D.
    return SoftMaxCrossEntropy()(x, t)[0]


def ctensor2numpy(x):
    '''
    To be used in SoftMax Operation.
    Convert a singa_tensor to numpy_tensor.
    '''
    np_array = x.GetFloatValue(int(x.Size()))
    return np_array.reshape(x.shape())


class MaxPool2d(Operation):

    def __init__(self, kernel_size=3, stride=1, padding=0, dilation=1,
                 return_indices=False, ceil_mode=False, **kwargs):

        inner_params = {'name': 'MaxPool2d',
                        'border_mode': 'same',
                        'data_format': 'NCHW',
                        'input_sample_shape': None
                        }

        for kwarg in kwargs:
            if kwarg not in inner_params:
                raise TypeError('Keyword argument not understood:', kwarg)
            else:
                inner_params[kwarg] = kwargs[kwarg]

        if padding == 0:
            pad = None
        else:
            pad = padding

        if dilation != 1 or return_indices or ceil_mode:
            raise ValueError('Not implemented yet')

        self.PyLayer = layer.Pooling2D(inner_params['name'],
                                       model_pb2.PoolingConf.MAX,
                                       kernel_size, stride, inner_params[
                                           'border_mode'],
                                       pad, inner_params['data_format'],
                                       inner_params['input_sample_shape'])

    def __call__(self, x):
        if training:
            self.flag = model_pb2.kTrain
        else:
            self.flag = model_pb2.kEval

        if not self.PyLayer.has_setup:
            self.PyLayer.setup(x.shape[1:])

        return self._do_forward(x)

    def forward(self, *xs):
        return self.PyLayer.layer.Forward(self.flag, xs[0])

    def backward(self, dy):
        return self.PyLayer.layer.Backward(0, dy)[0]


def max_pool_2d(x, kernel_size=3, stride=1, padding=0, dilation=1,
                return_indices=False, ceil_mode=False, **kwargs):
    return MaxPool2d(kernel_size, stride, padding, dilation, return_indices,
                     ceil_mode, **kwargs)(x)[0]


class Flatten(Operation):

    def __init__(self):
        self.PyLayer = layer.Flatten('flatten', 1)

    def __call__(self, x):
        if training:
            self.flag = model_pb2.kTrain
        else:
            self.flag = model_pb2.kEval
        if not self.PyLayer.has_setup:
            self.PyLayer.setup(x.shape[1:])
        return self._do_forward(x)

    def forward(self, *xs):
        return self.PyLayer.layer.Forward(self.flag, xs[0])

    def backward(self, dy):
        return self.PyLayer.layer.Backward(0, dy)[0]


def flatten(x):
    return Flatten()(x)[0]


class _Conv2D(Operation):

    def __init__(self, handle):
        self.handle = handle

    def forward(self, x, W, b):
        #assert x.nDim() == 4, 'The dimensions of input should be 4D.'
        #assert x.shape()[1] == self.in_channels, 'in_channels dismatched.'
        #assert (xs[0].shape()[2]+2*self.padding[0]-self.kernel_size[0])%self.stride[0] == 0, 'invalid padding.'
        #assert (xs[0].shape()[3]+2*self.padding[1]-self.kernel_size[1])%self.stride[1] == 0, 'invalid padding'
        #assert 0 == 0, 'invalid padding'

        if training:
            if self.handle.bias_term:
                self.inputs = (x, W, b)
            else:
                self.inputs = (x, W)

        if self.handle.device_id == -1:
            return singa.CpuConvForward(x, W, b, self.handle)

        else:
            return singa.GpuConvForward(x, W, b, self.handle)

    def backward(self, dy):
        assert training is True and hasattr(
            self, 'inputs'), 'Please set training as True before do BP. '

        if dy.device().id() != self.handle.device_id:
            dy.ToDevice(self.inputs[0].device())

        if self.handle.device_id == -1:
            dx = singa.CpuConvBackwardx(
                dy, self.inputs[1], self.inputs[0], self.handle)
            dW = singa.CpuConvBackwardW(
                dy, self.inputs[0], self.inputs[1], self.handle)
            if self.handle.bias_term:
                db = singa.CpuConvBackwardb(dy, self.inputs[2], self.handle)
                return dx, dW, db
            else:
                return dx, dW, None
        else:
            dx = singa.GpuConvBackwardx(
                dy, self.inputs[1], self.inputs[0], self.handle)
            dW = singa.GpuConvBackwardW(
                dy, self.inputs[0], self.inputs[1], self.handle)
            if self.handle.bias_term:
                db = singa.GpuConvBackwardb(dy, self.inputs[2], self.handle)
                return dx, dW, db
            else:
                return dx, dW, None


def conv2d(x, W, b, handle):
    return _Conv2D(handle)(x, W, b)[0]


def infer_dependency(op):
    '''
    Infer the dependency of all operations with the
    given op as the last operation.

    Operation A is depending on B is A uses the output(s) of B.

    Args:
        op: an Operation instance, e.g. the loss operation.

    Return:
        a Counter instance with the operation as the key,
        and the number of operations that are depending on it as the value
    '''
    # dependency = {}
    dependency_count = Counter()
    queue = deque([op])
    while len(queue) > 0:
        cur_op = queue.pop()
        for src_op, _, _, _ in cur_op.src:
            if src_op not in dependency_count and \
                    (not isinstance(src_op, Dummy)):
                # dependency[src_op] = [Counter() for _ in src_op.y_id2idx]
                dependency_count[src_op] = 0
                queue.append(src_op)
            # y_idx = src_op.y_id2idx[x_id]
            # dependency[src_op][y_idx][cur_op] += 1
            dependency_count[src_op] += 1
    return dependency_count


def gradients(y, dy=None):
    grads = {}  # mapping: x->dx if x.stores_grad
    for p, dp in backward(y, dy):
        gradients[p] = dp
    return grads


def backward(y, dy=None):
    '''
    Run the backward propagation starting at y.

    Args:
        y: a Tensor instance, usually the loss
        dy: a number or a Tensor instance, for the gradient of the
            objective/loss w.r.t y, usually 1.0

    Return:
        a dictionary storing the gradient tensors of all tensors
        whose stores_grad is true (e.g. parameter tensors)
    '''
    dependency = infer_dependency(y.creator)
    assert y.size() == 1, 'y must be a Tensor with a single value;'\
        'size of y is % d' % y.size()

    # by default the dy is a tensor with 1.0 for each sample;
    if dy is None:
        dy = float(1.0)
    elif isinstance(dy, Tensor):
        dy = dy.data
    else:
        dy = float(dy)

    # ready is a queue of (operation, dy list)
    ready = deque([(y.creator, (dy,))])
    not_ready = {}  # mapping: op->[dy]

    if y.stores_grad:
        gradients[y] = dy

    while len(ready) > 0:
        op, dys = ready.pop()
        if not op.requires_grad or isinstance(op, Dummy):
            continue
        # if not isinstance(op, tensor.Dummy):
        dxs = op._do_backward(*dys)
        # TODO src and dx must match
        assert len(op.src) == len(dxs), \
            'the number of src ops (=%d) and dx (=%d) not match' \
            % (len(op.src), len(dxs))
        for (src_op, x_id, y, y_stores_grad), dx in zip(op.src, dxs):
            # prefix x is w.r.t op; prefix y is w.r.t src_op.
            # x_id is the python id of one input arg of src_op, denoted as x.
            # y_idx (below) is the index of x among the outputs of src_op.
            # not_ready[src_op][y_idx] records the intermediate gradient
            # of the y_idx'th output of src_op. 'intermediate gradient'
            # indicates that if this output is used in multiple children
            # operations, then we have to add the graident (dx) from all these
            # children operations. When src_op is ready, it means that
            # the gradient of all its outputs are available, i.e. all children
            # operations have been backwarded.
            # y is None if y.stores_grad is false; otherwise it is a Tensor
            y_idx = src_op.y_id2idx[x_id]
            if src_op not in not_ready:
                # src_op may have mulitple outputs
                not_ready[src_op] = [None for _ in src_op.y_id2idx]
                not_ready[src_op][y_idx] = dx
            else:
                dxs = not_ready[src_op]
                if dxs[y_idx] is None:
                    dxs[y_idx] = dx
                else:
                    # add the gradient from another children operation that
                    # uses y_idx'th output of src_op as input arg
                    dxs[y_idx] += dx
            if y_stores_grad:
                # store the gradient for final return, e.g. if x is parameter
                g = not_ready[src_op][y_idx]
                tg = Tensor(device=g.device(), data=g)
                yield (y, tg)
            dependency[src_op] -= 1
            if src_op.requires_grad is True:
                if dependency[src_op] == 0:
                    if not isinstance(src_op, Dummy):
                        ready.append((src_op, not_ready[src_op]))
                    del not_ready[src_op]


class Layer(object):

    def __init__(self):
        pass

    def device_check(self, *inputs):
        x_device = inputs[0].device
        for var in inputs:
            if var.device.id() != x_device:
                var.to_device(x_device)


class Linear(Layer):

    def __init__(self, in_features, out_features, bias=True):
        #self.in_features = in_features
        #self.out_features = out_features
        w_shape = (in_features, out_features)
        b_shape = (1, out_features)
        self.bias = bias

        self.W = Tensor(shape=w_shape,
                        requires_grad=True, stores_grad=True)
        std = math.sqrt(2.0 / (in_features + out_features))
        self.W.gaussian(0.0, std)

        if self.bias:
            self.b = Tensor(shape=b_shape,
                            requires_grad=True, stores_grad=True)
            self.b.set_value(0.0)

    def __call__(self, x):
        if self.bias:
            self.device_check(x, self.W, self.b)
        else:
            self.device_check(x, self.W)
        y = matmul(x, self.W)
        if self.bias:
            y = add_bias(y, self.b, axis=0)
        return y


class Conv2D(Layer):

    def __init__(self, in_channels, out_channels, kernel_size, stride=1,
                 padding=0, dilation=1, groups=1, bias=True, **kwargs):

        self.in_channels = in_channels
        self.out_channels = out_channels

        if isinstance(kernel_size, int):
            self.kernel_size = (kernel_size, kernel_size)
        elif isinstance(kernel_size, tuple):
            self.kernel_size = kernel_size
        else:
            raise TypeError('Wrong kernel_size type.')

        if isinstance(stride, int):
            self.stride = (stride, stride)
        elif isinstance(stride, tuple):
            self.stride = stride
        else:
            raise TypeError('Wrong stride type.')

        if isinstance(padding, int):
            self.padding = (padding, padding)
        elif isinstance(padding, tuple):
            self.padding = padding
        else:
            raise TypeError('Wrong padding type.')

        if dilation != 1 or groups != 1:
            raise ValueError('Not implemented yet')

        self.bias = bias

        self.inner_params = {'cudnn_prefer': 'fastest',
                             'workspace_MB_limit': 1024}
        # TODO valid value of inner_params check

        for kwarg in kwargs:
            if kwarg not in self.inner_params:
                raise TypeError('Keyword argument not understood:', kwarg)
            else:
                self.inner_params[kwarg] = kwargs[kwarg]

        w_shape = (self.out_channels, self.in_channels,
                   self.kernel_size[0], self.kernel_size[1])
        self.W = Tensor(shape=w_shape, requires_grad=True, stores_grad=True)
        std = math.sqrt(
            2.0 / (self.in_channels * self.kernel_size[0] * self.kernel_size[1] + self.out_channels))
        self.W.gaussian(0.0, std)

        if self.bias:
            b_shape = (self.out_channels,)
            self.b = Tensor(shape=b_shape, requires_grad=True,
                            stores_grad=True)
            self.b.set_value(0.0)
        else:
            # to keep consistency when to do forward.
            self.b = Tensor(data=CTensor(
                []), requires_grad=False, stores_grad=False)

    def __call__(self, x):
        assert x.shape[1] == self.in_channels, 'in_channels dismatched'
        assert (x.shape[2] + 2 * self.padding[0] - self.kernel_size[0]
                ) % self.stride[0] == 0, 'invalid padding or strides.'
        assert (x.shape[3] + 2 * self.padding[1] - self.kernel_size[1]
                ) % self.stride[1] == 0, 'invalid padding or stride.'

        self.device_check(x, self.W, self.b)

        if x.device.id() == -1:
            if not hasattr(self, 'handle'):
                self.handle = singa.ConvHandle(x.data, self.kernel_size, self.stride,
                                               self.padding, self.in_channels, self.out_channels, self.bias)
            elif x.shape[0] != self.handle.batchsize:
                self.handle = singa.ConvHandle(x.data, self.kernel_size, self.stride,
                                               self.padding, self.in_channels, self.out_channels, self.bias)
        else:
            if not hasattr(self, 'handle'):
                self.handle = singa.CudnnConvHandle(x.data, self.kernel_size, self.stride,
                                                    self.padding, self.in_channels, self.out_channels, self.bias)
            elif x.shape[0] != self.handle.batchsize:
                self.handle = singa.CudnnConvHandle(x.data, self.kernel_size, self.stride,
                                                    self.padding, self.in_channels, self.out_channels, self.bias)
        self.handle.device_id = x.device.id()

        y = conv2d(x, self.W, self.b, self.handle)
        return y
