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

// **************************************
// Element-wise functions
// **************************************

// Sum is basically reduction.
// This reduction code is serial reduction modified from AMD's example.
// http://developer.amd.com/resources/documentation-articles/articles-whitepapers/opencl-optimization-case-study-simple-reductions/
__kernel 
void clkernel_abs(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = fabs(in[i]);
}

__kernel
void clkernel_add_scalar(const int num, float x, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in[i] + x;
}

__kernel
void clkernel_add(const int num, __global const float* in1, __global const float* in2, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in1[i] + in2[i];
}

__kernel
void clkernel_clamp(const int num, float low, float high, __global const float* in, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = clamp(in[i], low, high);
}

__kernel
void clkernel_divide_scalar_matx(const int num, __global const float* in1, const float x,
		  __global const float* in2, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in1[i] / x;
}

__kernel
void clkernel_divide_scalar_xmat(const int num, const float x, __global const float* in1, 
		  __global const float* in2, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = x / in1[i];
}

__kernel
void clkernel_divide(const int num, __global const float* in1, __global const float* in2, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in1[i] / in2[i];
}

__kernel
void clkernel_eltmult_scalar(const int num, const float x, __global const float* in, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in[i] * x;
}

__kernel
void clkernel_eltmult(const int num, __global const float* in1, __global const float* in2, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in1[i] * in2[i];
}

__kernel
void clkernel_exp(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = exp(in[i]);
}

__kernel
void clkernel_le(const int num, __global const float* in, const float x, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = (in[i] <= x) ? 1.0f : 0.0f;
}

__kernel
void clkernel_log(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = log(in[i]);
}

__kernel
void clkernel_lt(const int num, __global const float* in, const float x, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = (in[i] < x) ? 1.0f : 0.0f;
}

__kernel
void clkernel_ge(const int num, __global const float* in, const float x, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = (in[i] >= x) ? 1.0f : 0.0f;
}

__kernel
void clkernel_gt(const int num, __global const float* in, const float x, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = (in[i] > x) ? 1.0f : 0.0f;
}

__kernel
void clkernel_pow_scalar(const int num, const float x, __global const float* in, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = pow(in[i], x);
}

__kernel
void clkernel_pow(const int num, __global const float* in1, __global const float* in2, 
		  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = pow(in1[i], in2[i]);
}

__kernel
void clkernel_relu(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = (in[i] > 0) ? in[i] : 0.0f;
}

__kernel
void clkernel_set(const int num, const float x, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = x;
}

__kernel
void clkernel_sigmoid(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = 1 / (1 + exp(-(in[i])));
}

__kernel
void clkernel_sign(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = sign(in[i]);
}

__kernel
void clkernel_sqrt(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = sqrt(in[i]);
}

// kernel for square is called pow(2).

__kernel
void clkernel_subtract_scalar(const int num, __global const float* in, const float x, 
							  __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in[i] - x;
}

__kernel
void clkernel_subtract(const int num, __global const float* in1, __global const float* in2, 
					   __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = in1[i] - in2[i];
}

// reduce3 kernel from
// https://github.com/sschaetz/nvidia-opencl-examples/blob/master/OpenCL/src/oclReduction/oclReduction_kernel.cl
__kernel 
void clkernel_sum(const int num, __global const float* in, __global float* out, 
				  __local float* sdata) {
  const int i = get_group_id(0)*(get_local_size(0)*2) + get_local_id(0);
  const int tid = get_local_id(0);
  sdata[tid] = (i < num) ? in[i] : 0.0f;

  // Perform the first level of reduction.
  if (i + get_local_size(0) < num) {
	sdata[tid] += in[i + get_local_size(0)];
  }
  barrier(CLK_LOCAL_MEM_FENCE);

  for (int s = get_local_size(0)/2; s > 0; s >>= 1) {
	if (tid > s) {
	  sdata[tid] += sdata[tid + s];
	}
	barrier(CLK_LOCAL_MEM_FENCE);
  }

  if (tid == 0) {
	out[get_group_id(0)] = sdata[0];
  }
}

__kernel
void clkernel_tanh(const int num, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = tanh(in[i]);
}

// **************************************
// Random functions
// **************************************

// See: distribution.cl

// *********************************************************
// BLAS functions, ref to http://docs.nvidia.com/cuda/cublas
// *********************************************************

__kernel
void clkernel_amax(const int num, __global const float* in, __global int* ret, 
				   __local uint* sdata, __local size_t* temp) {
  const int gid = get_global_id(0);
  const int tid = get_local_id(0);

  for(int s = get_local_size(0)/2; s > 0; s >>= 1) {
	if (tid < s) {
	  sdata[tid] = (in[sdata[tid]] > in[tid+s]) ? sdata[tid] : tid;
	}
	barrier(CLK_LOCAL_MEM_FENCE);
  }
  if (tid == 0) {
	ret[0] = sdata[0];
  }
}

__kernel
void clkernel_amin(const int num, __global const float* in, __global int* ret, 
				   __local float* sdata, __local size_t* temp) {
  const int gid = get_global_id(0);
  const int tid = get_local_id(0);

  // Initialize the values to pos infinity.
  sdata[tid] = (i < num) ? in[i] : INFINITY;
  barrier(CLK_LOCAL_MEM_FENCE);

  for(int s = get_local_size(0)/2; s > 0; s >>= 1) {
	if (tid < s) {
	  sdata[tid] = (in[sdata[tid]] < in[tid+s]) ? sdata[tid] : tid;
	}
	barrier(CLK_LOCAL_MEM_FENCE);
  }
  if (tid == 0) {
	ret[0] = sdata[0];
  }
}

__kernel
void clkernel_asum(const int num, __global const float* in, __global float* out, 
				   __local float* sdata) {
  const int tid = get_local_id(0);
  const int i = get_global_id(0);

  // Initialize
  sdata[tid] = (i < num) ? in[i] : INFINITY;
  // Perform the first level of reduction.
  if (i + get_local_size(0) < num) {
	sdata[tid] += in[i + get_local_size(0)];
  }
  barrier(CLK_LOCAL_MEM_FENCE);

  for(int s = get_local_size(0)/2; s > 0; s >>= 1) {
	if (tid < s) {
	  sdata[tid] = fabs(sdata[tid + s]);
	}
	barrier(CLK_LOCAL_MEM_FENCE);
  }
  if (tid == 0) {
	out[0] = sdata[0];
  }
}

__kernel
void clkernel_axpy(const int num, float alpha, __global const float* in, 
				   __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = fma(alpha, in[i], out[i]);
}

// This kernel is essentially the same as Sum, except that during the process
// of reading in data to the local memory, the value is also doubled.
// Then, just before submitting the sum to out, we do a square-root on it.
__kernel
void clkernel_nrm2(const int num, __global const float* in, __global float* out,
				   __local float* sdata) {
  const int i = get_group_id(0)*(get_local_size(0)*2) + get_local_id(0);
  const int tid = get_local_id(0);
  sdata[tid] = (i < num) ? (in[i] * in[i]) : 0.0f;

  // Perform the first level of reduction.
  if (i + get_local_size(0) < num) {
	sdata[tid] += in[i + get_local_size(0)];
  }
  barrier(CLK_LOCAL_MEM_FENCE);

  for (int s = get_local_size(0)/2; s > 0; s >>= 1) {
	if (tid > s) {
	  sdata[tid] += sdata[tid + s];
	}
	barrier(CLK_LOCAL_MEM_FENCE);
  }

  if (tid == 0) {
	out[get_group_id(0)] = sqrt(sdata[0]);
  }
}

__kernel
void clkernel_scale(const int num, float x, __global float* out) {
  const int i = get_global_id(0);
  if (i >= num) return;
  out[i] = x * out[i];
}

__kernel
void clkernel_dot(const int num, __global const float* in1, __global const float* in2, 
	  			  __global float* out, __local float* scratch) {
  const int i = get_global_id(0);
  if (i >= num) return;
  int offset = i << 2;
  scratch[i] = in1[offset] * in2[offset];
  
}

// Third kernel from http://www.bealto.com/gpu-gemv_intro.html
// y = α*A*v + β*y
__kernel
void clkernel_gemv(const int m, const int n, const float alpha,
				   __global const float* A, __global const float* v, 
				   const float beta, __global float* out) {
  const int i = get_global_id(0);
  float sum  = 0.0f;
  for (int k = 0; k < n; k++) {
	sum += fma(alpha, A[i + m * k], v[k]) + beta * out[i + m * k];
  }
  out[i] = sum;
}

// http://docs.nvidia.com/cuda/cublas/#cublas-lt-t-gt-dgmm
// X[j] = x[j*inc(x)] 						if inc(x) ≥ 0 
//		= x[(χ − 1)*|inc(x)| − j*|inc(x)|] 	if inc(x) < 0

// C = diag( X )*A
__kernel
void clkernel_dgmm_left(const int nrow, const int ncol,
						__global const float* M, __global const float* v, 
						__global float* out) {
  const uint gidx = get_global_id(0);

  uint offset = gidx * ncol;
  for (uint i = 0; i < ncol; i+++) {
	out[offset + i] = M[offset + i] * v[i];
  }
}

// C = A*diag( X )
__kernel
void clkernel_dgmm_right(const int nrow, const int ncol,
						 __global const float* M, __global const float* v, 
						 __global float* out) {
  const uint gidx = get_global_id(0);

  uint offset = gidx * ncol;
  for (uint i = 0; i < ncol; i+++) {
	out[offset + i] = M[offset + i] * v[gidx];
  }
}

// TODO: Optimize with Reference from http://www.cedricnugteren.nl/tutorial.php?page=1
//  C = α*A*B + β*C
__kernel
void clkernel_gemm(const int nrowA, const int ncolB, const int ncolA, const float alpha,
		 		   __global const float *A, __global const float* B, const float beta, 
		  		   __global float* C) {
  const uint gidx = get_global_id(0);
  const uint gidy = get_global_id(1);

  float acc = 0.0f;
  for (uint i = 0; uint < ncolA; i++) {
	acc = fma(A[k * nrowA + gidx], B[gidy * ncolA + k] * alpha, acc);
  }

  C[gidy * nrowA + gidx] = fma(C[gidy * nrowA + gidx], beta, acc);
}


__kernel
void clkernel_crossentropy(const uint batchsize, const uint dim, 
						   __global const float* p, __global const int* t, 
						   __global float* loss) {
  const uint gidx = get_global_id(0);
  if (gidx >= batchsize) return;

  int truth_idx = t[gidx];
  if (truth_idx <= 0) return;
  float prob_of_truth = p[gidx + truth_idx];
  loss[gidx] = -log(fmax(prob_of_truth, -FLT_MIN));
}


__kernel
void clkernel_softmaxentropy(const uint batchsize, const uint dim,
							 __global const float* p, __global const int* t,
							 __global float* grad) {
  const uint gidx = get_global_id(0);
  if (gidx >= batchsize) return;

  int truth_idx = t[gidx];
  if (truth_idx <= 0) return;
  grad[gidx * dim + truth_idx] -= 1.0;
}


// **************************************
// Matrix functions
// **************************************
/*
__kernel
void clkernel_addcol(int nrow, int ncol, __global const float* A, __global const float* v, __global float* out) {
  const int i = get_global_id(0);
  const int j = get_global_id(1);
  if (i >= nrow) return;
  if (j >= ncol) return;
  ret[j] = A[j + nrow * i] + v[j];
}

__kernel
void clkernel_addrow(int nrow, int ncol, __global const float* A, __global const float* v, __global float* out) {
  const int i = get_global_id(0);
  const int j = get_global_id(1);
  if (i >= nrow) return;
  if (j >= ncol) return;
  out[i] = A[i + ncol * j] + v[i];
}

__kernel
void clkernel_outerproduct(int m, const int n, __global const float* in1, __global const float* in2, __global float* out) {
  const int col = get_global_id(0);
  const int row = get_global_id(1);
  
  // TODO: This
}

__kernel
void clkernel_sumcol(int nrow, int ncol, __global const float* in, __global float* out) {
  const int i = get_global_id(0);
  if (i >= nrow) return;

  float sum = 0.0f;
  for (int j = 0; j < nrow; j++) {
	sum += input[nrow * i + j];
  }
  out[i] = sum;
}
*/
__kernel
void clkernel_sumrow(int nrow, int ncol, __global const float* in, __global float* out) {
  const int idx = get_global_id(0);
  if (idx >= nrow) return;
  
  float sum = 0.0f;
  for (int j = 0; j < ncol; j++) {
	sum += in[j + ncol * idx];
  }
  out[i] = sum;
}


// Adapted from http://code.haskell.org/HsOpenCL/tests/bench/transpose.cl
#define BLOCK_DIM 16
__kernel
void clkernel_transpose(uint nrow, uint ncol, 
						__global const float* in, __global float* out, 
						__local float* sdata) {
  uint gidx = get_global_id(0);
  uint gidy = get_global_id(1);

  if ((gidx < ncol) && (gidy < nrow)) {
	uint id_in = gidy * ncol + gidx;
	sdata[get_local_id(1) * (BLOCK_DIM+1) + get_local_id(0)] = in[id_in];
  }

  barrier(CLK_LOCAL_MEM_FENCE);

  gidx = get_group_id(1) * BLOCK_DIM + get_local_id(0);
  gidy = get_group_id(0) * BLOCK_DIM + get_local_id(1);
  if ((gidx < nrow) && (gidy < ncol)) {
	uint id_out = gidy * nrow + gidx;
	out[id_out] = sdata[get_local_id(0) * (BLOCK_DIM + 1) + get_local_id(1)];
  }
}
/*
__kernel
void clkernel_transpose2(uint nrow, uint ncol, __global const float* in, __global float* out, __local float* sdata) {
  const uint lidx = get_local_id(0);
  const uint lidy = get_local_id(1);
  const uint id0 = get_group_id(0) * ncol * lidx;
  const uint id1 = get_group_id(1) * nrow * lidy;

  if (id0 < nrow && id1 < ncol) {
	sdata[lidx][lidy] = in[id1 * nrow + id0];
  }

  barrier(CLK_LOCAL_MEM_FENCE);

  const uint new_id0 = get_group_id(1) * nrow + lidx;
  const uint new_id1 = get_group_id(0) * ncol + lidy;

  if (new_id0 < ncol && new_id1 < nrow) {
	out[new_id1 * ncol + new_id0] = sdata[lidx][lidy];
  }
}*/

__kernel
void clkernel_diagvec_left(uint vsize, __global const float* vin, __global float* out) {
  const uint gid = get_global_id(0);

  for (uint i = 0; i < size; i++)
	mout[gidx * size + i] = (i == gidx) ? vin[gidx] : 0.0f;
}
