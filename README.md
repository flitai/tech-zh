# tech-zh

`tech-zh` 是一个面向中文技术文档的 Codex skill。它用于生成、改写和审查低歧义、可执行、可验证的中文文本。

本 skill 借鉴 ASD-STE100 Issue 9 的受控语言思想，并根据中文语法重新制定规则。它不是 ASD-STE100 的官方中文版本、翻译件或认证工具。

## 适用场景

- 操作规程、维修步骤和安全说明。
- 技术需求、接口要求和验收准则。
- 技术方案、设计说明和测试报告。
- LLM 提示词、Agent 指令、工具说明和错误信息。

本 skill 不适用于文学、广告、公关或需要保留个人风格的文本。

## 主要能力

- 统一术语，避免同一概念使用多个名称。
- 写明责任主体、动作对象、触发条件和执行顺序。
- 拆分多动作长句，减少指代和修饰范围歧义。
- 保留“必须、应、可以、不得、可能”等约束强度。
- 将模糊要求转换为可判定要求，或标记为待提供信息。
- 区分事实、推断、假设、建议和待验证项。
- 检查安全说明是否包含风险级别、预防动作、危险源和可能后果。
- 保护代码、命令、路径、字段名、标识符、公式、数字和单位。

## 中文适配

英文 STE 的部分规则不能直接用于中文。例如，中文没有对应的冠词规则、英文时态变化、短语动词和按空格计词方法。

本 skill 改为检查下列中文问题：

- 主语省略和零代词。
- “其、该、此、上述”等词的指向。
- 多层“的”结构和长定语。
- 连动结构、条件附着和否定范围。
- “分别、均、至少、仅”等词的作用范围。
- “及时、适当、有关、若干、原则上”等不可直接验收的表达。

## 安装

将本仓库放入 Codex 的个人 skill 目录：

```text
~/.codex/skills/tech-zh
```

可以直接克隆：

```bash
git clone https://github.com/flitai/tech-zh.git ~/.codex/skills/tech-zh
```

也可以保留现有工作目录，并创建符号链接：

```bash
ln -s /absolute/path/to/tech-zh ~/.codex/skills/tech-zh
```

安装后，刷新 Codex 的 skill 列表或新建会话。

## 使用

调用名称：

```text
$tech-zh
```

生成技术需求：

```text
$tech-zh 根据以下资料编写系统接口需求。不要补造未提供的参数。
```

严格改写规程：

```text
$tech-zh 按严格模式改写以下操作规程。保留全部数字、单位、条件和安全要求。
```

审查技术方案：

```text
$tech-zh 审查以下技术方案。列出术语不一致、责任主体不明和不可验收的要求。
```

默认使用两种工作模式：

- **严格模式**：适用于规程、安全文本、需求、接口约束、验收准则和 Agent 指令。
- **通用模式**：适用于技术方案、报告和原理说明。

## 示例

原文：

> 系统应及时处理异常，并在必要时通知相关人员。

改写：

> 系统应在 `[待提供：处理时限]` 内处理异常。满足 `[待提供：通知条件]` 时，系统应通知 `[待提供：接收角色]`。

改写没有猜测时限、通知条件或人员角色。缺失信息使用明确的待提供项表示。

更多示例见 [references/examples.md](references/examples.md)。

## 目录结构

```text
tech-zh/
├── LICENSE
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── asd-mapping.md
│   ├── chinese-rules.md
│   └── examples.md
└── scripts/
    └── ctc_lint.py
```

- [SKILL.md](SKILL.md)：skill 入口、核心规则和工作流程。
- [references/chinese-rules.md](references/chinese-rules.md)：完整的中文技术写作规则。
- [references/asd-mapping.md](references/asd-mapping.md)：ASD-STE100 规则与中文规则的映射。
- [references/examples.md](references/examples.md)：中文改写示例。
- [scripts/ctc_lint.py](scripts/ctc_lint.py)：中文技术文本机械初筛工具。

## 文本初筛工具

`ctc_lint.py` 仅使用 Python 标准库。

普通检查：

```bash
python3 scripts/ctc_lint.py document.md
```

严格检查：

```bash
python3 scripts/ctc_lint.py --strict procedure.md
```

输出 JSON：

```bash
python3 scripts/ctc_lint.py --json document.md
```

运行自测：

```bash
python3 scripts/ctc_lint.py --selftest
```

初筛脚本检查模糊词、潜在指代、动作名词化、被动责任、分号、注释中的指令、缺少后果的安全说明和超长句。检查结果只用于定位复核位置，不能证明语义正确或符合任何正式标准。

## 与 ASD-STE100 的关系

本 skill 继承以下方法：

- 一个概念使用一个术语。
- 一个句子只表达一个主要动作或判断。
- 条件先于动作。
- 程序、说明和安全文本使用不同的表达结构。
- 不为缩短句子而删除必要信息。
- 术语和风格在全文保持一致。

本 skill 不包含 ASD-STE100 的受控英文词典，也不逐句复制原标准。需要正式 STE 合规时，必须使用 ASD 发布的标准、词典和适用的组织流程。

ASD-STE100 的著作权和商标归权利人所有。官方信息见 [ASD-STE100 网站](https://www.asd-ste100.org/)。

## 能力边界

本 skill 可以改进表达形式，但不能：

- 验证技术事实是否正确。
- 证明设备或系统达到声明的效果。
- 替代安全分析、法规审查或专业认证。
- 根据缺失资料自行确定参数、阈值或责任分工。
- 保证自动检查结果等同于人工语义审查。

## 许可证

本项目使用 [MIT License](LICENSE)。该许可证仅适用于本仓库的原创内容，不改变 ASD-STE100 原始资料的著作权和商标归属。
