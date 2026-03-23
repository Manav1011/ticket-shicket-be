package db

import (
	"context"
	"log"

	"github.com/jackc/pgx/v5/pgxpool"
)

func NewDB(source string) *pgxpool.Pool {
	ctx := context.Background()

	pool, err := pgxpool.New(ctx, source)
	if err != nil {
		log.Fatal("cannot connect to db:", err)
	}

	err = pool.Ping(ctx)
	if err != nil {
		log.Fatal("cannot ping db:", err)
	}

	log.Println("✅ Connected to database (pgx)")

	return pool
}
