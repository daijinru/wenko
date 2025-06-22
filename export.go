package main

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

func exportAllData() error {
	today := time.Now().Format("20060102") // YYYYMMDD format
	filename := fmt.Sprintf("export_%s.md", today)

	exportPath := filepath.Join(".", filename)

	file, err := os.Create(exportPath)
	if err != nil {
		return fmt.Errorf("failed to create export file %s: %w", exportPath, err)
	}
	defer file.Close()

	const limit = 100
	offset := 0

	fmt.Printf("Starting data export to %s...\n", exportPath)

	for {
		documents, err := listDocuments(limit, offset)
		if err != nil {
			return fmt.Errorf("failed to list documents from ChromaDB at offset %d: %w", offset, err)
		}

		if len(documents.IDs) == 0 {
			break
		}

		for _, metadata := range documents.Metadatas {
			if content, ok := metadata["content"]; ok {
				if contentStr, isString := content.(string); isString {
					_, err := file.WriteString(contentStr + "\n")
					if err != nil {
						return fmt.Errorf("failed to write content to file: %w", err)
					}
				} else {
					fmt.Printf("Warning: 'content' in metadata is not a string, skipping: %v\n", content)
				}
			} else {
				fmt.Println("Warning: 'content' key not found in metadata for a document.")
			}
		}

		offset += len(documents.IDs)

		if len(documents.IDs) < limit {
			break
		}
	}

	fmt.Printf("Data export completed successfully to %s.\n", exportPath)
	return nil
}

// func importData(filename string) error {
// 	filePath := filepath.Join(".", filename) // 约定文件在项目根目录

// 	// 1. 读取并处理文件内容
// 	file, err := os.Open(filePath)
// 	if err != nil {
// 		return fmt.Errorf("无法打开文件 %s: %w", filePath, err)
// 	}
// 	defer file.Close() // 确保文件在处理后关闭

// 	scanner := bufio.NewScanner(file)
// 	lineNum := 0
// 	for scanner.Scan() {
// 		lineNum++
// 		content := strings.TrimSpace(scanner.Text())
// 		if content == "" {
// 			continue // 跳过空行
// 		}

// 		fmt.Printf("正在导入第 %d 行: %s\n", lineNum, content)
// 		_, err := generateAndStore(content)
// 		if err != nil {
// 			// 导入失败则立即返回错误
// 			return fmt.Errorf("为第 %d 行内容生成并存储失败: %w", lineNum, err)
// 		}
// 	}

// 	if err := scanner.Err(); err != nil {
// 		return fmt.Errorf("读取文件 %s 时出错: %w", filePath, err)
// 	}

// 	// 2. 在文件第一行添加 "imported_当前日期" 标记
// 	today := time.Now().Format("20060102") // YYYYMMDD 格式
// 	importTag := fmt.Sprintf("imported_%s\n", today)

// 	// 创建一个临时文件
// 	tempFile, err := os.CreateTemp(".", filename+".tmp") // 在当前目录创建临时文件
// 	if err != nil {
// 		return fmt.Errorf("无法创建临时文件: %w", err)
// 	}
// 	defer os.Remove(tempFile.Name()) // 确保在函数退出时（或发生错误时）清理临时文件
// 	defer tempFile.Close()

// 	// 将导入标记写入临时文件
// 	_, err = tempFile.WriteString(importTag)
// 	if err != nil {
// 		return fmt.Errorf("无法将导入标记写入临时文件: %w", err)
// 	}

// 	// 重新打开原始文件以复制其内容
// 	originalFile, err := os.Open(filePath)
// 	if err != nil {
// 		return fmt.Errorf("无法重新打开原始文件 %s 进行复制: %w", filePath, err)
// 	}
// 	defer originalFile.Close()

// 	// 将原始文件内容复制到临时文件
// 	_, err = io.Copy(tempFile, originalFile)
// 	if err != nil {
// 		return fmt.Errorf("无法将原始文件内容复制到临时文件: %w", err)
// 	}

// 	// 在重命名之前关闭两个文件
// 	originalFile.Close()
// 	tempFile.Close()

// 	// 将临时文件重命名为原始文件，覆盖原文件
// 	err = os.Rename(tempFile.Name(), filePath)
// 	if err != nil {
// 		return fmt.Errorf("无法将临时文件重命名为原始文件: %w", err)
// 	}

// 	fmt.Printf("数据已成功从 %s 导入并添加标记。\n", filePath)
// 	return nil
// }
