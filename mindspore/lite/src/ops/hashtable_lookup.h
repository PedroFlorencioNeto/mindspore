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
#ifndef LITE_MINDSPORE_LITE_C_OPS_HASHTABLE_LOOKUP_H_
#define LITE_MINDSPORE_LITE_C_OPS_HASHTABLE_LOOKUP_H_

#include <vector>
#include "src/ops/primitive_c.h"

namespace mindspore {
namespace lite {
class HashtableLookup : public PrimitiveC {
 public:
#ifdef PRIMITIVE_WRITEABLE
  MS_DECLARE_PARENT(HashtableLookup, PrimitiveC);
  HashtableLookup() = default;
  explicit HashtableLookup(schema::PrimitiveT *primitive) : PrimitiveC(primitive) {}
  int UnPackAttr(const Primitive &prim, const std::vector<AnfNodePtr> &inputs) override;
#else
  HashtableLookup() = default;
  int UnPackToFlatBuilder(const schema::Primitive *primitive, flatbuffers::FlatBufferBuilder *fbb) override;
#endif
  int InferShape(std::vector<Tensor *> inputs_, std::vector<Tensor *> outputs_) override;
};
}  // namespace lite
}  // namespace mindspore

#endif  // LITE_MINDSPORE_LITE_C_OPS_HASHTABLE_LOOKUP_H_
