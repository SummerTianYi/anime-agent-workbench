# 任务 C：权限层

## 目标
动作请求先过权限引擎：默认拒绝；显式规则放行；注入请求全拒。

## 工作文件
- src/permissions.py：实现 PermissionEngine.evaluate()

## 验收闸门
- g1_permissions 全绿：默认拒绝有证明性测试；两条注入样例（相对路径逃逸、绝对路径）全拒
- 规则命中须返回 rule_id；无规则命中时必须返回 default-deny

## 证据要求
1. run_all --strict ×3
2. 策略矩阵表（tool × origin → decision）
3. 每条拒绝规则对应的测试名
