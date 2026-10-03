# 删改边界示例

示例是合成的，用来区分“可删的防御性措辞”和“影响决策的限制”，不是禁词表。

## 1. 层层保留：压成一个限定

**原文：** We may perhaps potentially be able to finish the migration in roughly six to eight weeks, depending on access approval.

**改写：** We estimate six to eight weeks after access approval.

**理由：** 工期范围和前置条件是真的，四层不确定措辞不是。

**对照：** 若原文是 “six to eight weeks, but the vendor has not confirmed the API quota”，配额未确认会改变排期判断，要保留：“We estimate six to eight weeks after access approval; the vendor has not yet confirmed the API quota.”

## 2. 负面范围：只在影响归属时保留

**原文：** This proposal is not a comprehensive redesign and does not try to address every support workflow. It covers intake, routing, and escalation.

**改写：** This proposal covers intake, routing, and escalation.

**理由：** 正面写清覆盖范围就够了，被排除的部分没有人需要据此做决定。

**对照：** 若合同把 billing 划给另一个团队，并要求明确写出排除项：“This proposal covers intake, routing, and escalation; billing remains out of scope.” 这条排除能防止归属误解，要保留。

## 3. 证据强度：删勤勉叙述，不加强结论

**原文：** We reviewed the available data and tried to be appropriately cautious. Although we could not verify every possible edge case, in this observational pilot of 120 tickets, 24-hour completion rose from 68% to 76% after automatic triage was introduced, which suggests triage may help.

**改写：** In an observational pilot of 120 tickets, 24-hour completion rose from 68% to 76% after automatic triage was introduced, which suggests triage may help.

**理由：** 开头两句只是在自证谨慎，删掉。“observational”和“suggests … may help”标明了证据强度，要保留；不能改成 “triage improved completion”，那是把相关写成了因果。

**对照：** 若原文是随机对照（对照组 68%，自动分诊组 76%，预先设定的分析），才可以写 “automatic triage increased completion from 68% to 76%”。
