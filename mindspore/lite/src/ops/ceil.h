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

#ifndef LITE_MINDSPORE_LITE_C_OPS_CEIL_H_
#define LITE_MINDSPORE_LITE_C_OPS_CEIL_H_

#include <vector>
#include <set>
#include <cmath>
#include "src/ops/arithmetic_self.h"

namespace mindspore {
namespace lite {
class Ceil : public ArithmeticSelf {
 public:
  Ceil() = default;
  ~Ceil() = default;
#ifdef PRIMITIVE_WRITEABLE
  MS_DECLARE_PARENT(Ceil, ArithmeticSelf);
  explicit Ceil(schema::PrimitiveT *primitive) : ArithmeticSelf(primitive) {}
#else
  int UnPackToFlatBuilder(const schema::Primitive *primitive, flatbuffers::FlatBufferBuilder *fbb) override {
    MS_ASSERT(nullptr != primitive);
    MS_ASSERT(nullptr != fbb);
    auto val_offset = schema::CreateCeil(*fbb);
    auto prim_offset = schema::CreatePrimitive(*fbb, schema::PrimitiveType_Ceil, val_offset.o);
    fbb->Finish(prim_offset);
    return RET_OK;
  }
#endif
};

}  // namespace lite
}  // namespace mindspore

#endif  // LITE_MINDSPORE_LITE_C_OPS_CEIL_H_