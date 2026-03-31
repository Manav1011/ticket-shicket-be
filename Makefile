DB_URL=postgres://postgres:postgres@localhost:54322/ticket-shicket?sslmode=disable

# --- Swagger (swaggo) ---
# Regenerate docs after changing // @ annotations. Add new ./internal/... dirs here if you document more packages.
# Use -g main.go (not cmd/server/main.go) so swag does not double path with -d ./cmd/server.
swag:
	go run github.com/swaggo/swag/cmd/swag@latest init -g main.go -d ./cmd/server,./internal/user/handler,./internal/user/model,./internal/guest/handler,./internal/guest/model,./internal/scanning/handler,./internal/scanning/model,./pkg/utils -o ./docs --parseInternal

# --- Migrations ---
migrate-up:
	migrate -path ./migrations -database "$(DB_URL)" up

migrate-down:
	migrate -path ./migrations -database "$(DB_URL)" down 1

migrate-down-all:
	migrate -path ./migrations -database "$(DB_URL)" down

migrate-force:
	migrate -path ./migrations -database "$(DB_URL)" force $(VERSION)

migrate-version:
	migrate -path ./migrations -database "$(DB_URL)" version

# --- Create Migration ---
create-migration:
	migrate create -ext sql -dir ./migrations -seq $(name)
