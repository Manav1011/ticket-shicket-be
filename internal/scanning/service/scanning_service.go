package service

import (
	"context"

	"github.com/manav1011/ticket-shicket-be/internal/scanning/repository"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
)

type ScanningService struct {
	repo *repository.ScanningRepostirory
}

func NewScanningService(repo *repository.ScanningRepostirory) *ScanningService {
	return &ScanningService{repo: repo}
}

func (s *ScanningService) ValidateQRCode(ctx context.Context, payload string) (bool, error) {
	// the payload is a jwt token that contains event_id, event_id event_day_id, ticket_id, ticket_index
	// decode the token
	claims, err := token.ParseToken(payload)
	if err != nil {
		return false, err
	}
	eventID, ok := claims["event_id"].(string)
	if !ok {
		return false, err
	}

	eventDayID, ok := claims["event_day_id"].(string)
	if !ok {
		return false, err
	}

	ticketIndex, ok := claims["ticket_index"].(float64)
	if !ok {
		return false, err
	}
	ticketIndexInt := int(ticketIndex)

	// generate the redis key using event_id and event_day_id
	key := eventID + ":" + eventDayID + ":bitmap"
	// check if the ticket is valid
	valid, err := s.repo.ValidateQRCode(ctx, key, ticketIndexInt)
	if err != nil {
		return false, err
	}
	if !valid {
		return false, nil
	}
	// mark the ticket as used
	err = s.repo.MarkQRCodeUsed(ctx, key, ticketIndexInt)
	if err != nil {
		return false, err
	}
	return true, nil
}
