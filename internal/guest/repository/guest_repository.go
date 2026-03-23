package repository

import (
	"context"
	"database/sql"

	"github.com/google/uuid"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
)

// GuestRepository is the guest feature's persistence layer; it delegates to sqlc Queries.
type GuestRepository struct {
	q *sqldb.Queries
}

func NewGuestRepository(q *sqldb.Queries) *GuestRepository {
	return &GuestRepository{q: q}
}

func (r *GuestRepository) CreateGuest(ctx context.Context, userAgent, ipAddress string) (sqldb.Guest, error) {
	return r.q.CreateGuest(ctx, sqldb.CreateGuestParams{
		UserAgent: sql.NullString{String: userAgent, Valid: userAgent != ""},
		IpAddress: sql.NullString{String: ipAddress, Valid: ipAddress != ""},
	})
}

func (r *GuestRepository) GetGuestByID(ctx context.Context, guestID uuid.UUID) (sqldb.Guest, error) {
	return r.q.GetGuestByID(ctx, guestID)
}

func (r *GuestRepository) UpdateGuestLastActive(ctx context.Context, guestID uuid.UUID) (sqldb.Guest, error) {
	return r.q.UpdateGuestLastActive(ctx, guestID)
}
