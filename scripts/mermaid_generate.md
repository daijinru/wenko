使用 mermaid flowchat TB 描述，参考这段代码：
```bash
flowchart TB
  A("CO2 cycle") --> B("Photosynthesis")
  B --> E("Organic carbon") & n3("Decay organism")
  n1("Sunlight") --> B
  n3 --> nb("Dead organisms and waste product")
  nb --> n5("Root respiration") & ng("Fossil fuels")
  n5 --> nl("Factory emission")
  nl --> A
  nn("Animal respiration") --> A
  style A stroke:#000000,fill:#E1F0D4 
  style B stroke:#000000,fill:#C3EFE0 
  style E stroke:#000000,fill:#F6ACD8
  style n3 stroke:#000000,fill:#C2C4B3 
  style n1 stroke:#000000,fill:#F2F7D2 
  style nb stroke:#000000,fill:#E9A3B2 
  style n5 stroke:#000000,fill:#DBCDF8 
  style ng stroke:#000000,fill:#BEF6AC 
  style nl stroke:#000000,fill:#A3E9CC 
  style nn stroke:#000000,fill:#D4EFF0
```
这里是需要被转换到代码的内容：
1. Obsidian Plugin
1.1 提交Text Highlighter 到 Server
1.2 Text Embedding
1.3 存储到 Atlas MongoDB
2. Chrome Extension
2.1 提交 Text Highlighter 到 Server
2.2 Text Embedding
2.3 Vector Search 返回结果
2.4 比对结果，不同的话存储该 Text Embedding 到 Atlas MongoDB
