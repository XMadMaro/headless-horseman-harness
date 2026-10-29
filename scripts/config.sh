#!/usr/bin/env bash
# config.sh — Konfiguracja ścieżek dla Headless Horseman Harness
# Edytuj te wartości w zależności od struktury Twojego monorepo.

# STANDARD_TRACK — kod podlegający pełnym bramkom (Inception Gate, Adversarial Review)
APPS_GLOB="apps/* packages/* src/*"

# FAST_TRACK — zmiany czysto dokumentacyjne (omijają bramki architektoniczne)
DOCS_GLOB="*.md .env.example .github/** docs/**"

# Ścieżka do migracji bazodanowych (sprawdzanie niszczących migracji DROP bez tagu APPROVED)
MIGRATIONS_GLOB="**/migrations/* **/alembic/**"

# Czy włączyć regułę S7 (sprawdzanie wycieków tenanta / IDOR w multi-tenant RLS)
ENABLE_TENANT_CHECK=false
