package repository

import (
	"context"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/db"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
)

func TestCreateAndGetGuest(t *testing.T) {
	cfg := config.LoadConfig()
	pool := db.NewDB(cfg.DBSource)
	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)
	repo := NewGuestRepository(queries)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	userAgent := "Mozilla/5.0"
	ipAddress := "192.168.1.1"

	guest, err := repo.CreateGuest(ctx, userAgent, ipAddress)
	if err != nil {
		t.Fatalf("CreateGuest failed: %v", err)
	}
	if guest.GuestID.String() == "" {
		t.Fatal("Expected guest_id, got empty UUID")
	}
	if guest.UserAgent.String != userAgent {
		t.Fatalf("Expected user_agent %s, got %s", userAgent, guest.UserAgent.String)
	}
	if guest.IpAddress.String != ipAddress {
		t.Fatalf("Expected ip_address %s, got %s", ipAddress, guest.IpAddress.String)
	}

	retrieved, err := repo.GetGuestByID(ctx, guest.GuestID)
	if err != nil {
		t.Fatalf("GetGuestByID failed: %v", err)
	}
	if retrieved.GuestID != guest.GuestID {
		t.Fatalf("Expected guest_id %s, got %s", guest.GuestID, retrieved.GuestID)
	}
}
