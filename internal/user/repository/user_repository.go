package repository

import (
	"context"

	"github.com/google/uuid"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
)

// UserRepository is the user feature’s persistence layer; it delegates to sqlc Queries.
type UserRepository struct {
	q *sqldb.Queries
}

func NewUserRepository(q *sqldb.Queries) *UserRepository {
	return &UserRepository{q: q}
}

func (r *UserRepository) Create(ctx context.Context, arg sqldb.CreateUserParams) (sqldb.CreateUserRow, error) {
	return r.q.CreateUser(ctx, arg)
}

func (r *UserRepository) GetByEmail(ctx context.Context, email string) (sqldb.GetUserByEmailRow, error) {
	return r.q.GetUserByEmail(ctx, email)
}

func (r *UserRepository) GetByID(ctx context.Context, id uuid.UUID) (sqldb.GetUserByIDRow, error) {
	return r.q.GetUserByID(ctx, id)
}

func (r *UserRepository) InsertRefreshToken(ctx context.Context, arg sqldb.InsertRefreshTokenParams) (sqldb.InsertRefreshTokenRow, error) {
	return r.q.InsertRefreshToken(ctx, arg)
}

func (r *UserRepository) GetRefreshToken(ctx context.Context, token string) (sqldb.GetRefreshTokenRow, error) {
	return r.q.GetRefreshToken(ctx, token)
}

func (r *UserRepository) RevokeRefreshToken(ctx context.Context, token string) error {
	return r.q.RevokeRefreshToken(ctx, token)
}
