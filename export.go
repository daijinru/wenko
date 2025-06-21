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
