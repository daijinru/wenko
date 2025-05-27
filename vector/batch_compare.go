package vector

import (
	"math"
)

// L2 归一
func normalize(vec []float32) []float32 {
	sum := float32(0.0)
	for _, v := range vec {
		sum += v * v
	}
	norm := float32(math.Sqrt(float64(sum)))
	if norm == 0 {
		return vec
	}
	normalized := make([]float32, len(vec))
	for i, v := range vec {
		normalized[i] = v / norm
	}
	return normalized
}

func cosineSimilarity(a, b []float32) float32 {
	if len(a) != 768 || len(b) != 768 {
		panic("向量维度必须为768")
	}

	var dot float32
	for i := 0; i < 768; i++ {
		dot += a[i] * b[i]
	}
	return dot
}

// 相似度（阈值）计算
func BatchCompare(target []float32, vector []float32, threshold float32) bool {
	targetNorm := normalize(target)
	vecNorm := normalize(vector)

	sim := cosineSimilarity(targetNorm, vecNorm)
	return sim >= threshold
}

// 对 BatchCompare 结果聚合计算（多数投票法）
func AggregateBool(results []bool, param float64) bool {
	if len(results) == 0 {
		return false
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
