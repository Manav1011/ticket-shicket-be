package repository

import (
	"context"
	"testing"

	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
)

func TestValidateAndMarkQRCode(t *testing.T) {
	ctx := context.Background()
	// Initialize Redis client (use a test Redis instance or mock)
	rc := redis.NewClient(&redis.Options{
		Addr: "localhost:63799",
		DB:   1, // use a separate DB for testing
	})

	repo := &ScanningRepostirory{rc: rc}

	key := "test:event_day:bitmap"
	index := 5

	// Ensure bit is 0
	rc.SetBit(ctx, key, int64(index), 0)

	// Should be false (not used)
	used, err := repo.ValidateQRCode(ctx, key, index)
	require.NoError(t, err)
	require.False(t, used)

	// Mark as used
	err = repo.MarkQRCodeUsed(ctx, key, index)
	require.NoError(t, err)

	// Should be true (used)
	used, err = repo.ValidateQRCode(ctx, key, index)
	require.NoError(t, err)
	require.True(t, used)

	// Cleanup
	rc.Del(ctx, key)

}
