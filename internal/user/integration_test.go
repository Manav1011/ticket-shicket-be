package user

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/db"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
	"github.com/manav1011/ticket-shicket-be/internal/user/handler"
	"github.com/manav1011/ticket-shicket-be/internal/user/repository"
	"github.com/manav1011/ticket-shicket-be/internal/user/service"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
	"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

func TestUserRefreshFlow(t *testing.T) {
	cfg := config.LoadConfig()
	pool := db.NewDB(cfg.DBSource)
	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)
	repo := repository.NewUserRepository(queries)
	svc := service.NewUserService(repo, cfg)
	h := handler.NewUserHandler(svc)

	router := gin.New()
	v1 := router.Group("/v1")
	RegisterRoutes(v1, h)

	email := fmt.Sprintf("refresh-user-%d@example.com", time.Now().UnixNano())
	password := "pass123456"
	hash, err := utils.HashPassword(password)
	if err != nil {
		t.Fatalf("hash password: %v", err)
	}

	_, err = repo.Create(context.Background(), sqldb.CreateUserParams{
		Name:         sql.NullString{String: "Refresh User", Valid: true},
		Email:        email,
		PasswordHash: sql.NullString{String: hash, Valid: true},
	})
	if err != nil {
		t.Fatalf("create user: %v", err)
	}

	loginBody, _ := json.Marshal(map[string]string{
		"email":    email,
		"password": password,
	})
	loginReq := httptest.NewRequest("POST", "/v1/users/login", bytes.NewBuffer(loginBody))
	loginReq.Header.Set("Content-Type", "application/json")
	loginW := httptest.NewRecorder()
	router.ServeHTTP(loginW, loginReq)

	if loginW.Code != http.StatusOK {
		t.Fatalf("login failed: %d %s", loginW.Code, loginW.Body.String())
	}

	var loginResp map[string]interface{}
	if err := json.Unmarshal(loginW.Body.Bytes(), &loginResp); err != nil {
		t.Fatalf("parse login response: %v", err)
	}
	oldRefreshToken, _ := loginResp["data"].(map[string]interface{})["refresh_token"].(string)
	if oldRefreshToken == "" {
		t.Fatal("expected refresh token from login")
	}

	refreshBody, _ := json.Marshal(map[string]string{
		"refresh_token": oldRefreshToken,
	})
	refreshReq := httptest.NewRequest("POST", "/v1/users/refresh", bytes.NewBuffer(refreshBody))
	refreshReq.Header.Set("Content-Type", "application/json")
	refreshW := httptest.NewRecorder()
	router.ServeHTTP(refreshW, refreshReq)

	if refreshW.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", refreshW.Code, refreshW.Body.String())
	}

	var refreshResp map[string]interface{}
	if err := json.Unmarshal(refreshW.Body.Bytes(), &refreshResp); err != nil {
		t.Fatalf("parse refresh response: %v", err)
	}
	newAccessToken, _ := refreshResp["data"].(map[string]interface{})["access_token"].(string)
	newRefreshToken, _ := refreshResp["data"].(map[string]interface{})["refresh_token"].(string)

	if newAccessToken == "" {
		t.Fatal("expected new access token")
	}
	if newRefreshToken == "" {
		t.Fatal("expected new refresh token")
	}
	if newRefreshToken == oldRefreshToken {
		t.Fatal("expected rotated refresh token")
	}

	claims, err := token.ParseToken(newAccessToken)
	if err != nil {
		t.Fatalf("parse new access token: %v", err)
	}
	if claims["user_id"] == nil {
		t.Fatal("expected user_id in access token claims")
	}
}
