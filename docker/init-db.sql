-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create database if it doesn't exist
-- This is handled by the POSTGRES_DB environment variable
