#!/usr/bin/env bash
#/**
# *
# * Licensed to the Apache Software Foundation (ASF) under one
# * or more contributor license agreements.  See the NOTICE file
# * distributed with this work for additional information
# * regarding copyright ownership.  The ASF licenses this file
# * to you under the Apache License, Version 2.0 (the
# * "License"); you may not use this file except in compliance
# * with the License.  You may obtain a copy of the License at
# *
# *     http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# */

# This script is used by Jenkins to compile and distribute SINGA wheel file.

echo Compile, test and distribute PySINGA...
echo parameters: $1
echo workspace: `pwd`
echo OS version: `cat /etc/issue`
echo kernal version: `uname -a`
echo CUDA version: $CUDA_VERSION
echo CUDNN version: $CUDNN_VERSION
# set parameters
CUDNN="OFF"
if [ $1 = "CUDNN" ]; then
  CUDNN="ON"
fi
# setup env
rm -rf build
mkdir build
# compile singa c++
cd build
cmake -DUSE_CUDNN=$CUDNN -DUSE_CUDA=$CUDNN -DUSE_MODULES=ON ../
make
# unit test cpp code
./bin/test_singa --gtest_output=xml:./gtest.xml
# compile pysinga
cd python
python setup.py bdist_wheel
# rename dist
cd dist
mv singa-1.0.1-py2-none-any.whl singa-1.0.0-cp27-none-linux_x86_64.whl
# unit test python code
cd ../../../test/python
PYTHONPATH=../../build/python/ python run.py
echo Job finished...
