/**
 * Copyright 2020-2021 Huawei Technologies Co., Ltd
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef MINDSPORE_CCSRC_MINDDATA_DATASET_INCLUDE_EXECUTE_H_
#define MINDSPORE_CCSRC_MINDDATA_DATASET_INCLUDE_EXECUTE_H_

#include <vector>
#include <memory>
#include "include/api/types.h"
#include "include/constants.h"
#include "dataset/include/transforms.h"

namespace mindspore {
namespace dataset {

// class to run tensor operations in eager mode
class Execute {
 public:
  /// \brief Constructor
  explicit Execute(std::shared_ptr<TensorOperation> op);

  explicit Execute(std::vector<std::shared_ptr<TensorOperation>> ops);

  /// \brief Destructor
  ~Execute() = default;

  /// \brief callable function to execute the TensorOperation in eager mode
  /// \param[in] input Tensor to be transformed
  /// \param[out] output Transformed tensor
  /// \return Status code
  Status operator()(const mindspore::MSTensor &input, mindspore::MSTensor *output);

  /// \brief callable function to execute the TensorOperation in eager mode
  /// \param[in] input_tensor_list List of Tensor to be transformed
  /// \param[out] out Result tensor after transform
  /// \return - Status
  Status operator()(const std::vector<mindspore::MSTensor> &input_tensor_list, std::vector<mindspore::MSTensor> *out);

 private:
  std::vector<std::shared_ptr<TensorOperation>> ops_;
};

}  // namespace dataset
}  // namespace mindspore
#endif  // MINDSPORE_CCSRC_MINDDATA_DATASET_INCLUDE_EXECUTE_H_