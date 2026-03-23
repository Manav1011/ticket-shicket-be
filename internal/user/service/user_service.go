package service

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
	"github.com/manav1011/ticket-shicket-be/internal/user/model"
	"github.com/manav1011/ticket-shicket-be/internal/user/repository"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
	"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

// ErrInvalidCredentials is returned when login cannot be satisfied (wrong email/password or inactive user).
var ErrInvalidCredentials = errors.New("invalid credentials")

// ErrUserAlreadyExists is returned when during signup the email is already in use.
var ErrUserAlreadyExists = errors.New("user already exists")

type UserService struct {
	repo *repository.UserRepository
	cfg  *config.Config
}

func NewUserService(repo *repository.UserRepository, cfg *config.Config) *UserService {
	return &UserService{repo: repo, cfg: cfg}
}

// Login validates credentials, issues JWTs, and persists the refresh token.
func (s *UserService) Login(ctx context.Context, email, password string) (*model.LoginData, error) {
	row, err := s.repo.GetByEmail(ctx, email)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrInvalidCredentials
		}
		return nil, fmt.Errorf("get user: %w", err)
	}
	if !row.PasswordHash.Valid || row.PasswordHash.String == "" {
		return nil, ErrInvalidCredentials
	}
	if !utils.CheckPasswordHash(password, row.PasswordHash.String) {
		return nil, ErrInvalidCredentials
	}

	uid := row.ID.String()
	access, err := token.GenerateAccessToken(uid)
	if err != nil {
		return nil, fmt.Errorf("access token: %w", err)
	}
	refresh, err := token.GenerateRefreshToken(uid)
	if err != nil {
		return nil, fmt.Errorf("refresh token: %w", err)
	}

	expiresAt := time.Now().Add(s.cfg.RefreshTokenDuration)
	_, err = s.repo.InsertRefreshToken(ctx, sqldb.InsertRefreshTokenParams{
		UserID:    row.ID,
		Token:     refresh,
		ExpiresAt: expiresAt,
	})
	if err != nil {
		return nil, fmt.Errorf("persist refresh token: %w", err)
	}

	expiresIn := int64(s.cfg.AccessTokenDuration.Seconds())
	return &model.LoginData{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "Bearer",
		ExpiresIn:    expiresIn,
		User: model.LoginUser{
			ID:    row.ID,
			Email: row.Email,
		},
	}, nil
}

// Signup
func (s *UserService) Signup(ctx context.Context, name, email, password string) (*model.LoginUser, error) {
	// hash password
	passHashed, err := utils.HashPassword(password)
	if err != nil {
		return nil, fmt.Errorf("hash password: %w", err)
	}
	// create the user
	row, err := s.repo.Create(ctx, sqldb.CreateUserParams{
		Name:         sql.NullString{String: name, Valid: true},
		Email:        email,
		PasswordHash: sql.NullString{String: passHashed, Valid: true},
	})
	fmt.Println("created user:", err)
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) {
			if pgErr.Code == "23505" { // unique_violation
				return nil, ErrUserAlreadyExists
			}
		}
		return nil, fmt.Errorf("create user: %w", err)
	}
	return &model.LoginUser{
		ID:    row.ID,
		Email: row.Email,
	}, nil
}

// refresh
func (s *UserService) Refresh(ctx context.Context, refreshToken string) (*model.RefreshSuccessEnvelope, error) {
	// step parse and validate the incoming refresh token
	claims, err := token.ParseToken(refreshToken)
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}
	if claims["type"] != "refresh" {
		return nil, ErrInvalidCredentials
	}

	// check if the token exists in the db
	refreshRow, err := s.repo.GetRefreshToken(ctx, refreshToken)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrInvalidCredentials
		}
		return nil, fmt.Errorf("get refresh token: %w", err)
	}

	if refreshRow.Revoked.Valid && refreshRow.Revoked.Bool {
		return nil, ErrInvalidCredentials
	}

	// Invvalidate old refresh token
	err = s.repo.RevokeRefreshToken(ctx, refreshToken)
	if err != nil {
		return nil, fmt.Errorf("revoke refresh token: %w", err)
	}

	userId, ok := claims["user_id"].(string)
	if !ok {
		return nil, ErrInvalidCredentials
	}
	access, err := token.GenerateAccessToken(userId)
	if err != nil {
		return nil, fmt.Errorf("access token: %w", err)
	}
	refresh, err := token.GenerateRefreshToken(userId)
	if err != nil {
		return nil, fmt.Errorf("refresh token: %w", err)
	}

	userUUID, err := uuid.Parse(userId)
	if err != nil {
		return nil, fmt.Errorf("parse user id: %w", err)
	}

	expiresAt := time.Now().Add(s.cfg.RefreshTokenDuration)
	_, err = s.repo.InsertRefreshToken(ctx, sqldb.InsertRefreshTokenParams{
		UserID:    userUUID,
		Token:     refresh,
		ExpiresAt: expiresAt,
	})
	if err != nil {
		return nil, fmt.Errorf("persist refresh token: %w", err)
	}

	expiresIn := int64(s.cfg.AccessTokenDuration.Seconds())
	return &model.RefreshSuccessEnvelope{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "Bearer",
		ExpiresIn:    expiresIn,
	}, nil
}
