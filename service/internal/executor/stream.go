package executor

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
)

// consume accepts result as provisional until the complete NDJSON response ends.
// PostgreSQL completed is written by the caller after this returns true.
func consume(reader io.Reader, strict bool, appendEvent func(string, json.RawMessage) error) bool {
	scanner := bufio.NewScanner(io.LimitReader(reader, 2<<20))
	scanner.Buffer(make([]byte, 4096), 65536)
	result := false
	count := 0
	for scanner.Scan() {
		count++
		if count > 512 || result {
			return false
		}
		var ev struct {
			Kind string          `json:"kind"`
			Data json.RawMessage `json:"data"`
		}
		if json.Unmarshal(scanner.Bytes(), &ev) != nil {
			return false
		}
		switch ev.Kind {
		case "runtime":
		case "text":
			var text struct {
				Text string `json:"text"`
			}
			if json.Unmarshal(ev.Data, &text) != nil || text.Text == "" {
				return false
			}
		case "result":
			var value struct {
				Text       string           `json:"text"`
				StopReason string           `json:"stopReason"`
				Verified   bool             `json:"verified"`
				ModelCall  string           `json:"modelCall"`
				RawUsage   map[string]int64 `json:"rawUsage"`
				Usage      struct {
					Input      int64 `json:"input"`
					Output     int64 `json:"output"`
					CacheRead  int64 `json:"cacheRead"`
					CacheWrite int64 `json:"cacheWrite"`
					Total      int64 `json:"totalTokens"`
				} `json:"usage"`
			}
			if json.Unmarshal(ev.Data, &value) != nil || strings.TrimSpace(value.Text) == "" || (value.StopReason != "stop" && value.StopReason != "length") {
				return false
			}
			u := value.Usage
			if u.Input < 0 || u.Output < 0 || u.CacheRead < 0 || u.CacheWrite < 0 || u.Total != u.Input+u.Output+u.CacheRead+u.CacheWrite {
				return false
			}
			if strict {
				r := value.RawUsage
				p, pok := r["prompt_tokens"]
				o, ook := r["completion_tokens"]
				total, tok := r["total_tokens"]
				if !value.Verified || value.ModelCall == "" || len(r) != 3 || !pok || !ook || !tok || p < 0 || o < 0 || o > 128 || total > 1024 || total != p+o || u.Input != p || u.Output != o || u.Total != total {
					return false
				}
			}
			result = true
		default:
			return false
		}
		if appendEvent(ev.Kind, ev.Data) != nil {
			return false
		}
	}
	return result && scanner.Err() == nil
}
