package executor

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestResultRequiresCompleteValidStream(t *testing.T) {
	for _, raw := range []string{`{"kind":"result","data":{}}` + "\n", `{"kind":"result","data":{"text":"x","stopReason":"error","usage":{"input":1,"output":1,"totalTokens":2}}}` + "\n"} {
		if consume(strings.NewReader(raw), false, func(string, json.RawMessage) error { return nil }) {
			t.Fatal("invalid result completed")
		}
	}
}
func TestStrictResultAndPostTerminalFailures(t *testing.T) {
	good := `{"kind":"result","data":{"text":"hello","stopReason":"stop","verified":true,"modelCall":"call","rawUsage":{"prompt_tokens":32,"completion_tokens":2,"total_tokens":34},"usage":{"input":32,"output":2,"cacheRead":0,"cacheWrite":0,"totalTokens":34}}}` + "\n"
	if !consume(strings.NewReader(good), true, func(string, json.RawMessage) error { return nil }) {
		t.Fatal("valid strict result rejected")
	}
	for _, raw := range []string{good + `{"kind":"text","data":{"text":"late"}}` + "\n", strings.Replace(good, `"verified":true`, `"verified":false`, 1), strings.Replace(good, `"total_tokens":34`, `"total_tokens":35`, 1), strings.Replace(good, `"output":2`, `"output":0`, 1), strings.Replace(good, `"stopReason":"stop"`, `"stopReason":"toolUse"`, 1)} {
		if consume(strings.NewReader(raw), true, func(string, json.RawMessage) error { return nil }) {
			t.Fatal("bad strict stream accepted", raw)
		}
	}
	if consume(strings.NewReader(good), true, func(string, json.RawMessage) error { return json.Unmarshal([]byte("bad"), new(any)) }) {
		t.Fatal("failed persistence accepted")
	}
}
