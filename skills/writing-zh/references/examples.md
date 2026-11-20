# 删改边界示例

示例是合成的：第 1–3 组区分“可删的防御性措辞”和“影响决策的限制”，第 4–6 组示范正式稿与表格写法，都不是禁词表。

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

## 4. 正式稿：临时说法改成书面表达

**原文：** 9. 还没做需要注意的：导出功能还不太行，后面要弄一下。

**改写：** 9. 后期目标：完善导出功能，支持批量导出与失败重试。

**理由：** “还没做需要注意的”是聊天里的临时说法，“不太行”“弄一下”没有说明问题和动作；改成书面小标题，并写出具体要做的事。

## 5. 缩写电报体：补全主谓宾

**原文：** 同步链路收口，旧口径下线。

**改写：** 数据同步改由新服务统一处理，旧服务的统计规则不再使用。

**理由：** “链路”“收口”“口径”是团队内部说法，句子也缺主语；补出谁处理、处理什么，以及读者会看到的变化。

## 6. 表格与标题：自然书面中文

**原文：**

| 方案 | 处理一段 10 分钟视频大概需要花费的时间（单位为秒） | 本板实参 | 核心机制深度解析 |
|---|---|---|---|

**改写：**

| 方案 | 耗时 (s) | 实验板参数 | 工作机制与常见问题 |

## 7. 更新公告：去掉口语与黑话

**口语草稿：** 服务要换版那几分钟不要紧，旧任务还能接着跑，也不会不声不响把刚保存的框弄丢。

**黑话草稿：** 支持镜像无缝滚动升版与边车状态幂等落盘，保障标注写请求终态收敛与零数据丢失。

**正式定稿：** 服务升级期间暂停接收新建任务，已有保存、视频续传与训练停止操作仍可正常执行；更新完成后自动恢复服务，已提交标注数据不受影响。

**理由：** 口语草稿夹带“不要紧”“不声不响”“弄丢”等聊天气息；黑话草稿堆砌“幂等落盘”“边车状态”“终态收敛”等内部开发缩写，普通用户看不懂。正式定稿直接写出用户能感知的界面行为与结果。
|---|---|---|---|

**理由：** 表头写短属性名、把单位放进括号，不用句子也不硬造四字缩略词（如“本板实参”）；小标题写清内容即可，不堆“深度解析”“三大动作”等宣传黑话。
