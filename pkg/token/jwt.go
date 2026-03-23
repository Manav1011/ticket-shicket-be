package token

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/manav1011/ticket-shicket-be/internal/config"
)

var cfg = config.LoadConfig()

func GenerateAccessToken(userID string) (string, error) {
	claims := jwt.MapClaims{
		"user_id": userID,
		"type":    "access",
		"jti":     uuid.NewString(),
		"exp":     time.Now().Add(cfg.AccessTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWTSecret))
}

func GenerateRefreshToken(userID string) (string, error) {
	claims := jwt.MapClaims{
		"user_id": userID,
		"type":    "refresh",
		"jti":     uuid.NewString(),
		"exp":     time.Now().Add(cfg.RefreshTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWTSecret))
}

func ParseToken(tokenStr string) (jwt.MapClaims, error) {
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, jwt.ErrSignatureInvalid
		}
		return []byte(cfg.JWTSecret), nil
	})
	if err != nil {
		return nil, err
	}
	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		return claims, nil
	}
	return nil, jwt.ErrInvalidKey
}

// Guest token generation
func GenerateAccessTokenGuest(guestID string) (string, error) {
	claims := jwt.MapClaims{
		"guest_id": guestID,
		"type":     "access",
		"jti":      uuid.NewString(),
		"exp":      time.Now().Add(cfg.AccessTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWTSecret))
}

func GenerateRefreshTokenGuest(guestID string) (string, error) {
	claims := jwt.MapClaims{
		"guest_id": guestID,
		"type":     "refresh",
		"jti":      uuid.NewString(),
		"exp":      time.Now().Add(cfg.RefreshTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWTSecret))
}
