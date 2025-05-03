package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// local config.json >>>
//
//	{
//	  "OllamaURL": "http://localhost:11434/api/embeddings",
//	  "MongoURI": "mongodb+srv://<username>:<password>@wenku-vector.gsmjtbg.mongodb.net/?retryWrites=true&w=majority&appName=wenku-vector",
//	  "DatabaseName": "vector_db",
//	  "Collection": "embeddings"
//	}
type Config struct {
	OllamaURL    string `json:"OllamaURL"`
	MongoURI     string `json:"MongoURI"`
	DatabaseName string `json:"DatabaseName"`
	Collection   string `json:"Collection"`
}

var config Config

func init() {
	file, err := os.Open("config.json")
	if err != nil {
		panic(fmt.Sprintf("无法打开配置文件: %v", err))
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&config); err != nil {
		panic(fmt.Sprintf("解析配置文件失败: %v", err))
	}
}

// 定义数据结构
type EmbeddingDoc struct {
	ID        string    `bson:"_id,omitempty"`
	Content   string    `bson:"content"`
	Vector    []float32 `bson:"vector"`
	CreatedAt time.Time `bson:"created_at"`
}

// Ollama响应结构
type OllamaResponse struct {
	Embedding []float32 `json:"embedding"`
}

// 生成向量并存储
func generateAndStore(text string) (string, error) {
	// 调用Ollama API
	resp, err := http.Post(config.OllamaURL, "application/json",
		bytes.NewBufferString(fmt.Sprintf(`{"model":"nomic-embed-text","prompt":"%s"}`, text)))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var response OllamaResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return "", err
	}

	// 连接MongoDB
	client, err := mongo.Connect(context.TODO(), options.Client().ApplyURI(config.MongoURI))
	if err != nil {
		return "", err
	}
	defer client.Disconnect(context.TODO())

	collection := client.Database(config.DatabaseName).Collection(config.Collection)
	doc := EmbeddingDoc{
		Content:   text,
		Vector:    response.Embedding,
		CreatedAt: time.Now(),
	}

	result, err := collection.InsertOne(context.TODO(), doc)
	return result.InsertedID.(primitive.ObjectID).Hex(), err
}

// 独立向量生成函数（复用存储逻辑中的核心部分）
func generateEmbedding(text string) ([]float32, error) {
	resp, err := http.Post(config.OllamaURL, "application/json",
		bytes.NewBufferString(fmt.Sprintf(`{"model":"nomic-embed-text","prompt":"%s"}`, text)))
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

// 向量相似性检索
func vectorSearch(queryVector []float32) ([]EmbeddingDoc, error) {
	// 打印 queryVectr
	// fmt.Printf("queryVector: %v\n", queryVector)
	client, err := mongo.Connect(context.TODO(), options.Client().ApplyURI(config.MongoURI))
	if err != nil {
		return nil, err
	}
	defer client.Disconnect(context.TODO())

	// 向量近似搜索，提前在 Atlas Search 创建索引 numCandidates 768 默认 cosine
	pipeline := mongo.Pipeline{
		{{
			Key: "$vectorSearch",
			Value: bson.D{
				{Key: "queryVector", Value: queryVector},
				{Key: "path", Value: "vector"},
				{Key: "numCandidates", Value: 768},
				{Key: "limit", Value: 5},
				{Key: "index", Value: "vector_index"},
			},
		}},
	}

	cursor, err := client.Database(config.DatabaseName).Collection(config.Collection).Aggregate(context.TODO(), pipeline)
	if err != nil {
		return nil, err
	}

	var results []EmbeddingDoc
	if err = cursor.All(context.TODO(), &results); err != nil {
		return nil, err
	}
	return results, nil
}

// HTTP接口
func main() {
	http.HandleFunc("/generate", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "读取请求体失败", http.StatusBadRequest)
			return
		}

		var requestData struct {
			Text string `json:"text"`
		}
		if err := json.Unmarshal(body, &requestData); err != nil {
			http.Error(w, "解析请求体失败", http.StatusBadRequest)
			return
		}

		id, err := generateAndStore(requestData.Text)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"id": id})
	})

	http.HandleFunc("/search", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "读取请求体失败", http.StatusBadRequest)
			return
		}

		var requestData struct {
			Text string `json:"text"`
		}
		if err := json.Unmarshal(body, &requestData); err != nil {
			http.Error(w, "解析请求体失败", http.StatusBadRequest)
			return
		}

		text := requestData.Text
		fmt.Printf("search text: %s\n", text)
		// 生成文本向量
		vector, err := generateEmbedding(text)
		if err != nil {
			http.Error(w, "生成向量失败: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// 执行向量检索
		results, err := vectorSearch(vector)
		// fmt.Printf("results: %v\n", results)
		if err != nil {
			http.Error(w, "检索失败: "+err.Error(), http.StatusInternalServerError)
			return
		}

		returnResults := make([]map[string]string, len(results))
		for i, result := range results {
			returnResults[i] = map[string]string{
				"id":      result.ID,
				"content": result.Content,
			}
		}
		fmt.Printf("returnResults: %v\n", returnResults)
		// 返回相似内容
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(returnResults)
	})

	// 启动服务
	fmt.Println("Server running on :8080")
	http.ListenAndServe(":8080", nil)
}
