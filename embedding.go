package main

import (
	"books-vector-api/vector"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
)

// WeightedText 结构体用于容纳文本及其权重
type WeightedText struct {
	Text   string  `json:"text"`
	Weight float32 `json:"weight"`
}

// 独立向量生成函数（复用存储逻辑中的核心部分） -> L2
func generateEmbedding(text string) ([]float32, error) {
	resp, err := http.Post(config.OllamaURL, "application/json",
		bytes.NewBufferString(fmt.Sprintf(`{"model":"nomic-embed-text","prompt":"%s"}`, url.QueryEscape(text))))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var response OllamaResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, err
	}

	return response.Embedding, nil
}

// generateWeightedEmbedding 函数用于将多个文本合并，按既定权重生成向量
func generateWeightedEmbedding(weightedTexts []WeightedText) ([]float32, error) {
	if len(weightedTexts) == 0 {
		return nil, fmt.Errorf("no texts provided for weighted embedding generation")
	}

	var totalEmbedding []float32
	var totalWeight float32

	for _, wt := range weightedTexts {
		// fmt.Println("Generating embedding for text:", wt.Text)
		embedding, err := generateEmbedding(wt.Text)
		if err != nil {
			return nil, fmt.Errorf("failed to generate embedding for text \"%s\": %w", wt.Text, err)
		}

		if totalEmbedding == nil {
			totalEmbedding = make([]float32, len(embedding))
		}

		// 加权累加
		for i, val := range embedding {
			totalEmbedding[i] += val * wt.Weight
		}
		totalWeight += wt.Weight
	}

	if totalWeight == 0 {
		return nil, fmt.Errorf("total weight is zero, cannot generate weighted embedding")
	}

	for i := range totalEmbedding {
		totalEmbedding[i] /= totalWeight
	}

	return vector.Normalize(totalEmbedding), nil
}
