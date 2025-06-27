package outbox

type PayloadType struct {
	Content string                 `json:"content"`
	Meta    map[string]interface{} `json:"meta"`
}

type MessageType struct {
	Type     string      `json:"type"`
	Payload  PayloadType `json:"payload"`
	ActionID string      `json:"actionID"`
}

// 会话
type Session struct {
	sessionIDMap map[string][]MessageType
}

func NewSession() *Session {
	return &Session{
		sessionIDMap: make(map[string][]MessageType),
	}
}
func (s *Session) AddEntry(sessionID string, entry MessageType) {
	s.sessionIDMap[sessionID] = append(s.sessionIDMap[sessionID], entry)
}

func (s *Session) GetEntries(sessionID string) ([]MessageType, bool) {
	entries, exists := s.sessionIDMap[sessionID]
	return entries, exists
}

func (s *Session) DeleteEntries(sessionID string) {
	delete(s.sessionIDMap, sessionID)
}

// UpdateEntry
func (s *Session) UpdateEntry(sessionID string, index int, entry MessageType) bool {
	if entries, exists := s.sessionIDMap[sessionID]; exists && index >= 0 && index < len(entries) {
		entries[index] = entry
		return true
	}
	return false
}

// 删除最后一条信息
func (s *Session) DeleteLastEntry(sessionID string) {
	entries, exists := s.sessionIDMap[sessionID]
	if exists && len(entries) > 0 {
		s.sessionIDMap[sessionID] = entries[:len(entries)-1]
	}
}
