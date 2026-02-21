"""CLI smoke tests — verify all subcommands register and basic argument handling."""

from __future__ import annotations

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


class TestCLIRegistration:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "server" in result.output
        assert "tool" in result.output
        assert "agent" in result.output

    def test_server_help(self):
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "health" in result.output
        assert "list-tools" in result.output
        assert "start" in result.output

    def test_tool_help(self):
        result = runner.invoke(app, ["tool", "--help"])
        assert result.exit_code == 0
        assert "decode-vin" in result.output
        assert "ratings-search" in result.output
        assert "recalls" in result.output
        assert "complaints" in result.output
        assert "carseat" in result.output

    def test_agent_help(self):
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "ask" in result.output
        assert "demo" in result.output
        assert "chat" in result.output


class TestCLIErrors:
    def test_decode_vin_no_args(self):
        result = runner.invoke(app, ["tool", "decode-vin"])
        assert result.exit_code != 0

    def test_ratings_search_missing_args(self):
        result = runner.invoke(app, ["tool", "ratings-search"])
        assert result.exit_code != 0

    def test_carseat_no_location(self):
        result = runner.invoke(app, ["tool", "carseat"])
        # Should fail because no --zip, --state, or --lat/--long
        assert result.exit_code != 0
