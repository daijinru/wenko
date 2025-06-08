package outbox

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

var (
	// globalSession  *Session
	FlusherWriter  http.Flusher
	ResponseWriter http.ResponseWriter

	id int = 0 // 初始化 0

	OpenRouterApiKey string
)

func InitApiKey(apiKey string) {
	OpenRouterApiKey = apiKey
}

type OutMessage struct {
	Type     string `json:"type"`
	Payload  string `json:"payload"`
	ActionID string `json:"actionID"`
}

func Init() {
	// globalSession = NewSession()
}

func PrintOut(eventType string, data string) {
	fmt.Fprintf(ResponseWriter, "id: %d\n", id)
	fmt.Fprintf(ResponseWriter, "event: %s\n", eventType)
	fmt.Fprintf(ResponseWriter, "data: %s\n\n", data)
	FlusherWriter.Flush()
	id++
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

	// 创建一个 session
	data := OutMessage{
		Type:     "text",
		Payload:  "连接成功，请稍后",
		ActionID: "",
	}
	dataBytes, _ := json.Marshal(data)
	PrintOut("200", string(dataBytes))

	modelRequestBody, _ := json.Marshal(map[string]interface{}{
		"model": "qwen/qwen3-32b:fre",
		// 创建 system 和 user 角色的消息
		"messages": []map[string]string{
			{
				"role":    "system",
				"content": InteractivePlanningSystemPrompt,
			},
			{
				"role":    "user",
				"content": ChatRequest.Text,
			},
		},
		"stream": true,
	})
	// 请求 openrouter 并传入 InteractivePlanningSystemPrompt
	// 将返回的内容写入会话
	req, _ := http.NewRequest("POST", "https://openrouter.ai/api/v1/chat/completions", bytes.NewBuffer(modelRequestBody))
	req.Header.Set("Authorization", "Bearer "+OpenRouterApiKey)
	req.Header.Set("Content-Type", "application/json")

	// 发送请求
	// 将返回的内容写入会话
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "调用大模型失败: "+err.Error(), http.StatusInternalServerError)
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
	}
}

func Loop() {
	maxOuterLoop := 5        // 外层最大循环次数
	currentLoop := 0         // 当前循环计数器（可被重置）
	abortSignal := false     // 主动中断信号
	pauseByExternal := false // 外部传入的暂停信号
	pauseByInternal := false // 内部主动暂停信号

	for currentLoop < maxOuterLoop {
		if abortSignal {
			fmt.Println("外层循环被中断")
			break
		}

		fmt.Printf("外层循环第 %d 次开始\n", currentLoop)

		// 内层循环（模拟与大模型交互）
		for {
			// 判断是否进入暂停状态
			if pauseByExternal || pauseByInternal {
				fmt.Println("内层循环已暂停...")
				time.Sleep(1 * time.Second) // 模拟等待恢复
				continue
			}

			// 模拟大模型交互逻辑
			fmt.Println("处理与大模型的交互...")

			// 模拟内部主动触发一次暂停
			if currentLoop == 2 {
				pauseByInternal = true
			}

			// 示例：当执行到第3次时，重置循环计数器
			if currentLoop == 2 {
				fmt.Println("检测到特定条件，重置循环计数器...")
				currentLoop = 0
				fmt.Printf("当前循环次数已被重置为：%d\n", currentLoop)
			}

			// 模拟短暂延迟后继续执行
			time.Sleep(500 * time.Millisecond)

			// 结束内层循环测试（模拟完成当前任务）
			if !pauseByExternal && !pauseByInternal && currentLoop == 4 {
				fmt.Println("内层循环结束")
				break
			}
		}

		currentLoop++ // 正常递增
	}
}
