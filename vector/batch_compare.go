package vector

import (
	"math"
	"sync"
)

// 向量归一化（L2归一化）
func normalize(vec []float64) []float64 {
	sum := 0.0
	for _, v := range vec {
		sum += v * v
	}
	norm := math.Sqrt(sum)
	if norm == 0 {
		return vec
	}
	normalized := make([]float64, len(vec))
	for i, v := range vec {
		normalized[i] = v / norm
	}
	return normalized
}

// 余弦相似度计算（优化版）
func cosineSimilarity(a, b []float64) float64 {
	if len(a) != 768 || len(b) != 768 {
		panic("向量维度必须为768")
	}

	dot := 0.0
	for i := 0; i < 768; i++ {
		dot += a[i] * b[i]
	}
	return dot // 已归一化无需再除以模长
}

// 带阈值判断的批量计算
func BatchCompare(target []float64, vectors [][]float64, threshold float64) []bool {
	targetNorm := normalize(target)
	results := make([]bool, len(vectors))

	// 并行计算（利用Go协程）
	var wg sync.WaitGroup
	wg.Add(len(vectors))

	for i, vec := range vectors {
		go func(idx int, v []float64) {
			defer wg.Done()
			vecNorm := normalize(v)
			sim := cosineSimilarity(targetNorm, vecNorm)
			results[idx] = sim >= threshold
		}(i, vec)
	}
	wg.Wait()
	return results
}

// 对 BatchCompare 结果聚合计算（多数投票法）
func AggregateBool(results []bool, param float64) bool {
	if len(results) == 0 {
		return false // 空集合处理
	}

	trueCount := 0
	for _, v := range results {
		if v {
			trueCount++
		}
	}

	ratio := float64(trueCount) / float64(len(results))
	return ratio >= param
}
