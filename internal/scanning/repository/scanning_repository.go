package repository

import (
	"context"

	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
	"github.com/redis/go-redis/v9"
)

type ScanningRepostirory struct {
	q  *sqldb.Queries
	rc *redis.Client
}

func NewScanningRepository(q *sqldb.Queries, rc *redis.Client) *ScanningRepostirory {
	return &ScanningRepostirory{q: q, rc: rc}
}

func (r *ScanningRepostirory) ValidateQRCode(ctx context.Context, key string, index int) (bool, error) {
	// check if the key's index bit is 0 or 1
	bit, err := r.rc.GetBit(ctx, key, int64(index)).Result()
	if err != nil {
		return false, err
	}
	return bit == 0, nil
}

func (r *ScanningRepostirory) MarkQRCodeUsed(ctx context.Context, key string, index int) error {
	// set the key's index bit to 1
	_, err := r.rc.SetBit(ctx, key, int64(index), 1).Result()
	return err
}
