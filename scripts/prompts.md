```bash
假定有若干文案片段 ，每个片段都有 id 和 text，但是并不指定其中的文案片段关系，
构建一个层级脉络关系，转出数据结构为 JSON 数据：
const [cards, setCards] = useState<CardData[]>([
  { id: "1", content: "项目概述\n\n这是一个创新的写作工具项目，旨在提供更好的内容组织方式。", level: 0 },
  { id: "2", content: "核心功能\n\n• 多列布局\n• 卡片式编辑\n• 层级管理", level: 0 },
  { id: "3", content: "技术架构\n\n前端使用 React + TypeScript\n后端使用 Node.js", level: 0 },
  { id: "4", content: "用户界面设计\n\n简洁直观的设计理念", parentId: "1", level: 1 },
  { id: "5", content: "数据存储方案\n\n本地存储 + 云端同步", parentId: "1", level: 1 },
  { id: "6", content: "响应式布局\n\n适配各种屏幕尺寸", parentId: "4", level: 2 },
  { id: "7", content: "交互设计\n\n拖拽、快捷键支持", parentId: "4", level: 2 },
])，
给出生成该数据结构的提示词
```
