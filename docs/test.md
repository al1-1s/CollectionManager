# 收藏夹回归测试说明

本文档说明当前维护中的 pytest 回归测试套件，主要覆盖收藏夹相关行为。

## 默认覆盖范围

默认执行会覆盖以下内容：

- 收藏夹的增删改查、合并、重名拒绝，以及关联顺序保持
- 单个和多个收藏夹的 `collection.db` 导出/导入往返验证
- 空收藏夹与包含缺失 hash 的收藏夹导出行为
- 通过现有 service/bootstrap 路径执行单个和多个 `.osz` 导入
- 主窗口与副窗口“添加到收藏夹”的 ViewModel 边界行为
- 收藏夹选择器的单谱面预选中与多目标选择行为

## 运行命令

快速回归测试：

```powershell
.\.venv\Scripts\python -m pytest test/regression -q
```

基于 `test/test_data` 真实夹具的慢速启动/导入回归：

```powershell
.\.venv\Scripts\python -m pytest -o addopts= -m slow test/regression/test_startup_real_fixture_slow.py -q
```

单个测试切片示例：

```powershell
.\.venv\Scripts\python -m pytest test/regression/test_collection_service_regression.py -q
.\.venv\Scripts\python -m pytest test/regression/test_collection_import_export_regression.py -q
```

## 范围边界

默认套件有意不覆盖完整 Qt 拖放交互、真实文件选择对话框交互，以及依赖完整 osu! 数据集的启动/重置流程。这些内容应放在单独的慢速测试或手工检查中。

当前慢速测试夹具位于 `test/test_data/osu` 和 `test/test_data/osz_example`。慢速模块会先把夹具目录复制到临时工作区，再执行启动导入和真实 `.osz` 导入，从而避免修改仓库中保存的原始夹具。
