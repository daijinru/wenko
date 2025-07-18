package main

import (
	"books-vector-api/log"
	"books-vector-api/outbox"
	"books-vector-api/vector"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	// "go.mongodb.org/mongo-driver/bson/primitive"

	"github.com/google/uuid"
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
	OllamaURL string `json:"OllamaURL"`

	ModelProviderURI    string `json:"ModelProviderURI"`
	ModelProviderModel  string `json:"ModelProviderModel"`
	ModelProviderAPIKey string `json:"ModelProviderAPIKey"`

	Collection       string `json:"Collection"`
	ChromaDBURL      string `json:"ChromaDBURL"`
	ChromDBTenants   string `json:"ChromDBTenants"`
	ChromaDBDatabase string `json:"ChromaDBDatabase"`
}

var config Config
var Logger *log.DailyLogger

func init() {
	// 使用相对路径
	Logger = log.New("./logs")

	file, err := os.Open("config.json")
	if err != nil {
		panic(fmt.Sprintf("无法打开配置文件: %v", err))
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&config); err != nil {
		panic(fmt.Sprintf("解析配置文件失败: %v", err))
	}

	outbox.InitModelProvider(config.ModelProviderURI, config.ModelProviderModel, config.ModelProviderAPIKey)
	outbox.Init(Logger)

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
		Name      string            `json:"name"`
		Metadatas map[string]string `json:"metadatas"`
	}{
		Name: config.Collection,
		Metadatas: map[string]string{
			"hnsw:space": "ip", // "cosine" "12" "ip"
		},
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

func addToChromaDB(id string, embedding []float32, texts []WeightedText) (string, error) {
	// fmt.Println("Adding to ChromaDB...", embedding)
	var content string
	for _, text := range texts {
		content += fmt.Sprintf("%s-(weight-assign:%f)-$-$", text.Text, text.Weight)
	}
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
	// fmt.Println("url:", url)
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

func generateAndStore(texts []WeightedText) (string, error) {
	embedding, err := generateWeightedEmbedding(texts)
	if err != nil {
		return "", err
	}

	// id 使用 UUIDv4 生成
	id := strings.ReplaceAll(uuid.New().String(), "-", "")
	// fmt.Println("Adding to ChromaDB...", response)
	id, err = addToChromaDB(id, embedding, texts)
	fmt.Println(id, err)
	if err != nil {
		return "failed to add to chromadb:", err
	}
	return id, nil
}

// 删除记录
func deleteRecord(recordID string) (string, error) {
	// /api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/delete post
	url := fmt.Sprintf("%s/tenants/%s/databases/%s/collections/%s/delete", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase, CollectionId)
	payload := struct {
		IDs []string `json:"ids"`
	}{
		IDs: []string{recordID},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("HTTP request failed with status code %d", resp.StatusCode)
	}
	return recordID, nil
}

type VectorSearchResponse struct {
	IDs        [][]string                 `json:"ids"`
	Embeddings [][]float32                `json:"embeddings"`
	Documents  [][]interface{}            `json:"documents"`
	Metadatas  [][]map[string]interface{} `json:"metadatas"`
	Distances  [][]float32                `json:"distances"`
	Include    []string                   `json:"include"`
}

//	type EmbeddingDoc struct {
//	    ids       string                 `bson:"ids"`
//	    metadatas map[string]interface{} `bson:"metadatas"`
//	}
//
// 向量相似性检索
func vectorSearch(queryVector []float32) ([]map[string]interface{}, error) {
	// url := fmt.Sprintf("%s/tenants/%s/databases/%s/collections/%s/add", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase, CollectionId)
	// 检索 /api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/query post
	url := fmt.Sprintf("%s/tenants/%s/databases/%s/collections/%s/query", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase, CollectionId)
	Logger.Info("向量检索: " + url)
	payload := struct {
		QueryEmbeddings [][]float32 `json:"query_embeddings"`
		NResults        int         `json:"n_results"`
	}{
		QueryEmbeddings: [][]float32{queryVector},
		NResults:        5,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Println("Error:", err)
		return nil, err
	}
	// 打印 resp.body 并格式化
	defer resp.Body.Close()
	// bodyBytes, err := io.ReadAll(resp.Body)
	// if err != nil {
	// 	return nil, err
	// }
	// fmt.Println("Response Body:", string(bodyBytes))
	var response VectorSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, err
	}

	// 如果需要转换为 EmbeddingDoc 切片，可以手动映射
	// 保存最终结果，每个查询对应一组匹配项
	var allResults []map[string]interface{}
	Logger.Info("向量检索结果: " + fmt.Sprintf("%v", response.IDs))
	// 外层遍历：每个查询向量（通常是1个）
	for i := range response.IDs {
		// 内层遍历：每个匹配项
		for j := range response.IDs[i] {
			resultItem := map[string]interface{}{
				"id":       response.IDs[i][j],
				"metadata": response.Metadatas[i][j],
				// 可选：添加距离信息
				// "distance": response.Distances[i][j],
			}
			allResults = append(allResults, resultItem)
		}
	}
	return allResults, nil
}

type VectorGetRessponse struct {
	IDs        []string    `json:"ids"`
	Embeddings [][]float32 `json:"embeddings"`
}

func vectorCompare(texts []WeightedText, id string) (bool, error) {
	// fmt.Println("vectorCompare...", text, id)
	embeddings, err := generateWeightedEmbedding(texts)
	if err != nil {
		return false, err
	}
	// 通过 id 查询向量 /api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/get post
	url := fmt.Sprintf("%s/tenants/%s/databases/%s/collections/%s/get", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase, CollectionId)
	payload := struct {
		IDs     []string `json:"ids"`
		Include []string `json:"include"`
	}{
		IDs:     []string{id},
		Include: []string{"embeddings"},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return false, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return false, err
	}
	// fmt.Println(resp)
	defer resp.Body.Close()
	var response VectorGetRessponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return false, err
	}
	// fmt.Println("response:", response.Embeddings[0])
	compareResults := vector.BatchCompare(embeddings, response.Embeddings[0], 0.99)
	// 将 compareResults 打印为字符串
	// fmt.Println("compareResults:", compareResults)

	return compareResults, nil
}

type DocumentResponse struct {
	IDs       []string                 `json:"ids"`
	Metadatas []map[string]interface{} `json:"metadatas"`
}

func listDocuments(limit int, offset int) (DocumentResponse, error) {
	// 获取列表 /api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/get post
	url := fmt.Sprintf("%s/tenants/%s/databases/%s/collections/%s/get", config.ChromaDBURL, config.ChromDBTenants, config.ChromaDBDatabase, CollectionId)
	// 请求体 limit offset include
	payload := struct {
		Limit   int      `json:"limit"`
		Offset  int      `json:"offset"`
		Include []string `json:"include"`
	}{
		Limit:   limit,
		Offset:  offset,
		Include: []string{"metadatas"},
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return DocumentResponse{}, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return DocumentResponse{}, err
	}
	defer resp.Body.Close()
	var response DocumentResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return DocumentResponse{}, err
	}
	return response, nil
}

func enableCORS(handler http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 允许所有来源跨域
		w.Header().Set("Access-Control-Allow-Origin", "*")
		// 允许的请求方法
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		// 允许的请求头
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		// 跨域预检请求直接返回
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		handler.ServeHTTP(w, r)
	})
}

// HTTP接口
func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("/generate", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "读取请求体失败", http.StatusBadRequest)
			return
		}

		var requestData struct {
			Texts []struct {
				Text   string  `json:"text"`
				Weight float32 `json:"weight"`
			} `json:"texts"`
		}
		if err := json.Unmarshal(body, &requestData); err != nil {
			http.Error(w, "解析请求体失败", http.StatusBadRequest)
			return
		}
		weightedTexts := make([]WeightedText, len(requestData.Texts))
		for i, text := range requestData.Texts {
			weightedTexts[i] = WeightedText{Text: text.Text, Weight: text.Weight}
		}
		Logger.Info("正在存储: " + weightedTexts[0].Text)
		id, err := generateAndStore(weightedTexts)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"id": id})
	})

	mux.HandleFunc("/search", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "读取请求体失败", http.StatusBadRequest)
			return
		}

		var requestData struct {
			Texts []struct {
				Text   string  `json:"text"`
				Weight float32 `json:"weight"`
			} `json:"texts"`
		}
		if err := json.Unmarshal(body, &requestData); err != nil {
			http.Error(w, "解析请求体失败", http.StatusBadRequest)
			return
		}
		if requestData.Texts == nil {
			http.Error(w, "Texts should non empty", http.StatusBadRequest)
			return
		}
		// 将 requestData.Texts 转换为 WeightedText 切片
		weightedTexts := make([]WeightedText, len(requestData.Texts))
		for i, text := range requestData.Texts {
			weightedTexts[i] = WeightedText{Text: text.Text, Weight: text.Weight}
		}
		// 生成文本向量
		Logger.Info("生成文本向量: " + weightedTexts[0].Text)
		vector, err := generateWeightedEmbedding(weightedTexts)
		if err != nil {
			Logger.Error("生成向量失败: " + err.Error())
			http.Error(w, "生成向量失败: "+err.Error(), http.StatusInternalServerError)
			return
		}
		Logger.Info("生成向量成功: " + weightedTexts[0].Text)
		// 执行向量检索
		results, err := vectorSearch(vector)
		// fmt.Printf("results: %v\n", results)
		if err != nil {
			http.Error(w, "检索失败: "+err.Error(), http.StatusInternalServerError)
			return
		}

		returnResults := make([]map[string]interface{}, len(results))
		for i, result := range results {
			content := result["metadata"].(map[string]interface{})["content"]
			returnResults[i] = map[string]interface{}{
				"id":      result["id"],
				"content": content,
			}
		}
		// fmt.Printf("returnResults: %v\n", returnResults)
		// 返回相似内容
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(returnResults)
	})

	mux.HandleFunc("/chat", Chat)

	mux.HandleFunc("/compare", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "读取请求体失败", http.StatusBadRequest)
			return
		}

		var requestData struct {
			Texts []struct {
				Text   string  `json:"text"`
				Weight float32 `json:"weight"`
			} `json:"texts"`
			ID string `json:"id"`
		}
		if err := json.Unmarshal(body, &requestData); err != nil {
			http.Error(w, "解析请求体失败", http.StatusBadRequest)
			return
		}
		weightedTexts := make([]WeightedText, len(requestData.Texts))
		for i, text := range requestData.Texts {
			weightedTexts[i] = WeightedText{Text: text.Text, Weight: text.Weight}
		}
		result, err := vectorCompare(weightedTexts, requestData.ID)
		Logger.Info("比较结果: " + fmt.Sprintf("%v", result))
		if err != nil {
			http.Error(w, "比较失败: "+err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]bool{"result": result})
	})

	mux.HandleFunc("/documents", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "读取请求体失败", http.StatusBadRequest)
			return
		}

		var requestData struct {
			Limit  int `json:"limit"`
			Offset int `json:"offset"`
		}
		if err := json.Unmarshal(body, &requestData); err != nil {
			http.Error(w, "解析请求体失败", http.StatusBadRequest)
			return
		}

		documents, err := listDocuments(requestData.Limit, requestData.Offset)
		if err != nil {
			fmt.Println("获取文档失败:", err)
			http.Error(w, "获取文档失败", http.StatusInternalServerError)
			return
		}

		var allResults []map[string]interface{}

		for i := range documents.IDs {
			resultItem := map[string]interface{}{
				"id":       documents.IDs[i],
				"metadata": documents.Metadatas[i],
			}
			allResults = append(allResults, resultItem)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(allResults)
	})

	mux.HandleFunc("/delete", func(w http.ResponseWriter, r *http.Request) {
		// 从 query 参数取出 id
		id := r.URL.Query().Get("id")
		fmt.Println("删除记录", id)
		recordID, err := deleteRecord(id)
		if err != nil {
			http.Error(w, "删除失败", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		// 返回 { id } 结构体
		json.NewEncoder(w).Encode(map[string]string{"id": recordID})
	})

	// 创建一个 task 接口, post，使用 NewTask 方法
	mux.HandleFunc("/task", outbox.NewTask)
	// 用户回答 PlanningTask answer
	mux.HandleFunc("/planning/task/answer", outbox.PlanningTaskAnswer)
	// 用户中断 PlanningTask
	mux.HandleFunc("/planning/task/interrupt", outbox.InterruptTask)

	// 导出所有文本数据
	mux.HandleFunc("/export", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		fmt.Println("Received request to export all data.")
		err := exportAllData()
		if err != nil {
			fmt.Printf("Error during data export: %v\n", err)
			http.Error(w, fmt.Sprintf("Failed to export data: %v", err), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"message": "Data exported successfully to export_YYYYMMDD.md"})
	})

	// mux.HandleFunc("/import", func(w http.ResponseWriter, r *http.Request) {
	// 	if r.Method != http.MethodPost {
	// 		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	// 		return
	// 	}

	// 	body, err := io.ReadAll(r.Body)
	// 	if err != nil {
	// 		http.Error(w, "读取请求体失败", http.StatusBadRequest)
	// 		return
	// 	}

	// 	var requestData struct {
	// 		Filename string `json:"filename"`
	// 	}
	// 	if err := json.Unmarshal(body, &requestData); err != nil {
	// 		http.Error(w, "解析请求体失败", http.StatusBadRequest)
	// 		return
	// 	}

	// 	if requestData.Filename == "" {
	// 		http.Error(w, "文件名不能为空", http.StatusBadRequest)
	// 		return
	// 	}

	// 	fmt.Printf("收到导入文件请求: %s\n", requestData.Filename)
	// 	err = importData(requestData.Filename) // 调用新的导入函数
	// 	if err != nil {
	// 		fmt.Printf("数据导入失败: %v\n", err)
	// 		http.Error(w, fmt.Sprintf("数据导入失败: %v", err), http.StatusInternalServerError)
	// 		return
	// 	}

	// 	w.Header().Set("Content-Type", "application/json")
	// 	json.NewEncoder(w).Encode(map[string]string{"message": fmt.Sprintf("数据已成功从 %s 导入并添加标记。", requestData.Filename)})
	// })

	handlerWithCORS := enableCORS(mux)

	// 启动服务
	fmt.Println("✅ 启动服务成功 -- Server running on :8080")
	http.ListenAndServe(":8080", handlerWithCORS)
}
