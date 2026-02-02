# Design: Log Viewer

## Context

Wenko 后端使用 Python logging 模块，日志文件按日期命名存储在 `workflow/logs/` 目录下。日志格式为：
```
2026-02-02 15:23:07,349 - logger - INFO - Logging initialized...
```

需要在 Electron 面板提供日志查看功能，支持日期筛选、顺序切换和关键字高亮。

## Goals / Non-Goals

**Goals:**
- 在 Electron 面板添加日志查看 Tab
- 支持按日期选择查看不同日志文件
- 支持正序/倒序显示日志
- 支持关键字高亮
- 日志级别可视化区分（INFO/WARN/ERROR 使用不同颜色）

**Non-Goals:**
- 实时日志流（WebSocket）- 可作为后续增强
- 日志搜索/过滤 - 当前仅做高亮
- 日志导出功能
- 跨多日期搜索

## Decisions

### 1. API 设计

采用 RESTful 风格：

```
GET /api/logs
- 返回可用日志文件列表（按日期降序）
- Response: { files: [{ date: "2026-02-02", size: 27752 }, ...] }

GET /api/logs/{date}?offset=0&limit=500&order=desc
- 返回指定日期日志内容
- 支持分页（默认 limit=500 行）
- 支持顺序控制（asc/desc）
- Response: { lines: [...], total: 1234, has_more: true }
```

### 2. 前端架构

```
logs/
├── logs-tab.tsx        # 主 Tab 容器
├── log-controls.tsx    # 日期选择、顺序切换、关键字输入
├── log-viewer.tsx      # 日志显示区域
└── index.ts            # 导出入口
```

### 3. 关键字高亮实现

- 在前端渲染时进行文本匹配和高亮
- 使用 `<mark>` 标签或自定义样式包裹匹配文本
- 支持大小写不敏感匹配
- 不使用正则表达式（避免用户输入特殊字符导致问题）

### 4. 日志级别着色

解析日志行中的级别标识，应用不同颜色：
- INFO: 灰色/默认
- WARNING/WARN: 橙色
- ERROR: 红色
- DEBUG: 蓝色

### 5. 性能考量

- 使用分页加载避免一次性加载大文件
- 默认显示最新 500 行（倒序）
- 前端使用虚拟滚动（如日志量大）或简单分页

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 大日志文件加载慢 | 使用分页，默认只加载 500 行 |
| 日志文件不存在 | API 返回 404，前端显示友好提示 |
| 高亮关键字性能 | 仅在当前可见行做高亮处理 |

## Open Questions

1. 是否需要支持多关键字高亮？（当前设计为单关键字）
2. 是否需要自动刷新功能？（当前设计为手动刷新）
