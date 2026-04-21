import pytest
from src.utils.claim_link_utils import generate_claim_link_token


def test_generate_claim_link_token_returns_correct_length():
    token = generate_claim_link_token()
    assert len(token) == 8


def test_generate_claim_link_token_returns_string():
    token = generate_claim_link_token()
    assert isinstance(token, str)


def test_generate_claim_link_token_is_alphanumeric():
    token = generate_claim_link_token()
    assert token.isalnum()


def test_generate_claim_link_token_produces_unique_tokens():
    tokens = {generate_claim_link_token() for _ in range(100)}
    # With 8 chars from lowercase + digits (36 chars), 100 tokens should all be unique
    assert len(tokens) == 100


def test_generate_claim_link_token_custom_length():
    token = generate_claim_link_token(length=12)
    assert len(token) == 12
