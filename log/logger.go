package log

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type DailyLogger struct {
	logDir      string
	currentDate string
}

func New(logDir string) *DailyLogger {
	_ = os.MkdirAll(logDir, 0755) // 创建日志目录
	return &DailyLogger{
		logDir:      logDir,
		currentDate: getCurrentDate(),
	}
}

func getCurrentDate() string {
	return time.Now().Format("2006-01-02")
}

func (l *DailyLogger) getLogFile(logType string) string {
	currentDate := getCurrentDate()
	filename := currentDate
	if logType == "ERROR" {
		filename += ".error.log"
	} else {
		filename += ".log"
	}
	return filepath.Join(l.logDir, filename)
}

func (l *DailyLogger) writeLog(logType, message string) {
	logFile := l.getLogFile(logType)
	timestamp := time.Now().Format(time.RFC3339)
	logMessage := fmt.Sprintf("[%s] [%s] %s\n", timestamp, logType, message)

	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	_, _ = f.WriteString(logMessage)
}

func (l *DailyLogger) Info(message string) {
	l.writeLog("INFO", message)
}

func (l *DailyLogger) Warn(message string) {
	l.writeLog("WARN", message)
}

func (l *DailyLogger) Error(message string) {
	l.writeLog("ERROR", message)
}
