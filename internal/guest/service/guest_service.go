package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/guest/model"
	"github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
)

var ErrGuestRegistrationFailed = errors.New("guest registration failed")

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
