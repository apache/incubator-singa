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

import numpy as np
import onnx.utils
import onnx
from onnx.backend.base import Backend, BackendRep
from onnx import (checker, helper, numpy_helper, GraphProto, NodeProto,
                  TensorProto, OperatorSetIdProto, optimizer)
import warnings

from . import singa_wrap as singa
from . import autograd
from . import tensor
from singa import utils

import collections
deque = collections.deque


class SingaFrontend(object):
    """
    This class provides mthods to convert model from singa to onnx. 
    """

    # This number indicates the target onnx operator set version
    _target_opset_version = 11

    # beceuase singa's operators are different from onnx.
    # we define a dict for the name projection
    # "singa op name": "onnx op name"
    _rename_operators = {
        '_Conv2d': 'Conv',
        'ReLU': 'Relu',
        'Dummy': 'Constant',
        'MaxPool2d': 'MaxPool',
        'AvgPool2d': 'AveragePool',
        'SoftMax': 'Softmax',
        'Sigmoid': 'Sigmoid',
        'Add': 'Add',
        'Matmul': 'MatMul',
        '_BatchNorm2d': 'BatchNormalization',
        'Concat': 'Concat',
        'Flatten': 'Flatten',
        'AddBias': 'Add',
        'Gemm': 'Gemm',
        'Reshape': 'Reshape',
        'Sum': 'Sum',
        'cos': 'Cos',
        'cosh': 'Cosh',
        'sin': 'Sin',
        'sinh': 'Sinh',
        'tan': 'Tan',
        'tanh': 'Tanh',
        'acos': 'Acos',
        'acosh': 'Acosh',
        'asin': 'Asin',
        'asinh': 'Asinh',
        'atan': 'Atan',
        'atanh': 'Atanh',
        'SeLU': 'Selu',
        'Elu': 'Elu',
        'Equal': 'Equal',
        'Less': 'Less',
        'Sign': 'Sign',
        'Div': 'Div',
        'Sub': 'Sub',
        'Sqrt': 'Sqrt',
        'Log': 'Log',
        'Greater': 'Greater',
        'HardSigmoid': 'HardSigmoid',
        'Identity': 'Identity',
        'SoftPlus': 'Softplus',
        'SoftSign': 'Softsign',
        'Mean': 'Mean',
        'Pow': 'Pow',
        'Clip': 'Clip',
        'PRelu': 'PRelu',
        'Mul': 'Mul',
        'Transpose': 'Transpose',
        'Max': 'Max',
        'Min': 'Min',
        'Shape': 'Shape',
        'And': 'And',
        'Or': 'Or',
        'Xor': 'Xor',
        'Not': 'Not',
        'Negative': 'Neg',
        'Reciprocal': 'Reciprocal',
        'ConstantOfShape': 'ConstantOfShape',
        'Dropout': 'Dropout',
        'ReduceSum': 'ReduceSum',
        'ReduceMean': 'ReduceMean',
    }

    # this dict indicates the operators that need extra handle
    # each indicates a function name
    _special_operators = {
        '_Conv2d': '_create_conv_pool',
        '_Pooling2d': '_create_conv_pool',
        'Dummy': '_create_dummy',
        '_BatchNorm2d': '_create_batchnorm',
        'Concat': '_create_concat',
        'Flatten': '_create_flatten',
        'Gemm': '_create_gemm',
        'Reshape': '_create_reshape',
        'SoftMax': '_create_softmax',
        'SeLU': '_create_selu',
        'Elu': '_create_elu',
        'HardSigmoid': '_create_hardsigmoid',
        'Clip': '_create_clip',
        'Transpose': '_create_transpose',
        'ConstantOfShape': '_create_constantOfShape',
        'Dropout': '_create_dropout',
        'ReduceSum': '_create_reduceOp',
        'ReduceMean': '_create_reduceOp',
    }

    # operators with bool output
    _bool_operators = {
        'Equal': TensorProto.BOOL,
        'Greater': TensorProto.BOOL,
        'Less': TensorProto.BOOL,
        'And': TensorProto.BOOL,
        'Not': TensorProto.BOOL,
        'Or': TensorProto.BOOL,
        'Xor': TensorProto.BOOL,
        'Shape': TensorProto.INT64,
    }

    # some ops(such as batchnorm) has inputs we cannot handle directly,
    # so we record these items firstly so that we can handle then
    # at other place.
    _unhandled_operators = {}

    @classmethod
    def _create_reduceOp(cls, op, op_t):
        """
        get a onnx node from singa ReduceSum, ReduceMean, ReduceMax, ReduceMin, etc.
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('axes', list(op.axes)),
            helper.make_attribute('keepdims', op.keepdims),
        ])
        return node

    @classmethod
    def _create_dropout(cls, op, op_t):
        """
        get a onnx node from singa Dropout operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('ratio', op.ratio),
        ])
        return node

    @classmethod
    def _create_constantOfShape(cls, op, op_t):
        """
        get a onnx node from singa ConstantOfShape operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)
        tensor_type = onnx.TensorProto.FLOAT if isinstance(
            op.value, float) else onnx.TensorProto.INT32
        tensor_value = onnx.helper.make_tensor("value", tensor_type, [1],
                                               [op.value])
        node.attribute.extend([
            helper.make_attribute('value', tensor_value),
        ])
        return node

    @classmethod
    def _create_transpose(cls, op, op_t):
        """
        get a onnx node from singa Transpose operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('perm', op.perm),
        ])
        return node

    @classmethod
    def _create_clip(cls, op, op_t):
        """
        get a onnx node from singa clip operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """

        nodes = []
        clip_node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        # firstly we add the max and min
        for tmp_name in ['min', 'max']:
            node_name = op.name + ":" + tmp_name
            # moidfy the input of clip
            clip_node.input.append(node_name)

            # node = NodeProto()
            # node.name = node_name
            # node.op_type = cls._rename_operators.get("Dummy", "Dummy")
            # node.output.extend([node_name])

            # node.attribute.extend([helper.make_attribute(
            #     'value', helper.make_tensor(
            #         name=node_name,
            #         data_type=TensorProto.FLOAT,
            #         dims=[1],
            #         vals=[getattr(op,tmp_name)],
            #     )
            # )])
            # nodes.append(node)

        # then we add the clip op itself
        nodes.append(clip_node)

        return nodes

    @classmethod
    def _create_hardsigmoid(cls, op, op_t):
        """
        get a onnx node from singa HardSigmoid operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('alpha', op.alpha),
            helper.make_attribute('beta', op.gamma),
        ])
        return node

    @classmethod
    def _create_elu(cls, op, op_t):
        """
        get a onnx node from singa elu operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('alpha', op.alpha),
        ])
        return node

    @classmethod
    def _create_selu(cls, op, op_t):
        """
        get a onnx node from singa SeLU operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('alpha', op.alpha),
            helper.make_attribute('gamma', op.gamma),
        ])
        return node

    @classmethod
    def _create_reshape(cls, op, op_t):
        """
        get a onnx node from singa Concat operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        # make the shape node
        # because the reshape in singa does not provide its shape as input tensor
        shape_node_name = op.name + ":shape"
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)
        node.input.extend([shape_node_name])
        return node

    @classmethod
    def _create_concat(cls, op, op_t):
        """
        get a onnx node from singa Concat operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('axis', op.axis),
        ])
        return node

    @classmethod
    def _create_softmax(cls, op, op_t):
        """
        get a onnx node from singa Concat operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('axis', op.axis),
        ])
        return node

    @classmethod
    def _create_flatten(cls, op, op_t):
        """
        get a onnx node from singa flatten operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('axis', op.start_axis),
        ])
        return node

    @classmethod
    def _create_gemm(cls, op, op_t):
        """
        get a onnx node from singa gemm operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        node.attribute.extend([
            helper.make_attribute('alpha', float(op.alpha)),
            helper.make_attribute('beta', float(op.beta)),
            helper.make_attribute('transA', op.transA),
            helper.make_attribute('transB', op.transB),
        ])

        return node

    @classmethod
    def _create_batchnorm(cls, op, op_t):
        """
        get a onnx node from singa _BatchNorm2d operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        # first, we init batchnorm node
        epsilon = 1e-5  # the epsilon value used in singa
        bn_node = cls._common_singa_tensor_to_onnx_node(op, op_t)
        bn_node.attribute.extend([
            helper.make_attribute('momentum', op.handle.factor),
            helper.make_attribute('epsilon', epsilon),
        ])
        # then we add nodes of scal, bias, mean, var
        nodes = []
        running_values = {"mean": op.running_mean, "var": op.running_var}
        for tmp_name, running_value in running_values.items():
            node_name = op.name + ":" + tmp_name
            bn_node.input.append(node_name)

        nodes.append(bn_node)
        return nodes

    @classmethod
    def _create_conv_pool(cls, op, op_t):
        """
        get a onnx node from singa _Conv2d and _Pooling2d operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)

        k = [op.handle.kernel_h, op.handle.kernel_w]
        s = [op.handle.stride_h, op.handle.stride_w]
        p = [
            op.handle.pad_h,
            op.handle.pad_w,
            op.handle.pad_w,
            op.handle.pad_h,
        ]

        node.attribute.extend([
            helper.make_attribute('kernel_shape', k),
            helper.make_attribute('pads', p),
            helper.make_attribute('strides', s),
        ])
        if cls._get_singa_op_type(op) == '_Conv2d':
            node.op_type = cls._rename_operators.get('_Conv2d')
            node.attribute.extend([
                helper.make_attribute('group', op.handle.group),
            ])

        elif op.handle.is_max_pooling:
            node.op_type = cls._rename_operators.get('MaxPool2d')
        else:
            node.op_type = cls._rename_operators.get('AvgPool2d')
        return node

    @classmethod
    def _create_dummy(cls, op, op_t):
        """
        get a onnx node from singa dummy (constant)
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        node = cls._common_singa_tensor_to_onnx_node(op, op_t)
        node.attribute.extend([
            helper.make_attribute(
                'value',
                helper.make_tensor(
                    name=op.name,
                    data_type=TensorProto.FLOAT,
                    dims=op_t.shape,
                    vals=tensor.to_numpy(op_t).flatten().astype(float),
                ))
        ])
        del node.input[:]
        return node

    @classmethod
    def _common_singa_tensor_to_onnx_node(cls, op, op_t):
        """
        get a onnx node from a singa operator, prepare its type, inputs and outputs
        Args:
            op: a given operator
        Args:
            op: the tensor of the operator
        Returns: the onnx node
        """
        node_def = NodeProto()
        node_def.name = op.name

        optype = cls._get_singa_op_type(op)
        node_def.op_type = cls._rename_operators.get(optype, optype)

        inputs, outputs = cls._get_singa_op_inputs_outputs(op)
        node_def.input.extend(inputs)
        node_def.output.extend(outputs)

        return node_def

    @classmethod
    def singa_op_to_onnx_node(cls, op, op_t):
        """
        get a onnx node from singa operator
        Args:
            op: a given operator
        Args:
            op_t: the tensor of the operator
        Returns: 
            the onnx node
        """
        optype = cls._get_singa_op_type(op)
        # wether the operator needs special handler
        if optype in cls._special_operators:
            translator = getattr(cls, cls._special_operators[optype])
        else:
            translator = cls._common_singa_tensor_to_onnx_node
        nodes = translator(op, op_t)
        if not isinstance(nodes, collections.Iterable):
            nodes = [nodes]
        nodes = [node for node in nodes if node is not None]
        return nodes

    @classmethod
    def singa_to_onnx_graph(cls, inputs, y, model_name="sonnx"):
        """
        get onnx model from singa computational graph
        Args:
            inputs: a list of input tensors (each is initialized with a name)
        Args:
            y: a list of tensors, usually the outputs of the graph
        Returns: 
            the onnx model
        """
        assert len(y) == 1  # assume there is only one output
        y = y[0]

        graph_def = GraphProto()
        graph_def.name = model_name
        topol = utils.postorderRecursive(y.creator, y)
        # since tensor's name might change
        # we record its id
        input_tensors = {id(x): x for x in inputs}
        # print(input_tensors)
        X = []
        optype = cls._get_singa_op_type(y.creator)
        y_dtype = TensorProto.FLOAT
        if optype in cls._bool_operators:
            y_dtype = cls._bool_operators[optype]
        Y = [helper.make_tensor_value_info(y.name, y_dtype, y.shape)]
        for op, yid, op_t in topol:
            optype = cls._get_singa_op_type(op)
            # print(op.name, cls._get_singa_op_type(op), op_t, optype, yid)
            if yid in input_tensors and optype == 'Dummy':
                # find the input by its id
                op_t = input_tensors[yid]
                dtype = TensorProto.FLOAT
                if op_t.dtype == tensor.int32:
                    dtype = TensorProto.INT32
                X.append(
                    helper.make_tensor_value_info(op.name, dtype, op_t.shape))
            # because the inputs of batchnorm and reshape are differnet with onnx
            # we need to add these inputs into onnx model mannully
            elif yid in input_tensors and optype == '_BatchNorm2d':
                # batchnorm add scale, bias, mean, var as inputs
                running_values = {
                    "mean": op.running_mean,
                    "var": op.running_var
                }
                for tmp_name, running_value in running_values.items():
                    node_name = op.name + ":" + tmp_name
                    tmp_device = running_value.device()
                    running_value.ToHost()
                    np_running_value = running_value.GetFloatValue(
                        int(running_value.Size()))
                    running_value.ToDevice(tmp_device)
                    X.append(
                        helper.make_tensor_value_info(node_name,
                                                      TensorProto.FLOAT,
                                                      np_running_value.shape))
                graph_def.node.extend(cls.singa_op_to_onnx_node(op, op_t))
            elif yid in input_tensors and optype == 'Reshape':
                # reshape add shape
                node_name = op.name + ":shape"
                X.append(
                    helper.make_tensor_value_info(node_name, TensorProto.FLOAT,
                                                  [len(op.shape)]))
                graph_def.node.extend(cls.singa_op_to_onnx_node(op, op_t))
            elif yid in input_tensors and optype == 'Clip':
                # Clip add min and max
                node_name = op.name + ":min"
                X.append(
                    helper.make_tensor_value_info(node_name, TensorProto.FLOAT,
                                                  [1]))
                node_name = op.name + ":max"
                X.append(
                    helper.make_tensor_value_info(node_name, TensorProto.FLOAT,
                                                  [1]))
                graph_def.node.extend(cls.singa_op_to_onnx_node(op, op_t))
            else:
                graph_def.node.extend(cls.singa_op_to_onnx_node(op, op_t))

        graph_def.input.extend(X)
        graph_def.output.extend(Y)
        return graph_def

    @classmethod
    def singa_to_onnx_model(cls, inputs, y, model_name="sonnx"):
        """
        get onnx model from singa computational graph
        Args:
            inputs: a list of input tensors (each is initialized with a name)
        Args:
            y: a list of tensors, usually the outputs of the graph
        Returns: 
            the onnx model
        """
        opset_id = OperatorSetIdProto()
        opset_id.version = cls._target_opset_version
        model = helper.make_model(cls.singa_to_onnx_graph(inputs,
                                                          y,
                                                          model_name="sonnx"),
                                  producer_name='sonnx',
                                  opset_imports=[opset_id])
        # print('The model is:\n{}'.format(model))
        model = optimizer.optimize(model)
        checker.check_model(model)
        return model

    @classmethod
    def _get_singa_op_inputs_outputs(cls, op):
        """
        get inputs and outputs from a given operator
        Args:
            op: a given operator
        Returns: 
            inputs and outputs of the op
        """
        outputs = [op.output_name(idx) for yid, idx in op.y_id2idx.items()]
        inputs = [
            srcop.output_name(srcop.y_id2idx[yid])
            for (srcop, yid, _, _) in op.src
        ]
        return inputs, outputs

    @classmethod
    def _get_singa_op_type(cls, op):
        """
        get the operator type from a given operator
        Args:
            op: a given operator
        Returns: 
            operator type
        """
        return type(op).__name__


class OnnxNode(object):
    """
    Reimplementation of NodeProto from ONNX, but in a form
    more convenient to work with from Python.
    """

    def __init__(self, node):
        self.name = str(node.name)
        self.op_type = str(node.op_type)
        self.attrs = OnnxAttributes.from_onnx(node.attribute)
        # there may some inputs which we regard as attribute, so we mark them there
        self.consumed_inputs = list()
        self.inputs = list(node.input)
        self.outputs = list(node.output)

    def getattr(self, key, default=None):
        return self.attrs[key] if key in self.attrs else default


class OnnxAttributes(dict):
    """
    This is a more convenient way to work with ONNX attributes
    that is not the protobuf representation.
    """

    @staticmethod
    def from_onnx(args):
        d = OnnxAttributes()
        for arg in args:
            d[arg.name] = helper.get_attribute_value(arg)
        return d


class SingaBackend(Backend):

    # This number indicates the onnx operator set version
    _known_opset_version = 10

    # beceuase singa's operators are different from onnx.
    # we define a dict for the name projection
    _rename_operators = {
        'Relu': 'relu',
        'Softmax': 'SoftMax',
        'Sigmoid': 'sigmoid',
        'Add': 'add',
        'MatMul': 'Matmul',
        'Conv': '_Conv2d',
        'MaxPool': '_Pooling2d',
        'AveragePool': '_Pooling2d',
        'BatchNormalization': 'batchnorm_2d',
        'Concat': 'Concat',
        'Flatten': 'Flatten',
        'Gemm': 'Gemm',
        'Reshape': 'Reshape',
        'Sum': 'sum',
        'Cos': 'cos',
        'Cosh': 'cosh',
        'Sin': 'sin',
        'Sinh': 'sinh',
        'Tan': 'tan',
        'Tanh': 'tanh',
        'Acos': 'acos',
        'Acosh': 'acosh',
        'Asin': 'asin',
        'Asinh': 'asinh',
        'Atan': 'atan',
        'Atanh': 'atanh',
        'Selu': 'SeLU',
        'Elu': 'Elu',
        'Equal': 'equal',
        'Less': 'less',
        'Sign': 'sign',
        'Div': 'div',
        'Sub': 'sub',
        'Sqrt': 'sqrt',
        'Log': 'log',
        'Greater': 'greater',
        'HardSigmoid': 'HardSigmoid',
        'Identity': 'identity',
        'Softplus': 'softplus',
        'Softsign': 'softsign',
        'Mean': 'mean',
        'Pow': 'pow',
        'Clip': 'clip',
        'PRelu': 'prelu',
        'Mul': 'mul',
        'Transpose': 'Transpose',
        'Max': 'max',
        'Min': 'min',
        'Shape': 'shape',
        'And': '_and',
        'Or': '_or',
        'Xor': '_xor',
        'Not': '_not',
        'Neg': 'negative',
        'Reciprocal': 'reciprocal',
        'ConstantOfShape': 'ConstantOfShape',
        'Dropout': 'Dropout',
        'ReduceSum': 'ReduceSum',
        'ReduceMean': 'ReduceMean',
        'LeakyRelu': 'LeakyRelu',
        'GlobalAveragePool': 'GlobalAveragePool',
    }

    # this dict indicates the operators that need extra handle
    # each indicates a function name
    _special_operators = {
        'Conv': '_create_conv',
        'MaxPool': '_create_max_avg_pool',
        'AveragePool': '_create_max_avg_pool',
        'BatchNormalization': '_create_batchnorm',
        'Concat': '_create_concat',
        'MatMul': '_create_matmul',
        'Flatten': '_create_flatten',
        'Gemm': '_create_gemm',
        'Reshape': '_create_reshape',
        'Softmax': '_create_softmax',
        'Selu': '_create_selu',
        'Elu': '_create_elu',
        'HardSigmoid': '_create_hardsigmoid',
        'Clip': '_create_clip',
        'Transpose': '_create_transpose',
        'ConstantOfShape': '_create_constantOfShape',
        'Dropout': '_create_dropout',
        'ReduceSum': '_create_reduceOp',
        'ReduceMean': '_create_reduceOp',
        'LeakyRelu': '_create_leakyrelu',
        'GlobalAveragePool': '_create_globalaveragepool',
    }

    @classmethod
    def _create_globalaveragepool(cls, onnx_node, inputs, opset_version):
        """
        get the GlobalAveragePool operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        data_format = onnx_node.getattr("data_format", 'channels_first')
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(data_format)

    @classmethod
    def _create_leakyrelu(cls, onnx_node, inputs, opset_version):
        """
        get the LeakyRelu operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        alpha = onnx_node.getattr("alpha", 0.01)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(alpha)

    @classmethod
    def _create_reduceOp(cls, onnx_node, inputs, opset_version):
        """
        get the ReduceSum, ReduceMean, ReduceMax, ReduceMin, etc, operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        axes = onnx_node.getattr("axes", None)
        keepdims = onnx_node.getattr("keepdims", 1)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(axes, keepdims)

    @classmethod
    def _create_dropout(cls, onnx_node, inputs, opset_version):
        """
        get the Dropout operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        ratio = onnx_node.getattr("ratio", 0)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(ratio)

    @classmethod
    def _create_constantOfShape(cls, onnx_node, inputs, opset_version):
        """
        get the ConstantOfShape operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        value = onnx_node.getattr("value", 0)
        if isinstance(value, onnx.TensorProto):
            value = numpy_helper.to_array(value)[0].item()
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(value)

    @classmethod
    def _create_transpose(cls, onnx_node, inputs, opset_version):
        """
        get the Transpose operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        shape = inputs[0].shape
        perm = onnx_node.getattr("perm", list(range(len(shape) - 1, -1, -1)))
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(perm)

    @classmethod
    def _create_clip(cls, onnx_node, inputs, opset_version):
        """
        get the clip operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward

    @classmethod
    def _create_hardsigmoid(cls, onnx_node, inputs, opset_version):
        """
        get the HardSigmoid operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        alpha = onnx_node.getattr("alpha", 0.2)
        beta = onnx_node.getattr("beta", 0.5)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(alpha, beta)

    @classmethod
    def _create_equal(cls, onnx_node, inputs, opset_version):
        """
        get the equal operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward()

    @classmethod
    def _create_elu(cls, onnx_node, inputs, opset_version):
        """
        get the elu operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        alpha = onnx_node.getattr("alpha", 1.)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(alpha)

    @classmethod
    def _create_selu(cls, onnx_node, inputs, opset_version):
        """
        get the selu operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        alpha = onnx_node.getattr("alpha", 1.67326)
        gamma = onnx_node.getattr("gamma", 1.0507)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(alpha, gamma)

    @classmethod
    def _create_reshape(cls, onnx_node, inputs, opset_version):
        """
        get the reshape operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            the handle of singa operator
        Returns: 
            the autograd of singa operator
        """
        shape = tensor.to_numpy(inputs[1]).tolist()
        onnx_node.consumed_inputs.append(onnx_node.inputs[1])
        del inputs[1]
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(shape)

    @classmethod
    def _create_conv(cls, onnx_node, inputs, opset_version):
        """
        get the conv operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        kernel = tuple(onnx_node.attrs["kernel_shape"])
        padding = tuple(
            onnx_node.attrs["pads"]) if "pads" in onnx_node.attrs else (0, 0)
        stride = tuple(onnx_node.getattr('strides', (1, 1)))
        odd_padding = (0, 0, 0, 0)
        if "auto_pad" in onnx_node.attrs:
            auto_pad = utils.force_unicode(onnx_node.attrs['auto_pad'])
            padding, odd_padding = utils.get_padding_shape(
                auto_pad, inputs[0].shape[2:], kernel, stride)

        # not support dilation
        dilation = onnx_node.getattr('dilations', 1)
        if dilation != 1 and list(dilation) != [1, 1]:
            raise ValueError("Not implemented yet for dilation")
        group = onnx_node.getattr('group', 1)

        # only support 1d or 2d
        if len(kernel) > 2:
            raise ValueError("Only implemented for 1d or 2d")

        bias = len(inputs) == 3
        x = inputs[0]
        x_shape = inputs[0].shape
        in_channels = x_shape[1]
        w_shape = inputs[1].shape
        out_channels = w_shape[0]
        assert w_shape[1] == in_channels // group

        if inputs[0].device.id() == -1:
            if group != 1:
                raise NotImplementedError
            else:
                handle = singa.ConvHandle(x.data, kernel, stride, padding,
                                          in_channels, out_channels, bias,
                                          group)
        else:
            handle = singa.CudnnConvHandle(x.data, kernel, stride, padding,
                                           in_channels, out_channels, bias,
                                           group)

        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(handle, odd_padding)

    @classmethod
    def _create_max_avg_pool(cls, onnx_node, inputs, opset_version):
        """
        get the max or avg pool operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            handle, the handle of singa operator
        Returns: 
            forward, the autograd of singa operator
        """
        kernel = tuple(onnx_node.attrs["kernel_shape"])
        padding = tuple(
            onnx_node.attrs["pads"]) if "pads" in onnx_node.attrs else (0, 0)
        stride = tuple(onnx_node.getattr('strides', (1, 1)))
        odd_padding = (0, 0, 0, 0)
        if "auto_pad" in onnx_node.attrs:
            auto_pad = utils.force_unicode(onnx_node.attrs['auto_pad'])
            padding, odd_padding = utils.get_padding_shape(
                auto_pad, inputs[0].shape[2:], kernel, stride)

        # not support count_include_pad and auto_pad
        if "count_include_pad" in onnx_node.attrs or "ceil_mode" in onnx_node.attrs:
            raise ValueError(
                "Not implemented yet for count_include_pad or ceil_mode")

        # only support 2d
        if len(kernel) != 2:
            raise ValueError("Not implemented yet")

        is_max = onnx_node.op_type == 'MaxPool'
        x = inputs[0]
        if x.device.id() == -1:
            handle = singa.PoolingHandle(x.data, kernel, stride, padding,
                                         is_max)
        else:
            handle = singa.CudnnPoolingHandle(x.data, kernel, stride, padding,
                                              is_max)

        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return _, forward(handle, odd_padding)

    @classmethod
    def _create_batchnorm(cls, onnx_node, inputs, opset_version):
        """
        get the batch norm operator from onnx node
        Args:onnx_node: a given onnx node
        Args:inputs: the input tensor
        Args:opset_version: the opset version
        Returns: the handle of singa operator
        Returns: the autograd of singa operator
        """
        x = inputs[0]
        factor = onnx_node.getattr('momentum', 0.9)
        if x.device.id() == -1:
            raise NotImplementedError
        else:
            handle = singa.CudnnBatchNormHandle(factor, x.data)

        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return handle, forward

    @classmethod
    def _create_concat(cls, onnx_node, inputs, opset_version):
        """
        get the concat operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            the handle of singa operator
        Returns: 
            the autograd of singa operator
        """
        factor = onnx_node.attrs["axis"]
        if factor < 0:
            factor = len(inputs[0].shape
                        ) + factor  # in order to support the negative axis
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return None, forward(axis=factor)

    @classmethod
    def _create_softmax(cls, onnx_node, inputs, opset_version):
        """
        get the concat operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            the handle of singa operator
        Returns: 
            the autograd of singa operator
        """
        factor = onnx_node.getattr('axis', 1)
        if factor < 0:
            # in order to support the negative axis
            factor = len(inputs[0].shape) + factor
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return None, forward(axis=factor)

    @classmethod
    def _create_gemm(cls, onnx_node, inputs, opset_version):
        """
        get the gemm operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            the handle of singa operator
        Returns: 
            the autograd of singa operator
        """
        x = inputs[0]
        alpha = onnx_node.getattr('alpha', 1.)
        beta = onnx_node.getattr('beta', 1.)
        transA = onnx_node.getattr('transA', 0)
        transB = onnx_node.getattr('transB', 0)
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return None, forward(alpha=alpha,
                             beta=beta,
                             transA=transA,
                             transB=transB)

    @classmethod
    def _create_flatten(cls, onnx_node, inputs, opset_version):
        """
        get the flatten operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            the handle of singa operator
        Returns: 
            the autograd of singa operator
        """
        factor = onnx_node.getattr('axis', 1)
        if factor < 0:
            # in order to support the negative axis
            factor = len(inputs[0].shape) + factor

        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return None, forward(start_axis=factor)

    @classmethod
    def _create_matmul(cls, onnx_node, inputs, opset_version):
        """
        get the matmul operator from onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            the handle of singa operator
        Returns: 
            the autograd of singa operator
        """
        _, forward = cls._common_onnx_node_to_singa_op(onnx_node, inputs,
                                                       opset_version)
        return None, forward()

    @classmethod
    def _common_onnx_node_to_singa_op(cls, onnx_node, inputs, opset_version):
        """
        get a common singa operator(only autograd) from a onnx node
        other special operators also can call this func to get autograd
        Args:
            onnx_node: a given onnx node
        Args:
            tensor_map: the input tensor
        Args:
            opset_version: the opset version
        Returns: 
            a dict of tensors
        Returns: 
            a list of SingaOps('name', 'op', 'handle', 'forward')
        """
        onnx_op_type = onnx_node.op_type
        autograd_op = getattr(
            autograd, cls._rename_operators.get(onnx_op_type, onnx_op_type))
        return None, autograd_op

    @classmethod
    def _onnx_node_to_singa_op(cls, onnx_node, inputs, opset_version):
        """
        get a singa operator(handle and autograd) from a onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input list
        Args:
            opset_version: the opset version
        Returns: 
            a dict of tensors
        Returns: 
            a list of SingaOps('name', 'op', 'handle', 'forward')
        """
        if onnx_node.op_type in cls._special_operators:
            translator = getattr(cls, cls._special_operators[onnx_node.op_type])
        else:
            translator = cls._common_onnx_node_to_singa_op
        return translator(onnx_node, inputs, opset_version)

    @classmethod
    def run_node(cls, onnx_node, inputs, opset_version=_known_opset_version):
        """
        run a single singa operator from a onnx node
        Args:
            onnx_node: a given onnx node
        Args:
            inputs: the input tensor
        Args:
            device: the used device
        Args:
            opset_version: the opset version
        Returns: 
            list, the output of the 
        """
        valid_inputs = [x for x in onnx_node.inputs if x != ""]
        assert len(valid_inputs) == len(
            inputs), "{}: expected {} but got {}".format(
                onnx_node.op_type, len(valid_inputs), len(inputs))

        inputs = [inputs[x] for x in valid_inputs]
        handle, forward = cls._onnx_node_to_singa_op(onnx_node, inputs,
                                                     opset_version)
        return cls._run_node(onnx_node, inputs, handle, forward, opset_version)

    @classmethod
    def _run_node(cls,
                  onnx_node,
                  inputs,
                  handle,
                  forward,
                  opset_version=_known_opset_version):
        """
        run a single singa operator from a onnx node
        Args:inputs: 
            the input tensor
        Args:handle: 
            the handle of singa operator
        Args:forward: 
            the forward of singa operator
        Args:
            opset_version: the opset version
        Returns: 
            list, the output of the
        """
        # since reshape acutally only needs one input tensor
        # but onnx regard its shape as another tensor, we need to ommit it
        outputs = forward(*inputs) if handle is None else forward(
            handle, *inputs)
        if not isinstance(outputs, collections.Iterable):
            outputs = [outputs]
        outputs_dict = collections.OrderedDict()
        for (key, val) in zip(onnx_node.outputs, outputs):
            outputs_dict[key] = val
        return outputs_dict

    @classmethod
    def _init_graph_parameter(cls, graph, device):
        """
        init the singa tensor from onnx infos
        Args:
            graph: a given onnx graph
        Args:
            device: the used device
        """
        tensor_map = {}
        initializers = {t.name: t for t in graph.initializer}
        for x in graph.input:
            if x.name in initializers:
                np_tensor = numpy_helper.to_array(initializers[x.name])
                if np_tensor.dtype == "int64":
                    np_tensor = np_tensor.astype(np.int32)
            else:
                x_shape = tuple(
                    dim.dim_value for dim in x.type.tensor_type.shape.dim)
                np_tensor = np.random.randn(*x_shape).astype(np.float32)
            tmp_tensor = tensor.from_numpy(np_tensor)
            tmp_tensor.to_device(device)
            tensor_map[x.name] = tmp_tensor
        return tensor_map

    @classmethod
    def _onnx_model_to_singa_net(cls, model, device, opset_version):
        """
        get all intermediate tensors and operators from onnx model
        Args:
            model: a given onnx model
        Args:
            device: the used device
        Args:
            opset_version: the opset version
        Returns:
            a dict of tensors
        Returns:
            a list of SingaOps('name', 'op', 'handle', 'forward')
        """
        # init all tensor input and weight as a tensor map
        tensor_map = cls._init_graph_parameter(model.graph, device)
        # only weights tensor
        weights = {x.name: tensor_map[x.name] for x in model.graph.initializer}
        # this weights only contains the tensors which have stored the gradients
        singa_ops = []
        singa_op = collections.namedtuple('SingaOps',
                                          ['name', 'op', 'handle', 'forward'])
        for node in model.graph.node:
            node = OnnxNode(node)
            inputs = [tensor_map[x] for x in node.inputs if x not in node.consumed_inputs]
            handle, forward = cls._onnx_node_to_singa_op(
                node, inputs, opset_version)
            outputs = cls._run_node(node, inputs, handle, forward)
            for key, val in outputs.items():
                tensor_map[key] = val
            singa_ops.extend([singa_op(node.name, node, handle, forward)])
        return weights, singa_ops

    @classmethod
    def prepare(cls, model, device, **kwargs):
        """
        get the batch norm operator from onnx node
        Args:
            model: a given onnx node
        Args:
            device: the used device
        Returns: 
            a list of output values
        """
        super(SingaBackend, cls).prepare(model, device, **kwargs)
        # optimize the model
        model = onnx.utils.polish_model(model)
        # check the opset version and ir version
        opset_version = None
        for imp in model.opset_import:
            if not imp.HasField("domain") or imp.domain == "":
                opset_version = imp.version
                if imp.version > cls._known_opset_version:
                    warnings.warn(
                        "This version of singa targets ONNX operator set version {}, but the model we are trying to import uses version {}.  We will try to import it anyway, but if the model uses operators which had BC-breaking changes in the intervening versions, import will fail."
                        .format(cls._known_opset_version, imp.version))
            else:
                warnings.warn("Unrecognized operator set {}".format(imp.domain))
        if opset_version is None:
            if model.ir_version >= 0x00000003:
                raise RuntimeError(
                    "Model with IR version >= 3 did not specify ONNX operator set version (singa requires it)"
                )
            else:
                opset_version = 1
        tensor_map, singa_ops = cls._onnx_model_to_singa_net(
            model, device, opset_version)
        return SingaRep(model, tensor_map, singa_ops)


class SingaRep(BackendRep):

    def __init__(self, model, tensor_map, singa_ops):
        """
        SingaRep provides the intermediate representation of Singa,
        the user can run the forward of the singa model by run func,
        or, the user can append more layers after the singa_ops to do
        the transfer learning
        Args:
            model: a given operator
        Args:
            tensor_map: the tensor of the operator
        Args:
            singa_ops: the tensor of the operator
        """
        super(SingaRep, self).__init__()
        self.model = model
        self.tensor_map = tensor_map
        # this each item of singa_ops is: ('name', 'op', 'handle', 'forward')
        # the name is a string, op is OnnxNode,
        # handle is Singa handle to store the tensor into singa operator
        # the forward is singa autograd operator
        self.singa_ops = singa_ops

    def run(self, inputs, **kwargs):
        """
        run the forward of singa model
        Args:
            inputs: a given operator
        Returns: 
            the onnx node
        """
        # last_layers means we run this model until the last #N layers
        last_layers = kwargs.get('last_layers', len(self.singa_ops))
        # whether return all outputs
        all_outputs = kwargs.get('all_outputs', False)
        # get a specific op by its name
        op_name = kwargs.get('op_name', None)

        # the dict will be returned
        ret_outputs = collections.OrderedDict()
        graph = self.model.graph
        if len(graph.input) - len(graph.initializer) != len(inputs):
            raise RuntimeError(
                "The length of graph input is different from the tensor input: %d, %d"
                % (len(graph.input) - len(graph.initializer), len(inputs)))
        # run the handle by the order of the list(the list is Topological Sorting)
        for inp in graph.input:
            if inp.name not in self.tensor_map:
                self.tensor_map[inp.name] = inputs.pop(0)
        for _, op, handle, forward in self.singa_ops[:last_layers]:
            inputs = [self.tensor_map[x] for x in op.inputs if x not in op.consumed_inputs]
            outputs = _run_node(op, inputs, handle, forward)
            for key, val in outputs.items():
                self.tensor_map[key] = val
                ret_outputs[key] = val

        if op_name is not None:
            if op_name in outputs:
                return outputs[op_name]
            else:
                raise RuntimeError(
                    "The op_name {} does not exist, please check. The available op_names are: {}"
                    .format(op_name, [val for key, val in op_name.items()]))

        # return all outputs if all_outputs==True
        # else return last outputs
        if all_outputs:
            return ret_outputs
        else:
            return list(outputs.values())


run_node = SingaBackend.run_node
_run_node = SingaBackend._run_node
prepare = SingaBackend.prepare
to_onnx = SingaFrontend.singa_to_onnx_model
save = onnx.save
load = onnx.load
