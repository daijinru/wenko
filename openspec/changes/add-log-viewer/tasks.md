# Tasks: Add Log Viewer

## 1. Backend API

- [x] 1.1 在 `main.py` 添加日志文件列表 API (`GET /api/logs`)
- [x] 1.2 在 `main.py` 添加日志内容读取 API (`GET /api/logs/{date}`)
- [x] 1.3 添加分页支持（offset/limit）处理大日志文件
- [x] 1.4 添加 Pydantic 响应模型定义

## 2. Frontend Hook

- [x] 2.1 创建 `use-logs.ts` hook 管理日志数据状态
- [x] 2.2 实现日志文件列表获取功能
- [x] 2.3 实现日志内容加载功能
- [x] 2.4 实现分页/懒加载支持

## 3. Frontend Components

- [x] 3.1 创建 `logs-tab.tsx` 主组件
- [x] 3.2 创建日期选择器组件（使用已有的日志文件列表）
- [x] 3.3 创建日志显示区域组件（支持等宽字体和语法着色）
- [x] 3.4 实现顺序切换控制（正序/倒序）
- [x] 3.5 实现关键字输入和高亮功能
- [x] 3.6 实现日志级别着色（INFO/WARN/ERROR）

## 4. Integration

- [x] 4.1 在 `App.tsx` 中集成日志 Tab
- [x] 4.2 添加类型定义到 `types/api.ts`

## 5. Validation

- [x] 5.1 测试不同日期的日志加载
- [x] 5.2 测试大文件分页加载
- [x] 5.3 测试关键字高亮功能
- [x] 5.4 测试顺序切换功能
