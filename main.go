package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"go.mongodb.org/mongo-driver/bson"

	// "go.mongodb.org/mongo-driver/bson/primitive"

	"github.com/google/uuid"
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
	OllamaURL        string `json:"OllamaURL"`
	MongoURI         string `json:"MongoURI"`
	DatabaseName     string `json:"DatabaseName"`
	Collection       string `json:"Collection"`
	OpenRouterApiKey string `json:"OpenRouterApiKey"`
	ChromaDBURL      string `json:"ChromaDBURL"`
	ChromDBTenants   string `json:"ChromDBTenants"`
	ChromaDBDatabase string `json:"ChromaDBDatabase"`
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

	// 检查租户 addTenant 是否存在
	fmt.Println("🌍正在添加租户...")
	if err := addTenants(); err != nil {
		panic(fmt.Sprintf("添加租户失败: %v", err))
	}
	fmt.Println("🌍正在创建数据库...")
	if err := addDatabases(); err != nil {
		panic(fmt.Sprintf("创建数据库失败: %v", err))
	}
	fmt.Println("🌍正在添加Embedding集合...")
	if err := addEmbeddingCollection(); err != nil {
		panic(fmt.Sprintf("添加Embedding集合失败: %v", err))
	}
}

// 定义数据结构
type EmbeddingDoc struct {
	ID        string    `bson:"_id,omitempty"`
	Content   string    `bson:"content"`
	Article   string    `bson:"article"`
	Vector    []float32 `bson:"vector"`
	CreatedAt time.Time `bson:"created_at"`
}

// Ollama响应结构
type OllamaResponse struct {
	Embedding []float32 `json:"embedding"`
}

func addTenants() error {
	// 先检查租户是否存在 /api/v2/tenants/{tenant_name} get
	existURL := fmt.Sprintf("%s/tenants/%s", config.ChromaDBURL, config.ChromDBTenants)
	existsResp, err := http.Get(existURL)
	if err != nil {
		return fmt.Errorf("failed to check tenant: %v", err)
	}
	if existsResp.StatusCode == http.StatusOK {
		// 存在则返回
		fmt.Println("租户已存在")
		return nil
	}
	defer existsResp.Body.Close()

	// 创建租户 /api/v2/tenants post
	tenantsURL := fmt.Sprintf("%s/tenants", config.ChromaDBURL)
	payload := struct {
		Name string `json:"name"`
	}{
		Name: config.ChromDBTenants,
	}
	body, _ := json.Marshal(payload)
	resp, err := http.Post(tenantsURL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create tenant: %v", err)
	}
	defer resp.Body.Close()
	fmt.Println("创建租户成功")
	return nil
}

func addDatabases() error {
	// 检查数据库是否存在 /api/v2/tenants/{tenant}/databases/{database} get
	existsURL := fmt.Sprintf("%s/tenants/%s/databases/%s", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase)
	existsResp, err := http.Get(existsURL)
	if err != nil {
		return fmt.Errorf("failed to check database existence: %v", err)
	}
	defer existsResp.Body.Close()
	if existsResp.StatusCode == http.StatusOK {
		fmt.Println("数据库已存在")
		return nil
	}
	// 创建数据库 /api/v2/tenants/{tenant}/databases post
	createURL := fmt.Sprintf("%s/tenants/%s/databases", config.ChromaDBURL, config.ChromDBTenants)
	payload := struct {
		Name string `json:"name"`
	}{
		Name: config.ChromaDBDatabase,
	}
	body, _ := json.Marshal(payload)
	resp, err := http.Post(createURL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create database: %v", err)
	}
	defer resp.Body.Close()
	fmt.Println("创建数据库成功")
	return nil
}

var CollectionId string

func addEmbeddingCollection() error {
	// 检查用于 embedding 的集合是否存在 /api/v2/tenants/{tenant}/databases/{database}/collections get
	existsURL := fmt.Sprintf("%s/tenants/%s/databases/%s/collections", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase)
	existsResp, err := http.Get(existsURL)
	if err != nil {
		return fmt.Errorf("failed to check collection existence: %v", err)
	}
	defer existsResp.Body.Close()
	if existsResp.StatusCode == http.StatusOK {
		// 遍历 existsResp.Body，匹配 name == config.Collection 的集合，将其 id 赋值到 CollectionId
		var existsRespBody []struct {
			Name string `json:"name"`
			ID   string `json:"id"`
		}
		json.NewDecoder(existsResp.Body).Decode(&existsRespBody)
		for _, collection := range existsRespBody {
			if collection.Name == config.Collection {
				CollectionId = collection.ID
			}
		}
		if CollectionId != "" {
			fmt.Println("Embedding 集合已存在: ", CollectionId)
			return nil
		}
	}
	// 创建用于 embedding 的集合 /api/v2/tenants/{tenant}/databases/{database}/collections post
	createURL := fmt.Sprintf("%s/tenants/%s/databases/%s/collections", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase)
	payload := struct {
		Name string `json:"name"`
	}{
		Name: config.Collection,
	}
	body, _ := json.Marshal(payload)
	resp, err := http.Post(createURL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create collection: %v", err)
	}
	defer resp.Body.Close()
	// 将 resp.Body 的 id 赋值到 CreationId
	var respBody struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&respBody); err != nil {
		return fmt.Errorf("failed to decode response body: %v", err)
	}
	CollectionId = respBody.ID
	fmt.Println("Collection created: ", CollectionId)
	return nil
}

func addToChromaDB(id string, embedding []float32, content string) (string, error) {
	// 先查询 collectionId

	// 构造请求体
	payload := struct {
		Ids        []string            `json:"ids"`
		Embeddings [][]float32         `json:"embeddings"`
		Metadatas  []map[string]string `json:"metadatas,omitempty"`
	}{
		Ids:        []string{id},
		Embeddings: [][]float32{embedding},
		Metadatas: []map[string]string{
			{"content": content},
		},
	}
	// fmt.Println("payload:", payload)
	body, _ := json.Marshal(payload)
	// /api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/add post
	url := fmt.Sprintf("%s/tenants/%s/databases/%s/collections/%s/add", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase, CollectionId)
	fmt.Println("url:", url)
	// url := fmt.Sprintf("%s/collections/%s/add", config.ChromaDBURL, collectionName)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Println("Error:", err)
		return "", err
	}
	defer resp.Body.Close()
	fmt.Println("Response Status:", resp.Status)
	// 如果 resp.StatusCode 等于 201 或者 200 返回 id
	if resp.StatusCode == http.StatusCreated || resp.StatusCode == http.StatusOK {
		return id, nil
	}
	bodyBytes, _ := io.ReadAll(resp.Body)
	return "", fmt.Errorf("failed to add to chromadb: %s", string(bodyBytes))
}

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

	// id 使用 UUIDv4 生成
	id := strings.ReplaceAll(uuid.New().String(), "-", "")

	id, err = addToChromaDB(id, response.Embedding, text)
	fmt.Println(id, err)
	if err != nil {
		return "failed to add to chromadb:", err
	}
	return id, nil
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

	http.HandleFunc("/chat", Chat)

	// 启动服务
	fmt.Println("Server running on :8080")
	http.ListenAndServe(":8080", nil)
}
