package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

const (
	OllamaURL    = "http://localhost:11434/api/embeddings"
	MongoURI     = "mongodb://admin:admin123@localhost:27017"
	DatabaseName = "vector_db"
	Collection   = "embeddings"
)

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
	resp, err := http.Post(OllamaURL, "application/json",
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
	client, err := mongo.Connect(context.TODO(), options.Client().ApplyURI(MongoURI))
	if err != nil {
		return "", err
	}
	defer client.Disconnect(context.TODO())

	collection := client.Database(DatabaseName).Collection(Collection)
	doc := EmbeddingDoc{
		Content:   text,
		Vector:    response.Embedding,
		CreatedAt: time.Now(),
	}

	result, err := collection.InsertOne(context.TODO(), doc)
	return result.InsertedID.(primitive.ObjectID).Hex(), err
}

// 向量相似性检索
// func vectorSearch(queryVector []float32) ([]EmbeddingDoc, error) {
// 	client, err := mongo.Connect(context.TODO(), options.Client().ApplyURI(MongoURI))
// 	if err != nil {
// 		return nil, err
// 	}
// 	defer client.Disconnect(context.TODO())

// 	// 构建向量搜索管道
// 	pipeline := mongo.Pipeline{
// 		{{"$vectorSearch", bson.D{
// 			{"queryVector", queryVector},
// 			{"path", "vector"},
// 			{"numCandidates", 50},
// 			{"limit", 5},
// 			{"index", "vector_index"},
// 		}}},
// 	}

// 	cursor, err := client.Database(DatabaseName).Collection(Collection).Aggregate(context.TODO(), pipeline)
// 	if err != nil {
// 		return nil, err
// 	}

// 	var results []EmbeddingDoc
// 	if err = cursor.All(context.TODO(), &results); err != nil {
// 		return nil, err
// 	}
// 	return results, nil
// }

// HTTP接口
func main() {
	http.HandleFunc("/generate", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		id, err := generateAndStore(string(body))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(map[string]string{"id": id})
	})

	// http.HandleFunc("/search", func(w http.ResponseWriter, r *http.Request) {
	// 	var vector []float32
	// 	if err := json.NewDecoder(r.Body).Decode(&vector); err != nil {
	// 		http.Error(w, err.Error(), http.StatusBadRequest)
	// 		return
	// 	}
	// 	results, err := vectorSearch(vector)
	// 	if err != nil {
	// 		http.Error(w, err.Error(), http.StatusInternalServerError)
	// 		return
	// 	}
	// 	json.NewEncoder(w).Encode(results)
	// })

	// 启动服务
	fmt.Println("Server running on :8080")
	http.ListenAndServe(":8080", nil)
}
