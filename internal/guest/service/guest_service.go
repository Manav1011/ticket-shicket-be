package service

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/manav1011/ticket-shicket-be/internal/config"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
	"github.com/manav1011/ticket-shicket-be/internal/guest/model"
	"github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
)

var ErrGuestRegistrationFailed = errors.New("guest registration failed")
var ErrGuestInvalidRefreshToken = errors.New("invalid guest refresh token")

type GuestService struct {
	repo *repository.GuestRepository
	cfg  *config.Config
}

func NewGuestService(repo *repository.GuestRepository, cfg *config.Config) *GuestService {
	return &GuestService{repo: repo, cfg: cfg}
}

// Register creates a new guest and issues JWT tokens
func (s *GuestService) Register(ctx context.Context, userAgent, ipAddress string) (*model.GuestRegisterData, error) {
	// Create guest in database
	guest, err := s.repo.CreateGuest(ctx, userAgent, ipAddress)
	if err != nil {
		return nil, fmt.Errorf("create guest: %w", err)
	}

	// Generate tokens with guest_id
	guestID := guest.GuestID.String()
	access, err := token.GenerateAccessTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("access token: %w", err)
	}
	refresh, err := token.GenerateRefreshTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("refresh token: %w", err)
	}

	// Persist refresh token to database
	expiresAt := time.Now().Add(s.cfg.RefreshTokenDuration)
	_, err = s.repo.InsertGuestRefreshToken(ctx, sqldb.InsertGuestRefreshTokenParams{
		GuestID:   guest.GuestID,
		Token:     refresh,
		ExpiresAt: expiresAt,
		UserAgent: sql.NullString{String: userAgent, Valid: userAgent != ""},
		IpAddress: sql.NullString{String: ipAddress, Valid: ipAddress != ""},
	})
	if err != nil {
		return nil, fmt.Errorf("persist refresh token: %w", err)
	}

	expiresIn := int64(s.cfg.AccessTokenDuration.Seconds())
	createdAtUnix := guest.CreatedAt.Time.Unix()
	if createdAtUnix == 0 {
		createdAtUnix = time.Now().Unix()
	}

	return &model.GuestRegisterData{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "Bearer",
		ExpiresIn:    expiresIn,
		Guest: model.GuestInfo{
			ID:        guest.GuestID,
			Slug:      guest.Slug.UUID,
			CreatedAt: createdAtUnix,
		},
	}, nil
}

// Refresh validates a guest refresh token and issues new tokens.
func (s *GuestService) Refresh(ctx context.Context, refreshToken string) (*model.GuestRefreshSuccessEnvelope, error) {
	claims, err := token.ParseToken(refreshToken)
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}
	if claims["type"] != "refresh" {
		return nil, ErrGuestInvalidRefreshToken
	}

	refreshRow, err := s.repo.GetGuestRefreshToken(ctx, refreshToken)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrGuestInvalidRefreshToken
		}
		return nil, fmt.Errorf("get refresh token: %w", err)
	}

	if refreshRow.Revoked.Valid && refreshRow.Revoked.Bool {
		return nil, ErrGuestInvalidRefreshToken
	}

	err = s.repo.RevokeGuestRefreshToken(ctx, refreshToken)
	if err != nil {
		return nil, fmt.Errorf("revoke refresh token: %w", err)
	}

	guestID, ok := claims["guest_id"].(string)
	if !ok || guestID == "" {
		return nil, ErrGuestInvalidRefreshToken
	}

	access, err := token.GenerateAccessTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("access token: %w", err)
	}
	refresh, err := token.GenerateRefreshTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("refresh token: %w", err)
	}

	expiresAt := time.Now().Add(s.cfg.RefreshTokenDuration)
	_, err = s.repo.InsertGuestRefreshToken(ctx, sqldb.InsertGuestRefreshTokenParams{
		GuestID:   refreshRow.GuestID,
		Token:     refresh,
		ExpiresAt: expiresAt,
		UserAgent: refreshRow.UserAgent,
		IpAddress: refreshRow.IpAddress,
	})
	if err != nil {
		return nil, fmt.Errorf("persist refresh token: %w", err)
	}

	return &model.GuestRefreshSuccessEnvelope{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "Bearer",
		ExpiresIn:    int64(s.cfg.AccessTokenDuration.Seconds()),
	}, nil
}
