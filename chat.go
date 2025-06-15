package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

type ChatRequest struct {
	Messages []Message `json:"messages"`
	Model    string    `json:"model"`
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type OpenRouterResponse struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
	} `json:"choices"`
}

func Chat(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "读取请求体失败", http.StatusBadRequest)
		return
	}

	var chatReq ChatRequest
	if err := json.Unmarshal(body, &chatReq); err != nil {
		http.Error(w, "解析请求体失败", http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming 不支持", http.StatusInternalServerError)
		return
	}

	data := struct {
		Content string `json:"content"`
		Type    string `json:"type"`
	}{
		Content: "连接成功，请稍后",
		Type:    "statusText",
	}
	dataBytes, _ := json.Marshal(data)
	fmt.Fprintf(w, "id: %d\n", 0)
	fmt.Fprintf(w, "event: %s\n", "200")
	fmt.Fprintf(w, "data: %s\n\n", dataBytes)
	flusher.Flush()

	fmt.Printf("提示词: %v\n", chatReq.Messages)

	requestBody, _ := json.Marshal(map[string]interface{}{
		"model":    chatReq.Model,
		"messages": chatReq.Messages,
		"stream":   true,
	})

	req, _ := http.NewRequest("POST", "https://openrouter.ai/api/v1/chat/completions", bytes.NewBuffer(requestBody))
	req.Header.Set("Authorization", "Bearer "+config.ModelProviderAPIKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "调用大模型失败: "+err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	eventType := "message"
	var eventId int64 = 0

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if len(line) > 6 && line[:6] == "data: " {
			data := line[6:]
			if data == "[DONE]" {

				break
			}
			var orResp OpenRouterResponse
			if err := json.Unmarshal([]byte(data), &orResp); err == nil {
				if len(orResp.Choices) > 0 {
					content := orResp.Choices[0].Delta.Content
					if content != "" {

						eventId++ // 每次发送时递增 ID

						data := struct {
							Content string `json:"content"`
							Type    string `json:"type"`
						}{
							Content: content,
							Type:    "text",
						}
						dataBytes, _ := json.Marshal(data)

						fmt.Fprintf(w, "id: %d\n", eventId)
						fmt.Fprintf(w, "event: %s\n", eventType)
						fmt.Fprintf(w, "data: %s\n\n", dataBytes)
						flusher.Flush()
					}
				}
			}
		}
	}
}
