package guest

import (
"bytes"
"encoding/json"
"net/http"
"net/http/httptest"
"testing"

"github.com/gin-gonic/gin"
"github.com/jackc/pgx/v5/stdlib"
"github.com/manav1011/ticket-shicket-be/internal/config"
"github.com/manav1011/ticket-shicket-be/internal/db"
sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
guestHandler "github.com/manav1011/ticket-shicket-be/internal/guest/handler"
guestModel "github.com/manav1011/ticket-shicket-be/internal/guest/model"
guestRepo "github.com/manav1011/ticket-shicket-be/internal/guest/repository"
guestSvc "github.com/manav1011/ticket-shicket-be/internal/guest/service"
"github.com/manav1011/ticket-shicket-be/pkg/token"
)

func TestGuestRegistrationFlow(t *testing.T) {
	cfg := config.LoadConfig()
	pool := db.NewDB(cfg.DBSource)
	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)
	repo := guestRepo.NewGuestRepository(queries)
	svc := guestSvc.NewGuestService(repo, cfg)
	handler := guestHandler.NewGuestHandler(svc)

	router := gin.New()
	v1 := router.Group("/v1")
	RegisterRoutes(v1, handler)

	// Request body
	req := guestModel.GuestRegisterRequest{
		UserAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
		IpAddress: "192.168.1.1",
	}
	body, _ := json.Marshal(req)

	// Make request
	httpReq := httptest.NewRequest("POST", "/v1/guests/register", bytes.NewBuffer(body))
	httpReq.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, httpReq)

	// Verify response
	if w.Code != http.StatusOK {
		t.Fatalf("Expected 200, got %d: %s", w.Code, w.Body.String())
	}

	var respBody map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &respBody); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if !respBody["success"].(bool) {
		t.Fatal("Expected success to be true")
	}

	data := respBody["data"].(map[string]interface{})
	if data["access_token"] == "" {
		t.Fatal("Expected access_token in response")
	}
	if data["refresh_token"] == "" {
		t.Fatal("Expected refresh_token in response")
	}

	// Verify token contains guest_id
	accessToken := data["access_token"].(string)
	claims, err := token.ParseToken(accessToken)
	if err != nil {
		t.Fatalf("Failed to parse token: %v", err)
	}
	if claims["guest_id"] == nil {
		t.Fatal("Expected guest_id in token claims")
	}
}
