package outbox

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

var (
	globalSession  *Session
	FlusherWriter  http.Flusher
	ResponseWriter http.ResponseWriter

	id int = 0 // 初始化 0

	OpenRouterApiKey string
)

func InitGlobalSession() {
	globalSession = NewSession()
}

func InitApiKey(apiKey string) {
	OpenRouterApiKey = apiKey
}

type OutMessage struct {
	Type     string `json:"type"`
	Payload  string `json:"payload"`
	ActionID string `json:"actionID"`
}

func GenerateUUID() string {
	u := make([]byte, 16)
	_, err := rand.Read(u)
	if err != nil {
		return ""
	}
	// 设置版本 (4) 和变体 (RFC4122)
	u[6] = (u[6] & 0x0f) | 0x40
	u[8] = (u[8] & 0x3f) | 0x80

	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		u[0:4],
		u[4:6],
		u[6:8],
		u[8:10],
		u[10:16])
}

func waitUntil(timeout time.Duration, codition func() bool) {
	start := time.Now()
	for {
		fmt.Println("等待中...")
		if codition() {
			return
		}
		if time.Since(start) > timeout {
			return
		}
		time.Sleep(1000 * time.Millisecond)
	}
}

func PrintOut(eventType string, data string) {
	fmt.Fprintf(ResponseWriter, "id: %d\n", id)
	fmt.Fprintf(ResponseWriter, "event: %s\n", eventType)
	fmt.Fprintf(ResponseWriter, "data: %s\n\n", data)
	FlusherWriter.Flush()
	id++
}

type StopReason struct {
	Type    string `json:"type"`
	Payload string `json:"payload"`
}

func NewTask(w http.ResponseWriter, r *http.Request) {

	fmt.Println("创建新任务...")
	id = 0 // 重置 id
	// 从 body 中读取请求体
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "读取请求体失败", http.StatusBadRequest)
	}
	// 解析请求体，取出 text
	var ChatRequest struct {
		Text string `json:"text"`
	}
	if err := json.Unmarshal(body, &ChatRequest); err != nil {
		http.Error(w, "解析请求体失败", http.StatusBadRequest)
	}
	// 每个新任务都覆盖全局会话，暂时支持单任务
	ResponseWriter = w
	// 添加 text/event-stream 响应头
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	flusher, ok := w.(http.Flusher)
	FlusherWriter = flusher
	if !ok {
		http.Error(w, "Streaming 不支持", http.StatusInternalServerError)
	}

	data := OutMessage{
		Type:     "text",
		Payload:  "连接成功，请稍后",
		ActionID: "",
	}
	dataBytes, _ := json.Marshal(data)
	PrintOut("200", string(dataBytes))

	maxOuterLoop := 3 // 外层最大循环次数
	currentLoop := 0  // 当前循环计数器（可被重置）

	for {
		if currentLoop >= maxOuterLoop {
			data := OutMessage{
				Type:     "text",
				Payload:  "任务中断: 最大循环数",
				ActionID: "",
			}
			dataBytes, _ := json.Marshal(data)
			PrintOut("200", string(dataBytes))
			break
		}
		recursivePlanningTask(ChatRequest.Text)
		currentLoop++
	}
}

type OpenRouterResponse struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
	} `json:"choices"`
}

func recursivePlanningTask(text string) bool {
	modelRequestBody, _ := json.Marshal(map[string]interface{}{
		"model": "qwen/qwen3-32b:free",
		// 创建 system 和 user 角色的消息
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": InteractivePlanningSystemPrompt,
			},
			{
				"role":    "user",
				"content": text,
			},
		},
		// "stream": true,
	})
	// Planning Task: 请求 openrouter 并传入 InteractivePlanningSystemPrompt
	// 将返回的内容写入会话
	req, _ := http.NewRequest("POST", "https://openrouter.ai/api/v1/chat/completions", bytes.NewBuffer(modelRequestBody))
	req.Header.Set("Authorization", "Bearer "+OpenRouterApiKey)
	req.Header.Set("Content-Type", "application/json")

	// 发送请求
	// 将返回的内容写入会话
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(ResponseWriter, "调用大模型失败: "+err.Error(), http.StatusInternalServerError)
	}
	defer resp.Body.Close()

	// 流式返回
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		data := OutMessage{
			Type:     "text",
			Payload:  line,
			ActionID: "",
		}
		dataBytes, _ := json.Marshal(data)
		PrintOut("200", string(dataBytes))
		// 			}
		// 		}
		// 	}
		// }
	}

	// 添加一个 ask 消息
	actionID := GenerateUUID()
	askMessage := MessageType{
		Type: "ask",
		Payload: PayloadType{
			Content: "请问你有什么问题吗？",
			Meta: map[string]interface{}{
				"answer": false,
				"reason": "",
			},
		},
		ActionID: actionID,
	}

	//  发送 askMessage
	data := OutMessage{
		Type:     "ask",
		Payload:  askMessage.Payload.Content,
		ActionID: actionID,
	}
	dataBytes, _ := json.Marshal(data)
	PrintOut("200", string(dataBytes))
	globalSession.AddEntry("ask", askMessage)

	lastEntry := MessageType{}
	waitUntil(180*time.Second, func() bool {
		entries, exists := globalSession.GetEntries("ask")
		if exists {
			// 取出最后一条数据
			lastEntry = entries[len(entries)-1]
			// actionID 必须对上
			if actionID != lastEntry.ActionID {
				return false
			}
			// 取出 Payload 中的 Meta 中的 answer，如果是 false，返回 false，否则返回 true
			if lastEntry.Payload.Meta["answer"] == false {
				// if lastEntry.Payload.Meta["answer"] == "" {
				return false
			} else {
				// 只有满足 answer 为 true 才能返回 true
				return true
			}
		}
		return false
	})
	// TODO 如果 lastEntry.Payload.Meta["answer"] 为 true，但是 reason 为空，则停止循环，否则继续循环
	if lastEntry.Payload.Meta["answer"] == true && lastEntry.Payload.Meta["reason"] == "" {
		return true
	} else {
		text := lastEntry.Payload.Meta["reason"].(string)
		return recursivePlanningTask(text)
	}
}

func PlanningTaskAnswer(w http.ResponseWriter, r *http.Request) {
	// 从 body 中读取请求体
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "读取请求体失败", http.StatusBadRequest)
		return
	}
	// 解析请求体，取出 text
	var ChatRequest struct {
		Text     string `json:"text"`
		ActionID string `json:"actionID"`
	}
	if err := json.Unmarshal(body, &ChatRequest); err != nil {
		http.Error(w, "解析请求体失败", http.StatusBadRequest)
		return
	}

	entries, _ := globalSession.GetEntries("ask")
	// fmt.Println("entries: ", entries)
	if (entries == nil) || (len(entries) == 0) {
		http.Error(w, "没有找到相应的 ask 消息", http.StatusBadRequest)
	} else {
		lastEntry := entries[len(entries)-1]

		askMessage := MessageType{
			Type: "ask",
			Payload: PayloadType{
				Content: lastEntry.Payload.Content,
				Meta: map[string]interface{}{
					"answer": true,
					"reason": ChatRequest.Text,
				},
			},
			ActionID: ChatRequest.ActionID,
		}
		globalSession.AddEntry("ask", askMessage)
	}
}

// 客户端发起中断信号
func InterruptTask(w http.ResponseWriter, r *http.Request) {
	// 从 body 中读取请求体
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "读取请求体失败", http.StatusBadRequest)
	}
	// 解析请求体，取出 text
	var ChatRequest struct {
		Text     string `json:"text"`
		ActionID string `json:"actionID"`
	}
	if err := json.Unmarshal(body, &ChatRequest); err != nil {
		http.Error(w, "解析请求体失败", http.StatusBadRequest)
	}

	entries, _ := globalSession.GetEntries("ask")
	lastEntry := entries[len(entries)-1]

	askMessage := MessageType{
		Type: "ask",
		Payload: PayloadType{
			Content: lastEntry.Payload.Content,
			Meta: map[string]interface{}{
				"answer": true,
				"reason": "",
			},
		},
		ActionID: ChatRequest.ActionID,
	}
	globalSession.AddEntry("ask", askMessage)
}
