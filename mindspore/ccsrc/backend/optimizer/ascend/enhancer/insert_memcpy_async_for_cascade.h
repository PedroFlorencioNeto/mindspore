/**
 * Copyright 2020 Huawei Technologies Co., Ltd
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
#ifndef MINDSPORE_CCSRC_PRE_ACTIVATE_ASCEND_ENHANCER_INSERT_MEMCPY_ASYNC_FOR_CASCADE_H_
#define MINDSPORE_CCSRC_PRE_ACTIVATE_ASCEND_ENHANCER_INSERT_MEMCPY_ASYNC_FOR_CASCADE_H_

#include <memory>
#include "backend/optimizer/common/optimizer.h"
#include "backend/optimizer/ascend/ascend_helper.h"

namespace mindspore {
namespace opt {
class InsertMemcpyAsyncForCascade : public PatternProcessPass {
 public:
  explicit InsertMemcpyAsyncForCascade(bool multigraph = true)
      : PatternProcessPass("insert_memcpy_async_for_cascade", multigraph),
        kernel_select_(std::make_shared<KernelSelect>()) {}
  ~InsertMemcpyAsyncForCascade() override = default;
  const AnfNodePtr Process(const FuncGraphPtr &, const AnfNodePtr &, const EquivPtr &) const override;

 private:
  AnfNodePtr InsertMemcpyAsync(const FuncGraphPtr &graph, const CNodePtr &hccl_node) const;
  KernelSelectPtr kernel_select_;
};
}  // namespace opt
}  // namespace mindspore
#endif  // MINDSPORE_CCSRC_PRE_ACTIVATE_ASCEND_ENHANCER_INSERT_MEMCPY_ASYNC_FOR_OP_CASCADE_H_
