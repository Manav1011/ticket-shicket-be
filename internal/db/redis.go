package db

import (
	"github.com/redis/go-redis/v9"
)

// NewRedisClient initializes and returns a Redis client using the provided config
func NewRedisClient(addr, password string, db int) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})
}
