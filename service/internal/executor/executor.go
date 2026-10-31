// Package executor runs a bounded pool. Ambiguous failures are terminal and never automatically resent.
package executor

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"github.com/jackc/pgx/v5"
	"github.com/pym96/pi-agent-platform/service/internal/store"
	"log"
	"net/http"
	"time"
)

type Pool struct {
	Store  *store.Store
	Strict bool
	URL    string
	Notify func(string)
	Fatal  func(error)
}

func (p *Pool) Run(ctx context.Context) {
	client := &http.Client{Timeout: 60 * time.Second}
	for {
		if ctx.Err() != nil {
			return
		}
		t, e := p.Store.Claim(ctx)
		if e != nil {
			if !errors.Is(e, pgx.ErrNoRows) && ctx.Err() == nil {
				log.Printf("claim failed: %v", e)
			}
			select {
			case <-ctx.Done():
				return
			case <-time.After(100 * time.Millisecond):
			}
			continue
		}
		started := time.Now()
		trace := func(phase, status string) {
			raw, _ := json.Marshal(map[string]any{"task": t.ID, "session": t.Session, "phase": phase, "status": status, "clock": "go-since-claim", "sinceClaimNs": time.Since(started).Nanoseconds(), "utc": time.Now().UTC()})
			log.Print(string(raw))
		}
		trace("pi_request_start", "running")
		p.Notify(t.Session)
		status := "interrupted"
		body, _ := json.Marshal(map[string]string{"session": t.Session, "task": t.ID, "prompt": t.Prompt})
		requestCtx, cancel := context.WithTimeout(ctx, 60*time.Second)
		req, _ := http.NewRequestWithContext(requestCtx, "POST", p.URL+"/run", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		resp, err := client.Do(req)
		if err == nil {
			if resp.StatusCode == 200 {
				if consume(resp.Body, p.Strict, func(kind string, data json.RawMessage) error {
					trace("pi_event_"+kind, "running")
					if err := p.Store.Append(requestCtx, t, kind, data); err != nil {
						return err
					}
					p.Notify(t.Session)
					return nil
				}) {
					status = "completed"
				}
			}
			resp.Body.Close()
		}
		cancel()
		// Retry only an idempotent state transaction, never the model request.
		var finishErr error
		for attempt := 0; attempt < 3; attempt++ {
			finishCtx, finishCancel := context.WithTimeout(context.Background(), 5*time.Second)
			finishErr = p.Store.Finish(finishCtx, t, status)
			finishCancel()
			if finishErr == nil {
				break
			}
			time.Sleep(time.Duration(attempt+1) * 100 * time.Millisecond)
		}
		if finishErr != nil {
			log.Printf("terminal persistence unresolved task=%s; stopping", t.ID)
			if p.Fatal != nil {
				p.Fatal(finishErr)
			}
			return
		}
		trace("durable_terminal", status)
		p.Notify(t.Session)
	}
}
