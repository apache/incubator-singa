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

# This script is used by Jenkins to compile and test SINGA

echo Compile and test SINGA...
echo parameters: $1
echo workspace: `pwd`
echo OS version: `cat /etc/issue`
echo kernal version: `uname -a`
echo CUDA version: $CUDA_VERSION
echo CUDNN version: $CUDNN_VERSION
COMMIT=`git rev-parse --short HEAD`
echo COMMIT HASH: $COMMIT
# set parameters
CUDA="OFF"
CUDNN="OFF"
if [ $1 = "CUDA" ]; then
  CUDA="ON"
  CUDNN="ON"
fi

# setup env
rm -rf build
mkdir build

if [ `uname` = "Darwin" ]; then
  EXTRA_ARGS="-DPYTHON_LIBRARY=`python-config --prefix`/lib/libpython2.7.dylib -DPYTHON_INCLUDE_DIR=`python-config --prefix`/include/python2.7/"
fi

# compile singa c++
cd build
cmake -DUSE_CUDA=$CUDA -DENABLE_TEST=ON -DPACKAGE=ON $EXTRA_ARGS ../
make
# unit test cpp code
./bin/test_singa --gtest_output=xml:./gtest.xml
# unit test python code
cd ../test/python
PYTHONPATH=../../build/python/ python run.py
echo Test complete.
echo Building Debian package...
cd ../../build
make package
mkdir $BUILD_ID
cp *.deb $BUILD_ID
tar czf $BUILD_ID.tar.gz $BUILD_ID/*.deb
echo Job finished.
