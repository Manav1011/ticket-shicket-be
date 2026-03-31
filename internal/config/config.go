package config

import (
	"log"
	"os"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	DBDriver string
	DBSource string

	ServerPort string

	JWTSecret string

	AccessTokenDuration  time.Duration
	RefreshTokenDuration time.Duration

	RedisAddr      string
	RedisPassword  string
	RedisDefaultDB int
}

func LoadConfig() *Config {
	err := godotenv.Load(".env")
	if err != nil {
		log.Fatal("Error loading .env file")
	}

	accessDuration, err := time.ParseDuration(os.Getenv("ACCESS_TOKEN_DURATION"))
	if err != nil {
		log.Fatal("Error parsing ACCESS_TOKEN_DURATION")
	}

	refreshDuration, err := time.ParseDuration(os.Getenv("REFRESH_TOKEN_DURATION"))
	if err != nil {
		log.Fatal("Error parsing REFRESH_TOKEN_DURATION")
	}

	return &Config{
		DBDriver: os.Getenv("DB_DRIVER"),
		DBSource: os.Getenv("DB_SOURCE"),

		ServerPort: os.Getenv("SERVER_PORT"),

		JWTSecret: os.Getenv("JWT_SECRET"),

		AccessTokenDuration:  accessDuration,
		RefreshTokenDuration: refreshDuration,
		RedisAddr:            os.Getenv("REDIS_HOST") + ":" + os.Getenv("REDIS_PORT"),
		RedisPassword:        os.Getenv("REDIS_PASSWORD"),
		RedisDefaultDB:       0,
	}

}
