---
name: verification-loop
description: "面向 Claude Code 会话的综合验证系统。"
origin: AAN
---

# 验证回路技能（Verification Loop Skill）

面向 Claude Code 会话的综合验证系统。

## 何时使用

在以下情况下调用此技能：
- 完成一个功能或重要代码变更之后
- 创建 PR 之前
- 希望确保质量门禁通过时
- 重构之后

## 验证阶段

### 阶段 1：构建验证

```bash
# 检查项目是否可以构建
npm run build 2>&1 | tail -20
# 或
pnpm build 2>&1 | tail -20
```

若构建失败，停止并先行修复，再继续后续阶段。

### 阶段 2：类型检查

```bash
# TypeScript 项目
npx tsc --noEmit 2>&1 | head -30

# Python 项目
pyright . 2>&1 | head -30
```

汇报所有类型错误。继续之前修复关键问题。

### 阶段 3：Lint 检查

```bash
# JavaScript / TypeScript
npm run lint 2>&1 | head -30

# Python
ruff check . 2>&1 | head -30
```

### 阶段 4：测试套件

```bash
# 运行测试并输出覆盖率
npm run test -- --coverage 2>&1 | tail -50

# 检查覆盖率阈值
# 目标：至少 80%
```

汇报：
- 总测试数：X
- 通过：X
- 失败：X
- 覆盖率：X%

### 阶段 5：安全扫描

```bash
# 扫描密钥泄露
grep -rn "sk-" --include="*.ts" --include="*.js" . 2>/dev/null | head -10
grep -rn "api_key" --include="*.ts" --include="*.js" . 2>/dev/null | head -10

# 扫描 console.log
grep -rn "console.log" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | head -10
```

### 阶段 6：Diff 审查

```bash
# 展示变更内容
git diff --stat
git diff HEAD~1 --name-only
```

逐个审查变更文件，关注：
- 非预期的改动
- 缺失的错误处理
- 潜在的边界情况

## 输出格式

在完成所有阶段后，生成一份验证报告：

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

> 注：报告字段名保留英文，以便与下游脚本/grep 等工具链保持可解析的一致结构。

## 持续模式

对于较长的会话，每 15 分钟或在发生重大变更之后运行一次验证：

```markdown
设置心理检查点：
- 每完成一个函数之后
- 每完成一个组件之后
- 切换到下一个任务之前

运行：/verify
```

## 与 Hooks 的协同

此技能与 PostToolUse hooks 互为补充，但提供更深入的验证。
Hooks 捕捉即时问题；此技能提供系统性复核。
